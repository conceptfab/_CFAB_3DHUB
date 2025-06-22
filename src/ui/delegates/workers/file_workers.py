"""
Workery do operacji na parach plików (łączenie, zmiana nazwy, przenoszenie, usuwanie).
"""

import logging
import os
import shutil

from src.logic.metadata_manager import MetadataManager
from src.models.file_pair import FilePair
from src.utils.path_utils import normalize_path

from .base_workers import TransactionalWorker, UnifiedBaseWorker

logger = logging.getLogger(__name__)


class ManuallyPairFilesWorker(UnifiedBaseWorker):
    """
    Worker do ręcznego parowania plików archive i preview.
    """

    def __init__(self, archive_path: str, preview_path: str, working_directory: str):
        """
        Inicjalizuje worker do manualnego parowania plików.

        Args:
            archive_path: Ścieżka do pliku archiwum
            preview_path: Ścieżka do pliku podglądu
            working_directory: Katalog roboczy aplikacji
        """
        super().__init__()
        self.archive_path = archive_path
        self.preview_path = preview_path
        self.working_directory = working_directory
        self.updated_preview_path = None

    def _validate_inputs(self):
        """Walidacja parametrów wejściowych."""
        # Weryfikacja, czy ścieżki nie są puste
        if not self.archive_path or not self.preview_path:
            raise ValueError("Ścieżka archiwum lub podglądu nie może być pusta")

        # Weryfikacja, czy pliki istnieją
        if not os.path.isfile(self.archive_path):
            raise ValueError(f"Plik archiwum nie istnieje: {self.archive_path}")
        if not os.path.isfile(self.preview_path):
            raise ValueError(f"Plik podglądu nie istnieje: {self.preview_path}")

        # Weryfikacja, czy katalog roboczy istnieje
        if not os.path.isdir(self.working_directory):
            raise ValueError(f"Katalog roboczy nie istnieje: {self.working_directory}")

    def run(self):
        """Wykonuje operację ręcznego parowania plików."""
        try:
            self._validate_inputs()

            # Normalizacja ścieżek
            archive_path = normalize_path(self.archive_path)
            preview_path = normalize_path(self.preview_path)
            working_dir = normalize_path(self.working_directory)

            # Sprawdzenie czy pliki są w tym samym katalogu
            archive_dir = os.path.dirname(archive_path)
            preview_dir = os.path.dirname(preview_path)

            # Pobierz nazwy plików
            archive_filename = os.path.basename(archive_path)
            preview_filename = os.path.basename(preview_path)

            # Pobierz nazwę bazową archiwum (bez rozszerzenia)
            archive_base_name = os.path.splitext(archive_filename)[0]
            preview_base_name = os.path.splitext(preview_filename)[0]

            # Sprawdź czy pliki już mają tę samą nazwę bazową
            was_renamed = False
            current_preview_path = preview_path

            # Jeśli nazwy bazowe są różne a pliki znajdują się w tym samym katalogu,
            # zmień nazwę pliku podglądu, by pasowała do pliku archiwum
            if archive_base_name != preview_base_name and archive_dir == preview_dir:
                self.emit_progress(
                    20,
                    f"Zmiana nazwy pliku podglądu z {preview_filename} na {archive_base_name}{os.path.splitext(preview_filename)[1]}",
                )

                # Określ nową ścieżkę pliku podglądu
                new_preview_filename = (
                    f"{archive_base_name}{os.path.splitext(preview_filename)[1]}"
                )
                new_preview_path = os.path.join(preview_dir, new_preview_filename)

                # Sprawdź czy plik o takiej nazwie już istnieje
                if os.path.exists(new_preview_path):
                    self.emit_error(
                        f"Nie można zmienić nazwy - plik {new_preview_filename} już istnieje w katalogu."
                    )
                    return

                # Zmień nazwę pliku podglądu
                try:
                    os.rename(preview_path, new_preview_path)
                    current_preview_path = new_preview_path
                    was_renamed = True
                    preview_base_name = archive_base_name  # Aktualizacja nazwy bazowej
                except Exception as e:
                    self.emit_error(f"Błąd podczas zmiany nazwy pliku: {str(e)}")
                    return

            # Aktualizacja tylko jeśli operacja zmiany nazwy się powiodła
            if was_renamed:
                self.updated_preview_path = current_preview_path
            else:
                self.updated_preview_path = preview_path

            # Stwórz obiekt FilePair
            file_pair = FilePair(archive_path, self.updated_preview_path, working_dir)

            # Zapisz metadane
            self.emit_progress(60, "Przygotowywanie metadanych pary plików...")
            try:
                metadata_manager = MetadataManager.get_instance(working_dir)

                # NAPRAWKA PROGRESYWNOŚĆ: Sprawdź czy to pierwszy plik metadanych
                metadata_path = metadata_manager.get_metadata_path()
                is_first_metadata = not os.path.exists(metadata_path)

                if is_first_metadata:
                    self.emit_progress(70, "Tworzenie nowego pliku metadanych...")
                    # Utwórz katalog .app_metadata jeśli nie istnieje
                    metadata_dir = os.path.dirname(metadata_path)
                    os.makedirs(metadata_dir, exist_ok=True)
                    self.emit_progress(
                        80, "Zapisywanie pierwszej pary do metadanych..."
                    )
                else:
                    self.emit_progress(80, "Aktualizacja istniejących metadanych...")

                # Zapisz metadane pary
                success = metadata_manager.save_file_pair_metadata(
                    file_pair, working_dir
                )

                if not success:
                    self.emit_error("Nie udało się zapisać metadanych pary plików")
                    self._rollback_rename_if_needed(current_preview_path, was_renamed)
                    return

                if is_first_metadata:
                    self.emit_progress(90, "Plik metadanych utworzony pomyślnie!")
                else:
                    self.emit_progress(90, "Metadane zaktualizowane pomyślnie!")

            except Exception as e:
                self.emit_error(f"Błąd podczas zapisywania metadanych: {str(e)}")
                # Jeżeli zmieniono nazwę pliku podglądu, przywróć oryginalną nazwę
                self._rollback_rename_if_needed(current_preview_path, was_renamed)
                return

            # Operacja zakończona sukcesem
            self.emit_progress(100, "Parowanie plików zakończone pomyślnie.")
            self.emit_finished(file_pair)

        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Wystąpił nieoczekiwany błąd: {str(e)}", e)

    def _rollback_rename_if_needed(self, current_preview_path: str, was_renamed: bool):
        """Przywraca oryginalną nazwę pliku podglądu w przypadku błędu."""
        if was_renamed and current_preview_path and self.updated_preview_path:
            try:
                if os.path.exists(self.updated_preview_path):
                    os.rename(self.updated_preview_path, current_preview_path)
                    logger.info(
                        f"Przywrócono oryginalną nazwę pliku podglądu: {current_preview_path}"
                    )
            except Exception as e:
                logger.error(
                    f"Błąd podczas przywracania oryginalnej nazwy pliku: {str(e)}"
                )


