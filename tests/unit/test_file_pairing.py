"""
Testy jednostkowe dla modułu file_pairing.
"""

import pytest
import tempfile
import os
from unittest.mock import patch

from src.logic.file_pairing import (
    create_file_pairs,
    identify_unpaired_files,
    ARCHIVE_EXTENSIONS,
    PREVIEW_EXTENSIONS
)
from src.models.file_pair import FilePair


class TestCreateFilePairs:
    """Testy dla funkcji create_file_pairs."""
    
    def setup_method(self):
        """Setup przed każdym testem."""
        self.temp_dir = tempfile.mkdtemp()
    
    def test_create_file_pairs_empty_map(self):
        """Test dla pustej mapy plików."""
        file_map = {}
        pairs, processed = create_file_pairs(file_map, self.temp_dir)
        
        assert pairs == []
        assert processed == set()
    
    def test_create_file_pairs_no_matching_files(self):
        """Test dla mapy bez pasujących plików."""
        file_map = {
            "test1": [os.path.join(self.temp_dir, "test1.zip")],  # Tylko archiwum
            "test2": [os.path.join(self.temp_dir, "test2.jpg")]   # Tylko podgląd
        }
        pairs, processed = create_file_pairs(file_map, self.temp_dir)
        
        assert pairs == []
        assert processed == set()
    
    def test_create_file_pairs_first_match_strategy(self):
        """Test strategii first_match."""
        archive_path = os.path.join(self.temp_dir, "test.zip")
        preview_path = os.path.join(self.temp_dir, "test.jpg")
        
        file_map = {
            "test": [archive_path, preview_path]
        }
        
        pairs, processed = create_file_pairs(file_map, self.temp_dir, "first_match")
        
        assert len(pairs) == 1
        assert isinstance(pairs[0], FilePair)
        assert len(processed) == 2
        assert archive_path in processed
        assert preview_path in processed
    
    def test_create_file_pairs_all_combinations_strategy(self):
        """Test strategii all_combinations."""
        archive1_path = os.path.join(self.temp_dir, "test.zip")
        archive2_path = os.path.join(self.temp_dir, "test.rar")
        preview1_path = os.path.join(self.temp_dir, "test.jpg")
        preview2_path = os.path.join(self.temp_dir, "test.png")
        
        file_map = {
            "test": [archive1_path, archive2_path, preview1_path, preview2_path]
        }
        
        pairs, processed = create_file_pairs(file_map, self.temp_dir, "all_combinations")
        
        # 2 archiwa × 2 podglądy = 4 pary
        assert len(pairs) == 4
        assert len(processed) == 4
    
    def test_create_file_pairs_best_match_strategy(self):
        """Test strategii best_match."""
        # Utworzenie plików testowych z różnymi nazwami
        exact_archive = os.path.join(self.temp_dir, "photo001.zip")
        exact_preview = os.path.join(self.temp_dir, "photo001.jpg")
        partial_preview = os.path.join(self.temp_dir, "photo.png")
        
        file_map = {
            "photo001": [exact_archive, exact_preview, partial_preview]
        }
        
        pairs, processed = create_file_pairs(file_map, self.temp_dir, "best_match")
        
        # Powinien znaleźć dokładne dopasowanie
        assert len(pairs) == 1
        assert pairs[0].archive_path == exact_archive
        assert pairs[0].preview_path == exact_preview
    
    def test_create_file_pairs_best_match_with_scoring(self):
        """Test strategii best_match z oceną jakości."""
        archive_path = os.path.join(self.temp_dir, "test.zip")
        jpg_preview = os.path.join(self.temp_dir, "test.jpg")
        png_preview = os.path.join(self.temp_dir, "test.png")
        
        file_map = {
            "test": [archive_path, jpg_preview, png_preview]
        }
        
        pairs, processed = create_file_pairs(file_map, self.temp_dir, "best_match")
        
        # JPG powinien mieć wyższą ocenę niż PNG
        assert len(pairs) == 1
        assert pairs[0].preview_path == jpg_preview  # JPG preferowane
    
    def test_create_file_pairs_unknown_strategy(self):
        """Test dla nieznanej strategii."""
        file_map = {
            "test": [os.path.join(self.temp_dir, "test.zip"), os.path.join(self.temp_dir, "test.jpg")]
        }
        
        with patch('src.logic.file_pairing.logger') as mock_logger:
            pairs, processed = create_file_pairs(file_map, self.temp_dir, "unknown_strategy")
            
            assert pairs == []
            assert processed == set()
            mock_logger.error.assert_called_once()
    
    def test_create_file_pairs_with_invalid_filepair(self):
        """Test obsługi błędów przy tworzeniu FilePair."""
        # Test z nieprawidłowymi ścieżkami
        file_map = {
            "test": ["", os.path.join(self.temp_dir, "test.jpg")]  # Pusta ścieżka archiwum
        }
        
        with patch('src.logic.file_pairing.logger') as mock_logger:
            pairs, processed = create_file_pairs(file_map, self.temp_dir, "first_match")
            
            # FilePair powinien rzucić ValueError dla pustej ścieżki
            assert pairs == []
            assert processed == set()
            mock_logger.error.assert_called_once()


