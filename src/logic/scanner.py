"""
Moduł odpowiedzialny za skanowanie folderów i parowanie plików.
"""

import logging
import os
from collections import defaultdict
from typing import List, Tuple

from src import app_config  # Importujemy moduł konfiguracji
from src.models.file_pair import FilePair
from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)

# Używamy definicji rozszerzeń z centralnego pliku konfiguracyjnego
ARCHIVE_EXTENSIONS = set(app_config.SUPPORTED_ARCHIVE_EXTENSIONS)
PREVIEW_EXTENSIONS = set(app_config.SUPPORTED_PREVIEW_EXTENSIONS)


def scan_folder_for_pairs(
    directory: str,
) -> Tuple[List[FilePair], List[str], List[str]]:
    """
    Skanuje podany katalog i jego podkatalogi w poszukiwaniu par plików.

    Args:
        directory (str): Ścieżka do katalogu do przeskanowania.

    Returns:
        Tuple[List[FilePair], List[str], List[str]]: Krotka zawierająca listę
        znalezionych par, listę niesparowanych archiwów i listę niesparowanych
        podglądów.
    """
    directory = normalize_path(directory)
    logger.info(f"Rozpoczęto skanowanie katalogu: {directory}")
    logger.debug(f"Obsługiwane rozszerzenia archiwów: {ARCHIVE_EXTENSIONS}")
    logger.debug(f"Obsługiwane rozszerzenia podglądów: {PREVIEW_EXTENSIONS}")

    found_pairs: List[FilePair] = []
    unpaired_archives: List[str] = []
    unpaired_previews: List[str] = []
    file_map = defaultdict(list)

    total_folders_scanned = 0
    total_files_found = 0

    # Krok 1: Zbieranie wszystkich plików i normalizacja ścieżek od razu
    for root, dirs, files in os.walk(directory):
        normalized_root = normalize_path(root)
        total_folders_scanned += 1

        logger.debug(f"Skanowanie folderu: {normalized_root}")
        logger.debug(f"  Znalezione podfoldery: {dirs}")
        logger.debug(f"  Znalezione pliki: {len(files)}")

        for name in files:
            total_files_found += 1
            base_name, ext = os.path.splitext(name)
            ext_lower = ext.lower()
            if ext_lower in ARCHIVE_EXTENSIONS or ext_lower in PREVIEW_EXTENSIONS:
                map_key = os.path.join(normalized_root, base_name.lower())
                full_file_path = normalize_path(os.path.join(normalized_root, name))
                file_map[map_key].append(full_file_path)
                logger.debug(f"  Dodano do mapy: {name} (klucz: {map_key})")

    logger.info(
        f"Przeskanowano {total_folders_scanned} folderów, znaleziono {total_files_found} plików"
    )
    logger.info(f"Znaleziono {len(file_map)} unikalnych grup plików do sparowania")

    # Krok 2: Przetwarzanie zebranych plików i tworzenie par
    all_files_in_map = {file for files_list in file_map.values() for file in files_list}
    processed_files = set()

    for files_list in file_map.values():
        archive_files = [
            f
            for f in files_list
            if os.path.splitext(f)[1].lower() in ARCHIVE_EXTENSIONS
        ]
        preview_files = [
            f
            for f in files_list
            if os.path.splitext(f)[1].lower() in PREVIEW_EXTENSIONS
        ]

        # Tworzenie par
        if archive_files and preview_files:
            try:
                # Na razie bierzemy pierwszą znalezioną parę
                pair = FilePair(archive_files[0], preview_files[0], directory)
                found_pairs.append(pair)
                processed_files.add(archive_files[0])
                processed_files.add(preview_files[0])
            except ValueError as e:
                logger.error(f"Błąd tworzenia FilePair dla '{archive_files[0]}': {e}")

    # Krok 3: Identyfikacja niesparowanych plików
    unpaired_files = all_files_in_map - processed_files
    for f in unpaired_files:
        if os.path.splitext(f)[1].lower() in ARCHIVE_EXTENSIONS:
            unpaired_archives.append(f)
        elif os.path.splitext(f)[1].lower() in PREVIEW_EXTENSIONS:
            unpaired_previews.append(f)

    logger.info(
        f"Zakończono skanowanie '{directory}'. Znaleziono {len(found_pairs)} par, "
        f"{len(unpaired_archives)} niesparowanych archiwów i "
        f"{len(unpaired_previews)} niesparowanych podglądów."
    )
    return found_pairs, unpaired_archives, unpaired_previews


if __name__ == "__main__":
    # Ten blok jest przeznaczony do prostych testów manualnych.
    # Aby go użyć, odkomentuj i dostosuj ścieżkę `test_dir`.
    # Pamiętaj o utworzeniu odpowiedniej struktury folderów i plików.
    pass
