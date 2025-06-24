#!/usr/bin/env python3
"""
COMPARE REVISIONS TEST
Porównuje wydajność bazowego kodu z pierwszą rewizją optymalizacji
"""

import os
import time
import sys
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.logic.file_pairing import create_file_pairs, get_file_info_cache_stats
from src.logic.scanner_core import collect_files_streaming


class RevisionComparisonTest:
    """Test porównawczy między rewizjami kodu"""
    
    def __init__(self, test_gallery_path: str = "_test_gallery"):
        self.test_gallery_path = Path(test_gallery_path).resolve()
        self.backup_dir = project_root / "backup_original"
        self.results = {}
        
        print(f"🔍 Test porównawczy rewizji")
        print(f"📁 Galeria testowa: {self.test_gallery_path}")
        print(f"📊 Pliki w galerii: {len(list(self.test_gallery_path.glob('*')))}")
    
    def run_comparison_test(self) -> Dict:
        """Uruchamia test porównawczy"""
        print("\n🚀 ROZPOCZĘCIE TESTU PORÓWNAWCZEGO")
        print("=" * 60)
        
        # FAZA 1: Test z pierwszą rewizją (obecny kod)
        print("\n📊 FAZA 1: Test z pierwszą rewizją (FileInfoCache)")
        revision1_results = self._test_current_revision()
        
        # FAZA 2: Przywróć bazowy kod
        print("\n📊 FAZA 2: Przywracanie bazowego kodu...")
        self._restore_baseline_code()
        
        # FAZA 3: Test z bazowym kodem
        print("\n📊 FAZA 3: Test z bazowym kodem")
        baseline_results = self._test_baseline_code()
        
        # FAZA 4: Przywróć pierwszą rewizję
        print("\n📊 FAZA 4: Przywracanie pierwszej rewizji...")
        self._restore_revision1_code()
        
        # FAZA 5: Analiza wyników
        print("\n📈 FAZA 5: Analiza wyników...")
        comparison = self._analyze_comparison(baseline_results, revision1_results)
        
        return comparison
    
    def _test_current_revision(self) -> Dict:
        """Testuje obecny kod (pierwsza rewizja)"""
        start_time = time.time()
        
        # Skanowanie
        scan_start = time.time()
        file_map = collect_files_streaming(
            str(self.test_gallery_path),
            max_depth=0
        )
        scan_time = (time.time() - scan_start) * 1000
        
        # Parowanie
        pairing_start = time.time()
        pairs, processed = create_file_pairs(
            file_map,
            str(self.test_gallery_path),
            "best_match"
        )
        pairing_time = (time.time() - pairing_start) * 1000
        
        total_time = (time.time() - start_time) * 1000
        
        # Pobierz statystyki cache
        cache_stats = get_file_info_cache_stats()
        
        results = {
            'revision': 'revision1_fileinfo_cache',
            'total_files': sum(len(files) for files in file_map.values()),
            'pairs_created': len(pairs),
            'scan_time_ms': scan_time,
            'pairing_time_ms': pairing_time,
            'total_time_ms': total_time,
            'pairs_per_second': len(pairs) / (pairing_time / 1000) if pairing_time > 0 else 0,
            'cache_stats': cache_stats
        }
        
        print(f"  ✅ Rewizja 1: {len(pairs)} par w {pairing_time:.2f}ms")
        print(f"     Cache hit ratio: {cache_stats['hit_ratio_percent']}%")
        print(f"     Cache size: {cache_stats['cache_size']}")
        
        return results
    
    def _test_baseline_code(self) -> Dict:
        """Testuje bazowy kod (bez optymalizacji)"""
        start_time = time.time()
        
        # Skanowanie
        scan_start = time.time()
        file_map = collect_files_streaming(
            str(self.test_gallery_path),
            max_depth=0
        )
        scan_time = (time.time() - scan_start) * 1000
        
        # Parowanie
        pairing_start = time.time()
        pairs, processed = create_file_pairs(
            file_map,
            str(self.test_gallery_path),
            "best_match"
        )
        pairing_time = (time.time() - pairing_start) * 1000
        
        total_time = (time.time() - start_time) * 1000
        
        results = {
            'revision': 'baseline',
            'total_files': sum(len(files) for files in file_map.values()),
            'pairs_created': len(pairs),
            'scan_time_ms': scan_time,
            'pairing_time_ms': pairing_time,
            'total_time_ms': total_time,
            'pairs_per_second': len(pairs) / (pairing_time / 1000) if pairing_time > 0 else 0
        }
        
        print(f"  ✅ Bazowy kod: {len(pairs)} par w {pairing_time:.2f}ms")
        
        return results
    
    def _restore_baseline_code(self):
        """Przywraca bazowy kod (usuwa FileInfoCache)"""
        try:
            # Utwórz backup obecnego kodu
            if not self.backup_dir.exists():
                self.backup_dir.mkdir(parents=True)
            
            # Backup obecnego file_pairing.py
            current_file = project_root / "src" / "logic" / "file_pairing.py"
            backup_file = self.backup_dir / "file_pairing_revision1.py"
            
            if current_file.exists():
                shutil.copy2(current_file, backup_file)
                print(f"    💾 Backup utworzony: {backup_file}")
            
            # Przywróć bazowy kod (usuń FileInfoCache)
            self._create_baseline_code()
            print("    ✅ Bazowy kod przywrócony")
            
        except Exception as e:
            print(f"    ❌ Błąd przywracania: {e}")
    
    def _restore_revision1_code(self):
        """Przywraca pierwszą rewizję"""
        try:
            # Przywróć z backupu
            backup_file = self.backup_dir / "file_pairing_revision1.py"
            current_file = project_root / "src" / "logic" / "file_pairing.py"
            
            if backup_file.exists():
                shutil.copy2(backup_file, current_file)
                print("    ✅ Pierwsza rewizja przywrócona")
            else:
                print("    ❌ Brak backupu pierwszej rewizji")
                
        except Exception as e:
            print(f"    ❌ Błąd przywracania: {e}")
    
    def _create_baseline_code(self):
        """Tworzy bazowy kod bez FileInfoCache"""
        baseline_code = '''"""
Moduł odpowiedzialny za parowanie plików.

Ten modik zawiera funkcje do tworzenia par plików (archiwum + podgląd)
oraz identyfikowania niesparowanych plików.
"""

import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from src import app_config
from src.models.file_pair import FilePair

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Używamy definicji rozszerzeń z centralnego pliku konfiguracyjnego
ARCHIVE_EXTENSIONS = set(app_config.SUPPORTED_ARCHIVE_EXTENSIONS)
PREVIEW_EXTENSIONS = set(app_config.SUPPORTED_PREVIEW_EXTENSIONS)


@dataclass
class FileInfo:
    """Pre-computed file information dla performance optimization."""

    def __init__(self, path: str):
        self.path = path
        self.basename = os.path.basename(path)
        self.name_lower = os.path.splitext(self.basename)[0].lower()
        self.ext_lower = os.path.splitext(path)[1].lower()
        self.is_archive = self.ext_lower in ARCHIVE_EXTENSIONS
        self.is_preview = self.ext_lower in PREVIEW_EXTENSIONS


def _categorize_files_optimized(files_list: List[str]) -> Tuple[List[str], List[str]]:
    """
    Optimized kategoryzacja plików na archiwa i podglądy.
    Pre-computes file info once instead of parsing extensions multiple times.
    """
    if not files_list:
        return [], []

    start_time = time.time()

    # Pre-compute file info once - O(n) instead of O(2n)
    file_infos = [FileInfo(f) for f in files_list]

    # Single pass categorization - O(n) instead of O(2n)
    archive_files = [fi.path for fi in file_infos if fi.is_archive]
    preview_files = [fi.path for fi in file_infos if fi.is_preview]

    elapsed = (time.time() - start_time) * 1000
    logger.debug(
        f"File categorization completed: {len(archive_files)} archives, "
        f"{len(preview_files)} previews in {elapsed:.2f}ms"
    )

    return archive_files, preview_files


class SimpleTrie:
    """Thread-safe Simple Trie dla fast prefix matching."""

    def __init__(self, max_size: int = 10000):
        self.root = {}
        self.files = {}  # Maps prefix -> list of files
        self._lock = threading.RLock()
        self._max_size = max_size
        self._size = 0

    def add(self, key: str, file_path: str):
        """Thread-safe addition of file with its prefix key."""
        with self._lock:
            if self._size >= self._max_size:
                logger.warning(
                    f"Trie size limit reached ({self._max_size}), "
                    f"skipping addition of {key}"
                )
                return

            node = self.root
            for char in key:
                if char not in node:
                    node[char] = {}
                node = node[char]

            if key not in self.files:
                self.files[key] = []
                self._size += 1
            self.files[key].append(file_path)

    def find_prefix_matches(self, prefix: str, max_results: int = 20) -> List[str]:
        """Thread-safe prefix matching with sorted keys for O(log k) complexity."""
        with self._lock:
            matches = []

            # Exact match first (highest priority)
            if prefix in self.files:
                matches.extend(self.files[prefix])

            # Use sorted keys for O(log k) complexity
            sorted_keys = sorted(self.files.keys())

            # Binary search-like approach for prefix matches
            for key in sorted_keys:
                if len(matches) >= max_results:
                    break
                if key != prefix and (key.startswith(prefix) or prefix.startswith(key)):
                    matches.extend(self.files[key])

            return matches[:max_results]

    def cleanup(self):
        """Thread-safe cleanup of Trie data structures."""
        with self._lock:
            self.root.clear()
            self.files.clear()
            self._size = 0

    def get_size(self) -> int:
        """Thread-safe size query."""
        with self._lock:
            return self._size

    def get_memory_usage(self) -> int:
        """Estimate memory usage in bytes."""
        with self._lock:
            # Rough estimation: each key ~50 bytes, each file path ~100 bytes
            total_keys = len(self.files)
            total_files = sum(len(files) for files in self.files.values())
            return total_keys * 50 + total_files * 100


class PairingStrategy(ABC):
    """Abstrakcyjna klasa bazowa dla strategii parowania plików."""

    @abstractmethod
    def create_pairs(
        self, archive_files: List[str], preview_files: List[str], base_directory: str
    ) -> Tuple[List[FilePair], Set[str]]:
        """
        Tworzy pary plików według konkretnej strategii.

        Args:
            archive_files: Lista plików archiwów
            preview_files: Lista plików podglądów
            base_directory: Katalog bazowy

        Returns:
            Tuple zawierający listę par i zbiór przetworzonych plików
        """
        pass


class FirstMatchStrategy(PairingStrategy):
    """Strategia parowania pierwszego dopasowania."""

    def create_pairs(
        self, archive_files: List[str], preview_files: List[str], base_directory: str
    ) -> Tuple[List[FilePair], Set[str]]:
        """Tworzy tylko pierwszą parę."""
        pairs = []
        processed = set()

        if archive_files and preview_files:
            try:
                pair = FilePair(archive_files[0], preview_files[0], base_directory)
                pairs.append(pair)
                processed.add(archive_files[0])
                processed.add(preview_files[0])
            except ValueError as e:
                logger.error(
                    f"Błąd tworzenia FilePair dla '{archive_files[0]}' i '{preview_files[0]}': {e}"
                )

        return pairs, processed


class OptimizedBestMatchStrategy(PairingStrategy):
    """Optimized strategia inteligentnego parowania z Trie-based matching."""

    # Simplified preference - tylko extension priority, bez I/O operations
    PREVIEW_PREFERENCE = {
        ".jpg": 60,
        ".jpeg": 55,
        ".png": 50,
        ".gif": 40,
        ".bmp": 30,
        ".tiff": 20,
    }

    def create_pairs(
        self, archive_files: List[str], preview_files: List[str], base_directory: str
    ) -> Tuple[List[FilePair], Set[str]]:
        """Optimized intelligent pairing with Trie-based matching."""
        if not archive_files or not preview_files:
            return [], set()

        start_time = time.time()
        pairs = []
        processed = set()

        # Build preview Trie for fast prefix matching
        preview_trie = self._build_preview_trie(preview_files)

        # Process each archive
        for archive in archive_files:
            if archive in processed:
                continue

            # Find best preview using Trie
            best_preview = self._find_best_preview_optimized(archive, preview_trie)

            if best_preview and best_preview not in processed:
                try:
                    pair = FilePair(archive, best_preview, base_directory)
                    pairs.append(pair)
                    processed.add(archive)
                    processed.add(best_preview)
                except ValueError as e:
                    logger.error(
                        f"Błąd tworzenia FilePair dla '{archive}' i '{best_preview}': {e}"
                    )

        elapsed = (time.time() - start_time) * 1000
        logger.debug(
            f"OptimizedBestMatchStrategy: {len(pairs)} pairs created in {elapsed:.2f}ms"
        )

        return pairs, processed

    def _build_preview_trie(self, preview_files: List[str]) -> SimpleTrie:
        """Builds Trie for preview files."""
        trie = SimpleTrie()
        for preview in preview_files:
            # Use basename without extension as key
            key = os.path.splitext(os.path.basename(preview))[0].lower()
            trie.add(key, preview)
        return trie

    def _find_best_preview_optimized(
        self, archive: str, preview_trie: SimpleTrie
    ) -> str:
        """Finds best preview using Trie-based matching."""
        archive_name = os.path.splitext(os.path.basename(archive))[0].lower()

        # Get prefix matches from Trie
        matches = preview_trie.find_prefix_matches(archive_name, max_results=10)

        if not matches:
            return ""

        # Score matches and return best
        best_preview = ""
        best_score = -1

        for preview in matches:
            score = self._calculate_simple_score(preview, archive_name)
            if score > best_score:
                best_score = score
                best_preview = preview

        return best_preview

    def _calculate_simple_score(self, preview: str, archive_name: str) -> int:
        """Calculates simple matching score."""
        preview_name = os.path.splitext(os.path.basename(preview))[0].lower()
        preview_ext = os.path.splitext(preview)[1].lower()

        # Base score from extension preference
        score = self.PREVIEW_PREFERENCE.get(preview_ext, 0)

        # Bonus for exact name match
        if preview_name == archive_name:
            score += 1000

        # Bonus for partial match
        elif preview_name.startswith(archive_name) or archive_name.startswith(preview_name):
            score += 500

        return score


class OptimizedPairingStrategyFactory:
    """Simplified factory bez dead code."""

    _strategies = {
        "first_match": FirstMatchStrategy(),
        "best_match": OptimizedBestMatchStrategy(),
    }

    @classmethod
    def get_strategy(cls, strategy_name: str) -> PairingStrategy:
        """Gets pairing strategy by name."""
        if strategy_name not in cls._strategies:
            raise ValueError(f"Nieznana strategia parowania: {strategy_name}")
        return cls._strategies[strategy_name]

    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Gets list of available strategies."""
        return list(cls._strategies.keys())


def create_file_pairs(
    file_map: Dict[str, List[str]],
    base_directory: str,
    pair_strategy: str = "first_match",
) -> Tuple[List[FilePair], Set[str]]:
    """
    Tworzy pary plików na podstawie zebranych danych.

    REFAKTORYZACJA: Funkcja została uproszczona poprzez wydzielenie strategii parowania.

    Args:
        file_map: Słownik zmapowanych plików
        base_directory: Katalog bazowy dla względnych ścieżek w FilePair
        pair_strategy: Strategia parowania plików.

    Returns:
        Krotka zawierająca listę utworzonych par oraz zbiór przetworzonych plików
    """
    start_time = time.time()
    found_pairs: List[FilePair] = []
    processed_files: Set[str] = set()

    # Pobierz strategię parowania
    try:
        strategy = OptimizedPairingStrategyFactory.get_strategy(pair_strategy)
    except ValueError as e:
        logger.error(str(e))
        return found_pairs, processed_files

    total_files = sum(len(files) for files in file_map.values())
    logger.debug(
        f"Starting file pairing with {len(file_map)} directories, "
        f"{total_files} total files using '{pair_strategy}' strategy"
    )

    for base_path, files_list in file_map.items():
        # Kategoryzuj pliki na archiwa i podglądy - używaj optimized version
        archive_files, preview_files = _categorize_files_optimized(files_list)

        if not archive_files or not preview_files:
            continue

        # Użyj strategii do utworzenia par
        pairs, processed = strategy.create_pairs(
            archive_files, preview_files, base_directory
        )

        found_pairs.extend(pairs)
        processed_files.update(processed)

    elapsed = (time.time() - start_time) * 1000
    logger.debug(
        f"File pairing completed: {len(found_pairs)} pairs from "
        f"{len(processed_files)} files in {elapsed:.2f}ms"
    )

    return found_pairs, processed_files


def identify_unpaired_files(
    file_map: Dict[str, List[str]],
    processed_files: Set[str],
) -> Tuple[List[str], List[str]]:
    """
    Memory-efficient identification of unpaired files.
    Uses streaming approach instead of large set operations.
    """
    if not file_map:
        return [], []

    unpaired_archives: List[str] = []
    unpaired_previews: List[str] = []

    # Stream processing instead of creating large intermediate sets
    for files_list in file_map.values():
        for file_path in files_list:
            if file_path in processed_files:
                continue

            # Process file without creating intermediate objects
            ext_lower = os.path.splitext(file_path)[1].lower()

            if ext_lower in ARCHIVE_EXTENSIONS:
                unpaired_archives.append(file_path)
            elif ext_lower in PREVIEW_EXTENSIONS:
                unpaired_previews.append(file_path)

    # Sort efficiently with key function
    unpaired_archives.sort(key=lambda x: os.path.basename(x).lower())
    unpaired_previews.sort(key=lambda x: os.path.basename(x).lower())

    return unpaired_archives, unpaired_previews

    def _analyze_comparison(self, baseline: Dict, revision1: Dict) -> Dict:
        """Analizuje porównanie wyników"""
        print("\n" + "=" * 60)
        print("📊 ANALIZA PORÓWNAWCZA")
        print("=" * 60)
        
        # Oblicz różnice
        pairing_time_diff = revision1['pairing_time_ms'] - baseline['pairing_time_ms']
        pairing_time_improvement = (pairing_time_diff / baseline['pairing_time_ms']) * 100 if baseline['pairing_time_ms'] > 0 else 0
        
        total_time_diff = revision1['total_time_ms'] - baseline['total_time_ms']
        total_time_improvement = (total_time_diff / baseline['total_time_ms']) * 100 if baseline['total_time_ms'] > 0 else 0
        
        pairs_per_sec_diff = revision1['pairs_per_second'] - baseline['pairs_per_second']
        pairs_per_sec_improvement = (pairs_per_sec_diff / baseline['pairs_per_second']) * 100 if baseline['pairs_per_second'] > 0 else 0
        
        # Wyświetl wyniki
        print(f"📊 BAZOWY KOD:")
        print(f"   ⏱️  Czas parowania: {baseline['pairing_time_ms']:.2f}ms")
        print(f"   ⏱️  Łączny czas: {baseline['total_time_ms']:.2f}ms")
        print(f"   🚀 Wydajność: {baseline['pairs_per_second']:.2f} par/s")
        print()
        
        print(f"📊 PIERWSZA REWIZJA (FileInfoCache):")
        print(f"   ⏱️  Czas parowania: {revision1['pairing_time_ms']:.2f}ms")
        print(f"   ⏱️  Łączny czas: {revision1['total_time_ms']:.2f}ms")
        print(f"   🚀 Wydajność: {revision1['pairs_per_second']:.2f} par/s")
        print(f"   📊 Cache hit ratio: {revision1['cache_stats']['hit_ratio_percent']}%")
        print(f"   📊 Cache size: {revision1['cache_stats']['cache_size']}")
        print()
        
        print(f"📈 RÓŻNICE:")
        print(f"   ⏱️  Czas parowania: {pairing_time_diff:+.2f}ms ({pairing_time_improvement:+.1f}%)")
        print(f"   ⏱️  Łączny czas: {total_time_diff:+.2f}ms ({total_time_improvement:+.1f}%)")
        print(f"   🚀 Wydajność: {pairs_per_sec_diff:+.2f} par/s ({pairs_per_sec_improvement:+.1f}%)")
        print()
        
        # Określ czy to poprawa czy regresja
        if pairing_time_improvement < 0:
            print("✅ PIERWSZA REWIZJA: POPRAWA WYDAJNOŚCI!")
        else:
            print("❌ PIERWSZA REWIZJA: REGRESJA WYDAJNOŚCI!")
        
        return {
            'baseline': baseline,
            'revision1': revision1,
            'pairing_time_improvement': pairing_time_improvement,
            'total_time_improvement': total_time_improvement,
            'pairs_per_sec_improvement': pairs_per_sec_improvement,
            'is_improvement': pairing_time_improvement < 0
        }


def main():
    """Główna funkcja testu porównawczego"""
    print("🚀 COMPARE REVISIONS TEST")
    print("=" * 60)
    
    # Sprawdź czy galeria testowa istnieje
    test_gallery = Path("_test_gallery")
    if not test_gallery.exists():
        print("❌ Galeria testowa '_test_gallery' nie istnieje!")
        return
    
    # Uruchom test porównawczy
    tester = RevisionComparisonTest()
    results = tester.run_comparison_test()
    
    # Podsumowanie
    print("\n" + "=" * 60)
    print("📊 PODSUMOWANIE PORÓWNANIA")
    print("=" * 60)
    
    if results['is_improvement']:
        print("✅ PIERWSZA REWIZJA JEST LEPSZA!")
        print(f"📈 Poprawa wydajności: {abs(results['pairing_time_improvement']):.1f}%")
    else:
        print("❌ PIERWSZA REWIZJA JEST GORSZA!")
        print(f"📉 Regresja wydajności: {results['pairing_time_improvement']:.1f}%")
    
    print(f"📊 Cache hit ratio: {results['revision1']['cache_stats']['hit_ratio_percent']}%")
    print(f"📊 Cache size: {results['revision1']['cache_stats']['cache_size']}")
    
    print("\n✅ Test porównawczy zakończony!")


if __name__ == "__main__":
    main() 