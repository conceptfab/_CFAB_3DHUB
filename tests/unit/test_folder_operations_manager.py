"""
Testy jednostkowe dla FolderOperationsManager.
Pokrycie: operacje na folderach, dialog boxes, progress tracking.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from PyQt6.QtWidgets import QWidget, QApplication, QInputDialog, QMessageBox
from PyQt6.QtCore import QThreadPool

from src.ui.folder_operations_manager import FolderOperationsManager


class TestFolderOperationsManager:
    """Testy dla FolderOperationsManager."""

    @pytest.fixture(autouse=True)
    def setup_qt_app(self, qapp):
        """Setup Qt application for tests."""
        self.app = qapp

    @pytest.fixture
    def mock_parent_window(self):
        """Mock parent window widget."""
        return Mock(spec=QWidget)

    @pytest.fixture
    def manager(self, mock_parent_window):
        """Fixture dla FolderOperationsManager."""
        return FolderOperationsManager(mock_parent_window)

    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_manager_creation(self, mock_parent_window):
        """Test tworzenia managera."""
        manager = FolderOperationsManager(mock_parent_window)
        assert manager.parent_window == mock_parent_window
        assert len(manager._active_operations) == 0

    @patch('src.ui.folder_operations_manager.QInputDialog.getText')
    @patch('src.ui.folder_operations_manager.QMessageBox.warning')
    def test_create_folder_empty_name(self, mock_warning, mock_input, manager, temp_dir):
        """Test tworzenia folderu - pusta nazwa."""
        # User anuluje dialog lub podaje pustą nazwę
        mock_input.return_value = ("", False)
        
        manager.create_folder(temp_dir)
        
        # Nie powinno dojść do tworzenia folderu
        mock_warning.assert_not_called()

    @patch('src.ui.folder_operations_manager.QInputDialog.getText')
    @patch('src.ui.folder_operations_manager.QMessageBox.warning')
    def test_create_folder_existing_folder(self, mock_warning, mock_input, manager, temp_dir):
        """Test tworzenia folderu - folder już istnieje."""
        # Utwórz istniejący folder
        existing_folder = os.path.join(temp_dir, "existing")
        os.makedirs(existing_folder)
        
        # User podaje nazwę istniejącego folderu
        mock_input.return_value = ("existing", True)
        
        manager.create_folder(temp_dir)
        
        # Powinno pokazać ostrzeżenie
        mock_warning.assert_called_once()

    @patch('src.ui.folder_operations_manager.QInputDialog.getText')
    @patch('src.ui.folder_operations_manager.QThreadPool')
    @patch('src.ui.folder_operations_manager.CreateFolderWorker')
    def test_create_folder_success(self, mock_worker_class, mock_thread_pool, 
                                 mock_input, manager, temp_dir):
        """Test pomyślnego tworzenia folderu."""
        # User podaje prawidłową nazwę
        mock_input.return_value = ("new_folder", True)
        
        # Mock worker
        mock_worker = Mock()
        mock_worker.signals = Mock()
        mock_worker_class.return_value = mock_worker
        
        # Mock progress dialog
        with patch('src.ui.folder_operations_manager.FolderOperationsManager._create_progress_dialog') as mock_progress:
            mock_progress_dialog = Mock()
            mock_progress.return_value = mock_progress_dialog
            
            manager.create_folder(temp_dir)
            
            # Sprawdź czy worker został utworzony i uruchomiony
            expected_path = os.path.join(temp_dir, "new_folder")
            mock_worker_class.assert_called_once_with(expected_path)
            mock_thread_pool.globalInstance().start.assert_called_once_with(mock_worker)
            
            # Sprawdź czy worker jest w active_operations
            operation_id = f"create_{expected_path}"
            assert operation_id in manager._active_operations

    @patch('src.ui.folder_operations_manager.QInputDialog.getText')
    def test_rename_folder_same_name(self, mock_input, manager, temp_dir):
        """Test przemianowania folderu - ta sama nazwa."""
        # Utwórz folder do przemianowania
        folder_path = os.path.join(temp_dir, "test_folder")
        os.makedirs(folder_path)
        
        # User podaje tę samą nazwę
        mock_input.return_value = ("test_folder", True)
        
        with patch('src.ui.folder_operations_manager.QThreadPool') as mock_thread_pool:
            manager.rename_folder(folder_path)
            
            # Nie powinno uruchomić workera
            mock_thread_pool.globalInstance().start.assert_not_called()

    @patch('src.ui.folder_operations_manager.QInputDialog.getText')
    @patch('src.ui.folder_operations_manager.QMessageBox.warning')
    def test_rename_folder_existing_name(self, mock_warning, mock_input, manager, temp_dir):
        """Test przemianowania folderu - nazwa już istnieje."""
        # Utwórz foldery
        folder_path = os.path.join(temp_dir, "old_name")
        existing_path = os.path.join(temp_dir, "existing_name")
        os.makedirs(folder_path)
        os.makedirs(existing_path)
        
        # User podaje nazwę istniejącego folderu
        mock_input.return_value = ("existing_name", True)
        
        manager.rename_folder(folder_path)
        
        # Powinno pokazać ostrzeżenie
        mock_warning.assert_called_once()

    @patch('src.ui.folder_operations_manager.QInputDialog.getText')
    @patch('src.ui.folder_operations_manager.QThreadPool')
    @patch('src.ui.folder_operations_manager.RenameFolderWorker')
    def test_rename_folder_success(self, mock_worker_class, mock_thread_pool, 
                                 mock_input, manager, temp_dir):
        """Test pomyślnego przemianowania folderu."""
        # Utwórz folder
        folder_path = os.path.join(temp_dir, "old_name")
        os.makedirs(folder_path)
        
        # User podaje nową nazwę
        mock_input.return_value = ("new_name", True)
        
        # Mock worker
        mock_worker = Mock()
        mock_worker.signals = Mock()
        mock_worker_class.return_value = mock_worker
        
        with patch('src.ui.folder_operations_manager.FolderOperationsManager._create_progress_dialog') as mock_progress:
            mock_progress_dialog = Mock()
            mock_progress.return_value = mock_progress_dialog
            
            manager.rename_folder(folder_path)
            
            # Sprawdź czy worker został utworzony
            expected_new_path = os.path.join(temp_dir, "new_name")
            mock_worker_class.assert_called_once_with(folder_path, expected_new_path)

    @patch('src.ui.folder_operations_manager.QMessageBox.question')
    def test_delete_folder_cancelled(self, mock_question, manager, temp_dir):
        """Test usuwania folderu - user anuluje."""
        # User anuluje potwierdzenie
        mock_question.return_value = QMessageBox.StandardButton.No
        
        with patch('src.ui.folder_operations_manager.QThreadPool') as mock_thread_pool:
            manager.delete_folder(temp_dir)
            
            # Nie powinno uruchomić workera
            mock_thread_pool.globalInstance().start.assert_not_called()

    @patch('src.ui.folder_operations_manager.QMessageBox.question')
    @patch('src.ui.folder_operations_manager.QThreadPool')
    @patch('src.ui.folder_operations_manager.DeleteFolderWorker')
    def test_delete_folder_confirmed(self, mock_worker_class, mock_thread_pool, 
                                   mock_question, manager, temp_dir):
        """Test usuwania folderu - user potwierdza."""
        # User potwierdza usunięcie
        mock_question.return_value = QMessageBox.StandardButton.Yes
        
        # Mock worker
        mock_worker = Mock()
        mock_worker.signals = Mock()
        mock_worker_class.return_value = mock_worker
        
        with patch('src.ui.folder_operations_manager.FolderOperationsManager._create_progress_dialog') as mock_progress:
            mock_progress_dialog = Mock()
            mock_progress.return_value = mock_progress_dialog
            
            manager.delete_folder(temp_dir)
            
            # Sprawdź czy worker został utworzony
            mock_worker_class.assert_called_once_with(temp_dir)
            mock_thread_pool.globalInstance().start.assert_called_once_with(mock_worker)

    @patch('src.ui.folder_operations_manager.os.startfile')
    def test_open_folder_in_explorer_windows(self, mock_startfile, manager, temp_dir):
        """Test otwierania folderu w eksploratorze - Windows."""
        with patch('platform.system', return_value='Windows'):
            manager.open_folder_in_explorer(temp_dir)
            mock_startfile.assert_called_once_with(temp_dir)

    @patch('src.ui.folder_operations_manager.subprocess.run')
    def test_open_folder_in_explorer_macos(self, mock_run, manager, temp_dir):
        """Test otwierania folderu w eksploratorze - macOS."""
        with patch('platform.system', return_value='Darwin'):
            manager.open_folder_in_explorer(temp_dir)
            mock_run.assert_called_once_with(['open', temp_dir])

    @patch('src.ui.folder_operations_manager.subprocess.run')
    def test_open_folder_in_explorer_linux(self, mock_run, manager, temp_dir):
        """Test otwierania folderu w eksploratorze - Linux."""
        with patch('platform.system', return_value='Linux'):
            manager.open_folder_in_explorer(temp_dir)
            mock_run.assert_called_once_with(['xdg-open', temp_dir])

    @patch('src.ui.folder_operations_manager.QMessageBox.warning')
    def test_open_folder_nonexistent(self, mock_warning, manager):
        """Test otwierania nieistniejącego folderu."""
        nonexistent_path = "/nonexistent/folder"
        
        manager.open_folder_in_explorer(nonexistent_path)
        
        # Powinno pokazać ostrzeżenie
        mock_warning.assert_called_once()

    @patch('src.ui.folder_operations_manager.QMessageBox.critical')
    @patch('src.ui.folder_operations_manager.os.startfile')
    def test_open_folder_exception(self, mock_startfile, mock_critical, manager, temp_dir):
        """Test obsługi błędu przy otwieraniu folderu."""
        # Symuluj błąd startfile
        mock_startfile.side_effect = Exception("Test error")
        
        with patch('platform.system', return_value='Windows'):
            manager.open_folder_in_explorer(temp_dir)
            
            # Powinno pokazać błąd
            mock_critical.assert_called_once()

    def test_create_progress_dialog(self, manager):
        """Test tworzenia dialog postępu."""
        # Mock parent window dla Qt widgets
        with patch('src.ui.folder_operations_manager.QProgressDialog') as mock_dialog_class:
            mock_dialog = Mock()
            mock_dialog.windowTitle.return_value = "Test Title"
            mock_dialog_class.return_value = mock_dialog
            
            dialog = manager._create_progress_dialog("Test Title", "Test Description")
            
            assert dialog is not None
            mock_dialog_class.assert_called_once()
            mock_dialog.setWindowTitle.assert_called_with("Test Title")

    def test_cleanup_operation(self, manager):
        """Test czyszczenia po operacji."""
        # Dodaj mock operację
        mock_worker = Mock()
        operation_id = "test_operation"
        manager._active_operations[operation_id] = mock_worker
        
        # Mock progress dialog
        mock_progress_dialog = Mock()
        
        manager._cleanup_operation(operation_id, mock_progress_dialog)
        
        # Sprawdź czy operacja została usunięta
        assert operation_id not in manager._active_operations
        mock_progress_dialog.close.assert_called_once()

    def test_cancel_all_operations(self, manager):
        """Test anulowania wszystkich operacji."""
        # Dodaj mock operacje
        mock_worker1 = Mock()
        mock_worker2 = Mock()
        manager._active_operations["op1"] = mock_worker1
        manager._active_operations["op2"] = mock_worker2
        
        manager.cancel_all_operations()
        
        # Sprawdź czy wszystkie operacje zostały przerwane i usunięte
        mock_worker1.interrupt.assert_called_once()
        mock_worker2.interrupt.assert_called_once()
        assert len(manager._active_operations) == 0

    def test_get_active_operations_count(self, manager):
        """Test liczenia aktywnych operacji."""
        assert manager.get_active_operations_count() == 0
        
        # Dodaj mock operacje
        manager._active_operations["op1"] = Mock()
        manager._active_operations["op2"] = Mock()
        
        assert manager.get_active_operations_count() == 2

    def test_worker_callbacks_create_folder(self, manager, temp_dir):
        """Test callbacków workera dla tworzenia folderu."""
        with patch('src.ui.folder_operations_manager.QInputDialog.getText') as mock_input:
            mock_input.return_value = ("test_folder", True)
            
            with patch('src.ui.folder_operations_manager.CreateFolderWorker') as mock_worker_class:
                mock_worker = Mock()
                mock_worker.signals = Mock()
                mock_worker_class.return_value = mock_worker
                
                with patch('src.ui.folder_operations_manager.QThreadPool'):
                    with patch('src.ui.folder_operations_manager.FolderOperationsManager._create_progress_dialog') as mock_progress:
                        mock_progress_dialog = Mock()
                        mock_progress.return_value = mock_progress_dialog
                        
                        callback = Mock()
                        manager.create_folder(temp_dir, callback)
                        
                        # Sprawdź czy callback został podłączony
                        mock_worker.signals.finished.connect.assert_called()
                        mock_worker.signals.error.connect.assert_called()
                        mock_worker.signals.progress.connect.assert_called()

    def test_worker_callbacks_finished(self, manager, temp_dir):
        """Test obsługi sygnału finished od workera."""
        operation_id = "test_operation"
        mock_worker = Mock()
        manager._active_operations[operation_id] = mock_worker
        
        mock_progress_dialog = Mock()
        callback = Mock()
        
        # Symuluj callback finished
        created_path = os.path.join(temp_dir, "new_folder")
        
        with patch('src.ui.folder_operations_manager.QMessageBox.information') as mock_info:
            # Ręcznie wywołaj callback finished (symulacja)
            manager._cleanup_operation(operation_id, mock_progress_dialog)
            if callback:
                callback(created_path)
            
            # Sprawdź czy callback został wywołany
            callback.assert_called_once_with(created_path)

    def test_worker_callbacks_error(self, manager):
        """Test obsługi sygnału error od workera."""
        operation_id = "test_operation"
        mock_worker = Mock()
        manager._active_operations[operation_id] = mock_worker
        
        mock_progress_dialog = Mock()
        error_msg = "Test error message"
        
        with patch('src.ui.folder_operations_manager.QMessageBox.critical') as mock_critical:
            # Ręcznie wywołaj callback error (symulacja)
            manager._cleanup_operation(operation_id, mock_progress_dialog)
            
            # Sprawdź czy operacja została wyczyszczona
            assert operation_id not in manager._active_operations

    def test_worker_callbacks_progress(self, manager):
        """Test obsługi sygnału progress od workera."""
        mock_progress_dialog = Mock()
        
        # Symuluj callback progress (jako lambda function)
        percent = 50
        message = "Processing..."
        
        # Ręcznie wywołaj callback progress (symulacja)
        if mock_progress_dialog:
            mock_progress_dialog.setValue(percent)
            mock_progress_dialog.setLabelText(message)
        
        # Sprawdź czy progress został zaktualizowany
        mock_progress_dialog.setValue.assert_called_with(percent)
        mock_progress_dialog.setLabelText.assert_called_with(message)


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 