#!/usr/bin/env python3
"""
TEST RUNNER DLA PAROWANIA PLIKÓW
Specjalizowany runner do testowania i optymalizacji funkcji parowania plików
"""

import json
import os
import shutil
import sys
import time
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
from tests.file_pairing_optimization_strategies import (
    FilePairingOptimizationLibrary,
    FilePairingTestEnvironment,
)


class FilePairingTestRunner:
    """Specjalizowany test runner dla parowania plików"""

    def __init__(self):
        self.project_root = project_root
        self.results_dir = project_root / "file_pairing_test_results"
        self.results_dir.mkdir(exist_ok=True)

        # Komponenty
        self.optimization_library = FilePairingOptimizationLibrary()
        self.test_environment = FilePairingTestEnvironment()
        self.optimization_system = AutomatedOptimizationSystem()

        # Konfiguracja testów
        self.test_scenarios = [
            "small_best_match",  # 50 plików, best_match
            "medium_first_match",  # 300 plików, first_match
            "large_best_match",  # 1000 plików, best_match
        ]

        print("🔧 Inicjalizacja File Pairing Test Runner...")
        print(f"📁 Wyniki będą zapisywane w: {self.results_dir}")

    def run_comprehensive_pairing_tests(self) -> Dict[str, Any]:
        """Uruchamia kompleksowe testy parowania plików"""
        session_id = f"pairing_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        print(f"\n🚀 Rozpoczęcie testów parowania plików: {session_id}")

        results = {
            "session_id": session_id,
            "start_time": datetime.now().isoformat(),
            "test_scenarios": self.test_scenarios,
            "baseline_results": {},
            "optimization_results": [],
            "final_analysis": {},
            "recommendations": [],
        }

        try:
            # FAZA 1: Testy bazowe
            print("\n📊 FAZA 1: Testy bazowe...")
            baseline_results = self._run_baseline_tests()
            results["baseline_results"] = baseline_results

            # FAZA 2: Optymalizacje
            print("\n🔧 FAZA 2: Optymalizacje...")
            optimization_results = self._run_optimization_tests(baseline_results)
            results["optimization_results"] = optimization_results

            # FAZA 3: Analiza wyników
            print("\n📈 FAZA 3: Analiza wyników...")
            final_analysis = self._analyze_optimization_results(
                baseline_results, optimization_results
            )
            results["final_analysis"] = final_analysis

            # FAZA 4: Rekomendacje
            print("\n💡 FAZA 4: Generowanie rekomendacji...")
            recommendations = self._generate_recommendations(results)
            results["recommendations"] = recommendations

            print(f"\n✅ Testy parowania zakończone: {session_id}")

        except Exception as e:
            print(f"❌ Błąd podczas testów: {e}")
            results["error"] = str(e)

        finally:
            results["end_time"] = datetime.now().isoformat()
            self._save_test_results(results)

        return results

    def _run_baseline_tests(self) -> Dict[str, Any]:
        """Uruchamia testy bazowe bez optymalizacji"""
        baseline_results = {}

        for scenario in self.test_scenarios:
            print(f"  🔍 Testowanie scenariusza: {scenario}")

            # Pobierz konfigurację scenariusza
            config = self.test_environment.create_test_scenario(scenario)

            # Uruchom test
            metrics = self.test_environment.measure_pairing_performance(
                config["file_count"], config["pairing_strategy"]
            )

            baseline_results[scenario] = {
                "config": config,
                "metrics": metrics,
                "timestamp": datetime.now().isoformat(),
            }

            print(
                f"    ✅ {scenario}: {metrics['pairs_created']} par w {metrics['pairing_time_ms']:.2f}ms"
            )

        return baseline_results

    def _run_optimization_tests(
        self, baseline_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Uruchamia testy z optymalizacjami"""
        optimization_results = []

        # Przygotuj 2 rewizje kodu
        revisions = self._prepare_code_revisions()

        for i, revision in enumerate(revisions, 1):
            print(f"\n  🔧 Rewizja {i}: {revision['name']}")

            try:
                # Utwórz backup
                backup_path = self.optimization_system.create_backup(f"pairing_rev_{i}")

                # Zastosuj optymalizację
                success = self.optimization_system.apply_optimization(
                    revision["type"], revision["target_file"], revision["changes"]
                )

                if not success:
                    print(f"    ❌ Nie udało się zastosować rewizji {i}")
                    continue

                # Uruchom testy dla każdego scenariusza
                revision_results = {
                    "revision_id": f"rev_{i}",
                    "revision_name": revision["name"],
                    "revision_type": revision["type"],
                    "scenario_results": {},
                    "overall_improvement": 0.0,
                }

                total_improvement = 0.0
                scenario_count = 0

                for scenario in self.test_scenarios:
                    config = baseline_results[scenario]["config"]

                    # Uruchom test z optymalizacją
                    metrics = self.test_environment.measure_pairing_performance(
                        config["file_count"], config["pairing_strategy"]
                    )

                    # Oblicz poprawę
                    baseline_metrics = baseline_results[scenario]["metrics"]
                    improvement = self._calculate_improvement(
                        baseline_metrics["pairing_time_ms"], metrics["pairing_time_ms"]
                    )

                    revision_results["scenario_results"][scenario] = {
                        "metrics": metrics,
                        "improvement_percent": improvement,
                        "baseline_metrics": baseline_metrics,
                    }

                    total_improvement += improvement
                    scenario_count += 1

                if scenario_count > 0:
                    revision_results["overall_improvement"] = (
                        total_improvement / scenario_count
                    )

                optimization_results.append(revision_results)

                print(
                    f"    ✅ Rewizja {i} zakończona: {revision_results['overall_improvement']:.2f}% poprawa"
                )

                # Przywróć backup
                self._restore_backup(backup_path)

            except Exception as e:
                print(f"    ❌ Błąd podczas rewizji {i}: {e}")

                # Przywróć backup w przypadku błędu
                if "backup_path" in locals():
                    self._restore_backup(backup_path)

        return optimization_results

    def _prepare_code_revisions(self) -> List[Dict[str, Any]]:
        """Przygotowuje 2 rewizje kodu do testowania"""
        return [
            {
                "name": "Trie Memory Optimization",
                "type": "memory_optimization",
                "target_file": "src/logic/file_pairing.py",
                "changes": {
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
            },
            {
                "name": "File Info Cache Optimization",
                "type": "cache_optimization",
                "target_file": "src/logic/file_pairing.py",
                "changes": {
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
            },
        ]

    def _calculate_improvement(
        self, baseline_value: float, optimized_value: float
    ) -> float:
        """Oblicza procentową poprawę"""
        if baseline_value <= 0:
            return 0.0

        # Dla metryk czasowych - mniejsze jest lepsze
        improvement = ((baseline_value - optimized_value) / baseline_value) * 100
        return max(improvement, -100.0)  # Ogranicz do -100%

    def _restore_backup(self, backup_path: str):
        """Przywraca kod z backup"""
        try:
            backup_dir = Path(backup_path)
            if backup_dir.exists():
                # Przywróć pliki
                for file_path in backup_dir.rglob("*"):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(backup_dir)
                        target_path = self.project_root / relative_path
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, target_path)

                print(f"    🔄 Przywrócono backup: {backup_path}")
        except Exception as e:
            print(f"    ❌ Błąd podczas przywracania backup: {e}")

    def _analyze_optimization_results(
        self,
        baseline_results: Dict[str, Any],
        optimization_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Analizuje wyniki optymalizacji"""
        analysis = {
            "best_revision": None,
            "average_improvement": 0.0,
            "scenario_analysis": {},
            "recommendations": [],
        }

        if not optimization_results:
            return analysis

        # Znajdź najlepszą rewizję
        best_revision = max(
            optimization_results, key=lambda x: x["overall_improvement"]
        )
        analysis["best_revision"] = {
            "revision_id": best_revision["revision_id"],
            "revision_name": best_revision["revision_name"],
            "improvement": best_revision["overall_improvement"],
        }

        # Oblicz średnią poprawę
        total_improvement = sum(
            rev["overall_improvement"] for rev in optimization_results
        )
        analysis["average_improvement"] = total_improvement / len(optimization_results)

        # Analiza per scenariusz
        for scenario in self.test_scenarios:
            scenario_improvements = []
            for rev in optimization_results:
                if scenario in rev["scenario_results"]:
                    improvement = rev["scenario_results"][scenario][
                        "improvement_percent"
                    ]
                    scenario_improvements.append(improvement)

            if scenario_improvements:
                analysis["scenario_analysis"][scenario] = {
                    "best_improvement": max(scenario_improvements),
                    "average_improvement": sum(scenario_improvements)
                    / len(scenario_improvements),
                    "improvement_count": len(
                        [i for i in scenario_improvements if i > 0]
                    ),
                }

        return analysis

    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generuje rekomendacje na podstawie wyników"""
        recommendations = []

        if "final_analysis" not in results:
            return recommendations

        analysis = results["final_analysis"]

        # Rekomendacje na podstawie najlepszej rewizji
        if analysis.get("best_revision"):
            best_rev = analysis["best_revision"]
            recommendations.append(
                f"Zastosuj rewizję '{best_rev['revision_name']}' - "
                f"poprawa {best_rev['improvement']:.1f}%"
            )

        # Rekomendacje na podstawie średniej poprawy
        avg_improvement = analysis.get("average_improvement", 0)
        if avg_improvement > 20:
            recommendations.append(
                "Optymalizacje wykazały znaczącą poprawę - kontynuuj rozwój"
            )
        elif avg_improvement > 10:
            recommendations.append(
                "Optymalizacje wykazały umiarkowaną poprawę - rozważ dodatkowe strategie"
            )
        else:
            recommendations.append(
                "Optymalizacje wykazały minimalną poprawę - przeanalizuj inne podejścia"
            )

        # Rekomendacje per scenariusz
        for scenario, scenario_analysis in analysis.get(
            "scenario_analysis", {}
        ).items():
            if scenario_analysis["best_improvement"] > 30:
                recommendations.append(
                    f"Scenariusz {scenario} wykazał doskonałą poprawę - "
                    f"rozważ specjalizację dla tego typu danych"
                )

        return recommendations

    def _save_test_results(self, results: Dict[str, Any]):
        """Zapisuje wyniki testów"""
        try:
            # Zapisz główny wynik
            results_file = (
                self.results_dir / f"pairing_test_{results['session_id']}.json"
            )
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            # Wygeneruj raport
            self._generate_test_report(results)

            print(f"💾 Zapisano wyniki testów: {results_file}")

        except Exception as e:
            print(f"❌ Błąd podczas zapisywania wyników: {e}")

    def _generate_test_report(self, results: Dict[str, Any]):
        """Generuje raport z testów"""
        try:
            report_file = (
                self.results_dir / f"pairing_report_{results['session_id']}.md"
            )

            with open(report_file, "w", encoding="utf-8") as f:
                f.write(
                    f"# Raport Testów Parowania Plików: {results['session_id']}\n\n"
                )
                f.write(f"**Data rozpoczęcia:** {results['start_time']}\n")
                f.write(f"**Data zakończenia:** {results['end_time']}\n\n")

                f.write("## Scenariusze Testowe\n\n")
                for scenario in results["test_scenarios"]:
                    f.write(f"- {scenario}\n")
                f.write("\n")

                f.write("## Wyniki Bazowe\n\n")
                for scenario, data in results["baseline_results"].items():
                    metrics = data["metrics"]
                    f.write(f"### {scenario}\n\n")
                    f.write(
                        f"- **Czas parowania:** {metrics['pairing_time_ms']:.2f}ms\n"
                    )
                    f.write(f"- **Utworzone pary:** {metrics['pairs_created']}\n")
                    f.write(f"- **Przetworzone pliki:** {metrics['files_processed']}\n")
                    f.write(f"- **Stosunek par:** {metrics['pair_ratio']:.2f}\n")
                    f.write(
                        f"- **Pary/sekundę:** {metrics['pairs_per_second']:.2f}\n\n"
                    )

                f.write("## Wyniki Optymalizacji\n\n")
                for rev in results["optimization_results"]:
                    f.write(f"### {rev['revision_name']}\n\n")
                    f.write(
                        f"- **Ogólna poprawa:** {rev['overall_improvement']:.2f}%\n\n"
                    )

                    for scenario, scenario_data in rev["scenario_results"].items():
                        f.write(f"#### {scenario}\n")
                        f.write(
                            f"- **Poprawa:** {scenario_data['improvement_percent']:.2f}%\n"
                        )
                        f.write(
                            f"- **Nowy czas:** {scenario_data['metrics']['pairing_time_ms']:.2f}ms\n"
                        )
                        f.write(
                            f"- **Nowe pary/sekundę:** {scenario_data['metrics']['pairs_per_second']:.2f}\n\n"
                        )

                if "final_analysis" in results:
                    f.write("## Analiza Końcowa\n\n")
                    analysis = results["final_analysis"]

                    if analysis.get("best_revision"):
                        best = analysis["best_revision"]
                        f.write(
                            f"**Najlepsza rewizja:** {best['revision_name']} ({best['improvement']:.2f}%)\n\n"
                        )

                    f.write(
                        f"**Średnia poprawa:** {analysis.get('average_improvement', 0):.2f}%\n\n"
                    )

                if "recommendations" in results:
                    f.write("## Rekomendacje\n\n")
                    for i, rec in enumerate(results["recommendations"], 1):
                        f.write(f"{i}. {rec}\n")
                    f.write("\n")

            print(f"📊 Wygenerowano raport: {report_file}")

        except Exception as e:
            print(f"❌ Błąd podczas generowania raportu: {e}")


def main():
    """Główna funkcja uruchamiająca testy parowania"""
    print("🚀 TEST RUNNER DLA PAROWANIA PLIKÓW")
    print("=" * 50)

    # Uruchom testy
    runner = FilePairingTestRunner()
    results = runner.run_comprehensive_pairing_tests()

    # Podsumowanie
    print("\n" + "=" * 50)
    print("📊 PODSUMOWANIE TESTOW PAROWANIA")
    print("=" * 50)

    if "error" in results:
        print(f"❌ Testy zakończone z błędem: {results['error']}")
    else:
        print(f"✅ Testy zakończone pomyślnie")

        # Pokaż najlepszą rewizję
        if "final_analysis" in results and results["final_analysis"].get(
            "best_revision"
        ):
            best = results["final_analysis"]["best_revision"]
            print(f"🏆 Najlepsza rewizja: {best['revision_name']}")
            print(f"📈 Poprawa: {best['improvement']:.2f}%")

        # Pokaż średnią poprawę
        if "final_analysis" in results:
            avg = results["final_analysis"].get("average_improvement", 0)
            print(f"📊 Średnia poprawa: {avg:.2f}%")

        # Pokaż rekomendacje
        if results.get("recommendations"):
            print(f"💡 Rekomendacje: {len(results['recommendations'])}")

    print(f"\n📁 Wyniki zapisane w: {runner.results_dir}")


if __name__ == "__main__":
    main()
