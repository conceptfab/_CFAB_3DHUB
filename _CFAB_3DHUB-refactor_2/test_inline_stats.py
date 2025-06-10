#!/usr/bin/env python3
"""
Test skryptu weryfikujący wyświetlanie statystyk folderów bezpośrednio w drzewie.
"""

import logging
import os
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

# Dodaj ścieżki do modułów
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from PyQt6.QtWidgets import QTreeView

from src.ui.directory_tree_manager import DirectoryTreeManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Statystyk Folderów w Drzewie")
        self.setGeometry(100, 100, 800, 600)

        # Utwórz główny widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Utwórz drzewo folderów
        self.folder_tree = QTreeView()
        layout.addWidget(self.folder_tree)

        # Utwórz menedżer drzewa
        self.tree_manager = DirectoryTreeManager(self.folder_tree, self)

        # Ustaw folder testowy
        test_folder = r"c:\_cloud\___TEST_FOLDER"
        if os.path.exists(test_folder):
            self.tree_manager.init_directory_tree(test_folder)
            logger.info(f"Załadowano folder testowy: {test_folder}")
        else:
            logger.warning("Folder testowy nie istnieje, używam domyślnego")
            self.tree_manager.init_directory_tree(os.getcwd())

        # Rozwiń pierwszych kilka folderów po krótkim czasie
        QTimer.singleShot(2000, self.expand_some_folders)

    def expand_some_folders(self):
        """Rozwiń kilka folderów aby zobaczyć statystyki."""
        root_index = self.folder_tree.rootIndex()
        for i in range(min(3, self.tree_manager.proxy_model.rowCount(root_index))):
            child_index = self.tree_manager.proxy_model.index(i, 0, root_index)
            if child_index.isValid():
                self.folder_tree.expand(child_index)

        logger.info("Rozwinięto pierwsze foldery - sprawdź czy widać statystyki!")
        print("\n" + "=" * 50)
        print("INSTRUKCJA:")
        print("1. Sprawdź czy nazwy folderów zawierają '(X.X GB, Y par)'")
        print("2. Jeśli widać '(... GB, ... par)' - statystyki są obliczane w tle")
        print("3. Po chwili powinny się pojawić rzeczywiste wartości")
        print("=" * 50 + "\n")


def main():
    app = QApplication(sys.argv)

    window = TestWindow()
    window.show()

    # Automatyczne zamknięcie po 30 sekundach
    QTimer.singleShot(30000, app.quit)

    print("Uruchamianie testu inline statystyk folderów...")
    print("Okno zostanie automatycznie zamknięte po 30 sekundach")

    app.exec()


if __name__ == "__main__":
    main()
