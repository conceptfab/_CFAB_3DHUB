"""
Moduł odpowiedzialny za ładowanie i zarządzanie stylami QSS aplikacji.
"""

import logging
import os


def load_styles(style_path, verbose=False):
    """
    Ładuje style QSS z podanej ścieżki, obsługując różne kodowania.

    Args:
        style_path (str): Ścieżka do pliku ze stylami QSS
        verbose (bool): Czy wypisywać dodatkowe informacje na konsolę

    Returns:
        str: Zawartość pliku ze stylami lub pusty string w przypadku błędu
    """
    if not os.path.exists(style_path):
        if verbose:
            print(f"UWAGA: Nie znaleziono pliku stylów: {style_path}")
        logging.warning(f"Brak pliku stylów: {style_path}")
        return ""

    style_sheet = ""
    try:
        # Próbuj najpierw z UTF-8 (najbardziej powszechne kodowanie)
        with open(style_path, "r", encoding="utf-8") as style_file:
            style_sheet = style_file.read()
            if verbose:
                print(f"Załadowano {len(style_sheet)} bajtów stylów (UTF-8)")
            logging.debug(f"Załadowano style z: {style_path}")
    except UnicodeDecodeError:
        # Jeśli UTF-8 nie zadziała, spróbuj z UTF-16
        try:
            with open(style_path, "r", encoding="utf-16") as style_file:
                style_sheet = style_file.read()
                if verbose:
                    print(f"Załadowano {len(style_sheet)} bajtów stylów (UTF-16)")
                logging.info(f"Załadowano style z: {style_path} (UTF-16)")
        except UnicodeDecodeError:
            # Jako ostateczność, spróbuj z Latin-1 (ignoruje błędy kodowania)
            try:
                with open(style_path, "r", encoding="latin-1") as style_file:
                    style_sheet = style_file.read()
                    if verbose:
                        print(f"Załadowano {len(style_sheet)} bajtów stylów (Latin-1)")
                        print(
                            "UWAGA: Używanie awaryjnego kodowania Latin-1, mogą wystąpić problemy ze znakami specjalnymi."
                        )
                    logging.warning(
                        f"Załadowano style z awaryjnym kodowaniem Latin-1: {style_path}"
                    )
            except Exception as e:
                logging.error(f"Krytyczny błąd podczas ładowania stylów: {e}")
                return ""
    except Exception as e:
        logging.error(f"Błąd podczas ładowania stylów: {e}")
        return ""

    return style_sheet


def get_style_path(project_root, custom_path=None):
    """
    Określa ścieżkę do pliku stylów.

    Args:
        project_root (str): Katalog główny projektu
        custom_path (str, optional): Niestandardowa ścieżka do pliku stylów

    Returns:
        str: Pełna ścieżka do pliku stylów
    """
    if custom_path:
        if os.path.isabs(custom_path):
            return custom_path
        else:
            return os.path.join(project_root, custom_path)

    # Domyślne lokalizacje stylów (w kolejności sprawdzania)
    style_paths = [
        os.path.join(project_root, "styles.qss"),
        os.path.join(project_root, "src", "resources", "styles.qss"),
    ]

    # Zwróć pierwszą istniejącą ścieżkę lub domyślną z resources
    for path in style_paths:
        if os.path.exists(path):
            return path

    # Jeśli nie znaleziono, zwróć domyślną ścieżkę
    return style_paths[1]