class RenameFilePairWorker(TransactionalWorker):
    """
    Worker do zmiany nazwy pary plików.
    """

    def __init__(self, file_pair: FilePair, new_base_name: str, working_directory: str):
        """
        Inicjalizuje worker do zmiany nazwy pary plików.

        Args:
            file_pair: Para plików do zmiany nazwy
            new_base_name: Nowa nazwa bazowa dla pary plików
            working_directory: Katalog roboczy aplikacji
        """
        super().__init__()
        self.file_pair = file_pair
        self.new_base_name = new_base_name
        self.working_directory = working_directory

        # Zmienne pomocnicze do przechowywania nowych ścieżek
        self.new_archive_path = None
        self.new_preview_path = None

    def _validate_inputs(self):
        """Waliduje parametry wejściowe."""
        if not self.file_pair:
            raise ValueError("FilePair nie może być None")
        if not self.new_base_name:
            raise ValueError("Nowa nazwa bazowa nie może być pusta")
        if not self.working_directory or not os.path.isdir(self.working_directory):
            raise ValueError(f"Nieprawidłowy katalog roboczy: {self.working_directory}")

        # Sprawdź czy pliki istnieją
        if not os.path.isfile(self.file_pair.archive_path):
            raise ValueError(
                f"Plik archiwum nie istnieje: {self.file_pair.archive_path}"
            )
        if not os.path.isfile(self.file_pair.preview_path):
            raise ValueError(
                f"Plik podglądu nie istnieje: {self.file_pair.preview_path}"
            )

    def _rename_file(self, source_path, target_path):
        """Zmienia nazwę pliku z obsługą błędów."""
        os.rename(source_path, target_path)
        return target_path  # Zwracany dla rollbacku

    def _rollback_rename(self, result_path, original_path, *args, **kwargs):
        """Cofa operację zmiany nazwy pliku."""
        if os.path.exists(result_path):
            os.rename(result_path, original_path)
            logger.info(f"Przywrócono oryginalną nazwę pliku: {original_path}")

    def run(self):
        """Wykonuje operację zmiany nazwy pary plików."""
        try:
            self._validate_inputs()

            # Normalizacja ścieżek
            archive_path = normalize_path(self.file_pair.archive_path)
            preview_path = normalize_path(self.file_pair.preview_path)
            working_dir = normalize_path(self.working_directory)

            # Wyznaczenie katalogów dla plików
            archive_dir = os.path.dirname(archive_path)
            preview_dir = os.path.dirname(preview_path)

            # Pobranie rozszerzeń plików
            archive_ext = os.path.splitext(archive_path)[1]
            preview_ext = os.path.splitext(preview_path)[1]

            # Utworzenie nowych nazw plików
            new_archive_filename = f"{self.new_base_name}{archive_ext}"
            new_preview_filename = f"{self.new_base_name}{preview_ext}"

            # Utworzenie pełnych ścieżek dla nowych plików
            new_archive_path = os.path.join(archive_dir, new_archive_filename)
            new_preview_path = os.path.join(preview_dir, new_preview_filename)

            # Sprawdź czy nowe pliki nie kolidują z istniejącymi
            if os.path.exists(new_archive_path) and new_archive_path != archive_path:
                self.emit_error(
                    f"Nie można zmienić nazwy - plik {new_archive_filename} już istnieje."
                )
                return

            if os.path.exists(new_preview_path) and new_preview_path != preview_path:
                self.emit_error(
                    f"Nie można zmienić nazwy - plik {new_preview_filename} już istnieje."
                )
                return

            # Zmiana nazwy pliku archiwum
            self.emit_progress(
                30, f"Zmiana nazwy pliku archiwum na {new_archive_filename}..."
            )
            if new_archive_path != archive_path:
                self.new_archive_path = self.execute_with_rollback(
                    self._rename_file,
                    self._rollback_rename,
                    archive_path,
                    new_archive_path,
                )
            else:
                self.new_archive_path = archive_path

            # Zmiana nazwy pliku podglądu
            self.emit_progress(
                60, f"Zmiana nazwy pliku podglądu na {new_preview_filename}..."
            )
            if new_preview_path != preview_path:
                self.new_preview_path = self.execute_with_rollback(
                    self._rename_file,
                    self._rollback_rename,
                    preview_path,
                    new_preview_path,
                )
            else:
                self.new_preview_path = preview_path

            # Utworzenie nowego obiektu FilePair z zaktualizowanymi ścieżkami
            updated_file_pair = FilePair(
                self.new_archive_path, self.new_preview_path, working_dir
            )

            # Zapisanie zaktualizowanych metadanych
            self.emit_progress(80, "Aktualizacja metadanych pary plików...")
            try:
                metadata_manager = MetadataManager.get_instance(working_dir)
                metadata_manager.save_file_pair_metadata(updated_file_pair, working_dir)
            except Exception as e:
                self.emit_error(f"Błąd podczas zapisywania metadanych: {str(e)}", e)
                # Rollback wykonany automatycznie przez TransactionalWorker
                return

            # Operacja zakończona sukcesem
            self.emit_progress(100, "Zmiana nazwy plików zakończona pomyślnie.")
            self.emit_finished(updated_file_pair)

        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Wystąpił nieoczekiwany błąd: {str(e)}", e)


