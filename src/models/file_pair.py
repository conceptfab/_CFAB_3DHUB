"""
Moduł zawierający definicję klasy FilePair reprezentującej parę plików:
plik archiwum i plik podglądu
"""

import logging
import os


class FilePair:
    """
    Klasa reprezentująca parę plików: archiwum i podgląd.

    W początkowej wersji przechowuje tylko ścieżki do plików.
    W przyszłych wersjach zostanie rozbudowana o dodatkowe funkcje
    i atrybuty jak miniatura, rozmiar pliku, tag "ulubione", itp.
    """

    def __init__(self, archive_path, preview_path):
        """
        Inicjalizuje obiekt FilePair z podanymi ścieżkami.

        Args:
            archive_path (str): Ścieżka do pliku archiwum
            preview_path (str): Ścieżka do pliku podglądu
        """
        self.archive_path = archive_path
        self.preview_path = preview_path
        logging.debug(f"Utworzono nowy obiekt FilePair: {self.get_base_name()}")

    def get_base_name(self):
        """
        Zwraca podstawową nazwę pliku (bez rozszerzenia).

        Returns:
            str: Nazwa pliku bez rozszerzenia
        """
        # Pobierz nazwę pliku z archiwum bez rozszerzenia
        return os.path.splitext(os.path.basename(self.archive_path))[0]

    def get_archive_path(self):
        """
        Zwraca ścieżkę do pliku archiwum.

        Returns:
            str: Ścieżka do pliku archiwum
        """
        return self.archive_path

    def get_preview_path(self):
        """
        Zwraca ścieżkę do pliku podglądu.

        Returns:
            str: Ścieżka do pliku podglądu
        """
        return self.preview_path
