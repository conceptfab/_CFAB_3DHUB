#!/usr/bin/env python3
"""
MENEDŻER BAZY WIEDZY
System do przechowywania, analizy i wykorzystywania sprawdzonych rozwiązań optymalizacji
"""

import hashlib
import json
import logging
import os
import sqlite3
import statistics
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class KnowledgeCategory(Enum):
    """Kategorie wiedzy"""

    PERFORMANCE_PATTERNS = "performance_patterns"
    MEMORY_OPTIMIZATIONS = "memory_optimizations"
    THREAD_SAFETY_SOLUTIONS = "thread_safety_solutions"
    ALGORITHM_IMPROVEMENTS = "algorithm_improvements"
    FAILED_ATTEMPTS = "failed_attempts"
    BEST_PRACTICES = "best_practices"
    CODE_PATTERNS = "code_patterns"


class EffectivenessLevel(Enum):
    """Poziomy skuteczności"""

    EXCELLENT = "excellent"  # >50% poprawa
    GOOD = "good"  # 20-50% poprawa
    MODERATE = "moderate"  # 5-20% poprawa
    POOR = "poor"  # <5% poprawa
    NEGATIVE = "negative"  # pogorszenie


@dataclass
class KnowledgeEntry:
    """Wpis w bazie wiedzy"""

    entry_id: str
    category: KnowledgeCategory
    title: str
    description: str
    code_pattern: str
    target_component: str
    target_metric: str
    effectiveness_level: EffectivenessLevel
    improvement_percent: float
    success_rate: float  # 0.0-1.0
    usage_count: int
    first_used: str
    last_used: str
    dependencies: List[str]
    conflicts: List[str]
    risk_level: str
    complexity_score: int  # 1-10
    maintenance_cost: str  # low, medium, high
    tags: List[str]
    metadata: Dict[str, Any]


@dataclass
class OptimizationPattern:
    """Wzorzec optymalizacji"""

    pattern_id: str
    name: str
    description: str
    code_template: str
    parameters: Dict[str, Any]
    conditions: List[str]
    expected_improvement: float
    risk_factors: List[str]
    alternatives: List[str]