class DeleteFilePairWorker(UnifiedBaseWorker):
    """
    Worker do usuwania pary plików.
    """

    def __init__(self, file_pair: FilePair):
        """
        Inicjalizuje worker do usuwania pary plików.

        Args:
            file_pair: Para plików do usunięcia
        """
        super().__init__()
        self.file_pair = file_pair

    def _validate_inputs(self):
        """Waliduje parametry wejściowe."""
        if not self.file_pair:
            raise ValueError("FilePair nie może być None")

    def run(self):
        """Wykonuje operację usuwania pary plików."""
        try:
            self._validate_inputs()

            # Normalizacja ścieżek
            archive_path = None
            preview_path = None

            if self.file_pair.archive_path:
                archive_path = normalize_path(self.file_pair.archive_path)
            if self.file_pair.preview_path:
                preview_path = normalize_path(self.file_pair.preview_path)

            errors = []
            deleted_files = []

            # Usuwanie pliku archiwum
            if archive_path and os.path.exists(archive_path):
                self.emit_progress(
                    33, f"Usuwanie pliku archiwum {os.path.basename(archive_path)}..."
                )
                try:
                    os.remove(archive_path)
                    deleted_files.append(("archive", archive_path))
                except Exception as e:
                    errors.append(f"Błąd podczas usuwania pliku archiwum: {str(e)}")
                    logger.error(
                        f"Błąd podczas usuwania pliku archiwum: {str(e)}", exc_info=True
                    )

            # Usuwanie pliku podglądu
            if preview_path and os.path.exists(preview_path):
                self.emit_progress(
                    66, f"Usuwanie pliku podglądu {os.path.basename(preview_path)}..."
                )
                try:
                    os.remove(preview_path)
                    deleted_files.append(("preview", preview_path))
                except Exception as e:
                    errors.append(f"Błąd podczas usuwania pliku podglądu: {str(e)}")
                    logger.error(
                        f"Błąd podczas usuwania pliku podglądu: {str(e)}", exc_info=True
                    )

            # Sprawdzenie czy wystąpiły błędy
            if errors:
                error_message = "\n".join(errors)
                self.emit_error(
                    f"Wystąpiły błędy podczas usuwania plików:\n{error_message}"
                )
                return

            # Operacja zakończona sukcesem
            self.emit_progress(100, "Usunięcie plików zakończone pomyślnie.")
            self.emit_finished(deleted_files)

        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Wystąpił nieoczekiwany błąd: {str(e)}", e)


