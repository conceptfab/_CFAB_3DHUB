"""
Service odpowiedzialny za operacje na plikach.
Separacja logiki biznesowej od UI zgodnie z Etapem 2 corrections.md
"""

import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

# from src.logic.file_pairing import update_pairs_after_move, remove_deleted_from_pairs  # TODO: Implementować te funkcje
from src.models.file_pair import FilePair
from src.utils.path_validator import PathValidator


class FileOperationsService:
    """Serwis do operacji na plikach - separacja logiki biznesowej od UI."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def move_files(self, files: List[str], destination: str) -> bool:
        """Przenosi pliki do wskazanego katalogu."""
        try:
            for file_path in files:
                if os.path.exists(file_path):
                    shutil.move(file_path, destination)
            return True
        except Exception as e:
            self.logger.error(f"Błąd podczas przenoszenia plików: {e}")
            return False

    def delete_files(self, files: List[str]) -> bool:
        """Usuwa wskazane pliki."""
        try:
            for file_path in files:
                if os.path.exists(file_path):
                    os.remove(file_path)
            return True
        except Exception as e:
            self.logger.error(f"Błąd podczas usuwania plików: {e}")
            return False

    def _move_to_trash(self, file_path: str) -> bool:
        """Przenosi plik do kosza systemu"""
        try:
            # Implementacja zależna od platformy
            import sys

            if sys.platform.startswith("win"):
                # Windows - użyj send2trash jeśli dostępne
                try:
                    import send2trash

                    send2trash.send2trash(file_path)
                    return True
                except ImportError:
                    # Fallback dla Windows bez send2trash
                    self.logger.warning(
                        "send2trash nie jest dostępne, używam zwykłego usuwania"
                    )
                    Path(file_path).unlink()
                    return True
            else:
                # Linux/macOS - przenieś do ~/.local/share/Trash
                trash_dir = Path.home() / ".local" / "share" / "Trash" / "files"
                trash_dir.mkdir(parents=True, exist_ok=True)

                file_name = Path(file_path).name
                trash_path = trash_dir / file_name

                # Jeśli plik już istnieje w koszu, dodaj suffix
                counter = 1
                while trash_path.exists():
                    name_part = Path(file_path).stem
                    ext_part = Path(file_path).suffix
                    trash_path = trash_dir / f"{name_part}_{counter}{ext_part}"
                    counter += 1

                shutil.move(file_path, trash_path)
                return True

        except Exception as e:
            self.logger.error(f"Błąd podczas przenoszenia do kosza {file_path}: {e}")
            return False

    def bulk_delete(
        self, file_pairs: List[FilePair]
    ) -> Tuple[List[FilePair], List[str]]:
        """
        Usuwa masowo pary plików.

        Args:
            file_pairs: Lista par plików do usunięcia

        Returns:
            Tuple[List[FilePair], List[str]]: (pomyślnie usunięte, błędy)
        """
        successfully_deleted = []
        errors = []

        for file_pair in file_pairs:
            try:
                # Usuń archiwum
                if file_pair.archive_path and os.path.exists(file_pair.archive_path):
                    os.remove(file_pair.archive_path)
                    self.logger.info(f"Usunięto archiwum: {file_pair.archive_path}")

                # Usuń podgląd
                if file_pair.preview_path and os.path.exists(file_pair.preview_path):
                    os.remove(file_pair.preview_path)
                    self.logger.info(f"Usunięto podgląd: {file_pair.preview_path}")

                successfully_deleted.append(file_pair)

            except Exception as e:
                error_msg = f"Błąd usuwania {file_pair.name}: {str(e)}"
                self.logger.error(error_msg)
                errors.append(error_msg)

        return successfully_deleted, errors

    def bulk_move(
        self, file_pairs: List[FilePair], destination: str
    ) -> Tuple[List[FilePair], List[str]]:
        """
        Przenosi masowo pary plików do nowego katalogu.

        Args:
            file_pairs: Lista par plików do przeniesienia
            destination: Ścieżka docelowa

        Returns:
            Tuple[List[FilePair], List[str]]: (pomyślnie przeniesione, błędy)
        """
        if not os.path.exists(destination):
            try:
                os.makedirs(destination)
            except Exception as e:
                return [], [f"Nie można utworzyć katalogu docelowego: {str(e)}"]

        successfully_moved = []
        errors = []

        for file_pair in file_pairs:
            try:
                # Przygotuj nowe ścieżki
                new_archive_path = None
                new_preview_path = None

                # Przenieś archiwum
                if file_pair.archive_path and os.path.exists(file_pair.archive_path):
                    archive_name = os.path.basename(file_pair.archive_path)
                    new_archive_path = os.path.join(destination, archive_name)
                    shutil.move(file_pair.archive_path, new_archive_path)
                    self.logger.info(f"Przeniesiono archiwum: {new_archive_path}")

                # Przenieś podgląd
                if file_pair.preview_path and os.path.exists(file_pair.preview_path):
                    preview_name = os.path.basename(file_pair.preview_path)
                    new_preview_path = os.path.join(destination, preview_name)
                    shutil.move(file_pair.preview_path, new_preview_path)
                    self.logger.info(f"Przeniesiono podgląd: {new_preview_path}")

                # Utwórz nową parę z poprawnym working_directory
                new_pair = FilePair(
                    new_archive_path or file_pair.archive_path,
                    new_preview_path or file_pair.preview_path,
                    destination,  # nowy working_directory to destination
                )

                # Kopiuj metadane
                new_pair.stars = file_pair.stars
                new_pair.color_tag = file_pair.color_tag

                successfully_moved.append(new_pair)

            except Exception as e:
                error_msg = f"Błąd przenoszenia {file_pair.name}: {str(e)}"
                self.logger.error(error_msg)
                errors.append(error_msg)

        return successfully_moved, errors

    def manual_pair(self, archive_path: str, preview_path: str) -> Optional[FilePair]:
        """
        Tworzy ręczną parę plików.

        Args:
            archive_path: Ścieżka do archiwum
            preview_path: Ścieżka do podglądu

        Returns:
            Optional[FilePair]: Nowa para lub None w przypadku błędu
        """
        try:
            # Walidacja
            if not os.path.exists(archive_path):
                self.logger.error(f"Archiwum nie istnieje: {archive_path}")
                return None

            if not os.path.exists(preview_path):
                self.logger.error(f"Podgląd nie istnieje: {preview_path}")
                return None

            # Utwórz parę - working_directory to katalog zawierający archiwum
            working_directory = os.path.dirname(archive_path)
            file_pair = FilePair(archive_path, preview_path, working_directory)

            self.logger.info(f"Utworzono ręczną parę: {file_pair.name}")
            return file_pair

        except Exception as e:
            self.logger.error(f"Błąd tworzenia ręcznej pary: {str(e)}")
            return None

    def validate_file_paths(self, *paths: str) -> List[str]:
        """
        Waliduje czy podane ścieżki istnieją.

        Args:
            *paths: Ścieżki do walidacji

        Returns:
            List[str]: Lista błędów walidacji
        """
        errors = []

        for path in paths:
            if not path:
                errors.append("Pusta ścieżka")
                continue

            if not os.path.exists(path):
                errors.append(f"Plik nie istnieje: {path}")
                continue

            if not os.path.isfile(path):
                errors.append(f"Ścieżka nie wskazuje na plik: {path}")

        return errors

    def cleanup_empty_directories(self, base_path: str) -> int:
        """
        Usuwa puste katalogi po operacjach na plikach.

        Args:
            base_path: Ścieżka bazowa do sprawdzenia

        Returns:
            int: Liczba usuniętych katalogów
        """
        removed_count = 0

        try:
            for root, dirs, files in os.walk(base_path, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(dir_path):  # Katalog pusty
                            os.rmdir(dir_path)
                            removed_count += 1
                            self.logger.info(f"Usunięto pusty katalog: {dir_path}")
                    except OSError:
                        # Katalog nie jest pusty lub błąd dostępu
                        pass
        except Exception as e:
            self.logger.error(f"Błąd czyszczenia pustych katalogów: {str(e)}")

        return removed_count
