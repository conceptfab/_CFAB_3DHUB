"""
Testy jednostkowe dla UIManager.
🚀 ETAP 1: Refaktoryzacja MainWindow - testy UI
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtWidgets import QApplication, QMainWindow
import sys

from src.ui.main_window.ui_manager import UIManager


class TestUIManager:
    """Testy dla klasy UIManager."""

    @pytest.fixture
    def app(self):
        """Fixture dla QApplication."""
        if not QApplication.instance():
            app = QApplication(sys.argv)
        else:
            app = QApplication.instance()
        yield app

    @pytest.fixture
    def mock_main_window(self, app):
        """Fixture dla mock głównego okna."""
        main_window = Mock(spec=QMainWindow)
        main_window.app_config = Mock()
        main_window.app_config.min_thumbnail_size = 100
        main_window.app_config.max_thumbnail_size = 400
        main_window.initial_slider_position = 50
        main_window.current_thumbnail_size = 250
        main_window.main_layout = Mock()
        main_window.menuBar = Mock()
        main_window.setStatusBar = Mock()
        main_window.close = Mock()
        return main_window

    @pytest.fixture
    def ui_manager(self, mock_main_window):
        """Fixture dla UIManager."""
        return UIManager(mock_main_window)

    def test_init(self, ui_manager, mock_main_window):
        """Test inicjalizacji UIManager."""
        assert ui_manager.main_window == mock_main_window
        assert ui_manager.logger is not None

    @patch('src.ui.main_window.ui_manager.QStatusBar')
    @patch('src.ui.main_window.ui_manager.QProgressBar')
    @patch('src.ui.main_window.ui_manager.QLabel')
    def test_setup_status_bar(self, mock_label, mock_progress_bar, mock_status_bar, ui_manager):
        """Test konfiguracji paska statusu."""
        # Arrange
        mock_status_bar_instance = Mock()
        mock_progress_bar_instance = Mock()
        mock_label_instance = Mock()
        
        mock_status_bar.return_value = mock_status_bar_instance
        mock_progress_bar.return_value = mock_progress_bar_instance
        mock_label.return_value = mock_label_instance

        # Act
        ui_manager._setup_status_bar()

        # Assert
        ui_manager.main_window.setStatusBar.assert_called_once_with(mock_status_bar_instance)
        mock_progress_bar_instance.setFixedHeight.assert_called_once_with(15)
        mock_progress_bar_instance.setRange.assert_called_once_with(0, 100)
        mock_progress_bar_instance.setValue.assert_called_once_with(0)
        mock_progress_bar_instance.setVisible.assert_called_once_with(False)

    @patch('src.ui.main_window.ui_manager.QAction')
    def test_setup_menu_bar(self, mock_qaction, ui_manager):
        """Test konfiguracji paska menu."""
        # Arrange
        mock_menubar = Mock()
        mock_file_menu = Mock()
        mock_help_menu = Mock()
        mock_action = Mock()
        
        ui_manager.main_window.menuBar.return_value = mock_menubar
        mock_menubar.addMenu.side_effect = [mock_file_menu, mock_help_menu]
        mock_qaction.return_value = mock_action

        # Act
        ui_manager._setup_menu_bar()

        # Assert
        mock_menubar.addMenu.assert_any_call("Plik")
        mock_menubar.addMenu.assert_any_call("Pomoc")
        assert mock_file_menu.addAction.call_count >= 3  # Preferencje, usuń metadane, wyjście
        assert mock_help_menu.addAction.call_count >= 1  # O programie
        assert mock_qaction.call_count >= 4  # 4 akcje: preferencje, usuń metadane, wyjście, o programie

    @patch('src.ui.main_window.ui_manager.QWidget')
    @patch('src.ui.main_window.ui_manager.QHBoxLayout')
    @patch('src.ui.main_window.ui_manager.QPushButton')
    def test_create_top_panel(self, mock_button, mock_layout, mock_widget, ui_manager):
        """Test tworzenia górnego panelu."""
        # Arrange
        mock_widget_instance = Mock()
        mock_layout_instance = Mock()
        mock_button_instance = Mock()
        
        mock_widget.return_value = mock_widget_instance
        mock_layout.return_value = mock_layout_instance
        mock_button.return_value = mock_button_instance

        # Act
        ui_manager._create_top_panel()

        # Assert
        mock_layout_instance.setContentsMargins.assert_called_once_with(5, 5, 5, 5)
        mock_layout_instance.addWidget.assert_called()
        ui_manager.main_window.main_layout.addWidget.assert_called_once_with(mock_widget_instance)

    @patch('src.ui.main_window.ui_manager.QSlider')
    @patch('src.ui.main_window.ui_manager.QLabel')
    def test_create_size_control_panel(self, mock_label, mock_slider, ui_manager):
        """Test tworzenia panelu kontroli rozmiaru."""
        # Arrange
        mock_parent_layout = Mock()
        mock_slider_instance = Mock()
        mock_label_instance = Mock()
        
        mock_slider.return_value = mock_slider_instance
        mock_label.return_value = mock_label_instance

        # Act
        ui_manager._create_size_control_panel(mock_parent_layout)

        # Assert
        mock_slider_instance.setRange.assert_called_once_with(0, 100)
        mock_slider_instance.setValue.assert_called_once_with(ui_manager.main_window.initial_slider_position)
        mock_slider_instance.setFixedWidth.assert_called_once_with(200)
        assert mock_parent_layout.addWidget.call_count >= 3  # Label, slider, value label

    def test_show_preferences_loaded_confirmation(self, ui_manager):
        """Test pokazywania potwierdzenia wczytania preferencji."""
        # Arrange
        ui_manager.main_window.status_bar = Mock()

        # Act
        ui_manager.show_preferences_loaded_confirmation()

        # Assert
        ui_manager.main_window.status_bar.showMessage.assert_called_once_with(
            "Preferencje zostały wczytane", 3000
        )

    @patch('src.ui.main_window.ui_manager.QMessageBox')
    def test_show_about(self, mock_message_box, ui_manager):
        """Test pokazywania okna o programie."""
        # Act
        ui_manager._show_about()

        # Assert
        mock_message_box.about.assert_called_once()
        args = mock_message_box.about.call_args[0]
        assert args[0] == ui_manager.main_window
        assert "CFAB_3DHUB" in args[1]
        assert "ETAP 1" in args[2]

    def test_init_ui_calls_all_setup_methods(self, ui_manager):
        """Test że init_ui wywołuje wszystkie metody konfiguracyjne."""
        # Arrange
        ui_manager._setup_status_bar = Mock()
        ui_manager._setup_menu_bar = Mock()
        ui_manager._create_top_panel = Mock()
        ui_manager._create_bulk_operations_panel = Mock()
        ui_manager._setup_tab_widget = Mock()
        ui_manager._init_managers = Mock()

        # Act
        ui_manager.init_ui()

        # Assert
        ui_manager._setup_status_bar.assert_called_once()
        ui_manager._setup_menu_bar.assert_called_once()
        ui_manager._create_top_panel.assert_called_once()
        ui_manager._create_bulk_operations_panel.assert_called_once()
        ui_manager._setup_tab_widget.assert_called_once()
        ui_manager._init_managers.assert_called_once()

    def test_error_handling_in_setup_status_bar(self, ui_manager, caplog):
        """Test obsługi błędów w setup_status_bar."""
        # Arrange - Mock QStatusBar to raise exception
        with patch('src.ui.main_window.ui_manager.QStatusBar') as mock_status_bar:
            mock_status_bar.side_effect = Exception("Test error")

            # Act
            ui_manager._setup_status_bar()

            # Assert
            assert "Błąd podczas konfiguracji paska statusu" in caplog.text

    @patch('src.ui.main_window.ui_manager.DirectoryTreeManager')
    @patch('src.ui.main_window.ui_manager.GalleryTab')
    @patch('src.ui.main_window.ui_manager.UnpairedFilesTab')
    @patch('src.ui.main_window.ui_manager.FileExplorerTab')
    def test_init_managers(self, mock_explorer_tab, mock_unpaired_tab, mock_gallery_tab, 
                          mock_directory_manager, ui_manager):
        """Test inicjalizacji managerów i zakładek."""
        # Arrange
        ui_manager.main_window.tab_widget = Mock()
        
        mock_gallery_instance = Mock()
        mock_unpaired_instance = Mock()
        mock_explorer_instance = Mock()
        
        mock_gallery_tab.return_value = mock_gallery_instance
        mock_unpaired_tab.return_value = mock_unpaired_instance
        mock_explorer_tab.return_value = mock_explorer_instance
        
        mock_gallery_instance.create_gallery_tab.return_value = Mock()
        mock_unpaired_instance.create_unpaired_files_tab.return_value = Mock()
        mock_explorer_instance.create_file_explorer_tab.return_value = Mock()

        # Act
        ui_manager._init_managers()

        # Assert
        mock_directory_manager.assert_called_once_with(ui_manager.main_window)
        mock_gallery_tab.assert_called_once_with(ui_manager.main_window)
        mock_unpaired_tab.assert_called_once_with(ui_manager.main_window)
        mock_explorer_tab.assert_called_once_with(ui_manager.main_window)
        
        assert ui_manager.main_window.tab_widget.addTab.call_count == 3 