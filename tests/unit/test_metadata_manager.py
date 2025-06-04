"""
Testy dla modułu metadata_manager.py
"""

import json
import os
import pytest
import tempfile
import shutil
from unittest.mock import patch

from src.logic import metadata_manager
from src.models.file_pair import FilePair


class TestMetadataManager:
    
    @pytest.fixture
    def temp_dir(self):
        """Fixture zwracający tymczasowy katalog do testów."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
      def test_get_metadata_path(self):
        """Test generowania ścieżki do pliku metadanych."""
        working_dir = "/test/working/dir"
        expected_path = os.path.join(working_dir, 
                                    metadata_manager.METADATA_DIR_NAME, 
                                    metadata_manager.METADATA_FILE_NAME)
        
        assert metadata_manager.get_metadata_path(working_dir) == expected_path
    
    def test_get_relative_path(self):
        """Test konwersji ścieżki absolutnej na względną."""
        # Używamy os.path.join aby zapewnić poprawne separatory na różnych systemach
        base_path = os.path.normpath("/base/path")
        abs_path = os.path.normpath("/base/path/subdir/file.txt")
        
        rel_path = metadata_manager.get_relative_path(abs_path, base_path)
        # Normalizujemy ścieżkę wynikową dla porównania
        expected = os.path.normpath("subdir/file.txt")
        assert rel_path == expected
      def test_get_absolute_path(self):
        """Test konwersji ścieżki względnej na absolutną."""
        base_path = os.path.normpath("/base/path")
        rel_path = os.path.normpath("subdir/file.txt")
        
        abs_path = metadata_manager.get_absolute_path(rel_path, base_path)
        expected = os.path.normpath("/base/path/subdir/file.txt")
        assert abs_path == expected
    
    def test_load_metadata_nonexistent(self, temp_dir):
        """Test wczytywania metadanych gdy plik nie istnieje."""
        metadata = metadata_manager.load_metadata(temp_dir)
        
        # Powinniśmy otrzymać domyślną strukturę
        assert isinstance(metadata, dict)
        assert "file_pairs" in metadata
        assert metadata["file_pairs"] == {}
    
    def test_load_metadata_empty(self, temp_dir):
        """Test wczytywania pustego pliku metadanych."""
        # Utwórz katalog .app_metadata
        metadata_dir = os.path.join(temp_dir, metadata_manager.METADATA_DIR_NAME)
        os.makedirs(metadata_dir, exist_ok=True)
        
        # Utwórz pusty plik metadata.json
        metadata_path = os.path.join(metadata_dir, metadata_manager.METADATA_FILE_NAME)
        with open(metadata_path, 'w') as f:
            json.dump({}, f)
        
        metadata = metadata_manager.load_metadata(temp_dir)
        
        # Powinniśmy otrzymać zawartość pliku
        assert metadata == {}
    
    def test_load_metadata_corrupted(self, temp_dir):
        """Test wczytywania uszkodzonego pliku metadanych."""
        # Utwórz katalog .app_metadata
        metadata_dir = os.path.join(temp_dir, metadata_manager.METADATA_DIR_NAME)
        os.makedirs(metadata_dir, exist_ok=True)
        
        # Utwórz uszkodzony plik metadata.json
        metadata_path = os.path.join(metadata_dir, metadata_manager.METADATA_FILE_NAME)
        with open(metadata_path, 'w') as f:
            f.write("{invalid json")
        
        metadata = metadata_manager.load_metadata(temp_dir)
        
        # Powinniśmy otrzymać domyślną strukturę
        assert isinstance(metadata, dict)
        assert "file_pairs" in metadata
        assert metadata["file_pairs"] == {}
    
    def test_save_metadata(self, temp_dir):
        """Test zapisywania metadanych."""
        # Utwórz testowe obiekty FilePair
        archive_path = os.path.join(temp_dir, "archive.zip")
        preview_path = os.path.join(temp_dir, "preview.jpg")
        
        file_pair1 = FilePair(archive_path, preview_path)
        file_pair1.is_favorite = True
        file_pair2 = FilePair(archive_path + "2", preview_path + "2")
        
        # Zapisz metadane
        result = metadata_manager.save_metadata(temp_dir, [file_pair1, file_pair2])
        assert result is True
        
        # Sprawdź czy pliki zostały utworzone
        metadata_path = metadata_manager.get_metadata_path(temp_dir)
        assert os.path.exists(metadata_path)
        
        # Sprawdź zawartość pliku metadanych
        with open(metadata_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert "file_pairs" in saved_data
        
        # Pobierz względne ścieżki dla porównania
        rel_path1 = metadata_manager.get_relative_path(archive_path, temp_dir)
        rel_path2 = metadata_manager.get_relative_path(archive_path + "2", temp_dir)
        
        assert rel_path1 in saved_data["file_pairs"]
        assert rel_path2 in saved_data["file_pairs"]
        
        assert saved_data["file_pairs"][rel_path1]["is_favorite"] is True
        assert saved_data["file_pairs"][rel_path2]["is_favorite"] is False
    
    def test_apply_metadata_to_file_pairs(self, temp_dir):
        """Test aplikowania metadanych do obiektów FilePair."""
        # Utwórz testowe obiekty FilePair
        archive_path = os.path.join(temp_dir, "archive.zip")
        preview_path = os.path.join(temp_dir, "preview.jpg")
        
        file_pair1 = FilePair(archive_path, preview_path)
        file_pair2 = FilePair(archive_path + "2", preview_path + "2")
        
        # Zapisz testowe metadane do pliku
        metadata_dir = os.path.join(temp_dir, metadata_manager.METADATA_DIR_NAME)
        os.makedirs(metadata_dir, exist_ok=True)
        
        metadata_path = os.path.join(metadata_dir, metadata_manager.METADATA_FILE_NAME)
        
        # Pobierz względne ścieżki dla testów
        rel_path1 = metadata_manager.get_relative_path(archive_path, temp_dir)
        
        test_metadata = {
            "file_pairs": {
                rel_path1: {"is_favorite": True}
            }
        }
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(test_metadata, f)
        
        # Zastosuj metadane
        result = metadata_manager.apply_metadata_to_file_pairs(temp_dir, [file_pair1, file_pair2])
        
        assert result is True
        assert file_pair1.is_favorite is True  # Ten powinien być ulubiony
        assert file_pair2.is_favorite is False  # Ten nie powinien być zmieniony
    
    def test_save_load_cycle(self, temp_dir):
        """Test cyklu zapis -> odczyt metadanych."""
        # Utwórz testowe obiekty FilePair
        archive_path = os.path.join(temp_dir, "archive.zip")
        preview_path = os.path.join(temp_dir, "preview.jpg")
        
        file_pair = FilePair(archive_path, preview_path)
        file_pair.is_favorite = True
        
        # Zapisz metadane
        metadata_manager.save_metadata(temp_dir, [file_pair])
        
        # Utwórz nowy obiekt FilePair z taką samą ścieżką (symulacja ponownego wczytania)
        new_file_pair = FilePair(archive_path, preview_path)
        assert new_file_pair.is_favorite is False  # Początkowo nie jest ulubiony
        
        # Zastosuj metadane
        metadata_manager.apply_metadata_to_file_pairs(temp_dir, [new_file_pair])
        
        # Sprawdź czy status został przywrócony
        assert new_file_pair.is_favorite is True
