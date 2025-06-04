"""
Operacje na plikach, takie jak otwieranie zewnętrznym programem, usuwanie, zmiana nazwy, itp.
"""

import logging
import os
import platform

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices


def open_archive_externally(archive_path):
    """
    Otwiera plik archiwum w domyślnym programie systemu operacyjnego.

    Używa os.startfile na Windows lub QDesktopServices.openUrl na innych platformach
    do otwarcia pliku w domyślnym programie skojarzonym z danym typem pliku.

    Args:
        archive_path (str): Ścieżka do pliku archiwum.

    Returns:
        bool: True jeśli operacja się powiodła, False w przypadku błędu.
    """
    if not os.path.exists(archive_path):
        logging.error(f"Plik nie istnieje: {archive_path}")
        return False

    try:
        # Dla Windowsa używamy os.startfile, który jest prostszy i bardziej niezawodny
        if platform.system() == "Windows":
            os.startfile(archive_path)
        # Dla innych platform używamy Qt
        else:
            success = QDesktopServices.openUrl(QUrl.fromLocalFile(archive_path))
            if not success:
                logging.error(f"Nie udało się otworzyć pliku: {archive_path}")
                return False

        logging.info(f"Otwarto plik: {archive_path}")
        return True

    except Exception as e:
        logging.error(f"Błąd podczas otwierania pliku {archive_path}: {e}")
        return False
