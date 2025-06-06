"""
Zarządzanie metadanymi aplikacji, takimi jak "ulubione" oraz inne ustawienia.
Metadane są przechowywane w pliku JSON w folderze `.app_metadata`.
"""

import json
import logging
import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional

from filelock import FileLock, Timeout

# Import normalizacji ścieżek
from src.utils.path_utils import normalize_path

# Stałe związane z metadanymi
METADATA_DIR_NAME = ".app_metadata"
METADATA_FILE_NAME = "metadata.json"
LOCK_FILE_NAME = "metadata.lock"  # Nazwa pliku blokady
LOCK_TIMEOUT = 10  # Czas oczekiwania na blokadę w sekundach


def get_metadata_path(working_directory: str) -> str:
    """
    Zwraca pełną ścieżkę do pliku metadanych w podanym folderze roboczym.

    Args:
        working_directory (str): Ścieżka do folderu roboczego

    Returns:
        str: Pełna ścieżka do pliku metadanych
    """
    # Normalizujemy ścieżkę katalogu roboczego
    normalized_working_dir = normalize_path(working_directory)
    metadata_dir = os.path.join(normalized_working_dir, METADATA_DIR_NAME)
    return normalize_path(os.path.join(metadata_dir, METADATA_FILE_NAME))


def get_lock_path(working_directory: str) -> str:
    """
    Zwraca pełną ścieżkę do pliku blokady metadanych.

    Args:
        working_directory (str): Ścieżka do folderu roboczego.

    Returns:
        str: Pełna ścieżka do pliku blokady.
    """
    normalized_working_dir = normalize_path(working_directory)
    metadata_dir = os.path.join(normalized_working_dir, METADATA_DIR_NAME)
    return normalize_path(os.path.join(metadata_dir, LOCK_FILE_NAME))


def get_relative_path(absolute_path: str, base_path: str) -> Optional[str]:
    """
    Konwertuje ścieżkę absolutną na względną względem podanej ścieżki bazowej,
    używając znormalizowanych ścieżek.

    Args:
        absolute_path (str): Ścieżka absolutna do konwersji.
        base_path (str): Ścieżka bazowa, względem której tworzona jest ścieżka względna.

    Returns:
        Optional[str]: Ścieżka względna lub None w przypadku błędu.
    """
    try:
        # Normalizujemy obie ścieżki przed konwersją
        norm_abs_path = normalize_path(absolute_path)
        norm_base_path = normalize_path(base_path)

        # Upewniamy się, że obie ścieżki są absolutne
        if not os.path.isabs(norm_abs_path):
            logging.warning(f"Ścieżka do konwersji nie jest absolutna: {norm_abs_path}")
            # Próbujemy ją uczynić absolutną względem bieżącego katalogu roboczego,
            # ale to może nie być intencją użytkownika.
            norm_abs_path = normalize_path(os.path.abspath(norm_abs_path))

        if not os.path.isabs(norm_base_path):
            logging.warning(f"Ścieżka bazowa nie jest absolutna: {norm_base_path}")
            norm_base_path = normalize_path(os.path.abspath(norm_base_path))

        # Sprawdzamy, czy ścieżka absolutna zaczyna się od ścieżki bazowej
        # To jest ważne, aby os.path.relpath działało poprawnie na różnych dyskach w Windows
        if not norm_abs_path.startswith(norm_base_path):
            # Jeśli ścieżki są na różnych dyskach (Windows), relpath może zwrócić ścieżkę absolutną
            # co nie jest oczekiwane. W takim przypadku logujemy błąd i zwracamy None.
            if (
                os.name == "nt"
                and os.path.splitdrive(norm_abs_path)[0].lower()
                != os.path.splitdrive(norm_base_path)[0].lower()
            ):
                logging.error(
                    f"Nie można utworzyć ścieżki względnej: ścieżki są na różnych dyskach. "
                    f"Ścieżka: {norm_abs_path}, Baza: {norm_base_path}"
                )
                return None  # Zwracamy None, aby zasygnalizować problem

        rel_path = os.path.relpath(norm_abs_path, norm_base_path)
        return normalize_path(rel_path)  # Normalizujemy wynikową ścieżkę względną
    except (
        ValueError
    ) as ve:  # Może wystąpić, jeśli ścieżki są na różnych dyskach (Windows)
        logging.error(
            f"Błąd wartości podczas konwersji ścieżki {absolute_path} względem {base_path}: {ve}. "
            f"Możliwy problem z różnymi dyskami w systemie Windows."
        )
        return None
    except Exception as e:
        logging.error(
            f"Nieoczekiwany błąd konwersji ścieżki {absolute_path} względem {base_path}: {e}"
        )
        return None


