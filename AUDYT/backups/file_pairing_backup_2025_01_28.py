"""
Moduł odpowiedzialny za parowanie plików.

Ten moduł zawiera funkcje do tworzenia par plików (archiwum + podgląd)
oraz identyfikowania niesparowanych plików.
"""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from src import app_config
from src.models.file_pair import FilePair

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Używamy definicji rozszerzeń z centralnego pliku konfiguracyjnego
ARCHIVE_EXTENSIONS = set(app_config.SUPPORTED_ARCHIVE_EXTENSIONS)
PREVIEW_EXTENSIONS = set(app_config.SUPPORTED_PREVIEW_EXTENSIONS)


@dataclass
class FileInfo:
    """Pre-computed file information dla performance optimization."""

    def __init__(self, path: str):
        self.path = path
        self.basename = os.path.basename(path)
        self.name_lower = os.path.splitext(self.basename)[0].lower()
        self.ext_lower = os.path.splitext(path)[1].lower()
        self.is_archive = self.ext_lower in ARCHIVE_EXTENSIONS
        self.is_preview = self.ext_lower in PREVIEW_EXTENSIONS


def _categorize_files_optimized(files_list: List[str]) -> Tuple[List[str], List[str]]:
    """
    Optimized kategoryzacja plików na archiwa i podglądy.
    Pre-computes file info once instead of parsing extensions multiple times.
    """
    if not files_list:
        return [], []

    # Pre-compute file info once - O(n) instead of O(2n)
    file_infos = [FileInfo(f) for f in files_list]

    # Single pass categorization - O(n) instead of O(2n)
    archive_files = [fi.path for fi in file_infos if fi.is_archive]
    preview_files = [fi.path for fi in file_infos if fi.is_preview]

    return archive_files, preview_files


class SimpleTrie:
    """Simple Trie dla fast prefix matching."""

    def __init__(self):
        self.root = {}
        self.files = {}  # Maps prefix -> list of files

    def add(self, key: str, file_path: str):
        """Adds file with its prefix key."""
        node = self.root
        for char in key:
            if char not in node:
                node[char] = {}
            node = node[char]

        if key not in self.files:
            self.files[key] = []
        self.files[key].append(file_path)

    def find_prefix_matches(self, prefix: str, max_results: int = 20) -> List[str]:
        """Finds all keys that match the prefix."""
        matches = []

        # Exact match first (highest priority)
        if prefix in self.files:
            matches.extend(self.files[prefix])

        # Prefix matches
        for key in self.files:
            if len(matches) >= max_results:
                break
            if key != prefix and (key.startswith(prefix) or prefix.startswith(key)):
                matches.extend(self.files[key])

        return matches[:max_results]


class PairingStrategy(ABC):
    """Abstrakcyjna klasa bazowa dla strategii parowania plików."""

    @abstractmethod
    def create_pairs(
        self, archive_files: List[str], preview_files: List[str], base_directory: str
    ) -> Tuple[List[FilePair], Set[str]]:
        """
        Tworzy pary plików według konkretnej strategii.

        Args:
            archive_files: Lista plików archiwów
            preview_files: Lista plików podglądów
            base_directory: Katalog bazowy

        Returns:
            Tuple zawierający listę par i zbiór przetworzonych plików
        """
        pass


class FirstMatchStrategy(PairingStrategy):
    """Strategia parowania pierwszego dopasowania."""

    def create_pairs(
        self, archive_files: List[str], preview_files: List[str], base_directory: str
    ) -> Tuple[List[FilePair], Set[str]]:
        """Tworzy tylko pierwszą parę."""
        pairs = []
        processed = set()

        if archive_files and preview_files:
            try:
                pair = FilePair(archive_files[0], preview_files[0], base_directory)
                pairs.append(pair)
                processed.add(archive_files[0])
                processed.add(preview_files[0])
            except ValueError as e:
                logger.error(
                    f"Błąd tworzenia FilePair dla '{archive_files[0]}' i '{preview_files[0]}': {e}"
                )

        return pairs, processed


# AllCombinationsStrategy REMOVED - dead code (caused exponential memory usage)


