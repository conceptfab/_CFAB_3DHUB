"""
Testy dla modułu file_pair.py - funkcjonalność 'Ulubione'
"""

import pytest
from src.models.file_pair import FilePair


class TestFilePairFavorite:
    """Testy dla funkcjonalności 'Ulubione' w klasie FilePair."""

    def test_file_pair_favorite_default(self):
        """Test domyślnej wartości atrybutu 'is_favorite'."""
        file_pair = FilePair("path/to/archive.zip", "path/to/preview.jpg")
        
        # Domyślnie plik nie powinien być ulubionym
        assert file_pair.is_favorite == False
        assert file_pair.is_favorite_file() == False
    
    def test_file_pair_toggle_favorite(self):
        """Test przełączania statusu 'ulubione'."""
        file_pair = FilePair("path/to/archive.zip", "path/to/preview.jpg")
        
        # Pierwszy toggle powinien włączyć ulubione
        assert file_pair.toggle_favorite() == True
        assert file_pair.is_favorite == True
        assert file_pair.is_favorite_file() == True
        
        # Drugi toggle powinien wyłączyć ulubione
        assert file_pair.toggle_favorite() == False
        assert file_pair.is_favorite == False
        assert file_pair.is_favorite_file() == False
    
    def test_file_pair_set_favorite(self):
        """Test bezpośredniego ustawiania statusu 'ulubione'."""
        file_pair = FilePair("path/to/archive.zip", "path/to/preview.jpg")
        
        # Ustawienie na True
        file_pair.set_favorite(True)
        assert file_pair.is_favorite == True
        assert file_pair.is_favorite_file() == True
        
        # Ustawienie na False
        file_pair.set_favorite(False)
        assert file_pair.is_favorite == False
        assert file_pair.is_favorite_file() == False
        
        # Ustawienie wartości nieboolowskiej powinno konwertować do bool
        file_pair.set_favorite(1)
        assert file_pair.is_favorite == True
        
        file_pair.set_favorite(0)
        assert file_pair.is_favorite == False
        
        file_pair.set_favorite("string")
        assert file_pair.is_favorite == True
