"""
Moduł odpowiedzialny za parowanie plików.

Ten moduł zawiera funkcje do tworzenia par plików (archiwum + podgląd)
oraz identyfikowania niesparowanych plików.
"""

import logging
import os
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from src import app_config
from src.models.file_pair import FilePair

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Używamy definicji rozszerzeń z centralnego pliku konfiguracyjnego
ARCHIVE_EXTENSIONS = set(app_config.SUPPORTED_ARCHIVE_EXTENSIONS)
PREVIEW_EXTENSIONS = set(app_config.SUPPORTED_PREVIEW_EXTENSIONS)


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


class AllCombinationsStrategy(PairingStrategy):
    """Strategia parowania wszystkich kombinacji."""

    def create_pairs(
        self, archive_files: List[str], preview_files: List[str], base_directory: str
    ) -> Tuple[List[FilePair], Set[str]]:
        """Tworzy wszystkie możliwe kombinacje."""
        pairs = []
        processed = set()

        for archive in archive_files:
            for preview in preview_files:
                try:
                    pair = FilePair(archive, preview, base_directory)
                    pairs.append(pair)
                    processed.add(archive)
                    processed.add(preview)
                except ValueError as e:
                    logger.error(
                        f"Błąd tworzenia FilePair dla '{archive}' i '{preview}': {e}"
                    )

        return pairs, processed


class BestMatchStrategy(PairingStrategy):
    """Strategia inteligentnego parowania według nazw."""

    # Preferowane rozszerzenia podglądu (od najbardziej preferowanego)
    PREVIEW_PREFERENCE = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]

    def create_pairs(
        self, archive_files: List[str], preview_files: List[str], base_directory: str
    ) -> Tuple[List[FilePair], Set[str]]:
        """Inteligentne parowanie z oceną dopasowania."""
        pairs = []
        processed = set()

        # Budujemy hash mapę podglądów według nazw bazowych - O(m)
        preview_map = self._build_preview_map(preview_files)

        # Dla każdego archiwum szukamy najlepszego podglądu - O(n)
        for archive in archive_files:
            best_preview = self._find_best_preview(archive, preview_map)

            if best_preview:
                try:
                    pair = FilePair(archive, best_preview, base_directory)
                    pairs.append(pair)
                    processed.add(archive)
                    processed.add(best_preview)
                except ValueError as e:
                    logger.error(
                        f"Błąd tworzenia FilePair dla '{archive}' i '{best_preview}': {e}"
                    )

        return pairs, processed

    def _build_preview_map(self, preview_files: List[str]) -> Dict[str, List[str]]:
        """Buduje mapę podglądów według nazw bazowych."""
        preview_map = defaultdict(list)
        for preview in preview_files:
            preview_name = os.path.basename(preview)
            preview_base_name = os.path.splitext(preview_name)[0].lower()
            preview_map[preview_base_name].append(preview)
        return preview_map

    def _find_best_preview(
        self, archive: str, preview_map: Dict[str, List[str]]
    ) -> str:
        """Znajduje najlepszy podgląd dla archiwum."""
        archive_name = os.path.basename(archive)
        archive_base_name = os.path.splitext(archive_name)[0].lower()

        candidates = self._get_preview_candidates(archive_base_name, preview_map)

        if not candidates:
            return None

        # Znajdź kandydata z najwyższą oceną
        best_preview = None
        best_score = -1

        for preview, base_score in candidates:
            score = self._calculate_preview_score(preview, base_score)
            if score > best_score:
                best_score = score
                best_preview = preview

        return best_preview if best_score > 0 else None

    def _get_preview_candidates(
        self, archive_base_name: str, preview_map: Dict[str, List[str]]
    ) -> List[Tuple[str, int]]:
        """Pobiera kandydatów na podglądy z oceną bazową."""
        candidates = []

        # 1. Dokładna zgodność nazwy (najlepsze dopasowanie)
        if archive_base_name in preview_map:
            candidates.extend([(p, 1000) for p in preview_map[archive_base_name]])
        else:
            # 2. Częściowa zgodność - OPTYMALIZACJA: tylko gdy nie ma dokładnego dopasowania
            matching_keys = self._find_partial_matches(
                archive_base_name, preview_map.keys()
            )
            for preview_base_name in matching_keys[:20]:  # Limit do 20 najdłuższych
                candidates.extend([(p, 500) for p in preview_map[preview_base_name]])

        return candidates

    def _find_partial_matches(self, archive_base_name: str, preview_keys) -> List[str]:
        """Znajduje częściowe dopasowania nazw."""
        matching_keys = []
        for preview_base_name in preview_keys:
            if preview_base_name.startswith(
                archive_base_name
            ) or archive_base_name.startswith(preview_base_name):
                matching_keys.append(preview_base_name)

        # Sortowanie po długości (zaczynając od najdłuższych)
        matching_keys.sort(key=len, reverse=True)
        return matching_keys

    def _calculate_preview_score(self, preview: str, base_score: int) -> int:
        """Oblicza końcową ocenę podglądu."""
        score = base_score
        preview_ext = os.path.splitext(preview)[1].lower()

        # Dodajemy punkty za preferowane rozszerzenie
        if preview_ext in self.PREVIEW_PREFERENCE:
            score += (
                len(self.PREVIEW_PREFERENCE)
                - self.PREVIEW_PREFERENCE.index(preview_ext)
            ) * 10

        # Dodajemy mały bonus za nowsze pliki
        try:
            mtime = os.path.getmtime(preview)
            score += mtime / 10000000  # Dodaje mały ułamek do punktacji
        except (OSError, PermissionError):
            pass  # Ignorujemy błędy przy sprawdzaniu czasu modyfikacji

        return score