class KnowledgeBaseManager:
    """Menedżer bazy wiedzy"""

    def __init__(self, knowledge_base_path: Optional[Path] = None):
        self.project_root = project_root

        if knowledge_base_path:
            self.knowledge_base_path = knowledge_base_path
        else:
            self.knowledge_base_path = (
                project_root / "optimization_history" / "knowledge_base"
            )

        self.knowledge_base_path.mkdir(parents=True, exist_ok=True)

        # Logger - musi być przed _init_database()
        self._setup_logging()

        # Baza danych SQLite
        self.db_path = self.knowledge_base_path / "knowledge_base.db"
        self._init_database()

        # Cache
        self._pattern_cache = {}
        self._entry_cache = {}

    def _setup_logging(self):
        """Konfiguruje system logowania"""
        log_file = self.knowledge_base_path / "knowledge_base.log"

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
        )

        self.logger = logging.getLogger("KnowledgeBaseManager")

    def _init_database(self):
        """Inicjalizuje bazę danych SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabela wpisów wiedzy
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_entries (
                entry_id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                code_pattern TEXT,
                target_component TEXT,
                target_metric TEXT,
                effectiveness_level TEXT,
                improvement_percent REAL,
                success_rate REAL,
                usage_count INTEGER DEFAULT 0,
                first_used TEXT,
                last_used TEXT,
                dependencies TEXT,
                conflicts TEXT,
                risk_level TEXT,
                complexity_score INTEGER,
                maintenance_cost TEXT,
                tags TEXT,
                metadata TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """
        )

        # Tabela wzorców optymalizacji
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS optimization_patterns (
                pattern_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                code_template TEXT,
                parameters TEXT,
                conditions TEXT,
                expected_improvement REAL,
                risk_factors TEXT,
                alternatives TEXT,
                usage_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            )
        """
        )

        # Tabela historii użycia
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT,
                pattern_id TEXT,
                timestamp TEXT,
                context TEXT,
                result TEXT,
                improvement_percent REAL,
                execution_time_ms REAL,
                FOREIGN KEY (entry_id) REFERENCES knowledge_entries (entry_id),
                FOREIGN KEY (pattern_id) REFERENCES optimization_patterns (pattern_id)
            )
        """
        )

        # Indeksy
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_category ON knowledge_entries (category)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_target_component ON knowledge_entries (target_component)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_effectiveness ON knowledge_entries (effectiveness_level)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_usage_count ON knowledge_entries (usage_count)"
        )

        conn.commit()
        conn.close()

        self.logger.info(f"📊 Zainicjalizowano bazę danych: {self.db_path}")

    def add_knowledge_entry(self, entry: KnowledgeEntry) -> bool:
        """Dodaje wpis do bazy wiedzy"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO knowledge_entries (
                    entry_id, category, title, description, code_pattern,
                    target_component, target_metric, effectiveness_level,
                    improvement_percent, success_rate, usage_count,
                    first_used, last_used, dependencies, conflicts,
                    risk_level, complexity_score, maintenance_cost,
                    tags, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    entry.entry_id,
                    entry.category.value,
                    entry.title,
                    entry.description,
                    entry.code_pattern,
                    entry.target_component,
                    entry.target_metric,
                    entry.effectiveness_level.value,
                    entry.improvement_percent,
                    entry.success_rate,
                    entry.usage_count,
                    entry.first_used,
                    entry.last_used,
                    json.dumps(entry.dependencies),
                    json.dumps(entry.conflicts),
                    entry.risk_level,
                    entry.complexity_score,
                    entry.maintenance_cost,
                    json.dumps(entry.tags),
                    json.dumps(entry.metadata),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )

            conn.commit()
            conn.close()

            # Aktualizuj cache
            self._entry_cache[entry.entry_id] = entry

            self.logger.info(f"📚 Dodano wpis do bazy wiedzy: {entry.entry_id}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas dodawania wpisu: {e}")
            return False

    def get_knowledge_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Pobiera wpis z bazy wiedzy"""
        # Sprawdź cache
        if entry_id in self._entry_cache:
            return self._entry_cache[entry_id]

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM knowledge_entries WHERE entry_id = ?", (entry_id,)
            )
            row = cursor.fetchone()

            conn.close()

            if row:
                entry = self._row_to_knowledge_entry(row)
                self._entry_cache[entry_id] = entry
                return entry

            return None

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas pobierania wpisu: {e}")
            return None

    def _row_to_knowledge_entry(self, row: Tuple) -> KnowledgeEntry:
        """Konwertuje wiersz z bazy na obiekt KnowledgeEntry"""
        return KnowledgeEntry(
            entry_id=row[0],
            category=KnowledgeCategory(row[1]),
            title=row[2],
            description=row[3],
            code_pattern=row[4],
            target_component=row[5],
            target_metric=row[6],
            effectiveness_level=EffectivenessLevel(row[7]),
            improvement_percent=row[8],
            success_rate=row[9],
            usage_count=row[10],
            first_used=row[11],
            last_used=row[12],
            dependencies=json.loads(row[13]) if row[13] else [],
            conflicts=json.loads(row[14]) if row[14] else [],
            risk_level=row[15],
            complexity_score=row[16],
            maintenance_cost=row[17],
            tags=json.loads(row[18]) if row[18] else [],
            metadata=json.loads(row[19]) if row[19] else {},
        )

    def search_knowledge_entries(
        self,
        category: Optional[KnowledgeCategory] = None,
        target_component: Optional[str] = None,
        target_metric: Optional[str] = None,
        min_improvement: Optional[float] = None,
        effectiveness_level: Optional[EffectivenessLevel] = None,
        tags: Optional[List[str]] = None,
    ) -> List[KnowledgeEntry]:
        """Wyszukuje wpisy w bazie wiedzy"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = "SELECT * FROM knowledge_entries WHERE 1=1"
            params = []

            if category:
                query += " AND category = ?"
                params.append(category.value)

            if target_component:
                query += " AND target_component = ?"
                params.append(target_component)

            if target_metric:
                query += " AND target_metric = ?"
                params.append(target_metric)

            if min_improvement is not None:
                query += " AND improvement_percent >= ?"
                params.append(min_improvement)

            if effectiveness_level:
                query += " AND effectiveness_level = ?"
                params.append(effectiveness_level.value)

            if tags:
                # Wyszukiwanie po tagach (JSON array)
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append("tags LIKE ?")
                    params.append(f'%"{tag}"%')
                query += f" AND ({' OR '.join(tag_conditions)})"

            query += " ORDER BY improvement_percent DESC, usage_count DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            conn.close()

            entries = [self._row_to_knowledge_entry(row) for row in rows]

            self.logger.info(f"🔍 Znaleziono {len(entries)} wpisów w bazie wiedzy")
            return entries

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas wyszukiwania: {e}")
            return []

    def get_best_practices(
        self, target_component: str, target_metric: str
    ) -> List[KnowledgeEntry]:
        """Pobiera najlepsze praktyki dla danego komponentu i metryki"""
        return self.search_knowledge_entries(
            category=KnowledgeCategory.BEST_PRACTICES,
            target_component=target_component,
            target_metric=target_metric,
            min_improvement=10.0,  # Minimum 10% poprawa
            effectiveness_level=EffectivenessLevel.GOOD,
        )

    def get_performance_patterns(self, target_component: str) -> List[KnowledgeEntry]:
        """Pobiera wzorce wydajnościowe dla danego komponentu"""
        return self.search_knowledge_entries(
            category=KnowledgeCategory.PERFORMANCE_PATTERNS,
            target_component=target_component,
            min_improvement=15.0,
        )

    def get_memory_optimizations(self, target_component: str) -> List[KnowledgeEntry]:
        """Pobiera optymalizacje pamięci dla danego komponentu"""
        return self.search_knowledge_entries(
            category=KnowledgeCategory.MEMORY_OPTIMIZATIONS,
            target_component=target_component,
            min_improvement=10.0,
        )

    def record_usage(self, entry_id: str, context: str, result: Dict[str, Any]) -> bool:
        """Rejestruje użycie wpisu z bazy wiedzy"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Dodaj do historii użycia
            cursor.execute(
                """
                INSERT INTO usage_history (
                    entry_id, timestamp, context, result, improvement_percent, execution_time_ms
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    entry_id,
                    datetime.now().isoformat(),
                    context,
                    json.dumps(result),
                    result.get("improvement_percent", 0.0),
                    result.get("execution_time_ms", 0.0),
                ),
            )

            # Aktualizuj statystyki wpisu
            cursor.execute(
                """
                UPDATE knowledge_entries 
                SET usage_count = usage_count + 1,
                    last_used = ?,
                    updated_at = ?
                WHERE entry_id = ?
            """,
                (datetime.now().isoformat(), datetime.now().isoformat(), entry_id),
            )

            conn.commit()
            conn.close()

            self.logger.info(f"📝 Zarejestrowano użycie: {entry_id}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas rejestrowania użycia: {e}")
            return False

    def analyze_effectiveness(self, entry_id: str) -> Dict[str, Any]:
        """Analizuje skuteczność wpisu na podstawie historii użycia"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Pobierz historię użycia
            cursor.execute(
                """
                SELECT improvement_percent, execution_time_ms, result
                FROM usage_history 
                WHERE entry_id = ?
                ORDER BY timestamp DESC
            """,
                (entry_id,),
            )

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return {"error": "Brak historii użycia"}

            improvements = [row[0] for row in rows if row[0] is not None]
            execution_times = [row[1] for row in rows if row[1] is not None]

            analysis = {
                "total_uses": len(rows),
                "average_improvement": (
                    statistics.mean(improvements) if improvements else 0.0
                ),
                "median_improvement": (
                    statistics.median(improvements) if improvements else 0.0
                ),
                "min_improvement": min(improvements) if improvements else 0.0,
                "max_improvement": max(improvements) if improvements else 0.0,
                "improvement_std": (
                    statistics.stdev(improvements) if len(improvements) > 1 else 0.0
                ),
                "average_execution_time": (
                    statistics.mean(execution_times) if execution_times else 0.0
                ),
                "success_rate": (
                    len([i for i in improvements if i > 0]) / len(improvements)
                    if improvements
                    else 0.0
                ),
                "recent_trend": (
                    self._calculate_trend(improvements[-10:])
                    if len(improvements) >= 10
                    else "insufficient_data"
                ),
            }

            return analysis

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas analizy skuteczności: {e}")
            return {"error": str(e)}

    def _calculate_trend(self, values: List[float]) -> str:
        """Oblicza trend na podstawie ostatnich wartości"""
        if len(values) < 2:
            return "insufficient_data"

        # Prosta analiza trendu
        first_half = values[: len(values) // 2]
        second_half = values[len(values) // 2 :]

        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)

        if second_avg > first_avg * 1.1:
            return "improving"
        elif second_avg < first_avg * 0.9:
            return "declining"
        else:
            return "stable"

    def generate_recommendations(
        self, target_component: str, target_metric: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generuje rekomendacje na podstawie bazy wiedzy"""
        recommendations = []

        try:
            # Pobierz odpowiednie wpisy
            entries = self.search_knowledge_entries(
                target_component=target_component,
                target_metric=target_metric,
                min_improvement=5.0,
            )

            for entry in entries:
                # Oblicz score rekomendacji
                score = self._calculate_recommendation_score(entry, context)

                if score > 0.5:  # Minimum 50% score
                    recommendation = {
                        "entry_id": entry.entry_id,
                        "title": entry.title,
                        "description": entry.description,
                        "score": score,
                        "expected_improvement": entry.improvement_percent,
                        "risk_level": entry.risk_level,
                        "complexity_score": entry.complexity_score,
                        "success_rate": entry.success_rate,
                        "usage_count": entry.usage_count,
                        "tags": entry.tags,
                        "reasoning": self._generate_reasoning(entry, context),
                    }

                    recommendations.append(recommendation)

            # Sortuj po score (malejąco)
            recommendations.sort(key=lambda x: x["score"], reverse=True)

            self.logger.info(f"💡 Wygenerowano {len(recommendations)} rekomendacji")
            return recommendations

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas generowania rekomendacji: {e}")
            return []

    def _calculate_recommendation_score(
        self, entry: KnowledgeEntry, context: Dict[str, Any]
    ) -> float:
        """Oblicza score rekomendacji (0.0-1.0)"""
        score = 0.0

        # Podstawowy score na podstawie skuteczności
        if entry.effectiveness_level == EffectivenessLevel.EXCELLENT:
            score += 0.4
        elif entry.effectiveness_level == EffectivenessLevel.GOOD:
            score += 0.3
        elif entry.effectiveness_level == EffectivenessLevel.MODERATE:
            score += 0.2
        else:
            score += 0.1

        # Bonus za wysoką skuteczność
        if entry.improvement_percent > 30:
            score += 0.2
        elif entry.improvement_percent > 15:
            score += 0.1

        # Bonus za wysoką stopę sukcesu
        if entry.success_rate > 0.8:
            score += 0.15
        elif entry.success_rate > 0.6:
            score += 0.1

        # Bonus za częste użycie (sprawdzone rozwiązanie)
        if entry.usage_count > 10:
            score += 0.1
        elif entry.usage_count > 5:
            score += 0.05

        # Bonus za niskie ryzyko
        if entry.risk_level == "low":
            score += 0.1
        elif entry.risk_level == "medium":
            score += 0.05

        # Bonus za niską złożoność
        if entry.complexity_score <= 3:
            score += 0.1
        elif entry.complexity_score <= 5:
            score += 0.05

        # Sprawdź kontekst
        if "performance_critical" in context and "performance" in entry.tags:
            score += 0.1

        if "memory_constrained" in context and "memory" in entry.tags:
            score += 0.1

        return min(score, 1.0)

    def _generate_reasoning(
        self, entry: KnowledgeEntry, context: Dict[str, Any]
    ) -> str:
        """Generuje uzasadnienie rekomendacji"""
        reasons = []

        if entry.improvement_percent > 20:
            reasons.append(
                f"Wysoka skuteczność ({entry.improvement_percent:.1f}% poprawa)"
            )

        if entry.success_rate > 0.8:
            reasons.append(f"Wysoka stopa sukcesu ({entry.success_rate*100:.1f}%)")

        if entry.usage_count > 5:
            reasons.append(f"Sprawdzone rozwiązanie (użyte {entry.usage_count} razy)")

        if entry.risk_level == "low":
            reasons.append("Niskie ryzyko implementacji")

        if entry.complexity_score <= 3:
            reasons.append("Prosta implementacja")

        if "performance" in entry.tags and "performance_critical" in context:
            reasons.append("Dopasowane do krytycznych wymagań wydajnościowych")

        if "memory" in entry.tags and "memory_constrained" in context:
            reasons.append("Optymalizacja pamięci zgodna z ograniczeniami")

        return "; ".join(reasons) if reasons else "Ogólna rekomendacja"

    def export_knowledge_base(self, format: str = "json") -> str:
        """Eksportuje bazę wiedzy"""
        try:
            if format == "json":
                return self._export_to_json()
            elif format == "markdown":
                return self._export_to_markdown()
            else:
                raise ValueError(f"Nieobsługiwany format: {format}")

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas eksportu: {e}")
            return ""

    def _export_to_json(self) -> str:
        """Eksportuje bazę wiedzy do JSON"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM knowledge_entries ORDER BY improvement_percent DESC"
        )
        rows = cursor.fetchall()

        entries = []
        for row in rows:
            entry = self._row_to_knowledge_entry(row)
            entries.append(asdict(entry))

        conn.close()

        export_file = (
            self.knowledge_base_path
            / f"knowledge_base_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(export_file, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)

        return str(export_file)

    def _export_to_markdown(self) -> str:
        """Eksportuje bazę wiedzy do Markdown"""
        entries = self.search_knowledge_entries()

        export_file = (
            self.knowledge_base_path
            / f"knowledge_base_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )

        with open(export_file, "w", encoding="utf-8") as f:
            f.write("# Baza Wiedzy - Optymalizacje\n\n")
            f.write(f"**Data eksportu:** {datetime.now().isoformat()}\n")
            f.write(f"**Liczba wpisów:** {len(entries)}\n\n")

            # Grupuj według kategorii
            categories = {}
            for entry in entries:
                if entry.category not in categories:
                    categories[entry.category] = []
                categories[entry.category].append(entry)

            for category, category_entries in categories.items():
                f.write(f"## {category.value.replace('_', ' ').title()}\n\n")

                for entry in category_entries:
                    f.write(f"### {entry.title}\n\n")
                    f.write(f"**ID:** {entry.entry_id}\n")
                    f.write(f"**Komponent:** {entry.target_component}\n")
                    f.write(f"**Metryka:** {entry.target_metric}\n")
                    f.write(f"**Poprawa:** {entry.improvement_percent:.1f}%\n")
                    f.write(f"**Skuteczność:** {entry.effectiveness_level.value}\n")
                    f.write(f"**Ryzyko:** {entry.risk_level}\n")
                    f.write(f"**Użycia:** {entry.usage_count}\n")
                    f.write(f"**Stopa sukcesu:** {entry.success_rate*100:.1f}%\n\n")

                    f.write(f"**Opis:** {entry.description}\n\n")

                    if entry.tags:
                        f.write(f"**Tagi:** {', '.join(entry.tags)}\n\n")

                    if entry.dependencies:
                        f.write(f"**Zależności:** {', '.join(entry.dependencies)}\n\n")

                    f.write("---\n\n")

        return str(export_file)


def main():
    """Przykład użycia menedżera bazy wiedzy"""
    manager = KnowledgeBaseManager()

    # Przykładowy wpis
    entry = KnowledgeEntry(
        entry_id="cache_optimization_gallery",
        category=KnowledgeCategory.PERFORMANCE_PATTERNS,
        title="Cache dla obliczeń geometrii galerii",
        description="Implementacja cache dla obliczeń layoutu galerii z TTL 30s",
        code_pattern="cache = {}; cache[key] = calculation()",
        target_component="GalleryManager",
        target_metric="gallery_load_time_ms",
        effectiveness_level=EffectivenessLevel.GOOD,
        improvement_percent=25.5,
        success_rate=0.85,
        usage_count=3,
        first_used="2025-01-28T10:00:00",
        last_used="2025-01-28T15:30:00",
        dependencies=["threading"],
        conflicts=["memory_optimization"],
        risk_level="low",
        complexity_score=3,
        maintenance_cost="low",
        tags=["cache", "performance", "geometry"],
        metadata={"cache_size": 100, "ttl_seconds": 30},
    )

    # Dodaj wpis
    success = manager.add_knowledge_entry(entry)
    print(f"Dodano wpis: {success}")

    # Wyszukaj wpisy
    entries = manager.search_knowledge_entries(
        target_component="GalleryManager", min_improvement=20.0
    )
    print(f"Znaleziono {len(entries)} wpisów")

    # Generuj rekomendacje
    recommendations = manager.generate_recommendations(
        target_component="GalleryManager",
        target_metric="gallery_load_time_ms",
        context={"performance_critical": True},
    )
    print(f"Wygenerowano {len(recommendations)} rekomendacji")

    # Eksportuj bazę wiedzy
    export_file = manager.export_knowledge_base("markdown")
    print(f"Eksport: {export_file}")


if __name__ == "__main__":
    main()
