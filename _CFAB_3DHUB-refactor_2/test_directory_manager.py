#!/usr/bin/env python3
"""
Test skrypt dla DirectoryTreeManager - sprawdzenie nowych funkcjonalności.
"""

import logging
import os
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Dodaj ścieżkę do src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from PyQt6.QtWidgets import QTreeView

from src.ui.directory_tree_manager import DirectoryTreeManager
from src.utils.logging_config import setup_logging


class TestMainWindow(QMainWindow):
    """Testowe okno główne dla DirectoryTreeManager."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test DirectoryTreeManager - Nowe funkcjonalności")
        self.setGeometry(100, 100, 1000, 700)

        # Setup logging
        setup_logging(log_level="DEBUG")
        self.logger = logging.getLogger(__name__)

        # Mock current_working_directory
        self.current_working_directory = r"c:\_cloud\_CFAB_3DHUB"

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Info label
        info_label = QLabel("Test nowych funkcjonalności DirectoryTreeManager:")
        layout.addWidget(info_label)

        # Status label
        self.status_label = QLabel("Status: Inicjalizacja...")
        layout.addWidget(self.status_label)

        # Tree view
        self.folder_tree = QTreeView()
        layout.addWidget(self.folder_tree)

        # Test buttons
        buttons_layout = QVBoxLayout()

        test_expand_controls_btn = QPushButton("Test: Kontrolki rozwijania")
        test_expand_controls_btn.clicked.connect(self.test_expand_controls)
        buttons_layout.addWidget(test_expand_controls_btn)

        test_cache_btn = QPushButton("Test: Cache statystyk")
        test_cache_btn.clicked.connect(self.test_cache)
        buttons_layout.addWidget(test_cache_btn)

        test_filtering_btn = QPushButton("Test: Filtrowanie folderów")
        test_filtering_btn.clicked.connect(self.test_filtering)
        buttons_layout.addWidget(test_filtering_btn)

        layout.addLayout(buttons_layout)

        # Initialize DirectoryTreeManager
        self.init_directory_manager()

    def init_directory_manager(self):
        """Inicjalizuje DirectoryTreeManager z nowymi funkcjonalnościami."""
        try:
            self.directory_manager = DirectoryTreeManager(self.folder_tree, self)

            # Test asynchronicznej inicjalizacji
            self.directory_manager.init_directory_tree_async(
                self.current_working_directory
            )

            self.status_label.setText(
                "Status: DirectoryTreeManager zainicjalizowany z nowymi funkcjonalnościami!"
            )
            self.logger.info("DirectoryTreeManager zainicjalizowany pomyślnie")

        except Exception as e:
            self.status_label.setText(f"Status: BŁĄD - {e}")
            self.logger.error(f"Błąd inicjalizacji DirectoryTreeManager: {e}")

    def test_expand_controls(self):
        """Test kontrolek rozwijania/zwijania."""
        try:
            controls_widget = self.directory_manager.setup_expand_collapse_controls()
            self.status_label.setText("Status: Kontrolki rozwijania utworzone!")
            self.logger.info("Test kontrolek rozwijania - OK")
        except Exception as e:
            self.status_label.setText(f"Status: BŁĄD kontrolek - {e}")
            self.logger.error(f"Błąd testu kontrolek: {e}")

    def test_cache(self):
        """Test systemu cache statystyk."""
        try:
            test_folder = self.current_working_directory

            # Test cache miss
            cached_stats = self.directory_manager.get_cached_folder_statistics(
                test_folder
            )
            if cached_stats is None:
                self.logger.info("Cache MISS - poprawnie")
            else:
                self.logger.warning("Cache HIT gdy powinien być MISS")

            # Test asynchronicznego obliczania
            def on_stats_calculated(stats):
                self.status_label.setText(
                    f"Status: Statystyki - {stats.size_gb:.2f} GB, {stats.pairs_count} par"
                )
                self.logger.info(f"Obliczono statystyki: {stats.size_gb:.2f} GB")

            self.directory_manager.calculate_folder_statistics_async(
                test_folder, on_stats_calculated
            )
            self.logger.info("Test cache statystyk - uruchomiony")

        except Exception as e:
            self.status_label.setText(f"Status: BŁĄD cache - {e}")
            self.logger.error(f"Błąd testu cache: {e}")

    def test_filtering(self):
        """Test filtrowania ukrytych folderów."""
        try:
            # Test różnych nazw folderów
            test_folders = [
                ".app_metadata",
                "__pycache__",
                ".git",
                "normal_folder",
                "src",
            ]
            results = []

            for folder_name in test_folders:
                should_show = self.directory_manager.should_show_folder(folder_name)
                results.append(
                    f"{folder_name}: {'POKAZUJ' if should_show else 'UKRYJ'}"
                )
                self.logger.info(f"Filtrowanie {folder_name}: {should_show}")

            self.status_label.setText(f"Status: Filtrowanie - {len(results)} testów")
            self.logger.info("Test filtrowania - OK")

        except Exception as e:
            self.status_label.setText(f"Status: BŁĄD filtrowania - {e}")
            self.logger.error(f"Błąd testu filtrowania: {e}")

    def select_folder(self, folder_path):
        """Mock metoda dla MainWindow.select_folder()."""
        self.current_working_directory = folder_path
        self.logger.info(f"Mock: Zmieniono folder na {folder_path}")


def main():
    """Uruchom test aplikacji."""
    app = QApplication(sys.argv)

    window = TestMainWindow()
    window.show()

    # Auto-test po 2 sekundach
    QTimer.singleShot(2000, window.test_expand_controls)
    QTimer.singleShot(4000, window.test_cache)
    QTimer.singleShot(6000, window.test_filtering)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
