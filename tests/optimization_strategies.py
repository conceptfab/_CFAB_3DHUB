#!/usr/bin/env python3
"""
STRATEGIE OPTYMALIZACJI
Biblioteka gotowych strategii optymalizacji do automatycznego testowania
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class OptimizationStrategy(Enum):
    """Dostępne strategie optymalizacji"""

    CACHE_OPTIMIZATION = "cache_optimization"
    MEMORY_OPTIMIZATION = "memory_optimization"
    THREAD_SAFETY = "thread_safety"
    ALGORITHM_OPTIMIZATION = "algorithm_optimization"
    UI_RESPONSIVENESS = "ui_responsiveness"
    BATCH_PROCESSING = "batch_processing"
    LAZY_LOADING = "lazy_loading"
    CONNECTION_POOLING = "connection_pooling"


@dataclass
class OptimizationStrategyConfig:
    """Konfiguracja strategii optymalizacji"""

    strategy_type: OptimizationStrategy
    target_file: str
    target_metric: str
    description: str
    changes: Dict[str, Any]
    expected_improvement: float
    risk_level: str  # low, medium, high
    dependencies: List[str] = None


class OptimizationStrategiesLibrary:
    """Biblioteka strategii optymalizacji"""

    def __init__(self):
        self.strategies = self._initialize_strategies()

    def _initialize_strategies(self) -> Dict[str, OptimizationStrategyConfig]:
        """Inicjalizuje bibliotekę strategii"""
        return {
            # OPTYMALIZACJE WYDAJNOŚCIOWE
            "gallery_cache_geometry": OptimizationStrategyConfig(
                strategy_type=OptimizationStrategy.CACHE_OPTIMIZATION,
                target_file="src/ui/gallery_manager.py",
                target_metric="gallery_load_time_ms",
                description="Cache dla obliczeń geometrii galerii",
                changes={
                    "optimizations": [
                        {
                            "type": "cache_optimization",
                            "cache_name": "_geometry_cache",
                            "cache_key": "layout_geometry",
                            "calculation_method": "_calculate_layout_geometry",
                        }
                    ],
                    "description": [
                        "Dodano cache dla obliczeń geometrii layoutu",
                        "Implementacja LRU cache z TTL 30s",
                        "Automatyczne invalidate przy resize",
                    ],
                },
                expected_improvement=15.0,
                risk_level="low",
            ),
            "tile_creation_batch": OptimizationStrategyConfig(
                strategy_type=OptimizationStrategy.BATCH_PROCESSING,
                target_file="src/ui/gallery_manager.py",
                target_metric="tile_creation_time_ms",
                description="Batch processing dla tworzenia kafelków",
                changes={
                    "optimizations": [
                        {
                            "type": "batch_processing",
                            "batch_size": 50,
                            "batch_delay_ms": 10,
                            "method_name": "_create_tiles_batch",
                        }
                    ],
                    "description": [
                        "Implementacja batch processing dla kafelków",
                        "Batch size: 50 kafelków",
                        "Delay między batchami: 10ms",
                    ],
                },
                expected_improvement=25.0,
                risk_level="medium",
            ),
            # OPTYMALIZACJE PAMIĘCI
            "weak_references_tiles": OptimizationStrategyConfig(
                strategy_type=OptimizationStrategy.MEMORY_OPTIMIZATION,
                target_file="src/ui/gallery_manager.py",
                target_metric="memory_usage_mb",
                description="Weak references dla kafelków",
                changes={
                    "optimizations": [
                        {
                            "type": "weak_references",
                            "target_objects": ["tile_widgets", "thumbnail_cache"],
                            "cleanup_method": "_cleanup_weak_references",
                        }
                    ],
                    "description": [
                        "Zastąpiono strong references weak references",
                        "Automatyczne cleanup nieużywanych obiektów",
                        "Redukcja memory leaks",
                    ],
                },
                expected_improvement=20.0,
                risk_level="low",
            ),
            "memory_pool_thumbnails": OptimizationStrategyConfig(
                strategy_type=OptimizationStrategy.MEMORY_OPTIMIZATION,
                target_file="src/ui/widgets/file_tile_widget.py",
                target_metric="memory_usage_mb",
                description="Memory pool dla miniaturek",
                changes={
                    "optimizations": [
                        {
                            "type": "memory_pool",
                            "pool_name": "_thumbnail_pool",
                            "pool_size": 100,
                            "reuse_objects": True,
                        }
                    ],
                    "description": [
                        "Implementacja memory pool dla miniaturek",
                        "Pool size: 100 obiektów",
                        "Reuse obiektów zamiast tworzenia nowych",
                    ],
                },
                expected_improvement=30.0,
                risk_level="medium",
            ),
            # OPTYMALIZACJE THREAD SAFETY
            "thread_safe_cache": OptimizationStrategyConfig(
                strategy_type=OptimizationStrategy.THREAD_SAFETY,
                target_file="src/ui/gallery_manager.py",
                target_metric="gallery_load_time_ms",
                description="Thread-safe cache z lock-free reads",
                changes={
                    "optimizations": [
                        {
                            "type": "thread_safety",
                            "lock_type": "RLock",
                            "lock_name": "_cache_lock",
                            "atomic_operations": ["cache_get", "cache_set"],
                        }
                    ],
                    "description": [
                        "Dodano thread-safe cache",
                        "Lock-free reads dla lepszej wydajności",
                        "Atomic operations dla cache updates",
                    ],
                },
                expected_improvement=10.0,
                risk_level="low",
            ),
            # OPTYMALIZACJE ALGORYTMICZNE
            "optimized_scanning": OptimizationStrategyConfig(
                strategy_type=OptimizationStrategy.ALGORITHM_OPTIMIZATION,
                target_file="src/logic/scanner_core.py",
                target_metric="scan_time_ms",
                description="Zoptymalizowany algorytm skanowania",
                changes={
                    "optimizations": [
                        {
                            "type": "algorithm_optimization",
                            "old_algorithm": "recursive_scan",
                            "new_algorithm": "iterative_scan",
                            "optimization": "eliminate_recursion",
                        }
                    ],
                    "description": [
                        "Zastąpiono rekurencyjne skanowanie iteracyjnym",
                        "Eliminacja stack overflow dla głębokich folderów",
                        "Lepsze zarządzanie pamięcią",
                    ],
                },
                expected_improvement=40.0,
                risk_level="medium",
            ),
            # OPTYMALIZACJE UI
            "ui_responsiveness": OptimizationStrategyConfig(
                strategy_type=OptimizationStrategy.UI_RESPONSIVENESS,
                target_file="src/ui/main_window/main_window.py",
                target_metric="gallery_load_time_ms",
                description="Asynchroniczne operacje UI",
                changes={
                    "optimizations": [
                        {
                            "type": "ui_responsiveness",
                            "async_operations": ["gallery_update", "thumbnail_loading"],
                            "progress_callback": True,
                            "non_blocking": True,
                        }
                    ],
                    "description": [
                        "Przeniesiono operacje do background threads",
                        "Dodano progress callbacks",
                        "Non-blocking UI operations",
                    ],
                },
                expected_improvement=35.0,
                risk_level="medium",
            ),
            # OPTYMALIZACJE LAZY LOADING
            "lazy_thumbnail_loading": OptimizationStrategyConfig(
                strategy_type=OptimizationStrategy.LAZY_LOADING,
                target_file="src/ui/widgets/file_tile_widget.py",
                target_metric="gallery_load_time_ms",
                description="Lazy loading miniaturek",
                changes={
                    "optimizations": [
                        {
                            "type": "lazy_loading",
                            "load_trigger": "visibility_changed",
                            "placeholder": True,
                            "preload_distance": 5,
                        }
                    ],
                    "description": [
                        "Implementacja lazy loading miniaturek",
                        "Load tylko gdy kafelek jest widoczny",
                        "Placeholder podczas ładowania",
                        "Preload 5 kafelków do przodu",
                    ],
                },
                expected_improvement=50.0,
                risk_level="low",
            ),
            # OPTYMALIZACJE CONNECTION POOLING
            "connection_pooling": OptimizationStrategyConfig(
                strategy_type=OptimizationStrategy.CONNECTION_POOLING,
                target_file="src/logic/metadata_manager.py",
                target_metric="memory_usage_mb",
                description="Connection pooling dla operacji I/O",
                changes={
                    "optimizations": [
                        {
                            "type": "connection_pooling",
                            "pool_size": 10,
                            "max_connections": 20,
                            "timeout_seconds": 30,
                        }
                    ],
                    "description": [
                        "Implementacja connection pooling",
                        "Pool size: 10 connections",
                        "Max connections: 20",
                        "Timeout: 30s",
                    ],
                },
                expected_improvement=15.0,
                risk_level="medium",
            ),
        }

    def get_strategy(self, strategy_name: str) -> Optional[OptimizationStrategyConfig]:
        """Pobiera strategię po nazwie"""
        return self.strategies.get(strategy_name)

    def get_strategies_by_type(
        self, strategy_type: OptimizationStrategy
    ) -> List[OptimizationStrategyConfig]:
        """Pobiera wszystkie strategie danego typu"""
        return [
            config
            for config in self.strategies.values()
            if config.strategy_type == strategy_type
        ]

    def get_strategies_by_risk(
        self, risk_level: str
    ) -> List[OptimizationStrategyConfig]:
        """Pobiera strategie według poziomu ryzyka"""
        return [
            config
            for config in self.strategies.values()
            if config.risk_level == risk_level
        ]

    def get_high_impact_strategies(
        self, min_improvement: float = 20.0
    ) -> List[OptimizationStrategyConfig]:
        """Pobiera strategie z wysokim oczekiwanym wpływem"""
        return [
            config
            for config in self.strategies.values()
            if config.expected_improvement >= min_improvement
        ]

    def get_safe_strategies(self) -> List[OptimizationStrategyConfig]:
        """Pobiera bezpieczne strategie (low risk)"""
        return self.get_strategies_by_risk("low")

    def get_aggressive_strategies(self) -> List[OptimizationStrategyConfig]:
        """Pobiera agresywne strategie (high impact, medium/high risk)"""
        return [
            config
            for config in self.strategies.values()
            if config.expected_improvement >= 30.0
            and config.risk_level in ["medium", "high"]
        ]

    def generate_optimization_plan(
        self, target_metrics: List[str], max_risk: str = "medium"
    ) -> List[OptimizationStrategyConfig]:
        """Generuje plan optymalizacji na podstawie celów"""
        plan = []

        # Mapowanie poziomów ryzyka na wartości liczbowe
        risk_levels = {"low": 1, "medium": 2, "high": 3}
        max_risk_level = risk_levels.get(max_risk, 2)

        for config in self.strategies.values():
            if (
                config.target_metric in target_metrics
                and risk_levels.get(config.risk_level, 1) <= max_risk_level
            ):
                plan.append(config)

        # Sortuj po oczekiwanej poprawie (malejąco)
        plan.sort(key=lambda x: x.expected_improvement, reverse=True)

        return plan

    def get_strategy_dependencies(self, strategy_name: str) -> List[str]:
        """Pobiera zależności strategii"""
        strategy = self.get_strategy(strategy_name)
        if strategy and strategy.dependencies:
            return strategy.dependencies
        return []

    def validate_strategy_compatibility(self, strategy1: str, strategy2: str) -> bool:
        """Sprawdza kompatybilność dwóch strategii"""
        deps1 = self.get_strategy_dependencies(strategy1)
        deps2 = self.get_strategy_dependencies(strategy2)

        # Sprawdź czy strategie nie kolidują
        conflicts = [
            "cache_optimization",  # Może kolidować z memory_optimization
            "thread_safety",  # Może kolidować z performance_optimization
        ]

        for conflict in conflicts:
            if conflict in deps1 and conflict in deps2:
                return False

        return True

    def generate_combined_strategy(
        self, strategy_names: List[str]
    ) -> OptimizationStrategyConfig:
        """Generuje połączoną strategię z kilku strategii"""
        if not strategy_names:
            return None

        # Pobierz pierwszą strategię jako bazę
        base_strategy = self.get_strategy(strategy_names[0])
        if not base_strategy:
            return None

        # Połącz zmiany
        combined_changes = {
            "optimizations": base_strategy.changes.get("optimizations", []),
            "description": base_strategy.changes.get("description", []),
        }

        total_improvement = base_strategy.expected_improvement
        max_risk = base_strategy.risk_level

        # Dodaj pozostałe strategie
        for strategy_name in strategy_names[1:]:
            strategy = self.get_strategy(strategy_name)
            if strategy and self.validate_strategy_compatibility(
                strategy_names[0], strategy_name
            ):
                combined_changes["optimizations"].extend(
                    strategy.changes.get("optimizations", [])
                )
                combined_changes["description"].extend(
                    strategy.changes.get("description", [])
                )
                total_improvement += strategy.expected_improvement * 0.8  # 80% synergii

                # Podnieś poziom ryzyka
                if strategy.risk_level == "high":
                    max_risk = "high"
                elif strategy.risk_level == "medium" and max_risk == "low":
                    max_risk = "medium"

        return OptimizationStrategyConfig(
            strategy_type=OptimizationStrategy.ALGORITHM_OPTIMIZATION,  # Combined
            target_file=base_strategy.target_file,
            target_metric=base_strategy.target_metric,
            description=f"Połączona strategia: {', '.join(strategy_names)}",
            changes=combined_changes,
            expected_improvement=total_improvement,
            risk_level=max_risk,
            dependencies=strategy_names,
        )


class OptimizationStrategyExecutor:
    """Executor dla strategii optymalizacji"""

    def __init__(self, strategies_library: OptimizationStrategiesLibrary):
        self.library = strategies_library

    def execute_strategy(self, strategy_name: str) -> Dict[str, Any]:
        """Wykonuje pojedynczą strategię"""
        strategy = self.library.get_strategy(strategy_name)
        if not strategy:
            return {"error": f"Nieznana strategia: {strategy_name}"}

        return {
            "strategy_name": strategy_name,
            "strategy_type": strategy.strategy_type.value,
            "target_file": strategy.target_file,
            "target_metric": strategy.target_metric,
            "expected_improvement": strategy.expected_improvement,
            "risk_level": strategy.risk_level,
            "changes": strategy.changes,
        }

    def execute_optimization_plan(
        self, plan: List[OptimizationStrategyConfig]
    ) -> List[Dict[str, Any]]:
        """Wykonuje plan optymalizacji"""
        results = []

        for strategy in plan:
            result = self.execute_strategy(
                strategy.description.split(":")[0].lower().replace(" ", "_")
            )
            results.append(result)

        return results

    def generate_execution_report(self, results: List[Dict[str, Any]]) -> str:
        """Generuje raport z wykonania"""
        report = "# Raport Wykonania Strategii Optymalizacji\n\n"

        total_expected_improvement = 0
        successful_strategies = 0

        for result in results:
            if "error" not in result:
                successful_strategies += 1
                total_expected_improvement += result.get("expected_improvement", 0)

                report += f"## {result['strategy_name']}\n\n"
                report += f"- **Typ:** {result['strategy_type']}\n"
                report += f"- **Plik:** {result['target_file']}\n"
                report += f"- **Metryka:** {result['target_metric']}\n"
                report += (
                    f"- **Oczekiwana poprawa:** {result['expected_improvement']:.1f}%\n"
                )
                report += f"- **Poziom ryzyka:** {result['risk_level']}\n\n"
            else:
                report += f"## {result.get('strategy_name', 'Unknown')} - BŁĄD\n\n"
                report += f"**Błąd:** {result['error']}\n\n"

        report += f"## Podsumowanie\n\n"
        report += f"- **Udało się:** {successful_strategies}/{len(results)}\n"
        report += (
            f"- **Całkowita oczekiwana poprawa:** {total_expected_improvement:.1f}%\n"
        )

        return report


# Przykład użycia
if __name__ == "__main__":
    library = OptimizationStrategiesLibrary()
    executor = OptimizationStrategyExecutor(library)

    # Pobierz bezpieczne strategie
    safe_strategies = library.get_safe_strategies()
    print(f"Znaleziono {len(safe_strategies)} bezpiecznych strategii")

    # Wygeneruj plan optymalizacji
    plan = library.generate_optimization_plan(
        target_metrics=["gallery_load_time_ms", "memory_usage_mb"], max_risk="medium"
    )
    print(f"Wygenerowano plan z {len(plan)} strategiami")

    # Wykonaj plan
    results = executor.execute_optimization_plan(plan)

    # Wygeneruj raport
    report = executor.generate_execution_report(results)
    print(report)
