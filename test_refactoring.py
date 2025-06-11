#!/usr/bin/env python3
"""
Test szybki weryfikujący funkcjonalność po refaktoryzacji ETAP 1.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test importów wszystkich zrefaktoryzowanych modułów."""
    try:
        from src.logic.scanner import scan_folder_for_pairs, collect_files_streaming
        from src.logic.scan_cache import unified_cache, clear_cache
        from src.logic.scanner_core import ScanningInterrupted
        from src.logic.file_pairing import create_file_pairs
        print("✅ Wszystkie importy OK")
        return True
    except Exception as e:
        print(f"❌ Błąd importu: {e}")
        return False

def test_cache_functionality():
    """Test podstawowej funkcjonalności cache."""
    try:
        from src.logic.scan_cache import unified_cache, clear_cache
        
        # Test file_map API
        test_dir = "c:\\test_directory"
        test_file_map = {"png": ["file1.png", "file2.png"], "raw": ["file1.cr2"]}
        
        # Clear cache przed testem
        clear_cache()
        
        # Test store/get file_map
        unified_cache.store_file_map(test_dir, test_file_map)
        retrieved = unified_cache.get_file_map(test_dir)
        
        if retrieved is not None:
            print("✅ Cache store/get file_map działa poprawnie")
        else:
            print("❌ Cache store/get file_map nie działa")
            return False
            
        # Test get_cache_entry
        entry = unified_cache.get_cache_entry(test_dir)
        if entry is not None:
            print("✅ Cache get_cache_entry działa poprawnie")
        else:
            print("❌ Cache get_cache_entry nie działa")
            return False
            
        # Test clear
        clear_cache()
        entry_after_clear = unified_cache.get_cache_entry(test_dir)
        if entry_after_clear is None:
            print("✅ Cache clear działa poprawnie")
            return True
        else:
            print("❌ Cache clear nie działa")
            return False
            
    except Exception as e:
        print(f"❌ Błąd testu cache: {e}")
        return False

def test_scanner_api():
    """Test API skanera po refaktoryzacji."""
    try:
        from src.logic.scanner import scan_folder_for_pairs, collect_files_streaming
        
        # Test czy funkcje są dostępne i można je wywołać
        # (bez faktycznego skanowania, bo nie wiemy czy testowy folder istnieje)
        if callable(scan_folder_for_pairs):
            print("✅ scan_folder_for_pairs jest dostępne")
        else:
            print("❌ scan_folder_for_pairs nie jest funkcją")
            return False
            
        if callable(collect_files_streaming):
            print("✅ collect_files_streaming jest dostępne")
        else:
            print("❌ collect_files_streaming nie jest funkcją")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Błąd testu API skanera: {e}")
        return False

def test_deprecated_removal():
    """Test czy deprecated funkcje zostały usunięte."""
    try:
        from src.logic import scanner
        
        # Sprawdź czy collect_files (deprecated) nie istnieje
        if hasattr(scanner, 'collect_files'):
            print("❌ Deprecated collect_files nadal istnieje!")
            return False
        else:
            print("✅ Deprecated collect_files została usunięta")
            
        return True
        
    except Exception as e:
        print(f"❌ Błąd testu deprecated: {e}")
        return False

def main():
    """Uruchom wszystkie testy refaktoryzacji."""
    print("🔍 Test refaktoryzacji ETAP 1")
    print("=" * 50)
    
    tests = [
        ("Importy modułów", test_imports),
        ("Funkcjonalność cache", test_cache_functionality), 
        ("API skanera", test_scanner_api),
        ("Usunięcie deprecated", test_deprecated_removal)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        if test_func():
            passed += 1
        
    print("\n" + "=" * 50)
    print(f"📊 Wyniki: {passed}/{total} testów przeszło")
    
    if passed == total:
        print("🎉 Refaktoryzacja ETAP 1 zakończona pomyślnie!")
        return True
    else:
        print("⚠️ Niektóre testy nie przeszły - wymagane poprawki")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
