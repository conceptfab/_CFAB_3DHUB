#!/usr/bin/env python3
"""
AVERAGE PERFORMANCE TEST
Przeprowadza 3 testy i wylicza średnią wydajność
"""

import sys
import time
from pathlib import Path
from typing import Dict, List

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.logic.file_pairing import create_file_pairs
from src.logic.scanner_core import collect_files_streaming


def run_single_test(test_number: int) -> Dict:
    """Przeprowadza pojedynczy test"""
    print(f"🔬 TEST {test_number}/3")
    print("-" * 40)

    test_gallery = Path("_test_gallery").resolve()
    if not test_gallery.exists():
        print("❌ Galeria testowa '_test_gallery' nie istnieje!")
        return {}

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
        "test_number": test_number,
        "total_files": sum(len(files) for files in file_map.values()),
        "pairs_created": len(pairs),
        "scan_time_ms": scan_time,
        "pairing_time_ms": pairing_time,
        "total_time_ms": total_time,
        "pairs_per_second": (
            len(pairs) / (pairing_time / 1000) if pairing_time > 0 else 0
        ),
    }

    print(f"   📁 Pliki: {results['total_files']}")
    print(f"   🔗 Pary: {results['pairs_created']}")
    print(f"   ⏱️  Skanowanie: {results['scan_time_ms']:.2f}ms")
    print(f"   ⏱️  Parowanie: {results['pairing_time_ms']:.2f}ms")
    print(f"   ⏱️  Łącznie: {results['total_time_ms']:.2f}ms")
    print(f"   🚀 Wydajność: {results['pairs_per_second']:.2f} par/s")
    print()

    return results


def calculate_averages(test_results: List[Dict]) -> Dict:
    """Oblicza średnie z wyników testów"""
    if not test_results:
        return {}

    # Sumy
    total_files = sum(r["total_files"] for r in test_results)
    total_pairs = sum(r["pairs_created"] for r in test_results)
    total_scan_time = sum(r["scan_time_ms"] for r in test_results)
    total_pairing_time = sum(r["pairing_time_ms"] for r in test_results)
    total_time = sum(r["total_time_ms"] for r in test_results)
    total_pairs_per_sec = sum(r["pairs_per_second"] for r in test_results)

    # Średnie
    num_tests = len(test_results)
    averages = {
        "num_tests": num_tests,
        "total_files": total_files // num_tests,  # Integer division
        "pairs_created": total_pairs // num_tests,
        "scan_time_ms": total_scan_time / num_tests,
        "pairing_time_ms": total_pairing_time / num_tests,
        "total_time_ms": total_time / num_tests,
        "pairs_per_second": total_pairs_per_sec / num_tests,
    }

    return averages


def compare_with_baseline(average_results: Dict):
    """Porównuje średnie wyniki z bazowym kodem"""
    print("=" * 60)
    print("📊 PORÓWNANIE Z BAZOWYM KODEM")
    print("=" * 60)

    # Wyniki bazowe z poprzedniego testu
    baseline_results = {
        "pairing_time_ms": 16.98,
        "total_time_ms": 84.34,
        "pairs_per_second": 18848.95,
    }

    # Oblicz różnice
    pairing_time_diff = (
        average_results["pairing_time_ms"] - baseline_results["pairing_time_ms"]
    )
    pairing_time_improvement = (
        pairing_time_diff / baseline_results["pairing_time_ms"]
    ) * 100

    total_time_diff = (
        average_results["total_time_ms"] - baseline_results["total_time_ms"]
    )
    total_time_improvement = (total_time_diff / baseline_results["total_time_ms"]) * 100

    pairs_per_sec_diff = (
        average_results["pairs_per_second"] - baseline_results["pairs_per_second"]
    )
    pairs_per_sec_improvement = (
        pairs_per_sec_diff / baseline_results["pairs_per_second"]
    ) * 100

    print("📊 BAZOWY KOD:")
    print(f"   ⏱️  Czas parowania: {baseline_results['pairing_time_ms']:.2f}ms")
    print(f"   ⏱️  Łączny czas: {baseline_results['total_time_ms']:.2f}ms")
    print(f"   🚀 Wydajność: {baseline_results['pairs_per_second']:.2f} par/s")
    print()

    print("📊 DRUGA REWIZJA (ŚREDNIA z 3 testów):")
    print(f"   ⏱️  Czas parowania: {average_results['pairing_time_ms']:.2f}ms")
    print(f"   ⏱️  Łączny czas: {average_results['total_time_ms']:.2f}ms")
    print(f"   🚀 Wydajność: {average_results['pairs_per_second']:.2f} par/s")
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
    print("🚀 AVERAGE PERFORMANCE TEST - REVIZJA 2")
    print("=" * 60)
    print("Przeprowadzam 3 testy dla wyliczenia średniej...")
    print()

    # Przeprowadź 3 testy
    test_results = []
    for i in range(1, 4):
        result = run_single_test(i)
        if result:
            test_results.append(result)

        # Krótka przerwa między testami
        if i < 3:
            time.sleep(0.5)

    if len(test_results) == 3:
        # Oblicz średnie
        print("=" * 60)
        print("📊 OBLICZANIE ŚREDNIEJ")
        print("=" * 60)

        averages = calculate_averages(test_results)

        print("📊 ŚREDNIE WYNIKI:")
        print(f"   📁 Pliki: {averages['total_files']}")
        print(f"   🔗 Pary: {averages['pairs_created']}")
        print(f"   ⏱️  Skanowanie: {averages['scan_time_ms']:.2f}ms")
        print(f"   ⏱️  Parowanie: {averages['pairing_time_ms']:.2f}ms")
        print(f"   ⏱️  Łącznie: {averages['total_time_ms']:.2f}ms")
        print(f"   🚀 Wydajność: {averages['pairs_per_second']:.2f} par/s")
        print()

        # Porównaj z bazowym kodem
        compare_with_baseline(averages)

        print("=" * 60)
        print("📊 PODSUMOWANIE")
        print("=" * 60)

        if averages["pairing_time_ms"] < 16.98:  # Bazowy czas
            print("✅ DRUGA REWIZJA JEST LEPSZA!")
        else:
            print("❌ DRUGA REWIZJA JEST GORSZA!")

        print(f"📊 Liczba testów: {averages['num_tests']}")
        print(f"📊 Batch processing: włączony")
        print(f"📊 Optimized Trie: włączony")

        # Szczegółowe wyniki testów
        print("\n📊 SZCZEGÓŁOWE WYNIKI TESTÓW:")
        for result in test_results:
            print(
                f"   Test {result['test_number']}: "
                f"{result['pairing_time_ms']:.2f}ms, "
                f"{result['pairs_per_second']:.2f} par/s"
            )

    else:
        print("❌ Nie udało się przeprowadzić wszystkich 3 testów!")

    print("\n✅ Test średniej wydajności zakończony!")


if __name__ == "__main__":
    main()
