"""
Moduł odpowiedzialny za parsowanie argumentów linii poleceń aplikacji.
"""

import argparse
import logging
import os
import sys


def parse_args():
    """
    Parsuje argumenty linii poleceń i zwraca obiekt z argumentami.

    Returns:
        argparse.Namespace: Obiekt zawierający wszystkie argumenty linii poleceń
    """
    parser = argparse.ArgumentParser(
        description="CFAB_3DHUB - Aplikacja do zarządzania modelami 3D",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Podstawowe opcje aplikacji
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Włącz tryb debugowania z dodatkowymi logami",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Poziom logowania aplikacji",
    )

    parser.add_argument(
        "--no-file-log", action="store_true", help="Wyłącz zapisywanie logów do pliku"
    )

    parser.add_argument(
        "--log-dir", type=str, default="logs", help="Katalog na pliki logów"
    )

    # Opcje stylu
    parser.add_argument(
        "--style", type=str, help="Ścieżka do niestandardowego pliku QSS ze stylami"
    )

    parser.add_argument(
        "--no-style", action="store_true", help="Uruchom aplikację bez ładowania stylów"
    )

    # Opcje pomocnicze
    parser.add_argument(
        "--version", action="store_true", help="Wyświetl wersję aplikacji i zakończ"
    )

    # Parsuj argumenty
    args = parser.parse_args()

    return args


def setup_logging_from_args(args):
    """
    Konfiguruje system logowania na podstawie argumentów linii poleceń.

    Args:
        args (argparse.Namespace): Sparsowane argumenty linii poleceń
    """
    from src.utils.logging_config import setup_logging

    # Konwersja nazwy poziomu logowania na wartość numeryczną
    log_level = getattr(logging, args.log_level)

    # Konfiguracja systemu logowania
    setup_logging(
        log_level=log_level, log_to_file=not args.no_file_log, log_dir=args.log_dir
    )

    # Dodatkowa konfiguracja dla trybu debug
    if args.debug:
        logging.getLogger("src.logic.scanner").setLevel(logging.DEBUG)
        logging.info("Tryb debugowania włączony - szczegółowe logi skanowania")


def get_app_version():
    """
    Pobiera wersję aplikacji z pliku (jeśli istnieje) lub zwraca wersję domyślną.

    Returns:
        str: Wersja aplikacji
    """
    version_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "VERSION",
    )

    try:
        if os.path.exists(version_file):
            with open(version_file, "r") as f:
                return f.read().strip()
    except Exception as e:
        logging.warning(f"Nie udało się odczytać wersji aplikacji: {e}")

    return "1.0.0"  # Domyślna wersja
