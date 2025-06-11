"""
Algorytmy parowania plików.
"""

import logging
import os
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from src import app_config
from src.models.file_pair import FilePair

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Używamy definicji rozszerzeń z centralnego pliku konfiguracyjnego
ARCHIVE_EXTENSIONS = set(app_config.SUPPORTED_ARCHIVE_EXTENSIONS)
PREVIEW_EXTENSIONS = set(app_config.SUPPORTED_PREVIEW_EXTENSIONS)


def create_file_pairs(
    file_map: Dict[str, List[str]],
    base_directory: str,
    pair_strategy: str = "first_match",  # "first_match", "all_combinations", "best_match"
) -> Tuple[List[FilePair], Set[str]]:
    """
    Tworzy pary plików na podstawie zebranych danych.

    Args:
        file_map: Słownik zmapowanych plików
        base_directory: Katalog bazowy dla par
        pair_strategy: Strategia parowania plików

    Returns:
        Krotka zawierająca listę znalezionych par i zbiór przetworzonych plików

    Raises:
        ValueError: Jeśli nie można utworzyć FilePair
    """
    found_pairs: List[FilePair] = []
    processed_files: Set[str] = set()

    for base_name, files in file_map.items():
        # Rozdzielamy pliki na archiwa i podglądy
        archive_files = [
            f for f in files if os.path.splitext(f)[1].lower() in ARCHIVE_EXTENSIONS
        ]
        preview_files = [
            f for f in files if os.path.splitext(f)[1].lower() in PREVIEW_EXTENSIONS
        ]

        # Jeśli nie ma archiwów lub podglądów, pomijamy
        if not archive_files or not preview_files:
            continue

        if pair_strategy == "first_match":
            # Tylko pierwsza para (odpowiednik pair_all=False)
            try:
                pair = FilePair(archive_files[0], preview_files[0], base_directory)
                found_pairs.append(pair)
                processed_files.add(archive_files[0])
                processed_files.add(preview_files[0])
            except ValueError as e:
                logger.error(
                    f"Błąd tworzenia FilePair dla '{archive_files[0]}' i '{preview_files[0]}': {e}"
                )

        elif pair_strategy == "all_combinations":
            # Wszystkie kombinacje (odpowiednik pair_all=True)
            for archive in archive_files:
                for preview in preview_files:
                    try:
                        pair = FilePair(archive, preview, base_directory)
                        found_pairs.append(pair)
                        processed_files.add(archive)
                        processed_files.add(preview)
                    except ValueError as e:
                        logger.error(
                            f"Błąd tworzenia FilePair dla '{archive}' i '{preview}': {e}"
                        )
        elif pair_strategy == "best_match":
            # OPTYMALIZACJA: Zmieniono z O(n*m) na O(n+m) używając hash maps
            # Stary algorytm miał zagnieżdżone pętle dla każdej pary archiwum-podgląd
            # Nowy algorytm grupuje podglądy według nazw bazowych i używa hashowania

            # Preferowane rozszerzenia podglądu (od najbardziej preferowanego)
            preview_preference = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]

            # Budujemy hash mapę podglądów według nazw bazowych - O(m)
            preview_map = defaultdict(list)
            for preview in preview_files:
                preview_name = os.path.basename(preview)
                preview_base_name = os.path.splitext(preview_name)[0].lower()
                preview_map[preview_base_name].append(preview)

            # Dla każdego archiwum szukamy najlepszego podglądu - O(n)
            for archive in archive_files:
                archive_name = os.path.basename(archive)
                archive_base_name = os.path.splitext(archive_name)[0].lower()
                best_preview = None
                best_score = -1

                # Szukamy kandydatów podglądów - O(1) dzięki hash mapie
                candidates = []

                # 1. Dokładna zgodność nazwy (najlepsze dopasowanie)
                if archive_base_name in preview_map:
                    candidates.extend(
                        [(p, 1000) for p in preview_map[archive_base_name]]
                    )

                # 2. Częściowa zgodność - sprawdzamy tylko prefiksy (optymalizacja)
                for preview_base_name, preview_list in preview_map.items():
                    if preview_base_name != archive_base_name:  # Już sprawdzone wyżej
                        if preview_base_name.startswith(archive_base_name):
                            candidates.extend([(p, 500) for p in preview_list])
                        elif archive_base_name.startswith(preview_base_name):
                            candidates.extend([(p, 500) for p in preview_list])

                # Oceniamy tylko znalezionych kandydatów
                for preview, base_score in candidates:
                    score = base_score
                    preview_ext = os.path.splitext(preview)[1].lower()

                    # Dodajemy punkty za preferowane rozszerzenie
                    if preview_ext in preview_preference:
                        score += (
                            len(preview_preference)
                            - preview_preference.index(preview_ext)
                        ) * 10

                    # Dodajemy mały bonus za nowsze pliki
                    try:
                        mtime = os.path.getmtime(preview)
                        score += mtime / 10000000  # Dodaje mały ułamek do punktacji
                    except (OSError, PermissionError):
                        pass  # Ignorujemy błędy przy sprawdzaniu czasu modyfikacji

                    # Aktualizujemy najlepszy podgląd
                    if score > best_score:
                        best_score = score
                        best_preview = preview

                # Jeśli znaleźliśmy pasujący podgląd, tworzymy parę
                if best_preview and best_score > 0:
                    try:
                        pair = FilePair(archive, best_preview, base_directory)
                        found_pairs.append(pair)
                        processed_files.add(archive)
                        processed_files.add(best_preview)
                    except ValueError as e:
                        logger.error(
                            f"Błąd tworzenia FilePair dla '{archive}' i '{best_preview}': {e}"
                        )
        else:
            logger.error(f"Nieznana strategia parowania: {pair_strategy}")

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

    return unpaired_archives, unpaired_previews