def get_absolute_path(relative_path: str, base_path: str) -> Optional[str]:
    """
    Konwertuje ścieżkę względną na absolutną względem podanej ścieżki bazowej,
    używając znormalizowanych ścieżek.

    Args:
        relative_path (str): Ścieżka względna do konwersji.
        base_path (str): Ścieżka bazowa, względem której rozwiązywana jest ścieżka względna.

    Returns:
        Optional[str]: Ścieżka absolutna lub None w przypadku błędu.
    """
    try:
        # Normalizujemy obie ścieżki
        norm_rel_path = normalize_path(relative_path)
        norm_base_path = normalize_path(base_path)

        # Łączymy ścieżkę bazową i względną, a następnie normalizujemy i absolutyzujemy
        # os.path.abspath jest ważne, aby upewnić się, że ścieżka jest rzeczywiście absolutna
        abs_path = os.path.abspath(os.path.join(norm_base_path, norm_rel_path))
        return normalize_path(abs_path)
    except Exception as e:
        logging.error(
            f"Błąd konwersji ścieżki względnej {relative_path} względem {base_path}: {e}"
        )
        return None


def _validate_metadata_structure(metadata: Dict[str, Any]) -> bool:
    """
    Waliduje podstawową strukturę wczytanych metadanych.
    Sprawdza obecność i typy kluczowych pól.
    """
    if not isinstance(metadata, dict):
        logging.error("Metadane nie są słownikiem.")
        return False

    required_keys = {
        "file_pairs": dict,
        "unpaired_archives": list,
        "unpaired_previews": list,
    }

    for key, expected_type in required_keys.items():
        if key not in metadata:
            logging.warning(
                f"Brakujący klucz w metadanych: '{key}'. Uzupełnianie domyślnym."
            )
            # Uzupełniamy brakujące klucze, aby uniknąć błędów dalej
            if expected_type == dict:
                metadata[key] = {}
            elif expected_type == list:
                metadata[key] = []
            else:  # Powinno nie wystąpić z obecnymi required_keys
                metadata[key] = None

        elif not isinstance(metadata[key], expected_type):
            logging.error(
                f"Nieprawidłowy typ dla klucza '{key}' w metadanych. "
                f"Oczekiwano {expected_type.__name__}, otrzymano {type(metadata[key]).__name__}."
            )
            return False  # Błąd struktury jest poważny

    # Walidacja struktury wewnątrz 'file_pairs'
    if "file_pairs" in metadata and isinstance(metadata["file_pairs"], dict):
        for pair_key, pair_data in metadata["file_pairs"].items():
            if not isinstance(pair_data, dict):
                logging.error(
                    f"Nieprawidłowy format danych dla pary plików '{pair_key}'. Oczekiwano słownika."
                )
                return False
            # Można dodać bardziej szczegółową walidację pól wewnątrz pair_data, np. is_favorite, stars
            if "is_favorite" in pair_data and not isinstance(
                pair_data["is_favorite"], bool
            ):
                logging.warning(
                    f"Nieprawidłowy typ dla 'is_favorite' w parze '{pair_key}'."
                )
            if "stars" in pair_data and not isinstance(pair_data["stars"], int):
                logging.warning(f"Nieprawidłowy typ dla 'stars' w parze '{pair_key}'.")
            if "color_tag" in pair_data and not (
                isinstance(pair_data["color_tag"], str)
                or pair_data["color_tag"] is None
            ):
                logging.warning(
                    f"Nieprawidłowy typ dla 'color_tag' w parze '{pair_key}'."
                )

    return True


