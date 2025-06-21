"""
Testy dla wydzielonych komponentów DirectoryTreeManager.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, MagicMock, patch

from PyQt6.QtCore import QModelIndex
from PyQt6.QtWidgets import QApplication, QTreeView
from PyQt6.QtGui import QFileSystemModel

from src.ui.directory_tree.drag_drop_handler import DirectoryTreeDragDropHandler
from src.ui.directory_tree.operations_manager import DirectoryTreeOperationsManager
from src.ui.directory_tree.stats_manager import DirectoryTreeStatsManager
from src.ui.directory_tree.ui_handler import DirectoryTreeUIHandler


class TestDirectoryTreeDragDropHandler:
    """Testy dla DirectoryTreeDragDropHandler."""

    def setup_method(self):
        """Konfiguracja przed każdym testem."""
        self.mock_manager = Mock()
        self.mock_manager.folder_tree = Mock(spec=QTreeView)
        self.handler = DirectoryTreeDragDropHandler(self.mock_manager)

    def test_initialization(self):
        """Test inicjalizacji handlera."""
        assert self.handler.manager == self.mock_manager
        assert self.handler.folder_tree == self.mock_manager.folder_tree
        assert self.handler._highlighted_drop_target is None

    def test_setup_drag_and_drop_handlers(self):
        """Test konfiguracji drag and drop handlers."""
        self.handler.setup_drag_and_drop_handlers()
        
        # Sprawdź czy handlery zostały przypisane
        assert hasattr(self.mock_manager.folder_tree, 'dragEnterEvent')
        assert hasattr(self.mock_manager.folder_tree, 'dragMoveEvent')
        assert hasattr(self.mock_manager.folder_tree, 'dragLeaveEvent')
        assert hasattr(self.mock_manager.folder_tree, 'dropEvent')

    def test_get_highlighted_drop_target(self):
        """Test pobierania podświetlonego celu."""
        # Test gdy brak celu
        assert self.handler.get_highlighted_drop_target() is None
        
        # Test gdy cel jest ustawiony
        self.handler._highlighted_drop_target = "/test/path"
        assert self.handler.get_highlighted_drop_target() == "/test/path"


class TestDirectoryTreeOperationsManager:
    """Testy dla DirectoryTreeOperationsManager."""

    def setup_method(self):
        """Konfiguracja przed każdym testem."""
        self.mock_manager = Mock()
        self.mock_manager.parent_window = Mock()
        self.mock_manager.worker_factory = Mock()
        self.operations_manager = DirectoryTreeOperationsManager(self.mock_manager)

    def test_initialization(self):
        """Test inicjalizacji operations manager."""
        assert self.operations_manager.manager == self.mock_manager
        assert self.operations_manager.parent_window == self.mock_manager.parent_window
        assert self.operations_manager.worker_factory == self.mock_manager.worker_factory


class TestDirectoryTreeStatsManager:
    """Testy dla DirectoryTreeStatsManager."""

    def setup_method(self):
        """Konfiguracja przed każdym testem."""
        self.mock_manager = Mock()
        self.mock_manager.parent_window = Mock()
        self.mock_manager.data_manager = Mock()
        self.mock_manager.worker_coordinator = Mock()
        self.mock_manager._main_working_directory = "/test/dir"
        self.stats_manager = DirectoryTreeStatsManager(self.mock_manager)

    def test_initialization(self):
        """Test inicjalizacji stats manager."""
        assert self.stats_manager.manager == self.mock_manager
        assert self.stats_manager.parent_window == self.mock_manager.parent_window
        assert self.stats_manager.data_manager == self.mock_manager.data_manager
        assert self.stats_manager.worker_coordinator == self.mock_manager.worker_coordinator

    def test_get_visible_folders_empty_directory(self):
        """Test pobierania widocznych folderów gdy brak katalogu."""
        self.mock_manager._main_working_directory = None
        result = self.stats_manager._get_visible_folders()
        assert result == []

    def test_get_visible_folders_with_directory(self):
        """Test pobierania widocznych folderów z katalogu."""
        # Mock data_manager
        mock_folders = ["/test/folder1", "/test/folder2"]
        self.mock_manager.data_manager.get_visible_folders.return_value = mock_folders
        
        result = self.stats_manager._get_visible_folders()
        
        # Sprawdź czy data_manager został wywołany
        self.mock_manager.data_manager.get_visible_folders.assert_called_once()
        assert result == mock_folders


class TestDirectoryTreeUIHandler:
    """Testy dla DirectoryTreeUIHandler."""

    def setup_method(self):
        """Konfiguracja przed każdym testem."""
        self.mock_manager = Mock()
        self.mock_manager.parent_window = Mock()
        self.mock_manager.folder_tree = Mock(spec=QTreeView)
        self.ui_handler = DirectoryTreeUIHandler(self.mock_manager)

    def test_initialization(self):
        """Test inicjalizacji UI handler."""
        assert self.ui_handler.manager == self.mock_manager
        assert self.ui_handler.parent_window == self.mock_manager.parent_window
        assert self.ui_handler.folder_tree == self.mock_manager.folder_tree

    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_open_folder_in_explorer_invalid_path(self, mock_isdir, mock_exists):
        """Test otwierania nieistniejącego folderu w eksploratorze."""
        mock_exists.return_value = False
        
        # Test nie powinien wywołać subprocess
        with patch('subprocess.Popen') as mock_popen:
            self.ui_handler.open_folder_in_explorer("/nonexistent/path")
            mock_popen.assert_not_called()

    def test_create_expand_collapse_buttons(self):
        """Test tworzenia przycisków rozwijania/zwijania."""
        expand_btn, collapse_btn = self.ui_handler.create_expand_collapse_buttons()
        
        # Sprawdź czy przyciski zostały utworzone
        assert expand_btn is not None
        assert collapse_btn is not None
        
        # Sprawdź tekst przycisków
        assert "Rozwiń" in expand_btn.text()
        assert "Zwiń" in collapse_btn.text()


class TestComponentIntegration:
    """Testy integracyjne komponentów."""

    def test_components_work_together(self):
        """Test czy komponenty współpracują ze sobą."""
        # Symuluj główny manager
        mock_manager = Mock()
        mock_manager.folder_tree = Mock(spec=QTreeView)
        mock_manager.parent_window = Mock()
        mock_manager.data_manager = Mock()
        mock_manager.worker_coordinator = Mock()
        mock_manager._main_working_directory = "/test"
        
        # Utwórz wszystkie komponenty
        drag_drop = DirectoryTreeDragDropHandler(mock_manager)
        operations = DirectoryTreeOperationsManager(mock_manager)
        stats = DirectoryTreeStatsManager(mock_manager)
        ui = DirectoryTreeUIHandler(mock_manager)
        
        # Sprawdź czy wszystkie komponenty mają referencję do managera
        assert drag_drop.manager == mock_manager
        assert operations.manager == mock_manager
        assert stats.manager == mock_manager
        assert ui.manager == mock_manager


if __name__ == "__main__":
    # Uruchom testy
    pytest.main([__file__, "-v"])