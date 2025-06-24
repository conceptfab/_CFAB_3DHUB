#!/usr/bin/env python3
"""
GŁÓWNY SKRYPT AUTOMATYCZNEJ OPTYMALIZACJI
Uruchamia kompletny system testowania, optymalizacji i dokumentowania
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.automated_optimization_system import AutomatedOptimizationSystem
from tests.automated_test_runner import AutomatedTestRunner
from tests.knowledge_base_manager import (
    EffectivenessLevel,
    KnowledgeBaseManager,
    KnowledgeCategory,
)
from tests.optimization_strategies import OptimizationStrategiesLibrary


class AutomatedOptimizationOrchestrator:
    """Orchestrator całego systemu automatycznej optymalizacji"""

    def __init__(self):
        self.project_root = project_root
        self.results_dir = project_root / "optimization_results"
        self.results_dir.mkdir(exist_ok=True)

        # Inicjalizuj komponenty
        self.optimization_system = AutomatedOptimizationSystem()
        self.strategies_library = OptimizationStrategiesLibrary()
        self.test_runner = AutomatedTestRunner()
        self.knowledge_manager = KnowledgeBaseManager()

        # Konfiguracja
        self.config = {
            "max_iterations": 15,
            "improvement_threshold": 5.0,
            "convergence_threshold": 3,
            "target_metrics": [
                "gallery_load_time_ms",
                "memory_usage_mb",
                "scan_time_ms",
            ],
            "focus_components": ["GalleryManager", "scanner_core", "file_tile_widget"],
            "risk_tolerance": "medium",  # low, medium, high
        }

        print("🚀 Inicjalizacja systemu automatycznej optymalizacji...")
        print(f"📁 Wyniki będą zapisywane w: {self.results_dir}")

    def run_full_optimization_cycle(
        self, custom_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Uruchamia pełny cykl optymalizacji"""
        if custom_config:
            self.config.update(custom_config)

        session_id = f"full_cycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        print(f"\n🔄 Rozpoczęcie pełnego cyklu optymalizacji: {session_id}")
        print(f"🎯 Metryki docelowe: {self.config['target_metrics']}")
        print(f"🔧 Komponenty: {self.config['focus_components']}")
        print(f"⚠️ Tolerancja ryzyka: {self.config['risk_tolerance']}")

        results = {
            "session_id": session_id,
            "start_time": datetime.now().isoformat(),
            "config": self.config.copy(),
            "phases": [],
            "final_results": {},
            "knowledge_gained": [],
            "recommendations": [],
        }

        try:
            # FAZA 1: Ustalenie metryk bazowych
            print("\n📊 FAZA 1: Ustalenie metryk bazowych...")
            baseline_phase = self._run_baseline_phase()
            results["phases"].append(baseline_phase)

            if not baseline_phase["success"]:
                print("❌ Nie udało się ustalić metryk bazowych - przerwanie")
                return results

            # FAZA 2: Analiza bazy wiedzy
            print("\n📚 FAZA 2: Analiza bazy wiedzy...")
            knowledge_phase = self._run_knowledge_analysis_phase()
            results["phases"].append(knowledge_phase)

            # FAZA 3: Automatyczna optymalizacja
            print("\n🔧 FAZA 3: Automatyczna optymalizacja...")
            optimization_phase = self._run_optimization_phase(
                baseline_phase["baseline_metrics"]
            )
            results["phases"].append(optimization_phase)

            # FAZA 4: Analiza wyników
            print("\n📈 FAZA 4: Analiza wyników...")
            analysis_phase = self._run_analysis_phase(results["phases"])
            results["phases"].append(analysis_phase)

            # FAZA 5: Aktualizacja bazy wiedzy
            print("\n📝 FAZA 5: Aktualizacja bazy wiedzy...")
            knowledge_update_phase = self._run_knowledge_update_phase(results["phases"])
            results["phases"].append(knowledge_update_phase)

            # FAZA 6: Generowanie rekomendacji
            print("\n💡 FAZA 6: Generowanie rekomendacji...")
            recommendations_phase = self._run_recommendations_phase(results["phases"])
            results["phases"].append(recommendations_phase)

            results["final_results"] = analysis_phase["final_metrics"]
            results["knowledge_gained"] = knowledge_update_phase["new_entries"]
            results["recommendations"] = recommendations_phase["recommendations"]

            print(f"\n✅ Pełny cykl optymalizacji zakończony: {session_id}")

        except Exception as e:
            print(f"❌ Błąd podczas cyklu optymalizacji: {e}")
            results["error"] = str(e)

        finally:
            results["end_time"] = datetime.now().isoformat()
            self._save_session_results(results)

        return results

    def _run_baseline_phase(self) -> Dict[str, Any]:
        """Uruchamia fazę ustalania metryk bazowych"""
        phase_result = {
            "phase": "baseline",
            "start_time": datetime.now().isoformat(),
            "success": False,
            "baseline_metrics": {},
            "execution_time_ms": 0,
        }

        try:
            start_time = time.time()

            # Ustal metryki bazowe
            baseline_metrics = self.optimization_system.establish_baseline()

            execution_time = (time.time() - start_time) * 1000

            phase_result.update(
                {
                    "success": True,
                    "baseline_metrics": baseline_metrics,
                    "execution_time_ms": execution_time,
                    "end_time": datetime.now().isoformat(),
                }
            )

            print(f"✅ Metryki bazowe ustalone w {execution_time:.2f}ms")
            for metric, value in baseline_metrics.items():
                print(f"   {metric}: {value}")

        except Exception as e:
            print(f"❌ Błąd podczas ustalania metryk bazowych: {e}")
            phase_result["error"] = str(e)
            phase_result["end_time"] = datetime.now().isoformat()

        return phase_result

    def _run_knowledge_analysis_phase(self) -> Dict[str, Any]:
        """Uruchamia fazę analizy bazy wiedzy"""
        phase_result = {
            "phase": "knowledge_analysis",
            "start_time": datetime.now().isoformat(),
            "success": False,
            "existing_patterns": [],
            "best_practices": [],
            "failed_attempts": [],
        }

        try:
            # Analizuj istniejące wzorce
            for component in self.config["focus_components"]:
                for metric in self.config["target_metrics"]:
                    # Pobierz najlepsze praktyki
                    best_practices = self.knowledge_manager.get_best_practices(
                        component, metric
                    )
                    phase_result["best_practices"].extend(best_practices)

                    # Pobierz wzorce wydajnościowe
                    performance_patterns = (
                        self.knowledge_manager.get_performance_patterns(component)
                    )
                    phase_result["existing_patterns"].extend(performance_patterns)

                    # Pobierz nieudane próby
                    failed_attempts = self.knowledge_manager.search_knowledge_entries(
                        category=KnowledgeCategory.FAILED_ATTEMPTS,
                        target_component=component,
                    )
                    phase_result["failed_attempts"].extend(failed_attempts)

            phase_result["success"] = True
            phase_result["end_time"] = datetime.now().isoformat()

            print(f"✅ Przeanalizowano bazę wiedzy:")
            print(f"   - {len(phase_result['best_practices'])} najlepszych praktyk")
            print(
                f"   - {len(phase_result['existing_patterns'])} wzorców wydajnościowych"
            )
            print(f"   - {len(phase_result['failed_attempts'])} nieudanych prób")

        except Exception as e:
            print(f"❌ Błąd podczas analizy bazy wiedzy: {e}")
            phase_result["error"] = str(e)
            phase_result["end_time"] = datetime.now().isoformat()

        return phase_result

    def _run_optimization_phase(
        self, baseline_metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """Uruchamia fazę automatycznej optymalizacji"""
        phase_result = {
            "phase": "optimization",
            "start_time": datetime.now().isoformat(),
            "success": False,
            "optimization_results": [],
            "total_improvements": {},
            "best_optimization": None,
        }

        try:
            # Uruchom automatyczny cykl optymalizacji
            test_suite_result = self.test_runner.run_automated_optimization_cycle(
                self.config["target_metrics"]
            )

            if test_suite_result:
                phase_result.update(
                    {
                        "success": True,
                        "optimization_results": test_suite_result.optimization_history,
                        "total_improvements": test_suite_result.improvements,
                        "best_optimization": test_suite_result.best_result,
                        "end_time": datetime.now().isoformat(),
                    }
                )

                print(f"✅ Faza optymalizacji zakończona:")
                print(
                    f"   - {len(test_suite_result.optimization_history)} zastosowanych optymalizacji"
                )
                print(
                    f"   - Najlepsza poprawa: {test_suite_result.total_improvement:.2f}%"
                )

                if test_suite_result.best_result:
                    print(
                        f"   - Najlepsza optymalizacja: {test_suite_result.best_result.target_metric}"
                    )

        except Exception as e:
            print(f"❌ Błąd podczas fazy optymalizacji: {e}")
            phase_result["error"] = str(e)
            phase_result["end_time"] = datetime.now().isoformat()

        return phase_result

    def _run_analysis_phase(
        self, previous_phases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Uruchamia fazę analizy wyników"""
        phase_result = {
            "phase": "analysis",
            "start_time": datetime.now().isoformat(),
            "success": False,
            "final_metrics": {},
            "improvement_summary": {},
            "performance_analysis": {},
        }

        try:
            # Znajdź metryki bazowe i końcowe
            baseline_phase = next(
                (p for p in previous_phases if p["phase"] == "baseline"), None
            )
            optimization_phase = next(
                (p for p in previous_phases if p["phase"] == "optimization"), None
            )

            if baseline_phase and optimization_phase and optimization_phase["success"]:
                baseline_metrics = baseline_phase["baseline_metrics"]

                # Pobierz końcowe metryki (z ostatniego testu)
                final_metrics = self.test_runner.run_baseline_test().metrics

                # Oblicz podsumowanie poprawek
                improvements = {}
                for metric in self.config["target_metrics"]:
                    if metric in baseline_metrics and metric in final_metrics:
                        baseline_val = baseline_metrics[metric]
                        final_val = final_metrics[metric]

                        if baseline_val > 0:
                            if metric in [
                                "scan_time_ms",
                                "gallery_load_time_ms",
                                "tile_creation_time_ms",
                                "memory_usage_mb",
                            ]:
                                improvement = (
                                    (baseline_val - final_val) / baseline_val
                                ) * 100
                            else:
                                improvement = (
                                    (final_val - baseline_val) / baseline_val
                                ) * 100

                            improvements[metric] = improvement

                phase_result.update(
                    {
                        "success": True,
                        "final_metrics": final_metrics,
                        "improvement_summary": improvements,
                        "performance_analysis": self._analyze_performance_improvements(
                            improvements
                        ),
                        "end_time": datetime.now().isoformat(),
                    }
                )

                print(f"✅ Analiza wyników zakończona:")
                for metric, improvement in improvements.items():
                    print(f"   {metric}: {improvement:+.2f}%")

        except Exception as e:
            print(f"❌ Błąd podczas analizy wyników: {e}")
            phase_result["error"] = str(e)
            phase_result["end_time"] = datetime.now().isoformat()

        return phase_result

    def _analyze_performance_improvements(
        self, improvements: Dict[str, float]
    ) -> Dict[str, Any]:
        """Analizuje poprawki wydajnościowe"""
        analysis = {
            "overall_improvement": 0.0,
            "best_improvement": None,
            "worst_improvement": None,
            "improvement_count": 0,
            "degradation_count": 0,
            "significant_improvements": [],
        }

        if not improvements:
            return analysis

        positive_improvements = [imp for imp in improvements.values() if imp > 0]
        negative_improvements = [imp for imp in improvements.values() if imp < 0]

        analysis.update(
            {
                "overall_improvement": sum(improvements.values()) / len(improvements),
                "best_improvement": max(improvements.values()) if improvements else 0,
                "worst_improvement": min(improvements.values()) if improvements else 0,
                "improvement_count": len(positive_improvements),
                "degradation_count": len(negative_improvements),
                "significant_improvements": [
                    metric
                    for metric, imp in improvements.items()
                    if imp > self.config["improvement_threshold"]
                ],
            }
        )

        return analysis

    def _run_knowledge_update_phase(
        self, previous_phases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Uruchamia fazę aktualizacji bazy wiedzy"""
        phase_result = {
            "phase": "knowledge_update",
            "start_time": datetime.now().isoformat(),
            "success": False,
            "new_entries": [],
            "updated_entries": [],
            "knowledge_gained": 0,
        }

        try:
            # Znajdź wyniki optymalizacji
            optimization_phase = next(
                (p for p in previous_phases if p["phase"] == "optimization"), None
            )

            if optimization_phase and optimization_phase["success"]:
                new_entries = []

                # Dodaj nowe wpisy do bazy wiedzy
                for optimization in optimization_phase["optimization_results"]:
                    if optimization and optimization.improvement_percent > 0:
                        # Utwórz wpis wiedzy
                        entry = self._create_knowledge_entry_from_optimization(
                            optimization
                        )

                        if self.knowledge_manager.add_knowledge_entry(entry):
                            new_entries.append(entry.entry_id)

                phase_result.update(
                    {
                        "success": True,
                        "new_entries": new_entries,
                        "knowledge_gained": len(new_entries),
                        "end_time": datetime.now().isoformat(),
                    }
                )

                print(f"✅ Zaktualizowano bazę wiedzy:")
                print(f"   - Dodano {len(new_entries)} nowych wpisów")

        except Exception as e:
            print(f"❌ Błąd podczas aktualizacji bazy wiedzy: {e}")
            phase_result["error"] = str(e)
            phase_result["end_time"] = datetime.now().isoformat()

        return phase_result

    def _create_knowledge_entry_from_optimization(
        self, optimization_result
    ) -> "KnowledgeEntry":
        """Tworzy wpis wiedzy z wyniku optymalizacji"""
        from tests.knowledge_base_manager import (
            EffectivenessLevel,
            KnowledgeCategory,
            KnowledgeEntry,
        )

        # Określ kategorię
        if "cache" in optimization_result.changes_made:
            category = KnowledgeCategory.PERFORMANCE_PATTERNS
        elif "memory" in optimization_result.changes_made:
            category = KnowledgeCategory.MEMORY_OPTIMIZATIONS
        elif "thread" in optimization_result.changes_made:
            category = KnowledgeCategory.THREAD_SAFETY_SOLUTIONS
        else:
            category = KnowledgeCategory.ALGORITHM_IMPROVEMENTS

        # Określ poziom skuteczności
        if optimization_result.improvement_percent > 50:
            effectiveness = EffectivenessLevel.EXCELLENT
        elif optimization_result.improvement_percent > 20:
            effectiveness = EffectivenessLevel.GOOD
        elif optimization_result.improvement_percent > 5:
            effectiveness = EffectivenessLevel.MODERATE
        else:
            effectiveness = EffectivenessLevel.POOR

        # Określ tagi
        tags = []
        if "cache" in optimization_result.changes_made:
            tags.append("cache")
        if "memory" in optimization_result.changes_made:
            tags.append("memory")
        if "performance" in optimization_result.changes_made:
            tags.append("performance")

        return KnowledgeEntry(
            entry_id=f"auto_{optimization_result.revision_id}",
            category=category,
            title=f"Automatyczna optymalizacja: {optimization_result.target_metric}",
            description=f"Automatycznie wygenerowana optymalizacja z poprawą {optimization_result.improvement_percent:.1f}%",
            code_pattern="auto_generated",
            target_component="auto_detected",
            target_metric=optimization_result.target_metric,
            effectiveness_level=effectiveness,
            improvement_percent=optimization_result.improvement_percent,
            success_rate=1.0 if optimization_result.success else 0.0,
            usage_count=1,
            first_used=optimization_result.timestamp,
            last_used=optimization_result.timestamp,
            dependencies=[],
            conflicts=[],
            risk_level="low",
            complexity_score=3,
            maintenance_cost="low",
            tags=tags,
            metadata={
                "auto_generated": True,
                "revision_id": optimization_result.revision_id,
                "execution_time_ms": optimization_result.execution_time_ms,
            },
        )

    def _run_recommendations_phase(
        self, previous_phases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Uruchamia fazę generowania rekomendacji"""
        phase_result = {
            "phase": "recommendations",
            "start_time": datetime.now().isoformat(),
            "success": False,
            "recommendations": [],
            "next_steps": [],
        }

        try:
            # Znajdź analizę wyników
            analysis_phase = next(
                (p for p in previous_phases if p["phase"] == "analysis"), None
            )

            if analysis_phase and analysis_phase["success"]:
                recommendations = []
                next_steps = []

                # Generuj rekomendacje na podstawie wyników
                for component in self.config["focus_components"]:
                    for metric in self.config["target_metrics"]:
                        comp_recommendations = (
                            self.knowledge_manager.generate_recommendations(
                                target_component=component,
                                target_metric=metric,
                                context={"recent_optimization": True},
                            )
                        )
                        recommendations.extend(comp_recommendations)

                # Sortuj po score
                recommendations.sort(key=lambda x: x["score"], reverse=True)

                # Generuj następne kroki
                if analysis_phase["performance_analysis"]["significant_improvements"]:
                    next_steps.append(
                        "Kontynuuj optymalizację zidentyfikowanych obszarów"
                    )

                if analysis_phase["performance_analysis"]["degradation_count"] > 0:
                    next_steps.append(
                        "Przeanalizuj i cofnij optymalizacje które pogorszyły wydajność"
                    )

                if len(recommendations) > 0:
                    next_steps.append(
                        "Przetestuj rekomendowane strategie z bazy wiedzy"
                    )

                phase_result.update(
                    {
                        "success": True,
                        "recommendations": recommendations[:10],  # Top 10
                        "next_steps": next_steps,
                        "end_time": datetime.now().isoformat(),
                    }
                )

                print(f"✅ Wygenerowano rekomendacje:")
                print(f"   - {len(recommendations)} rekomendacji")
                print(f"   - {len(next_steps)} następnych kroków")

        except Exception as e:
            print(f"❌ Błąd podczas generowania rekomendacji: {e}")
            phase_result["error"] = str(e)
            phase_result["end_time"] = datetime.now().isoformat()

        return phase_result

    def _save_session_results(self, results: Dict[str, Any]):
        """Zapisuje wyniki sesji"""
        try:
            session_file = self.results_dir / f"session_{results['session_id']}.json"

            with open(session_file, "w", encoding="utf-8") as f:
                import json

                json.dump(results, f, indent=2, ensure_ascii=False)

            # Wygeneruj raport
            self._generate_session_report(results)

            print(f"💾 Zapisano wyniki sesji: {session_file}")

        except Exception as e:
            print(f"❌ Błąd podczas zapisywania wyników: {e}")

    def _generate_session_report(self, results: Dict[str, Any]):
        """Generuje raport z sesji"""
        try:
            report_file = self.results_dir / f"report_{results['session_id']}.md"

            with open(report_file, "w", encoding="utf-8") as f:
                f.write(
                    f"# Raport Sesji Automatycznej Optymalizacji: {results['session_id']}\n\n"
                )
                f.write(f"**Data rozpoczęcia:** {results['start_time']}\n")
                f.write(f"**Data zakończenia:** {results['end_time']}\n\n")

                f.write("## Konfiguracja\n\n")
                for key, value in results["config"].items():
                    f.write(f"- **{key}:** {value}\n")
                f.write("\n")

                f.write("## Podsumowanie Wyników\n\n")
                if "final_results" in results:
                    f.write("### Końcowe Metryki\n\n")
                    for metric, value in results["final_results"].items():
                        f.write(f"- **{metric}:** {value:.2f}\n")
                    f.write("\n")

                f.write("## Fazy Wykonania\n\n")
                for phase in results["phases"]:
                    f.write(f"### {phase['phase'].replace('_', ' ').title()}\n\n")
                    f.write(f"- **Status:** {'✅' if phase['success'] else '❌'}\n")
                    f.write(
                        f"- **Czas:** {phase['start_time']} - {phase['end_time']}\n"
                    )

                    if "error" in phase:
                        f.write(f"- **Błąd:** {phase['error']}\n")

                    f.write("\n")

                if "recommendations" in results:
                    f.write("## Rekomendacje\n\n")
                    for i, rec in enumerate(results["recommendations"][:5], 1):
                        f.write(
                            f"{i}. **{rec['title']}** (Score: {rec['score']:.2f})\n"
                        )
                        f.write(f"   - {rec['description']}\n")
                        f.write(
                            f"   - Oczekiwana poprawa: {rec['expected_improvement']:.1f}%\n"
                        )
                        f.write(f"   - Ryzyko: {rec['risk_level']}\n\n")

                if "knowledge_gained" in results:
                    f.write("## Zdobyta Wiedza\n\n")
                    f.write(f"- **Nowe wpisy:** {len(results['knowledge_gained'])}\n")
                    for entry_id in results["knowledge_gained"]:
                        f.write(f"  - {entry_id}\n")
                    f.write("\n")

            print(f"📊 Wygenerowano raport: {report_file}")

        except Exception as e:
            print(f"❌ Błąd podczas generowania raportu: {e}")


def main():
    """Główna funkcja uruchamiająca system"""
    parser = argparse.ArgumentParser(description="Automatyczny system optymalizacji")
    parser.add_argument("--config", type=str, help="Plik konfiguracyjny JSON")
    parser.add_argument(
        "--target-metrics",
        nargs="+",
        default=["gallery_load_time_ms", "memory_usage_mb", "scan_time_ms"],
        help="Metryki docelowe",
    )
    parser.add_argument(
        "--components",
        nargs="+",
        default=["GalleryManager", "scanner_core", "file_tile_widget"],
        help="Komponenty do optymalizacji",
    )
    parser.add_argument(
        "--risk-tolerance",
        choices=["low", "medium", "high"],
        default="medium",
        help="Tolerancja ryzyka",
    )
    parser.add_argument(
        "--max-iterations", type=int, default=15, help="Maksymalna liczba iteracji"
    )

    args = parser.parse_args()

    # Konfiguracja
    config = {
        "target_metrics": args.target_metrics,
        "focus_components": args.components,
        "risk_tolerance": args.risk_tolerance,
        "max_iterations": args.max_iterations,
    }

    # Wczytaj konfigurację z pliku jeśli podano
    if args.config:
        import json

        with open(args.config, "r", encoding="utf-8") as f:
            file_config = json.load(f)
            config.update(file_config)

    print("🚀 AUTOMATYCZNY SYSTEM OPTYMALIZACJI")
    print("=" * 50)

    # Uruchom orchestrator
    orchestrator = AutomatedOptimizationOrchestrator()
    results = orchestrator.run_full_optimization_cycle(config)

    # Podsumowanie
    print("\n" + "=" * 50)
    print("📊 PODSUMOWANIE")
    print("=" * 50)

    if "error" in results:
        print(f"❌ Sesja zakończona z błędem: {results['error']}")
    else:
        print(f"✅ Sesja zakończona pomyślnie")
        print(f"📈 Końcowe metryki:")

        if "final_results" in results:
            for metric, value in results["final_results"].items():
                print(f"   {metric}: {value:.2f}")

        print(f"💡 Wygenerowano {len(results.get('recommendations', []))} rekomendacji")
        print(
            f"📚 Zdobyto {len(results.get('knowledge_gained', []))} nowych wpisów wiedzy"
        )

    print(f"\n📁 Wyniki zapisane w: {orchestrator.results_dir}")


if __name__ == "__main__":
    main()
