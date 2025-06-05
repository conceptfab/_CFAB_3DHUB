"""
Moduł odpowiedzialny za logikę filtrowania listy par plików.
"""

import logging
from typing import Any, Dict, List

from src.models.file_pair import FilePair
from src.utils.path_utils import normalize_path


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
                "show_favorites_only": bool,  # True, by pokazać tylko ulubione
                "min_stars": int,             # 0-5, 0 = brak filtra gwiazdek
                "required_color_tag": str     # "ALL" = brak filtra,
                                              # "__NONE__" = tag pusty,
                                              # "#RRGGBB" = konkretny kolor
            }

    Returns:
        List[FilePair]: Nowa lista obiektów FilePair spełniających kryteria.
    """
    if not filter_criteria:
        logging.debug("Brak kryteriów filtrowania, zwracam oryginał.")
        return file_pairs_list

    filtered_list: List[FilePair] = []
    show_favorites_only = filter_criteria.get("show_favorites_only", False)
    min_stars = filter_criteria.get("min_stars", 0)
    required_color_tag = filter_criteria.get("required_color_tag", "ALL")
    path_prefix = filter_criteria.get("path_prefix")

    logging.debug(f"Filter run: {len(file_pairs_list)} pairs.")
    logging.debug(
        f"Crit: Fav={show_favorites_only}, S>={min_stars}, "
        f"C='{required_color_tag}', Path='{path_prefix}'"
    )

    for i, pair in enumerate(file_pairs_list):
        fp_name = pair.get_base_name()[:20]  # Nazwa dla logów

        # Sprawdzenie warunku ścieżki (nowy warunek na początku)
        if path_prefix:
            # Używamy tej samej, spójnej normalizacji
            pair_path = normalize_path(pair.get_archive_path())
            prefix = normalize_path(path_prefix)

            # Sprawdzamy, czy ścieżka pliku zaczyna się od ścieżki folderu.
            # To jest kluczowe dla poprawnego filtrowania.
            if not pair_path.startswith(prefix):
                continue

        pair_is_fav = pair.is_favorite
        pair_stars = pair.get_stars()
        pair_color_tag = pair.get_color_tag()

        logging.debug(
            f"P#{i}({fp_name}):F?{pair_is_fav},S:{pair_stars},T:'{pair_color_tag}'"
        )

        # Sprawdzenie warunku ulubionych
        if show_favorites_only and not pair_is_fav:
            logging.debug(f"  P#{i}({fp_name}): REJ (fav)")
            continue

        # Sprawdzenie warunku minimalnej liczby gwiazdek
        if min_stars > 0 and pair_stars < min_stars:
            logging.debug(f"  P#{i}({fp_name}): REJ (stars {pair_stars}<{min_stars})")
            continue

        # Sprawdzenie warunku tagu kolorystycznego
        passes_color_filter = False
        if required_color_tag == "ALL":
            passes_color_filter = True
            logging.debug(f"  P#{i}({fp_name}): FilterC='ALL' -> OK")
        elif required_color_tag == "__NONE__":
            if not pair_color_tag:  # Pusty string lub None
                passes_color_filter = True
                logging.debug(
                    f"  P#{i}({fp_name}): FilterC='__NONE__', "
                    f"T:'{pair_color_tag}' -> OK"
                )
            else:
                logging.debug(
                    f"  P#{i}({fp_name}): FilterC='__NONE__', "
                    f"T:'{pair_color_tag}' -> REJ"
                )
        else:  # Konkretny kod hex
            # Porównanie niewrażliwe na wielkość liter i z trimowaniem
            if (
                isinstance(pair_color_tag, str)
                and isinstance(required_color_tag, str)
                and pair_color_tag.strip().lower() == required_color_tag.strip().lower()
            ):
                passes_color_filter = True
                logging.debug(
                    f"  P#{i}({fp_name}): FilterC='{required_color_tag}', "
                    f"T:'{pair_color_tag}' -> OK"
                )
            else:
                logging.debug(
                    f"  P#{i}({fp_name}): FilterC='{required_color_tag}', "
                    f"T:'{pair_color_tag}' -> REJ"
                )

        if not passes_color_filter:
            continue

        logging.debug(f"  P#{i}({fp_name}): PASS")
        filtered_list.append(pair)

    logging.debug(f"Filter end. Matches: {len(filtered_list)}.")
    return filtered_list