def load_metadata(working_directory: str) -> Dict[str, Any]:
    """
    Wczytuje metadane z pliku JSON w podanym folderze roboczym.
    Używa blokady pliku, aby zapobiec problemom współbieżności.

    Args:
        working_directory (str): Ścieżka do folderu roboczego.

    Returns:
        Dict[str, Any]: Słownik z metadanymi. Zawsze zawiera klucze
                        'file_pairs', 'unpaired_archives', 'unpaired_previews'.
    """
    metadata_path = get_metadata_path(working_directory)
    lock_path = get_lock_path(working_directory)

    default_metadata = {
        "file_pairs": {},
        "unpaired_archives": [],
        "unpaired_previews": [],
    }

    # Utworzenie katalogu metadanych, jeśli nie istnieje (potrzebne dla pliku blokady)
    try:
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
    except OSError as e:
        logging.error(
            f"Nie można utworzyć katalogu metadanych {os.path.dirname(metadata_path)}: {e}"
        )
        return default_metadata  # Nie można kontynuować bez katalogu

    lock = FileLock(lock_path, timeout=LOCK_TIMEOUT)

    try:
        with lock:
            if not os.path.exists(metadata_path):
                logging.debug(
                    f"Plik metadanych nie istnieje: {metadata_path}. Zwracam domyślne."
                )
                return default_metadata

            with open(metadata_path, "r", encoding="utf-8") as file:
                metadata = json.load(file)
                logging.debug(f"Wczytano metadane z {metadata_path}")

            if not _validate_metadata_structure(metadata):
                logging.warning(
                    f"Struktura metadanych w {metadata_path} jest nieprawidłowa. Zwracam domyślne."
                )
                return default_metadata

            return metadata
    except Timeout:
        logging.error(
            f"Nie można uzyskać blokady pliku metadanych {lock_path} w ciągu {LOCK_TIMEOUT}s."
        )
        return default_metadata
    except json.JSONDecodeError as e:
        logging.error(
            f"Błąd parsowania JSON w pliku metadanych {metadata_path}: {e}. Zwracam domyślne."
        )
        # Można rozważyć próbę odzyskania z kopii zapasowej, jeśli istnieje
        return default_metadata
    except Exception as e:
        logging.error(
            f"Nieoczekiwany błąd wczytywania metadanych z {metadata_path}: {e}. Zwracam domyślne."
        )
        return default_metadata


def save_metadata(
    working_directory: str,
    file_pairs_list: List,  # Oczekujemy listy obiektów FilePair
    unpaired_archives: List[str],
    unpaired_previews: List[str],
) -> bool:
    """
    Zapisuje metadane do pliku JSON w podanym folderze roboczym.
    Używa blokady pliku i atomowego zapisu (przez plik tymczasowy).

    Args:
        working_directory (str): Ścieżka do folderu roboczego.
        file_pairs_list (List): Lista obiektów FilePair, których metadane mają być zapisane.
        unpaired_archives (List[str]): Lista ścieżek absolutnych do niesparowanych archiwów.
        unpaired_previews (List[str]): Lista ścieżek absolutnych do niesparowanych podglądów.

    Returns:
        bool: True jeśli zapisano pomyślnie, False w przypadku błędu.
    """
    metadata_path = get_metadata_path(working_directory)
    lock_path = get_lock_path(working_directory)
    metadata_dir = os.path.dirname(metadata_path)  # Pobieramy katalog z pełnej ścieżki

    lock = FileLock(lock_path, timeout=LOCK_TIMEOUT)

    try:
        with lock:
            os.makedirs(metadata_dir, exist_ok=True)

            # Wczytanie istniejących metadanych, aby nie nadpisać innych informacji,
            # jeśli plik metadanych zawierałby więcej niż tylko te trzy klucze.
            # Jednak obecna logika load_metadata i tak zwraca tylko te klucze lub domyślne.
            # Dla bezpieczeństwa i przyszłej rozbudowy, lepiej wczytać.
            current_metadata = load_metadata(
                working_directory
            )  # load_metadata już obsługuje blokadę, ale tu jesteśmy wewnątrz bloku

            # Przygotowanie danych do zapisu dla sparowanych plików
            # Używamy słownika do przechowywania metadanych par, aby łatwiej aktualizować
            # i unikać duplikatów, jeśli file_pairs_list zawierałoby je.
            updated_file_pairs_metadata = current_metadata.get("file_pairs", {})

            for file_pair in file_pairs_list:
                # Sprawdzamy, czy obiekt ma wymagane atrybuty/metody
                if not all(
                    hasattr(file_pair, attr)
                    for attr in [
                        "archive_path",
                        "is_favorite",
                        "get_stars",
                        "get_color_tag",
                    ]
                ):
                    logging.warning(
                        f"Pominięto obiekt w file_pairs_list - brak wymaganych atrybutów: {file_pair}"
                    )
                    continue

                relative_archive_path = get_relative_path(
                    file_pair.archive_path, working_directory
                )
                if relative_archive_path is None:
                    logging.warning(
                        f"Nie można uzyskać ścieżki względnej dla {file_pair.archive_path}. Pomijam zapis tej pary."
                    )
                    continue

                pair_metadata = {
                    "is_favorite": file_pair.is_favorite,
                    "stars": file_pair.get_stars(),
                    "color_tag": file_pair.get_color_tag(),
                }
                updated_file_pairs_metadata[relative_archive_path] = pair_metadata

            current_metadata["file_pairs"] = updated_file_pairs_metadata

            # Przygotowanie i zapis list niesparowanych plików
            current_metadata["unpaired_archives"] = []
            for p in unpaired_archives:
                rel_p = get_relative_path(p, working_directory)
                if rel_p is not None:
                    current_metadata["unpaired_archives"].append(rel_p)
                else:
                    logging.warning(
                        f"Nie można uzyskać ścieżki względnej dla niesparowanego archiwum: {p}. Pomijam."
                    )

            current_metadata["unpaired_previews"] = []
            for p in unpaired_previews:
                rel_p = get_relative_path(p, working_directory)
                if rel_p is not None:
                    current_metadata["unpaired_previews"].append(rel_p)
                else:
                    logging.warning(
                        f"Nie można uzyskać ścieżki względnej dla niesparowanego podglądu: {p}. Pomijam."
                    )

            # Atomowy zapis: najpierw do pliku tymczasowego, potem zamiana
            temp_file_path = ""
            with tempfile.NamedTemporaryFile(
                mode="w",
                delete=False,
                encoding="utf-8",
                dir=metadata_dir,
                suffix=".tmp",
            ) as temp_file:
                json.dump(current_metadata, temp_file, ensure_ascii=False, indent=4)
                temp_file_path = temp_file.name

            # Zastępujemy docelowy plik tymczasowym
            # shutil.move jest generalnie atomowe na większości systemów, jeśli źródło i cel są na tym samym systemie plików.
            shutil.move(temp_file_path, metadata_path)
            logging.debug(f"Zapisano metadane do {metadata_path}")
            return True

    except Timeout:
        logging.error(
            f"Nie można uzyskać blokady pliku metadanych {lock_path} w ciągu {LOCK_TIMEOUT}s podczas zapisu."
        )
        return False
    except Exception as e:
        logging.error(f"Błąd zapisywania metadanych do {metadata_path}: {e}")
        # Usuń plik tymczasowy, jeśli istnieje i wystąpił błąd po jego utworzeniu
        if "temp_file_path" in locals() and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError as remove_err:
                logging.error(
                    f"Nie można usunąć tymczasowego pliku metadanych {temp_file_path}: {remove_err}"
                )
        return False


