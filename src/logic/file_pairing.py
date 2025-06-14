"""
Moduł odpowiedzialny za parowanie plików.

Ten moduł zawiera funkcje do tworzenia par plików (archiwum + podgląd)
oraz identyfikowania niesparowanych plików.
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
    pair_strategy: str = "first_match",
) -> Tuple[List[FilePair], Set[str]]:
    """
    Tworzy pary plików na podstawie zebranych danych.

    Args:
        file_map: Słownik zmapowanych plików
        base_directory: Katalog bazowy dla względnych ścieżek w FilePair
        pair_strategy: Strategia parowania plików.
                         "first_match": tylko pierwsza znaleziona para.
                         "all_combinations": wszystkie możliwe kombinacje archiwum-podgląd.
                         "best_match": inteligentne parowanie po nazwach.

    Returns:
        Krotka zawierająca listę utworzonych par oraz zbiór przetworzonych plików
    """
    found_pairs: List[FilePair] = []
    processed_files: Set[str] = set()

    for base_path, files_list in file_map.items():
        # Pre-compute rozszerzeń dla optymalizacji
        files_with_ext = [(f, os.path.splitext(f)[1].lower()) for f in files_list]

        archive_files = [f for f, ext in files_with_ext if ext in ARCHIVE_EXTENSIONS]
        preview_files = [f for f, ext in files_with_ext if ext in PREVIEW_EXTENSIONS]

        if not archive_files or not preview_files:
            continue

        if pair_strategy == "first_match":
            # Tylko pierwsza para
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
            # Wszystkie kombinacje
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
            # Zoptymalizowany algorytm używający hashmaps - złożoność O(n+m)

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
                else:
                    # 2. Częściowa zgodność - OPTYMALIZACJA: tylko gdy nie ma dokładnego dopasowania
                    # Ograniczamy sprawdzanie prefiksów do 20 najdłuższych
                    matching_keys = []
                    for preview_base_name in preview_map.keys():
                        if preview_base_name.startswith(
                            archive_base_name
                        ) or archive_base_name.startswith(preview_base_name):
                            matching_keys.append(preview_base_name)

                    # Sortowanie po długości (zaczynając od najdłuższych)
                    matching_keys.sort(key=len, reverse=True)
                    for preview_base_name in matching_keys[
                        :20
                    ]:  # Limit do 20 najdłuższych
                        candidates.extend(
                            [(p, 500) for p in preview_map[preview_base_name]]
                        )

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

    unpaired_archives.sort(key=lambda x: os.path.basename(x).lower())
    unpaired_previews.sort(key=lambda x: os.path.basename(x).lower())

    return unpaired_archives, unpaired_previews
