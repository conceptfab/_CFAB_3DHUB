"""
Workery do operacji na folderach (tworzenie, usuwanie, zmiana nazwy).
"""

import logging
import os
import shutil

from .base_workers import UnifiedBaseWorker
from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)


class CreateFolderWorker(UnifiedBaseWorker):
    """
    Worker do tworzenia folderu w osobnym wątku.
    """

    def __init__(self, parent_directory: str, folder_name: str):
        super().__init__()
        self.parent_directory = parent_directory
        self.folder_name = folder_name
        self.created_path = None

    def _validate_inputs(self):
        """Waliduje parametry wejściowe."""
        if not self.parent_directory or not os.path.isdir(self.parent_directory):
            raise ValueError(f"Nieprawidłowy katalog nadrzędny: {self.parent_directory}")
        if not self.folder_name:
            raise ValueError("Nazwa folderu nie może być pusta")

    def run(self):
        """Tworzy nowy folder w określonym katalogu."""
        try:
            self._validate_inputs()

            # Normalizacja ścieżek
            parent_dir = normalize_path(self.parent_directory)
            new_folder_path = os.path.join(parent_dir, self.folder_name)

            # Sprawdź czy folder już istnieje
            if os.path.exists(new_folder_path):
                self.emit_error(f"Folder {new_folder_path} już istnieje.")
                return

            # Tworzenie folderu
            self.emit_progress(10, f"Tworzenie folderu {self.folder_name}...")

            try:
                # Pierwszy próbujemy utworzyć tylko jeden katalog
                os.mkdir(new_folder_path)
            except FileNotFoundError:
                # Jeśli nie udało się utworzyć pojedynczego katalogu,
                # próbujemy utworzyć głęboką strukturę
                self.emit_progress(
                    30, f"Tworzenie struktury katalogów dla {self.folder_name}..."
                )
                os.makedirs(new_folder_path, exist_ok=True)

            # Upewnij się, że folder faktycznie został utworzony
            if not os.path.isdir(new_folder_path):
                self.emit_error(f"Nie udało się utworzyć folderu {new_folder_path}")
                return

            self.created_path = new_folder_path
            self.emit_progress(100, f"Folder {self.folder_name} utworzony pomyślnie.")
            self.emit_finished(new_folder_path)

        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Wystąpił błąd: {str(e)}", e)


class RenameFolderWorker(UnifiedBaseWorker):
    """
    Worker do zmiany nazwy folderu w osobnym wątku.
    """

    def __init__(self, folder_path: str, new_folder_name: str):
        super().__init__()
        self.folder_path = folder_path
        self.new_folder_name = new_folder_name
        self.new_full_path = None  # Zostanie ustawione w run()

    def _validate_inputs(self):
        """Waliduje parametry wejściowe."""
        if not self.folder_path or not os.path.isdir(self.folder_path):
            raise ValueError(f"Nieprawidłowa ścieżka folderu: {self.folder_path}")
        if not self.new_folder_name:
            raise ValueError("Nowa nazwa folderu nie może być pusta")

    def run(self):
        """Zmienia nazwę folderu."""
        try:
            self._validate_inputs()

            # Normalizacja ścieżki
            folder_path = normalize_path(self.folder_path)

            # Określenie nowej ścieżki
            parent_dir = os.path.dirname(folder_path)
            self.new_full_path = os.path.join(parent_dir, self.new_folder_name)

            # Sprawdź czy docelowy folder już istnieje
            if os.path.exists(self.new_full_path):
                self.emit_error(
                    f"Nie można zmienić nazwy - folder {self.new_full_path} już istnieje."
                )
                return

            # Zmiana nazwy folderu
            self.emit_progress(
                30, f"Zmiana nazwy folderu {os.path.basename(folder_path)} na {self.new_folder_name}..."
            )

            try:
                os.rename(folder_path, self.new_full_path)
            except PermissionError:
                self.emit_error("Brak uprawnień do zmiany nazwy folderu.")
                return
            except OSError as ose:
                self.emit_error(f"Błąd systemu operacyjnego: {str(ose)}")
                return

            # Sprawdzenie czy operacja się powiodła
            if not os.path.isdir(self.new_full_path):
                self.emit_error("Nie udało się zmienić nazwy folderu.")
                return

            self.emit_progress(100, "Zmiana nazwy folderu zakończona pomyślnie.")
            self.emit_finished(self.new_full_path)

        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Wystąpił nieoczekiwany błąd: {str(e)}", e)


class DeleteFolderWorker(UnifiedBaseWorker):
    """
    Worker do usuwania folderu w osobnym wątku.
    """

    def __init__(self, folder_path: str, delete_content: bool):
        super().__init__()
        self.folder_path = folder_path
        self.delete_content = delete_content
        self.deleted_path = None  # Zostanie ustawione w run()

    def _validate_inputs(self):
        """Waliduje parametry wejściowe."""
        if not self.folder_path:
            raise ValueError("Ścieżka folderu nie może być pusta")
        if not os.path.exists(self.folder_path):
            raise ValueError(f"Folder {self.folder_path} nie istnieje")
        if not os.path.isdir(self.folder_path):
            raise ValueError(f"{self.folder_path} nie jest folderem")

    def run(self):
        """Usuwa folder."""
        try:
            self._validate_inputs()

            # Normalizacja ścieżki
            folder_path = normalize_path(self.folder_path)

            # Zapamiętaj ścieżkę przed usunięciem
            self.deleted_path = folder_path

            # Sprawdź czy folder jest pusty
            is_empty = True
            try:
                is_empty = len(os.listdir(folder_path)) == 0
            except PermissionError:
                self.emit_error("Brak uprawnień do przeglądania zawartości folderu.")
                return

            # Jeśli folder nie jest pusty, a nie można usuwać zawartości
            if not is_empty and not self.delete_content:
                self.emit_error("Folder nie jest pusty. Operacja anulowana.")
                return

            # Właściwe usuwanie folderu
            self.emit_progress(30, f"Usuwanie folderu {os.path.basename(folder_path)}...")

            try:
                if not is_empty and self.delete_content:
                    # Usuwanie folderu z zawartością
                    shutil.rmtree(folder_path)
                else:
                    # Usuwanie pustego folderu
                    os.rmdir(folder_path)
            except PermissionError:
                self.emit_error("Brak uprawnień do usunięcia folderu.")
                return
            except OSError as ose:
                self.emit_error(f"Błąd systemu operacyjnego: {str(ose)}")
                return

            # Sprawdzenie czy operacja się powiodła
            if os.path.exists(folder_path):
                self.emit_error("Nie udało się usunąć folderu.")
                return

            self.emit_progress(100, "Usunięcie folderu zakończone pomyślnie.")
            self.emit_finished(self.deleted_path)

        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Wystąpił nieoczekiwany błąd: {str(e)}", e) 