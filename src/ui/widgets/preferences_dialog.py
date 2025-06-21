"""
Dialog preferencji aplikacji CFAB_3DHUB.
"""

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.app_config import AppConfig


class PreferencesDialog(QDialog):
    """Dialog okna preferencji aplikacji."""

    preferences_changed = pyqtSignal()  # Sygnał emitowany po zmianie ustawień

    def __init__(self, parent=None):
        super().__init__(parent)
        self.app_config = AppConfig()
        self.setWindowTitle("Preferencje - CFAB_3DHUB")
        self.setModal(True)
        self.resize(600, 500)

        # Flagi do śledzenia zmian
        self.changes_made = False

        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        """Tworzy interfejs użytkownika okna preferencji."""
        layout = QVBoxLayout(self)

        # Tab widget dla różnych kategorii ustawień
        self.tab_widget = QTabWidget()

        # Zakładki
        self._create_general_tab()
        self._create_scanning_tab()
        self._create_ui_tab()
        self._create_advanced_tab()

        layout.addWidget(self.tab_widget)

        # Przyciski na dole
        self._create_button_box()
        layout.addWidget(self.button_box)

    def _create_general_tab(self):
        """Tworzy zakładkę ogólnych ustawień."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Grupa: Domyślne ścieżki
        paths_group = QGroupBox("Domyślne ścieżki")
        paths_layout = QGridLayout(paths_group)

        # Domyślny folder roboczy
        paths_layout.addWidget(QLabel("Domyślny folder roboczy:"), 0, 0)
        self.default_folder_edit = QLineEdit()
        self.default_folder_browse = QPushButton("Przeglądaj...")
        self.default_folder_browse.clicked.connect(self._browse_default_folder)
        paths_layout.addWidget(self.default_folder_edit, 0, 1)
        paths_layout.addWidget(self.default_folder_browse, 0, 2)

        # Folder dla eksportu
        paths_layout.addWidget(QLabel("Folder eksportu:"), 1, 0)
        self.export_folder_edit = QLineEdit()
        self.export_folder_browse = QPushButton("Przeglądaj...")
        self.export_folder_browse.clicked.connect(self._browse_export_folder)
        paths_layout.addWidget(self.export_folder_edit, 1, 1)
        paths_layout.addWidget(self.export_folder_browse, 1, 2)

        # Przycisk do ustawienia aktualnego folderu jako domyślny
        self.set_current_as_default_btn = QPushButton(
            "🔒 Ustaw aktualny folder jako domyślny"
        )
        self.set_current_as_default_btn.clicked.connect(self._set_current_as_default)
        paths_layout.addWidget(self.set_current_as_default_btn, 2, 0, 1, 3)

        layout.addWidget(paths_group)

        # Grupa: Automatyzacja
        automation_group = QGroupBox("Automatyzacja")
        automation_layout = QVBoxLayout(automation_group)

        self.auto_save_metadata = QCheckBox("Automatycznie zapisuj metadane")
        self.auto_load_last_folder = QCheckBox("Załaduj ostatni folder przy starcie")
        self.auto_backup_metadata = QCheckBox("Twórz kopie zapasowe metadanych")

        automation_layout.addWidget(self.auto_save_metadata)
        automation_layout.addWidget(self.auto_load_last_folder)
        automation_layout.addWidget(self.auto_backup_metadata)

        layout.addWidget(automation_group)

        # Grupa: Powiadomienia
        notifications_group = QGroupBox("Powiadomienia")
        notifications_layout = QVBoxLayout(notifications_group)

        self.show_completion_messages = QCheckBox(
            "Pokaż komunikaty o zakończeniu operacji"
        )
        self.show_error_details = QCheckBox("Pokaż szczegóły błędów")
        self.confirm_delete_operations = QCheckBox("Potwierdź operacje usuwania")

        notifications_layout.addWidget(self.show_completion_messages)
        notifications_layout.addWidget(self.show_error_details)
        notifications_layout.addWidget(self.confirm_delete_operations)

        layout.addWidget(notifications_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Ogólne")

    def _create_scanning_tab(self):
        """Tworzy zakładkę ustawień skanowania."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Grupa: Strategie parowania
        pairing_group = QGroupBox("Strategia parowania plików")
        pairing_layout = QVBoxLayout(pairing_group)

        self.pairing_strategy_group = QButtonGroup()

        self.strategy_first_match = QRadioButton("Pierwsza para (first_match)")
        self.strategy_best_match = QRadioButton("Najlepsza para (best_match)")
        self.strategy_size_priority = QRadioButton("Priorytet rozmiaru (size_priority)")

        self.pairing_strategy_group.addButton(self.strategy_first_match, 0)
        self.pairing_strategy_group.addButton(self.strategy_best_match, 1)
        self.pairing_strategy_group.addButton(self.strategy_size_priority, 2)

        pairing_layout.addWidget(self.strategy_first_match)
        pairing_layout.addWidget(self.strategy_best_match)
        pairing_layout.addWidget(self.strategy_size_priority)

        layout.addWidget(pairing_group)

        # Grupa: Opcje skanowania
        scanning_group = QGroupBox("Opcje skanowania")
        scanning_layout = QGridLayout(scanning_group)

        # Głębokość skanowania
        scanning_layout.addWidget(QLabel("Maksymalna głębokość:"), 0, 0)
        self.max_depth_spin = QSpinBox()
        self.max_depth_spin.setMinimum(0)
        self.max_depth_spin.setMaximum(10)
        self.max_depth_spin.setSpecialValueText("Bez limitu")
        scanning_layout.addWidget(self.max_depth_spin, 0, 1)

        # Ignorowane rozszerzenia
        scanning_layout.addWidget(QLabel("Ignorowane rozszerzenia:"), 1, 0)
        self.ignored_extensions_edit = QLineEdit()
        self.ignored_extensions_edit.setPlaceholderText(
            "np. .tmp,.bak,.log (oddzielone przecinkami)"
        )
        scanning_layout.addWidget(self.ignored_extensions_edit, 1, 1)

        # Minimalna wielkość pliku
        scanning_layout.addWidget(QLabel("Minimalna wielkość pliku (KB):"), 2, 0)
        self.min_file_size_spin = QSpinBox()
        self.min_file_size_spin.setMinimum(0)
        self.min_file_size_spin.setMaximum(1000000)
        self.min_file_size_spin.setSuffix(" KB")
        scanning_layout.addWidget(self.min_file_size_spin, 2, 1)

        layout.addWidget(scanning_group)

        # Grupa: Cache
        cache_group = QGroupBox("Cache i wydajność")
        cache_layout = QGridLayout(cache_group)

        self.enable_thumbnail_cache = QCheckBox("Włącz cache miniatur")
        cache_layout.addWidget(self.enable_thumbnail_cache, 0, 0, 1, 2)

        cache_layout.addWidget(QLabel("Maksymalny rozmiar cache (MB):"), 1, 0)
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setMinimum(10)
        self.cache_size_spin.setMaximum(1000)
        self.cache_size_spin.setSuffix(" MB")
        cache_layout.addWidget(self.cache_size_spin, 1, 1)

        layout.addWidget(cache_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Skanowanie")

    def _create_ui_tab(self):
        """Tworzy zakładkę ustawień interfejsu."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Grupa: Wygląd
        appearance_group = QGroupBox("Wygląd")
        appearance_layout = QGridLayout(appearance_group)

        # Rozmiar miniatur
        appearance_layout.addWidget(QLabel("Domyślny rozmiar miniatur:"), 0, 0)
        self.default_thumbnail_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.default_thumbnail_size_slider.setMinimum(100)
        self.default_thumbnail_size_slider.setMaximum(400)
        self.default_thumbnail_size_slider.setValue(200)
        self.thumbnail_size_label = QLabel("200px")
        self.default_thumbnail_size_slider.valueChanged.connect(
            lambda v: self.thumbnail_size_label.setText(f"{v}px")
        )
        appearance_layout.addWidget(self.default_thumbnail_size_slider, 0, 1)
        appearance_layout.addWidget(self.thumbnail_size_label, 0, 2)

        # Kolumny w galerii
        appearance_layout.addWidget(QLabel("Kolumny w galerii:"), 1, 0)
        self.gallery_columns_combo = QComboBox()
        self.gallery_columns_combo.addItems(["Auto", "2", "3", "4", "5", "6", "8"])
        appearance_layout.addWidget(self.gallery_columns_combo, 1, 1)

        layout.addWidget(appearance_group)

        # Grupa: Sortowanie
        sorting_group = QGroupBox("Domyślne sortowanie")
        sorting_layout = QGridLayout(sorting_group)

        sorting_layout.addWidget(QLabel("Sortuj według:"), 0, 0)
        self.sort_by_combo = QComboBox()
        self.sort_by_combo.addItems(
            [
                "Nazwy pliku",
                "Daty modyfikacji",
                "Rozmiaru pliku",
                "Rozszerzenia",
                "Oceny",
                "Koloru",
            ]
        )
        sorting_layout.addWidget(self.sort_by_combo, 0, 1)

        sorting_layout.addWidget(QLabel("Kierunek:"), 1, 0)
        self.sort_order_combo = QComboBox()
        self.sort_order_combo.addItems(["Rosnąco", "Malejąco"])
        sorting_layout.addWidget(self.sort_order_combo, 1, 1)

        layout.addWidget(sorting_group)

        # Grupa: Kolory i tagi
        colors_group = QGroupBox("Kolory i tagi")
        colors_layout = QVBoxLayout(colors_group)

        self.show_color_tags = QCheckBox("Pokaż kolorowe tagi")
        self.show_star_ratings = QCheckBox("Pokaż oceny gwiazdkami")
        self.show_file_info = QCheckBox("Pokaż informacje o plikach")

        colors_layout.addWidget(self.show_color_tags)
        colors_layout.addWidget(self.show_star_ratings)
        colors_layout.addWidget(self.show_file_info)

        layout.addWidget(colors_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Interfejs")

    def _create_advanced_tab(self):
        """Tworzy zakładkę zaawansowanych ustawień."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Grupa: Logowanie
        logging_group = QGroupBox("Logowanie")
        logging_layout = QGridLayout(logging_group)

        logging_layout.addWidget(QLabel("Poziom logowania:"), 0, 0)
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        logging_layout.addWidget(self.log_level_combo, 0, 1)

        self.enable_file_logging = QCheckBox("Zapisuj logi do pliku")
        logging_layout.addWidget(self.enable_file_logging, 1, 0, 1, 2)

        layout.addWidget(logging_group)

        # Grupa: Wydajność
        performance_group = QGroupBox("Wydajność")
        performance_layout = QGridLayout(performance_group)

        performance_layout.addWidget(QLabel("Liczba wątków roboczych:"), 0, 0)
        self.worker_threads_spin = QSpinBox()
        self.worker_threads_spin.setMinimum(1)
        self.worker_threads_spin.setMaximum(16)
        performance_layout.addWidget(self.worker_threads_spin, 0, 1)

        self.enable_parallel_processing = QCheckBox("Włącz przetwarzanie równoległe")
        performance_layout.addWidget(self.enable_parallel_processing, 1, 0, 1, 2)

        layout.addWidget(performance_group)

        # Grupa: Bezpieczeństwo
        security_group = QGroupBox("Bezpieczeństwo")
        security_layout = QVBoxLayout(security_group)

        self.confirm_file_operations = QCheckBox("Potwierdź operacje na plikach")
        self.backup_before_operations = QCheckBox(
            "Utwórz kopie zapasowe przed operacjami"
        )
        self.safe_mode = QCheckBox("Tryb bezpieczny (dodatkowe sprawdzenia)")

        security_layout.addWidget(self.confirm_file_operations)
        security_layout.addWidget(self.backup_before_operations)
        security_layout.addWidget(self.safe_mode)

        layout.addWidget(security_group)

        # Grupa: Konserwacja
        maintenance_group = QGroupBox("Konserwacja")
        maintenance_layout = QVBoxLayout(maintenance_group)

        # Przycisk czyszczenia cache
        self.clear_cache_btn = QPushButton("Wyczyść cache miniatur")
        self.clear_cache_btn.clicked.connect(self._clear_thumbnail_cache)
        maintenance_layout.addWidget(self.clear_cache_btn)

        # Przycisk resetowania ustawień
        self.reset_settings_btn = QPushButton("Resetuj wszystkie ustawienia")
        self.reset_settings_btn.clicked.connect(self._reset_all_settings)
        maintenance_layout.addWidget(self.reset_settings_btn)

        layout.addWidget(maintenance_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Zaawansowane")

    def _create_button_box(self):
        """Tworzy przyciski na dole okna."""
        self.button_box = QWidget()
        layout = QHBoxLayout(self.button_box)

        # Przycisk Resetuj
        self.reset_btn = QPushButton("Resetuj")
        self.reset_btn.clicked.connect(self._reset_current_tab)
        layout.addWidget(self.reset_btn)

        layout.addStretch()

        # Przyciski OK, Anuluj, Zastosuj
        self.apply_btn = QPushButton("Zastosuj")
        self.apply_btn.clicked.connect(self._apply_settings)
        self.apply_btn.setEnabled(False)
        layout.addWidget(self.apply_btn)

        self.cancel_btn = QPushButton("Anuluj")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._accept_and_apply)
        self.ok_btn.setDefault(True)
        layout.addWidget(self.ok_btn)

    def _load_current_settings(self):
        """Ładuje aktualne ustawienia do kontrolek."""
        try:
            # Ogólne
            self.default_folder_edit.setText(
                self.app_config.get("default_working_directory", "")
            )
            self.export_folder_edit.setText(
                self.app_config.get("default_export_directory", "")
            )
            self.auto_save_metadata.setChecked(
                self.app_config.get("auto_save_metadata", True)
            )
            self.auto_load_last_folder.setChecked(
                self.app_config.get("auto_load_last_folder", True)
            )
            self.auto_backup_metadata.setChecked(
                self.app_config.get("auto_backup_metadata", False)
            )

            self.show_completion_messages.setChecked(
                self.app_config.get("show_completion_messages", True)
            )
            self.show_error_details.setChecked(
                self.app_config.get("show_error_details", True)
            )
            self.confirm_delete_operations.setChecked(
                self.app_config.get("confirm_delete_operations", True)
            )

            # Skanowanie
            strategy = self.app_config.get("pairing_strategy", "first_match")
            if strategy == "first_match":
                self.strategy_first_match.setChecked(True)
            elif strategy == "best_match":
                self.strategy_best_match.setChecked(True)
            else:
                self.strategy_size_priority.setChecked(True)

            self.max_depth_spin.setValue(self.app_config.get("max_scan_depth", -1))
            self.ignored_extensions_edit.setText(
                ",".join(self.app_config.get("ignored_extensions", []))
            )
            self.min_file_size_spin.setValue(self.app_config.get("min_file_size_kb", 0))
            self.enable_thumbnail_cache.setChecked(
                self.app_config.get("enable_thumbnail_cache", True)
            )
            self.cache_size_spin.setValue(
                self.app_config.get("thumbnail_cache_size_mb", 100)
            )

            # Interfejs
            self.default_thumbnail_size_slider.setValue(
                self.app_config.get("default_thumbnail_size", 200)
            )
            gallery_columns = str(self.app_config.get("gallery_columns", "Auto"))
            index = self.gallery_columns_combo.findText(gallery_columns)
            if index >= 0:
                self.gallery_columns_combo.setCurrentIndex(index)

            self.show_color_tags.setChecked(
                self.app_config.get("show_color_tags", True)
            )
            self.show_star_ratings.setChecked(
                self.app_config.get("show_star_ratings", True)
            )
            self.show_file_info.setChecked(self.app_config.get("show_file_info", True))

            # Zaawansowane
            log_level = self.app_config.get("log_level", "INFO")
            index = self.log_level_combo.findText(log_level)
            if index >= 0:
                self.log_level_combo.setCurrentIndex(index)

            self.enable_file_logging.setChecked(
                self.app_config.get("enable_file_logging", False)
            )
            self.worker_threads_spin.setValue(self.app_config.get("worker_threads", 4))
            self.enable_parallel_processing.setChecked(
                self.app_config.get("enable_parallel_processing", True)
            )
            self.confirm_file_operations.setChecked(
                self.app_config.get("confirm_file_operations", True)
            )
            self.backup_before_operations.setChecked(
                self.app_config.get("backup_before_operations", False)
            )
            self.safe_mode.setChecked(self.app_config.get("safe_mode", False))

            # Połącz sygnały do śledzenia zmian
            self._connect_change_signals()

        except Exception as e:
            logging.error(f"Błąd podczas ładowania ustawień: {e}")

    def _connect_change_signals(self):
        """Podłącza sygnały do śledzenia zmian w ustawieniach."""
        # Ogólne
        self.default_folder_edit.textChanged.connect(self._mark_changed)
        self.export_folder_edit.textChanged.connect(self._mark_changed)
        self.auto_save_metadata.toggled.connect(self._mark_changed)
        self.auto_load_last_folder.toggled.connect(self._mark_changed)
        self.auto_backup_metadata.toggled.connect(self._mark_changed)

        self.show_completion_messages.toggled.connect(self._mark_changed)
        self.show_error_details.toggled.connect(self._mark_changed)
        self.confirm_delete_operations.toggled.connect(self._mark_changed)

        # Skanowanie
        self.pairing_strategy_group.buttonToggled.connect(self._mark_changed)
        self.max_depth_spin.valueChanged.connect(self._mark_changed)
        self.ignored_extensions_edit.textChanged.connect(self._mark_changed)
        self.min_file_size_spin.valueChanged.connect(self._mark_changed)
        self.enable_thumbnail_cache.toggled.connect(self._mark_changed)
        self.cache_size_spin.valueChanged.connect(self._mark_changed)

        # Interfejs
        self.default_thumbnail_size_slider.valueChanged.connect(self._mark_changed)
        self.gallery_columns_combo.currentTextChanged.connect(self._mark_changed)
        self.show_color_tags.toggled.connect(self._mark_changed)
        self.show_star_ratings.toggled.connect(self._mark_changed)
        self.show_file_info.toggled.connect(self._mark_changed)

        # Zaawansowane
        self.log_level_combo.currentTextChanged.connect(self._mark_changed)
        self.enable_file_logging.toggled.connect(self._mark_changed)
        self.worker_threads_spin.valueChanged.connect(self._mark_changed)
        self.enable_parallel_processing.toggled.connect(self._mark_changed)
        self.confirm_file_operations.toggled.connect(self._mark_changed)
        self.backup_before_operations.toggled.connect(self._mark_changed)
        self.safe_mode.toggled.connect(self._mark_changed)

    def _mark_changed(self):
        """Oznacza że ustawienia zostały zmienione."""
        self.changes_made = True
        self.apply_btn.setEnabled(True)

    def _browse_default_folder(self):
        """Otwiera dialog wyboru domyślnego folderu."""
        folder = QFileDialog.getExistingDirectory(
            self, "Wybierz domyślny folder roboczy"
        )
        if folder:
            self.default_folder_edit.setText(folder)

    def _browse_export_folder(self):
        """Otwiera dialog wyboru folderu eksportu."""
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder eksportu")
        if folder:
            self.export_folder_edit.setText(folder)

    def _set_current_as_default(self):
        """Ustawia aktualny folder głównego okna jako domyślny."""
        if (
            hasattr(self.parent(), "controller")
            and self.parent().controller.current_directory
        ):
            current_folder = self.parent().controller.current_directory
            self.default_folder_edit.setText(current_folder)
            self._mark_changed()
            logging.info(
                f"🔒 RĘCZNE ustawienie domyślnego folderu na: {current_folder}"
            )
        else:
            QMessageBox.information(
                self, "Informacja", "Nie ma otwartego folderu do ustawienia!"
            )

    def _clear_thumbnail_cache(self):
        """Czyści cache miniatur."""
        reply = QMessageBox.question(
            self, "Potwierdź", "Czy na pewno chcesz wyczyścić cache miniatur?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Wyślij sygnał do parent window aby wyczyścił cache
                if self.parent() and hasattr(self.parent(), "gallery_manager"):
                    gallery_manager = self.parent().gallery_manager
                    if hasattr(gallery_manager, "thumbnail_cache"):
                        gallery_manager.thumbnail_cache.clear()

                QMessageBox.information(
                    self, "Sukces", "Cache miniatur został wyczyszczony."
                )
                logging.info("Cache miniatur wyczyszczony z okna preferencji")
            except Exception as e:
                logging.error(f"Błąd czyszczenia cache: {e}")
                QMessageBox.critical(self, "Błąd", f"Nie można wyczyścić cache: {e}")

    def _reset_all_settings(self):
        """Resetuje wszystkie ustawienia do wartości domyślnych."""
        reply = QMessageBox.question(
            self,
            "Potwierdź",
            "Czy na pewno chcesz zresetować wszystkie ustawienia?\n"
            "Ta operacja jest nieodwracalna.",
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Reset konfiguracji do domyślnych wartości
                if self.app_config.reset_to_defaults():
                    # Przeładuj wszystkie ustawienia w oknie
                    self._load_current_settings()
                    # Wyślij sygnał że preferencje się zmieniły
                    self.preferences_changed.emit()
                    self.changes_made = False
                    self.apply_btn.setEnabled(False)
                    QMessageBox.information(
                        self, "Sukces", "Ustawienia zostały zresetowane."
                    )
                    logging.info("Wszystkie ustawienia zresetowane do domyślnych")
                else:
                    QMessageBox.warning(
                        self, "Ostrzeżenie", "Nie udało się zapisać ustawień."
                    )
            except Exception as e:
                logging.error(f"Błąd resetowania ustawień: {e}")
                QMessageBox.critical(
                    self, "Błąd", f"Nie można zresetować ustawień: {e}"
                )

    def _reset_current_tab(self):
        """Resetuje ustawienia bieżącej zakładki."""
        current_tab = self.tab_widget.currentIndex()
        tab_name = self.tab_widget.tabText(current_tab)

        reply = QMessageBox.question(
            self,
            "Potwierdź",
            f"Czy na pewno chcesz zresetować ustawienia zakładki '{tab_name}'?",
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._load_current_settings()  # Reload wszystkich ustawień

    def _apply_settings(self):
        """Stosuje ustawienia bez zamykania okna."""
        try:
            self._save_settings()
            self.preferences_changed.emit()
            self.changes_made = False
            self.apply_btn.setEnabled(False)
            QMessageBox.information(self, "Sukces", "Ustawienia zostały zastosowane.")
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można zastosować ustawień: {e}")

    def _accept_and_apply(self):
        """Stosuje ustawienia i zamyka okno."""
        if self.changes_made:
            try:
                self._save_settings()
                self.preferences_changed.emit()
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Nie można zapisać ustawień: {e}")
                return
        self.accept()

    def _save_settings(self):
        """Zapisuje wszystkie ustawienia do konfiguracji."""
        # Ogólne
        self.app_config.set(
            "default_working_directory", self.default_folder_edit.text()
        )
        self.app_config.set("default_export_directory", self.export_folder_edit.text())
        self.app_config.set("auto_save_metadata", self.auto_save_metadata.isChecked())
        self.app_config.set(
            "auto_load_last_folder", self.auto_load_last_folder.isChecked()
        )
        self.app_config.set(
            "auto_backup_metadata", self.auto_backup_metadata.isChecked()
        )
        self.app_config.set(
            "show_completion_messages", self.show_completion_messages.isChecked()
        )
        self.app_config.set("show_error_details", self.show_error_details.isChecked())
        self.app_config.set(
            "confirm_delete_operations", self.confirm_delete_operations.isChecked()
        )

        # Skanowanie
        if self.strategy_first_match.isChecked():
            strategy = "first_match"
        elif self.strategy_best_match.isChecked():
            strategy = "best_match"
        else:
            strategy = "size_priority"
        self.app_config.set("pairing_strategy", strategy)

        self.app_config.set("max_scan_depth", self.max_depth_spin.value())
        extensions = [
            ext.strip()
            for ext in self.ignored_extensions_edit.text().split(",")
            if ext.strip()
        ]
        self.app_config.set("ignored_extensions", extensions)
        self.app_config.set("min_file_size_kb", self.min_file_size_spin.value())
        self.app_config.set(
            "enable_thumbnail_cache", self.enable_thumbnail_cache.isChecked()
        )
        self.app_config.set("thumbnail_cache_size_mb", self.cache_size_spin.value())

        # Interfejs
        self.app_config.set(
            "default_thumbnail_size", self.default_thumbnail_size_slider.value()
        )
        gallery_columns = self.gallery_columns_combo.currentText()
        if gallery_columns == "Auto":
            self.app_config.set("gallery_columns", "Auto")
        else:
            self.app_config.set("gallery_columns", int(gallery_columns))
        self.app_config.set("show_color_tags", self.show_color_tags.isChecked())
        self.app_config.set("show_star_ratings", self.show_star_ratings.isChecked())
        self.app_config.set("show_file_info", self.show_file_info.isChecked())

        # Zaawansowane
        self.app_config.set("log_level", self.log_level_combo.currentText())
        self.app_config.set("enable_file_logging", self.enable_file_logging.isChecked())
        self.app_config.set("worker_threads", self.worker_threads_spin.value())
        self.app_config.set(
            "enable_parallel_processing", self.enable_parallel_processing.isChecked()
        )
        self.app_config.set(
            "confirm_file_operations", self.confirm_file_operations.isChecked()
        )
        self.app_config.set(
            "backup_before_operations", self.backup_before_operations.isChecked()
        )
        self.app_config.set("safe_mode", self.safe_mode.isChecked())

        # Zapisz do pliku
        self.app_config.save()

    def closeEvent(self, event):
        """Obsługuje zamykanie okna."""
        if self.changes_made:
            reply = QMessageBox.question(
                self,
                "Niezapisane zmiany",
                "Masz niezapisane zmiany. Czy chcesz je zapisać?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )

            if reply == QMessageBox.StandardButton.Save:
                try:
                    self._save_settings()
                    self.preferences_changed.emit()
                    event.accept()
                except Exception as e:
                    QMessageBox.critical(
                        self, "Błąd", f"Nie można zapisać ustawień: {e}"
                    )
                    event.ignore()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
