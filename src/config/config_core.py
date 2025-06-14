"""
ConfigCore - główna klasa konfiguracji.
🚀 ETAP 2: Refaktoryzacja AppConfig - główna klasa z komponentami
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from collections import OrderedDict

from .config_defaults import ConfigDefaults
from .config_io import ConfigIO
from .config_properties import ConfigProperties
from .config_validator import ConfigValidator

logger = logging.getLogger(__name__)


class AppConfig:
    """
    Klasa zarządzająca konfiguracją aplikacji z singleton pattern.
    🚀 ETAP 2: Zrefaktoryzowana na komponenty

    Umożliwia odczyt i zapis parametrów konfiguracyjnych,
    z walidacją danych i obsługą błędów.
    
    Komponenty:
    - ConfigDefaults: domyślne wartości
    - ConfigIO: operacje I/O
    - ConfigProperties: właściwości i gettery/settery
    - ConfigValidator: walidacja
    """

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
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
        """
        if self._initialized:
            return

        self._initialized = True

        # Inicjalizacja komponentów
        self._config_io = ConfigIO(config_dir, config_file)
        self._config = self._config_io.load_config()
        self._config_properties = ConfigProperties(self._config, self._config_io)

        logger.info(f"Konfiguracja wczytana z: {self._config_io.get_config_file_path()}")

    @classmethod
    def get_instance(cls) -> "AppConfig":
        """Pobiera singleton instancję konfiguracji."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __getattr__(self, name: str) -> Any:
        """Dynamic property access for config values."""
        # Map property names to config keys
        property_map = {
            "min_thumbnail_size": "min_thumbnail_size",
            "max_thumbnail_size": "max_thumbnail_size",
            "scanner_max_cache_entries": "scanner_max_cache_entries",
            "scanner_max_cache_age_seconds": "scanner_max_cache_age_seconds",
            "thumbnail_cache_max_entries": "thumbnail_cache_max_entries",
            "thumbnail_cache_max_memory_mb": "thumbnail_cache_max_memory_mb",
            "thumbnail_cache_enable_disk": "thumbnail_cache_enable_disk",
            "thumbnail_cache_cleanup_threshold": "thumbnail_cache_cleanup_threshold",
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

        if name in property_map:
            return self.get(
                property_map[name], ConfigDefaults.get_default_value(property_map[name])
            )

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )

    # --- Delegacja do ConfigProperties ---

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

    def set_thumbnail_slider_position(self, position: int) -> bool:
        """
        Ustawia pozycję suwaka miniaturek.

        Args:
            position: Pozycja suwaka (0-100).

        Returns:
            True jeśli pozycja została ustawiona.
        """
        return self._config_properties.set_thumbnail_slider_position(position)

    def get_thumbnail_slider_position(self) -> int:
        """
        Pobiera pozycję suwaka miniaturek.

        Returns:
            Pozycja suwaka (0-100).
        """
        return self._config_properties.get_thumbnail_slider_position()

    def set_thumbnail_size_range(self, min_size: int, max_size: int) -> bool:
        """
        Ustawia zakres rozmiarów miniaturek.

        Args:
            min_size: Minimalny rozmiar miniaturek.
            max_size: Maksymalny rozmiar miniaturek.

        Returns:
            True jeśli zakres został ustawiony.
        """
        return self._config_properties.set_thumbnail_size_range(min_size, max_size)

    def get_supported_extensions(self, extension_type: str) -> List[str]:
        """
        Pobiera listę obsługiwanych rozszerzeń.

        Args:
            extension_type: Typ rozszerzeń ('archive' lub 'preview').

        Returns:
            Lista obsługiwanych rozszerzeń.
        """
        return self._config_properties.get_supported_extensions(extension_type)

    def set_supported_extensions(
        self, extension_type: str, extensions: List[str]
    ) -> bool:
        """
        Ustawia listę obsługiwanych rozszerzeń.

        Args:
            extension_type: Typ rozszerzeń ('archive' lub 'preview').
            extensions: Lista rozszerzeń.

        Returns:
            True jeśli lista została ustawiona.
        """
        return self._config_properties.set_supported_extensions(extension_type, extensions)

    def get_predefined_colors(self) -> Dict[str, str]:
        """
        Pobiera słownik predefiniowanych kolorów.

        Returns:
            Słownik kolorów {nazwa: kod_hex}.
        """
        return self._config_properties.get_predefined_colors()

    def set_predefined_colors(self, colors: Dict[str, str]) -> bool:
        """
        Ustawia słownik predefiniowanych kolorów.

        Args:
            colors: Słownik kolorów {nazwa: kod_hex}.

        Returns:
            True jeśli kolory zostały ustawione.
        """
        return self._config_properties.set_predefined_colors(colors)

    def save(self) -> bool:
        """
        Zapisuje konfigurację do pliku.

        Returns:
            True jeśli zapisano pomyślnie.
        """
        return self._config_io.save_config_sync(self._config)

    def reload(self) -> bool:
        """
        Przeładowuje konfigurację z pliku.

        Returns:
            True jeśli przeładowano pomyślnie.
        """
        try:
            self._config = self._config_io.load_config()
            self._config_properties = ConfigProperties(self._config, self._config_io)
            logger.info("Konfiguracja przeładowana z pliku")
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
            self._config = ConfigDefaults.get_default_config()
            self._config_properties = ConfigProperties(self._config, self._config_io)
            self._config_io.save_config_sync(self._config)
            logger.info("Konfiguracja zresetowana do wartości domyślnych")
            return True
        except Exception as e:
            logger.error(f"Błąd resetowania konfiguracji: {e}")
            return False

    # --- Properties ---

    @property
    def thumbnail_size(self) -> Tuple[int, int]:
        """Pobiera aktualny rozmiar miniaturek jako tuple (width, height)."""
        return self._config_properties.thumbnail_size

    @property
    def predefined_colors_filter(self) -> OrderedDict:
        """Pobiera kolory jako OrderedDict dla filtrów."""
        return self._config_properties.predefined_colors_filter

    def get_thumbnail_format(self) -> str:
        """
        Pobiera format miniaturek.

        Returns:
            Format miniaturek (WEBP, JPEG, PNG).
        """
        return self._config_properties.get_thumbnail_format()

    def set_thumbnail_format(self, format_name: str) -> bool:
        """
        Ustawia format miniaturek.

        Args:
            format_name: Nazwa formatu (WEBP, JPEG, PNG).

        Returns:
            True jeśli format został ustawiony.
        """
        return self._config_properties.set_thumbnail_format(format_name)

    def get_thumbnail_quality(self) -> int:
        """
        Pobiera jakość kompresji miniaturek.

        Returns:
            Jakość kompresji (1-100).
        """
        return self._config_properties.get_thumbnail_quality()

    def set_thumbnail_quality(self, quality: int) -> bool:
        """
        Ustawia jakość kompresji miniaturek.

        Args:
            quality: Jakość kompresji (1-100).

        Returns:
            True jeśli jakość została ustawiona.
        """
        return self._config_properties.set_thumbnail_quality(quality)

    def get_thumbnail_webp_method(self) -> int:
        """
        Pobiera metodę kompresji WebP.

        Returns:
            Metoda kompresji WebP (0-6).
        """
        return self._config_properties.get_thumbnail_webp_method()

    def set_thumbnail_webp_method(self, method: int) -> bool:
        """
        Ustawia metodę kompresji WebP.

        Args:
            method: Metoda kompresji (0-6, wyższa = lepsza kompresja).

        Returns:
            True jeśli metoda została ustawiona.
        """
        return self._config_properties.set_thumbnail_webp_method(method)

    def get_thumbnail_preserve_transparency(self) -> bool:
        """
        Sprawdza czy zachowywać przezroczystość w miniaturkach.

        Returns:
            True jeśli zachowywać przezroczystość.
        """
        return self._config_properties.get_thumbnail_preserve_transparency()

    def set_thumbnail_preserve_transparency(self, preserve: bool) -> bool:
        """
        Ustawia czy zachowywać przezroczystość w miniaturkach.

        Args:
            preserve: Czy zachowywać przezroczystość.

        Returns:
            True jeśli ustawienie zostało zmienione.
        """
        return self._config_properties.set_thumbnail_preserve_transparency(preserve)

    # --- Static validation methods (backward compatibility) ---

    @staticmethod
    def _validate_int(
        value: Any,
        min_val: Optional[int] = None,
        max_val: Optional[int] = None,
        param_name: str = "Parametr",
    ) -> int:
        """Waliduje wartość całkowitą."""
        return ConfigValidator.validate_int(value, min_val, max_val, param_name)

    @staticmethod
    def _validate_str(value: Any, param_name: str = "Parametr") -> str:
        """Waliduje wartość tekstową."""
        return ConfigValidator.validate_str(value, param_name)

    @staticmethod
    def _validate_list(
        value: Any, item_type: Optional[type] = None, param_name: str = "Parametr"
    ) -> List:
        """Waliduje listę wartości."""
        return ConfigValidator.validate_list(value, item_type, param_name)

    @staticmethod
    def _validate_dict(value: Any, param_name: str = "Parametr") -> Dict:
        """Waliduje słownik."""
        return ConfigValidator.validate_dict(value, param_name)

    def __del__(self):
        """Cleanup przy usuwaniu obiektu."""
        if hasattr(self, '_config_io'):
            self._config_io.cleanup() 