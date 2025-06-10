#!/usr/bin/env python3
"""
Test funkcji open_folder_in_explorer z DirectoryTreeManager
"""

import logging
import os
import sys
import tempfile

# Dodaj ścieżki do modułów
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from PyQt6.QtWidgets import QApplication, QTreeView, QWidget

from src.ui.directory_tree_manager import DirectoryTreeManager

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class DummyParentWindow(QWidget):
    """Fałszywe okno nadrzędne do testów."""

    pass


def test_explorer_function():
    """Test funkcji open_folder_in_explorer."""

    # Utwórz aplikację Qt
    app = QApplication([])

    # Utwórz tymczasowy folder do testów
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Test folder: {temp_dir}")

        # Utwórz tree view i manager
        tree_view = QTreeView()
        parent_window = DummyParentWindow()

        # Utwórz DirectoryTreeManager
        manager = DirectoryTreeManager(tree_view, parent_window)

        print("🔍 Testowanie funkcji open_folder_in_explorer...")

        # Test 1: Prawidłowy folder
        print(f"Test 1: Otwieranie prawidłowego folderu: {temp_dir}")
        manager.open_folder_in_explorer(temp_dir)

        # Test 2: Nieistniejący folder
        print("Test 2: Otwieranie nieistniejącego folderu")
        fake_path = os.path.join(temp_dir, "nieistniejacy_folder")
        manager.open_folder_in_explorer(fake_path)

        # Test 3: Ścieżka do pliku (nie folder)
        print("Test 3: Otwieranie ścieżki do pliku")
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test")
        manager.open_folder_in_explorer(test_file)

        print("✅ Test zakończony - sprawdź logi powyżej")


if __name__ == "__main__":
    test_explorer_function()
