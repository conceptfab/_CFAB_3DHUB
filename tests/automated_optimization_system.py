#!/usr/bin/env python3
"""
AUTOMATYCZNY SYSTEM OPTYMALIZACJI I TESTOWANIA
System który automatycznie testuje, optymalizuje i dokumentuje rozwiązania
"""

import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.test_gallery_environment import GalleryTestStats, RealGalleryTestEnvironment


class OptimizationStatus(Enum):
    """Status optymalizacji"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    OPTIMAL = "optimal"


class TestCategory(Enum):
    """Kategorie testów"""

    PERFORMANCE = "performance"
    MEMORY = "memory"
    FUNCTIONALITY = "functionality"
    STABILITY = "stability"
    UI_RESPONSIVENESS = "ui_responsiveness"


@dataclass
class OptimizationResult:
    """Wynik optymalizacji"""

    revision_id: str
    timestamp: str
    category: str
    target_metric: str
    before_value: float
    after_value: float
    improvement_percent: float
    status: OptimizationStatus
    changes_made: List[str]
    test_results: Dict[str, Any]
    execution_time_ms: float
    memory_usage_mb: float
    success: bool
    error_message: Optional[str] = None


@dataclass
class OptimizationSession:
    """Sesja optymalizacji"""

    session_id: str
    start_time: str
    end_time: Optional[str]
    target_component: str
    optimization_goals: List[str]
    results: List[OptimizationResult]
    best_result: Optional[OptimizationResult]
    total_improvement: float
    status: OptimizationStatus


class AutomatedOptimizationSystem:
    """Główny system automatycznej optymalizacji"""

    def __init__(self):
        self.project_root = project_root
        self.optimization_dir = project_root / "optimization_history"
        self.revisions_dir = self.optimization_dir / "revisions"
        self.reports_dir = self.optimization_dir / "reports"
        self.backups_dir = self.optimization_dir / "backups"
        self.knowledge_base_dir = self.optimization_dir / "knowledge_base"

        # Utwórz strukturę katalogów
        self._create_directory_structure()

        # Konfiguracja loggera
        self._setup_logging()

        # Aktualna sesja
        self.current_session: Optional[OptimizationSession] = None

        # Środowisko testowe
        self.test_environment = None

        # Metryki bazowe
        self.baseline_metrics = {}

    def _create_directory_structure(self):
        """Tworzy strukturę katalogów dla systemu optymalizacji"""
        directories = [
            self.optimization_dir,
            self.revisions_dir,
            self.reports_dir,
            self.backups_dir,
            self.knowledge_base_dir,
            self.knowledge_base_dir / "best_practices",
            self.knowledge_base_dir / "performance_patterns",
            self.knowledge_base_dir / "memory_optimizations",
            self.knowledge_base_dir / "failed_attempts",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        print(f"📁 Utworzono strukturę katalogów w: {self.optimization_dir}")

    def _setup_logging(self):
        """Konfiguruje system logowania"""
        log_file = self.optimization_dir / "optimization.log"

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
        )

        self.logger = logging.getLogger("AutomatedOptimization")

    def start_optimization_session(
        self, target_component: str, goals: List[str]
    ) -> str:
        """Rozpoczyna nową sesję optymalizacji"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.current_session = OptimizationSession(
            session_id=session_id,
            start_time=datetime.now().isoformat(),
            end_time=None,
            target_component=target_component,
            optimization_goals=goals,
            results=[],
            best_result=None,
            total_improvement=0.0,
            status=OptimizationStatus.PENDING,
        )

        self.logger.info(f"🚀 Rozpoczęto sesję optymalizacji: {session_id}")
        self.logger.info(f"🎯 Cel: {target_component}")
        self.logger.info(f"📋 Cele: {goals}")

        return session_id

    def establish_baseline(self) -> Dict[str, float]:
        """Ustala metryki bazowe przed optymalizacją"""
        self.logger.info("📊 Ustalanie metryk bazowych...")

        try:
            # Inicjalizuj środowisko testowe
            self.test_environment = RealGalleryTestEnvironment()
            self.test_environment.setup_test_environment()

            # Uruchom pełny zestaw testów
            results = self.test_environment.run_comprehensive_test_suite()

            # Wyciągnij kluczowe metryki
            baseline_metrics = {
                "scan_time_ms": results.get(
                    "scan_performance", GalleryTestStats(0, 0, 0, 0, 0, 0, 0, 0, 0)
                ).scan_time_ms,
                "gallery_load_time_ms": results.get(
                    "gallery_performance", GalleryTestStats(0, 0, 0, 0, 0, 0, 0, 0, 0)
                ).gallery_load_time_ms,
                "tile_creation_time_ms": results.get(
                    "tile_performance", GalleryTestStats(0, 0, 0, 0, 0, 0, 0, 0, 0)
                ).tile_creation_time_ms,
                "memory_usage_mb": results.get("memory_usage", {}).get("after_mb", 0.0),
                "memory_increase_mb": results.get("memory_usage", {}).get(
                    "increase_mb", 0.0
                ),
                "total_files_processed": results.get(
                    "scan_performance", GalleryTestStats(0, 0, 0, 0, 0, 0, 0, 0, 0)
                ).total_files,
            }

            self.baseline_metrics = baseline_metrics

            self.logger.info(f"✅ Metryki bazowe ustalone:")
            for metric, value in baseline_metrics.items():
                self.logger.info(f"   {metric}: {value}")

            return baseline_metrics

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas ustalania metryk bazowych: {e}")
            raise

    def create_backup(self, revision_id: str) -> str:
        """Tworzy backup kodu przed optymalizacją"""
        backup_path = self.backups_dir / f"backup_{revision_id}"

        try:
            # Kopiuj kluczowe pliki
            key_files = [
                "src/ui/gallery_manager.py",
                "src/logic/scanner_core.py",
                "src/ui/widgets/file_tile_widget.py",
                "src/ui/main_window/main_window.py",
            ]

            for file_path in key_files:
                src_path = self.project_root / file_path
                if src_path.exists():
                    dst_path = backup_path / file_path
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dst_path)

            self.logger.info(f"💾 Utworzono backup: {backup_path}")
            return str(backup_path)

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas tworzenia backup: {e}")
            raise

    def apply_optimization(
        self, optimization_type: str, target_file: str, changes: Dict[str, Any]
    ) -> bool:
        """Aplikuje optymalizację do kodu"""
        try:
            file_path = self.project_root / target_file

            if not file_path.exists():
                self.logger.error(f"❌ Plik nie istnieje: {target_file}")
                return False

            # Wczytaj kod
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

            # Zastosuj zmiany
            modified_code = self._apply_code_changes(code, changes, optimization_type)

            # Zapisz zmodyfikowany kod
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(modified_code)

            self.logger.info(
                f"✅ Zastosowano optymalizację: {optimization_type} do {target_file}"
            )
            return True

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas aplikowania optymalizacji: {e}")
            return False

    def _apply_code_changes(
        self, code: str, changes: Dict[str, Any], optimization_type: str
    ) -> str:
        """Aplikuje zmiany do kodu na podstawie typu optymalizacji"""
        if optimization_type == "performance_optimization":
            return self._apply_performance_optimization(code, changes)
        elif optimization_type == "memory_optimization":
            return self._apply_memory_optimization(code, changes)
        elif optimization_type == "thread_safety_optimization":
            return self._apply_thread_safety_optimization(code, changes)
        else:
            return code

    def _apply_performance_optimization(
        self, code: str, changes: Dict[str, Any]
    ) -> str:
        """Aplikuje optymalizacje wydajnościowe"""
        # Przykładowe optymalizacje
        optimizations = changes.get("optimizations", [])

        for opt in optimizations:
            if opt.get("type") == "cache_optimization":
                # Dodaj cache dla często używanych obliczeń
                cache_code = """
# Performance optimization: Cache for frequently used calculations
_cache = {}
def get_cached_result(key, calculation_func):
    if key not in _cache:
        _cache[key] = calculation_func()
    return _cache[key]
"""
                # Wstaw cache na początku pliku
                code = cache_code + "\n" + code

            elif opt.get("type") == "loop_optimization":
                # Zoptymalizuj pętle
                old_pattern = opt.get("old_pattern", "for item in items:")
                new_pattern = opt.get("new_pattern", "for item in items:")
                code = code.replace(old_pattern, new_pattern)

        return code

    def _apply_memory_optimization(self, code: str, changes: Dict[str, Any]) -> str:
        """Aplikuje optymalizacje pamięci"""
        optimizations = changes.get("optimizations", [])

        for opt in optimizations:
            if opt.get("type") == "weak_references":
                # Dodaj weak references
                weak_ref_code = """
import weakref
# Memory optimization: Use weak references
_weak_cache = weakref.WeakValueDictionary()
"""
                code = weak_ref_code + "\n" + code

            elif opt.get("type") == "garbage_collection":
                # Dodaj explicit garbage collection
                gc_code = """
import gc
# Memory optimization: Explicit garbage collection
gc.collect()
"""
                code = code.replace("import gc", gc_code)

        return code

    def _apply_thread_safety_optimization(
        self, code: str, changes: Dict[str, Any]
    ) -> str:
        """Aplikuje optymalizacje thread safety"""
        optimizations = changes.get("optimizations", [])

        for opt in optimizations:
            if opt.get("type") == "threading_lock":
                # Dodaj threading locks
                lock_code = """
import threading
# Thread safety optimization: Add locks
_lock = threading.RLock()
"""
                code = lock_code + "\n" + code

            elif opt.get("type") == "atomic_operations":
                # Zastąp operacje atomowymi
                old_op = opt.get("old_operation", "counter += 1")
                new_op = opt.get("new_operation", "with _lock: counter += 1")
                code = code.replace(old_op, new_op)

        return code

    def run_tests_and_measure(self) -> Dict[str, Any]:
        """Uruchamia testy i mierzy wyniki"""
        try:
            if not self.test_environment:
                self.test_environment = RealGalleryTestEnvironment()
                self.test_environment.setup_test_environment()

            start_time = time.time()
            results = self.test_environment.run_comprehensive_test_suite()
            execution_time_ms = (time.time() - start_time) * 1000

            # Wyciągnij metryki
            metrics = {
                "scan_time_ms": results.get(
                    "scan_performance", GalleryTestStats(0, 0, 0, 0, 0, 0, 0, 0, 0)
                ).scan_time_ms,
                "gallery_load_time_ms": results.get(
                    "gallery_performance", GalleryTestStats(0, 0, 0, 0, 0, 0, 0, 0, 0)
                ).gallery_load_time_ms,
                "tile_creation_time_ms": results.get(
                    "tile_performance", GalleryTestStats(0, 0, 0, 0, 0, 0, 0, 0, 0)
                ).tile_creation_time_ms,
                "memory_usage_mb": results.get("memory_usage", {}).get("after_mb", 0.0),
                "memory_increase_mb": results.get("memory_usage", {}).get(
                    "increase_mb", 0.0
                ),
                "execution_time_ms": execution_time_ms,
                "success": "error" not in results,
            }

            return metrics

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas testowania: {e}")
            return {"error": str(e), "success": False, "execution_time_ms": 0}

    def calculate_improvement(
        self, before_metrics: Dict[str, float], after_metrics: Dict[str, float]
    ) -> Dict[str, float]:
        """Oblicza procentową poprawę metryk"""
        improvements = {}

        for metric in before_metrics:
            if metric in after_metrics:
                before_val = before_metrics[metric]
                after_val = after_metrics[metric]

                if before_val > 0:
                    if metric in [
                        "scan_time_ms",
                        "gallery_load_time_ms",
                        "tile_creation_time_ms",
                        "memory_usage_mb",
                    ]:
                        # Dla metryk czasowych i pamięci - mniejsze jest lepsze
                        improvement = ((before_val - after_val) / before_val) * 100
                    else:
                        # Dla innych metryk - większe jest lepsze
                        improvement = ((after_val - before_val) / before_val) * 100

                    improvements[metric] = improvement

        return improvements

    def save_optimization_result(self, result: OptimizationResult):
        """Zapisuje wynik optymalizacji"""
        try:
            # Zapisz do pliku JSON
            result_file = self.revisions_dir / f"revision_{result.revision_id}.json"
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(asdict(result), f, indent=2, ensure_ascii=False)

            # Dodaj do sesji
            if self.current_session:
                self.current_session.results.append(result)

                # Sprawdź czy to najlepszy wynik
                if (
                    not self.current_session.best_result
                    or result.improvement_percent
                    > self.current_session.best_result.improvement_percent
                ):
                    self.current_session.best_result = result

            self.logger.info(f"💾 Zapisano wynik optymalizacji: {result.revision_id}")

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas zapisywania wyniku: {e}")

    def generate_optimization_report(self) -> str:
        """Generuje raport z optymalizacji"""
        if not self.current_session:
            return "Brak aktywnej sesji optymalizacji"

        report_file = self.reports_dir / f"report_{self.current_session.session_id}.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(f"# Raport Optymalizacji: {self.current_session.session_id}\n\n")
            f.write(f"**Data:** {self.current_session.start_time}\n")
            f.write(f"**Komponent:** {self.current_session.target_component}\n")
            f.write(
                f"**Cele:** {', '.join(self.current_session.optimization_goals)}\n\n"
            )

            f.write("## Podsumowanie\n\n")
            f.write(f"- **Liczba rewizji:** {len(self.current_session.results)}\n")
            f.write(f"- **Status:** {self.current_session.status.value}\n")

            if self.current_session.best_result:
                f.write(
                    f"- **Najlepsza poprawa:** {self.current_session.best_result.improvement_percent:.2f}%\n"
                )
                f.write(
                    f"- **Metryka:** {self.current_session.best_result.target_metric}\n"
                )

            f.write("\n## Szczegółowe Wyniki\n\n")

            for i, result in enumerate(self.current_session.results, 1):
                f.write(f"### Rewizja {i}: {result.revision_id}\n\n")
                f.write(f"- **Kategoria:** {result.category}\n")
                f.write(f"- **Poprawa:** {result.improvement_percent:.2f}%\n")
                f.write(f"- **Status:** {result.status.value}\n")
                f.write(f"- **Czas wykonania:** {result.execution_time_ms:.2f}ms\n")
                f.write(f"- **Pamięć:** {result.memory_usage_mb:.2f}MB\n")

                if result.changes_made:
                    f.write("- **Zmiany:**\n")
                    for change in result.changes_made:
                        f.write(f"  - {change}\n")

                if result.error_message:
                    f.write(f"- **Błąd:** {result.error_message}\n")

                f.write("\n")

        self.logger.info(f"📊 Wygenerowano raport: {report_file}")
        return str(report_file)

    def update_knowledge_base(self, result: OptimizationResult):
        """Aktualizuje bazę wiedzy na podstawie wyniku"""
        try:
            if result.success and result.improvement_percent > 0:
                # Dodaj do best practices
                best_practices_file = (
                    self.knowledge_base_dir
                    / "best_practices"
                    / f"{result.category}.json"
                )

                if best_practices_file.exists():
                    with open(best_practices_file, "r", encoding="utf-8") as f:
                        practices = json.load(f)
                else:
                    practices = []

                practice_entry = {
                    "timestamp": result.timestamp,
                    "improvement_percent": result.improvement_percent,
                    "target_metric": result.target_metric,
                    "changes_made": result.changes_made,
                    "test_results": result.test_results,
                }

                practices.append(practice_entry)

                # Sortuj po poprawie (malejąco)
                practices.sort(key=lambda x: x["improvement_percent"], reverse=True)

                # Zachowaj tylko top 10
                practices = practices[:10]

                with open(best_practices_file, "w", encoding="utf-8") as f:
                    json.dump(practices, f, indent=2, ensure_ascii=False)

                self.logger.info(f"📚 Zaktualizowano bazę wiedzy: {result.category}")

            elif not result.success:
                # Dodaj do failed attempts
                failed_file = (
                    self.knowledge_base_dir
                    / "failed_attempts"
                    / f"{result.category}.json"
                )

                if failed_file.exists():
                    with open(failed_file, "r", encoding="utf-8") as f:
                        failed_attempts = json.load(f)
                else:
                    failed_attempts = []

                failed_entry = {
                    "timestamp": result.timestamp,
                    "error_message": result.error_message,
                    "changes_made": result.changes_made,
                    "target_metric": result.target_metric,
                }

                failed_attempts.append(failed_entry)

                with open(failed_file, "w", encoding="utf-8") as f:
                    json.dump(failed_attempts, f, indent=2, ensure_ascii=False)

                self.logger.info(f"📚 Zapisano nieudaną próbę: {result.category}")

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas aktualizacji bazy wiedzy: {e}")

    def run_optimization_cycle(
        self, optimization_config: Dict[str, Any]
    ) -> OptimizationResult:
        """Uruchamia pełny cykl optymalizacji"""
        revision_id = f"rev_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.logger.info(f"🔄 Rozpoczęto cykl optymalizacji: {revision_id}")

        try:
            # 1. Utwórz backup
            backup_path = self.create_backup(revision_id)

            # 2. Aplikuj optymalizację
            success = self.apply_optimization(
                optimization_config["type"],
                optimization_config["target_file"],
                optimization_config["changes"],
            )

            if not success:
                raise Exception("Nie udało się zastosować optymalizacji")

            # 3. Uruchom testy
            test_results = self.run_tests_and_measure()

            # 4. Oblicz poprawę
            improvements = self.calculate_improvement(
                self.baseline_metrics, test_results
            )

            # 5. Utwórz wynik
            target_metric = optimization_config.get(
                "target_metric", "gallery_load_time_ms"
            )
            improvement_percent = improvements.get(target_metric, 0.0)

            result = OptimizationResult(
                revision_id=revision_id,
                timestamp=datetime.now().isoformat(),
                category=optimization_config["type"],
                target_metric=target_metric,
                before_value=self.baseline_metrics.get(target_metric, 0.0),
                after_value=test_results.get(target_metric, 0.0),
                improvement_percent=improvement_percent,
                status=(
                    OptimizationStatus.COMPLETED
                    if test_results.get("success", False)
                    else OptimizationStatus.FAILED
                ),
                changes_made=optimization_config["changes"].get("description", []),
                test_results=test_results,
                execution_time_ms=test_results.get("execution_time_ms", 0.0),
                memory_usage_mb=test_results.get("memory_usage_mb", 0.0),
                success=test_results.get("success", False),
                error_message=test_results.get("error"),
            )

            # 6. Zapisz wynik
            self.save_optimization_result(result)

            # 7. Aktualizuj bazę wiedzy
            self.update_knowledge_base(result)

            self.logger.info(f"✅ Zakończono cykl optymalizacji: {revision_id}")
            self.logger.info(f"📈 Poprawa: {improvement_percent:.2f}%")

            return result

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas cyklu optymalizacji: {e}")

            # Utwórz wynik błędu
            result = OptimizationResult(
                revision_id=revision_id,
                timestamp=datetime.now().isoformat(),
                category=optimization_config["type"],
                target_metric=optimization_config.get("target_metric", "unknown"),
                before_value=0.0,
                after_value=0.0,
                improvement_percent=0.0,
                status=OptimizationStatus.FAILED,
                changes_made=optimization_config["changes"].get("description", []),
                test_results={},
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
                success=False,
                error_message=str(e),
            )

            self.save_optimization_result(result)
            return result

    def end_optimization_session(self):
        """Kończy sesję optymalizacji"""
        if self.current_session:
            self.current_session.end_time = datetime.now().isoformat()
            self.current_session.status = OptimizationStatus.COMPLETED

            # Oblicz całkowitą poprawę
            if self.current_session.best_result:
                self.current_session.total_improvement = (
                    self.current_session.best_result.improvement_percent
                )

            # Wygeneruj raport
            report_file = self.generate_optimization_report()

            # Zapisz sesję
            session_file = (
                self.optimization_dir
                / f"session_{self.current_session.session_id}.json"
            )
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(asdict(self.current_session), f, indent=2, ensure_ascii=False)

            self.logger.info(
                f"🏁 Zakończono sesję optymalizacji: {self.current_session.session_id}"
            )
            self.logger.info(f"📊 Raport: {report_file}")
            self.logger.info(
                f"📈 Całkowita poprawa: {self.current_session.total_improvement:.2f}%"
            )

            # Cleanup
            if self.test_environment:
                self.test_environment.cleanup_test_environment()
                self.test_environment = None


