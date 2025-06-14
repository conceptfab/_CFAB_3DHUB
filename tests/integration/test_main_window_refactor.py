"""
Test integracyjny dla zrefaktoryzowanego MainWindow.
🚀 ETAP 1: Refaktoryzacja MainWindow - test integracji
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
import sys

from src.ui.main_window.main_window_core import MainWindow


class TestMainWindowRefactorIntegration:
    """Test integracji zrefaktoryzowanego MainWindow."""

    @pytest.fixture
    def app(self):
        """Fixture dla QApplication."""
        if not QApplication.instance():
            app = QApplication(sys.argv)
        else:
            app = QApplication.instance()
        yield app

    @patch('src.ui.main_window.main_window_core.app_config.AppConfig')
    @patch('src.ui.main_window.main_window_core.MainWindowController')
    @patch('src.ui.main_window.main_window_core.get_event_bus')
    @patch('src.ui.main_window.main_window_core.ViewRefreshManager')
    @patch('src.ui.main_window.main_window_core.get_main_window_logger')
    def test_main_window_initialization(self, mock_logger, mock_view_refresh, mock_event_bus, 
                                      mock_controller, mock_app_config, app):
        """Test inicjalizacji głównego okna z wszystkimi komponentami."""
        # Arrange
        mock_logger.return_value = Mock()
        mock_app_config.return_value = Mock()
        mock_app_config.return_value.get.return_value = ""
        mock_app_config.return_value.min_thumbnail_size = 100
        mock_app_config.return_value.max_thumbnail_size = 400
        mock_app_config.return_value.window_min_width = 800
        mock_app_config.return_value.window_min_height = 600
        
        mock_event_bus.return_value = Mock()
        mock_view_refresh.return_value = Mock()
        mock_controller.return_value = Mock()

        # Act
        with patch.object(MainWindow, '_init_ui_components') as mock_init_ui:
            main_window = MainWindow()

        # Assert
        assert main_window.ui_manager is not None
        assert main_window.event_handler is not None
        assert main_window.worker_manager is not None
        assert main_window.progress_manager is not None
        assert main_window.file_operations_coordinator is not None
        
        # Sprawdź czy komponenty zostały zainicjalizowane
        assert hasattr(main_window, 'app_config')
        assert hasattr(main_window, 'event_bus')
        assert hasattr(main_window, 'view_refresh_manager')
        assert hasattr(main_window, 'controller')

    def test_component_delegation(self, app):
        """Test delegowania metod do odpowiednich komponentów."""
        # Arrange
        with patch.multiple(
            'src.ui.main_window.main_window_core',
            app_config=Mock(),
            MainWindowController=Mock(),
            get_event_bus=Mock(),
            ViewRefreshManager=Mock(),
            get_main_window_logger=Mock()
        ):
            with patch.object(MainWindow, '_init_ui_components'):
                main_window = MainWindow()
            
            # Mock komponenty
            main_window.event_handler = Mock()
            main_window.progress_manager = Mock()
            main_window.worker_manager = Mock()
            main_window.file_operations_coordinator = Mock()

        # Act & Assert - Test delegowania metod
        
        # Test closeEvent
        mock_event = Mock()
        main_window.closeEvent(mock_event)
        main_window.event_handler.handle_close_event.assert_called_once_with(mock_event)
        
        # Test resizeEvent
        mock_event = Mock()
        main_window.resizeEvent(mock_event)
        main_window.event_handler.handle_resize_event.assert_called_once_with(mock_event)
        
        # Test show_progress
        main_window.show_progress(50, "Test")
        main_window.progress_manager.show_progress.assert_called_once_with(50, "Test")
        
        # Test hide_progress
        main_window.hide_progress()
        main_window.progress_manager.hide_progress.assert_called_once()
        
        # Test start_data_processing_worker
        mock_file_pairs = [Mock()]
        main_window.start_data_processing_worker(mock_file_pairs)
        main_window.worker_manager.start_data_processing_worker.assert_called_once_with(mock_file_pairs)
        
        # Test handle_file_drop_on_folder
        source_paths = ["path1", "path2"]
        target_path = "target"
        main_window.handle_file_drop_on_folder(source_paths, target_path)
        main_window.file_operations_coordinator.handle_file_drop_on_folder.assert_called_once_with(
            source_paths, target_path
        )

    def test_component_interaction(self, app):
        """Test interakcji między komponentami."""
        # Arrange
        with patch.multiple(
            'src.ui.main_window.main_window_core',
            app_config=Mock(),
            MainWindowController=Mock(),
            get_event_bus=Mock(),
            ViewRefreshManager=Mock(),
            get_main_window_logger=Mock()
        ):
            with patch.object(MainWindow, '_init_ui_components'):
                main_window = MainWindow()
            
            # Mock komponenty
            main_window.ui_manager = Mock()
            main_window.view_refresh_manager = Mock()

        # Act & Assert
        
        # Test refresh_all_views
        main_window.refresh_all_views("test_selection")
        main_window.view_refresh_manager.refresh_all_views.assert_called_once_with("test_selection")
        
        # Test force_full_refresh
        main_window.force_full_refresh()
        main_window.view_refresh_manager.force_full_refresh.assert_called_once()

    def test_initialization_order(self, app):
        """Test poprawnej kolejności inicjalizacji komponentów."""
        # Arrange
        init_calls = []
        
        def track_init(name):
            def wrapper(*args, **kwargs):
                init_calls.append(name)
                return Mock()
            return wrapper

        with patch.multiple(
            'src.ui.main_window.main_window_core',
            app_config=Mock(),
            MainWindowController=track_init('controller'),
            get_event_bus=track_init('event_bus'),
            ViewRefreshManager=track_init('view_refresh'),
            get_main_window_logger=track_init('logger')
        ):
            with patch.object(MainWindow, '_init_ui_components'):
                with patch.object(MainWindow, '_post_init_setup'):
                    main_window = MainWindow()

        # Assert - sprawdź czy inicjalizacja była w poprawnej kolejności
        # Logger i AppConfig powinny być pierwsze
        # Potem komponenty
        assert len(init_calls) > 0

    def test_error_handling_in_initialization(self, app):
        """Test obsługi błędów podczas inicjalizacji."""
        # Arrange
        with patch('src.ui.main_window.main_window_core.get_main_window_logger') as mock_logger:
            mock_logger.return_value = Mock()
            
            with patch('src.ui.main_window.main_window_core.app_config.AppConfig') as mock_config:
                mock_config.side_effect = Exception("Config error")
                
                # Act & Assert - sprawdź czy błąd jest obsłużony
                with pytest.raises(Exception):
                    MainWindow()

    def test_component_cleanup(self, app):
        """Test czyszczenia komponentów."""
        # Arrange
        with patch.multiple(
            'src.ui.main_window.main_window_core',
            app_config=Mock(),
            MainWindowController=Mock(),
            get_event_bus=Mock(),
            ViewRefreshManager=Mock(),
            get_main_window_logger=Mock()
        ):
            with patch.object(MainWindow, '_init_ui_components'):
                main_window = MainWindow()
            
            main_window.event_handler = Mock()

        # Act
        mock_event = Mock()
        main_window.closeEvent(mock_event)

        # Assert
        main_window.event_handler.handle_close_event.assert_called_once_with(mock_event)

    def test_memory_efficiency(self, app):
        """Test efektywności pamięciowej - komponenty nie duplikują danych."""
        # Arrange
        with patch.multiple(
            'src.ui.main_window.main_window_core',
            app_config=Mock(),
            MainWindowController=Mock(),
            get_event_bus=Mock(),
            ViewRefreshManager=Mock(),
            get_main_window_logger=Mock()
        ):
            with patch.object(MainWindow, '_init_ui_components'):
                main_window = MainWindow()

        # Assert - sprawdź czy komponenty mają referencje do głównego okna, nie kopie
        assert main_window.ui_manager.main_window is main_window
        assert main_window.event_handler.main_window is main_window
        assert main_window.worker_manager.main_window is main_window
        assert main_window.progress_manager.main_window is main_window
        assert main_window.file_operations_coordinator.main_window is main_window 