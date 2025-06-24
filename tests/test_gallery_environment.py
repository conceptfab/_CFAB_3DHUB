#!/usr/bin/env python3
"""
PROFESJONALNE ŚRODOWISKO TESTOWE DLA REALNEJ GALERII
Testuje aplikację na rzeczywistych danych z _test_gallery (321 WebP + 4 archiwa)
"""

import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import pytest
from PyQt6.QtWidgets import QApplication

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.logic.scanner_core import scan_folder_for_pairs
from src.ui.main_window.main_window import MainWindow
from src.ui.widgets.file_tile_widget import FileTileWidget


@dataclass
class GalleryTestStats:
    """Statystyki testów galerii"""

    total_files: int
    webp_files: int
    archive_files: int
    paired_files: int
    unpaired_files: int
    scan_time_ms: float
    gallery_load_time_ms: float
    memory_usage_mb: float
    tile_creation_time_ms: float


class RealGalleryTestEnvironment:
    """Środowisko testowe dla realnej galerii"""

    def __init__(self):
        self.test_gallery_path = project_root / "_test_gallery"
        self.temp_working_dir = None
        self.main_window = None
        self.gallery_manager = None
        self.stats = None

        # Sprawdź czy galeria testowa istnieje
        if not self.test_gallery_path.exists():
            raise FileNotFoundError(
                f"Galeria testowa nie istnieje: {self.test_gallery_path}"
            )

    def setup_test_environment(self) -> None:
        """Przygotowanie środowiska testowego"""
        print("🔧 Przygotowanie środowiska testowego...")
        print(f"📁 Galeria testowa: {self.test_gallery_path}")

        # Utwórz tymczasowy katalog roboczy
        self.temp_working_dir = tempfile.mkdtemp(prefix="gallery_test_")
        print(f"📂 Katalog roboczy: {self.temp_working_dir}")

        # Inicjalizuj QApplication jeśli nie istnieje
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

        # Utwórz główne okno aplikacji
        self.main_window = MainWindow()
        self.gallery_manager = self.main_window.gallery_manager

        print("✅ Środowisko testowe gotowe")

    def cleanup_test_environment(self) -> None:
        """Czyszczenie środowiska testowego"""
        print("🧹 Czyszczenie środowiska testowego...")

        if self.main_window:
            self.main_window.close()
            self.main_window.deleteLater()

        if self.temp_working_dir and os.path.exists(self.temp_working_dir):
            shutil.rmtree(self.temp_working_dir, ignore_errors=True)

        print("✅ Środowisko testowe wyczyszczone")

    def get_gallery_statistics(self) -> Dict[str, int]:
        """Pobiera statystyki galerii testowej"""
        stats = {
            "total_files": 0,
            "webp_files": 0,
            "archive_files": 0,
            "metadata_files": 0,
        }

        # Licz pliki w głównym folderze
        for file_path in self.test_gallery_path.iterdir():
            if file_path.is_file():
                stats["total_files"] += 1
                if file_path.suffix.lower() == ".webp":
                    stats["webp_files"] += 1

        # Licz archiwa w _bez_pary_
        bez_pary_path = self.test_gallery_path / "_bez_pary_"
        if bez_pary_path.exists():
            for file_path in bez_pary_path.iterdir():
                if file_path.is_file():
                    stats["archive_files"] += 1

        # Sprawdź metadane
        metadata_path = self.test_gallery_path / ".app_metadata" / "metadata.json"
        if metadata_path.exists():
            stats["metadata_files"] = 1

        return stats

    def test_full_gallery_scan(self) -> GalleryTestStats:
        """Test pełnego skanowania galerii"""
        print("🔍 Test pełnego skanowania galerii...")

        start_time = time.time()

        # Skanuj galerię
        file_pairs, unpaired_previews, unpaired_archives, special_folders = (
            scan_folder_for_pairs(str(self.test_gallery_path), max_depth=2)
        )

        scan_time_ms = (time.time() - start_time) * 1000

        print(f"📊 Wyniki skanowania:")
        print(f"   - Znalezione pary: {len(file_pairs)}")
        print(f"   - Nieparowane podglądy: {len(unpaired_previews)}")
        print(f"   - Nieparowane archiwa: {len(unpaired_archives)}")
        print(f"   - Czas skanowania: {scan_time_ms:.2f}ms")

        total_files = len(file_pairs) + len(unpaired_previews) + len(unpaired_archives)

        unpaired_files = len(unpaired_previews) + len(unpaired_archives)

        return GalleryTestStats(
            total_files=total_files,
            webp_files=len(unpaired_previews),
            archive_files=len(unpaired_archives),
            paired_files=len(file_pairs),
            unpaired_files=unpaired_files,
            scan_time_ms=scan_time_ms,
            gallery_load_time_ms=0,
            memory_usage_mb=0,
            tile_creation_time_ms=0,
        )

    def test_gallery_manager_performance(self) -> GalleryTestStats:
        """Test wydajności GalleryManager"""
        print("⚡ Test wydajności GalleryManager...")

        # Skanuj galerię
        file_pairs, unpaired_previews, unpaired_archives, special_folders = (
            scan_folder_for_pairs(str(self.test_gallery_path), max_depth=2)
        )

        # Test ładowania galerii
        start_time = time.time()

        self.gallery_manager.file_pairs_list = file_pairs
        self.gallery_manager.update_gallery_view()

        gallery_load_time_ms = (time.time() - start_time) * 1000

        # Pobierz statystyki pamięci
        memory_usage_mb = self._get_memory_usage()

        print(f"📊 Wydajność GalleryManager:")
        print(f"   - Czas ładowania: {gallery_load_time_ms:.2f}ms")
        print(f"   - Użycie pamięci: {memory_usage_mb:.2f}MB")

        return GalleryTestStats(
            total_files=len(file_pairs),
            webp_files=0,
            archive_files=0,
            paired_files=len(file_pairs),
            unpaired_files=0,
            scan_time_ms=0,
            gallery_load_time_ms=gallery_load_time_ms,
            memory_usage_mb=memory_usage_mb,
            tile_creation_time_ms=0,
        )

    def test_tile_creation_performance(self, sample_size: int = 10) -> GalleryTestStats:
        """Test wydajności tworzenia kafelków"""
        print(f"🎯 Test tworzenia kafelków (próbka: {sample_size})...")

        # Skanuj galerię
        file_pairs, unpaired_previews, unpaired_archives, special_folders = (
            scan_folder_for_pairs(str(self.test_gallery_path), max_depth=2)
        )

        if not file_pairs:
            print("⚠️ Brak par plików do testowania")
            return GalleryTestStats(0, 0, 0, 0, 0, 0, 0, 0, 0)

        # Weź próbkę par
        sample_pairs = file_pairs[:sample_size]

        start_time = time.time()
        tiles_created = 0

        for file_pair in sample_pairs:
            try:
                tile = FileTileWidget(file_pair)
                tiles_created += 1
                tile.deleteLater()
            except Exception as e:
                print(f"❌ Błąd tworzenia kafelka: {e}")

        tile_creation_time_ms = (time.time() - start_time) * 1000

        print(f"📊 Wydajność tworzenia kafelków:")
        print(f"   - Utworzone kafelki: {tiles_created}/{sample_size}")
        print(f"   - Czas tworzenia: {tile_creation_time_ms:.2f}ms")
        avg_time = tile_creation_time_ms / sample_size
        print(f"   - Średni czas/kafelek: {avg_time:.2f}ms")

        return GalleryTestStats(
            total_files=sample_size,
            webp_files=0,
            archive_files=0,
            paired_files=sample_size,
            unpaired_files=0,
            scan_time_ms=0,
            gallery_load_time_ms=0,
            memory_usage_mb=0,
            tile_creation_time_ms=tile_creation_time_ms,
        )

    def test_memory_usage_under_load(self) -> Dict[str, float]:
        """Test użycia pamięci pod obciążeniem"""
        print("💾 Test użycia pamięci pod obciążeniem...")

        memory_before = self._get_memory_usage()

        # Skanuj galerię
        file_pairs, unpaired_previews, unpaired_archives, special_folders = (
            scan_folder_for_pairs(str(self.test_gallery_path), max_depth=2)
        )

        # Załaduj galerię
        self.gallery_manager.file_pairs_list = file_pairs
        self.gallery_manager.update_gallery_view()

        memory_after = self._get_memory_usage()
        memory_increase = memory_after - memory_before

        print(f"📊 Użycie pamięci:")
        print(f"   - Przed: {memory_before:.2f}MB")
        print(f"   - Po: {memory_after:.2f}MB")
        print(f"   - Wzrost: {memory_increase:.2f}MB")

        return {
            "before_mb": memory_before,
            "after_mb": memory_after,
            "increase_mb": memory_increase,
        }

    def _get_memory_usage(self) -> float:
        """Pobiera aktualne użycie pamięci procesu"""
        try:
            import psutil

            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            return 0.0

    def run_comprehensive_test_suite(self) -> Dict[str, any]:
        """Uruchamia kompleksowy zestaw testów"""
        print("🚀 URUCHAMIANIE KOMPLEKSOWEGO ZESTAWU TESTÓW")
        print("=" * 60)

        results = {}

        try:
            # 1. Statystyki galerii
            print("\n📊 1. ANALIZA GALERII TESTOWEJ")
            gallery_stats = self.get_gallery_statistics()
            results["gallery_statistics"] = gallery_stats
            print(f"   - Pliki WebP: {gallery_stats['webp_files']}")
            print(f"   - Archiwa: {gallery_stats['archive_files']}")
            print(f"   - Metadane: {gallery_stats['metadata_files']}")

            # 2. Test skanowania
            print("\n🔍 2. TEST SKANOWANIA")
            scan_stats = self.test_full_gallery_scan()
            results["scan_performance"] = scan_stats

            # 3. Test GalleryManager
            print("\n⚡ 3. TEST GALLERY MANAGER")
            gallery_stats = self.test_gallery_manager_performance()
            results["gallery_performance"] = gallery_stats

            # 4. Test tworzenia kafelków
            print("\n🎯 4. TEST TWORZENIA KAFLIKÓW")
            tile_stats = self.test_tile_creation_performance(sample_size=20)
            results["tile_performance"] = tile_stats

            # 5. Test pamięci
            print("\n💾 5. TEST PAMIĘCI")
            memory_stats = self.test_memory_usage_under_load()
            results["memory_usage"] = memory_stats

            print("\n✅ WSZYSTKIE TESTY ZAKOŃCZONE POMYŚLNIE")

        except Exception as e:
            print(f"\n❌ BŁĄD PODCZAS TESTÓW: {e}")
            results["error"] = str(e)

        return results


