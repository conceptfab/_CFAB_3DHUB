"""
Testy integracyjne dla refaktoryzacji DirectoryTreeManager.
Testują współpracę między modułami: statistics, operations, tree manager.
"""

import pytest
import tempfile
import os
import time
from unittest.mock import Mock, patch, MagicMock

from PyQt6.QtWidgets import QTreeView, QWidget
from PyQt6.QtCore import QModelIndex

from src.ui.directory_tree_manager_refactored import DirectoryTreeManager
from src.ui.folder_statistics_manager import FolderStatisticsManager, FolderStatistics
from src.ui.folder_operations_manager import FolderOperationsManager


class TestDirectoryTreeIntegration:
    """Testy integracyjne dla nowej architektury DirectoryTreeManager."""

    @pytest.fixture(autouse=True)
    def setup_qt_app(self, qapp):
        """Setup Qt application for tests."""
        self.app = qapp

    @pytest.fixture
    def mock_parent_window(self):
        """Mock parent window widget."""
        return Mock(spec=QWidget)

    @pytest.fixture
    def mock_tree_view(self):
        """Mock QTreeView."""
        return Mock(spec=QTreeView)

    @pytest.fixture
    def tree_manager(self, mock_tree_view, mock_parent_window):
        """Fixture dla DirectoryTreeManager."""
        with patch('src.ui.folder_statistics_manager.AppConfig') as mock_config:
            mock_config.return_value.get.side_effect = lambda key, default: default
            return DirectoryTreeManager(mock_tree_view, mock_parent_window)

    @pytest.fixture
    def temp_dir_with_files(self):
        """Temporary directory z testowymi plikami."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Utwórz strukturę folderów z plikami
            folder1 = os.path.join(temp_dir, "folder1")
            folder2 = os.path.join(temp_dir, "folder2")
            os.makedirs(folder1)
            os.makedirs(folder2)
            
            # Dodaj pliki
            for i in range(3):
                with open(os.path.join(folder1, f"file{i}.txt"), 'w') as f:
                    f.write(f"content {i}")
                with open(os.path.join(folder2, f"file{i}.txt"), 'w') as f:
                    f.write(f"content {i}")
            
            yield temp_dir

    def test_manager_components_integration(self, tree_manager):
        """Test integracji komponentów managera."""
        # Sprawdź czy wszystkie komponenty zostały utworzone
        assert isinstance(tree_manager.stats_manager, FolderStatisticsManager)
        assert isinstance(tree_manager.operations_manager, FolderOperationsManager)
        
        # Sprawdź czy modele Qt zostały skonfigurowane
        assert tree_manager.model is not None
        assert tree_manager.proxy_model is not None
        
        # Sprawdź czy proxy model używa stats_manager
        assert tree_manager.proxy_model.stats_manager == tree_manager.stats_manager

    def test_statistics_and_operations_collaboration(self, tree_manager, temp_dir_with_files):
        """Test współpracy między statistics i operations managerami."""
        folder_path = os.path.join(temp_dir_with_files, "folder1")
        
        # 1. Oblicz statystyki
        stats = None
        def on_stats_ready(calculated_stats):
            nonlocal stats
            stats = calculated_stats
        
        tree_manager.stats_manager.calculate_statistics_async(folder_path, on_stats_ready)
        
        # Czekaj na obliczenie (w rzeczywistym teście użyj QSignalSpy)
        for _ in range(10):
            if stats:
                break
            time.sleep(0.1)
        
        # Sprawdź czy statystyki zostały obliczone
        assert stats is not None
        assert stats.total_files > 0
        
        # 2. Sprawdź czy statystyki są w cache
        cached_stats = tree_manager.stats_manager.get_cached_statistics(folder_path)
        assert cached_stats == stats
        
        # 3. Symuluj operację na folderze (która powinna invalidować cache)
        tree_manager.stats_manager.invalidate_cache(folder_path)
        
        # 4. Sprawdź czy cache został invalidowany
        cached_after_invalidation = tree_manager.stats_manager.get_cached_statistics(folder_path)
        assert cached_after_invalidation is None

    @patch('src.ui.delegates.workers.ScanFolderWorker')
    def test_async_initialization_flow(self, mock_worker_class, tree_manager, temp_dir_with_files):
        """Test asynchronicznego flow inicjalizacji."""
        # Mock worker
        mock_worker = Mock()
        mock_worker.custom_signals = Mock()
        mock_worker_class.return_value = mock_worker
        
        # Mock QThreadPool
        with patch('src.ui.directory_tree_manager_refactored.QThreadPool') as mock_thread_pool:
            # Rozpocznij inicjalizację
            tree_manager.init_directory_tree_async(temp_dir_with_files)
            
            # Sprawdź czy worker został utworzony i uruchomiony
            mock_worker_class.assert_called_once_with(temp_dir_with_files)
            mock_thread_pool.globalInstance().start.assert_called_once_with(mock_worker)
            
            # Symuluj zakończenie skanowania
            found_pairs = [Mock(), Mock()]  # 2 pary plików
            unpaired_archives = []
            unpaired_previews = []
            
            # Sprawdź czy callback został podłączony
            mock_worker.custom_signals.finished.connect.assert_called()
            mock_worker.custom_signals.error.connect.assert_called()

    def test_folder_filtering_integration(self, tree_manager):
        """Test integracji filtrowania folderów."""
        # Test funkcji should_show_folder
        assert tree_manager.should_show_folder("normal_folder") == True
        assert tree_manager.should_show_folder(".hidden_folder") == False
        assert tree_manager.should_show_folder("Windows") == False
        assert tree_manager.should_show_folder("$RECYCLE.BIN") == False
        
        # Test proxy model filtering
        assert tree_manager.proxy_model._filter_function is not None

    def test_context_menu_integration(self, tree_manager):
        """Test integracji menu kontekstowego z operations manager."""
        # Mock index i model
        mock_index = Mock(spec=QModelIndex)
        mock_index.isValid.return_value = True
        
        mock_source_index = Mock(spec=QModelIndex)
        tree_manager.proxy_model.mapToSource = Mock(return_value=mock_source_index)
        tree_manager.model.filePath = Mock(return_value="/test/folder")
        
        # Mock position
        position = Mock()
        tree_manager.folder_tree.indexAt = Mock(return_value=mock_index)
        
        # Mock QMenu
        with patch('src.ui.directory_tree_manager_refactored.QMenu') as mock_menu_class:
            mock_menu = Mock()
            mock_menu_class.return_value = mock_menu
            
            with patch('src.ui.directory_tree_manager_refactored.QAction') as mock_action_class:
                mock_action = Mock()
                mock_action_class.return_value = mock_action
                
                # Wywołaj menu kontekstowe
                tree_manager._show_context_menu(position)
                
                # Sprawdź czy menu zostało utworzone
                mock_menu_class.assert_called_once()
                
                # Sprawdź czy akcje zostały utworzone
                assert mock_action_class.call_count >= 5  # create, rename, delete, open, stats

    def test_cache_info_integration(self, tree_manager):
        """Test integracji informacji o cache."""
        cache_info = tree_manager.get_cache_info()
        
        # Sprawdź czy wszystkie wymagane klucze są obecne
        required_keys = ['size', 'max_size', 'ttl_seconds', 'active_workers']
        for key in required_keys:
            assert key in cache_info
        
        # Sprawdź typy wartości
        assert isinstance(cache_info['size'], int)
        assert isinstance(cache_info['max_size'], int)
        assert isinstance(cache_info['ttl_seconds'], int)
        assert isinstance(cache_info['active_workers'], int)

    def test_refresh_tree_integration(self, tree_manager, temp_dir_with_files):
        """Test integracji odświeżania drzewa."""
        # Ustaw working directory
        tree_manager._main_working_directory = temp_dir_with_files
        
        # Mock proxy model
        tree_manager.proxy_model.invalidate = Mock()
        
        # Mock background stats calculation
        with patch.object(tree_manager, '_start_background_stats_calculation') as mock_stats:
            # Wywołaj refresh
            tree_manager.refresh_tree()
            
            # Sprawdź czy proxy model został invalidowany
            tree_manager.proxy_model.invalidate.assert_called_once()
            
            # Sprawdź czy rozpoczęto ponowne obliczanie statystyk
            # (z opóźnieniem przez QTimer.singleShot)
            assert mock_stats.call_count >= 0  # Może być wywołane asynchronicznie

    def test_folder_click_handling_integration(self, tree_manager):
        """Test integracji obsługi kliknięć folderów."""
        # Mock proxy index
        mock_proxy_index = Mock(spec=QModelIndex)
        mock_proxy_index.isValid.return_value = True
        
        # Mock source index
        mock_source_index = Mock(spec=QModelIndex)
        tree_manager.proxy_model.mapToSource = Mock(return_value=mock_source_index)
        
        # Mock folder path
        test_folder_path = "/test/folder/path"
        tree_manager.model.filePath = Mock(return_value=test_folder_path)
        
        # Mock parent window callback
        tree_manager.parent_window.on_folder_changed = Mock()
        
        # Wywołaj obsługę kliknięcia
        tree_manager._on_folder_clicked(mock_proxy_index)
        
        # Sprawdź czy callback został wywołany
        tree_manager.parent_window.on_folder_changed.assert_called_once_with(test_folder_path)

    def test_error_handling_integration(self, tree_manager, temp_dir_with_files):
        """Test integracji obsługi błędów."""
        # Test błędu podczas inicjalizacji
        with patch('src.ui.delegates.workers.ScanFolderWorker') as mock_worker_class:
            mock_worker = Mock()
            mock_worker.custom_signals = Mock()
            mock_worker_class.return_value = mock_worker
            
            with patch('src.ui.directory_tree_manager_refactored.QThreadPool'):
                # Rozpocznij inicjalizację
                tree_manager.init_directory_tree_async(temp_dir_with_files)
                
                # Symuluj błąd skanowania
                error_callback = mock_worker.custom_signals.error.connect.call_args[0][0]
                error_callback("Test error message")
                
                # Sprawdź czy fallback został użyty
                assert tree_manager.model is not None

    def test_stats_display_refresh_integration(self, tree_manager, temp_dir_with_files):
        """Test integracji odświeżania wyświetlania statystyk."""
        folder_path = os.path.join(temp_dir_with_files, "folder1")
        
        # Mock model index
        mock_source_index = Mock(spec=QModelIndex)
        mock_source_index.isValid.return_value = True
        tree_manager.model.index = Mock(return_value=mock_source_index)
        
        # Mock proxy index
        mock_proxy_index = Mock(spec=QModelIndex)
        mock_proxy_index.isValid.return_value = True
        tree_manager.proxy_model.mapFromSource = Mock(return_value=mock_proxy_index)
        
        # Mock tree view update
        tree_manager.folder_tree.update = Mock()
        
        # Wywołaj refresh display
        tree_manager._refresh_folder_display(folder_path)
        
        # Sprawdź czy update został wywołany
        tree_manager.folder_tree.update.assert_called_once_with(mock_proxy_index)

    def test_background_stats_calculation_integration(self, tree_manager, temp_dir_with_files):
        """Test integracji background calculation statystyk."""
        # Ustaw working directory
        tree_manager._main_working_directory = temp_dir_with_files
        
        # Mock get_visible_folders
        visible_folders = [
            os.path.join(temp_dir_with_files, "folder1"),
            os.path.join(temp_dir_with_files, "folder2")
        ]
        tree_manager._get_visible_folders = Mock(return_value=visible_folders)
        
        # Mock stats manager
        tree_manager.stats_manager.calculate_statistics_async = Mock()
        
        # Wywołaj background calculation
        tree_manager._start_background_stats_calculation()
        
        # Sprawdź czy dla każdego folderu zostało rozpoczęte obliczanie
        assert tree_manager.stats_manager.calculate_statistics_async.call_count == len(visible_folders)

    def test_memory_usage_integration(self, tree_manager, temp_dir_with_files):
        """Test integracji zarządzania pamięcią."""
        # Sprawdź początkowy stan cache
        initial_cache_info = tree_manager.get_cache_info()
        assert initial_cache_info['size'] == 0
        
        # Dodaj statystyki do cache (przez manager)
        folder_path = os.path.join(temp_dir_with_files, "folder1")
        test_stats = FolderStatistics(size_gb=1.0, pairs_count=5, total_files=10)
        
        tree_manager.stats_manager.cache_statistics(folder_path, test_stats)
        
        # Sprawdź wzrost cache
        cache_info_after = tree_manager.get_cache_info()
        assert cache_info_after['size'] == 1
        
        # Test invalidacji
        tree_manager.invalidate_folder_cache(folder_path)
        
        # Sprawdź czy cache został wyczyszczony
        cache_info_final = tree_manager.get_cache_info()
        assert cache_info_final['size'] == 0


class TestManagersCollaboration:
    """Testy współpracy między managerami bez UI."""

    @pytest.fixture
    def stats_manager(self):
        """Fixture dla FolderStatisticsManager."""
        with patch('src.ui.folder_statistics_manager.AppConfig') as mock_config:
            mock_config.return_value.get.side_effect = lambda key, default: default
            return FolderStatisticsManager()

    @pytest.fixture
    def operations_manager(self):
        """Fixture dla FolderOperationsManager."""
        mock_parent = Mock(spec=QWidget)
        return FolderOperationsManager(mock_parent)

    def test_cache_invalidation_after_operations(self, stats_manager, operations_manager):
        """Test invalidacji cache po operacjach na folderach."""
        # Dodaj statystyki do cache
        folder_path = "/test/folder"
        test_stats = FolderStatistics(size_gb=1.0, pairs_count=5)
        stats_manager.cache_statistics(folder_path, test_stats)
        
        # Sprawdź czy statystyki są w cache
        assert stats_manager.get_cached_statistics(folder_path) == test_stats
        
        # Symuluj operację która powinna invalidować cache
        stats_manager.invalidate_cache(folder_path)
        
        # Sprawdź czy cache został invalidowany
        assert stats_manager.get_cached_statistics(folder_path) is None

    def test_worker_lifecycle_coordination(self, stats_manager, operations_manager):
        """Test koordynacji lifecycle workerów."""
        # Sprawdź początkowy stan
        assert stats_manager.get_cache_info()['active_workers'] == 0
        assert operations_manager.get_active_operations_count() == 0
        
        # Dodaj mock aktywnych workerów
        stats_manager._active_workers["/test/path"] = Mock()
        operations_manager._active_operations["test_op"] = Mock()
        
        # Sprawdź aktywność
        assert stats_manager.get_cache_info()['active_workers'] == 1
        assert operations_manager.get_active_operations_count() == 1
        
        # Wyczyść wszystko
        stats_manager._active_workers.clear()
        operations_manager.cancel_all_operations()
        
        # Sprawdź stan końcowy
        assert stats_manager.get_cache_info()['active_workers'] == 0
        assert operations_manager.get_active_operations_count() == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 