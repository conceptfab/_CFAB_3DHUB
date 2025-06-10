#!/usr/bin/env python3
"""
Test filtrowania folderów
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from PyQt6.QtCore import QDir, QTimer
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import QApplication, QTreeView, QWidget


def test_filtering():
    """Test filtrowania folderów."""

    app = QApplication([])
    tree_view = QTreeView()

    model = QFileSystemModel()
    model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)

    test_folder = r"C:\_cloud\___TEST_FOLDER"

    if os.path.exists(test_folder):
        print(f"📁 Test folderu: {test_folder}")
        print(f"📂 Zawartość folderu (system):")

        # Pokaż wszystkie foldery systemowo
        items = os.listdir(test_folder)
        for item in items:
            item_path = os.path.join(test_folder, item)
            if os.path.isdir(item_path):
                print(f"   📁 {item} (hidden: {item.startswith('.')})")

        # Ustaw model i czekaj na załadowanie
        print(f"\n🔧 Konfiguracja modelu...")
        model.setRootPath(test_folder)
        tree_view.setModel(model)

        folder_index = model.index(test_folder)
        tree_view.setRootIndex(folder_index)

        # Czekaj na asynchroniczne załadowanie
        print(f"⏳ Czekam na załadowanie modelu...")

        for attempt in range(10):  # Maksymalnie 1 sekunda
            app.processEvents()  # Pozwól Qt przetworzyć eventy
            time.sleep(0.1)

            row_count = model.rowCount(folder_index)
            print(f"   Próba {attempt + 1}: Row count = {row_count}")

            if row_count > 0:
                break

        # Sprawdź końcowy stan
        final_count = model.rowCount(folder_index)
        print(f"\n📊 Końcowy row count: {final_count}")

        if final_count > 0:
            print(f"📋 Elementy w modelu:")
            for i in range(final_count):
                child_index = model.index(i, 0, folder_index)
                if child_index.isValid():
                    file_path = model.filePath(child_index)
                    file_name = model.fileName(child_index)
                    print(f"   {i}: '{file_name}' -> '{file_path}'")
        else:
            print(f"❌ Model nadal pusty po odczekaniu")

            # Test bez filtra NoDotAndDotDot
            print(f"\n🔧 Test bez filtra NoDotAndDotDot...")
            model2 = QFileSystemModel()
            model2.setFilter(QDir.Filter.AllDirs)
            model2.setRootPath(test_folder)

            time.sleep(0.2)
            app.processEvents()

            folder_index2 = model2.index(test_folder)
            count2 = model2.rowCount(folder_index2)
            print(f"   Row count bez filtra: {count2}")

            if count2 > 0:
                print(f"📋 Elementy bez filtra:")
                for i in range(min(5, count2)):
                    child_index = model2.index(i, 0, folder_index2)
                    if child_index.isValid():
                        file_path = model2.filePath(child_index)
                        file_name = model2.fileName(child_index)
                        print(f"   {i}: '{file_name}' -> '{file_path}'")
    else:
        print(f"❌ Folder nie istnieje: {test_folder}")


if __name__ == "__main__":
    test_filtering()
