#!/usr/bin/env python3
"""
STRATEGIE OPTYMALIZACJI DLA PAROWANIA PLIKÓW
Specjalizowane strategie optymalizacji dla modułu file_pairing.py
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

from tests.optimization_strategies import OptimizationStrategyConfig


class FilePairingOptimizationStrategy(Enum):
    """Specjalizowane strategie dla parowania plików"""

    TRIE_OPTIMIZATION = "trie_optimization"
    CACHE_OPTIMIZATION = "cache_optimization"
    ALGORITHM_OPTIMIZATION = "algorithm_optimization"
    MEMORY_OPTIMIZATION = "memory_optimization"
    THREAD_SAFETY_OPTIMIZATION = "thread_safety_optimization"


@dataclass
class FilePairingOptimizationConfig(OptimizationStrategyConfig):
    """Konfiguracja optymalizacji parowania plików"""

    pairing_strategy: str = "best_match"
    file_count_range: str = "medium"  # small, medium, large
    expected_pair_ratio: float = 0.8  # Oczekiwany stosunek sparowanych plików


class FilePairingOptimizationLibrary:
    """Biblioteka strategii optymalizacji dla parowania plików"""

    def __init__(self):
        self.strategies = self._initialize_file_pairing_strategies()

    def _initialize_file_pairing_strategies(
        self,
    ) -> Dict[str, FilePairingOptimizationConfig]:
        """Inicjalizuje strategie optymalizacji parowania plików"""
        return {
            # OPTYMALIZACJA TRIE STRUCTURE
            "trie_memory_optimization": FilePairingOptimizationConfig(
                strategy_type=FilePairingOptimizationStrategy.TRIE_OPTIMIZATION,
                target_file="src/logic/file_pairing.py",
                target_metric="memory_usage_mb",
                description="Optymalizacja pamięci struktury Trie",
                changes={
                    "optimizations": [
                        {
                            "type": "trie_memory_optimization",
                            "max_size": 5000,
                            "cleanup_threshold": 0.8,
                            "memory_limit_mb": 50,
                        }
                    ],
                    "description": [
                        "Zmniejszenie maksymalnego rozmiaru Trie z 10000 na 5000",
                        "Dodanie automatycznego cleanup przy 80% wykorzystania",
                        "Limit pamięci 50MB dla struktury Trie",
                    ],
                },
                expected_improvement=25.0,
                risk_level="low",
                pairing_strategy="best_match",
                file_count_range="large",
                expected_pair_ratio=0.8,
            ),
            "trie_search_optimization": FilePairingOptimizationConfig(
                strategy_type=FilePairingOptimizationStrategy.TRIE_OPTIMIZATION,
                target_file="src/logic/file_pairing.py",
                target_metric="scan_time_ms",
                description="Optymalizacja wyszukiwania w Trie",
                changes={
                    "optimizations": [
                        {
                            "type": "trie_search_optimization",
                            "use_binary_search": True,
                            "cache_results": True,
                            "max_cache_size": 1000,
                        }
                    ],
                    "description": [
                        "Implementacja binary search dla wyszukiwania prefixów",
                        "Cache wyników wyszukiwania (max 1000 wyników)",
                        "Optymalizacja algorytmu find_prefix_matches",
                    ],
                },
                expected_improvement=35.0,
                risk_level="medium",
                pairing_strategy="best_match",
                file_count_range="large",
                expected_pair_ratio=0.8,
            ),
            # OPTYMALIZACJA CACHE
            "file_info_cache": FilePairingOptimizationConfig(
                strategy_type=FilePairingOptimizationStrategy.CACHE_OPTIMIZATION,
                target_file="src/logic/file_pairing.py",
                target_metric="scan_time_ms",
                description="Cache dla FileInfo obiektów",
                changes={
                    "optimizations": [
                        {
                            "type": "file_info_cache",
                            "cache_size": 10000,
                            "ttl_seconds": 300,
                            "cache_key": "file_info",
                        }
                    ],
                    "description": [
                        "Cache dla FileInfo obiektów (max 10000 wpisów)",
                        "TTL 5 minut dla cache",
                        "Unikanie ponownego parsowania rozszerzeń plików",
                    ],
                },
                expected_improvement=20.0,
                risk_level="low",
                pairing_strategy="first_match",
                file_count_range="medium",
                expected_pair_ratio=0.6,
            ),
            # OPTYMALIZACJA ALGORYTMU
            "parallel_pairing": FilePairingOptimizationConfig(
                strategy_type=FilePairingOptimizationStrategy.ALGORITHM_OPTIMIZATION,
                target_file="src/logic/file_pairing.py",
                target_metric="scan_time_ms",
                description="Równoległe parowanie plików",
                changes={
                    "optimizations": [
                        {
                            "type": "parallel_pairing",
                            "max_workers": 4,
                            "chunk_size": 100,
                            "use_threadpool": True,
                        }
                    ],
                    "description": [
                        "Równoległe przetwarzanie parowania (max 4 wątki)",
                        "Chunk size 100 plików na wątek",
                        "ThreadPoolExecutor dla równoległości",
                    ],
                },
                expected_improvement=40.0,
                risk_level="medium",
                pairing_strategy="best_match",
                file_count_range="large",
                expected_pair_ratio=0.8,
            ),
            "early_termination": FilePairingOptimizationConfig(
                strategy_type=FilePairingOptimizationStrategy.ALGORITHM_OPTIMIZATION,
                target_file="src/logic/file_pairing.py",
                target_metric="scan_time_ms",
                description="Early termination dla parowania",
                changes={
                    "optimizations": [
                        {
                            "type": "early_termination",
                            "max_pairs_per_directory": 50,
                            "stop_on_perfect_match": True,
                            "skip_unlikely_matches": True,
                        }
                    ],
                    "description": [
                        "Maksymalnie 50 par na katalog",
                        "Zatrzymanie przy idealnym dopasowaniu",
                        "Pomijanie mało prawdopodobnych dopasowań",
                    ],
                },
                expected_improvement=30.0,
                risk_level="low",
                pairing_strategy="best_match",
                file_count_range="medium",
                expected_pair_ratio=0.7,
            ),
            # OPTYMALIZACJA PAMIĘCI
            "streaming_processing": FilePairingOptimizationConfig(
                strategy_type=FilePairingOptimizationStrategy.MEMORY_OPTIMIZATION,
                target_file="src/logic/file_pairing.py",
                target_metric="memory_usage_mb",
                description="Streaming processing dla dużych zbiorów",
                changes={
                    "optimizations": [
                        {
                            "type": "streaming_processing",
                            "batch_size": 500,
                            "process_in_chunks": True,
                            "cleanup_after_batch": True,
                        }
                    ],
                    "description": [
                        "Przetwarzanie w batchach po 500 plików",
                        "Cleanup pamięci po każdym batchu",
                        "Streaming zamiast ładowania wszystkiego do pamięci",
                    ],
                },
                expected_improvement=45.0,
                risk_level="low",
                pairing_strategy="first_match",
                file_count_range="large",
                expected_pair_ratio=0.6,
            ),
            "weak_references_trie": FilePairingOptimizationConfig(
                strategy_type=FilePairingOptimizationStrategy.MEMORY_OPTIMIZATION,
                target_file="src/logic/file_pairing.py",
                target_metric="memory_usage_mb",
                description="Weak references w Trie",
                changes={
                    "optimizations": [
                        {
                            "type": "weak_references_trie",
                            "use_weakref": True,
                            "auto_cleanup": True,
                            "gc_trigger": True,
                        }
                    ],
                    "description": [
                        "Zastąpienie strong references weak references w Trie",
                        "Automatyczne cleanup nieużywanych obiektów",
                        "Trigger garbage collection po operacjach",
                    ],
                },
                expected_improvement=20.0,
                risk_level="low",
                pairing_strategy="best_match",
                file_count_range="large",
                expected_pair_ratio=0.8,
            ),
            # OPTYMALIZACJA THREAD SAFETY
            "lock_free_trie": FilePairingOptimizationConfig(
                strategy_type=FilePairingOptimizationStrategy.THREAD_SAFETY_OPTIMIZATION,
                target_file="src/logic/file_pairing.py",
                target_metric="scan_time_ms",
                description="Lock-free operacje w Trie",
                changes={
                    "optimizations": [
                        {
                            "type": "lock_free_trie",
                            "use_atomic_operations": True,
                            "read_write_separation": True,
                            "optimistic_locking": True,
                        }
                    ],
                    "description": [
                        "Atomic operations dla operacji read-only",
                        "Separacja operacji read/write",
                        "Optimistic locking dla lepszej wydajności",
                    ],
                },
                expected_improvement=15.0,
                risk_level="medium",
                pairing_strategy="best_match",
                file_count_range="large",
                expected_pair_ratio=0.8,
            ),
        }

    def get_strategies_for_file_count(
        self, file_count: int
    ) -> List[FilePairingOptimizationConfig]:
        """Pobiera strategie odpowiednie dla liczby plików"""
        if file_count < 100:
            range_type = "small"
        elif file_count < 1000:
            range_type = "medium"
        else:
            range_type = "large"

        return [
            config
            for config in self.strategies.values()
            if config.file_count_range == range_type
        ]

    def get_strategies_for_pairing_strategy(
        self, strategy: str
    ) -> List[FilePairingOptimizationConfig]:
        """Pobiera strategie dla konkretnej strategii parowania"""
        return [
            config
            for config in self.strategies.values()
            if config.pairing_strategy == strategy
        ]

    def get_high_impact_strategies(
        self, min_improvement: float = 25.0
    ) -> List[FilePairingOptimizationConfig]:
        """Pobiera strategie z wysokim wpływem"""
        return [
            config
            for config in self.strategies.values()
            if config.expected_improvement >= min_improvement
        ]

    def generate_optimization_plan(
        self, file_count: int, pairing_strategy: str = "best_match"
    ) -> List[FilePairingOptimizationConfig]:
        """Generuje plan optymalizacji dla parowania plików"""
        plan = []

        # Pobierz strategie odpowiednie dla liczby plików
        file_count_strategies = self.get_strategies_for_file_count(file_count)

        # Pobierz strategie dla strategii parowania
        strategy_specific = self.get_strategies_for_pairing_strategy(pairing_strategy)

        # Połącz i usuń duplikaty
        all_strategies = list(set(file_count_strategies + strategy_specific))

        # Sortuj po oczekiwanej poprawie (malejąco)
        all_strategies.sort(key=lambda x: x.expected_improvement, reverse=True)

        # Wybierz top strategie
        for strategy in all_strategies:
            if len(plan) >= 5:  # Maksymalnie 5 strategii
                break

            # Sprawdź kompatybilność
            if self._is_strategy_compatible(strategy, plan):
                plan.append(strategy)

        return plan

    def _is_strategy_compatible(
        self,
        strategy: FilePairingOptimizationConfig,
        existing_plan: List[FilePairingOptimizationConfig],
    ) -> bool:
        """Sprawdza kompatybilność strategii z istniejącym planem"""
        # Sprawdź konflikty
        conflicts = {
            "trie_memory_optimization": ["trie_search_optimization"],
            "streaming_processing": ["parallel_pairing"],
            "lock_free_trie": ["weak_references_trie"],
        }

        strategy_name = strategy.description.split(":")[0].lower().replace(" ", "_")

        for existing in existing_plan:
            existing_name = existing.description.split(":")[0].lower().replace(" ", "_")

            # Sprawdź czy istniejąca strategia ma konflikt z nową
            if existing_name in conflicts and strategy_name in conflicts[existing_name]:
                return False

            # Sprawdź czy nowa strategia ma konflikt z istniejącą
            if strategy_name in conflicts and existing_name in conflicts[strategy_name]:
                return False

        return True


class FilePairingTestEnvironment:
    """Środowisko testowe dla parowania plików"""

    def __init__(self, test_folder: str = "_test_gallery"):
        self.test_folder = test_folder
        self.file_counts = {"small": 50, "medium": 300, "large": 1000}

    def create_test_scenario(self, scenario_type: str) -> Dict[str, Any]:
        """Tworzy scenariusz testowy"""
        scenarios = {
            "small_best_match": {
                "file_count": self.file_counts["small"],
                "pairing_strategy": "best_match",
                "expected_pairs": 20,
                "description": "Mały zbiór z inteligentnym parowaniem",
            },
            "medium_first_match": {
                "file_count": self.file_counts["medium"],
                "pairing_strategy": "first_match",
                "expected_pairs": 100,
                "description": "Średni zbiór z prostym parowaniem",
            },
            "large_best_match": {
                "file_count": self.file_counts["large"],
                "pairing_strategy": "best_match",
                "expected_pairs": 400,
                "description": "Duży zbiór z inteligentnym parowaniem",
            },
        }

        return scenarios.get(scenario_type, scenarios["medium_first_match"])

    def measure_pairing_performance(
        self, file_count: int, pairing_strategy: str
    ) -> Dict[str, float]:
        """Mierzy wydajność parowania"""
        import time

        from src.logic.file_pairing import create_file_pairs
        from src.logic.scanner_core import collect_files_streaming

        # Przygotuj dane testowe
        test_files = self._generate_test_files(file_count)

        # Wyznacz katalog bazowy (wspólny dla wszystkich plików)
        base_directory = os.path.abspath(self.test_folder)

        # Symuluj file_map: {base_directory: [list of files]}
        file_map = {base_directory: test_files}

        # Zmierz czas parowania
        start_time = time.time()

        # Uruchom parowanie
        pairs, processed = create_file_pairs(file_map, base_directory, pairing_strategy)

        execution_time = (time.time() - start_time) * 1000

        # Oblicz metryki
        metrics = {
            "pairing_time_ms": execution_time,
            "pairs_created": len(pairs),
            "files_processed": len(processed),
            "pair_ratio": len(pairs) / (file_count // 2) if file_count > 0 else 0,
            "pairs_per_second": (
                len(pairs) / (execution_time / 1000) if execution_time > 0 else 0
            ),
        }

        return metrics

    def _generate_test_files(self, count: int) -> List[str]:
        """Generuje listę testowych plików z absolutnymi ścieżkami"""
        files = []

        # Generuj pary plików (archiwum + podgląd)
        for i in range(count // 2):
            base_name = f"test_file_{i:04d}"

            # Archiwum
            archive_ext = [".zip", ".rar", ".7z", ".blend"][i % 4]
            archive_path = os.path.abspath(
                os.path.join(self.test_folder, f"{base_name}{archive_ext}")
            )
            files.append(archive_path)

            # Podgląd
            preview_ext = [".jpg", ".png", ".webp"][i % 3]
            preview_path = os.path.abspath(
                os.path.join(self.test_folder, f"{base_name}{preview_ext}")
            )
            files.append(preview_path)

        return files


def main():
    """Przykład użycia biblioteki optymalizacji parowania"""
    library = FilePairingOptimizationLibrary()
    test_env = FilePairingTestEnvironment()

    # Przykład: optymalizacja dla dużego zbioru plików
    print("🔧 Strategie optymalizacji dla dużego zbioru plików:")
    large_strategies = library.get_strategies_for_file_count(1500)
    for strategy in large_strategies:
        print(
            f"  - {strategy.description}: {strategy.expected_improvement:.1f}% poprawa"
        )

    # Przykład: plan optymalizacji
    print("\n📋 Plan optymalizacji dla 1000 plików z best_match:")
    plan = library.generate_optimization_plan(1000, "best_match")
    for i, strategy in enumerate(plan, 1):
        print(f"  {i}. {strategy.description}")
        print(f"     Oczekiwana poprawa: {strategy.expected_improvement:.1f}%")
        print(f"     Ryzyko: {strategy.risk_level}")

    # Przykład: test wydajności
    print("\n⚡ Test wydajności parowania:")
    metrics = test_env.measure_pairing_performance(300, "best_match")
    for metric, value in metrics.items():
        print(f"  {metric}: {value:.2f}")


if __name__ == "__main__":
    main()
