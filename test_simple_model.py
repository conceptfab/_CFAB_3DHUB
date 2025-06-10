#!/usr/bin/env python3
"""
Test prostego modelu bez proxy
"""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from PyQt6.QtCore import QDir
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import QApplication, QTreeView, QWidget

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def test_simple_model():
    """Test prostego modelu file system."""

    app = QApplication([])
    tree_view = QTreeView()

    # Utwórz prosty file system model
    model = QFileSystemModel()
    model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)

    test_folder = r"C:\_cloud\___TEST_FOLDER"

    # Sprawdź czy folder istnieje
    if not os.path.exists(test_folder):
        test_base = r"C:\_cloud"
        if os.path.exists(test_base):
            for item in os.listdir(test_base):
                item_path = os.path.join(test_base, item)
                if os.path.isdir(item_path) and not item.startswith("."):
                    test_folder = item_path
                    break

    if os.path.exists(test_folder):
        print(f"📁 Test folderu: {test_folder}")

        # Ustaw model
        model.setRootPath(test_folder)
        tree_view.setModel(model)

        # Pobierz indeks folderu
        folder_index = model.index(test_folder)
        tree_view.setRootIndex(folder_index)

        print(f"📊 Model root path: '{model.rootPath()}'")
        print(f"📊 Tree root index valid: {folder_index.isValid()}")

        if folder_index.isValid():
            # Sprawdź elementy w folderze
            row_count = model.rowCount(folder_index)
            print(f"📊 Row count: {row_count}")

            for i in range(min(3, row_count)):
                child_index = model.index(i, 0, folder_index)
                if child_index.isValid():
                    file_path = model.filePath(child_index)
                    file_name = model.fileName(child_index)
                    print(f"   {i}: '{file_name}' -> '{file_path}'")

                    # Test otwierania w eksploratorze dla pierwszego elementu
                    if i == 0 and os.path.isdir(file_path):
                        print(f"🗂️ Test otwierania w eksploratorze: '{file_path}'")

                        # Sprawdź czy to prawidłowa ścieżka
                        if os.path.exists(file_path):
                            print(f"   ✅ Ścieżka istnieje")
                            print(f"   📂 Jest folderem: {os.path.isdir(file_path)}")

                            # Test czy to folder Dokumenty
                            if "Documents" in file_path or "Dokumenty" in file_path:
                                print(f"   ⚠️ UWAGA: To jest folder Dokumenty!")
                            else:
                                print(f"   ✅ To nie jest folder Dokumenty")

                        else:
                            print(f"   ❌ Ścieżka nie istnieje")

        print(f"✅ Test zakończony pomyślnie")
    else:
        print(f"❌ Folder testowy nie istnieje: {test_folder}")


if __name__ == "__main__":
    test_simple_model()
