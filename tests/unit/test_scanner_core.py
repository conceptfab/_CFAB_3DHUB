"""
Testy jednostkowe dla modułu scanner_core.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from src.logic.scanner_core import (
    ScanningInterrupted,
    get_directory_modification_time,
    collect_files_streaming,
    ARCHIVE_EXTENSIONS,
    PREVIEW_EXTENSIONS
)


class TestScanningInterrupted:
    """Testy dla wyjątku ScanningInterrupted."""
    
    def test_scanning_interrupted_creation(self):
        """Test tworzenia wyjątku ScanningInterrupted."""
        exception = ScanningInterrupted("Test message")
        assert str(exception) == "Test message"
    
    def test_scanning_interrupted_inheritance(self):
        """Test dziedziczenia wyjątku."""
        exception = ScanningInterrupted()
        assert isinstance(exception, Exception)


class TestGetDirectoryModificationTime:
    """Testy dla funkcji get_directory_modification_time."""
    
    def test_get_directory_modification_time_nonexistent(self):
        """Test dla nieistniejącego katalogu."""
        result = get_directory_modification_time("/nonexistent/directory")
        assert result == 0
    
    def test_get_directory_modification_time_valid_directory(self):
        """Test dla istniejącego katalogu."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = get_directory_modification_time(temp_dir)
            assert result > 0
            assert isinstance(result, float)
    
    def test_get_directory_modification_time_with_files(self):
        """Test dla katalogu z plikami."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Utworzenie pliku w katalogu
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")
            
            result = get_directory_modification_time(temp_dir)
            assert result > 0
    
    @patch('src.logic.scanner_core.path_exists')
    @patch('os.path.getmtime')
    def test_get_directory_modification_time_permission_error(self, mock_getmtime, mock_path_exists):
        """Test obsługi błędów uprawnień."""
        mock_path_exists.return_value = True
        mock_getmtime.side_effect = PermissionError("Access denied")
        
        result = get_directory_modification_time("/test/directory")
        assert result == 0


class TestCollectFilesStreaming:
    """Testy dla funkcji collect_files_streaming."""
    
    def setup_method(self):
        """Setup przed każdym testem."""
        # Clear cache przed każdym testem
        from src.logic.scan_cache import clear_cache
        clear_cache()
    
    def test_collect_files_streaming_nonexistent_directory(self):
        """Test dla nieistniejącego katalogu."""
        result = collect_files_streaming("/nonexistent/directory")
        assert result == {}
    
    def test_collect_files_streaming_empty_directory(self):
        """Test dla pustego katalogu."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = collect_files_streaming(temp_dir)
            assert result == {}
    
    def test_collect_files_streaming_with_supported_files(self):
        """Test dla katalogu z obsługiwanymi plikami."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Utworzenie plików testowych
            archive_file = os.path.join(temp_dir, "test.zip")
            preview_file = os.path.join(temp_dir, "test.jpg")
            unsupported_file = os.path.join(temp_dir, "test.txt")
            
            # Utworzenie plików
            for file_path in [archive_file, preview_file, unsupported_file]:
                with open(file_path, "w") as f:
                    f.write("test content")
            
            result = collect_files_streaming(temp_dir)
            
            # Sprawdzamy czy znaleziono obsługiwane pliki
            assert len(result) == 1  # Jeden base name "test"
            base_key = list(result.keys())[0]
            assert len(result[base_key]) == 2  # .zip i .jpg
            
            # Sprawdzamy ścieżki
            file_paths = result[base_key]
            assert any("test.zip" in path for path in file_paths)
            assert any("test.jpg" in path for path in file_paths)
    
    def test_collect_files_streaming_with_progress_callback(self):
        """Test z callback funkcją postępu."""
        progress_calls = []
        
        def mock_progress(percent, message):
            progress_calls.append((percent, message))
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Utworzenie pliku testowego
            test_file = os.path.join(temp_dir, "test.jpg")
            with open(test_file, "w") as f:
                f.write("test content")
            
            result = collect_files_streaming(temp_dir, progress_callback=mock_progress)
            
            # Sprawdzamy czy callback był wywoływany
            assert len(progress_calls) > 0
            assert any(call[0] == 0 for call in progress_calls)  # Start progress
    
    def test_collect_files_streaming_with_interrupt_check(self):
        """Test z funkcją przerwania."""
        interrupt_called = False
        
        def mock_interrupt():
            nonlocal interrupt_called
            interrupt_called = True
            return True  # Przerwij skanowanie
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Utworzenie pliku testowego
            test_file = os.path.join(temp_dir, "test.jpg")
            with open(test_file, "w") as f:
                f.write("test content")
            
            with pytest.raises(ScanningInterrupted):
                collect_files_streaming(temp_dir, interrupt_check=mock_interrupt)
            
            assert interrupt_called is True
    
    def test_collect_files_streaming_max_depth(self):
        """Test z ograniczeniem głębokości."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Utworzenie struktury folderów
            sub_dir = os.path.join(temp_dir, "subdir")
            os.makedirs(sub_dir)
            
            # Pliki w głównym katalogu
            main_file = os.path.join(temp_dir, "main.jpg")
            with open(main_file, "w") as f:
                f.write("test content")
            
            # Pliki w podkatalogu
            sub_file = os.path.join(sub_dir, "sub.jpg")
            with open(sub_file, "w") as f:
                f.write("test content")
            
            # Test z max_depth = 0 (tylko główny katalog)
            result = collect_files_streaming(temp_dir, max_depth=0)
            assert len(result) == 1  # Tylko plik z głównego katalogu
            
            # Test z max_depth = 1 (główny + pierwszy poziom)
            result = collect_files_streaming(temp_dir, max_depth=1)
            assert len(result) == 2  # Pliki z obu katalogów
    
    def test_collect_files_streaming_force_refresh(self):
        """Test z wymuszeniem odświeżenia cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.jpg")
            with open(test_file, "w") as f:
                f.write("test content")
            
            # Pierwsze skanowanie - powinno zapisać do cache
            result1 = collect_files_streaming(temp_dir, force_refresh=False)
            
            # Drugie skanowanie bez force_refresh - powinno używać cache
            with patch('src.logic.scanner_core.logger') as mock_logger:
                result2 = collect_files_streaming(temp_dir, force_refresh=False)
                
                # Sprawdzamy czy użyto cache (w logach powinien być wpis o cache hit)
                assert result1 == result2
            
            # Trzecie skanowanie z force_refresh - powinno pominąć cache
            result3 = collect_files_streaming(temp_dir, force_refresh=True)
            assert result1 == result3


class TestConstants:
    """Testy dla stałych modułu."""
    
    def test_archive_extensions_not_empty(self):
        """Test czy ARCHIVE_EXTENSIONS nie jest puste."""
        assert len(ARCHIVE_EXTENSIONS) > 0
        assert isinstance(ARCHIVE_EXTENSIONS, set)
    
    def test_preview_extensions_not_empty(self):
        """Test czy PREVIEW_EXTENSIONS nie jest puste."""
        assert len(PREVIEW_EXTENSIONS) > 0
        assert isinstance(PREVIEW_EXTENSIONS, set)
    
    def test_extensions_are_lowercase(self):
        """Test czy rozszerzenia są małymi literami."""
        for ext in ARCHIVE_EXTENSIONS:
            assert ext.islower(), f"Archive extension {ext} should be lowercase"
        
        for ext in PREVIEW_EXTENSIONS:
            assert ext.islower(), f"Preview extension {ext} should be lowercase"
