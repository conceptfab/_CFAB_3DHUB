#!/usr/bin/env python3
"""
SKRYPT DO URUCHAMIANIA TESTÓW REALNEJ GALERII
Uruchamia kompleksowe testy na folderze _test_gallery
"""

import sys
from pathlib import Path

# Dodaj src do ścieżki
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.test_gallery_environment import RealGalleryTestEnvironment


def main():
    """Główna funkcja uruchamiająca testy"""
    print("🧪 URUCHAMIANIE TESTÓW REALNEJ GALERII")
    print("=" * 60)
    print(f"📁 Projekt: {project_root}")
    print(f"📂 Galeria testowa: {project_root}/_test_gallery")
    print()

    # Sprawdź czy galeria testowa istnieje
    gallery_path = project_root / "_test_gallery"
    if not gallery_path.exists():
        print("❌ BŁĄD: Galeria testowa nie istnieje!")
        print(f"   Oczekiwana ścieżka: {gallery_path}")
        print("   Utwórz folder _test_gallery z plikami testowymi")
        return 1

    # Sprawdź czy są pliki WebP
    webp_files = list(gallery_path.glob("*.webp"))
    if len(webp_files) == 0:
        print("❌ BŁĄD: Brak plików WebP w galerii testowej!")
        print("   Dodaj pliki .webp do folderu _test_gallery")
        return 1

    print(f"✅ Znaleziono {len(webp_files)} plików WebP")

    # Sprawdź archiwa
    bez_pary_path = gallery_path / "_bez_pary_"
    if bez_pary_path.exists():
        archive_files = list(bez_pary_path.glob("*.*"))
        print(f"✅ Znaleziono {len(archive_files)} archiwów w _bez_pary_")
    else:
        print("⚠️ Brak folderu _bez_pary_ (opcjonalny)")

    print()

    # Uruchom testy
    try:
        env = RealGalleryTestEnvironment()
        env.setup_test_environment()

        print("🚀 URUCHAMIANIE KOMPLEKSOWEGO ZESTAWU TESTÓW")
        print("=" * 60)

        results = env.run_comprehensive_test_suite()

        print("\n📋 PODSUMOWANIE WYNIKÓW:")
        print("=" * 40)

        success_count = 0
        total_tests = 0

        for test_name, result in results.items():
            total_tests += 1

            if isinstance(result, dict) and "error" in result:
                print(f"❌ {test_name}: BŁĄD - {result['error']}")
            else:
                print(f"✅ {test_name}: OK")
                success_count += 1

                if hasattr(result, "scan_time_ms"):
                    print(f"   📊 Skanowanie: {result.scan_time_ms:.2f}ms")
                if hasattr(result, "gallery_load_time_ms"):
                    print(f"   📊 Galeria: {result.gallery_load_time_ms:.2f}ms")
                if hasattr(result, "tile_creation_time_ms"):
                    print(f"   📊 Kafelki: {result.tile_creation_time_ms:.2f}ms")
                if hasattr(result, "memory_usage_mb"):
                    print(f"   📊 Pamięć: {result.memory_usage_mb:.2f}MB")

        print()
        print(f"📊 WYNIKI: {success_count}/{total_tests} testów przeszło")

        if success_count == total_tests:
            print("🎉 WSZYSTKIE TESTY ZAKOŃCZONE POMYŚLNIE!")
            return 0
        else:
            print("⚠️ NIEKTÓRE TESTY NIE PRZESZŁY")
            return 1

    except Exception as e:
        print(f"❌ BŁĄD KRYTYCZNY: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        if "env" in locals():
            env.cleanup_test_environment()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