class TestIdentifyUnpairedFiles:
    """Testy dla funkcji identify_unpaired_files."""
    
    def setup_method(self):
        """Setup przed każdym testem."""
        self.temp_dir = tempfile.mkdtemp()
    
    def test_identify_unpaired_files_empty_inputs(self):
        """Test dla pustych danych wejściowych."""
        file_map = {}
        processed_files = set()
        
        archives, previews = identify_unpaired_files(file_map, processed_files)
        
        assert archives == []
        assert previews == []
    
    def test_identify_unpaired_files_all_paired(self):
        """Test gdy wszystkie pliki są sparowane."""
        archive_path = os.path.join(self.temp_dir, "test.zip")
        preview_path = os.path.join(self.temp_dir, "test.jpg")
        
        file_map = {
            "test": [archive_path, preview_path]
        }
        processed_files = {archive_path, preview_path}
        
        archives, previews = identify_unpaired_files(file_map, processed_files)
        
        assert archives == []
        assert previews == []
    
    def test_identify_unpaired_files_some_unpaired(self):
        """Test gdy niektóre pliki są niesparowane."""
        paired_archive = os.path.join(self.temp_dir, "paired.zip")
        paired_preview = os.path.join(self.temp_dir, "paired.jpg")
        unpaired_archive = os.path.join(self.temp_dir, "unpaired.rar")
        unpaired_preview = os.path.join(self.temp_dir, "unpaired.png")
        
        file_map = {
            "paired": [paired_archive, paired_preview],
            "unpaired1": [unpaired_archive],
            "unpaired2": [unpaired_preview]
        }
        processed_files = {paired_archive, paired_preview}
        
        archives, previews = identify_unpaired_files(file_map, processed_files)
        
        assert len(archives) == 1
        assert unpaired_archive in archives
        assert len(previews) == 1
        assert unpaired_preview in previews
    
    def test_identify_unpaired_files_mixed_extensions(self):
        """Test z różnymi rozszerzeniami plików."""
        archive1 = os.path.join(self.temp_dir, "test1.zip")
        archive2 = os.path.join(self.temp_dir, "test2.rar")
        preview1 = os.path.join(self.temp_dir, "test3.jpg")
        preview2 = os.path.join(self.temp_dir, "test4.png")
        unsupported = os.path.join(self.temp_dir, "test5.txt")
        
        file_map = {
            "test1": [archive1],
            "test2": [archive2],
            "test3": [preview1],
            "test4": [preview2],
            "test5": [unsupported]
        }
        processed_files = set()  # Nic nie jest sparowane
        
        archives, previews = identify_unpaired_files(file_map, processed_files)
        
        assert len(archives) == 2
        assert archive1 in archives
        assert archive2 in archives
        assert len(previews) == 2
        assert preview1 in previews
        assert preview2 in previews
        # Nieobsługiwany plik nie powinien być na żadnej liście
        assert unsupported not in archives
        assert unsupported not in previews


class TestModuleConstants:
    """Testy dla stałych modułu."""
    
    def test_archive_extensions_content(self):
        """Test zawartości ARCHIVE_EXTENSIONS."""
        assert '.zip' in ARCHIVE_EXTENSIONS
        assert isinstance(ARCHIVE_EXTENSIONS, set)
    
    def test_preview_extensions_content(self):
        """Test zawartości PREVIEW_EXTENSIONS."""
        assert '.jpg' in PREVIEW_EXTENSIONS
        assert '.png' in PREVIEW_EXTENSIONS
        assert isinstance(PREVIEW_EXTENSIONS, set)
    
    def test_extensions_consistency(self):
        """Test spójności rozszerzeń między modułami."""
        # Sprawdzamy czy rozszerzenia są identyczne z scanner_core
        from src.logic.scanner_core import ARCHIVE_EXTENSIONS as CORE_ARCHIVES
        from src.logic.scanner_core import PREVIEW_EXTENSIONS as CORE_PREVIEWS
        
        assert ARCHIVE_EXTENSIONS == CORE_ARCHIVES
        assert PREVIEW_EXTENSIONS == CORE_PREVIEWS
