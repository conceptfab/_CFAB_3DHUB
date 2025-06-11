"""
UI Manager - zarządzanie podstawowymi elementami interfejsu użytkownika.
Refaktoryzacja MainWindow ETAP 2 - wydzielenie komponentów UI.
"""

import logging
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.filter_panel import FilterPanel

logger = logging.getLogger(__name__)


class UIManager:
    """
    Manager odpowiedzialny za tworzenie i zarządzanie podstawowymi komponentami UI.
    Wydzielony z MainWindow dla lepszej organizacji kodu.
    """

    def __init__(self, main_window):
        """
        Inicjalizuje UI Manager.
        
        Args:
            main_window: Główne okno aplikacji (MainWindow)
        """
        self.main_window = main_window
        self.app_config = main_window.app_config
        
    def setup_status_bar(self) -> QStatusBar:
        """
        Tworzy i konfiguruje pasek statusu z progresem.
        
        Returns:
            QStatusBar: Skonfigurowany pasek statusu
        """
        status_bar = QStatusBar(self.main_window)
        
        # Pasek postępu
        progress_bar = QProgressBar()
        progress_bar.setFixedHeight(15)
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setVisible(False)
        
        # Etykieta postępu
        progress_label = QLabel("Gotowy")
        progress_label.setStyleSheet("color: gray; font-style: italic;")
        
        # Dodanie do paska statusu
        status_bar.addWidget(progress_label, 1)
        status_bar.addPermanentWidget(progress_bar, 2)
        
        # Zapisz referencje w main_window
        self.main_window.progress_bar = progress_bar
        self.main_window.progress_label = progress_label
        
        return status_bar
        
    def create_top_panel(self) -> QWidget:
        """
        Tworzy panel górny z przyciskami i kontrolkami.
        
        Returns:
            QWidget: Panel górny
        """
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # Przycisk wyboru folderu
        select_folder_button = QPushButton("Wybierz Folder Roboczy")
        select_folder_button.clicked.connect(self.main_window._select_working_directory)
        top_layout.addWidget(select_folder_button)
        
        # Przycisk czyszczenia cache
        clear_cache_button = QPushButton("Wyczyść Cache")
        clear_cache_button.clicked.connect(self.main_window._force_refresh)
        clear_cache_button.setVisible(False)  # Ukryty na start
        top_layout.addWidget(clear_cache_button)
        
        # Panel kontroli rozmiaru
        size_control_panel = self.create_size_control_panel()
        top_layout.addStretch(1)
        top_layout.addWidget(size_control_panel)
        
        # Zapisz referencje w main_window
        self.main_window.select_folder_button = select_folder_button
        self.main_window.clear_cache_button = clear_cache_button
        self.main_window.size_control_panel = size_control_panel
        
        return top_panel
        
    def create_size_control_panel(self) -> QWidget:
        """
        Tworzy panel kontroli rozmiaru miniatur.
        
        Returns:
            QWidget: Panel kontroli rozmiaru
        """
        size_control_panel = QWidget()
        size_control_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        layout = QHBoxLayout(size_control_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Label
        size_label = QLabel("Rozmiar miniatur:")
        layout.addWidget(size_label)
        
        # Suwak
        size_slider = QSlider()
        size_slider.setOrientation(Qt.Orientation.Horizontal)
        size_slider.setMinimum(0)
        size_slider.setMaximum(100)
        size_slider.setValue(self.main_window.initial_slider_position)
        size_slider.sliderReleased.connect(self.main_window._update_thumbnail_size)
        layout.addWidget(size_slider)
        
        # Zapisz referencje w main_window
        self.main_window.size_slider = size_slider
        
        return size_control_panel
        
    def create_bulk_operations_panel(self) -> QWidget:
        """
        Tworzy panel operacji masowych dla zaznaczonych kafelków.
        
        Returns:
            QWidget: Panel operacji masowych
        """
        bulk_panel = QWidget()
        bulk_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        bulk_panel.setVisible(False)  # Ukryty domyślnie
        
        # Stylowanie
        bulk_panel.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                margin: 2px;
            }
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #285a9b;
            }
            QLabel {
                color: #333;
                font-weight: bold;
            }
        """)
        
        layout = QHBoxLayout(bulk_panel)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Licznik zaznaczonych
        selected_count_label = QLabel("Zaznaczone: 0")
        layout.addWidget(selected_count_label)
        layout.addStretch(1)
        
        # Przyciski
        select_all_button = QPushButton("Zaznacz wszystkie")
        select_all_button.clicked.connect(self.main_window._select_all_tiles)
        layout.addWidget(select_all_button)
        
        clear_selection_button = QPushButton("Wyczyść zaznaczenie")
        clear_selection_button.clicked.connect(self.main_window._clear_all_selections)
        layout.addWidget(clear_selection_button)
        
        bulk_move_button = QPushButton("Przenieś zaznaczone")
        bulk_move_button.clicked.connect(self.main_window._perform_bulk_move)
        layout.addWidget(bulk_move_button)
        
        bulk_delete_button = QPushButton("Usuń zaznaczone")
        bulk_delete_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        bulk_delete_button.clicked.connect(self.main_window._perform_bulk_delete)
        layout.addWidget(bulk_delete_button)
        
        # Zapisz referencje w main_window
        self.main_window.bulk_operations_panel = bulk_panel
        self.main_window.selected_count_label = selected_count_label
        self.main_window.select_all_button = select_all_button
        self.main_window.clear_selection_button = clear_selection_button
        self.main_window.bulk_move_button = bulk_move_button
        self.main_window.bulk_delete_button = bulk_delete_button
        
        return bulk_panel
        
    def create_filter_panel(self) -> FilterPanel:
        """
        Tworzy panel filtrów.
        
        Returns:
            FilterPanel: Panel filtrów
        """
        filter_panel = FilterPanel()
        filter_panel.setVisible(True)  # Zawsze widoczny
        filter_panel.setEnabled(False)  # Ale zablokowany na start
        filter_panel.connect_signals(self.main_window._apply_filters_and_update_view)
        
        return filter_panel
        
    def create_tab_widget(self) -> QTabWidget:
        """
        Tworzy główny widget zakładek.
        
        Returns:
            QTabWidget: Widget zakładek
        """
        return QTabWidget()
        
    def update_progress(self, percent: int, message: str):
        """
        Aktualizuje pasek postępu.
        
        Args:
            percent: Procent postępu (0-100)
            message: Wiadomość do wyświetlenia
        """
        if hasattr(self.main_window, 'progress_bar') and hasattr(self.main_window, 'progress_label'):
            self.main_window.progress_bar.setValue(percent)
            self.main_window.progress_label.setText(message)
            
            if percent > 0:
                self.main_window.progress_bar.setVisible(True)
            else:
                self.main_window.progress_bar.setVisible(False)
                
    def hide_progress(self):
        """Ukrywa pasek postępu i resetuje etykietę."""
        if hasattr(self.main_window, 'progress_bar') and hasattr(self.main_window, 'progress_label'):
            self.main_window.progress_bar.setVisible(False)
            self.main_window.progress_label.setText("Gotowy")
            
    def update_bulk_operations_visibility(self):
        """Aktualizuje widoczność panelu operacji masowych."""
        if hasattr(self.main_window, 'bulk_operations_panel') and hasattr(self.main_window, 'selected_count_label'):
            has_selection = len(self.main_window.selected_tiles) > 0
            self.main_window.bulk_operations_panel.setVisible(has_selection)
            
            if has_selection:
                count = len(self.main_window.selected_tiles)
                self.main_window.selected_count_label.setText(f"Zaznaczone: {count}")
