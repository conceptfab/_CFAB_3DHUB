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


class BulkDeleteWorker(UnifiedBaseWorker, BatchOperationMixin):
    """
    Worker do masowego usuwania plików z optymalizacją batch operations.
    """

    def __init__(self, files_to_delete: list[FilePair], batch_size: int = 20):
        """
        Inicjalizuje worker do masowego usuwania plików.

        Args:
            files_to_delete: Lista par plików do usunięcia
            batch_size: Rozmiar batch'a dla operacji grupowych
        """
        UnifiedBaseWorker.__init__(
            self, timeout_seconds=300, priority=WorkerPriority.NORMAL
        )
        BatchOperationMixin.__init__(self, batch_size)
        self.files_to_delete = files_to_delete
        self.deleted_files = []  # Lista pomyślnie usuniętych plików
        self.error_count = 0
        self.success_count = 0

    def _validate_inputs(self):
        """Waliduje parametry wejściowe."""
        if not self.files_to_delete:
            raise ValueError("Lista plików do usunięcia jest pusta")

    def _group_files_by_directory(self) -> dict:
        """Grupuje pliki według katalogów dla optymalizacji I/O."""
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
        """Przetwarza batch operacji usuwania."""
        for file_type, file_path in batch_data:
            if self.check_interruption():
                return

            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.deleted_files.append((file_type, file_path))
                    self.success_count += 1
                    logger.debug(f"Usunięto {file_type}: {os.path.basename(file_path)}")
            except Exception as e:
                self.error_count += 1
                logger.error(
                    f"Błąd podczas usuwania pliku {file_path}: {str(e)}", exc_info=True
                )

    def _run_implementation(self):
        """Wykonuje operację masowego usuwania plików z batch processing."""
        try:
            self._validate_inputs()

            total_pairs = len(self.files_to_delete)
            self.emit_progress(0, f"Rozpoczęto usuwanie {total_pairs} par plików...")

            # Grupuj pliki według katalogów dla lepszej wydajności I/O
            grouped_files = self._group_files_by_directory()

            processed_pairs = 0

            # Przetwarzaj każdy katalog osobno
            for directory, files_in_dir in grouped_files.items():
                if self.check_interruption():
                    break

                logger.debug(
                    f"Przetwarzanie katalogu: {directory} ({len(files_in_dir)} plików)"
                )

                # Dodaj pliki do batch'a
                for file_info in files_in_dir:
                    self.add_to_batch(file_info)
                    processed_pairs += 1

                    # Emituj progress co 5% lub co 10 plików
                    if (
                        processed_pairs % max(1, total_pairs // 20) == 0
                        or processed_pairs % 10 == 0
                    ):
                        percent = int(
                            (processed_pairs / (total_pairs * 2)) * 100
                        )  # *2 bo archive + preview
                        self.emit_progress(
                            percent,
                            f"Usuwanie: {self.success_count} plików usuniętych...",
                        )

            # Przetworz pozostałe pliki w batch'u
            self.finalize_batches()

            # Podsumowanie operacji
            message = f"Usunięto {self.success_count} plików."
            if self.error_count > 0:
                message += f" Wystąpiły błędy przy {self.error_count} plikach."

            self.emit_progress(100, message)
            self.emit_finished(self.deleted_files)

        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Nieoczekiwany błąd: {str(e)}", e)


class BulkMoveWorker(UnifiedBaseWorker, BatchOperationMixin):
    """
    Worker do masowego przenoszenia plików z optymalizacją batch operations.
    """

    def __init__(
        self, files_to_move: list[FilePair], destination_dir: str, batch_size: int = 15
    ):
        """
        Inicjalizuje worker do masowego przenoszenia plików.

        Args:
            files_to_move: Lista par plików do przeniesienia
            destination_dir: Katalog docelowy
            batch_size: Rozmiar batch'a dla operacji grupowych
        """
        UnifiedBaseWorker.__init__(
            self, timeout_seconds=600, priority=WorkerPriority.NORMAL
        )
        BatchOperationMixin.__init__(self, batch_size)
        self.files_to_move = files_to_move
        self.destination_dir = destination_dir
        self.moved_files = []  # Lista pomyślnie przeniesionych plików
        self.updated_file_pairs = []  # Lista zaktualizowanych par plików
        self.error_count = 0
        self.success_count = 0
        self.skipped_count = 0

    def _validate_inputs(self):
        """Waliduje parametry wejściowe."""
        if not self.files_to_move:
            raise ValueError("Lista plików do przeniesienia jest pusta")
        if not self.destination_dir:
            raise ValueError("Katalog docelowy nie może być pusty")
        if not os.path.isdir(self.destination_dir):
            raise ValueError(f"Katalog docelowy nie istnieje: {self.destination_dir}")

    def _group_files_by_source_directory(self) -> dict:
        """Grupuje pliki według katalogów źródłowych dla optymalizacji I/O."""
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

    def _process_batch_implementation(
        self, batch_data: List[Tuple[str, str, FilePair]]
    ):
        """Przetwarza batch operacji przenoszenia."""
        dest_dir = normalize_path(self.destination_dir)

        for file_type, file_path, file_pair in batch_data:
            if self.check_interruption():
                return

            try:
                if not os.path.exists(file_path):
                    continue

                filename = os.path.basename(file_path)
                target_path = os.path.join(dest_dir, filename)

                # Sprawdź czy plik już istnieje w katalogu docelowym
                if os.path.exists(target_path):
                    logger.warning(
                        f"Plik {filename} już istnieje w katalogu docelowym. Pomijanie."
                    )
                    self.skipped_count += 1
                    continue

                # Wykonaj przeniesienie
                shutil.move(file_path, target_path)
                self.moved_files.append((file_type, file_path, target_path))
                self.success_count += 1

                # Aktualizuj FilePair jeśli to archive lub preview
                self._update_file_pair_path(file_pair, file_type, target_path)

                logger.debug(f"Przeniesiono {file_type}: {filename}")

            except Exception as e:
                self.error_count += 1
                logger.error(
                    f"Błąd podczas przenoszenia pliku {file_path}: {str(e)}",
                    exc_info=True,
                )

    def _update_file_pair_path(
        self, file_pair: FilePair, file_type: str, new_path: str
    ):
        """Aktualizuje ścieżkę w FilePair po przeniesieniu."""
        # Sprawdź czy już mamy zaktualizowaną parę dla tego file_pair
        existing_pair = None
        for updated_pair in self.updated_file_pairs:
            if (
                updated_pair.archive_path == file_pair.archive_path
                or updated_pair.preview_path == file_pair.preview_path
            ):
                existing_pair = updated_pair
                break

        if existing_pair:
            # Aktualizuj istniejącą parę
            if file_type == "archive":
                existing_pair.archive_path = new_path
            elif file_type == "preview":
                existing_pair.preview_path = new_path
        else:
            # Utwórz nową zaktualizowaną parę
            working_directory = file_pair.working_directory
            new_archive_path = (
                new_path if file_type == "archive" else file_pair.archive_path
            )
            new_preview_path = (
                new_path if file_type == "preview" else file_pair.preview_path
            )

            updated_pair = FilePair(
                new_archive_path, new_preview_path, working_directory
            )
            self.updated_file_pairs.append(updated_pair)

    def _run_implementation(self):
        """Wykonuje operację masowego przenoszenia plików z batch processing."""
        try:
            self._validate_inputs()

            total_pairs = len(self.files_to_move)
            self.emit_progress(
                0, f"Rozpoczęto przenoszenie {total_pairs} par plików..."
            )

            # Grupuj pliki według katalogów źródłowych dla lepszej wydajności I/O
            grouped_files = self._group_files_by_source_directory()

            processed_files = 0
            total_files = sum(len(files) for files in grouped_files.values())

            # Przetwarzaj każdy katalog źródłowy osobno
            for source_directory, files_in_dir in grouped_files.items():
                if self.check_interruption():
                    break

                logger.debug(
                    f"Przetwarzanie katalogu: {source_directory} ({len(files_in_dir)} plików)"
                )

                # Dodaj pliki do batch'a
                for file_info in files_in_dir:
                    self.add_to_batch(file_info)
                    processed_files += 1

                    # Emituj progress co 5% lub co 10 plików
                    if (
                        processed_files % max(1, total_files // 20) == 0
                        or processed_files % 10 == 0
                    ):
                        percent = int((processed_files / total_files) * 100)
                        self.emit_progress(
                            percent,
                            f"Przenoszenie: {self.success_count} plików przeniesiono...",
                        )

            # Przetworz pozostałe pliki w batch'u
            self.finalize_batches()

            # Podsumowanie operacji
            message = f"Przeniesiono {self.success_count} plików."
            if self.skipped_count > 0:
                message += f" Pominięto {self.skipped_count} plików (już istniejących)."
            if self.error_count > 0:
                message += f" Wystąpiły błędy przy {self.error_count} plikach."

            self.emit_progress(100, message)
            self.emit_finished(self.updated_file_pairs)

        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Nieoczekiwany błąd: {str(e)}", e)
