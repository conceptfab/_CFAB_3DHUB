#!/usr/bin/env python3
"""
Test modelu drzewa folderów i proxy modelu
"""

import logging
import os
import sys
import time

# Dodaj ścieżki do modułów
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from PyQt6.QtCore import QPoint, QTimer
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


def wait_for_model_load(manager, timeout=5):
    """Czeka aż model się załaduje."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if manager.model.rowCount() > 0:
            return True
        time.sleep(0.1)
        QApplication.processEvents()
    return False


def test_model_and_proxy():
    """Test modelu i proxy drzewa folderów."""

    # Utwórz aplikację Qt
    app = QApplication([])

    # Utwórz tree view i manager
    tree_view = QTreeView()
    parent_window = TestParentWindow()

    # Utwórz DirectoryTreeManager
    manager = DirectoryTreeManager(tree_view, parent_window)

    # Ustaw testowy folder roboczy
    test_folder = r"C:\_cloud\___TEST_FOLDER"
    if not os.path.exists(test_folder):
        # Sprawdź czy istnieją inne foldery testowe
        test_base = r"C:\_cloud"
        if os.path.exists(test_base):
            for item in os.listdir(test_base):
                item_path = os.path.join(test_base, item)
                if os.path.isdir(item_path) and not item.startswith("."):
                    test_folder = item_path
                    break

    if os.path.exists(test_folder):
        print(f"📁 Inicjalizuję drzewo dla: {test_folder}")
        manager.init_directory_tree(test_folder)

        # Czekaj na załadowanie modelu
        print("⏳ Czekam na załadowanie modelu...")
        if wait_for_model_load(manager):
            print("✅ Model załadowany!")

            # Sprawdź stan modelu
            print(f"📊 Model rows: {manager.model.rowCount()}")
            print(f"📊 Proxy rows: {manager.proxy_model.rowCount()}")
            print(f"📊 Root path: {manager.model.rootPath()}")

            # Sprawdź pierwszy element
            if manager.proxy_model.rowCount() > 0:
                first_index = manager.proxy_model.index(0, 0)
                if first_index.isValid():
                    # Mapuj na source
                    source_index = manager.proxy_model.mapToSource(first_index)
                    if source_index.isValid():
                        folder_path = manager.model.filePath(source_index)
                        folder_name = manager.model.fileName(source_index)
                        print(
                            f"✅ Pierwszy element: '{folder_name}' -> '{folder_path}'"
                        )

                        # Test menu kontekstowego na pierwszym elemencie
                        print("🖱️ Test menu kontekstowego na pierwszym elemencie...")

                        # Ustaw indeks jako current
                        tree_view.setCurrentIndex(first_index)

                        # Pobierz pozycję pierwszego elementu
                        rect = tree_view.visualRect(first_index)
                        if not rect.isEmpty():
                            center_point = rect.center()
                            print(f"📍 Pozycja pierwszego elementu: {center_point}")

                            # Przechwytuj wywołania eksploratora
                            captured_paths = []
                            original_open_folder = manager.open_folder_in_explorer

                            def capture_explorer_call(folder_path):
                                captured_paths.append(folder_path)
                                print(f"🗂️ PRZECHWYCONO WYWOŁANIE: '{folder_path}'")
                                return

                            manager.open_folder_in_explorer = capture_explorer_call

                            # Wywołaj menu kontekstowe
                            try:
                                manager.show_folder_context_menu(center_point)

                                if captured_paths:
                                    print(f"✅ Sukces! Przechwycono ścieżki:")
                                    for path in captured_paths:
                                        print(f"   📂 '{path}'")

                                        # Sprawdź czy to jest prawidłowa ścieżka
                                        if os.path.exists(path):
                                            print(f"   ✅ Ścieżka istnieje")
                                        else:
                                            print(f"   ❌ Ścieżka nie istnieje!")

                                        # Sprawdź czy to Documents
                                        if "Documents" in path:
                                            print(
                                                f"   ⚠️ UWAGA: Ścieżka zawiera 'Documents' - to może być źródło problemu!"
                                            )
                                else:
                                    print("⚠️ Nie przechwycono żadnych wywołań")

                            except Exception as e:
                                print(f"❌ Błąd menu kontekstowego: {e}")
                                import traceback

                                traceback.print_exc()
                        else:
                            print("❌ Nie można uzyskać pozycji pierwszego elementu")
                    else:
                        print("❌ Nie można zmapować na source index")
                else:
                    print("❌ Pierwszy proxy index jest nieprawidłowy")
            else:
                print("❌ Proxy model jest pusty")
        else:
            print("❌ Model nie załadował się w czasie")
    else:
        print(f"❌ Folder testowy nie istnieje: {test_folder}")

    print("🔚 Test zakończony")


if __name__ == "__main__":
    test_model_and_proxy()
