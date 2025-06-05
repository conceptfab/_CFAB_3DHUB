"""Narzędzia pomocnicze związane ze ścieżkami.

Ten moduł zawiera funkcje do manipulacji i walidacji ścieżek plików i folderów,
zapewniając spójność między różnymi częściami aplikacji i systemami operacyjnymi.
Obsługuje ścieżki Unicode, ścieżki UNC oraz URL-e.
"""

import os
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple, Union


def normalize_path(path: str) -> str:
    """
    Normalizuje ścieżkę, zamieniając separatory na uniwersalny '/'.
    Jest to kluczowe dla spójności między różnymi częściami aplikacji.

    Obsługuje:
    - Ścieżki Unicode
    - Ścieżki UNC (Windows Network Paths)
    - Ścieżki z różnymi separatorami

    Args:
        path: Ścieżka do normalizacji

    Returns:
        Znormalizowana ścieżka z separatorami '/'
    """
    if not path:
        return ""

    # Zachowaj ewentualne prefiksy UNC
    is_unc = False
    if (path.startswith("\\\\") or path.startswith("//")) and sys.platform == "win32":
        is_unc = True
        path = path[2:]  # Usuwamy prefiksy "//" lub "\\" tymczasowo

    # Używamy os.path.normpath, aby najpierw rozwiązać '..' itp., a potem
    # zamieniamy na forward slashes dla spójności.
    normalized = os.path.normpath(path).replace("\\", "/")

    # Przywracamy prefiksy UNC
    if is_unc:
        normalized = "//" + normalized

    # Usunięcie powtarzających się slashy (np. ////)
    while "//" in normalized and not is_unc:
        normalized = normalized.replace("//", "/")

    # Jeśli był UNC, naprawiamy początkowe //
    if is_unc and not normalized.startswith("//"):
        normalized = "//" + normalized

    return normalized


def is_path_valid(path: str) -> bool:
    """
    Sprawdza, czy podana ścieżka jest prawidłowa.

    Args:
        path: Ścieżka do sprawdzenia

    Returns:
        True jeśli ścieżka jest prawidłowa, False w przeciwnym razie
    """
    if not path:
        return False

    try:
        # Próba stworzenia obiektu Path
        Path(path)

        # Na Windows sprawdzenie nieprawidłowych znaków w ścieżce
        if sys.platform == "win32":
            forbidden_chars = r'<>:"|?*'
            # Nazwę dysku (np. C:) traktujemy specjalnie
            drive, rest = os.path.splitdrive(path)

            # Sprawdzamy tylko część po nazwie dysku
            return not any(char in rest for char in forbidden_chars)

        return True
    except Exception:
        return False


def safe_join_paths(*paths: str) -> str:
    """
    Bezpiecznie łączy części ścieżek, normalizując wynik.

    Args:
        *paths: Części ścieżki do połączenia

    Returns:
        Znormalizowana połączona ścieżka
    """
    if not paths:
        return ""

    # Usuń puste ścieżki
    filtered_paths = [p for p in paths if p]

    if not filtered_paths:
        return ""

    # Specjalne traktowanie dla ścieżek dyskowych na Windows
    if (
        sys.platform == "win32"
        and filtered_paths
        and filtered_paths[0]
        and filtered_paths[0].endswith(":")
    ):
        # Dla ścieżek typu "C:" dodajemy separatory
        filtered_paths[0] = filtered_paths[0] + os.sep

    # Łączenie ścieżek
    joined = os.path.join(*filtered_paths)

    # Normalizacja wynikowej ścieżki
    return normalize_path(joined)


def is_absolute(path: str) -> bool:
    """
    Sprawdza, czy ścieżka jest absolutna.

    Args:
        path: Ścieżka do sprawdzenia

    Returns:
        True jeśli ścieżka jest absolutna, False w przeciwnym razie
    """
    if not path:
        return False
    return os.path.isabs(path)


def to_absolute_path(path: str, base_path: Optional[str] = None) -> str:
    """
    Konwertuje ścieżkę względną do absolutnej.

    Args:
        path: Ścieżka do konwersji
        base_path: Ścieżka bazowa dla ścieżek względnych. Jeśli nie podano,
                   używa bieżącego katalogu.

    Returns:
        Absolutna ścieżka
    """
    if not path:
        return ""

    # Jeśli ścieżka już jest absolutna, zwróć ją po normalizacji
    if is_absolute(path):
        return normalize_path(path)

    # Jeśli nie podano ścieżki bazowej, użyj bieżącego katalogu
    if base_path is None:
        base_path = os.getcwd()

    # Łączenie i normalizacja
    return normalize_path(os.path.join(base_path, path))


def to_relative_path(path: str, base_path: str) -> str:
    """
    Konwertuje ścieżkę absolutną do względnej.

    Args:
        path: Ścieżka do konwersji
        base_path: Ścieżka bazowa względem której ma być obliczona ścieżka względna

    Returns:
        Względna ścieżka
    """
    if not path or not base_path:
        return path

    # Normalizacja ścieżek do porównania
    norm_path = normalize_path(path)
    norm_base = normalize_path(base_path)

    # Próba obliczenia ścieżki względnej
    try:
        rel_path = os.path.relpath(norm_path, norm_base)
        return normalize_path(rel_path)
    except ValueError:
        # W przypadku różnych dysków/urządzeń, zwracamy oryginalną ścieżkę
        return norm_path