class PairingStrategyFactory:
    """Fabryka strategii parowania."""

    _strategies = {
        "first_match": FirstMatchStrategy,
        "all_combinations": AllCombinationsStrategy,
        "best_match": BestMatchStrategy,
    }

    @classmethod
    def get_strategy(cls, strategy_name: str) -> PairingStrategy:
        """
        Zwraca instancję strategii parowania.

        Args:
            strategy_name: Nazwa strategii

        Returns:
            Instancja strategii parowania

        Raises:
            ValueError: Jeśli strategia nie istnieje
        """
        if strategy_name not in cls._strategies:
            raise ValueError(f"Nieznana strategia parowania: {strategy_name}")

        return cls._strategies[strategy_name]()


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
        strategy = PairingStrategyFactory.get_strategy(pair_strategy)
    except ValueError as e:
        logger.error(str(e))
        return found_pairs, processed_files

    for base_path, files_list in file_map.items():
        # Kategoryzuj pliki na archiwa i podglądy
        archive_files, preview_files = _categorize_files(files_list)

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
    Identyfikuje niesparowane pliki na podstawie zebranych danych.

    Args:
        file_map: Słownik zmapowanych plików
        processed_files: Zbiór już przetworzonych (sparowanych) plików

    Returns:
        Krotka zawierająca listy niesparowanych archiwów i podglądów
    """
    unpaired_archives: List[str] = []
    unpaired_previews: List[str] = []

    # Zbieramy wszystkie pliki z mapy
    all_files = {file for files_list in file_map.values() for file in files_list}

    # Identyfikujemy niesparowane pliki
    unpaired_files = all_files - processed_files
    for f in unpaired_files:
        if os.path.splitext(f)[1].lower() in ARCHIVE_EXTENSIONS:
            unpaired_archives.append(f)
        elif os.path.splitext(f)[1].lower() in PREVIEW_EXTENSIONS:
            unpaired_previews.append(f)

    unpaired_archives.sort(key=lambda x: os.path.basename(x).lower())
    unpaired_previews.sort(key=lambda x: os.path.basename(x).lower())

    return unpaired_archives, unpaired_previews
