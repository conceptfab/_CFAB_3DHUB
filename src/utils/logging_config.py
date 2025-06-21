"""
Konfiguracja systemu logowania dla aplikacji.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
import re
from typing import Optional


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
            log_file_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logging.debug("System logowania zainicjalizowany")
    return logger


class OptimizedLogger:
    """
    Zoptymalizowany logger bez emoji dla main_window.
    Eliminuje problemy wydajnościowe i spam logów z emoji.
    """
    
    def __init__(self, name: str = "MainWindow"):
        self.logger = logging.getLogger(name)
        self.use_emoji = False  # Domyślnie bez emoji
        self._setup_logger()
        
        # Regex do usuwania emoji
        self._emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251"
            "\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF"
            "\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF]+",
            flags=re.UNICODE
        )

    def _setup_logger(self):
        """Konfiguracja loggera bez emoji dla wydajności."""
        # Sprawdź czy handler już istnieje
        if self.logger.handlers:
            return
            
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'  # Krótszy timestamp dla wydajności
        )

        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _clean_message(self, message: str) -> str:
        """Usuwa emoji z tekstu dla wydajności."""
        if not isinstance(message, str):
            return str(message)
            
        # Usuń emoji dla wydajności
        clean_message = self._emoji_pattern.sub('', message).strip()
        
        # Usuń nadmiarowe spacje
        clean_message = ' '.join(clean_message.split())
        
        return clean_message if clean_message else message

    def info(self, message: str):
        """Log info bez emoji."""
        self.logger.info(self._clean_message(message))

    def debug(self, message: str):
        """Log debug bez emoji."""
        self.logger.debug(self._clean_message(message))

    def warning(self, message: str):
        """Log warning bez emoji."""
        self.logger.warning(self._clean_message(message))

    def error(self, message: str):
        """Log error bez emoji."""
        self.logger.error(self._clean_message(message))

    def critical(self, message: str):
        """Log critical bez emoji."""
        self.logger.critical(self._clean_message(message))


# Singleton instance dla main_window
_main_window_logger: Optional[OptimizedLogger] = None


def get_main_window_logger() -> OptimizedLogger:
    """Zwraca singleton instance OptimizedLogger dla main_window."""
    global _main_window_logger
    if _main_window_logger is None:
        _main_window_logger = OptimizedLogger("MainWindow")
    return _main_window_logger
