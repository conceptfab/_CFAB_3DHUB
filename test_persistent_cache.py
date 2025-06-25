#!/usr/bin/env python3
"""
Test dla Persistent Cache Manager.
"""

import os
import tempfile
import shutil
import time
from pathlib import Path

# Dodaj ścieżkę do src
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.logic.persistent_cache_manager import PersistentCacheManager, PersistentCacheConfig
from src.models.file_pair import FilePair
from src.models.special_folder import SpecialFolder

def test_persistent_cache():
    """Test podstawowej funkcjonalności persistent cache."""
    
    # Utwórz tymczasowy folder testowy
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"🧪 Test folder: {temp_dir}")
        
        # Utwórz kilka plików testowych
        test_files = [
            "model1.blend",
            "model1.jpg", 
            "model2.blend",
            "model2.png",
            "texture1.jpg"
        ]
        
        for file_name in test_files:
            file_path = os.path.join(temp_dir, file_name)
            with open(file_path, 'w') as f:
                f.write(f"Test content for {file_name}")
        
        # Utwórz cache manager
        config = PersistentCacheConfig(
            max_cache_age_days=1
        )
        cache_manager = PersistentCacheManager(config)
        
        print("✅ Cache manager utworzony")
        
        # Test 1: Sprawdź czy cache path jest tworzony
        cache_path = cache_manager.get_cache_path(temp_dir)
        print(f"📁 Cache path: {cache_path}")
        
        # Test 2: Zapisz scan result
        file_pairs = [
            FilePair(
                archive_path=os.path.join(temp_dir, "model1.blend"),
                preview_path=os.path.join(temp_dir, "model1.jpg"),
                working_directory=temp_dir
            ),
            FilePair(
                archive_path=os.path.join(temp_dir, "model2.blend"),
                preview_path=os.path.join(temp_dir, "model2.png"),
                working_directory=temp_dir
            )
        ]
        
        unpaired_archives = []
        unpaired_previews = [os.path.join(temp_dir, "texture1.jpg")]
        special_folders = [
            SpecialFolder("tex", os.path.join(temp_dir, "tex"), 5)
        ]
        
        cache_manager.save_scan_result(
            temp_dir, "first_match", file_pairs, unpaired_archives, unpaired_previews, special_folders
        )
        
        print("✅ Scan result zapisany do cache")
        
        # Test 3: Sprawdź czy cache został utworzony
        if cache_path.exists():
            print(f"✅ Cache folder utworzony: {cache_path}")
            print(f"📄 Zawartość cache:")
            for item in cache_path.rglob("*"):
                if item.is_file():
                    print(f"   📄 {item.relative_to(cache_path)}")
        else:
            print("❌ Cache folder nie został utworzony!")
            return False
        
        # Test 4: Załaduj scan result z cache
        loaded_result = cache_manager.get_scan_result(temp_dir, "first_match")
        if loaded_result:
            loaded_pairs, loaded_archives, loaded_previews, loaded_folders = loaded_result
            print(f"✅ Scan result załadowany z cache:")
            print(f"   📊 Pary: {len(loaded_pairs)}")
            print(f"   📊 Niesparowane archiwa: {len(loaded_archives)}")
            print(f"   📊 Niesparowane podglądy: {len(loaded_previews)}")
            print(f"   📊 Foldery specjalne: {len(loaded_folders)}")
        else:
            print("❌ Nie udało się załadować scan result z cache!")
            return False
        
        # Test 5: Sprawdź statystyki cache
        stats = cache_manager.get_cache_stats(temp_dir)
        print(f"📊 Statystyki cache:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # Test 6: Test mtime validation - zmodyfikuj plik
        time.sleep(1)  # Poczekaj żeby mtime się zmienił
        test_file = os.path.join(temp_dir, "model1.blend")
        with open(test_file, 'a') as f:
            f.write("Modified content")
        
        # Sprawdź czy cache jest nieważny po modyfikacji
        invalid_result = cache_manager.get_scan_result(temp_dir, "first_match")
        if invalid_result is None:
            print("✅ Cache prawidłowo unieważniony po modyfikacji pliku")
        else:
            print("❌ Cache nie został unieważniony po modyfikacji pliku!")
            return False
        
        # Test 7: Wyczyść cache
        cache_manager.clear_cache(temp_dir)
        if not cache_path.exists():
            print("✅ Cache prawidłowo wyczyszczony")
        else:
            print("❌ Cache nie został wyczyszczony!")
            return False
        
        print("\n🎉 WSZYSTKIE TESTY PRZESZŁY POMYŚLNIE!")
        return True

if __name__ == "__main__":
    success = test_persistent_cache()
    if success:
        print("\n✅ Persistent Cache Manager działa poprawnie!")
        sys.exit(0)
    else:
        print("\n❌ Testy nie przeszły!")
        sys.exit(1) 