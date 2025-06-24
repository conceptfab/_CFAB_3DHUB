"""
Moduł odpowiedzialny za parowanie plików.

Ten moduł zawiera funkcje do tworzenia par plików (archiwum + podgląd)
oraz identyfikowania niesparowanych plików.
"""

import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Tuple

from src import app_config
from src.models.file_pair import FilePair

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Używamy definicji rozszerzeń z centralnego pliku konfiguracyjnego
ARCHIVE_EXTENSIONS = set(app_config.SUPPORTED_ARCHIVE_EXTENSIONS)
PREVIEW_EXTENSIONS = set(app_config.SUPPORTED_PREVIEW_EXTENSIONS)


def _categorize_files(files_list: List[str]) -> Tuple[List[str], List[str]]:
    """
    Kategoryzuje pliki na archiwa i podglądy.
    """
    if not files_list:
        return [], []

    archive_files = []
    preview_files = []

    for file_path in files_list:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ARCHIVE_EXTENSIONS:
            archive_files.append(file_path)
        elif ext in PREVIEW_EXTENSIONS:
            preview_files.append(file_path)

    return archive_files, preview_files


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
                    f"Błąd tworzenia FilePair dla '{archive_files[0]}' "
                    f"i '{preview_files[0]}': {e}"
                )

        return pairs, processed


class BestMatchStrategy(PairingStrategy):
    """Strategia inteligentnego parowania plików."""

    # Preferencje dla rozszerzeń podglądów (wyższa wartość = lepsza)
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
        """Tworzy pary plików używając inteligentnego dopasowania."""
        if not archive_files or not preview_files:
            return [], set()

        start_time = time.time()
        pairs = []
        processed = set()

        # Dla każdego archiwum znajdź najlepszy podgląd
        for archive in archive_files:
            if archive in processed:
                continue

            best_preview = self._find_best_preview(archive, preview_files, processed)

            if best_preview:
                try:
                    pair = FilePair(archive, best_preview, base_directory)
                    pairs.append(pair)
                    processed.add(archive)
                    processed.add(best_preview)
                except ValueError as e:
                    logger.error(
                        f"Błąd tworzenia FilePair dla '{archive}' "
                        f"i '{best_preview}': {e}"
                    )

        elapsed = (time.time() - start_time) * 1000
        logger.debug(
            f"BestMatchStrategy: {len(pairs)} pairs created in {elapsed:.2f}ms"
        )

        return pairs, processed

    def _find_best_preview(
        self, archive: str, preview_files: List[str], processed: Set[str]
    ) -> str:
        """Znajduje najlepszy podgląd dla danego archiwum."""
        archive_name = os.path.splitext(os.path.basename(archive))[0].lower()

        best_preview = ""
        best_score = -1

        for preview in preview_files:
            if preview in processed:
                continue

            score = self._calculate_match_score(preview, archive_name)
            if score > best_score:
                best_score = score
                best_preview = preview

        return best_preview

    def _calculate_match_score(self, preview: str, archive_name: str) -> int:
        """Oblicza wynik dopasowania między podglądem a archiwum."""
        preview_name = os.path.splitext(os.path.basename(preview))[0].lower()
        preview_ext = os.path.splitext(preview)[1].lower()

        # Podstawowy wynik z preferencji rozszerzenia
        score = self.PREVIEW_PREFERENCE.get(preview_ext, 0)

        # Bonus za dokładne dopasowanie nazwy
        if preview_name == archive_name:
            score += 1000

        # Bonus za częściowe dopasowanie
        elif preview_name.startswith(archive_name) or archive_name.startswith(
            preview_name
        ):
            score += 500

        return score


class PairingStrategyFactory:
    """Fabryka strategii parowania plików."""

    _strategies = {
        "first_match": FirstMatchStrategy(),
        "best_match": BestMatchStrategy(),
    }

    @classmethod
    def get_strategy(cls, strategy_name: str) -> PairingStrategy:
        """Pobiera strategię parowania po nazwie."""
        if strategy_name not in cls._strategies:
            raise ValueError(f"Nieznana strategia parowania: {strategy_name}")
        return cls._strategies[strategy_name]

    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Pobiera listę dostępnych strategii."""
        return list(cls._strategies.keys())


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
    start_time = time.time()
    found_pairs: List[FilePair] = []
    processed_files: Set[str] = set()

    # Pobierz strategię parowania
    try:
        strategy = PairingStrategyFactory.get_strategy(pair_strategy)
    except ValueError as e:
        logger.error(str(e))
        return found_pairs, processed_files

    total_files = sum(len(files) for files in file_map.values())
    logger.debug(
        f"Starting file pairing with {len(file_map)} directories, "
        f"{total_files} total files using '{pair_strategy}' strategy"
    )

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

    elapsed = (time.time() - start_time) * 1000
    logger.debug(
        f"File pairing completed: {len(found_pairs)} pairs from "
        f"{len(processed_files)} files in {elapsed:.2f}ms"
    )

    return found_pairs, processed_files


def identify_unpaired_files(
    file_map: Dict[str, List[str]],
    processed_files: Set[str],
) -> Tuple[List[str], List[str]]:
    """
    Identyfikuje niesparowane pliki.
    """
    if not file_map:
        return [], []

    unpaired_archives: List[str] = []
    unpaired_previews: List[str] = []

    for files_list in file_map.values():
        for file_path in files_list:
            if file_path in processed_files:
                continue

            ext = os.path.splitext(file_path)[1].lower()
            if ext in ARCHIVE_EXTENSIONS:
                unpaired_archives.append(file_path)
            elif ext in PREVIEW_EXTENSIONS:
                unpaired_previews.append(file_path)

    # Sortuj alfabetycznie
    unpaired_archives.sort(key=lambda x: os.path.basename(x).lower())
    unpaired_previews.sort(key=lambda x: os.path.basename(x).lower())

    return unpaired_archives, unpaired_previews
