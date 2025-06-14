"""
Testy jednostkowe dla RenameOperations.
"""

import sys
import unittest
from unittest.mock import Mock, patch

from PyQt6.QtWidgets import QApplication, QWidget

# Upewnij się, że QApplication istnieje dla testów Qt
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.models.file_pair import FilePair
from src.ui.file_operations.rename_operations import RenameOperations


class TestRenameOperations(unittest.TestCase):
    """Testy dla klasy RenameOperations."""

    def setUp(self):
        """Przygotowanie testów."""
        self.parent_window = Mock()
        self.rename_ops = RenameOperations(self.parent_window)

        # Mock file pair
        self.file_pair = Mock(spec=FilePair)
        self.file_pair.get_base_name.return_value = "test_file"
        self.file_pair.working_directory = "/test/working/dir"

        # Mock widget
        self.widget = Mock(spec=QWidget)

    @patch("src.ui.file_operations.rename_operations.QProgressDialog")
    @patch("src.ui.file_operations.rename_operations.QThreadPool")
    @patch("src.ui.file_operations.rename_operations.QInputDialog")
    @patch("src.ui.file_operations.rename_operations.file_operations")
    def test_rename_file_pair_success(
        self, mock_file_ops, mock_input_dialog, mock_thread_pool, mock_progress_dialog
    ):
        """Test pomyślnej zmiany nazwy pliku."""
        # Arrange
        mock_input_dialog.getText.return_value = ("new_name", True)
        mock_worker = Mock()
        mock_file_ops.rename_file_pair.return_value = mock_worker
        mock_progress_instance = Mock()
        mock_progress_dialog.return_value = mock_progress_instance
        mock_thread_pool.globalInstance.return_value.start = Mock()

        # Act
        self.rename_ops.rename_file_pair(self.file_pair, self.widget)

        # Assert
        mock_input_dialog.getText.assert_called_once()
        mock_file_ops.rename_file_pair.assert_called_once_with(
            self.file_pair, "new_name", "/test/working/dir"
        )
        mock_worker.signals.finished.connect.assert_called_once()
        mock_worker.signals.error.connect.assert_called_once()
        mock_worker.signals.progress.connect.assert_called_once()
        mock_worker.signals.interrupted.connect.assert_called_once()
        mock_progress_dialog.assert_called_once()
        mock_thread_pool.globalInstance.return_value.start.assert_called_once_with(
            mock_worker
        )

    @patch("src.ui.file_operations.rename_operations.QInputDialog")
    def test_rename_file_pair_cancelled(self, mock_input_dialog):
        """Test anulowania zmiany nazwy."""
        # Arrange
        mock_input_dialog.getText.return_value = ("", False)

        # Act
        self.rename_ops.rename_file_pair(self.file_pair, self.widget)

        # Assert
        mock_input_dialog.getText.assert_called_once()

    @patch("src.ui.file_operations.rename_operations.QInputDialog")
    def test_rename_file_pair_same_name(self, mock_input_dialog):
        """Test podania tej samej nazwy."""
        # Arrange
        mock_input_dialog.getText.return_value = ("test_file", True)

        # Act
        self.rename_ops.rename_file_pair(self.file_pair, self.widget)

        # Assert
        mock_input_dialog.getText.assert_called_once()

    @patch("src.ui.file_operations.rename_operations.QInputDialog")
    @patch("src.ui.file_operations.rename_operations.file_operations")
    @patch("src.ui.file_operations.rename_operations.QMessageBox")
    def test_rename_file_pair_worker_error(
        self, mock_msg_box, mock_file_ops, mock_input_dialog
    ):
        """Test błędu inicjalizacji workera."""
        # Arrange
        mock_input_dialog.getText.return_value = ("new_name", True)
        mock_file_ops.rename_file_pair.return_value = None

        # Act
        self.rename_ops.rename_file_pair(self.file_pair, self.widget)

        # Assert
        mock_msg_box.warning.assert_called_once()

    def test_handle_rename_finished(self):
        """Test obsługi zakończenia zmiany nazwy."""
        # Arrange
        old_file_pair = Mock(spec=FilePair)
        old_file_pair.get_base_name.return_value = "old_name"
        new_file_pair = Mock(spec=FilePair)
        new_file_pair.get_base_name.return_value = "new_name"
        progress_dialog = Mock()
        progress_dialog.isVisible.return_value = True

        self.parent_window.refresh_all_views = Mock()

        with patch(
            "src.ui.file_operations.rename_operations.QMessageBox"
        ) as mock_msg_box:
            # Act
            self.rename_ops._handle_rename_finished(
                old_file_pair, new_file_pair, progress_dialog
            )

            # Assert
            progress_dialog.accept.assert_called_once()
            mock_msg_box.information.assert_called_once()
            self.parent_window.refresh_all_views.assert_called_once_with(
                new_selection=new_file_pair
            )

    def test_handle_operation_error(self):
        """Test obsługi błędu operacji."""
        # Arrange
        progress_dialog = Mock()
        progress_dialog.isVisible.return_value = True
        self.parent_window.refresh_all_views = Mock()

        with patch(
            "src.ui.file_operations.rename_operations.QMessageBox"
        ) as mock_msg_box:
            # Act
            self.rename_ops._handle_operation_error(
                "Test error", "Test title", progress_dialog
            )

            # Assert
            progress_dialog.reject.assert_called_once()
            mock_msg_box.critical.assert_called_once()
            self.parent_window.refresh_all_views.assert_called_once()

    def test_handle_operation_progress(self):
        """Test obsługi postępu operacji."""
        # Arrange
        progress_dialog = Mock()
        progress_dialog.isVisible.return_value = True
        progress_dialog.maximum.return_value = 100

        # Act
        self.rename_ops._handle_operation_progress(50, "Test message", progress_dialog)

        # Assert
        progress_dialog.setValue.assert_called_once_with(50)
        progress_dialog.setLabelText.assert_called_once_with("Test message")

    def test_handle_operation_interrupted(self):
        """Test obsługi przerwania operacji."""
        # Arrange
        progress_dialog = Mock()
        progress_dialog.isVisible.return_value = True
        self.parent_window.refresh_all_views = Mock()

        with patch(
            "src.ui.file_operations.rename_operations.QMessageBox"
        ) as mock_msg_box:
            # Act
            self.rename_ops._handle_operation_interrupted(
                "Test message", progress_dialog
            )

            # Assert
            progress_dialog.reject.assert_called_once()
            mock_msg_box.information.assert_called_once()
            self.parent_window.refresh_all_views.assert_called_once()


if __name__ == "__main__":
    unittest.main()
