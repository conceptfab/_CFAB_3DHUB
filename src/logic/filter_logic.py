"""
Moduł odpowiedzialny za logikę filtrowania listy par plików.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from src.models.file_pair import FilePair
from src.utils.path_utils import normalize_path

# Stałe dla specjalnych wartości filtrów
COLOR_FILTER_ALL = "ALL"  # Brak filtrowania kolorów
COLOR_FILTER_NONE = "__NONE__"  # Tylko elementy bez koloru


def _validate_filter_criteria(filter_criteria: Dict[str, Any]) -> Dict[str, Any]:
    """
    Waliduje kryteria filtrowania i zapewnia odpowiednie typy danych.

    Args:
        filter_criteria: Słownik z kryteriami filtrowania.

    Returns:
        Zwalidowany słownik kryteriów filtrowania.
    """
    validated_criteria = {}

    # Walidacja min_stars (musi być liczbą całkowitą >= 0)
    min_stars = filter_criteria.get("min_stars", 0)
    try:
        min_stars = int(min_stars)
        if min_stars < 0:
            min_stars = 0
    except (TypeError, ValueError):
        min_stars = 0
    validated_criteria["min_stars"] = min_stars

    # Walidacja required_color_tag (musi być stringiem lub None)
    color_tag = filter_criteria.get("required_color_tag", COLOR_FILTER_ALL)
    if color_tag is None:
        color_tag = COLOR_FILTER_ALL
    elif not isinstance(color_tag, str):
        try:
            color_tag = str(color_tag)
        except (TypeError, ValueError):
            color_tag = COLOR_FILTER_ALL
    validated_criteria["required_color_tag"] = color_tag

    # Walidacja path_prefix (musi być stringiem lub None)
    path_prefix = filter_criteria.get("path_prefix")
    if path_prefix is not None and not isinstance(path_prefix, str):
        try:
            path_prefix = str(path_prefix)
        except (TypeError, ValueError):
            path_prefix = None
    validated_criteria["path_prefix"] = path_prefix

    return validated_criteria


def _check_color_match(pair_color_tag: Optional[str], required_color_tag: str) -> bool:
    """
    Sprawdza, czy tag koloru pary pasuje do wymaganego tagu koloru.

    Args:
        pair_color_tag: Tag koloru pary plików (może być None).
        required_color_tag: Wymagany tag koloru z kryteriów filtrowania.

    Returns:
        True jeśli tagi są zgodne, False w przeciwnym przypadku.
    """
    # Przypadek: brak filtrowania kolorów
    if required_color_tag == COLOR_FILTER_ALL:
        return True

    # Przypadek: filtrowanie tylko elementów bez koloru
    if required_color_tag == COLOR_FILTER_NONE:
        return pair_color_tag is None or pair_color_tag == ""

    # Przypadek: konkretny kolor - porównanie niewrażliwe na wielkość liter
    if pair_color_tag is None:
        return False

    return pair_color_tag.strip().lower() == required_color_tag.strip().lower()


def filter_file_pairs(
    file_pairs_list: List[FilePair], filter_criteria: Dict[str, Any]
) -> List[FilePair]:
    """
    Filtruje listę obiektów FilePair na podstawie podanych kryteriów.

    Args:
        file_pairs_list (List[FilePair]): Lista wszystkich obiektów FilePair.
        filter_criteria (Dict[str, Any]): Słownik określający kryteria
            filtrowania:
            {
                "min_stars": int,             # 0-5, 0 = brak filtra gwiazdek
                "required_color_tag": str     # "ALL" = brak filtra,
                                              # "__NONE__" = tag pusty,
                                              # "#RRGGBB" = konkretny kolor
                "path_prefix": str            # Prefiks ścieżki do filtrowania
            }

    Returns:
        List[FilePair]: Nowa lista obiektów FilePair spełniających kryteria.
    """
    if not filter_criteria:
        logging.debug("Brak kryteriów filtrowania, zwracam oryginał.")
        return file_pairs_list

    # Walidacja kryteriów filtrowania
    validated_criteria = _validate_filter_criteria(filter_criteria)

    filtered_list: List[FilePair] = []
    min_stars = validated_criteria["min_stars"]
    required_color_tag = validated_criteria["required_color_tag"]
    path_prefix = validated_criteria["path_prefix"]

    # Optymalizacja: normalizacja path_prefix przed pętlą
    normalized_path_prefix = normalize_path(path_prefix) if path_prefix else None

    logging.debug(f"Filter run: {len(file_pairs_list)} pairs.")
    logging.debug(
        f"Crit: S>={min_stars}, " f"C='{required_color_tag}', Path='{path_prefix}'"
    )

    rejected_count = 0

    for i, pair in enumerate(file_pairs_list):
        # Wybieramy krótszą nazwę do logowania
        fp_name = pair.get_base_name()[:20]

        # Sprawdzenie warunku ścieżki (optymalizacja)
        if normalized_path_prefix:
            pair_path = normalize_path(pair.get_archive_path())
            if not pair_path.startswith(normalized_path_prefix):
                rejected_count += 1
                continue

        # Sprawdzenie warunku minimalnej liczby gwiazdek
        pair_stars = pair.get_stars()
        if min_stars > 0 and pair_stars < min_stars:
            rejected_count += 1
            continue

        # Sprawdzenie warunku tagu kolorystycznego
        pair_color_tag = pair.get_color_tag()
        if not _check_color_match(pair_color_tag, required_color_tag):
            rejected_count += 1
            continue

        # Logowanie tylko dla co 100. elementu lub dla małych zbiorów danych
        if i < 10 or i % 100 == 0:
            logging.debug(f"  P#{i}({fp_name}): PASS")

        filtered_list.append(pair)

    logging.debug(
        f"Filter end. Total: {len(file_pairs_list)}, Matches: {len(filtered_list)}, Rejected: {rejected_count}"
    )
    return filtered_list
