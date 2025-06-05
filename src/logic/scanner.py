"""
Moduł odpowiedzialny za skanowanie folderów i parowanie plików.
"""

import logging
import os
from collections import defaultdict
from typing import List, Tuple

from src.models.file_pair import FilePair

logger = logging.getLogger(__name__)

# Definicje rozszerzeń są teraz w jednym miejscu, tutaj.
ARCHIVE_EXTENSIONS = {".rar", ".zip", ".7z"}
PREVIEW_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}


def _normalize_path(path: str) -> str:
    """Normalizuje ścieżkę, zamieniając separatory na '/'."""
    if not path:
        return ""
    return os.path.normpath(path).replace("\\", "/")


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
    directory = _normalize_path(directory)
    logger.info(f"Rozpoczęto skanowanie katalogu: {directory}")
    found_pairs: List[FilePair] = []
    unpaired_archives: List[str] = []
    unpaired_previews: List[str] = []
    file_map = defaultdict(list)

    # Krok 1: Zbieranie wszystkich plików i normalizacja ścieżek od razu
    for root, _, files in os.walk(directory):
        normalized_root = _normalize_path(root)
        for name in files:
            base_name, _ = os.path.splitext(name)
            full_path = os.path.join(normalized_root, name)
            # Kluczem mapy jest ścieżka bazowa (folder/nazwa_bez_rozszerzenia)
            map_key = os.path.join(normalized_root, base_name.lower())
            file_map[map_key].append(full_path)

    # Krok 2: Przetwarzanie zebranych plików i tworzenie par
    for _, files in file_map.items():
        archive_file = None
        preview_file = None

        for file_path in files:
            _, ext = os.path.splitext(file_path)
            if ext.lower() in ARCHIVE_EXTENSIONS:
                archive_file = file_path
            elif ext.lower() in PREVIEW_EXTENSIONS:
                preview_file = file_path

        if archive_file and preview_file:
            # Znaleziono parę
            try:
                pair = FilePair(archive_file, preview_file, directory)
                found_pairs.append(pair)
            except ValueError as e:
                logger.error(f"Błąd tworzenia FilePair dla '{archive_file}': {e}")
        else:
            # Pliki bez pary
            if archive_file:
                unpaired_archives.append(archive_file)
            if preview_file:
                unpaired_previews.append(preview_file)

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
