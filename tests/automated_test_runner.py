#!/usr/bin/env python3
"""
AUTOMATYCZNY RUNNER TESTOW
Runner który automatycznie testuje, optymalizuje i dokumentuje wyniki
"""

import json
import logging
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.automated_optimization_system import (
    AutomatedOptimizationSystem,
    OptimizationResult,
)
from tests.optimization_strategies import (
    OptimizationStrategiesLibrary,
    OptimizationStrategyExecutor,
)
from tests.test_gallery_environment import RealGalleryTestEnvironment


@dataclass
class TestRunResult:
    """Wynik pojedynczego uruchomienia testów"""

    run_id: str
    timestamp: str
    test_suite: str
    execution_time_ms: float
    success: bool
    metrics: Dict[str, float]
    error_message: Optional[str] = None
    optimization_applied: Optional[str] = None


@dataclass
class TestSuiteResult:
    """Wynik całego zestawu testów"""

    suite_id: str
    start_time: str
    end_time: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    average_execution_time_ms: float
    best_metrics: Dict[str, float]
    worst_metrics: Dict[str, float]
    improvements: Dict[str, float]
    optimization_history: List[str]


class AutomatedTestRunner:
    """Automatyczny runner testów z optymalizacją"""

    def __init__(self):
        self.project_root = project_root
        self.test_results_dir = project_root / "test_results"
        self.test_results_dir.mkdir(exist_ok=True)

        # Systemy
        self.optimization_system = AutomatedOptimizationSystem()
        self.strategies_library = OptimizationStrategiesLibrary()
        self.strategy_executor = OptimizationStrategyExecutor(self.strategies_library)

        # Środowisko testowe
        self.test_environment = None

        # Konfiguracja
        self.max_iterations = 10
        self.improvement_threshold = 5.0  # 5% poprawa
        self.convergence_threshold = 3  # 3 iteracje bez poprawy

        # Logger
        self._setup_logging()

        # Wyniki
        self.current_suite_result: Optional[TestSuiteResult] = None
        self.test_history: List[TestRunResult] = []

    def _setup_logging(self):
        """Konfiguruje system logowania"""
        log_file = self.test_results_dir / "test_runner.log"

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
        )

        self.logger = logging.getLogger("AutomatedTestRunner")

    def start_test_suite(self, suite_name: str, target_metrics: List[str]) -> str:
        """Rozpoczyna nowy zestaw testów"""
        suite_id = f"suite_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.current_suite_result = TestSuiteResult(
            suite_id=suite_id,
            start_time=datetime.now().isoformat(),
            end_time="",
            total_runs=0,
            successful_runs=0,
            failed_runs=0,
            average_execution_time_ms=0.0,
            best_metrics={},
            worst_metrics={},
            improvements={},
            optimization_history=[],
        )

        self.test_history = []

        self.logger.info(f"🚀 Rozpoczęto zestaw testów: {suite_id}")
        self.logger.info(f"📋 Nazwa: {suite_name}")
        self.logger.info(f"🎯 Metryki: {target_metrics}")

        return suite_id

    def run_baseline_test(self) -> TestRunResult:
        """Uruchamia test bazowy bez optymalizacji"""
        self.logger.info("📊 Uruchamianie testu bazowego...")

        run_id = f"baseline_{datetime.now().strftime('%H%M%S')}"
        start_time = time.time()

        try:
            # Inicjalizuj środowisko testowe
            if not self.test_environment:
                self.test_environment = RealGalleryTestEnvironment()
                self.test_environment.setup_test_environment()

            # Uruchom testy
            results = self.test_environment.run_comprehensive_test_suite()
            execution_time_ms = (time.time() - start_time) * 1000

            # Wyciągnij metryki
            metrics = self._extract_metrics(results)

            result = TestRunResult(
                run_id=run_id,
                timestamp=datetime.now().isoformat(),
                test_suite="baseline",
                execution_time_ms=execution_time_ms,
                success=results.get("success", True),
                metrics=metrics,
                optimization_applied=None,
            )

            self.logger.info(f"✅ Test bazowy zakończony: {execution_time_ms:.2f}ms")
            return result

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas testu bazowego: {e}")

            return TestRunResult(
                run_id=run_id,
                timestamp=datetime.now().isoformat(),
                test_suite="baseline",
                execution_time_ms=(time.time() - start_time) * 1000,
                success=False,
                metrics={},
                error_message=str(e),
                optimization_applied=None,
            )

    def _extract_metrics(self, test_results: Dict[str, Any]) -> Dict[str, float]:
        """Wyciąga metryki z wyników testów"""
        metrics = {}

        # Metryki skanowania
        if "scan_performance" in test_results:
            scan_stats = test_results["scan_performance"]
            metrics["scan_time_ms"] = scan_stats.scan_time_ms
            metrics["files_per_second"] = scan_stats.files_per_second
            metrics["total_files"] = scan_stats.total_files

        # Metryki galerii
        if "gallery_performance" in test_results:
            gallery_stats = test_results["gallery_performance"]
            metrics["gallery_load_time_ms"] = gallery_stats.gallery_load_time_ms
            metrics["tiles_per_second"] = gallery_stats.tiles_per_second
            metrics["total_tiles"] = gallery_stats.total_tiles

        # Metryki kafelków
        if "tile_performance" in test_results:
            tile_stats = test_results["tile_performance"]
            metrics["tile_creation_time_ms"] = tile_stats.tile_creation_time_ms
            metrics["tiles_created"] = tile_stats.tiles_created

        # Metryki pamięci
        if "memory_usage" in test_results:
            memory_stats = test_results["memory_usage"]
            metrics["memory_usage_mb"] = memory_stats.get("after_mb", 0.0)
            metrics["memory_increase_mb"] = memory_stats.get("increase_mb", 0.0)

        return metrics

    def run_optimization_test(self, strategy_name: str) -> TestRunResult:
        """Uruchamia test z zastosowaną optymalizacją"""
        self.logger.info(f"🔧 Uruchamianie testu z optymalizacją: {strategy_name}")

        run_id = f"opt_{strategy_name}_{datetime.now().strftime('%H%M%S')}"
        start_time = time.time()

        try:
            # Pobierz strategię
            strategy = self.strategies_library.get_strategy(strategy_name)
            if not strategy:
                raise ValueError(f"Nieznana strategia: {strategy_name}")

            # Zastosuj optymalizację
            success = self.optimization_system.apply_optimization(
                strategy.strategy_type.value, strategy.target_file, strategy.changes
            )

            if not success:
                raise Exception(
                    f"Nie udało się zastosować optymalizacji: {strategy_name}"
                )

            # Uruchom testy
            results = self.test_environment.run_comprehensive_test_suite()
            execution_time_ms = (time.time() - start_time) * 1000

            # Wyciągnij metryki
            metrics = self._extract_metrics(results)

            result = TestRunResult(
                run_id=run_id,
                timestamp=datetime.now().isoformat(),
                test_suite=f"optimization_{strategy_name}",
                execution_time_ms=execution_time_ms,
                success=results.get("success", True),
                metrics=metrics,
                optimization_applied=strategy_name,
            )

            self.logger.info(
                f"✅ Test z optymalizacją zakończony: {execution_time_ms:.2f}ms"
            )
            return result

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas testu z optymalizacją: {e}")

            return TestRunResult(
                run_id=run_id,
                timestamp=datetime.now().isoformat(),
                test_suite=f"optimization_{strategy_name}",
                execution_time_ms=(time.time() - start_time) * 1000,
                success=False,
                metrics={},
                error_message=str(e),
                optimization_applied=strategy_name,
            )

    def calculate_improvement(
        self, baseline_metrics: Dict[str, float], current_metrics: Dict[str, float]
    ) -> Dict[str, float]:
        """Oblicza poprawę względem testu bazowego"""
        improvements = {}

        for metric in baseline_metrics:
            if metric in current_metrics:
                baseline_val = baseline_metrics[metric]
                current_val = current_metrics[metric]

                if baseline_val > 0:
                    if metric in [
                        "scan_time_ms",
                        "gallery_load_time_ms",
                        "tile_creation_time_ms",
                        "memory_usage_mb",
                    ]:
                        # Dla metryk czasowych i pamięci - mniejsze jest lepsze
                        improvement = (
                            (baseline_val - current_val) / baseline_val
                        ) * 100
                    else:
                        # Dla innych metryk - większe jest lepsze
                        improvement = (
                            (current_val - baseline_val) / baseline_val
                        ) * 100

                    improvements[metric] = improvement

        return improvements

    def select_next_strategy(
        self, baseline_metrics: Dict[str, float], applied_strategies: List[str]
    ) -> Optional[str]:
        """Wybiera następną strategię do przetestowania"""
        # Pobierz wszystkie dostępne strategie
        all_strategies = list(self.strategies_library.strategies.keys())

        # Wyklucz już zastosowane
        available_strategies = [
            s for s in all_strategies if s not in applied_strategies
        ]

        if not available_strategies:
            return None

        # Sortuj według oczekiwanej poprawy dla głównych metryk
        strategy_scores = []

        for strategy_name in available_strategies:
            strategy = self.strategies_library.get_strategy(strategy_name)
            if not strategy:
                continue

            # Sprawdź czy strategia dotyczy głównych metryk
            if strategy.target_metric in baseline_metrics:
                score = strategy.expected_improvement

                # Bonus dla bezpiecznych strategii
                if strategy.risk_level == "low":
                    score *= 1.2

                strategy_scores.append((strategy_name, score))

        # Sortuj malejąco po score
        strategy_scores.sort(key=lambda x: x[1], reverse=True)

        if strategy_scores:
            return strategy_scores[0][0]

        return None

    def run_automated_optimization_cycle(
        self, target_metrics: List[str]
    ) -> TestSuiteResult:
        """Uruchamia automatyczny cykl optymalizacji"""
        self.logger.info("🔄 Rozpoczęcie automatycznego cyklu optymalizacji")

        # Rozpocznij zestaw testów
        suite_id = self.start_test_suite("automated_optimization", target_metrics)

        try:
            # Test bazowy
            baseline_result = self.run_baseline_test()
            self.test_history.append(baseline_result)

            if not baseline_result.success:
                self.logger.error("❌ Test bazowy nie powiódł się - przerwanie cyklu")
                return self._finalize_test_suite()

            baseline_metrics = baseline_result.metrics
            applied_strategies = []
            consecutive_no_improvement = 0

            self.logger.info(f"📊 Metryki bazowe: {baseline_metrics}")

            # Cykl optymalizacji
            for iteration in range(self.max_iterations):
                self.logger.info(f"🔄 Iteracja {iteration + 1}/{self.max_iterations}")

                # Wybierz następną strategię
                next_strategy = self.select_next_strategy(
                    baseline_metrics, applied_strategies
                )

                if not next_strategy:
                    self.logger.info("✅ Wszystkie strategie zostały przetestowane")
                    break

                self.logger.info(f"🎯 Wybrana strategia: {next_strategy}")

                # Uruchom test z optymalizacją
                test_result = self.run_optimization_test(next_strategy)
                self.test_history.append(test_result)

                if test_result.success:
                    # Oblicz poprawę
                    improvements = self.calculate_improvement(
                        baseline_metrics, test_result.metrics
                    )

                    # Sprawdź czy jest znacząca poprawa
                    main_metric = self.strategies_library.get_strategy(
                        next_strategy
                    ).target_metric
                    improvement = improvements.get(main_metric, 0.0)

                    if improvement >= self.improvement_threshold:
                        self.logger.info(f"✅ Znacząca poprawa: {improvement:.2f}%")
                        applied_strategies.append(next_strategy)
                        consecutive_no_improvement = 0

                        # Aktualizuj metryki bazowe
                        baseline_metrics = test_result.metrics
                    else:
                        self.logger.info(
                            f"⚠️ Brak znaczącej poprawy: {improvement:.2f}%"
                        )
                        consecutive_no_improvement += 1

                        # Cofnij optymalizację
                        self._revert_optimization(next_strategy)
                else:
                    self.logger.warning(
                        f"⚠️ Test z optymalizacją nie powiódł się: {test_result.error_message}"
                    )
                    consecutive_no_improvement += 1

                    # Cofnij optymalizację
                    self._revert_optimization(next_strategy)

                # Sprawdź konwergencję
                if consecutive_no_improvement >= self.convergence_threshold:
                    self.logger.info(
                        f"🛑 Konwergencja osiągnięta po {iteration + 1} iteracjach"
                    )
                    break

            # Finalizuj zestaw testów
            return self._finalize_test_suite()

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas cyklu optymalizacji: {e}")
            return self._finalize_test_suite()

    def _revert_optimization(self, strategy_name: str):
        """Cofa zastosowaną optymalizację"""
        try:
            strategy = self.strategies_library.get_strategy(strategy_name)
            if not strategy:
                return

            # Przywróć z backup
            backup_path = (
                self.optimization_system.backups_dir / f"backup_{strategy_name}"
            )
            if backup_path.exists():
                # Przywróć plik
                target_file = self.project_root / strategy.target_file
                backup_file = backup_path / strategy.target_file

                if backup_file.exists():
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    import shutil

                    shutil.copy2(backup_file, target_file)

                    self.logger.info(f"🔄 Przywrócono backup dla: {strategy_name}")

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas cofania optymalizacji: {e}")

    def _finalize_test_suite(self) -> TestSuiteResult:
        """Finalizuje zestaw testów"""
        if not self.current_suite_result:
            return None

        self.current_suite_result.end_time = datetime.now().isoformat()
        self.current_suite_result.total_runs = len(self.test_history)
        self.current_suite_result.successful_runs = len(
            [r for r in self.test_history if r.success]
        )
        self.current_suite_result.failed_runs = len(
            [r for r in self.test_history if not r.success]
        )

        # Oblicz średni czas wykonania
        if self.test_history:
            total_time = sum(r.execution_time_ms for r in self.test_history)
            self.current_suite_result.average_execution_time_ms = total_time / len(
                self.test_history
            )

        # Znajdź najlepsze i najgorsze metryki
        if self.test_history:
            all_metrics = [r.metrics for r in self.test_history if r.metrics]
            if all_metrics:
                # Najlepsze metryki (najmniejsze czasy, największe throughput)
                self.current_suite_result.best_metrics = {}
                self.current_suite_result.worst_metrics = {}

                for metric in all_metrics[0].keys():
                    values = [
                        m.get(metric, 0) for m in all_metrics if m.get(metric, 0) > 0
                    ]
                    if values:
                        if metric in [
                            "scan_time_ms",
                            "gallery_load_time_ms",
                            "tile_creation_time_ms",
                            "memory_usage_mb",
                        ]:
                            # Dla metryk czasowych - najmniejsze jest najlepsze
                            best_value = min(values)
                            worst_value = max(values)
                        else:
                            # Dla innych metryk - największe jest najlepsze
                            best_value = max(values)
                            worst_value = min(values)

                        self.current_suite_result.best_metrics[metric] = best_value
                        self.current_suite_result.worst_metrics[metric] = worst_value

        # Historia optymalizacji
        self.current_suite_result.optimization_history = [
            r.optimization_applied for r in self.test_history if r.optimization_applied
        ]

        # Zapisz wyniki
        self._save_test_suite_results()

        return self.current_suite_result

    def _save_test_suite_results(self):
        """Zapisuje wyniki zestawu testów"""
        if not self.current_suite_result:
            return

        try:
            # Zapisz główny wynik
            suite_file = (
                self.test_results_dir
                / f"suite_{self.current_suite_result.suite_id}.json"
            )
            with open(suite_file, "w", encoding="utf-8") as f:
                json.dump(
                    self.current_suite_result.__dict__, f, indent=2, ensure_ascii=False
                )

            # Zapisz szczegółowe wyniki testów
            details_file = (
                self.test_results_dir
                / f"details_{self.current_suite_result.suite_id}.json"
            )
            with open(details_file, "w", encoding="utf-8") as f:
                json.dump(
                    [r.__dict__ for r in self.test_history],
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            # Wygeneruj raport
            self._generate_test_report()

            self.logger.info(f"💾 Zapisano wyniki zestawu testów: {suite_file}")

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas zapisywania wyników: {e}")

    def _generate_test_report(self):
        """Generuje raport z testów"""
        if not self.current_suite_result:
            return

        report_file = (
            self.test_results_dir / f"report_{self.current_suite_result.suite_id}.md"
        )

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(
                f"# Raport Automatycznego Testowania: {self.current_suite_result.suite_id}\n\n"
            )
            f.write(f"**Data rozpoczęcia:** {self.current_suite_result.start_time}\n")
            f.write(f"**Data zakończenia:** {self.current_suite_result.end_time}\n\n")

            f.write("## Podsumowanie\n\n")
            f.write(
                f"- **Całkowita liczba uruchomień:** {self.current_suite_result.total_runs}\n"
            )
            f.write(f"- **Udało się:** {self.current_suite_result.successful_runs}\n")
            f.write(f"- **Nie udało się:** {self.current_suite_result.failed_runs}\n")
            f.write(
                f"- **Średni czas wykonania:** {self.current_suite_result.average_execution_time_ms:.2f}ms\n\n"
            )

            f.write("## Historia Optymalizacji\n\n")
            for i, optimization in enumerate(
                self.current_suite_result.optimization_history, 1
            ):
                f.write(f"{i}. {optimization}\n")
            f.write("\n")

            f.write("## Najlepsze Metryki\n\n")
            for metric, value in self.current_suite_result.best_metrics.items():
                f.write(f"- **{metric}:** {value:.2f}\n")
            f.write("\n")

            f.write("## Szczegółowe Wyniki\n\n")
            for result in self.test_history:
                f.write(f"### {result.run_id}\n\n")
                f.write(f"- **Czas:** {result.timestamp}\n")
                f.write(f"- **Test:** {result.test_suite}\n")
                f.write(f"- **Czas wykonania:** {result.execution_time_ms:.2f}ms\n")
                f.write(f"- **Status:** {'✅' if result.success else '❌'}\n")

                if result.optimization_applied:
                    f.write(f"- **Optymalizacja:** {result.optimization_applied}\n")

                if result.metrics:
                    f.write("- **Metryki:**\n")
                    for metric, value in result.metrics.items():
                        f.write(f"  - {metric}: {value:.2f}\n")

                if result.error_message:
                    f.write(f"- **Błąd:** {result.error_message}\n")

                f.write("\n")

        self.logger.info(f"📊 Wygenerowano raport: {report_file}")


def main():
    """Przykład użycia automatycznego runnera testów"""
    runner = AutomatedTestRunner()

    # Uruchom automatyczny cykl optymalizacji
    target_metrics = ["gallery_load_time_ms", "memory_usage_mb", "scan_time_ms"]

    print("🚀 Rozpoczęcie automatycznego testowania i optymalizacji...")
    print(f"🎯 Metryki docelowe: {target_metrics}")

    suite_result = runner.run_automated_optimization_cycle(target_metrics)

    if suite_result:
        print(f"\n✅ Zestaw testów zakończony: {suite_result.suite_id}")
        print(f"📊 Udało się: {suite_result.successful_runs}/{suite_result.total_runs}")
        print(f"⏱️ Średni czas: {suite_result.average_execution_time_ms:.2f}ms")
        print(f"🔧 Zastosowane optymalizacje: {len(suite_result.optimization_history)}")

        if suite_result.best_metrics:
            print("\n🏆 Najlepsze metryki:")
            for metric, value in suite_result.best_metrics.items():
                print(f"   {metric}: {value:.2f}")
    else:
        print("❌ Błąd podczas testowania")


if __name__ == "__main__":
    main()
