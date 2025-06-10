#!/usr/bin/env python3
"""
Test bezpośredniego wywołania funkcji eksploratora na znanych ścieżkach
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from PyQt6.QtWidgets import QApplication, QTreeView, QWidget

from src.ui.directory_tree_manager import DirectoryTreeManager


class TestParentWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.current_working_directory = r"C:\_cloud\___TEST_FOLDER"


def test_explorer_on_known_paths():
    """Test funkcji eksploratora na znanych ścieżkach."""

    app = QApplication([])
    tree_view = QTreeView()
    parent_window = TestParentWindow()
    manager = DirectoryTreeManager(tree_view, parent_window)

    # Test różnych folderów
    test_paths = [
        r"C:\_cloud\___TEST_FOLDER\test",
        r"C:\_cloud\___TEST_FOLDER\Vehicle",
        r"C:\_cloud\___TEST_FOLDER\_test",
        r"C:\_cloud\___TEST_FOLDER",  # Folder nadrzędny
        r"C:\_cloud",  # Jeszcze wyżej
    ]

    print("🗂️ Test funkcji 'Otwórz w eksploratorze' na różnych ścieżkach:")
    print("=" * 60)

    for i, path in enumerate(test_paths, 1):
        print(f"\n{i}. Test ścieżki: '{path}'")

        # Sprawdź czy ścieżka istnieje
        if os.path.exists(path):
            if os.path.isdir(path):
                print(f"   ✅ Ścieżka istnieje i jest folderem")

                # Sprawdź czy to Documents
                if "Documents" in path or "Dokumenty" in path:
                    print(f"   ⚠️ UWAGA: To jest folder Dokumenty/Documents!")
                else:
                    print(f"   ✅ To nie jest folder Dokumenty")

                # Wywołaj funkcję eksploratora
                try:
                    print(f"   🚀 Wywołuję open_folder_in_explorer...")
                    manager.open_folder_in_explorer(path)
                    print(f"   ✅ Funkcja wykonana bez błędu")

                except Exception as e:
                    print(f"   ❌ Błąd: {e}")

            else:
                print(f"   ❌ Ścieżka istnieje ale nie jest folderem")
        else:
            print(f"   ❌ Ścieżka nie istnieje")

    print("\n" + "=" * 60)
    print("🔚 Test zakończony")
    print("\nINSTRUKCJA:")
    print("1. Sprawdź które okna Eksploratora się otworzyły")
    print("2. Czy wszystkie wskazują na prawidłowe foldery?")
    print("3. Czy któryś wskazuje na folder Dokumenty?")


if __name__ == "__main__":
    test_explorer_on_known_paths()
