"""
FileOpener - otwieranie plików w zewnętrznych programach.
Wydzielone z file_operations.py dla lepszej separacji odpowiedzialności.
"""

import logging
import os

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from src.utils.path_utils import normalize_path


class FileOpener:
    """
    Klasa odpowiedzialna za otwieranie plików w zewnętrznych programach.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def open_archive_externally(self, archive_path: str) -> bool:
        """
        Otwiera plik archiwum w domyślnym programie systemowym.

        Args:
            archive_path: Ścieżka do pliku archiwum

        Returns:
            True jeśli operacja się powiodła
        """
        self.logger.info(f"Żądanie otwarcia archiwum")

        # Normalizacja ścieżki dla spójności
        archive_path_norm = normalize_path(archive_path)

        # Sprawdź czy plik istnieje
        if not os.path.exists(archive_path_norm):
            self.logger.warning(f"Plik archiwum nie istnieje: {archive_path_norm}")
            return False

        try:
            # QDesktopServices.openUrl jest bardziej przenośne niż os.startfile
            # i działa lepiej z różnymi typami ścieżek (np. UNC na Windows).
            url = QUrl.fromLocalFile(archive_path_norm)

            if QDesktopServices.openUrl(url):
                self.logger.info("Pomyślnie zainicjowano otwarcie archiwum")
                return True
            else:
                self.logger.warning(
                    "Nie udało się otworzyć archiwum (QDesktopServices)"
                )

                # Próba z os.startfile jako fallback dla Windows
                if self._try_windows_fallback(archive_path_norm):
                    return True

                return False

        except Exception as e:
            self.logger.error(f"Nieoczekiwany błąd podczas otwarcia archiwum: {e}")
            return False

    def _try_windows_fallback(self, file_path: str) -> bool:
        """
        Próbuje otworzyć plik używając os.startfile na Windows.

        Args:
            file_path: Ścieżka do pliku

        Returns:
            True jeśli operacja się powiodła
        """
        if os.name != "nt":
            return False

        try:
            os.startfile(file_path)
            self.logger.info("Pomyślnie zainicjowano otwarcie (os.startfile)")
            return True
        except Exception as e:
            self.logger.error(f"Nie udało się otworzyć (os.startfile): {e}")
            return False

    def open_file_externally(self, file_path: str) -> bool:
        """
        Otwiera dowolny plik w domyślnym programie systemowym.

        Args:
            file_path: Ścieżka do pliku

        Returns:
            True jeśli operacja się powiodła
        """
        self.logger.info("Żądanie otwarcia pliku")

        # Normalizacja ścieżki
        file_path_norm = normalize_path(file_path)

        # Sprawdź czy plik istnieje
        if not os.path.exists(file_path_norm):
            self.logger.warning(f"Plik nie istnieje: {file_path_norm}")
            return False

        try:
            url = QUrl.fromLocalFile(file_path_norm)

            if QDesktopServices.openUrl(url):
                self.logger.info("Pomyślnie zainicjowano otwarcie pliku")
                return True
            else:
                self.logger.warning("Nie udało się otworzyć pliku (QDesktopServices)")

                # Próba z fallback
                if self._try_windows_fallback(file_path_norm):
                    return True

                return False

        except Exception as e:
            self.logger.error(f"Nieoczekiwany błąd podczas otwarcia pliku: {e}")
            return False

    def open_folder_externally(self, folder_path: str) -> bool:
        """
        Otwiera folder w eksploratorze plików.

        Args:
            folder_path: Ścieżka do folderu

        Returns:
            True jeśli operacja się powiodła
        """
        self.logger.info("Żądanie otwarcia folderu")

        # Normalizacja ścieżki
        folder_path_norm = normalize_path(folder_path)

        # Sprawdź czy folder istnieje
        if not os.path.isdir(folder_path_norm):
            self.logger.warning(f"Folder nie istnieje: {folder_path_norm}")
            return False

        try:
            url = QUrl.fromLocalFile(folder_path_norm)

            if QDesktopServices.openUrl(url):
                self.logger.info("Pomyślnie zainicjowano otwarcie folderu")
                return True
            else:
                self.logger.warning("Nie udało się otworzyć folderu (QDesktopServices)")

                # Próba z fallback
                if self._try_windows_folder_fallback(folder_path_norm):
                    return True

                return False

        except Exception as e:
            self.logger.error(f"Nieoczekiwany błąd podczas otwarcia folderu: {e}")
            return False

    def _try_windows_folder_fallback(self, folder_path: str) -> bool:
        """
        Próbuje otworzyć folder używając explorer.exe na Windows.

        Args:
            folder_path: Ścieżka do folderu

        Returns:
            True jeśli operacja się powiodła
        """
        if os.name != "nt":
            return False

        try:
            os.startfile(folder_path)
            self.logger.info("Pomyślnie zainicjowano otwarcie folderu (explorer)")
            return True
        except Exception as e:
            self.logger.error(f"Nie udało się otworzyć folderu (explorer): {e}")
            return False
