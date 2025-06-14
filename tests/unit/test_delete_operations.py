"""
Testy jednostkowe dla DeleteOperations.
"""

import sys
import unittest
from unittest.mock import Mock, patch

from PyQt6.QtWidgets import QApplication, QWidget

# Upewnij się, że QApplication istnieje dla testów Qt
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.models.file_pair import FilePair
from src.ui.file_operations.delete_operations import DeleteOperations


class TestDeleteOperations(unittest.TestCase):
    """Testy dla klasy DeleteOperations."""

    def setUp(self):
        """Przygotowanie testów."""
        self.parent_window = Mock()
        self.delete_ops = DeleteOperations(self.parent_window)

        # Mock file pair
        self.file_pair = Mock(spec=FilePair)
        self.file_pair.get_base_name.return_value = "test_file"
        self.file_pair.get_archive_path.return_value = "/path/to/archive.zip"
        self.file_pair.get_preview_path.return_value = "/path/to/preview.jpg"

        # Mock widget
        self.widget = Mock(spec=QWidget)

    @patch("src.ui.file_operations.delete_operations.QProgressDialog")
    @patch("src.ui.file_operations.delete_operations.QThreadPool")
    @patch("src.ui.file_operations.delete_operations.QMessageBox")
    @patch("src.ui.file_operations.delete_operations.file_operations")
    def test_delete_file_pair_confirmed(
        self, mock_file_ops, mock_msg_box, mock_thread_pool, mock_progress_dialog
    ):
        """Test usuwania pliku po potwierdzeniu."""
        # Arrange
        mock_msg_box.question.return_value = mock_msg_box.StandardButton.Yes
        mock_worker = Mock()
        mock_file_ops.delete_file_pair.return_value = mock_worker
        mock_progress_instance = Mock()
        mock_progress_dialog.return_value = mock_progress_instance
        mock_thread_pool.globalInstance.return_value.start = Mock()

        # Act
        self.delete_ops.delete_file_pair(self.file_pair, self.widget)

        # Assert
        mock_msg_box.question.assert_called_once()
        mock_file_ops.delete_file_pair.assert_called_once_with(self.file_pair)
        mock_worker.signals.finished.connect.assert_called_once()
        mock_worker.signals.error.connect.assert_called_once()
        mock_worker.signals.progress.connect.assert_called_once()
        mock_worker.signals.interrupted.connect.assert_called_once()
        mock_progress_dialog.assert_called_once()
        mock_thread_pool.globalInstance.return_value.start.assert_called_once_with(
            mock_worker
        )

    @patch("src.ui.file_operations.delete_operations.QMessageBox")
    def test_delete_file_pair_cancelled(self, mock_msg_box):
        """Test anulowania usuwania."""
        # Arrange
        mock_msg_box.question.return_value = mock_msg_box.StandardButton.No

        # Act
        self.delete_ops.delete_file_pair(self.file_pair, self.widget)

        # Assert
        mock_msg_box.question.assert_called_once()

    @patch("src.ui.file_operations.delete_operations.QMessageBox")
    @patch("src.ui.file_operations.delete_operations.file_operations")
    def test_delete_file_pair_worker_error(self, mock_file_ops, mock_msg_box):
        """Test błędu inicjalizacji workera."""
        # Arrange
        mock_msg_box.question.return_value = mock_msg_box.StandardButton.Yes
        mock_file_ops.delete_file_pair.return_value = None

        # Act
        self.delete_ops.delete_file_pair(self.file_pair, self.widget)

        # Assert
        mock_msg_box.warning.assert_called_once()

    def test_handle_delete_finished(self):
        """Test obsługi zakończenia usuwania."""
        # Arrange
        deleted_file_pair = Mock(spec=FilePair)
        deleted_file_pair.get_base_name.return_value = "deleted_file"
        progress_dialog = Mock()
        progress_dialog.isVisible.return_value = True

        self.parent_window.refresh_all_views = Mock()

        with patch(
            "src.ui.file_operations.delete_operations.QMessageBox"
        ) as mock_msg_box:
            # Act
            self.delete_ops._handle_delete_finished(deleted_file_pair, progress_dialog)

            # Assert
            progress_dialog.accept.assert_called_once()
            mock_msg_box.information.assert_called_once()
            self.parent_window.refresh_all_views.assert_called_once()

    def test_handle_operation_error(self):
        """Test obsługi błędu operacji."""
        # Arrange
        progress_dialog = Mock()
        progress_dialog.isVisible.return_value = True
        self.parent_window.refresh_all_views = Mock()

        with patch(
            "src.ui.file_operations.delete_operations.QMessageBox"
        ) as mock_msg_box:
            # Act
            self.delete_ops._handle_operation_error(
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
        self.delete_ops._handle_operation_progress(50, "Test message", progress_dialog)

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
            "src.ui.file_operations.delete_operations.QMessageBox"
        ) as mock_msg_box:
            # Act
            self.delete_ops._handle_operation_interrupted(
                "Test message", progress_dialog
            )

            # Assert
            progress_dialog.reject.assert_called_once()
            mock_msg_box.information.assert_called_once()
            self.parent_window.refresh_all_views.assert_called_once()


if __name__ == "__main__":
    unittest.main()