# Testy pytest
class TestRealGalleryEnvironment:
    """Testy dla środowiska realnej galerii"""

    @pytest.fixture(scope="class")
    def test_environment(self):
        """Przygotowanie środowiska testowego"""
        env = RealGalleryTestEnvironment()
        env.setup_test_environment()
        yield env
        env.cleanup_test_environment()

    def test_gallery_exists(self):
        """Test czy galeria testowa istnieje"""
        gallery_path = project_root / "_test_gallery"
        assert gallery_path.exists(), f"Galeria testowa nie istnieje: {gallery_path}"

        # Sprawdź czy są pliki WebP
        webp_files = list(gallery_path.glob("*.webp"))
        assert len(webp_files) > 0, "Brak plików WebP w galerii testowej"

        print(f"✅ Galeria testowa OK: {len(webp_files)} plików WebP")

    def test_gallery_statistics(self, test_environment):
        """Test statystyk galerii"""
        stats = test_environment.get_gallery_statistics()

        assert (
            stats["webp_files"] > 300
        ), f"Oczekiwano >300 WebP, znaleziono: {stats['webp_files']}"
        assert stats["archive_files"] > 0, "Brak archiwów w _bez_pary_"

        print(
            f"✅ Statystyki galerii OK: {stats['webp_files']} WebP, {stats['archive_files']} archiwów"
        )

    def test_full_scan_performance(self, test_environment):
        """Test wydajności pełnego skanowania"""
        stats = test_environment.test_full_gallery_scan()

        assert (
            stats.scan_time_ms < 10000
        ), f"Skanowanie za wolne: {stats.scan_time_ms}ms"
        assert stats.total_files > 300, f"Za mało plików: {stats.total_files}"

        print(
            f"✅ Skanowanie OK: {stats.scan_time_ms:.2f}ms dla {stats.total_files} plików"
        )

    def test_gallery_manager_performance(self, test_environment):
        """Test wydajności GalleryManager"""
        stats = test_environment.test_gallery_manager_performance()

        assert (
            stats.gallery_load_time_ms < 5000
        ), f"Ładowanie galerii za wolne: {stats.gallery_load_time_ms}ms"

        print(f"✅ GalleryManager OK: {stats.gallery_load_time_ms:.2f}ms")

    def test_tile_creation_performance(self, test_environment):
        """Test wydajności tworzenia kafelków"""
        stats = test_environment.test_tile_creation_performance(sample_size=10)

        assert (
            stats.tile_creation_time_ms < 1000
        ), f"Tworzenie kafelków za wolne: {stats.tile_creation_time_ms}ms"

        print(f"✅ Tworzenie kafelków OK: {stats.tile_creation_time_ms:.2f}ms")

    def test_memory_usage(self, test_environment):
        """Test użycia pamięci"""
        memory_stats = test_environment.test_memory_usage_under_load()

        assert (
            memory_stats["increase_mb"] < 500
        ), f"Za duży wzrost pamięci: {memory_stats['increase_mb']}MB"

        print(f"✅ Pamięć OK: wzrost {memory_stats['increase_mb']:.2f}MB")


if __name__ == "__main__":
    print("🧪 URUCHAMIANIE TESTÓW ŚRODOWISKA REALNEJ GALERII")
    print("=" * 60)

    # Uruchom kompleksowy test
    env = RealGalleryTestEnvironment()
    env.setup_test_environment()

    try:
        results = env.run_comprehensive_test_suite()

        print("\n📋 PODSUMOWANIE WYNIKÓW:")
        print("=" * 40)

        for test_name, result in results.items():
            if isinstance(result, GalleryTestStats):
                scan_time = result.scan_time_ms
                gallery_time = result.gallery_load_time_ms
                print(
                    f"{test_name}: {scan_time:.2f}ms scan, {gallery_time:.2f}ms gallery"
                )
            elif isinstance(result, dict):
                print(f"{test_name}: {result}")
            else:
                print(f"{test_name}: {result}")

    finally:
        env.cleanup_test_environment()
