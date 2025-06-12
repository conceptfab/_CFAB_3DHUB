"""
Workery do operacji masowych (bulk) na wielu plikach jednocześnie.
"""

import logging
import os
import shutil

from .base_workers import UnifiedBaseWorker
from src.models.file_pair import FilePair
from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)


class BulkDeleteWorker(UnifiedBaseWorker):
    """
    Worker do masowego usuwania plików.
    """

    def __init__(self, files_to_delete: list[FilePair]):
        """
        Inicjalizuje worker do masowego usuwania plików.
        
        Args:
            files_to_delete: Lista par plików do usunięcia
        """
        super().__init__()
        self.files_to_delete = files_to_delete
        self.deleted_files = []  # Lista pomyślnie usuniętych plików

    def _validate_inputs(self):
        """Waliduje parametry wejściowe."""
        if not self.files_to_delete:
            raise ValueError("Lista plików do usunięcia jest pusta")

    def run(self):
        """Wykonuje operację masowego usuwania plików."""
        try:
            self._validate_inputs()
            
            total_pairs = len(self.files_to_delete)
            success_count = 0
            error_count = 0
            
            self.emit_progress(0, f"Rozpoczęto usuwanie {total_pairs} par plików...")
            
            for i, file_pair in enumerate(self.files_to_delete):
                if self.check_interruption():
                    break
                
                # Emituj progress co 5% lub co 2 pary plików
                current_percent = int((i / total_pairs) * 100)
                if i % max(1, total_pairs // 20) == 0 or i % 2 == 0:
                    self.emit_progress(
                        current_percent, f"Usuwanie: {i}/{total_pairs} par plików..."
                    )
                
                # Usuwanie pliku archiwum
                if file_pair.archive_path and os.path.exists(file_pair.archive_path):
                    try:
                        os.remove(file_pair.archive_path)
                        self.deleted_files.append(("archive", file_pair.archive_path))
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        logger.error(
                            f"Błąd podczas usuwania pliku {file_pair.archive_path}: {str(e)}",
                            exc_info=True
                        )
                
                # Usuwanie pliku podglądu
                if file_pair.preview_path and os.path.exists(file_pair.preview_path):
                    try:
                        os.remove(file_pair.preview_path)
                        self.deleted_files.append(("preview", file_pair.preview_path))
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        logger.error(
                            f"Błąd podczas usuwania pliku {file_pair.preview_path}: {str(e)}",
                            exc_info=True
                        )
            
            # Podsumowanie operacji
            message = f"Usunięto {success_count} plików."
            if error_count > 0:
                message += f" Wystąpiły błędy przy {error_count} plikach."
            
            self.emit_progress(100, message)
            self.emit_finished(self.deleted_files)
        
        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Nieoczekiwany błąd: {str(e)}", e)


class BulkMoveWorker(UnifiedBaseWorker):
    """
    Worker do masowego przenoszenia plików.
    """

    def __init__(self, files_to_move: list[FilePair], destination_dir: str):
        """
        Inicjalizuje worker do masowego przenoszenia plików.
        
        Args:
            files_to_move: Lista par plików do przeniesienia
            destination_dir: Katalog docelowy
        """
        super().__init__()
        self.files_to_move = files_to_move
        self.destination_dir = destination_dir
        self.moved_files = []  # Lista pomyślnie przeniesionych plików
        self.updated_file_pairs = []  # Lista zaktualizowanych par plików

    def _validate_inputs(self):
        """Waliduje parametry wejściowe."""
        if not self.files_to_move:
            raise ValueError("Lista plików do przeniesienia jest pusta")
        if not self.destination_dir:
            raise ValueError("Katalog docelowy nie może być pusty")
        if not os.path.isdir(self.destination_dir):
            raise ValueError(f"Katalog docelowy nie istnieje: {self.destination_dir}")

    def run(self):
        """Wykonuje operację masowego przenoszenia plików."""
        try:
            self._validate_inputs()
            
            # Normalizacja ścieżki docelowej
            dest_dir = normalize_path(self.destination_dir)
            total_pairs = len(self.files_to_move)
            success_count = 0
            error_count = 0
            skipped_count = 0
            
            self.emit_progress(0, f"Rozpoczęto przenoszenie {total_pairs} par plików...")
            
            for i, file_pair in enumerate(self.files_to_move):
                if self.check_interruption():
                    break
                
                # Emituj progress co 5% lub co 2 pary plików
                current_percent = int((i / total_pairs) * 100)
                if i % max(1, total_pairs // 20) == 0 or i % 2 == 0:
                    self.emit_progress(
                        current_percent, f"Przenoszenie: {i}/{total_pairs} par plików..."
                    )
                
                new_archive_path = None
                new_preview_path = None
                
                # Przenoszenie pliku archiwum
                if file_pair.archive_path and os.path.exists(file_pair.archive_path):
                    archive_filename = os.path.basename(file_pair.archive_path)
                    target_archive_path = os.path.join(dest_dir, archive_filename)
                    
                    # Sprawdź czy plik już istnieje w katalogu docelowym
                    if os.path.exists(target_archive_path):
                        logger.warning(
                            f"Plik {archive_filename} już istnieje w katalogu docelowym. Pomijanie."
                        )
                        skipped_count += 1
                    else:
                        try:
                            shutil.move(file_pair.archive_path, target_archive_path)
                            self.moved_files.append(
                                ("archive", file_pair.archive_path, target_archive_path)
                            )
                            new_archive_path = target_archive_path
                            success_count += 1
                        except Exception as e:
                            error_count += 1
                            logger.error(
                                f"Błąd podczas przenoszenia pliku {file_pair.archive_path}: {str(e)}",
                                exc_info=True
                            )
                
                # Przenoszenie pliku podglądu
                if file_pair.preview_path and os.path.exists(file_pair.preview_path):
                    preview_filename = os.path.basename(file_pair.preview_path)
                    target_preview_path = os.path.join(dest_dir, preview_filename)
                    
                    # Sprawdź czy plik już istnieje w katalogu docelowym
                    if os.path.exists(target_preview_path):
                        logger.warning(
                            f"Plik {preview_filename} już istnieje w katalogu docelowym. Pomijanie."
                        )
                        skipped_count += 1
                    else:
                        try:
                            shutil.move(file_pair.preview_path, target_preview_path)
                            self.moved_files.append(
                                ("preview", file_pair.preview_path, target_preview_path)
                            )
                            new_preview_path = target_preview_path
                            success_count += 1
                        except Exception as e:
                            error_count += 1
                            logger.error(
                                f"Błąd podczas przenoszenia pliku {file_pair.preview_path}: {str(e)}",
                                exc_info=True
                            )
                
                # Aktualizacja obiektu FilePair tylko jeśli oba pliki zostały przeniesione
                if new_archive_path or new_preview_path:
                    updated_pair = FilePair(
                        new_archive_path or file_pair.archive_path,
                        new_preview_path or file_pair.preview_path,
                    )
                    self.updated_file_pairs.append(updated_pair)
            
            # Podsumowanie operacji
            message = f"Przeniesiono {success_count} plików."
            if skipped_count > 0:
                message += f" Pominięto {skipped_count} plików (już istniejących)."
            if error_count > 0:
                message += f" Wystąpiły błędy przy {error_count} plikach."
            
            self.emit_progress(100, message)
            self.emit_finished(self.updated_file_pairs)
        
        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Nieoczekiwany błąd: {str(e)}", e) 