def apply_metadata_to_file_pairs(working_directory: str, file_pairs_list: List) -> bool:
    """
    Aktualizuje obiekty FilePair na podstawie metadanych z pliku JSON.

    Args:
        working_directory (str): Ścieżka do folderu roboczego.
        file_pairs_list (List): Lista obiektów FilePair do aktualizacji.

    Returns:
        bool: True jeśli aktualizacja przebiegła pomyślnie, False w przypadku błędu.
    """
    try:
        metadata = load_metadata(working_directory)  # load_metadata obsługuje blokadę

        if not metadata or "file_pairs" not in metadata or not metadata["file_pairs"]:
            logging.debug(
                "Brak metadanych par plików do zastosowania lub błąd wczytywania."
            )
            # Jeśli load_metadata zwróciło domyślne (puste) metadane, to jest to normalne, jeśli plik nie istniał.
            # Jeśli był błąd, load_metadata już to zalogowało.
            return True  # Traktujemy to jako "sukces" w sensie braku danych do przetworzenia

        file_pairs_metadata = metadata["file_pairs"]

        for file_pair in file_pairs_list:
            if not all(
                hasattr(file_pair, attr)
                for attr in [
                    "archive_path",
                    "is_favorite",
                    "get_stars",
                    "set_stars",
                    "get_color_tag",
                    "set_color_tag",
                    "get_base_name",
                ]
            ):
                logging.warning(
                    f"Pominięto obiekt w file_pairs_list przy stosowaniu metadanych - brak wymaganych atrybutów: {file_pair}"
                )
                continue

            relative_archive_path = get_relative_path(
                file_pair.archive_path, working_directory
            )

            if relative_archive_path is None:
                logging.warning(
                    f"Nie można uzyskać ścieżki względnej dla {file_pair.archive_path} podczas stosowania metadanych. Pomijam."
                )
                continue

            if relative_archive_path in file_pairs_metadata:
                pair_metadata = file_pairs_metadata[relative_archive_path]

                if "is_favorite" in pair_metadata and isinstance(
                    pair_metadata["is_favorite"], bool
                ):
                    file_pair.is_favorite = pair_metadata["is_favorite"]
                # else:
                #     logging.debug(f"Brak 'is_favorite' lub nieprawidłowy typ dla {relative_archive_path}")

                if "stars" in pair_metadata and isinstance(pair_metadata["stars"], int):
                    file_pair.set_stars(pair_metadata["stars"])
                # else:
                #     logging.debug(f"Brak 'stars' lub nieprawidłowy typ dla {relative_archive_path}")

                if "color_tag" in pair_metadata and (
                    isinstance(pair_metadata["color_tag"], str)
                    or pair_metadata["color_tag"] is None
                ):
                    file_pair.set_color_tag(pair_metadata["color_tag"])
                # else:
                #     logging.debug(f"Brak 'color_tag' lub nieprawidłowy typ dla {relative_archive_path}")

                logging.debug(
                    f"Zastosowano metadane dla {file_pair.get_base_name()}: "
                    f"Ulubiony={file_pair.is_favorite}, Gwiazdki={file_pair.get_stars()}, Kolor={file_pair.get_color_tag()}"
                )
            # else:
            #     logging.debug(f"Brak metadanych w pliku dla pary: {relative_archive_path}")

        return True

    except Exception as e:
        logging.error(f"Błąd stosowania metadanych do par plików: {e}")
        return False


