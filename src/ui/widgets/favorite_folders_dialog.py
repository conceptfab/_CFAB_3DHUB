"""
Dialog konfiguracji ulubionych folderów.
"""

import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.config.config_core import AppConfig


class FavoriteFoldersDialog(QDialog):
    """Dialog do konfiguracji ulubionych folderów."""

    configuration_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.app_config = AppConfig.get_instance()
        self.logger = logging.getLogger(__name__)

        self.setWindowTitle("Konfiguruj ulubione foldery")
        self.setModal(True)
        self.resize(800, 400)

        self._init_ui()
        self._load_current_configuration()

    def _init_ui(self):
        """Inicjalizuje interfejs użytkownika."""
        layout = QVBoxLayout(self)

        # Nagłówek
        header_label = QLabel("Konfiguracja ulubionych folderów")
        header_label.setStyleSheet(
            """
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #CCCCCC;
                padding: 10px;
            }
        """
        )
        layout.addWidget(header_label)

        # Tabela konfiguracji
        self._create_configuration_table()
        layout.addWidget(self.table)

        # Przyciski akcji
        self._create_action_buttons()
        layout.addLayout(self.action_buttons_layout)

        # Przyciski dialogu
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self._save_configuration)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _create_configuration_table(self):
        """Tworzy tabelę konfiguracji."""
        self.table = QTableWidget(4, 4)
        headers = ["Nazwa", "Ścieżka", "Kolor", "Opis"]
        self.table.setHorizontalHeaderLabels(headers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(2, 80)

    def _create_action_buttons(self):
        """Tworzy przyciski akcji."""
        self.action_buttons_layout = QHBoxLayout()

        self.select_folder_btn = QPushButton("📁 Wybierz folder")
        self.select_folder_btn.clicked.connect(self._select_folder_for_current_row)
        self.action_buttons_layout.addWidget(self.select_folder_btn)

        self.select_color_btn = QPushButton("🎨 Wybierz kolor")
        self.select_color_btn.clicked.connect(self._select_color_for_current_row)
        self.action_buttons_layout.addWidget(self.select_color_btn)

        self.action_buttons_layout.addStretch()

    def _load_current_configuration(self):
        """Ładuje aktualną konfigurację."""
        favorite_folders = self.app_config.get("favorite_folders", [])

        for row, folder_config in enumerate(favorite_folders):
            if row >= 4:
                break

            name_item = QTableWidgetItem(folder_config.get("name", f"Folder {row+1}"))
            self.table.setItem(row, 0, name_item)

            path_item = QTableWidgetItem(folder_config.get("path", ""))
            self.table.setItem(row, 1, path_item)

            color_btn = QPushButton()
            color_value = folder_config.get("color", "#007ACC")
            color_btn.setStyleSheet(f"background-color: {color_value};")
            color_btn.clicked.connect(
                lambda checked, r=row: self._select_color_for_row(r)
            )
            self.table.setCellWidget(row, 2, color_btn)

            desc_item = QTableWidgetItem(folder_config.get("description", ""))
            self.table.setItem(row, 3, desc_item)

    def _select_folder_for_current_row(self):
        """Wybiera folder dla aktualnego wiersza."""
        current_row = self.table.currentRow()
        if current_row >= 0:
            self._select_folder_for_row(current_row)

    def _select_folder_for_row(self, row: int):
        """Wybiera folder dla wiersza."""
        folder_path = QFileDialog.getExistingDirectory(
            self, f"Wybierz folder dla przycisku {row + 1}"
        )

        if folder_path:
            path_item = self.table.item(row, 1)
            if not path_item:
                path_item = QTableWidgetItem()
                self.table.setItem(row, 1, path_item)
            path_item.setText(folder_path)

    def _select_color_for_current_row(self):
        """Wybiera kolor dla aktualnego wiersza."""
        current_row = self.table.currentRow()
        if current_row >= 0:
            self._select_color_for_row(current_row)

    def _select_color_for_row(self, row: int):
        """Wybiera kolor dla wiersza."""
        color = QColorDialog.getColor(QColor("#007ACC"), self)

        if color.isValid():
            color_btn = self.table.cellWidget(row, 2)
            if color_btn:
                color_btn.setStyleSheet(f"background-color: {color.name()};")

    def _save_configuration(self):
        """Zapisuje konfigurację."""
        try:
            favorite_folders = []

            for row in range(4):
                name_item = self.table.item(row, 0)
                path_item = self.table.item(row, 1)
                color_btn = self.table.cellWidget(row, 2)
                desc_item = self.table.item(row, 3)

                color_value = "#007ACC"
                if color_btn:
                    style = color_btn.styleSheet()
                    if "background-color:" in style:
                        start = style.find("background-color:") + len(
                            "background-color:"
                        )
                        end = style.find(";", start)
                        if end > start:
                            color_value = style[start:end].strip()

                folder_config = {
                    "name": name_item.text() if name_item else f"Folder {row+1}",
                    "path": path_item.text() if path_item else "",
                    "color": color_value,
                    "description": desc_item.text() if desc_item else "",
                }

                favorite_folders.append(folder_config)

            self.app_config.set("favorite_folders", favorite_folders)
            self.configuration_saved.emit()
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd zapisu: {str(e)}")
