#!/usr/bin/env python3
"""
BASIC FILE PAIRING TEST
Test bazowego kodu parowania plików na rzeczywistej galerii testowej
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.logic.file_pairing import create_file_pairs, identify_unpaired_files
from src.logic.scanner_core import collect_files_streaming


class BasicFilePairingTest:
    """Test bazowego kodu parowania plików"""

    def __init__(self, test_gallery_path: str = "_test_gallery"):
        self.test_gallery_path = Path(test_gallery_path).resolve()
        self.results = {}

        print(f"🔍 Test bazowego parowania plików")
        print(f"📁 Galeria testowa: {self.test_gallery_path}")
        print(f"📊 Pliki w galerii: {len(list(self.test_gallery_path.glob('*')))}")

    def run_basic_test(self) -> Dict:
        """Uruchamia podstawowy test parowania"""
        print("\n🚀 ROZPOCZĘCIE TESTU BAZOWEGO")
        print("=" * 50)

        start_time = time.time()

        # FAZA 1: Skanowanie plików
        print("\n📊 FAZA 1: Skanowanie plików...")
        scan_start = time.time()

        file_map = collect_files_streaming(str(self.test_gallery_path), max_depth=0)

        scan_time = (time.time() - scan_start) * 1000
        total_files = sum(len(files) for files in file_map.values())

        print(f"  ✅ Skanowanie zakończone: {total_files} plików w {scan_time:.2f}ms")

        # FAZA 2: Parowanie plików
        print("\n🔗 FAZA 2: Parowanie plików...")
        pairing_start = time.time()

        pairs, processed_files = create_file_pairs(
            file_map, str(self.test_gallery_path), "best_match"
        )

        pairing_time = (time.time() - pairing_start) * 1000

        print(f"  ✅ Parowanie zakończone: {len(pairs)} par w {pairing_time:.2f}ms")

        # FAZA 3: Identyfikacja niesparowanych plików
        print("\n🔍 FAZA 3: Identyfikacja niesparowanych plików...")
        unpaired_start = time.time()

        unpaired_archives, unpaired_previews = identify_unpaired_files(
            file_map, processed_files
        )

        unpaired_time = (time.time() - unpaired_start) * 1000

        print(
            f"  ✅ Identyfikacja zakończona: {len(unpaired_archives)} archiwów, {len(unpaired_previews)} podglądów w {unpaired_time:.2f}ms"
        )

        # FAZA 4: Analiza wyników
        print("\n📈 FAZA 4: Analiza wyników...")

        total_time = (time.time() - start_time) * 1000

        # Oblicz metryki
        metrics = {
            "total_files": total_files,
            "pairs_created": len(pairs),
            "processed_files": len(processed_files),
            "unpaired_archives": len(unpaired_archives),
            "unpaired_previews": len(unpaired_previews),
            "scan_time_ms": scan_time,
            "pairing_time_ms": pairing_time,
            "unpaired_time_ms": unpaired_time,
            "total_time_ms": total_time,
            "pairs_per_second": (
                len(pairs) / (pairing_time / 1000) if pairing_time > 0 else 0
            ),
            "pair_ratio": len(pairs) / (total_files // 2) if total_files > 0 else 0,
        }

        # Wyświetl szczegółowe wyniki
        self._display_detailed_results(
            metrics, pairs, unpaired_archives, unpaired_previews
        )

        return metrics

    def _display_detailed_results(
        self,
        metrics: Dict,
        pairs: List,
        unpaired_archives: List,
        unpaired_previews: List,
    ):
        """Wyświetla szczegółowe wyniki testu"""
        print("\n" + "=" * 50)
        print("📊 SZCZEGÓŁOWE WYNIKI TESTU")
        print("=" * 50)

        print(f"📁 Łączna liczba plików: {metrics['total_files']}")
        print(f"🔗 Utworzone pary: {metrics['pairs_created']}")
        print(f"📝 Przetworzone pliki: {metrics['processed_files']}")
        print(f"📦 Niesparowane archiwa: {metrics['unpaired_archives']}")
        print(f"🖼️  Niesparowane podglądy: {metrics['unpaired_previews']}")
        print()

        print(f"⏱️  Czas skanowania: {metrics['scan_time_ms']:.2f}ms")
        print(f"⏱️  Czas parowania: {metrics['pairing_time_ms']:.2f}ms")
        print(f"⏱️  Czas identyfikacji: {metrics['unpaired_time_ms']:.2f}ms")
        print(f"⏱️  Łączny czas: {metrics['total_time_ms']:.2f}ms")
        print()

        print(f"🚀 Wydajność: {metrics['pairs_per_second']:.2f} par/sekundę")
        print(f"📊 Stosunek par: {metrics['pair_ratio']:.2%}")
        print()

        # Pokaż przykłady par
        if pairs:
            print("🔗 PRZYKŁADY UTWORZONYCH PAR:")
            for i, pair in enumerate(pairs[:5], 1):  # Pokaż pierwsze 5 par
                archive_name = os.path.basename(pair.archive_path)
                preview_name = os.path.basename(pair.preview_path)
                print(f"  {i}. {archive_name} ↔ {preview_name}")

            if len(pairs) > 5:
                print(f"  ... i {len(pairs) - 5} więcej par")
            print()

        # Pokaż przykłady niesparowanych plików
        if unpaired_archives or unpaired_previews:
            print("❌ PRZYKŁADY NIESPAROWANYCH PLIKÓW:")

            if unpaired_archives:
                print("  📦 Archiwa:")
                for i, archive in enumerate(unpaired_archives[:3], 1):
                    print(f"    {i}. {os.path.basename(archive)}")
                if len(unpaired_archives) > 3:
                    print(f"    ... i {len(unpaired_archives) - 3} więcej")

            if unpaired_previews:
                print("  🖼️  Podglądy:")
                for i, preview in enumerate(unpaired_previews[:3], 1):
                    print(f"    {i}. {os.path.basename(preview)}")
                if len(unpaired_previews) > 3:
                    print(f"    ... i {len(unpaired_previews) - 3} więcej")
            print()

    def test_different_strategies(self) -> Dict[str, Dict]:
        """Testuje różne strategie parowania"""
        print("\n🔧 TEST RÓŻNYCH STRATEGII PAROWANIA")
        print("=" * 50)

        strategies = ["first_match", "best_match"]
        results = {}

        for strategy in strategies:
            print(f"\n📊 Testowanie strategii: {strategy}")

            # Skanowanie
            file_map = collect_files_streaming(str(self.test_gallery_path), max_depth=0)

            # Parowanie z daną strategią
            start_time = time.time()
            pairs, processed = create_file_pairs(
                file_map, str(self.test_gallery_path), strategy
            )
            pairing_time = (time.time() - start_time) * 1000

            # Metryki
            total_files = sum(len(files) for files in file_map.values())
            metrics = {
                "strategy": strategy,
                "total_files": total_files,
                "pairs_created": len(pairs),
                "pairing_time_ms": pairing_time,
                "pairs_per_second": (
                    len(pairs) / (pairing_time / 1000) if pairing_time > 0 else 0
                ),
                "pair_ratio": len(pairs) / (total_files // 2) if total_files > 0 else 0,
            }

            results[strategy] = metrics

            print(
                f"  ✅ {strategy}: {len(pairs)} par w {pairing_time:.2f}ms ({metrics['pairs_per_second']:.2f} par/s)"
            )

        return results


def main():
    """Główna funkcja testu"""
    print("🚀 BASIC FILE PAIRING TEST")
    print("=" * 50)

    # Sprawdź czy galeria testowa istnieje
    test_gallery = Path("_test_gallery")
    if not test_gallery.exists():
        print("❌ Galeria testowa '_test_gallery' nie istnieje!")
        print("   Utwórz galerię z plikami do testowania.")
        return

    # Uruchom test
    tester = BasicFilePairingTest()

    # Test bazowy
    basic_results = tester.run_basic_test()

    # Test różnych strategii
    strategy_results = tester.test_different_strategies()

    # Podsumowanie
    print("\n" + "=" * 50)
    print("📊 PODSUMOWANIE TESTOW")
    print("=" * 50)

    print(f"📁 Testowana galeria: {test_gallery}")
    print(f"📊 Łączna liczba plików: {basic_results['total_files']}")
    print(
        f"🔗 Najlepsza strategia: {max(strategy_results.keys(), key=lambda k: strategy_results[k]['pairs_created'])}"
    )
    print(f"⏱️  Łączny czas testów: {basic_results['total_time_ms']:.2f}ms")

    print("\n✅ Test bazowy zakończony pomyślnie!")


if __name__ == "__main__":
    main()
