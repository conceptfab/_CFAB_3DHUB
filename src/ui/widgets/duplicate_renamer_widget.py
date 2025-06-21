"""
Widget do renumeracji duplikatów plików - zintegrowany z aplikacją CFAB_3DHUB
"""

import logging
import os
import random
import string
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class DuplicateRenamerWorker(QThread):
    """Worker thread dla renumeracji duplikatów."""

    progress_updated = pyqtSignal(int, str)
    finished = pyqtSignal(int, int, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self.is_cancelled = False

    def cancel(self):
        """Anuluje operację."""
        self.is_cancelled = True

    def run(self):
        """Wykonuje renumerację duplikatów."""
        try:
            self.progress_updated.emit(10, "🔍 Skanowanie plików...")

            if not os.path.exists(self.folder_path):
                self.error_occurred.emit(f"Folder nie istnieje: {self.folder_path}")
                return

            # Zbierz wszystkie pliki
            files_by_name = {}
            duplicates_found = []

            path_obj = Path(self.folder_path)
            all_files = list(path_obj.glob("*"))
            file_count = len([f for f in all_files if f.is_file()])

            if file_count == 0:
                self.finished.emit(0, 0, "Brak plików w folderze")
                return

            self.progress_updated.emit(25, f"📄 Analiza {file_count} plików...")

            # Grupuj pliki według STEM (nazwa bez rozszerzenia) - dla par archiwum/podgląd
            for file_path in all_files:
                if self.is_cancelled:
                    return

                if file_path.is_file():
                    # STEM (nazwa bez rozszerzenia) - żeby znaleźć pary plików!
                    stem_name = file_path.stem.lower()

                    if stem_name not in files_by_name:
                        files_by_name[stem_name] = []
                    files_by_name[stem_name].append(file_path)

            # Znajdź duplikaty
            for full_name, paths in files_by_name.items():
                if len(paths) > 1:
                    duplicates_found.extend(paths)

            if not duplicates_found:
                self.finished.emit(0, 0, "Nie znaleziono duplikatów")
                return

            self.progress_updated.emit(
                50, f"🎯 Znaleziono {len(duplicates_found)} duplikatów"
            )

            # Renumeruj duplikaty
            renamed_count = 0
            errors_count = 0
            total_duplicates = len(duplicates_found)

            for stem_name, paths in files_by_name.items():
                if self.is_cancelled:
                    return

                if len(paths) > 1:
                    # Generuj LOSOWĄ nazwę dla CAŁEJ pary plików!
                    random_name = self._generate_random_suffix(8)

                    for i, old_path in enumerate(paths):
                        if self.is_cancelled:
                            return

                        try:
                            ext = old_path.suffix

                            # WSZYSCY w parze dostają tę samą losową nazwę!
                            new_filename = f"{random_name}{ext}"
                            new_path = old_path.parent / new_filename

                            # Sprawdź kolizje nazw
                            counter = 1
                            while new_path.exists():
                                new_filename = f"{random_name}_{counter}{ext}"
                                new_path = old_path.parent / new_filename
                                counter += 1

                            # Wykonaj rename
                            old_path.rename(new_path)
                            renamed_count += 1

                            # Aktualizuj progress
                            progress = 50 + (renamed_count * 40 // total_duplicates)
                            msg = f"✅ Zmieniono: {old_path.name} → {new_filename}"
                            self.progress_updated.emit(progress, msg)

                        except Exception as e:
                            errors_count += 1
                            logging.error(f"Błąd zmiany nazwy {old_path}: {e}")

            self.progress_updated.emit(100, "🎉 Zakończono!")
            self.finished.emit(
                renamed_count, errors_count, f"Zrenumerowano {renamed_count} plików"
            )

        except Exception as e:
            self.error_occurred.emit(f"Błąd podczas renumeracji: {e}")

    def _generate_random_suffix(self, length):
        """Generuje losowy sufiks."""
        characters = string.ascii_letters + string.digits
        return "".join(random.choice(characters) for _ in range(length))


class DuplicateRenamerDialog(QDialog):
    """Dialog do renumeracji duplikatów plików."""

    def __init__(self, initial_folder="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎲 Generator Losowych Nazw")
        self.setModal(True)
        self.resize(600, 450)
        self.initial_folder = initial_folder
        self.worker = None
        self._setup_ui()
        self._setup_styles()

        if initial_folder:
            self.folder_edit.setText(initial_folder)
            # Automatycznie skanuj po otwarciu
            QTimer.singleShot(200, self._scan_duplicates)

    def _setup_ui(self):
        """Konfiguruje interfejs użytkownika."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Nagłówek
        header = QLabel("🎲 Generator Losowych Nazw")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        header.setFont(font)
        layout.addWidget(header)

        # Opis
        desc = QLabel(
            "Generuje losowe nazwy dla par plików o wspólnym stem (zachowuje rozszerzenia)."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        # Info o folderze
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("📁 Folder do skanowania:"))

        self.folder_edit = QLineEdit()
        self.folder_edit.setReadOnly(True)
        folder_layout.addWidget(self.folder_edit)

        layout.addLayout(folder_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Log area
        self.log_area = QTextEdit()
        self.log_area.setMaximumHeight(150)
        self.log_area.setVisible(False)
        layout.addWidget(self.log_area)

        # Buttons
        button_layout = QHBoxLayout()

        self.scan_button = QPushButton("Skanuj")
        self.scan_button.clicked.connect(self._scan_duplicates)
        self.scan_button.setFixedHeight(30)
        self.scan_button.setStyleSheet(
            """
            QPushButton {
                background-color: #3F3F46;
                color: white;
                border: 1px solid #007ACC;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #007ACC;
            }
            QPushButton:pressed {
                background-color: #005A9E;
            }
            QPushButton:disabled {
                background-color: #252526;
                color: #6A6A6A;
                border-color: #464647;
            }
        """
        )
        button_layout.addWidget(self.scan_button)

        self.rename_button = QPushButton("Generuj")
        self.rename_button.clicked.connect(self._rename_duplicates)
        self.rename_button.setEnabled(False)
        self.rename_button.setFixedHeight(30)
        self.rename_button.setStyleSheet(
            """
            QPushButton {
                background-color: #3F3F46;
                color: white;
                border: 1px solid #DC2626;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
            QPushButton:pressed {
                background-color: #B91C1C;
            }
            QPushButton:disabled {
                background-color: #252526;
                color: #6A6A6A;
                border-color: #464647;
            }
        """
        )
        button_layout.addWidget(self.rename_button)

        self.cancel_button = QPushButton("Anuluj")
        self.cancel_button.clicked.connect(self._cancel_operation)
        self.cancel_button.setVisible(False)
        self.cancel_button.setFixedHeight(30)
        self.cancel_button.setStyleSheet(
            """
            QPushButton {
                background-color: #3F3F46;
                color: white;
                border: 1px solid #6B7280;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #6B7280;
            }
            QPushButton:pressed {
                background-color: #4B5563;
            }
        """
        )
        button_layout.addWidget(self.cancel_button)

        button_layout.addStretch()

        self.close_button = QPushButton("Zamknij")
        self.close_button.clicked.connect(self.accept)
        self.close_button.setFixedHeight(30)
        self.close_button.setStyleSheet(
            """
            QPushButton {
                background-color: #3F3F46;
                color: white;
                border: 1px solid #16A34A;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #16A34A;
            }
            QPushButton:pressed {
                background-color: #15803D;
            }
        """
        )
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def _setup_styles(self):
        """Konfiguruje style CSS."""
        self.setStyleSheet(
            """
            QDialog {
                background-color: #252526;
                color: #CCCCCC;
            }
            QLabel {
                color: #CCCCCC;
                padding: 5px;
            }
            QLineEdit {
                background-color: #1C1C1C;
                border: 1px solid #3F3F46;
                border-radius: 4px;
                padding: 8px;
                color: #CCCCCC;
                font-family: 'Courier New', monospace;
            }
            QPushButton {
                background-color: #0078D4;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 6px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
            QPushButton:pressed {
                background-color: #005A9E;
            }
            QPushButton:disabled {
                background-color: #3F3F46;
                color: #666666;
            }
            QTextEdit {
                background-color: #1C1C1C;
                border: 1px solid #3F3F46;
                border-radius: 4px;
                color: #CCCCCC;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
            QProgressBar {
                border: 1px solid #3F3F46;
                border-radius: 4px;
                background-color: #1C1C1C;
                text-align: center;
                color: #CCCCCC;
            }
            QProgressBar::chunk {
                background-color: #0078D4;
                border-radius: 3px;
            }
        """
        )

        # Specjalne style dla przycisków
        self.scan_button.setStyleSheet(
            self.scan_button.styleSheet()
            + """
            QPushButton { background-color: #16537e; }
            QPushButton:hover { background-color: #1f6692; }
        """
        )

        self.rename_button.setStyleSheet(
            self.rename_button.styleSheet()
            + """
            QPushButton { background-color: #e74c3c; }
            QPushButton:hover { background-color: #c0392b; }
        """
        )

        self.cancel_button.setStyleSheet(
            self.cancel_button.styleSheet()
            + """
            QPushButton { background-color: #DC2626; }
            QPushButton:hover { background-color: #B91C1C; }
        """
        )

    def _scan_duplicates(self):
        """Skanuje folder w poszukiwaniu duplikatów."""
        folder_path = self.folder_edit.text().strip()
        if not folder_path:
            QMessageBox.warning(self, "Błąd", "Brak ścieżki folderu.")
            return

        if not os.path.exists(folder_path):
            QMessageBox.warning(self, "Błąd", "Folder nie istnieje.")
            return

        try:
            files_by_name = {}
            duplicates_found = []

            path_obj = Path(folder_path)
            for file_path in path_obj.glob("*"):
                if file_path.is_file():
                    # STEM (nazwa bez rozszerzenia) - dla par archiwum/podgląd
                    stem_name = file_path.stem.lower()
                    if stem_name not in files_by_name:
                        files_by_name[stem_name] = []
                    files_by_name[stem_name].append(file_path)

            # Znajdź pary plików
            for stem_name, paths in files_by_name.items():
                if len(paths) > 1:
                    duplicates_found.extend(paths)

            if duplicates_found:
                groups = len([p for p in files_by_name.values() if len(p) > 1])
                self.status_label.setText(
                    f"🎯 Znaleziono {len(duplicates_found)} plików w {groups} parach"
                )
                self.rename_button.setEnabled(True)

                # Pokaż log z duplikatami
                self.log_area.setVisible(True)
                self.log_area.clear()
                self.log_area.append("🔍 ZNALEZIONE PARY PLIKÓW:\n")

                for stem_name, paths in files_by_name.items():
                    if len(paths) > 1:
                        self.log_area.append(
                            f"📁 Para '{stem_name}' ({len(paths)} plików):"
                        )
                        for path in paths:
                            self.log_area.append(f"   • {path.name}")
                        self.log_area.append("")
            else:
                self.status_label.setText(
                    "✅ Nie znaleziono par - wszystkie pliki mają unikalne nazwy stem"
                )
                self.rename_button.setEnabled(False)
                self.log_area.setVisible(False)

        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd podczas skanowania: {e}")
            logging.error(f"DuplicateRenamer scan error: {e}")

    def _rename_duplicates(self):
        """Rozpoczyna renumerację duplikatów."""
        folder_path = self.folder_edit.text().strip()
        if not folder_path:
            return

        # Potwierdzenie
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            f"Czy na pewno chcesz wygenerować losowe nazwy dla wszystkich par w folderze?\n\n{folder_path}\n\nTa operacja jest nieodwracalna!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Uruchom worker
        self.worker = DuplicateRenamerWorker(folder_path)
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.finished.connect(self._on_rename_finished)
        self.worker.error_occurred.connect(self._on_rename_error)

        # UI changes
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.cancel_button.setVisible(True)
        self.scan_button.setEnabled(False)
        self.rename_button.setEnabled(False)

        self.log_area.setVisible(True)
        self.log_area.clear()
        self.log_area.append("🚀 ROZPOCZYNAM GENEROWANIE...\n")

        self.worker.start()

    def _cancel_operation(self):
        """Anuluje bieżącą operację."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(3000)

        self._reset_ui()
        self.status_label.setText("❌ Operacja anulowana")

    def _on_progress_updated(self, progress, message):
        """Aktualizuje progress bar i status."""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
        self.log_area.append(f"{progress:3d}% - {message}")

    def _on_rename_finished(self, renamed_count, errors_count, message):
        """Obsługuje zakończenie renumeracji."""
        self._reset_ui()

        if errors_count > 0:
            self.status_label.setText(f"⚠️ {message} (błędów: {errors_count})")
            QMessageBox.warning(
                self,
                "Zakończono z błędami",
                f"{message}\n\nWystąpiło {errors_count} błędów.",
            )
        else:
            self.status_label.setText(f"✅ {message}")
            QMessageBox.information(
                self,
                "Sukces",
                f"{message}\n\nWszystkie pary otrzymały losowe nazwy.",
            )

        self.log_area.append(f"\n🎉 ZAKOŃCZONO: {message}")

        # Odśwież interfejs po renumeracji
        if renamed_count > 0:
            QTimer.singleShot(1000, lambda: self._scan_duplicates())

    def _on_rename_error(self, error_message):
        """Obsługuje błędy podczas renumeracji."""
        self._reset_ui()
        self.status_label.setText(f"❌ Błąd: {error_message}")
        QMessageBox.critical(self, "Błąd", error_message)
        self.log_area.append(f"\n❌ BŁĄD: {error_message}")

    def _reset_ui(self):
        """Resetuje UI po zakończeniu operacji."""
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)
        self.scan_button.setEnabled(True)
