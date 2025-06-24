#!/usr/bin/env python3
"""
SIMPLE REVISION TEST
Prosty test drugiej rewizji optymalizacji
"""

import sys
import time
from pathlib import Path
from typing import Dict

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.logic.file_pairing import create_file_pairs
from src.logic.scanner_core import collect_files_streaming


def test_revision2_performance() -> Dict:
    """Testuje wydajność drugiej rewizji (batch processing + optimized Trie)"""
    print("🚀 TEST DRUGIEJ REWIZJI (Batch Processing + Optimized Trie)")
    print("=" * 60)

    test_gallery = Path("_test_gallery").resolve()
    if not test_gallery.exists():
        print("❌ Galeria testowa '_test_gallery' nie istnieje!")
        return {}

    print(f"📁 Galeria testowa: {test_gallery}")
    print(f"📊 Pliki w galerii: {len(list(test_gallery.glob('*')))}")

    # Test z drugą rewizją
    start_time = time.time()

    # Skanowanie
    scan_start = time.time()
    file_map = collect_files_streaming(str(test_gallery), max_depth=0)
    scan_time = (time.time() - scan_start) * 1000

    # Parowanie
    pairing_start = time.time()
    pairs, processed = create_file_pairs(file_map, str(test_gallery), "best_match")
    pairing_time = (time.time() - pairing_start) * 1000

    total_time = (time.time() - start_time) * 1000

    results = {
        "revision": "revision2_batch_processing",
        "total_files": sum(len(files) for files in file_map.values()),
        "pairs_created": len(pairs),
        "scan_time_ms": scan_time,
        "pairing_time_ms": pairing_time,
        "total_time_ms": total_time,
        "pairs_per_second": (
            len(pairs) / (pairing_time / 1000) if pairing_time > 0 else 0
        ),
    }

    # Wyświetl wyniki
    print(f"\n📊 WYNIKI DRUGIEJ REWIZJI:")
    print(f"   📁 Łączna liczba plików: {results['total_files']}")
    print(f"   🔗 Utworzone pary: {results['pairs_created']}")
    print(f"   ⏱️  Czas skanowania: {results['scan_time_ms']:.2f}ms")
    print(f"   ⏱️  Czas parowania: {results['pairing_time_ms']:.2f}ms")
    print(f"   ⏱️  Łączny czas: {results['total_time_ms']:.2f}ms")
    print(f"   🚀 Wydajność: {results['pairs_per_second']:.2f} par/s")

    return results


def compare_with_baseline(revision_results: Dict):
    """Porównuje z wynikami bazowymi z poprzedniego testu"""
    print("\n" + "=" * 60)
    print("📊 PORÓWNANIE Z BAZOWYM KODEM")
    print("=" * 60)

    # Wyniki bazowe z poprzedniego testu
    baseline_results = {
        "pairing_time_ms": 16.98,  # Z poprzedniego testu
        "total_time_ms": 84.34,  # Z poprzedniego testu
        "pairs_per_second": 18848.95,  # Z poprzedniego testu
    }

    # Oblicz różnice
    pairing_time_diff = (
        revision_results["pairing_time_ms"] - baseline_results["pairing_time_ms"]
    )
    pairing_time_improvement = (
        pairing_time_diff / baseline_results["pairing_time_ms"]
    ) * 100

    total_time_diff = (
        revision_results["total_time_ms"] - baseline_results["total_time_ms"]
    )
    total_time_improvement = (total_time_diff / baseline_results["total_time_ms"]) * 100

    pairs_per_sec_diff = (
        revision_results["pairs_per_second"] - baseline_results["pairs_per_second"]
    )
    pairs_per_sec_improvement = (
        pairs_per_sec_diff / baseline_results["pairs_per_second"]
    ) * 100

    print("📊 BAZOWY KOD:")
    print(f"   ⏱️  Czas parowania: {baseline_results['pairing_time_ms']:.2f}ms")
    print(f"   ⏱️  Łączny czas: {baseline_results['total_time_ms']:.2f}ms")
    print(f"   🚀 Wydajność: {baseline_results['pairs_per_second']:.2f} par/s")
    print()

    print("📊 DRUGA REWIZJA (Batch + Optimized Trie):")
    print(f"   ⏱️  Czas parowania: {revision_results['pairing_time_ms']:.2f}ms")
    print(f"   ⏱️  Łączny czas: {revision_results['total_time_ms']:.2f}ms")
    print(f"   🚀 Wydajność: {revision_results['pairs_per_second']:.2f} par/s")
    print()

    print("📈 RÓŻNICE:")
    print(
        f"   ⏱️  Czas parowania: {pairing_time_diff:+.2f}ms "
        f"({pairing_time_improvement:+.1f}%)"
    )
    print(
        f"   ⏱️  Łączny czas: {total_time_diff:+.2f}ms "
        f"({total_time_improvement:+.1f}%)"
    )
    print(
        f"   🚀 Wydajność: {pairs_per_sec_diff:+.2f} par/s "
        f"({pairs_per_sec_improvement:+.1f}%)"
    )
    print()

    # Określ czy to poprawa czy regresja
    if pairing_time_improvement < 0:
        print("✅ DRUGA REWIZJA: POPRAWA WYDAJNOŚCI!")
        print(f"📈 Poprawa: {abs(pairing_time_improvement):.1f}%")
    else:
        print("❌ DRUGA REWIZJA: REGRESJA WYDAJNOŚCI!")
        print(f"📉 Regresja: {pairing_time_improvement:.1f}%")


def main():
    """Główna funkcja testu"""
    print("🚀 SIMPLE REVISION TEST - REVIZJA 2")
    print("=" * 60)

    # Test drugiej rewizji
    results = test_revision2_performance()

    if results:
        # Porównaj z bazowym kodem
        compare_with_baseline(results)

        print("\n" + "=" * 60)
        print("📊 PODSUMOWANIE")
        print("=" * 60)

        if results["pairing_time_ms"] < 16.98:  # Bazowy czas
            print("✅ DRUGA REWIZJA JEST LEPSZA!")
        else:
            print("❌ DRUGA REWIZJA JEST GORSZA!")

        print(f"📊 Batch processing: włączony")
        print(f"📊 Optimized Trie: włączony")

    print("\n✅ Test drugiej rewizji zakończony!")


if __name__ == "__main__":
    main()