def is_url(path: str) -> bool:
    """
    Sprawdza, czy podana ścieżka jest URL-em.

    Args:
        path: Ścieżka do sprawdzenia

    Returns:
        True jeśli ścieżka jest URL-em, False w przeciwnym razie
    """
    if not path:
        return False

    parsed = urllib.parse.urlparse(path)
    return bool(parsed.scheme and parsed.netloc)


def is_unc_path(path: str) -> bool:
    """
    Sprawdza, czy podana ścieżka jest ścieżką UNC (Universal Naming Convention).

    Args:
        path: Ścieżka do sprawdzenia

    Returns:
        True jeśli ścieżka jest ścieżką UNC, False w przeciwnym razie
    """
    if not path:
        return False

    # UNC ścieżki zaczynają się od "\\" lub "//" na Windows
    if sys.platform == "win32":
        return path.startswith("\\\\") or path.startswith("//")

    return False


def get_path_type(path: str) -> str:
    """
    Określa typ ścieżki: 'file', 'url', 'unc' lub 'invalid'.

    Args:
        path: Ścieżka do sprawdzenia

    Returns:
        Typ ścieżki jako string
    """
    if not path:
        return "invalid"

    if is_url(path):
        return "url"

    if is_unc_path(path):
        return "unc"

    if is_path_valid(path):
        return "file"

    return "invalid"


def path_exists(path: str) -> bool:
    """
    Sprawdza, czy podana ścieżka istnieje w systemie plików.

    Args:
        path: Ścieżka do sprawdzenia

    Returns:
        True jeśli ścieżka istnieje, False w przeciwnym razie
    """
    if not path:
        return False

    # Jeśli to URL, traktujemy jako nieistniejący (nie sprawdzamy)
    if is_url(path):
        return False

    # Dla innych typów ścieżek sprawdzamy istnienie
    return os.path.exists(path)


def parse_url(url: str) -> Tuple[str, str, str]:
    """
    Parsuje URL na składowe: protokół, host i ścieżkę.

    Args:
        url: URL do przetworzenia

    Returns:
        Krotka (protokół, host, ścieżka)
    """
    if not url:
        return ("", "", "")

    try:
        parsed = urllib.parse.urlparse(url)
        # Specjalny przypadek dla "http://" - zatrzymujemy schemat
        if parsed.scheme and not parsed.netloc and url.endswith("://"):
            return (parsed.scheme, "", "")
        # Jeśli nie ma schematu lub netloc, to prawdopodobnie nie jest prawidłowy URL
        if not parsed.scheme or not parsed.netloc:
            # Dla schematów specjalnych bez netloc (e.g. "file:///path")
            if parsed.scheme == "file" and parsed.path:
                return ("file", "", parsed.path)
            if not is_url(url):
                return ("", "", "")
        return (parsed.scheme, parsed.netloc, parsed.path)
    except Exception:
        return ("", "", "")


def get_directory_name(path: str) -> str:
    """
    Zwraca nazwę katalogu (ostatni element ścieżki) dla ścieżki katalogu.

    Args:
        path: Ścieżka katalogu

    Returns:
        Nazwa katalogu
    """
    if not path:
        return ""

    # Normalizacja i usunięcie końcowego slasha
    norm_path = normalize_path(path.rstrip("/\\"))

    # Pobieramy ostatni element ścieżki
    return os.path.basename(norm_path)


def is_valid_filename(filename: str) -> bool:
    """
    Sprawdza, czy podana nazwa pliku jest prawidłowa.

    Reguły walidacji:
    - Nazwa nie może być pusta
    - Nazwa nie może zawierać znaków niedozwolonych w systemie

    Args:
        filename: Nazwa pliku do sprawdzenia (bez ścieżki)

    Returns:
        True jeśli nazwa jest prawidłowa, False w przeciwnym razie
    """
    if not filename or not filename.strip():
        return False

    # Znaki niedozwolone w nazwach plików (dla większości systemów)
    forbidden_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]

    # Sprawdzenie czy któryś z niedozwolonych znaków występuje w nazwie
    return not any(char in filename for char in forbidden_chars)


def get_parent_directory(path: str) -> str:
    """
    Zwraca ścieżkę do katalogu nadrzędnego.

    Args:
        path: Ścieżka do pliku lub katalogu

    Returns:
        Ścieżka do katalogu nadrzędnego
    """
    if not path:
        return ""

    # Normalizacja ścieżki
    norm_path = normalize_path(path)

    # Ustalenie katalogu nadrzędnego
    parent = os.path.dirname(norm_path)

    # Specjalne traktowanie głównego katalogu dysku Windows
    if sys.platform == "win32" and norm_path.endswith(":"):
        return norm_path
    elif sys.platform == "win32" and norm_path.endswith(":/"):
        return norm_path[:-1]

    return normalize_path(parent)
