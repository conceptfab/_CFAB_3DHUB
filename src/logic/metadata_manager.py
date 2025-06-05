"""
Zarządzanie metadanymi aplikacji, takimi jak "ulubione" oraz inne ustawienia.
Metadane są przechowywane w pliku JSON w folderze `.app_metadata`.
"""

import json
import logging
import os
import shutil
import tempfile
from typing import Any, Dict, List

# Stałe związane z metadanymi
METADATA_DIR_NAME = ".app_metadata"
METADATA_FILE_NAME = "metadata.json"


def get_metadata_path(working_directory: str) -> str:
    """
    Zwraca pełną ścieżkę do pliku metadanych w podanym folderze roboczym.

    Args:
        working_directory (str): Ścieżka do folderu roboczego

    Returns:
        str: Pełna ścieżka do pliku metadanych
    """
    metadata_dir = os.path.join(working_directory, METADATA_DIR_NAME)
    return os.path.join(metadata_dir, METADATA_FILE_NAME)


def get_relative_path(absolute_path: str, base_path: str) -> str:
    """
    Konwertuje ścieżkę absolutną na względną względem podanej ścieżki bazowej.

    Args:
        absolute_path (str): Ścieżka absolutna do konwersji
        base_path (str): Ścieżka bazowa, względem której tworzona jest ścieżka względna

    Returns:
        str: Ścieżka względna
    """
    try:
        # Upewniamy się, że obie ścieżki są absolutne i znormalizowane
        abs_path = os.path.abspath(absolute_path)
        base = os.path.abspath(base_path)

        # Konwertujemy na ścieżkę względną
        rel_path = os.path.relpath(abs_path, base)
        return rel_path
    except Exception as e:
        logging.error(
            f"Błąd konwersji ścieżki {absolute_path} względem {base_path}: {e}"
        )
        # W razie problemu zwracamy ścieżkę oryginalną
        return absolute_path


def get_absolute_path(relative_path: str, base_path: str) -> str:
    """
    Konwertuje ścieżkę względną na absolutną względem podanej ścieżki bazowej.

    Args:
        relative_path (str): Ścieżka względna do konwersji
        base_path (str): Ścieżka bazowa, względem której rozwiązywana jest ścieżka względna

    Returns:
        str: Ścieżka absolutna
    """
    try:
        # Łączymy ścieżkę bazową i względną, a następnie normalizujemy
        abs_path = os.path.normpath(os.path.join(base_path, relative_path))
        return abs_path
    except Exception as e:
        logging.error(
            f"Błąd konwersji ścieżki względnej {relative_path} względem {base_path}: {e}"
        )
        # W razie problemu zwracamy None
        return None


def load_metadata(working_directory: str) -> Dict[str, Any]:
    """
    Wczytuje metadane z pliku JSON w podanym folderze roboczym.

    Args:
        working_directory (str): Ścieżka do folderu roboczego

    Returns:
        Dict[str, Any]: Słownik z metadanymi. Zawsze zawiera klucze
                        'file_pairs', 'unpaired_archives', 'unpaired_previews'.
    """
    metadata_path = get_metadata_path(working_directory)

    # Domyślna struktura metadanych
    default_metadata = {
        "file_pairs": {},  # Dane par plików, klucz to względna ścieżka archiwum
        "unpaired_archives": [],  # Lista względnych ścieżek do niesparowanych archiwów
        "unpaired_previews": [],  # Lista względnych ścieżek do niesparowanych podglądów
    }

    # Jeśli plik nie istnieje, zwracamy domyślne metadane
    if not os.path.exists(metadata_path):
        logging.debug(f"Plik metadanych nie istnieje: {metadata_path}")
        return default_metadata

    try:
        # Wczytujemy dane z pliku JSON
        with open(metadata_path, "r", encoding="utf-8") as file:
            metadata = json.load(file)
            logging.debug(f"Wczytano metadane z {metadata_path}")

            # Uzupełnienie o brakujące klucze dla niesparowanych plików
            if "unpaired_archives" not in metadata:
                metadata["unpaired_archives"] = []
            if "unpaired_previews" not in metadata:
                metadata["unpaired_previews"] = []

            # Upewnienie się, że klucz file_pairs istnieje
            if "file_pairs" not in metadata:
                metadata["file_pairs"] = {}

            return metadata
    except json.JSONDecodeError as e:
        logging.error(f"Błąd parsowania JSON w pliku metadanych {metadata_path}: {e}")
        return default_metadata  # Zwracamy domyślną strukturę w przypadku błędu
    except Exception as e:
        logging.error(f"Błąd wczytywania metadanych z {metadata_path}: {e}")
        return default_metadata  # Zwracamy domyślną strukturę w przypadku błędu


