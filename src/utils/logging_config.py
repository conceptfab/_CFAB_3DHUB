"""
Konfiguracja systemu logowania dla aplikacji.
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(log_level=logging.INFO, log_to_file=True, log_dir="logs"):
    """
    Konfiguruje system logowania aplikacji.

    Args:
        log_level (int): Poziom logowania, domyślnie INFO.
        log_to_file (bool): Czy zapisywać logi do pliku, domyślnie True.
        log_dir (str): Katalog na pliki logów, domyślnie 'logs'.
    """
    # Tworzenie formatowania dla logów
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Konfiguracja głównego loggera
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Czyszczenie istniejących handlerów
    if logger.hasHandlers():
        logger.handlers.clear()

    # Dodanie handlera konsoli
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Dodanie handlera pliku, jeśli wymagane
    if log_to_file:
        # Upewnij się, że katalog na logi istnieje
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Konfiguracja handlera plików z rotacją (max 5MB, max 5 plików)
        log_file_path = os.path.join(log_dir, "app.log")
        file_handler = RotatingFileHandler(
            log_file_path, maxBytes=5 * 1024 * 1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logging.info("System logowania zainicjalizowany")
    return logger