def main():
    """Przykład użycia systemu automatycznej optymalizacji"""
    system = AutomatedOptimizationSystem()

    # Rozpocznij sesję
    session_id = system.start_optimization_session(
        target_component="GalleryManager",
        goals=["Zmniejszenie czasu ładowania galerii", "Optymalizacja użycia pamięci"],
    )

    try:
        # Ustal metryki bazowe
        baseline = system.establish_baseline()

        # Konfiguracje optymalizacji do przetestowania
        optimization_configs = [
            {
                "type": "performance_optimization",
                "target_file": "src/ui/gallery_manager.py",
                "target_metric": "gallery_load_time_ms",
                "changes": {
                    "optimizations": [
                        {
                            "type": "cache_optimization",
                            "description": "Dodano cache dla obliczeń geometrii",
                        }
                    ],
                    "description": ["Dodano cache dla obliczeń geometrii"],
                },
            },
            {
                "type": "memory_optimization",
                "target_file": "src/ui/gallery_manager.py",
                "target_metric": "memory_usage_mb",
                "changes": {
                    "optimizations": [
                        {
                            "type": "weak_references",
                            "description": "Zastąpiono strong references weak references",
                        }
                    ],
                    "description": ["Zastąpiono strong references weak references"],
                },
            },
        ]

        # Uruchom cykle optymalizacji
        for config in optimization_configs:
            result = system.run_optimization_cycle(config)
            print(
                f"Rewizja {result.revision_id}: {result.improvement_percent:.2f}% poprawa"
            )

    finally:
        # Zakończ sesję
        system.end_optimization_session()


if __name__ == "__main__":
    main()
