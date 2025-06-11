"""
Testy integracyjne dla zrefaktoryzowanego skanera.
"""

import pytest
import tempfile
import os
from unittest.mock import patch

from src.logic.scanner import (
    scan_folder_for_pairs,
    clear_cache,
    get_scan_statistics,
    ScanningInterrupted
)


class TestScannerIntegration:
    """Testy integracji między modułami skanera."""
    
    def setup_method(self):
        """Setup przed każdym testem."""
        self.temp_dir = tempfile.mkdtemp()
        clear_cache()  # Wyczyść cache przed każdym testem
    
    def teardown_method(self):
        """Cleanup po każdym teście."""
        clear_cache()
    
    def test_scan_folder_for_pairs_empty_directory(self):
        """Test skanowania pustego katalogu."""
        pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(self.temp_dir)
        
        assert pairs == []
        assert unpaired_archives == []
        assert unpaired_previews == []
    
    def test_scan_folder_for_pairs_nonexistent_directory(self):
        """Test skanowania nieistniejącego katalogu."""
        pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs("/nonexistent/dir")
        
        assert pairs == []
        assert unpaired_archives == []
        assert unpaired_previews == []
    
    def test_scan_folder_for_pairs_complete_workflow(self):
        """Test kompletnego workflow skanowania."""
        # Utworzenie struktury plików testowych
        # Para 1: dokładne dopasowanie
        archive1 = os.path.join(self.temp_dir, "photo001.zip")
        preview1 = os.path.join(self.temp_dir, "photo001.jpg")
        
        # Para 2: częściowe dopasowanie
        archive2 = os.path.join(self.temp_dir, "image.rar")
        preview2 = os.path.join(self.temp_dir, "image_preview.png")
        
        # Niesparowane pliki
        unpaired_archive = os.path.join(self.temp_dir, "standalone.7z")
        unpaired_preview = os.path.join(self.temp_dir, "orphan.gif")
        
        # Utworzenie plików
        test_files = [archive1, preview1, archive2, preview2, unpaired_archive, unpaired_preview]
        for file_path in test_files:
            with open(file_path, "w") as f:
                f.write("test content")
        
        # Skanowanie z różnymi strategiami
        for strategy in ["first_match", "all_combinations", "best_match"]:
            pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
                self.temp_dir, pair_strategy=strategy
            )
            
            # Sprawdzamy wyniki
            assert len(pairs) >= 1, f"Strategy {strategy} should find at least 1 pair"
            assert len(unpaired_archives) >= 1, f"Strategy {strategy} should find unpaired archives"
            assert len(unpaired_previews) >= 1, f"Strategy {strategy} should find unpaired previews"
            
            # Sprawdzamy typy zwracanych obiektów
            for pair in pairs:
                assert hasattr(pair, 'archive_path')
                assert hasattr(pair, 'preview_path')
            
            for archive in unpaired_archives:
                assert isinstance(archive, str)
                assert os.path.exists(archive)
            
            for preview in unpaired_previews:
                assert isinstance(preview, str)
                assert os.path.exists(preview)
    
    def test_scan_folder_for_pairs_with_cache(self):
        """Test funkcjonowania cache między skanowaniami."""
        # Utworzenie plików testowych
        archive = os.path.join(self.temp_dir, "test.zip")
        preview = os.path.join(self.temp_dir, "test.jpg")
        
        for file_path in [archive, preview]:
            with open(file_path, "w") as f:
                f.write("test content")
        
        # Pierwsze skanowanie - cache miss
        stats_before = get_scan_statistics()
        pairs1, _, _ = scan_folder_for_pairs(self.temp_dir, use_cache=True)
        stats_after_first = get_scan_statistics()
        
        # Drugie skanowanie - cache hit
        pairs2, _, _ = scan_folder_for_pairs(self.temp_dir, use_cache=True)
        stats_after_second = get_scan_statistics()
        
        # Sprawdzamy czy wyniki są identyczne
        assert len(pairs1) == len(pairs2) == 1
        
        # Sprawdzamy czy cache działał
        assert stats_after_second["cache_hits"] > stats_after_first["cache_hits"]
    
    def test_scan_folder_for_pairs_force_refresh_cache(self):
        """Test wymuszenia odświeżenia cache."""
        # Utworzenie plików testowych
        archive = os.path.join(self.temp_dir, "test.zip")
        preview = os.path.join(self.temp_dir, "test.jpg")
        
        for file_path in [archive, preview]:
            with open(file_path, "w") as f:
                f.write("test content")
        
        # Pierwsze skanowanie
        pairs1, _, _ = scan_folder_for_pairs(self.temp_dir, use_cache=True)
        
        # Drugie skanowanie z force_refresh_cache=True
        pairs2, _, _ = scan_folder_for_pairs(
            self.temp_dir, 
            use_cache=True, 
            force_refresh_cache=True
        )
        
        # Wyniki powinny być identyczne
        assert len(pairs1) == len(pairs2) == 1
    
    def test_scan_folder_for_pairs_with_progress_callback(self):
        """Test z funkcją callback postępu."""
        progress_calls = []
        
        def progress_callback(percent, message):
            progress_calls.append((percent, message))
        
        # Utworzenie plików testowych
        archive = os.path.join(self.temp_dir, "test.zip")
        preview = os.path.join(self.temp_dir, "test.jpg")
        
        for file_path in [archive, preview]:
            with open(file_path, "w") as f:
                f.write("test content")
        
        pairs, _, _ = scan_folder_for_pairs(
            self.temp_dir, 
            progress_callback=progress_callback
        )
        
        # Sprawdzamy czy callback był wywoływany
        assert len(progress_calls) > 0
        
        # Sprawdzamy czy progress zwiększał się
        percentages = [call[0] for call in progress_calls]
        assert 0 in percentages  # Start
        assert 100 in percentages  # End
        
        # Sprawdzamy czy są komunikaty
        messages = [call[1] for call in progress_calls]
        assert all(isinstance(msg, str) for msg in messages)
    
    def test_scan_folder_for_pairs_with_interrupt(self):
        """Test przerwania skanowania."""
        interrupt_call_count = 0
        
        def interrupt_check():
            nonlocal interrupt_call_count
            interrupt_call_count += 1
            return interrupt_call_count > 2  # Przerwij po kilku wywołaniach
        
        # Utworzenie plików testowych
        archive = os.path.join(self.temp_dir, "test.zip")
        preview = os.path.join(self.temp_dir, "test.jpg")
        
        for file_path in [archive, preview]:
            with open(file_path, "w") as f:
                f.write("test content")
        
        # Skanowanie powinno być przerwane
        with pytest.raises(ScanningInterrupted):
            scan_folder_for_pairs(
                self.temp_dir, 
                interrupt_check=interrupt_check
            )
        
        assert interrupt_call_count > 2
    
    def test_scan_folder_for_pairs_max_depth(self):
        """Test ograniczenia głębokości skanowania."""
        # Utworzenie struktury folderów
        sub_dir = os.path.join(self.temp_dir, "subdir")
        deep_dir = os.path.join(sub_dir, "deep")
        os.makedirs(deep_dir)
        
        # Pliki na różnych poziomach
        main_archive = os.path.join(self.temp_dir, "main.zip")
        main_preview = os.path.join(self.temp_dir, "main.jpg")
        sub_archive = os.path.join(sub_dir, "sub.zip")
        sub_preview = os.path.join(sub_dir, "sub.jpg")
        deep_archive = os.path.join(deep_dir, "deep.zip")
        deep_preview = os.path.join(deep_dir, "deep.jpg")
        
        all_files = [main_archive, main_preview, sub_archive, sub_preview, deep_archive, deep_preview]
        for file_path in all_files:
            with open(file_path, "w") as f:
                f.write("test content")
        
        # Test z max_depth = 0 (tylko główny katalog)
        pairs_0, _, _ = scan_folder_for_pairs(self.temp_dir, max_depth=0)
        assert len(pairs_0) == 1  # Tylko para z głównego katalogu
        
        # Test z max_depth = 1 (główny + pierwszy poziom)
        pairs_1, _, _ = scan_folder_for_pairs(self.temp_dir, max_depth=1)
        assert len(pairs_1) == 2  # Pary z głównego i sub katalogu
        
        # Test z max_depth = -1 (bez limitu)
        pairs_all, _, _ = scan_folder_for_pairs(self.temp_dir, max_depth=-1)
        assert len(pairs_all) == 3  # Wszystkie pary
    
    def test_clear_cache_integration(self):
        """Test czyszczenia cache w kontekście integracji."""
        # Utworzenie plików testowych
        archive = os.path.join(self.temp_dir, "test.zip")
        preview = os.path.join(self.temp_dir, "test.jpg")
        
        for file_path in [archive, preview]:
            with open(file_path, "w") as f:
                f.write("test content")
        
        # Skanowanie - powinno zapełnić cache
        scan_folder_for_pairs(self.temp_dir)
        stats_before = get_scan_statistics()
        assert stats_before["cache_entries"] > 0
        
        # Wyczyszczenie cache
        clear_cache()
        stats_after = get_scan_statistics()
        assert stats_after["cache_entries"] == 0
        assert stats_after["cache_hits"] == 0
        assert stats_after["cache_misses"] == 0
    
    def test_get_scan_statistics_integration(self):
        """Test funkcji statystyk w kontekście integracji."""
        # Początkowe statystyki
        initial_stats = get_scan_statistics()
        assert initial_stats["cache_entries"] == 0
        
        # Utworzenie plików testowych
        archive = os.path.join(self.temp_dir, "test.zip")
        preview = os.path.join(self.temp_dir, "test.jpg")
        
        for file_path in [archive, preview]:
            with open(file_path, "w") as f:
                f.write("test content")
        
        # Skanowanie
        scan_folder_for_pairs(self.temp_dir)
        after_scan_stats = get_scan_statistics()
        
        # Cache powinien zawierać wpisy
        assert after_scan_stats["cache_entries"] > initial_stats["cache_entries"]
        
        # Ponowne skanowanie (cache hit)
        scan_folder_for_pairs(self.temp_dir)
        final_stats = get_scan_statistics()
        
        # Hits powinny wzrosnąć
        assert final_stats["cache_hits"] > after_scan_stats["cache_hits"]
