"""
Workery do operacji masowych (bulk) na wielu plikach jednocześnie.
"""

import logging
import os
import shutil
from collections import defaultdict
from typing import List, Tuple

from src.models.file_pair import FilePair
from src.utils.path_utils import normalize_path

from .base_workers import BatchOperationMixin, UnifiedBaseWorker, WorkerPriority

logger = logging.getLogger(__name__)


class BulkWorkerBase(UnifiedBaseWorker, BatchOperationMixin):
    """Klasa bazowa dla wszystkich bulk workerów z wspólną funkcjonalnością."""

    def __init__(self, timeout_seconds: int = 300, batch_size: int = 20):
        UnifiedBaseWorker.__init__(
            self, timeout_seconds=timeout_seconds, priority=WorkerPriority.NORMAL
        )
        BatchOperationMixin.__init__(self, batch_size)
        self.error_count = 0
        self.success_count = 0
        self.detailed_errors = []

    def _validate_file_list(self, files: list, error_msg: str):
        """Wspólna walidacja listy plików."""
        if not files:
            raise ValueError(error_msg)

    def _validate_directory(self, directory: str, error_msg: str):
        """Wspólna walidacja katalogu."""
        if not directory:
            raise ValueError(f"{error_msg} - katalog nie może być pusty")
        if not os.path.isdir(directory):
            raise ValueError(f"{error_msg} - katalog nie istnieje: {directory}")

    def _safe_file_operation(self, operation_func, file_path: str, *args, **kwargs):
        """Bezpieczne wykonanie operacji na pliku z obsługą błędów."""
        try:
            return operation_func(file_path, *args, **kwargs)
        except FileNotFoundError:
            logger.warning(f"Plik nie istnieje: {file_path}")
            return False
        except PermissionError as e:
            self.error_count += 1
            self.detailed_errors.append(
                {
                    "file_path": file_path,
                    "error": f"Brak uprawnień: {str(e)}",
                    "error_type": "PERMISSION_ERROR",
                }
            )
            logger.error(f"Brak uprawnień do {file_path}: {str(e)}")
            return False
        except Exception as e:
            self.error_count += 1
            self.detailed_errors.append(
                {"file_path": file_path, "error": str(e), "error_type": "UNKNOWN_ERROR"}
            )
            logger.error(f"Błąd operacji na {file_path}: {str(e)}", exc_info=True)
            return False

    def _emit_progress_with_throttle(
        self, processed: int, total: int, message: str, throttle: int = 25
    ):
        """Emituj progress z throttling."""
        if processed % throttle == 0 or processed % max(1, total // 20) == 0:
            percent = int((processed / total) * 100)
            self.emit_progress(percent, message)


class BulkDeleteWorker(BulkWorkerBase):
    """Worker do masowego usuwania plików."""

    def __init__(self, files_to_delete: list[FilePair], batch_size: int = 20):
        super().__init__(timeout_seconds=300, batch_size=batch_size)
        self.files_to_delete = files_to_delete
        self.deleted_files = []

    def _validate_inputs(self):
        self._validate_file_list(
            self.files_to_delete, "Lista plików do usunięcia jest pusta"
        )

    def _group_files_by_directory(self) -> dict:
        """Grupuje pliki według katalogów."""
        grouped = defaultdict(list)
        for file_pair in self.files_to_delete:
            if file_pair.archive_path:
                archive_dir = os.path.dirname(file_pair.archive_path)
                grouped[archive_dir].append(("archive", file_pair.archive_path))
            if file_pair.preview_path:
                preview_dir = os.path.dirname(file_pair.preview_path)
                grouped[preview_dir].append(("preview", file_pair.preview_path))
        return grouped

    def _process_batch_implementation(self, batch_data: List[Tuple[str, str]]):
        for file_type, file_path in batch_data:
            if self.check_interruption():
                return

            if self._safe_file_operation(os.remove, file_path):
                self.deleted_files.append((file_type, file_path))
                self.success_count += 1

    def _run_implementation(self):
        try:
            self._validate_inputs()
            total_pairs = len(self.files_to_delete)
            self.emit_progress(0, f"Rozpoczęto usuwanie {total_pairs} par plików...")

            grouped_files = self._group_files_by_directory()
            processed_pairs = 0

            for directory, files_in_dir in grouped_files.items():
                if self.check_interruption():
                    break

                for file_info in files_in_dir:
                    self.add_to_batch(file_info)
                    processed_pairs += 1

                    self._emit_progress_with_throttle(
                        processed_pairs,
                        total_pairs * 2,
                        f"Usuwanie: {len(self.deleted_files)} plików usuniętych...",
                    )

            self.finalize_batches()

            message = f"Usunięto {len(self.deleted_files)} plików."
            if self.error_count > 0:
                message += f" Błędy: {self.error_count}"

            self.emit_progress(100, message)
            self.emit_finished(self.deleted_files)

        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Nieoczekiwany błąd: {str(e)}", e)


class BulkMoveWorker(BulkWorkerBase):
    """Worker do masowego przenoszenia plików."""

    def __init__(
        self, files_to_move: list[FilePair], destination_dir: str, batch_size: int = 50
    ):
        super().__init__(timeout_seconds=600, batch_size=batch_size)
        self.files_to_move = files_to_move
        self.destination_dir = destination_dir
        self.moved_files = []
        self.updated_file_pairs = []
        self.skipped_count = 0
        self.skipped_files = []

    def _validate_inputs(self):
        self._validate_file_list(
            self.files_to_move, "Lista plików do przeniesienia jest pusta"
        )
        self._validate_directory(self.destination_dir, "Katalog docelowy")

    def _group_files_by_source_directory(self) -> dict:
        """Grupuje pliki według katalogów źródłowych."""
        grouped = defaultdict(list)
        for file_pair in self.files_to_move:
            if file_pair.archive_path:
                source_dir = os.path.dirname(file_pair.archive_path)
                grouped[source_dir].append(
                    ("archive", file_pair.archive_path, file_pair)
                )
            if file_pair.preview_path:
                source_dir = os.path.dirname(file_pair.preview_path)
                grouped[source_dir].append(
                    ("preview", file_pair.preview_path, file_pair)
                )
        return grouped

    def _move_file_safe(self, source_path: str, target_path: str) -> bool:
        """Bezpieczne przeniesienie pliku."""
        if os.path.exists(target_path):
            self.skipped_count += 1
            self.skipped_files.append(
                {
                    "file_path": source_path,
                    "target_path": target_path,
                    "reason": "Plik już istnieje",
                }
            )
            return False

        return self._safe_file_operation(shutil.move, source_path, target_path)

    def _process_batch_implementation(
        self, batch_data: List[Tuple[str, str, FilePair]]
    ):
        dest_dir = normalize_path(self.destination_dir)

        for file_type, file_path, file_pair in batch_data:
            if self.check_interruption():
                return

            filename = os.path.basename(file_path)
            target_path = os.path.join(dest_dir, filename)

            if self._move_file_safe(file_path, target_path):
                self.moved_files.append((file_path, target_path))
                self.success_count += 1

                # Aktualizuj ścieżkę w file_pair
                if file_type == "archive":
                    file_pair.archive_path = target_path
                else:
                    file_pair.preview_path = target_path

                if file_pair not in self.updated_file_pairs:
                    self.updated_file_pairs.append(file_pair)

    def _run_implementation(self):
        try:
            self._validate_inputs()
            total_files = len(self.files_to_move) * 2  # archive + preview
            self.emit_progress(
                0, f"Rozpoczęto przenoszenie {len(self.files_to_move)} par plików..."
            )

            grouped_files = self._group_files_by_source_directory()
            processed_files = 0

            for source_directory, files_in_dir in grouped_files.items():
                if self.check_interruption():
                    break

                for file_info in files_in_dir:
                    self.add_to_batch(file_info)
                    processed_files += 1

                    self._emit_progress_with_throttle(
                        processed_files,
                        total_files,
                        f"Przenoszenie: {len(self.moved_files)} plików przeniesiono...",
                    )

            self.finalize_batches()

            result = {
                "moved_pairs": self.updated_file_pairs,
                "detailed_errors": self.detailed_errors,
                "skipped_files": self.skipped_files,
                "summary": {
                    "total_requested": len(self.files_to_move),
                    "successfully_moved": len(self.updated_file_pairs),
                    "errors": self.error_count,
                    "skipped": self.skipped_count,
                },
            }

            self.emit_progress(
                100, f"Przeniesiono {len(self.updated_file_pairs)} par plików"
            )
            self.emit_finished(result)

        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Nieoczekiwany błąd: {str(e)}", e)


class BulkMoveFilesWorker(BulkWorkerBase):
    """Worker do masowego przenoszenia pojedynczych plików (dla drag&drop)."""

    def __init__(
        self, file_paths: List[str], destination_dir: str, batch_size: int = 50
    ):
        super().__init__(timeout_seconds=600, batch_size=batch_size)
        self.file_paths = file_paths
        self.destination_dir = destination_dir
        self.moved_files = []
        self.skipped_count = 0
        self.skipped_files = []

    def _validate_inputs(self):
        self._validate_file_list(
            self.file_paths, "Lista plików do przeniesienia jest pusta"
        )
        self._validate_directory(self.destination_dir, "Katalog docelowy")

    def _process_batch_implementation(self, batch_data: List[str]):
        dest_dir = normalize_path(self.destination_dir)

        for file_path in batch_data:
            if self.check_interruption():
                return

            filename = os.path.basename(file_path)
            target_path = os.path.join(dest_dir, filename)

            if os.path.exists(target_path):
                self.skipped_count += 1
                self.skipped_files.append(
                    {
                        "file_path": file_path,
                        "target_path": target_path,
                        "reason": "Plik już istnieje",
                    }
                )
                continue

            if self._safe_file_operation(shutil.move, file_path, target_path):
                self.moved_files.append((file_path, target_path))
                self.success_count += 1

    def _run_implementation(self):
        try:
            self._validate_inputs()
            total_files = len(self.file_paths)
            self.emit_progress(0, f"Rozpoczęto przenoszenie {total_files} plików...")

            processed_files = 0
            for file_path in self.file_paths:
                if self.check_interruption():
                    break

                self.add_to_batch(file_path)
                processed_files += 1

                self._emit_progress_with_throttle(
                    processed_files,
                    total_files,
                    f"Przenoszenie: {len(self.moved_files)} plików przeniesiono...",
                )

            self.finalize_batches()

            result = {
                "moved_files": self.moved_files,
                "detailed_errors": self.detailed_errors,
                "skipped_files": self.skipped_files,
                "summary": {
                    "total_requested": total_files,
                    "successfully_moved": self.success_count,
                    "errors": self.error_count,
                    "skipped": self.skipped_count,
                },
            }

            self.emit_progress(100, f"Przeniesiono {self.success_count} plików")
            self.emit_finished(result)

        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Nieoczekiwany błąd: {str(e)}", e)


class MoveUnpairedArchivesWorker(BulkWorkerBase):
    """Worker do przenoszenia plików archiwum bez pary."""

    def __init__(
        self, unpaired_archives: List[str], target_folder: str, batch_size: int = 20
    ):
        super().__init__(timeout_seconds=300, batch_size=batch_size)
        self.unpaired_archives = unpaired_archives
        self.target_folder = target_folder
        self.moved_files = []

    def _validate_inputs(self):
        self._validate_file_list(
            self.unpaired_archives, "Lista plików archiwum bez pary jest pusta"
        )
        self._validate_directory(self.target_folder, "Folder docelowy")

    def _get_unique_filename(self, target_path: str) -> str:
        """Generuje unikalną nazwę pliku jeśli już istnieje."""
        if not os.path.exists(target_path):
            return target_path

        base, ext = os.path.splitext(target_path)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        return f"{base}_{counter}{ext}"

    def _process_batch_implementation(self, batch_data: List[str]):
        for archive_path in batch_data:
            if self.check_interruption():
                return

            filename = os.path.basename(archive_path)
            target_path = os.path.join(self.target_folder, filename)

            # Wygeneruj unikalną nazwę jeśli plik już istnieje
            target_path = self._get_unique_filename(target_path)

            if self._safe_file_operation(shutil.move, archive_path, target_path):
                self.moved_files.append((archive_path, target_path))
                self.success_count += 1

    def _run_implementation(self):
        try:
            self._validate_inputs()
            total_files = len(self.unpaired_archives)
            self.emit_progress(
                0, f"Rozpoczęto przenoszenie {total_files} plików archiwum..."
            )

            processed_files = 0
            for archive_path in self.unpaired_archives:
                if self.check_interruption():
                    break

                self.add_to_batch(archive_path)
                processed_files += 1

                self._emit_progress_with_throttle(
                    processed_files,
                    total_files,
                    f"Przenoszenie: {len(self.moved_files)} archiwów przeniesiono...",
                    throttle=10,
                )

            self.finalize_batches()

            result = {
                "moved_files": self.moved_files,
                "detailed_errors": self.detailed_errors,
                "summary": {
                    "total_requested": total_files,
                    "successfully_moved": self.success_count,
                    "errors": self.error_count,
                },
            }

            self.emit_progress(100, f"Przeniesiono {self.success_count} archiwów")
            self.emit_finished(result)

        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Nieoczekiwany błąd: {str(e)}", e)
