"""
Zarządzanie metadanymi aplikacji, takimi jak "ulubione" oraz inne ustawienia.
Metadane są przechowywane w pliku JSON w folderze `.app_metadata`.
"""

import json
import logging
import os
import shutil
import tempfile
import time
from typing import Any, Dict, List, Optional

from filelock import FileLock, Timeout

# Import normalizacji ścieżek
from src.utils.path_utils import normalize_path

# Stałe związane z metadanymi
METADATA_DIR_NAME = ".app_metadata"
METADATA_FILE_NAME = "metadata.json"
LOCK_FILE_NAME = "metadata.lock"  # Nazwa pliku blokady
LOCK_TIMEOUT = 1  # Czas oczekiwania na blokadę w sekundach (zmniejszone)

# Konfiguracja loggera dla tego modułu
logger = logging.getLogger(__name__)


class MetadataManager:
    """
    Klasa zarządzająca metadanymi aplikacji.
    Opakowuje funkcje związane z operacjami na metadanych.
    """

    def __init__(self, working_directory: str):
        """
        Inicjalizuje menedżer metadanych.

        Args:
            working_directory (str): Ścieżka do folderu roboczego
        """
        self.working_directory = working_directory
        self._changes_buffer = {}  # Bufor zmian
        self._last_save_time = 0
        self._save_delay = 2.0  # Opóźnienie zapisu w sekundach

    def get_metadata_path(self) -> str:
        """Zwraca ścieżkę do pliku metadanych."""
        return get_metadata_path(self.working_directory)

    def get_lock_path(self) -> str:
        """Zwraca ścieżkę do pliku blokady."""
        return get_lock_path(self.working_directory)

    def load_metadata(self) -> Dict[str, Any]:
        """Wczytuje metadane z pliku."""
        return load_metadata(self.working_directory)

    def _should_save(self) -> bool:
        """Sprawdza czy należy zapisać zmiany."""
        current_time = time.time()
        return (current_time - self._last_save_time) >= self._save_delay

    def _flush_changes(self):
        """Zapisuje wszystkie zmiany z bufora."""
        if not self._changes_buffer:
            return

        try:
            # Wczytaj aktualne metadane
            current_metadata = load_metadata(self.working_directory)

            # Zastosuj zmiany z bufora
            for key, value in self._changes_buffer.items():
                current_metadata[key] = value

            # Zapisz zmiany
            save_metadata(
                self.working_directory,
                current_metadata.get("file_pairs", []),
                current_metadata.get("unpaired_archives", []),
                current_metadata.get("unpaired_previews", []),
            )

            # Wyczyść bufor
            self._changes_buffer.clear()
            self._last_save_time = time.time()

        except Exception as e:
            logger.error(f"Błąd podczas zapisywania metadanych: {e}", exc_info=True)

    def save_metadata(
        self,
        file_pairs_list: List,
        unpaired_archives: List[str],
        unpaired_previews: List[str],
    ) -> bool:
        """Zapisuje metadane do pliku z buforowaniem."""
        try:
            # Dodaj zmiany do bufora
            self._changes_buffer["file_pairs"] = file_pairs_list
            self._changes_buffer["unpaired_archives"] = unpaired_archives
            self._changes_buffer["unpaired_previews"] = unpaired_previews

            # Sprawdź czy należy zapisać
            if self._should_save():
                self._flush_changes()
            return True

        except Exception as e:
            logger.error(f"Błąd podczas buforowania metadanych: {e}", exc_info=True)
            return False

    def apply_metadata_to_file_pairs(self, file_pairs_list: List) -> bool:
        """Aplikuje metadane do listy par plików."""
        return apply_metadata_to_file_pairs(self.working_directory, file_pairs_list)

    def remove_metadata_for_file(self, relative_archive_path: str) -> bool:
        """Usuwa metadane dla pliku."""
        return remove_metadata_for_file(self.working_directory, relative_archive_path)

    def get_metadata_for_relative_path(
        self, relative_archive_path: str
    ) -> Optional[Dict[str, Any]]:
        """Pobiera metadane dla ścieżki względnej."""
        return get_metadata_for_relative_path(
            self.working_directory, relative_archive_path
        )

    def save_file_pair_metadata(self, file_pair, working_directory: str) -> bool:
        """Zapisuje metadane dla pojedynczej pary plików."""
        return save_file_pair_metadata(file_pair, working_directory)


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
        Optional[str]: Ścieżka względna lub None w przypadku błędu (np. różne dyski).
    """
    try:
        # Normalizujemy obie ścieżki przed konwersją
        norm_abs_path = normalize_path(absolute_path)
        norm_base_path = normalize_path(base_path)

        # Upewniamy się, że obie ścieżki są absolutne
        if not os.path.isabs(norm_abs_path):
            logger.warning(f"Ścieżka do konwersji nie jest absolutna: {norm_abs_path}")
            norm_abs_path = normalize_path(os.path.abspath(norm_abs_path))

        if not os.path.isabs(norm_base_path):
            logger.warning(f"Ścieżka bazowa nie jest absolutna: {norm_base_path}")
            norm_base_path = normalize_path(os.path.abspath(norm_base_path))

        # Sprawdzenie, czy ścieżki są na różnych dyskach (tylko Windows)
        if os.name == "nt":
            abs_drive = os.path.splitdrive(norm_abs_path)[0].lower()
            base_drive = os.path.splitdrive(norm_base_path)[0].lower()
            if abs_drive and base_drive and abs_drive != base_drive:
                logger.error(
                    f"Nie można utworzyć ścieżki względnej: ścieżki są na różnych dyskach. "
                    f"Ścieżka: {norm_abs_path}, Baza: {norm_base_path}"
                )
                return None

        rel_path = os.path.relpath(norm_abs_path, norm_base_path)
        return normalize_path(rel_path)  # Normalizujemy wynikową ścieżkę względną
    except ValueError as ve:
        # ValueError może być nadal zgłaszany przez os.path.relpath w pewnych skrajnych przypadkach,
        # chociaż sprawdzenie dysków powinno pokryć najczęstszy scenariusz.
        logger.error(
            f"Błąd wartości podczas konwersji ścieżki {absolute_path} względem {base_path}: {ve}. "
            f"Możliwy problem z różnymi dyskami w systemie Windows lub nieprawidłowymi ścieżkami."
        )
        return None
    except Exception as e:
        logger.error(
            f"Nieoczekiwany błąd konwersji ścieżki {absolute_path} względem {base_path}: {e}",
            exc_info=True,
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
        logger.error(
            f"Błąd konwersji ścieżki względnej {relative_path} względem {base_path}: {e}",
            exc_info=True,
        )
        return None


def _validate_metadata_structure(metadata: Dict[str, Any]) -> bool:
    """
    Waliduje podstawową strukturę wczytanych metadanych.
    Sprawdza obecność i typy kluczowych pól.
    """
    if not isinstance(metadata, dict):
        logger.error("Metadane nie są słownikiem.")
        return False

    required_keys = {
        "file_pairs": dict,
        "unpaired_archives": list,
        "unpaired_previews": list,
    }

    for key, expected_type in required_keys.items():
        if key not in metadata:
            logger.warning(
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
            logger.error(
                f"Nieprawidłowy typ dla klucza '{key}' w metadanych. "
                f"Oczekiwano {expected_type.__name__}, otrzymano {type(metadata[key]).__name__}."
            )
            return False  # Błąd struktury jest poważny

    # Walidacja struktury wewnątrz 'file_pairs'
    if "file_pairs" in metadata and isinstance(metadata["file_pairs"], dict):
        for pair_key, pair_data in metadata["file_pairs"].items():
            if not isinstance(pair_data, dict):
                logger.error(
                    f"Nieprawidłowy format danych dla pary plików '{pair_key}'. Oczekiwano słownika."
                )
                return False
            # Można dodać bardziej szczegółową walidację pól wewnątrz pair_data, np. stars
            if "stars" in pair_data and not isinstance(pair_data["stars"], int):
                logger.warning(f"Nieprawidłowy typ dla 'stars' w parze '{pair_key}'.")
            if "color_tag" in pair_data and not (
                isinstance(pair_data["color_tag"], str)
                or pair_data["color_tag"] is None
            ):
                logger.warning(
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
        logger.error(
            f"Nie można utworzyć katalogu metadanych {os.path.dirname(metadata_path)}: {e}",
            exc_info=True,
        )
        return default_metadata  # Nie można kontynuować bez katalogu

    # Wyłączamy blokadę plików - powoduje niepotrzebne opóźnienia
    # lock = FileLock(lock_path, timeout=LOCK_TIMEOUT)

    try:
        # with lock:  # Zakomentowane - bez blokady
        if not os.path.exists(metadata_path):
            logger.debug(
                f"Plik metadanych nie istnieje: {metadata_path}. Zwracam domyślne."
            )
            return default_metadata

        with open(metadata_path, "r", encoding="utf-8") as file:
            metadata = json.load(file)
            logger.debug(f"Wczytano metadane z {metadata_path}")

        if not _validate_metadata_structure(metadata):
            logger.warning(
                f"Struktura metadanych w {metadata_path} jest nieprawidłowa. Zwracam domyślne."
            )
            return default_metadata

        return metadata
    except (
        Timeout
    ):  # Ten wyjątek nie powinien wystąpić, jeśli FileLock jest zakomentowany
        logger.error(
            f"Nie można uzyskać blokady pliku metadanych {lock_path} w ciągu {LOCK_TIMEOUT}s.",
            exc_info=True,
        )
        return default_metadata
    except json.JSONDecodeError as e:
        logger.error(
            f"Błąd parsowania JSON w pliku metadanych {metadata_path}: {e}. Zwracam domyślne.",
            exc_info=True,
        )
        # Można rozważyć próbę odzyskania z kopii zapasowej, jeśli istnieje
        return default_metadata
    except Exception as e:
        logger.error(
            f"Nieoczekiwany błąd wczytywania metadanych z {metadata_path}: {e}. Zwracam domyślne.",
            exc_info=True,
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
    logger.info(f"Rozpoczęcie zapisu metadanych dla katalogu: {working_directory}")
    logger.debug(f"Liczba par plików do przetworzenia: {len(file_pairs_list)}")

    metadata_path = get_metadata_path(working_directory)
    lock_path = get_lock_path(
        working_directory
    )  # Potencjalnie nieużywane, jeśli blokada wyłączona
    metadata_dir = os.path.dirname(metadata_path)

    logger.debug(f"Ścieżka do pliku metadanych: {metadata_path}")
    logger.debug(f"Katalog metadanych: {metadata_dir}")

    # Wyłączamy blokadę plików - powoduje niepotrzebne opóźnienia
    # lock = FileLock(lock_path, timeout=LOCK_TIMEOUT)

    try:
        # with lock:  # Zakomentowane - bez blokady
        os.makedirs(metadata_dir, exist_ok=True)
        logger.debug(f"Katalog metadanych '{metadata_dir}' sprawdzony/utworzony.")

        # Wczytanie istniejących metadanych, aby nie nadpisać innych informacji,
        # jeśli plik metadanych zawierałby więcej niż tylko te trzy klucze.
        # Jednak obecna logika load_metadata i tak zwraca tylko te klucze lub domyślne.
        # Dla bezpieczeństwa i przyszłej rozbudowy, lepiej wczytać.
        current_metadata = load_metadata(working_directory)
        logger.debug("Istniejące metadane wczytane przed zapisem.")

        # Przygotowanie danych do zapisu dla sparowanych plików
        # Używamy słownika do przechowywania metadanych par, aby łatwiej aktualizować
        # i unikać duplikatów, jeśli file_pairs_list zawierałoby je.
        updated_file_pairs_metadata = current_metadata.get("file_pairs", {})

        logger.debug(f"Przetwarzanie {len(file_pairs_list)} par plików do zapisu...")

        for file_pair in file_pairs_list:
            # Sprawdzamy, czy obiekt ma wymagane atrybuty/metody
            if not all(
                hasattr(file_pair, attr)
                for attr in [
                    "archive_path",
                    "get_stars",
                    "get_color_tag",
                    "get_base_name",  # Dodano dla lepszego logowania
                ]
            ):
                logger.warning(
                    f"Pominięto obiekt w file_pairs_list - brak wymaganych atrybutów: {file_pair}"
                )
                continue

            relative_archive_path = get_relative_path(
                file_pair.archive_path, working_directory
            )
            if relative_archive_path is None:
                logger.warning(
                    f"Nie można uzyskać ścieżki względnej dla {file_pair.archive_path} (nazwa bazowa: {file_pair.get_base_name()}). "
                    "Pomijam zapis metadanych dla tej pary."
                )
                continue

            pair_metadata = {
                "stars": file_pair.get_stars(),
                "color_tag": file_pair.get_color_tag(),
            }
            updated_file_pairs_metadata[relative_archive_path] = pair_metadata

            logger.debug(
                f"Przygotowano metadane dla '{relative_archive_path}' (nazwa bazowa: {file_pair.get_base_name()}): "
                f"stars={file_pair.get_stars()}, color_tag='{file_pair.get_color_tag()}'"
            )

        current_metadata["file_pairs"] = updated_file_pairs_metadata

        # Przygotowanie i zapis list niesparowanych plików
        current_metadata["unpaired_archives"] = []
        for p in unpaired_archives:
            rel_p = get_relative_path(p, working_directory)
            if rel_p is not None:
                current_metadata["unpaired_archives"].append(rel_p)
            else:
                logger.warning(
                    f"Nie można uzyskać ścieżki względnej dla niesparowanego archiwum: {p}. Pomijam."
                )

        current_metadata["unpaired_previews"] = []
        for p in unpaired_previews:
            rel_p = get_relative_path(p, working_directory)
            if rel_p is not None:
                current_metadata["unpaired_previews"].append(rel_p)
            else:
                logger.warning(
                    f"Nie można uzyskać ścieżki względnej dla niesparowanego podglądu: {p}. Pomijam."
                )
        logger.debug(
            f"Liczba niesparowanych archiwów do zapisu: {len(current_metadata['unpaired_archives'])}. "
            f"Liczba niesparowanych podglądów do zapisu: {len(current_metadata['unpaired_previews'])}."
        )
        # Atomowy zapis: najpierw do pliku tymczasowego, potem zamiana
        temp_file_path = ""  # Inicjalizacja zmiennej
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
        logger.info(f"Pomyślnie zapisano metadane do {metadata_path}")
        return True

    except (
        Timeout
    ):  # Ten wyjątek nie powinien wystąpić, jeśli FileLock jest zakomentowany
        logger.error(
            f"Nie można uzyskać blokady pliku metadanych {lock_path} w ciągu {LOCK_TIMEOUT}s podczas zapisu.",
            exc_info=True,
        )
        return False
    except Exception as e:
        logger.error(
            f"Błąd zapisywania metadanych do {metadata_path}: {e}", exc_info=True
        )
        # Usuń plik tymczasowy, jeśli istnieje i wystąpił błąd po jego utworzeniu
        if (
            "temp_file_path" in locals()
            and temp_file_path
            and os.path.exists(temp_file_path)
        ):
            try:
                os.remove(temp_file_path)
                logger.debug(
                    f"Usunięto tymczasowy plik metadanych {temp_file_path} po błędzie zapisu."
                )
            except OSError as remove_err:
                logger.error(
                    f"Nie można usunąć tymczasowego pliku metadanych {temp_file_path} po błędzie: {remove_err}",
                    exc_info=True,
                )
        return False


def save_file_pair_metadata(file_pair, working_directory: str) -> bool:
    """
    Zapisuje metadane dla pojedynczej pary plików, zachowując istniejące metadane.
    
    Args:
        file_pair: Obiekt FilePair do zapisania metadanych
        working_directory: Katalog roboczy
        
    Returns:
        bool: True jeśli zapisano pomyślnie, False w przypadku błędu
    """
    try:
        # Wczytaj aktualne metadane aby zachować istniejące dane
        current_metadata = load_metadata(working_directory)
        
        # Pobierz ścieżkę względną dla pliku archiwum
        relative_archive_path = get_relative_path(file_pair.archive_path, working_directory)
        if relative_archive_path is None:
            logger.warning(f"Nie można uzyskać ścieżki względnej dla {file_pair.archive_path}")
            return False
        
        # Pobierz istniejące metadane par plików
        file_pairs_metadata = current_metadata.get("file_pairs", {})
        
        # Aktualizuj metadane dla tej konkretnej pary
        file_pairs_metadata[relative_archive_path] = {
            "stars": file_pair.get_stars(),
            "color_tag": file_pair.get_color_tag(),
        }
        
        # Zapisz z zachowaniem struktury
        updated_metadata = current_metadata.copy()
        updated_metadata["file_pairs"] = file_pairs_metadata
        
        # Zapisz do pliku
        metadata_path = get_metadata_path(working_directory)
        metadata_dir = os.path.dirname(metadata_path)
        os.makedirs(metadata_dir, exist_ok=True)
        
        # Atomowy zapis przez plik tymczasowy
        import tempfile
        import shutil
        import json
        
        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            encoding="utf-8",
            dir=metadata_dir,
            suffix=".tmp",
        ) as temp_file:
            json.dump(updated_metadata, temp_file, ensure_ascii=False, indent=4)
            temp_file_path = temp_file.name
        
        # Zastąp docelowy plik
        shutil.move(temp_file_path, metadata_path)
        logger.info(f"Zapisano metadane dla pary: {relative_archive_path}")
        return True
        
    except Exception as e:
        logger.error(f"Błąd podczas zapisywania metadanych dla pojedynczej pary: {e}", exc_info=True)
        return False


def apply_metadata_to_file_pairs(working_directory: str, file_pairs_list: List) -> bool:
    """
    Aktualizuje obiekty FilePair na podstawie metadanych z pliku JSON.
    OPTYMALIZACJA: Cache dla normalizowanych ścieżek bazowych.

    Args:
        working_directory (str): Ścieżka do folderu roboczego.
        file_pairs_list (List): Lista obiektów FilePair do aktualizacji.

    Returns:
        bool: True jeśli aktualizacja przebiegła pomyślnie, False w przypadku błędu.
    """
    try:
        metadata = load_metadata(working_directory)  # load_metadata obsługuje blokadę

        if not metadata or "file_pairs" not in metadata or not metadata["file_pairs"]:
            logger.debug(
                "Brak metadanych par plików do zastosowania lub błąd wczytywania. "
                f"(Katalog: {working_directory})"
            )
            # Jeśli load_metadata zwróciło domyślne (puste) metadane, to jest to normalne, jeśli plik nie istniał.
            # Jeśli był błąd, load_metadata już to zalogowało.
            return True  # Traktujemy to jako "sukces" w sensie braku danych do przetworzenia

        file_pairs_metadata = metadata["file_pairs"]

        logger.debug(
            f"Rozpoczynanie stosowania metadanych do {len(file_pairs_list)} par plików."
        )
        applied_count = 0

        # OPTYMALIZACJA: Cache dla normalizacji ścieżek - unikaj powtarzania
        normalized_working_dir = normalize_path(working_directory)

        # OPTYMALIZACJA: Batch processing z progress reportingiem
        total_files = len(file_pairs_list)
        batch_size = 50  # Przetwarzaj w batches dla lepszego progressu

        for i, file_pair in enumerate(file_pairs_list):
            # Progress reporting co batch_size plików
            if i % batch_size == 0:
                logger.debug(f"Przetwarzanie metadanych: {i}/{total_files} plików...")

            if not all(
                hasattr(file_pair, attr)
                for attr in [
                    "archive_path",
                    "get_stars",
                    "set_stars",
                    "get_color_tag",
                    "set_color_tag",
                    "get_base_name",  # Kluczowe dla identyfikacji
                ]
            ):
                logger.warning(
                    f"Pominięto obiekt w file_pairs_list przy stosowaniu metadanych - brak wymaganych atrybutów: {file_pair}"
                )
                continue

            # OPTYMALIZACJA: Użyj prostszego sposobu na obliczenie ścieżki względnej
            # zamiast pełnej get_relative_path która robi zbyt dużo pracy
            try:
                normalized_archive_path = normalize_path(file_pair.archive_path)
                relative_archive_path = os.path.relpath(
                    normalized_archive_path, normalized_working_dir
                )
                relative_archive_path = normalize_path(relative_archive_path)
            except (ValueError, OSError) as e:
                logger.warning(
                    f"Nie można uzyskać ścieżki względnej dla {file_pair.archive_path} (nazwa bazowa: {file_pair.get_base_name()}) "
                    f"podczas stosowania metadanych: {e}. Pomijam."
                )
                continue

            if relative_archive_path in file_pairs_metadata:
                pair_metadata = file_pairs_metadata[relative_archive_path]
                updated = False

                if "stars" in pair_metadata and isinstance(pair_metadata["stars"], int):
                    if file_pair.get_stars() != pair_metadata["stars"]:
                        file_pair.set_stars(pair_metadata["stars"])
                        updated = True

                if "color_tag" in pair_metadata and (
                    isinstance(pair_metadata["color_tag"], str)
                    or pair_metadata["color_tag"] is None
                ):
                    if file_pair.get_color_tag() != pair_metadata["color_tag"]:
                        file_pair.set_color_tag(pair_metadata["color_tag"])
                        updated = True

                if updated:
                    applied_count += 1
                    # Zmniejsz verbose logging dla lepszej wydajności
                    if applied_count % 10 == 0:  # Log co 10 zaktualizowanych plików
                        logger.debug(
                            f"Zastosowano metadane dla {applied_count} plików (ostatni: '{relative_archive_path}')"
                        )

        logger.info(
            f"Zakończono stosowanie metadanych. Zaktualizowano {applied_count} z {len(file_pairs_list)} par plików."
        )
        return True

    except Exception as e:
        logger.error(f"Błąd stosowania metadanych do par plików: {e}", exc_info=True)
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
    lock_path = get_lock_path(working_directory)  # Nieużywane, jeśli blokada wyłączona
    # lock = FileLock(lock_path, timeout=LOCK_TIMEOUT) # Blokada wyłączona

    logger.debug(
        f"Próba usunięcia metadanych dla pliku '{relative_archive_path}' w katalogu '{working_directory}'."
    )

    try:
        # with lock: # Blokada wyłączona
        if not os.path.exists(metadata_path):
            logger.debug(
                f"Plik metadanych {metadata_path} nie istnieje. Nic do usunięcia dla '{relative_archive_path}'."
            )
            return True  # Traktujemy jako sukces, bo nie ma czego usuwać

        # Używamy wewnętrznej funkcji do wczytania, aby uniknąć problemów z zagnieżdżonymi blokadami,
        # gdyby load_metadata używało FileLock. Obecnie load_metadata nie używa blokady.
        current_metadata: Dict[str, Any] = {}
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                current_metadata = json.load(f)
            if not _validate_metadata_structure(
                current_metadata
            ):  # Walidacja po wczytaniu
                logger.warning(
                    f"Nieprawidłowa struktura metadanych w {metadata_path} podczas próby usunięcia wpisu. Próba kontynuacji."
                )
                # Jeśli struktura jest zła, możemy nie znaleźć klucza 'file_pairs'
                # lub może on nie być słownikiem. Poniższy kod powinien to obsłużyć.
        except json.JSONDecodeError:
            logger.error(
                f"Błąd dekodowania JSON w {metadata_path} podczas usuwania wpisu dla '{relative_archive_path}'. Nie można kontynuować.",
                exc_info=True,
            )
            return False  # Nie można bezpiecznie zmodyfikować uszkodzonego pliku
        except Exception as e_load:
            logger.error(
                f"Nieoczekiwany błąd wczytywania {metadata_path} podczas usuwania wpisu: {e_load}",
                exc_info=True,
            )
            return False

        if (
            "file_pairs" in current_metadata
            and isinstance(current_metadata.get("file_pairs"), dict)
            and relative_archive_path in current_metadata["file_pairs"]
        ):
            del current_metadata["file_pairs"][relative_archive_path]
            logger.info(
                f"Usunięto metadane dla pliku: {relative_archive_path} z {metadata_path}"
            )

            # Zapisz zmiany (używając logiki z save_metadata, ale uproszczonej, bo modyfikujemy tylko jeden klucz)
            # Bezpieczniej jest zapisać cały obiekt current_metadata.

            temp_file_path = ""  # Inicjalizacja zmiennej
            metadata_dir = os.path.dirname(metadata_path)
            try:
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
                logger.debug(
                    f"Pomyślnie zapisano zmiany w {metadata_path} po usunięciu wpisu."
                )
                return True
            except Exception as e_save:
                logger.error(
                    f"Błąd zapisu metadanych po usunięciu wpisu dla '{relative_archive_path}': {e_save}",
                    exc_info=True,
                )
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                        logger.debug(
                            f"Usunięto tymczasowy plik {temp_file_path} po błędzie zapisu."
                        )
                    except OSError as remove_err:
                        logger.error(
                            f"Nie można usunąć tymczasowego pliku {temp_file_path}: {remove_err}",
                            exc_info=True,
                        )
                return False
        else:
            logger.debug(
                f"Brak metadanych do usunięcia dla pliku: {relative_archive_path} w {metadata_path}"
            )
            return True  # Nic do zrobienia, więc sukces
    except (
        Timeout
    ):  # Ten wyjątek nie powinien wystąpić, jeśli FileLock jest zakomentowany
        logger.error(
            f"Timeout podczas próby usunięcia metadanych dla {relative_archive_path}.",
            exc_info=True,
        )
        return False
    except Exception as e:
        logger.error(
            f"Błąd podczas usuwania metadanych dla {relative_archive_path}: {e}",
            exc_info=True,
        )
        return False


def get_metadata_for_relative_path(
    working_directory: str, relative_archive_path: str
) -> Optional[Dict[str, Any]]:
    """
    Pobiera metadane dla pojedynczej pary plików na podstawie jej względnej ścieżki archiwum.
    """
    metadata = load_metadata(
        working_directory
    )  # load_metadata obsługuje logowanie błędów
    if (
        metadata
        and "file_pairs" in metadata
        and isinstance(metadata.get("file_pairs"), dict)
    ):
        return metadata["file_pairs"].get(relative_archive_path)
    elif not metadata:
        logger.debug(
            f"Nie udało się wczytać metadanych dla katalogu '{working_directory}' przy próbie pobrania dla '{relative_archive_path}'."
        )
    else:  # metadata istnieje, ale brakuje 'file_pairs' lub ma zły typ
        logger.debug(
            f"Klucz 'file_pairs' nie istnieje lub ma nieprawidłowy typ w metadanych dla '{working_directory}' przy próbie pobrania dla '{relative_archive_path}'."
        )
    return None
