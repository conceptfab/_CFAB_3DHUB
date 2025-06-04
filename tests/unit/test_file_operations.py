"""
Testy dla modułu file_operations.py
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from src.logic import file_operations


class TestFileOperations:
    
    def test_open_archive_externally_nonexistent_file(self):
        """Test otwierania nieistniejącego pliku."""
        non_existent_path = "/path/to/non_existent_file.zip"
        result = file_operations.open_archive_externally(non_existent_path)
        assert result is False

    @patch('os.path.exists')
    @patch('platform.system')
    @patch('os.startfile')
    def test_open_archive_externally_windows(self, mock_startfile, mock_system, mock_exists):
        """Test otwierania pliku na Windowsie."""
        # Konfiguracja mocków
        mock_exists.return_value = True
        mock_system.return_value = 'Windows'
        
        # Wywołanie testowanej funkcji
        result = file_operations.open_archive_externally("test_file.zip")
        
        # Sprawdzenie wyników
        assert result is True
        mock_startfile.assert_called_once_with("test_file.zip")

    @patch('os.path.exists')
    @patch('platform.system')
    @patch('PyQt6.QtGui.QDesktopServices.openUrl')
    def test_open_archive_externally_other_os(self, mock_openurl, mock_system, mock_exists):
        """Test otwierania pliku na innych systemach operacyjnych."""
        # Konfiguracja mocków
        mock_exists.return_value = True
        mock_system.return_value = 'Linux'
        mock_openurl.return_value = True
        
        # Wywołanie testowanej funkcji
        result = file_operations.open_archive_externally("test_file.zip")
        
        # Sprawdzenie wyników
        assert result is True
        mock_openurl.assert_called_once()
        
    @patch('os.path.exists')
    @patch('platform.system')
    @patch('PyQt6.QtGui.QDesktopServices.openUrl')
    def test_open_archive_externally_qt_failure(self, mock_openurl, mock_system, mock_exists):
        """Test gdy otwarcie pliku przez Qt się nie powiedzie."""
        # Konfiguracja mocków
        mock_exists.return_value = True
        mock_system.return_value = 'Linux'
        mock_openurl.return_value = False
        
        # Wywołanie testowanej funkcji
        result = file_operations.open_archive_externally("test_file.zip")
        
        # Sprawdzenie wyników
        assert result is False
        mock_openurl.assert_called_once()
        
    @patch('os.path.exists')
    @patch('platform.system')
    @patch('os.startfile')
    def test_open_archive_externally_exception(self, mock_startfile, mock_system, mock_exists):
        """Test obsługi wyjątku podczas otwierania pliku."""
        # Konfiguracja mocków
        mock_exists.return_value = True
        mock_system.return_value = 'Windows'
        mock_startfile.side_effect = Exception("Test exception")
        
        # Wywołanie testowanej funkcji
        result = file_operations.open_archive_externally("test_file.zip")
        
        # Sprawdzenie wyników
        assert result is False
        mock_startfile.assert_called_once_with("test_file.zip")
