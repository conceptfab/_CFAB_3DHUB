#!/usr/bin/env python3
"""
Debug ścieżek i indeksów w drzewie folderów
"""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from PyQt6.QtCore import QModelIndex
from PyQt6.QtWidgets import QApplication, QTreeView, QWidget

from src.ui.directory_tree_manager import DirectoryTreeManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class TestParentWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.current_working_directory = r"C:\_cloud\___TEST_FOLDER"


def debug_model_structure():
    """Debug struktury modelu."""

    app = QApplication([])
    tree_view = QTreeView()
    parent_window = TestParentWindow()
    manager = DirectoryTreeManager(tree_view, parent_window)

    test_folder = r"C:\_cloud\___TEST_FOLDER"

    print(f"🔍 Debug dla folderu: {test_folder}")

    # Sprawdź czy folder istnieje
    if not os.path.exists(test_folder):
        # Znajdź istniejący folder testowy
        test_base = r"C:\_cloud"
        if os.path.exists(test_base):
            for item in os.listdir(test_base):
                item_path = os.path.join(test_base, item)
                if os.path.isdir(item_path) and not item.startswith("."):
                    test_folder = item_path
                    print(f"📁 Używam folderu: {test_folder}")
                    parent_window.current_working_directory = test_folder
                    break

    if os.path.exists(test_folder):
        print(f"✅ Folder istnieje: {test_folder}")
        print(f"📂 Zawartość folderu:")
        try:
            items = os.listdir(test_folder)
            for item in items[:5]:  # Pokaż pierwsze 5 elementów
                item_path = os.path.join(test_folder, item)
                if os.path.isdir(item_path):
                    print(f"   📁 {item}")
        except Exception as e:
            print(f"   ❌ Błąd listowania: {e}")

        # Inicjalizuj model
        print(f"\n🔧 Inicjalizacja modelu...")
        manager.init_directory_tree(test_folder)

        # Debug modelu po inicjalizacji
        print(f"\n📊 Stan modelu po inicjalizacji:")
        print(f"   Model root path: '{manager.model.rootPath()}'")
        print(f"   Model row count: {manager.model.rowCount()}")
        print(f"   Proxy row count: {manager.proxy_model.rowCount()}")

        # Sprawdź root index
        root_index = manager.folder_tree.rootIndex()
        print(f"   Tree view root index valid: {root_index.isValid()}")

        if root_index.isValid():
            # Mapuj z proxy na source
            source_root = manager.proxy_model.mapToSource(root_index)
            if source_root.isValid():
                root_path = manager.model.filePath(source_root)
                root_name = manager.model.fileName(source_root)
                print(f"   Root element: '{root_name}' -> '{root_path}'")

        # Sprawdź pierwszy element w proxy model
        if manager.proxy_model.rowCount() > 0:
            print(f"\n📋 Elementy w proxy model:")
            for i in range(min(3, manager.proxy_model.rowCount())):
                proxy_index = manager.proxy_model.index(i, 0)
                if proxy_index.isValid():
                    source_index = manager.proxy_model.mapToSource(proxy_index)
                    if source_index.isValid():
                        file_path = manager.model.filePath(source_index)
                        file_name = manager.model.fileName(source_index)
                        print(f"   {i}: '{file_name}' -> '{file_path}'")

                        # Test menu kontekstowego na tym elemencie
                        if i == 0:  # Tylko pierwszy element
                            print(f"\n🖱️ Test menu kontekstowego dla '{file_name}':")

                            # Simulate context menu
                            captured_paths = []
                            original_func = manager.open_folder_in_explorer

                            def capture_path(path):
                                captured_paths.append(path)
                                print(f"   🗂️ Przechwycono ścieżkę: '{path}'")

                            manager.open_folder_in_explorer = capture_path

                            # Symuluj wywołanie menu kontekstowego bezpośrednio z parametrami
                            print(
                                f"   📍 Bezpośrednie wywołanie z ścieżką: '{file_path}'"
                            )

                            # Test bezpośredniego wywołania funkcji menu
                            try:
                                # Bezpośrednie testowanie extract ścieżki z indeksu
                                test_source_index = manager.model.index(file_path)
                                test_proxy_index = manager.proxy_model.mapFromSource(
                                    test_source_index
                                )

                                print(f"   🔍 Test mapowania:")
                                print(
                                    f"      Source index valid: {test_source_index.isValid()}"
                                )
                                print(
                                    f"      Proxy index valid: {test_proxy_index.isValid()}"
                                )

                                if test_proxy_index.isValid():
                                    # Symuluj menu kontekstowe
                                    print(f"   🎯 Symulacja menu kontekstowego...")

                                    # Manualnie wywołaj części funkcji show_folder_context_menu
                                    folder_path = manager.model.filePath(
                                        test_source_index
                                    )
                                    print(f"      Pobrana ścieżka: '{folder_path}'")

                                    if os.path.exists(folder_path) and os.path.isdir(
                                        folder_path
                                    ):
                                        print(
                                            f"   ✅ Ścieżka jest prawidłowym folderem"
                                        )
                                        # Symuluj kliknięcie "Otwórz w eksploratorze"
                                        manager.open_folder_in_explorer(folder_path)
                                    else:
                                        print(
                                            f"   ❌ Ścieżka nie jest prawidłowym folderem"
                                        )

                            except Exception as e:
                                print(f"   ❌ Błąd testu: {e}")
                                import traceback

                                traceback.print_exc()
        else:
            print(f"❌ Proxy model jest pusty")
    else:
        print(f"❌ Folder nie istnieje: {test_folder}")

    print(f"\n🔚 Debug zakończony")


if __name__ == "__main__":
    debug_model_structure()
