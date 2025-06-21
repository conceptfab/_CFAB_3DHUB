"""
ConfigCore - główna klasa konfiguracji.
🚀 ETAP 4: Refaktoryzacja - uproszczenie architektury i thread safety
"""

import logging
import threading
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from .config_defaults import ConfigDefaults
from .config_io import ConfigIO
from .config_properties import ConfigProperties

logger = logging.getLogger(__name__)


class AppConfig:
    """
    Klasa zarządzająca konfiguracją aplikacji z thread-safe singleton pattern.
    🚀 ETAP 4: Zrefaktoryzowana - uproszczona architektura

    Umożliwia odczyt i zapis parametrów konfiguracyjnych,
    z walidacją danych i obsługą błędów.

    Komponenty:
    - ConfigDefaults: domyślne wartości
    - ConfigIO: operacje I/O
    - ConfigProperties: właściwości i gettery/settery
    """

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    # Property mapping jako class attribute (optymalizacja)
    _PROPERTY_MAP = {
        "min_thumbnail_size": "min_thumbnail_size",
        "max_thumbnail_size": "max_thumbnail_size",
        "scanner_max_cache_entries": "scanner_max_cache_entries",
        "scanner_max_cache_age_seconds": "scanner_max_cache_age_seconds",
        "thumbnail_cache_max_entries": "thumbnail_cache_max_entries",
        "thumbnail_cache_max_memory_mb": "thumbnail_cache_max_memory_mb",
        "thumbnail_cache_enable_disk": "thumbnail_cache_enable_disk",
        "thumbnail_cache_cleanup_threshold": ("thumbnail_cache_cleanup_threshold"),
        "window_min_width": "window_min_width",
        "window_min_height": "window_min_height",
        "resize_timer_delay_ms": "resize_timer_delay_ms",
        "progress_hide_delay_ms": "progress_hide_delay_ms",
        "thread_wait_timeout_ms": "thread_wait_timeout_ms",
        "preferences_status_display_ms": "preferences_status_display_ms",
        "supported_archive_extensions": "supported_archive_extensions",
        "supported_preview_extensions": "supported_preview_extensions",
        "default_thumbnail_size": "thumbnail_size",
    }

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(
        self, config_dir: Optional[str] = None, config_file: Optional[str] = None
    ) -> None:
        """
        Inicjalizuje obiekt konfiguracji.

        Args:
            config_dir: Katalog konfiguracji. Jeśli None, używa domyślny.
            config_file: Nazwa pliku konfiguracji. Jeśli None, używa domyślny.

        Raises:
            ValueError: Jeśli parametry są nieprawidłowe
            OSError: Jeśli nie można utworzyć/odczytać pliku konfiguracji
        """
        with self._lock:
            if self._initialized:
                return

            # Walidacja parametrów inicjalizacji
            if config_dir is not None and not isinstance(config_dir, str):
                raise ValueError("config_dir musi być stringiem lub None")
            if config_file is not None and not isinstance(config_file, str):
                raise ValueError("config_file musi być stringiem lub None")

            try:
                # Inicjalizacja komponentów
                self._config_io = ConfigIO(config_dir, config_file)
                self._config = self._config_io.load_config()
                self._config_properties = ConfigProperties(
                    self._config, self._config_io
                )

                self._initialized = True
                config_path = self._config_io.get_config_file_path()
                logger.debug(f"Konfiguracja wczytana z: {config_path}")

            except Exception as e:
                logger.error(f"Błąd inicjalizacji konfiguracji: {e}")
                raise

    @classmethod
    def get_instance(cls, config_path: Optional[str] = None) -> "AppConfig":
        """
        Pobiera thread-safe singleton instancję konfiguracji.

        Args:
            config_path: Ścieżka do katalogu konfiguracji
                (ignorowana dla istniejącej instancji)

        Returns:
            Instancja AppConfig
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __getattr__(self, name: str) -> Any:
        """
        Dynamic property access for config values.
        Używa class attribute dla lepszej wydajności.
        """
        if name in self._PROPERTY_MAP:
            config_key = self._PROPERTY_MAP[name]
            return self.get(config_key, ConfigDefaults.get_default_value(config_key))

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )

    # --- Core methods (uproszczone) ---

    def get(self, key: str, default: Any = None) -> Any:
        """
        Pobiera wartość konfiguracji.

        Args:
            key: Klucz konfiguracji.
            default: Wartość domyślna jeśli klucz nie istnieje.

        Returns:
            Wartość konfiguracji lub default.
        """
        return self._config_properties.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """
        Ustawia wartość konfiguracji.

        Args:
            key: Klucz konfiguracji.
            value: Nowa wartość.

        Returns:
            True jeśli wartość została ustawiona.
        """
        return self._config_properties.set(key, value)

    def save(self) -> bool:
        """
        Zapisuje konfigurację do pliku.

        Returns:
            True jeśli zapisano pomyślnie.
        """
        try:
            return self._config_io.save_config_sync(self._config)
        except Exception as e:
            logger.error(f"Błąd zapisu konfiguracji: {e}")
            return False

    def reload(self) -> bool:
        """
        Przeładowuje konfigurację z pliku.

        Returns:
            True jeśli przeładowano pomyślnie.
        """
        try:
            with self._lock:
                self._config = self._config_io.load_config()
                self._config_properties = ConfigProperties(
                    self._config, self._config_io
                )
                logger.debug("Konfiguracja przeładowana z pliku")
                return True
        except Exception as e:
            logger.error(f"Błąd przeładowania konfiguracji: {e}")
            return False

    def reset_to_defaults(self) -> bool:
        """
        Resetuje konfigurację do wartości domyślnych.

        Returns:
            True jeśli zresetowano pomyślnie.
        """
        try:
            with self._lock:
                self._config = ConfigDefaults.get_default_config()
                self._config_properties = ConfigProperties(
                    self._config, self._config_io
                )
                success = self._config_io.save_config_sync(self._config)
                if success:
                    logger.debug("Konfiguracja zresetowana do wartości domyślnych")
                return success
        except Exception as e:
            logger.error(f"Błąd resetowania konfiguracji: {e}")
            return False

    # --- Essential properties (explicit properties zamiast delegacji) ---

    @property
    def thumbnail_size(self) -> Tuple[int, int]:
        """Pobiera aktualny rozmiar miniaturek jako tuple (width, height)."""
        return self._config_properties.thumbnail_size

    @property
    def predefined_colors_filter(self) -> OrderedDict:
        """Pobiera kolory jako OrderedDict dla filtrów."""
        return self._config_properties.predefined_colors_filter

    @property
    def special_folders(self) -> List[str]:
        """Pobiera listę nazw folderów specjalnych."""
        return self._config_properties.special_folders

    # --- Advanced methods (delegation to ConfigProperties for complex operations) ---

    def get_supported_extensions(self, extension_type: str) -> List[str]:
        """Pobiera listę obsługiwanych rozszerzeń."""
        return self._config_properties.get_supported_extensions(extension_type)

    def set_supported_extensions(
        self, extension_type: str, extensions: List[str]
    ) -> bool:
        """Ustawia listę obsługiwanych rozszerzeń."""
        return self._config_properties.set_supported_extensions(
            extension_type, extensions
        )

    def get_predefined_colors(self) -> Dict[str, str]:
        """Pobiera słownik predefiniowanych kolorów."""
        return self._config_properties.get_predefined_colors()

    def set_predefined_colors(self, colors: Dict[str, str]) -> bool:
        """Ustawia słownik predefiniowanych kolorów."""
        return self._config_properties.set_predefined_colors(colors)

    def get_thumbnail_format(self) -> str:
        """Pobiera format miniaturek."""
        return self._config_properties.get_thumbnail_format()

    def set_thumbnail_format(self, format_name: str) -> bool:
        """Ustawia format miniaturek."""
        return self._config_properties.set_thumbnail_format(format_name)

    def get_thumbnail_quality(self) -> int:
        """Pobiera jakość kompresji miniaturek."""
        return self._config_properties.get_thumbnail_quality()

    def set_thumbnail_quality(self, quality: int) -> bool:
        """Ustawia jakość kompresji miniaturek."""
        return self._config_properties.set_thumbnail_quality(quality)

    def get_thumbnail_webp_method(self) -> int:
        """Pobiera metodę kompresji WebP."""
        return self._config_properties.get_thumbnail_webp_method()

    def set_thumbnail_webp_method(self, method: int) -> bool:
        """Ustawia metodę kompresji WebP."""
        return self._config_properties.set_thumbnail_webp_method(method)

    def get_thumbnail_preserve_transparency(self) -> bool:
        """Sprawdza czy zachowywać przezroczystość w miniaturkach."""
        return self._config_properties.get_thumbnail_preserve_transparency()

    def set_thumbnail_preserve_transparency(self, preserve: bool) -> bool:
        """Ustawia czy zachowywać przezroczystość w miniaturkach."""
        return self._config_properties.set_thumbnail_preserve_transparency(preserve)

    # --- Simplified slider and range methods ---

    def set_thumbnail_slider_position(self, position: int) -> bool:
        """Ustawia pozycję suwaka miniaturek."""
        return self._config_properties.set_thumbnail_slider_position(position)

    def get_thumbnail_slider_position(self) -> int:
        """Pobiera pozycję suwaka miniaturek."""
        return self._config_properties.get_thumbnail_slider_position()

    def set_thumbnail_size_range(self, min_size: int, max_size: int) -> bool:
        """Ustawia zakres rozmiarów miniaturek."""
        return self._config_properties.set_thumbnail_size_range(min_size, max_size)

    # --- Advanced ConfigProperties features ---

    def reset_all_to_defaults(self) -> bool:
        """Resetuje wszystkie właściwości do wartości domyślnych."""
        return self._config_properties.reset_all_to_defaults()

    def validate_all_settings(self) -> bool:
        """Waliduje wszystkie ustawienia konfiguracji."""
        return self._config_properties.validate_all_settings()

    def cleanup_invalid_settings(self) -> bool:
        """Czyści nieprawidłowe ustawienia z konfiguracji."""
        return self._config_properties.cleanup_invalid_settings()

    # --- Access to specialized property managers ---

    @property
    def thumbnail_properties(self):
        """Dostęp do managera właściwości miniaturek."""
        return self._config_properties.thumbnail_properties

    @property
    def extension_properties(self):
        """Dostęp do managera rozszerzeń plików."""
        return self._config_properties.extension_properties

    @property
    def color_properties(self):
        """Dostęp do managera kolorów."""
        return self._config_properties.color_properties

    @property
    def format_properties(self):
        """Dostęp do managera formatów."""
        return self._config_properties.format_properties
