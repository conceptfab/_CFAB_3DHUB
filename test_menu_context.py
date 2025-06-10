#!/usr/bin/env python3
"""
Test menu kontekstowego i ścieżek przekazywanych do funkcji eksploratora
"""

import logging
import os
import sys

# Dodaj ścieżki do modułów
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication, QTreeView, QWidget

from src.ui.directory_tree_manager import DirectoryTreeManager

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class TestParentWindow(QWidget):
    """Okno testowe z current_working_directory."""

    def __init__(self):
        super().__init__()
        self.current_working_directory = r"C:\_cloud\___TEST_FOLDER"


def test_context_menu_paths():
    """Test ścieżek w menu kontekstowym."""

    # Utwórz aplikację Qt
    app = QApplication([])

    # Utwórz tree view i manager
    tree_view = QTreeView()
    parent_window = TestParentWindow()

    # Utwórz DirectoryTreeManager
    manager = DirectoryTreeManager(tree_view, parent_window)

    # Ustaw testowy folder roboczy
    test_folder = r"C:\_cloud\___TEST_FOLDER"
    if os.path.exists(test_folder):
        print(f"📁 Inicjalizuję drzewo dla: {test_folder}")
        manager.init_directory_tree(test_folder)

        # Symuluj kliknięcie prawym przyciskiem myszy
        print("🖱️ Symulacja menu kontekstowego...")

        # Utwórz funkcję przechwytującą wywołania eksploratora
        original_open_folder = manager.open_folder_in_explorer
        captured_paths = []

        def capture_explorer_call(folder_path):
            captured_paths.append(folder_path)
            print(f"🗂️ PRZECHWYCONO WYWOŁANIE EKSPLORATORA: '{folder_path}'")
            # Nie wywołuj oryginalnej funkcji żeby nie otwierać explorera
            return

        manager.open_folder_in_explorer = capture_explorer_call

        # Symuluj menu kontekstowe na pozycji (10, 10)
        position = QPoint(10, 10)

        try:
            manager.show_folder_context_menu(position)
            print("✅ Menu kontekstowe zostało wyświetlone")

            if captured_paths:
                print(f"✅ Przechwycono {len(captured_paths)} wywołań eksploratora:")
                for i, path in enumerate(captured_paths, 1):
                    print(f"   {i}. '{path}'")
            else:
                print("⚠️ Nie przechwycono żadnych wywołań eksploratora")

        except Exception as e:
            print(f"❌ Błąd podczas wyświetlania menu: {e}")
            import traceback

            traceback.print_exc()
    else:
        print(f"❌ Folder testowy nie istnieje: {test_folder}")
        print("📁 Sprawdzenie dostępnych folderów:")
        test_base = r"C:\_cloud"
        if os.path.exists(test_base):
            for item in os.listdir(test_base):
                item_path = os.path.join(test_base, item)
                if os.path.isdir(item_path):
                    print(f"   📂 {item}")

    print("🔚 Test zakończony")


if __name__ == "__main__":
    test_context_menu_paths()