# Dodatkowe funkcje pomocnicze, jeśli potrzebne, np. do usuwania metadanych dla konkretnych plików
# lub czyszczenia nieaktualnych wpisów.


def remove_metadata_for_file(
    working_directory: str, relative_archive_path: str
) -> bool:
    """
    Usuwa metadane dla konkretnej pary plików identyfikowanej przez jej względną ścieżkę archiwum.
    """
    metadata_path = get_metadata_path(working_directory)
    lock_path = get_lock_path(working_directory)
    lock = FileLock(lock_path, timeout=LOCK_TIMEOUT)

    try:
        with lock:
            if not os.path.exists(metadata_path):
                logging.debug(
                    f"Plik metadanych {metadata_path} nie istnieje. Nic do usunięcia."
                )
                return True

            current_metadata = load_metadata(
                working_directory
            )  # Ponownie, load_metadata ma swoją blokadę

            if (
                "file_pairs" in current_metadata
                and relative_archive_path in current_metadata["file_pairs"]
            ):
                del current_metadata["file_pairs"][relative_archive_path]
                logging.info(f"Usunięto metadane dla pliku: {relative_archive_path}")

                # Zapisz zmiany (używając logiki z save_metadata, ale uproszczonej, bo modyfikujemy tylko jeden klucz)
                # Dla uproszczenia, można by wywołać save_metadata z pustymi listami,
                # ale to by nadpisało unpaired_archives/previews.
                # Bezpieczniej jest zapisać cały obiekt current_metadata.

                temp_file_path = ""
                metadata_dir = os.path.dirname(metadata_path)
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    delete=False,
                    encoding="utf-8",
                    dir=metadata_dir,
                    suffix=".tmp",
                ) as temp_file:
                    json.dump(current_metadata, temp_file, ensure_ascii=False, indent=4)
                    temp_file_path = temp_file.name
                shutil.move(temp_file_path, metadata_path)
                return True
            else:
                logging.debug(
                    f"Brak metadanych do usunięcia dla pliku: {relative_archive_path}"
                )
                return True
    except Timeout:
        logging.error(
            f"Timeout podczas próby usunięcia metadanych dla {relative_archive_path}."
        )
        return False
    except Exception as e:
        logging.error(
            f"Błąd podczas usuwania metadanych dla {relative_archive_path}: {e}"
        )
        return False


def get_all_favorite_relative_paths(working_directory: str) -> List[str]:
    """
    Zwraca listę względnych ścieżek do archiwów oznaczonych jako ulubione.
    """
    metadata = load_metadata(working_directory)
    favorites = []
    if metadata and "file_pairs" in metadata:
        for rel_path, pair_data in metadata["file_pairs"].items():
            if pair_data.get("is_favorite", False):
                favorites.append(rel_path)
    return favorites


def get_metadata_for_relative_path(
    working_directory: str, relative_archive_path: str
) -> Optional[Dict[str, Any]]:
    """
    Pobiera metadane dla pojedynczej pary plików na podstawie jej względnej ścieżki archiwum.
    """
    metadata = load_metadata(working_directory)
    if metadata and "file_pairs" in metadata:
        return metadata["file_pairs"].get(relative_archive_path)
    return None