def save_metadata(
    working_directory: str,
    file_pairs_list: List,
    unpaired_archives: List[str],
    unpaired_previews: List[str],
) -> bool:
    """
    Zapisuje metadane do pliku JSON w podanym folderze roboczym.
    Obejmuje to dane sparowanych plików oraz listy niesparowanych archiwów i podglądów.

    Args:
        working_directory (str): Ścieżka do folderu roboczego.
        file_pairs_list (List): Lista obiektów FilePair, których metadane mają być zapisane.
        unpaired_archives (List[str]): Lista ścieżek absolutnych do niesparowanych archiwów.
        unpaired_previews (List[str]): Lista ścieżek absolutnych do niesparowanych podglądów.

    Returns:
        bool: True jeśli zapisano pomyślnie, False w przypadku błędu.
    """
    # Utwórz folder metadanych jeśli nie istnieje
    metadata_dir = os.path.join(working_directory, METADATA_DIR_NAME)
    metadata_path = os.path.join(metadata_dir, METADATA_FILE_NAME)

    try:
        # Tworzenie katalogu metadanych, jeśli nie istnieje
        os.makedirs(metadata_dir, exist_ok=True)

        # Wczytanie istniejących metadanych, jeśli są dostępne
        current_metadata = load_metadata(working_directory)

        # Zapewnienie, że 'file_pairs' istnieje w current_metadata, nawet jeśli load_metadata zwróciło domyślne
        if "file_pairs" not in current_metadata:
            current_metadata["file_pairs"] = {}

        # Przygotowanie danych do zapisu dla sparowanych plików
        for file_pair in file_pairs_list:
            # Konwersja ścieżki absolutnej na względną
            relative_archive_path = get_relative_path(
                file_pair.archive_path, working_directory
            )

            # Zapisujemy tylko te właściwości, które chcemy zachować między sesjami
            pair_metadata = {
                "is_favorite": file_pair.is_favorite,
                "stars": file_pair.get_stars(),
                "color_tag": file_pair.get_color_tag(),
            }

            # Aktualizujemy istniejące metadane
            current_metadata["file_pairs"][relative_archive_path] = pair_metadata

        # Przygotowanie i zapis list niesparowanych plików (jako ścieżki względne)
        current_metadata["unpaired_archives"] = [
            get_relative_path(p, working_directory) for p in unpaired_archives
        ]
        current_metadata["unpaired_previews"] = [
            get_relative_path(p, working_directory) for p in unpaired_previews
        ]

        # Zapisujemy do pliku tymczasowego, a potem zastępujemy docelowy
        # dla bezpieczeństwa (w przypadku przerwania zapisu)
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, encoding="utf-8"
        ) as temp_file:
            json.dump(current_metadata, temp_file, ensure_ascii=False, indent=4)

        # Zastępujemy docelowy plik tymczasowym
        shutil.move(temp_file.name, metadata_path)
        logging.debug(f"Zapisano metadane do {metadata_path}")
        return True

    except Exception as e:
        logging.error(f"Błąd zapisywania metadanych do {metadata_path}: {e}")
        return False


def apply_metadata_to_file_pairs(working_directory: str, file_pairs_list: List) -> bool:
    """
    Aktualizuje obiekty FilePair na podstawie metadanych z pliku JSON.

    Args:
        working_directory (str): Ścieżka do folderu roboczego
        file_pairs_list (List): Lista obiektów FilePair do aktualizacji

    Returns:
        bool: True jeśli aktualizacja przebiegła pomyślnie, False w przypadku błędu
    """
    try:
        # Wczytujemy metadane
        metadata = load_metadata(working_directory)

        # Sprawdzamy, czy są jakiekolwiek metadane dla par plików
        if "file_pairs" not in metadata or not metadata["file_pairs"]:
            logging.debug("Brak metadanych par plików do zastosowania")
            return True

        # Aktualizujemy obiekty FilePair
        for file_pair in file_pairs_list:
            # Konwersja ścieżki absolutnej na względną dla dopasowania
            relative_archive_path = get_relative_path(
                file_pair.archive_path, working_directory
            )

            # Sprawdzamy, czy istnieją metadane dla tego pliku
            if relative_archive_path in metadata["file_pairs"]:
                pair_metadata = metadata["file_pairs"][relative_archive_path]

                # Ustawiamy status "ulubiony", jeśli istnieje w metadanych
                if "is_favorite" in pair_metadata:
                    file_pair.is_favorite = pair_metadata["is_favorite"]
                    logging.debug(
                        f"Zastosowano status 'ulubiony' dla {file_pair.get_base_name()}: {file_pair.is_favorite}"
                    )

                # Ustawiamy liczbę gwiazdek, jeśli istnieje w metadanych
                if "stars" in pair_metadata:
                    file_pair.set_stars(pair_metadata["stars"])
                    logging.debug(
                        f"Zastosowano gwiazdki dla {file_pair.get_base_name()}: {file_pair.get_stars()}"
                    )

                # Ustawiamy tag kolorystyczny, jeśli istnieje w metadanych
                if "color_tag" in pair_metadata:
                    file_pair.set_color_tag(pair_metadata["color_tag"])
                    logging.debug(
                        f"Zastosowano tag koloru dla {file_pair.get_base_name()}: {file_pair.get_color_tag()}"
                    )

        return True

    except Exception as e:
        logging.error(f"Błąd stosowania metadanych do par plików: {e}")
        return False
