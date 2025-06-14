"""
ConfigIO - operacje I/O konfiguracji.
🚀 ETAP 2: Refaktoryzacja AppConfig - komponent operacji I/O
"""

import json
import logging
import os
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from src.utils.path_utils import normalize_path
from .config_defaults import ConfigDefaults
from .config_validator import ConfigValidator

logger = logging.getLogger(__name__)


class ConfigIO:
    """
    Operacje I/O dla konfiguracji.
    
    Odpowiedzialności:
    - Ładowanie konfiguracji z pliku
    - Zapisywanie konfiguracji do pliku
    - Asynchroniczne zapisywanie z debouncing
    - Tworzenie kopii zapasowych
    - Obsługa błędów I/O
    """

    def __init__(self, config_dir: str = None, config_file: str = None):
        """
        Inicjalizuje ConfigIO.
        
        Args:
            config_dir: Katalog konfiguracji
            config_file: Nazwa pliku konfiguracji
        """
        # Konfiguracja ścieżek
        self._config_file_name = config_file or "config.json"
        self._app_data_dir = config_dir or os.path.join(
            os.path.expanduser("~"), ".CFAB_3DHUB"
        )
        self._config_file_path = normalize_path(
            os.path.join(self._app_data_dir, self._config_file_name)
        )

        # Async save components
        self._save_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="config_save"
        )
        self._save_lock = threading.Lock()
        self._save_future = None

        # Flaga informująca czy konfiguracja została wczytana z domyślnych wartości z powodu błędu
        self._config_loaded_from_defaults = False

    def load_config(self) -> Dict[str, Any]:
        """
        Wczytuje konfigurację z pliku JSON z walidacją.

        Returns:
            Konfiguracja aplikacji
        """
        if not os.path.exists(self._config_file_path):
            logger.debug(
                f"Plik konfiguracyjny nie istnieje: {self._config_file_path}. Używam domyślnych ustawień."
            )
            return ConfigDefaults.get_default_config()

        try:
            with open(self._config_file_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Validate and fix config
            config = ConfigValidator.validate(config)

            # Uzupełnij brakujące klucze
            updated = False
            default_config = ConfigDefaults.get_default_config()
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
                    updated = True

            if updated:
                logger.info("Zaktualizowano konfigurację o nowe parametry domyślne.")

            return config

        except Exception as e:
            logger.error(
                f"Błąd wczytywania konfiguracji: {e}. Używam domyślnych ustawień."
            )
            self._config_loaded_from_defaults = True
            return ConfigDefaults.get_default_config()

    def save_config_sync(self, config: Dict[str, Any]) -> bool:
        """
        Synchroniczne zapisywanie konfiguracji.
        
        Args:
            config: Konfiguracja do zapisania
            
        Returns:
            True jeśli zapisano pomyślnie
        """
        try:
            # Tworzenie katalogu konfiguracyjnego (z obsługą błędów uprawnień)
            try:
                os.makedirs(self._app_data_dir, exist_ok=True)
            except (PermissionError, OSError) as e:
                logger.error(f"Nie można utworzyć katalogu konfiguracyjnego: {e}")
                return False

            # Jeśli ostatnio załadowano domyślną konfigurację z powodu błędu, a plik istnieje,
            # utwórz kopię zapasową pliku przed zapisem
            if self._config_loaded_from_defaults and os.path.exists(
                self._config_file_path
            ):
                backup_path = f"{self._config_file_path}.bak"
                try:
                    shutil.copy2(self._config_file_path, backup_path)
                    logger.info(f"Utworzono kopię zapasową konfiguracji: {backup_path}")
                except (IOError, PermissionError) as e:
                    logger.warning(
                        f"Nie udało się utworzyć kopii zapasowej konfiguracji: {e}"
                    )

            # Zapisywanie pliku konfiguracyjnego
            with open(self._config_file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)

            # Po pomyślnym zapisie, resetujemy flagę
            self._config_loaded_from_defaults = False
            logger.debug(f"Konfiguracja zapisana do: {self._config_file_path}")
            return True

        except IOError as e:
            logger.error(f"Błąd zapisu konfiguracji: {e}")
            return False

    def schedule_async_save(self, config: Dict[str, Any]):
        """
        Planuje asynchroniczne zapisanie z debouncing.
        
        Args:
            config: Konfiguracja do zapisania
        """
        with self._save_lock:
            # Anuluj poprzedni zapis jeśli oczekuje
            if self._save_future and not self._save_future.done():
                self._save_future.cancel()

            # Zaplanuj nowy zapis z opóźnieniem 500ms
            self._save_future = self._save_executor.submit(self._delayed_save, config)

    def _delayed_save(self, config: Dict[str, Any]) -> bool:
        """
        Opóźnione zapisywanie z debouncing.
        
        Args:
            config: Konfiguracja do zapisania
            
        Returns:
            True jeśli zapisano pomyślnie
        """
        time.sleep(0.5)  # 500ms debounce

        try:
            return self.save_config_sync(config)
        except Exception as e:
            logger.error(f"Asynchroniczny zapis konfiguracji nieudany: {e}")
            return False

    def get_config_file_path(self) -> str:
        """
        Pobiera ścieżkę do pliku konfiguracji.
        
        Returns:
            Ścieżka do pliku konfiguracji
        """
        return self._config_file_path

    def config_file_exists(self) -> bool:
        """
        Sprawdza czy plik konfiguracji istnieje.
        
        Returns:
            True jeśli plik istnieje
        """
        return os.path.exists(self._config_file_path)

    def cleanup(self):
        """
        Czyści zasoby (zamyka executor).
        """
        if hasattr(self, '_save_executor'):
            self._save_executor.shutdown(wait=True) 