class OptimizedBestMatchStrategy(PairingStrategy):
    """Optimized strategia inteligentnego parowania z Trie-based matching."""

    # Simplified preference - tylko extension priority, bez I/O operations
    PREVIEW_PREFERENCE = {
        ".jpg": 60,
        ".jpeg": 55,
        ".png": 50,
        ".gif": 40,
        ".bmp": 30,
        ".tiff": 20,
    }

    def create_pairs(
        self, archive_files: List[str], preview_files: List[str], base_directory: str
    ) -> Tuple[List[FilePair], Set[str]]:
        """Optimized pairing z Trie-based matching."""
        pairs = []
        processed = set()

        if not archive_files or not preview_files:
            return pairs, processed

        # Build optimized Trie index - O(m log m)
        preview_trie = self._build_preview_trie(preview_files)

        # Match archives to previews - O(n log m) instead of O(n*m)
        for archive in archive_files:
            if archive in processed:
                continue

            best_preview = self._find_best_preview_optimized(archive, preview_trie)

            if best_preview and best_preview not in processed:
                try:
                    pair = FilePair(archive, best_preview, base_directory)
                    pairs.append(pair)
                    processed.add(archive)
                    processed.add(best_preview)
                except ValueError as e:
                    logger.warning(
                        f"Skipping invalid pair {archive} + {best_preview}: {e}"
                    )

        return pairs, processed

    def _build_preview_trie(self, preview_files: List[str]) -> SimpleTrie:
        """Builds Trie index dla fast preview lookup."""
        trie = SimpleTrie()

        for preview in preview_files:
            basename = os.path.basename(preview)
            name_lower = os.path.splitext(basename)[0].lower()
            trie.add(name_lower, preview)

        return trie

    def _find_best_preview_optimized(
        self, archive: str, preview_trie: SimpleTrie
    ) -> str:
        """Fast best preview lookup using Trie."""
        archive_basename = os.path.basename(archive)
        archive_name = os.path.splitext(archive_basename)[0].lower()

        # Get candidates using Trie - O(log m) instead of O(m)
        candidates = preview_trie.find_prefix_matches(archive_name, max_results=20)

        if not candidates:
            return None

        # Simple scoring without expensive I/O operations
        best_preview = None
        best_score = -1

        for preview in candidates:
            score = self._calculate_simple_score(preview, archive_name)
            if score > best_score:
                best_score = score
                best_preview = preview

        return best_preview if best_score > 0 else None

    def _calculate_simple_score(self, preview: str, archive_name: str) -> int:
        """Simplified scoring bez I/O operations."""
        preview_basename = os.path.basename(preview)
        preview_name = os.path.splitext(preview_basename)[0].lower()
        preview_ext = os.path.splitext(preview)[1].lower()

        # Base score from name matching
        if preview_name == archive_name:
            score = 1000  # Perfect match
        elif preview_name.startswith(archive_name) or archive_name.startswith(
            preview_name
        ):
            score = 500  # Partial match
        else:
            score = 100  # Fallback

        # Extension preference bonus
        if preview_ext in self.PREVIEW_PREFERENCE:
            score += self.PREVIEW_PREFERENCE[preview_ext]

        return score


class OptimizedPairingStrategyFactory:
    """Simplified factory bez dead code."""

    _strategies = {
        "first_match": FirstMatchStrategy,
        "best_match": OptimizedBestMatchStrategy,  # Use optimized version
        # "all_combinations": REMOVED - dead code
    }

    @classmethod
    def get_strategy(cls, strategy_name: str) -> PairingStrategy:
        """
        Returns strategy instance z validation.

        Args:
            strategy_name: Strategy name ("first_match" or "best_match")

        Returns:
            Strategy instance

        Raises:
            ValueError: If strategy doesn't exist
        """
        if not strategy_name or strategy_name not in cls._strategies:
            logger.warning(
                f"Unknown strategy '{strategy_name}', using 'first_match' as fallback"
            )
            strategy_name = "first_match"

        return cls._strategies[strategy_name]()

    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Returns list of available strategy names."""
        return list(cls._strategies.keys())


def _categorize_files(files_list: List[str]) -> Tuple[List[str], List[str]]:
    """
    Kategoryzuje pliki na archiwa i podglądy.

    Args:
        files_list: Lista plików do kategoryzacji

    Returns:
        Tuple zawierający listy archiwów i podglądów
    """
    # Pre-compute rozszerzeń dla optymalizacji
    files_with_ext = [(f, os.path.splitext(f)[1].lower()) for f in files_list]

    archive_files = [f for f, ext in files_with_ext if ext in ARCHIVE_EXTENSIONS]
    preview_files = [f for f, ext in files_with_ext if ext in PREVIEW_EXTENSIONS]

    return archive_files, preview_files


def create_file_pairs(
    file_map: Dict[str, List[str]],
    base_directory: str,
    pair_strategy: str = "first_match",
) -> Tuple[List[FilePair], Set[str]]:
    """
    Tworzy pary plików na podstawie zebranych danych.

    REFAKTORYZACJA: Funkcja została uproszczona poprzez wydzielenie strategii parowania.

    Args:
        file_map: Słownik zmapowanych plików
        base_directory: Katalog bazowy dla względnych ścieżek w FilePair
        pair_strategy: Strategia parowania plików.

    Returns:
        Krotka zawierająca listę utworzonych par oraz zbiór przetworzonych plików
    """
    found_pairs: List[FilePair] = []
    processed_files: Set[str] = set()

    # Pobierz strategię parowania
    try:
        strategy = OptimizedPairingStrategyFactory.get_strategy(pair_strategy)
    except ValueError as e:
        logger.error(str(e))
        return found_pairs, processed_files

    for base_path, files_list in file_map.items():
        # Kategoryzuj pliki na archiwa i podglądy - używaj optimized version
        archive_files, preview_files = _categorize_files_optimized(files_list)

        if not archive_files or not preview_files:
            continue

        # Użyj strategii do utworzenia par
        pairs, processed = strategy.create_pairs(
            archive_files, preview_files, base_directory
        )

        found_pairs.extend(pairs)
        processed_files.update(processed)

    return found_pairs, processed_files


def identify_unpaired_files(
    file_map: Dict[str, List[str]],
    processed_files: Set[str],
) -> Tuple[List[str], List[str]]:
    """
    Memory-efficient identification of unpaired files.
    Uses streaming approach instead of large set operations.
    """
    if not file_map:
        return [], []

    unpaired_archives: List[str] = []
    unpaired_previews: List[str] = []

    # Stream processing instead of creating large intermediate sets
    for files_list in file_map.values():
        for file_path in files_list:
            if file_path in processed_files:
                continue

            # Process file without creating intermediate objects
            ext_lower = os.path.splitext(file_path)[1].lower()

            if ext_lower in ARCHIVE_EXTENSIONS:
                unpaired_archives.append(file_path)
            elif ext_lower in PREVIEW_EXTENSIONS:
                unpaired_previews.append(file_path)

    # Sort efficiently with key function
    unpaired_archives.sort(key=lambda x: os.path.basename(x).lower())
    unpaired_previews.sort(key=lambda x: os.path.basename(x).lower())

    return unpaired_archives, unpaired_previews