class MoveFilePairWorker(TransactionalWorker):
    """
    Worker do przenoszenia pary plików do nowego katalogu.
    """

    def __init__(self, file_pair: FilePair, new_target_directory: str):
        """
        Inicjalizuje worker do przenoszenia pary plików.

        Args:
            file_pair: Para plików do przeniesienia
            new_target_directory: Katalog docelowy dla plików
        """
        super().__init__()
        self.file_pair = file_pair
        self.new_target_directory = new_target_directory

        # Zmienne pomocnicze do przechowywania nowych ścieżek
        self.new_archive_path = None
        self.new_preview_path = None

    def _validate_inputs(self):
        """Waliduje parametry wejściowe."""
        if not self.file_pair:
            raise ValueError("FilePair nie może być None")
        if not self.new_target_directory:
            raise ValueError("Katalog docelowy nie może być pusty")
        if not os.path.isdir(self.new_target_directory):
            raise ValueError(
                f"Katalog docelowy nie istnieje: {self.new_target_directory}"
            )

        # Sprawdź czy pliki istnieją
        if not self.file_pair.archive_path or not os.path.isfile(
            self.file_pair.archive_path
        ):
            raise ValueError(
                f"Plik archiwum nie istnieje: {self.file_pair.archive_path}"
            )
        if not self.file_pair.preview_path or not os.path.isfile(
            self.file_pair.preview_path
        ):
            raise ValueError(
                f"Plik podglądu nie istnieje: {self.file_pair.preview_path}"
            )

    def _move_file(self, source_path, target_path):
        """Przenosi plik z obsługą błędów."""
        shutil.move(source_path, target_path)
        return target_path  # Zwracany dla rollbacku

    def _rollback_move(self, result_path, original_path, *args, **kwargs):
        """Cofa operację przeniesienia pliku."""
        if os.path.exists(result_path):
            shutil.move(result_path, original_path)
            logger.info(f"Przywrócono plik do oryginalnej lokalizacji: {original_path}")

    def run(self):
        """Wykonuje operację przeniesienia pary plików."""
        try:
            self._validate_inputs()

            # Normalizacja ścieżek
            archive_path = normalize_path(self.file_pair.archive_path)
            preview_path = normalize_path(self.file_pair.preview_path)
            target_dir = normalize_path(self.new_target_directory)

            # Sprawdź czy pliki nie są już w katalogu docelowym
            archive_dir = os.path.dirname(archive_path)
            preview_dir = os.path.dirname(preview_path)

            if archive_dir == target_dir and preview_dir == target_dir:
                self.emit_error("Pliki są już w katalogu docelowym.")
                return

            # Określ nowe ścieżki plików
            archive_filename = os.path.basename(archive_path)
            preview_filename = os.path.basename(preview_path)

            new_archive_path = os.path.join(target_dir, archive_filename)
            new_preview_path = os.path.join(target_dir, preview_filename)

            # Sprawdź czy pliki o takich nazwach już istnieją w katalogu docelowym
            if os.path.exists(new_archive_path):
                self.emit_error(
                    f"Plik {archive_filename} już istnieje w katalogu docelowym."
                )
                return

            if os.path.exists(new_preview_path):
                self.emit_error(
                    f"Plik {preview_filename} już istnieje w katalogu docelowym."
                )
                return

            # Przeniesienie pliku archiwum
            if archive_dir != target_dir:
                self.emit_progress(
                    30,
                    f"Przenoszenie pliku archiwum {archive_filename} do {target_dir}...",
                )
                self.new_archive_path = self.execute_with_rollback(
                    self._move_file, self._rollback_move, archive_path, new_archive_path
                )
            else:
                self.new_archive_path = archive_path

            # Przeniesienie pliku podglądu
            if preview_dir != target_dir:
                self.emit_progress(
                    60,
                    f"Przenoszenie pliku podglądu {preview_filename} do {target_dir}...",
                )
                self.new_preview_path = self.execute_with_rollback(
                    self._move_file, self._rollback_move, preview_path, new_preview_path
                )
            else:
                self.new_preview_path = preview_path

            # Utworzenie nowego obiektu FilePair z zaktualizowanymi ścieżkami
            # Używamy working_directory z oryginalnego file_pair
            working_dir = self.file_pair.working_directory
            updated_file_pair = FilePair(
                self.new_archive_path, self.new_preview_path, working_dir
            )

            # Operacja zakończona sukcesem
            self.emit_progress(100, "Przenoszenie plików zakończone pomyślnie.")
            self.emit_finished(updated_file_pair)

        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Wystąpił nieoczekiwany błąd: {str(e)}", e)
            # Rollback wykonany automatycznie przez TransactionalWorker

    def _rollback(self):
        """Przywraca pliki do oryginalnej lokalizacji."""
        self._rollback_operations()
