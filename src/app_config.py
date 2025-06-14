# src/app_config.py
import json
import logging
import os
import shutil
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

import jsonschema

from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Centralized configuration validation."""

    SCHEMA = {
        "type": "object",
        "properties": {
            "thumbnail_size": {"type": "integer", "minimum": 100, "maximum": 600},
            "min_thumbnail_size": {"type": "integer", "minimum": 10, "maximum": 1000},
            "max_thumbnail_size": {"type": "integer", "minimum": 100, "maximum": 2000},
            "supported_archive_extensions": {
                "type": "array",
                "items": {"type": "string", "pattern": r"^\.[a-zA-Z0-9]+$"},
            },
            "supported_preview_extensions": {
                "type": "array",
                "items": {"type": "string", "pattern": r"^\.[a-zA-Z0-9]+$"},
            },
            "predefined_colors": {
                "type": "object",
                "patternProperties": {
                    ".*": {
                        "type": "string",
                        "pattern": r"^#[0-9A-Fa-f]{6}$|^ALL$|^__NONE__$",
                    }
                },
            },
            "scanner_max_cache_entries": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10000,
            },
            "scanner_max_cache_age_seconds": {
                "type": "integer",
                "minimum": 60,
                "maximum": 86400,
            },
            "thumbnail_cache_max_entries": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10000,
            },
            "thumbnail_cache_max_memory_mb": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1000,
            },
            "thumbnail_cache_enable_disk": {"type": "boolean"},
            "thumbnail_cache_cleanup_threshold": {
                "type": "number",
                "minimum": 0.1,
                "maximum": 1.0,
            },
            "window_min_width": {"type": "integer", "minimum": 400, "maximum": 2000},
            "window_min_height": {"type": "integer", "minimum": 300, "maximum": 1500},
            "resize_timer_delay_ms": {
                "type": "integer",
                "minimum": 50,
                "maximum": 1000,
            },
            "progress_hide_delay_ms": {
                "type": "integer",
                "minimum": 1000,
                "maximum": 10000,
            },
            "thread_wait_timeout_ms": {
                "type": "integer",
                "minimum": 100,
                "maximum": 5000,
            },
            "preferences_status_display_ms": {
                "type": "integer",
                "minimum": 1000,
                "maximum": 10000,
            },
            "thumbnail_format": {"type": "string", "pattern": r"^(WEBP|JPEG|PNG)$"},
            "thumbnail_quality": {"type": "integer", "minimum": 1, "maximum": 100},
            "thumbnail_webp_method": {"type": "integer", "minimum": 0, "maximum": 6},
            "thumbnail_preserve_transparency": {"type": "boolean"},
        },
        "additionalProperties": True,
    }

    @classmethod
    def validate(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate entire config against schema."""
        try:
            jsonschema.validate(config, cls.SCHEMA)
            return config
        except jsonschema.ValidationError as e:
            logger.warning(f"Config validation failed: {e.message}")
            # Return config with invalid values replaced by defaults
            return cls._fix_invalid_config(config, e)

    @classmethod
    def _fix_invalid_config(
        cls, config: Dict[str, Any], error: jsonschema.ValidationError
    ) -> Dict[str, Any]:
        """Fix invalid config by replacing bad values with defaults."""
        from copy import deepcopy

        # Create a working copy
        fixed_config = deepcopy(config)

        # Note: We can't access AppConfig.DEFAULT_CONFIG here due to circular import
        # Instead, we just log the error and return the original config
        logger.warning(f"Config validation error, using original config: {error}")

        return fixed_config


class AppConfig:
    """
    Klasa zarządzająca konfiguracją aplikacji z singleton pattern.

    Umożliwia odczyt i zapis parametrów konfiguracyjnych,
    z walidacją danych i obsługą błędów.
    """

    _instance = None
    _initialized = False

    # --- Domyślne wartości konfiguracji ---
    DEFAULT_CONFIG = {
        # UI
        "thumbnail_size": 250,
        "thumbnail_slider_position": 50,
        "min_thumbnail_size": 100,
        "max_thumbnail_size": 600,  # Zwiększono z 400
        # Obsługiwane rozszerzenia
        "supported_archive_extensions": [".rar", ".zip", ".7z", ".tar", ".gz", ".bz2"],
        "supported_preview_extensions": [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".tiff",
            ".webp",
        ],
        # Kolory do filtrowania
        "predefined_colors": {
            "Wszystkie kolory": "ALL",
            "Brak koloru": "__NONE__",
            "Czerwony": "#E53935",
            "Zielony": "#43A047",
            "Niebieski": "#1E88E5",
            "Żółty": "#FDD835",
            "Fioletowy": "#8E24AA",
            "Czarny": "#000000",
        },
        # Parametry cache dla scanera
        "scanner_max_cache_entries": 500,
        "scanner_max_cache_age_seconds": 3600,  # 1 godzina
        # Parametry cache dla miniaturek
        "thumbnail_cache_max_entries": 2000,
        "thumbnail_cache_max_memory_mb": 500,
        "thumbnail_cache_enable_disk": False,
        "thumbnail_cache_cleanup_threshold": 0.8,
        # Thumbnail format settings - NOWE
        "thumbnail_format": "WEBP",  # WEBP, JPEG, PNG
        "thumbnail_quality": 80,     # 1-100 dla lossy formatów
        "thumbnail_webp_method": 6,  # 0-6, wyższa wartość = lepsza kompresja
        "thumbnail_preserve_transparency": True,  # Zachowaj przezroczystość w WebP/PNG
        # Parametry okna i timerów
        "window_min_width": 800,  # Minimalna szerokość okna
        "window_min_height": 600,  # Minimalna wysokość okna
        "resize_timer_delay_ms": 150,  # Opóźnienie timera resize galerii (ms)
        "progress_hide_delay_ms": 3000,  # Czas wyświetlania postępu po zakończeniu (ms)
        "thread_wait_timeout_ms": 1000,  # Timeout oczekiwania na zakończenie wątku (ms)
        "preferences_status_display_ms": 3000,  # Czas wyświetlania statusu preferencji (ms)
        # Ochrona ustawień
    }

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

        # Async save components
        self._save_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="config_save"
        )
        self._save_lock = threading.Lock()
        self._save_future = None

        # Flaga informująca czy konfiguracja została wczytana z domyślnych wartości z powodu błędu
        self._config_loaded_from_defaults = False

        # Konfiguracja ścieżek
        self._config_file_name = config_file or "config.json"
        self._app_data_dir = config_dir or os.path.join(
            os.path.expanduser("~"), ".CFAB_3DHUB"
        )
        self._config_file_path = normalize_path(
            os.path.join(self._app_data_dir, self._config_file_name)
        )

        # Inicjalizacja konfiguracji
        self._config = self._load_config()
        logger.info(f"Konfiguracja wczytana z: {self._config_file_path}")

        # Obliczanie pochodnych wartości
        self._update_derived_values()

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
                property_map[name], self.DEFAULT_CONFIG.get(property_map[name])
            )

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )

    def _update_derived_values(self) -> None:
        """Aktualizuje wartości pochodne na podstawie konfiguracji."""
        slider_pos = self._config.get("thumbnail_slider_position", 50)
        min_size = self._config.get(
            "min_thumbnail_size", self.DEFAULT_CONFIG["min_thumbnail_size"]
        )
        max_size = self._config.get(
            "max_thumbnail_size", self.DEFAULT_CONFIG["max_thumbnail_size"]
        )

        size_range = max_size - min_size
        width = min_size + int((size_range * slider_pos) / 100)
        self._thumbnail_size = (width, width)

    def _load_config(self) -> Dict[str, Any]:
        """
        Wczytuje konfigurację z pliku JSON z walidacją.

        Returns:
            Konfiguracja aplikacji.
        """
        if not os.path.exists(self._config_file_path):
            logger.debug(
                f"Plik konfiguracyjny nie istnieje: {self._config_file_path}. Używam domyślnych ustawień."
            )
            return self.DEFAULT_CONFIG.copy()

        try:
            with open(self._config_file_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Validate and fix config
            config = ConfigValidator.validate(config)

            # Uzupełnij brakujące klucze
            updated = False
            for key, value in self.DEFAULT_CONFIG.items():
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
            return self.DEFAULT_CONFIG.copy()

    def _schedule_async_save(self):
        """Schedule async save with debouncing."""
        with self._save_lock:
            # Cancel previous save if pending
            if self._save_future and not self._save_future.done():
                self._save_future.cancel()

            # Schedule new save with 500ms delay
            self._save_future = self._save_executor.submit(self._delayed_save)

    def _delayed_save(self) -> bool:
        """Delayed save with debouncing."""
        time.sleep(0.5)  # 500ms debounce

        try:
            return self._save_config_sync()
        except Exception as e:
            logger.error(f"Async config save failed: {e}")
            return False

    def _save_config_sync(self) -> bool:
        """Synchronous save implementation."""
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
                json.dump(self._config, f, indent=4)

            # Po pomyślnym zapisie, resetujemy flagę
            self._config_loaded_from_defaults = False
            logger.debug(f"Konfiguracja zapisana do: {self._config_file_path}")
            return True

        except IOError as e:
            logger.error(f"Błąd zapisu konfiguracji: {e}")
            return False

    def _save_config(self) -> bool:
        """Legacy method - redirects to sync save for backward compatibility."""
        return self._save_config_sync()

    # --- Publiczne API do zarządzania konfiguracją ---

    def get(self, key: str, default: Any = None) -> Any:
        """
        Pobiera wartość konfiguracji.

        Args:
            key: Klucz konfiguracji.
            default: Wartość domyślna jeśli klucz nie istnieje.

        Returns:
            Wartość konfiguracji lub wartość domyślna.
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """
        Ustawia wartość konfiguracji z async save.

        Args:
            key: Klucz konfiguracji.
            value: Nowa wartość.

        Returns:
            True jeśli wartość została ustawiona.
        """
        self._config[key] = value
        self._update_derived_values()
        self._schedule_async_save()
        return True

    def set_thumbnail_slider_position(self, position: int) -> bool:
        """
        Ustawia pozycję suwaka rozmiaru miniaturek.

        Args:
            position: Pozycja suwaka (0-100).

        Returns:
            True jeśli pozycja została ustawiona.
        """
        try:
            validated_position = self._validate_int(position, 0, 100, "Pozycja suwaka")
            self._config["thumbnail_slider_position"] = validated_position
            self._update_derived_values()
            self._schedule_async_save()
            return True
        except ValueError as e:
            logger.error(f"Błąd ustawiania pozycji suwaka: {e}")
            return False

    def get_thumbnail_slider_position(self) -> int:
        """
        Pobiera pozycję suwaka rozmiaru miniaturek.

        Returns:
            Pozycja suwaka (0-100).
        """
        return self._config.get("thumbnail_slider_position", 50)

    def set_thumbnail_size_range(self, min_size: int, max_size: int) -> bool:
        """
        Ustawia zakres rozmiarów miniaturek.

        Args:
            min_size: Minimalny rozmiar miniaturki.
            max_size: Maksymalny rozmiar miniaturki.

        Returns:
            True jeśli zakres został ustawiony.
        """
        try:
            validated_min = self._validate_int(min_size, 50, 1000, "Minimalny rozmiar")
            validated_max = self._validate_int(
                max_size, 100, 2000, "Maksymalny rozmiar"
            )

            if validated_min >= validated_max:
                raise ValueError(
                    f"Minimalny rozmiar ({validated_min}) musi być mniejszy od maksymalnego ({validated_max})"
                )

            self._config["min_thumbnail_size"] = validated_min
            self._config["max_thumbnail_size"] = validated_max
            self._update_derived_values()
            self._schedule_async_save()
            return True

        except ValueError as e:
            logger.error(f"Błąd ustawiania zakresu rozmiarów miniaturek: {e}")
            return False

    def get_supported_extensions(self, extension_type: str) -> List[str]:
        """
        Pobiera listę obsługiwanych rozszerzeń.

        Args:
            extension_type: Typ rozszerzeń ("archive" lub "preview").

        Returns:
            Lista obsługiwanych rozszerzeń.
        """
        key_map = {
            "archive": "supported_archive_extensions",
            "preview": "supported_preview_extensions",
        }

        key = key_map.get(extension_type)
        if not key:
            logger.error(
                f"Nieprawidłowy typ rozszerzeń: {extension_type}. Dozwolone: {list(key_map.keys())}"
            )
            return []

        return self._config.get(key, [])

    def set_supported_extensions(
        self, extension_type: str, extensions: List[str]
    ) -> bool:
        """
        Ustawia listę obsługiwanych rozszerzeń.

        Args:
            extension_type: Typ rozszerzeń ("archive" lub "preview").
            extensions: Lista rozszerzeń.

        Returns:
            True jeśli lista została ustawiona.
        """
        try:
            validated_extensions = self._validate_list(
                extensions, str, "Lista rozszerzeń"
            )

            # Walidacja formatów rozszerzeń
            for ext in validated_extensions:
                if not ext.startswith("."):
                    raise ValueError(f"Rozszerzenie musi zaczynać się od kropki: {ext}")

            key_map = {
                "archive": "supported_archive_extensions",
                "preview": "supported_preview_extensions",
            }

            key = key_map.get(extension_type)
            if not key:
                raise ValueError(
                    f"Nieprawidłowy typ rozszerzeń: {extension_type}. Dozwolone: {list(key_map.keys())}"
                )

            self._config[key] = validated_extensions
            self._schedule_async_save()
            return True

        except ValueError as e:
            logger.error(f"Błąd ustawiania obsługiwanych rozszerzeń: {e}")
            return False

    def get_predefined_colors(self) -> Dict[str, str]:
        """
        Pobiera predefiniowane kolory.

        Returns:
            Słownik kolorów {nazwa: kod_hex}.
        """
        return self._config.get("predefined_colors", {})

    def set_predefined_colors(self, colors: Dict[str, str]) -> bool:
        """
        Ustawia predefiniowane kolory.

        Args:
            colors: Słownik kolorów {nazwa: kod_hex}.

        Returns:
            True jeśli kolory zostały ustawione.
        """
        try:
            validated_colors = self._validate_dict(colors, "Słownik kolorów")
            self._config["predefined_colors"] = validated_colors
            self._schedule_async_save()
            return True
        except ValueError as e:
            logger.error(f"Błąd ustawiania predefiniowanych kolorów: {e}")
            return False

    def save(self) -> bool:
        """
        Zapisuje konfigurację synchronicznie.

        Returns:
            True jeśli zapis się powiódł.
        """
        return self._save_config_sync()

    def reload(self) -> bool:
        """
        Przeładowuje konfigurację z pliku.

        Returns:
            True jeśli przeładowanie się powiodło.
        """
        try:
            self._config = self._load_config()
            self._update_derived_values()
            logger.info("Konfiguracja została przeładowana.")
            return True
        except Exception as e:
            logger.error(f"Błąd przeładowywania konfiguracji: {e}")
            return False

    def reset_to_defaults(self) -> bool:
        """
        Resetuje konfigurację do wartości domyślnych.

        Returns:
            True jeśli reset się powiódł.
        """
        try:
            self._config = self.DEFAULT_CONFIG.copy()
            self._update_derived_values()
            self._schedule_async_save()
            logger.info("Konfiguracja została zresetowana do domyślnych wartości.")
            return True
        except Exception as e:
            logger.error(f"Błąd resetowania konfiguracji: {e}")
            return False

    # --- Complex computed properties ---

    @property
    def thumbnail_size(self) -> Tuple[int, int]:
        """Computed property for thumbnail size."""
        return self._thumbnail_size

    @property
    def predefined_colors_filter(self) -> OrderedDict:
        """Computed property for ordered colors."""
        colors = self.get("predefined_colors", {})
        return OrderedDict(colors)

    # --- Thumbnail format configuration methods ---
    
    def get_thumbnail_format(self) -> str:
        """
        Pobiera format miniaturek.
        
        Returns:
            Format miniaturek: "WEBP", "JPEG" lub "PNG"
        """
        return self._config.get("thumbnail_format", "WEBP")
    
    def set_thumbnail_format(self, format_name: str) -> bool:
        """
        Ustawia format miniaturek.
        
        Args:
            format_name: Format miniaturek ("WEBP", "JPEG", "PNG")
            
        Returns:
            True jeśli format został ustawiony
        """
        if format_name not in ["WEBP", "JPEG", "PNG"]:
            logger.error(f"Nieprawidłowy format miniaturek: {format_name}")
            return False
            
        self._config["thumbnail_format"] = format_name
        self._schedule_async_save()
        logger.info(f"Format miniaturek zmieniony na: {format_name}")
        return True
    
    def get_thumbnail_quality(self) -> int:
        """
        Pobiera jakość kompresji miniaturek.
        
        Returns:
            Jakość kompresji (1-100)
        """
        return self._config.get("thumbnail_quality", 80)
    
    def set_thumbnail_quality(self, quality: int) -> bool:
        """
        Ustawia jakość kompresji miniaturek.
        
        Args:
            quality: Jakość kompresji (1-100)
            
        Returns:
            True jeśli jakość została ustawiona
        """
        try:
            validated_quality = self._validate_int(quality, 1, 100, "Jakość miniaturek")
            self._config["thumbnail_quality"] = validated_quality
            self._schedule_async_save()
            logger.info(f"Jakość miniaturek zmieniona na: {validated_quality}")
            return True
        except ValueError as e:
            logger.error(f"Błąd ustawiania jakości miniaturek: {e}")
            return False
    
    def get_thumbnail_webp_method(self) -> int:
        """
        Pobiera metodę kompresji WebP.
        
        Returns:
            Metoda kompresji WebP (0-6)
        """
        return self._config.get("thumbnail_webp_method", 6)
    
    def set_thumbnail_webp_method(self, method: int) -> bool:
        """
        Ustawia metodę kompresji WebP.
        
        Args:
            method: Metoda kompresji (0-6, wyższa = lepsza kompresja)
            
        Returns:
            True jeśli metoda została ustawiona
        """
        try:
            validated_method = self._validate_int(method, 0, 6, "Metoda WebP")
            self._config["thumbnail_webp_method"] = validated_method
            self._schedule_async_save()
            logger.info(f"Metoda WebP zmieniona na: {validated_method}")
            return True
        except ValueError as e:
            logger.error(f"Błąd ustawiania metody WebP: {e}")
            return False
    
    def get_thumbnail_preserve_transparency(self) -> bool:
        """
        Sprawdza czy zachowywać przezroczystość w miniaturkach.
        
        Returns:
            True jeśli zachowywać przezroczystość
        """
        return self._config.get("thumbnail_preserve_transparency", True)
    
    def set_thumbnail_preserve_transparency(self, preserve: bool) -> bool:
        """
        Ustawia czy zachowywać przezroczystość w miniaturkach.
        
        Args:
            preserve: Czy zachowywać przezroczystość
            
        Returns:
            True jeśli ustawienie zostało zmienione
        """
        self._config["thumbnail_preserve_transparency"] = preserve
        self._schedule_async_save()
        logger.info(f"Zachowywanie przezroczystości: {preserve}")
        return True

    # --- Static validation methods (kept for backward compatibility) ---

    @staticmethod
    def _validate_int(
        value: Any,
        min_val: Optional[int] = None,
        max_val: Optional[int] = None,
        param_name: str = "Parametr",
    ) -> int:
        """Waliduje wartość całkowitą."""
        if not isinstance(value, int):
            raise ValueError(
                f"{param_name} musi być liczbą całkowitą, otrzymano: {type(value)}"
            )

        if min_val is not None and value < min_val:
            raise ValueError(
                f"{param_name} musi być większy lub równy {min_val}, otrzymano: {value}"
            )

        if max_val is not None and value > max_val:
            raise ValueError(
                f"{param_name} musi być mniejszy lub równy {max_val}, otrzymano: {value}"
            )

        return value

    @staticmethod
    def _validate_str(value: Any, param_name: str = "Parametr") -> str:
        """Waliduje wartość tekstową."""
        if not isinstance(value, str):
            raise ValueError(f"{param_name} musi być tekstem, otrzymano: {type(value)}")
        return value

    @staticmethod
    def _validate_list(
        value: Any, item_type: Optional[type] = None, param_name: str = "Parametr"
    ) -> List:
        """Waliduje listę wartości."""
        if not isinstance(value, list):
            raise ValueError(f"{param_name} musi być listą, otrzymano: {type(value)}")

        if item_type is not None:
            for i, item in enumerate(value):
                if not isinstance(item, item_type):
                    raise ValueError(
                        f"Element {i} w {param_name} musi być typu {item_type}, otrzymano: {type(item)}"
                    )
        return value

    @staticmethod
    def _validate_dict(value: Any, param_name: str = "Parametr") -> Dict:
        """Waliduje słownik."""
        if not isinstance(value, dict):
            raise ValueError(
                f"{param_name} musi być słownikiem, otrzymano: {type(value)}"
            )
        return value


# --- Legacy global functions (backward compatibility) ---


def set_thumbnail_slider_position(position: int) -> bool:
    """Legacy function for backward compatibility."""
    config = AppConfig.get_instance()
    return config.set_thumbnail_slider_position(position)


def get_supported_extensions(extension_type: str) -> List[str]:
    """Legacy function for backward compatibility."""
    config = AppConfig.get_instance()
    return config.get_supported_extensions(extension_type)


def get_predefined_colors() -> Dict[str, str]:
    """Legacy function for backward compatibility."""
    config = AppConfig.get_instance()
    return config.get_predefined_colors()


def set_predefined_colors(colors: Dict[str, str]) -> bool:
    """Legacy function for backward compatibility."""
    config = AppConfig.get_instance()
    return config.set_predefined_colors(colors)


# --- Thumbnail format legacy functions ---

def get_thumbnail_format() -> str:
    """Legacy function for backward compatibility."""
    config = AppConfig.get_instance()
    return config.get_thumbnail_format()


def set_thumbnail_format(format_name: str) -> bool:
    """Legacy function for backward compatibility."""
    config = AppConfig.get_instance()
    return config.set_thumbnail_format(format_name)


def get_thumbnail_quality() -> int:
    """Legacy function for backward compatibility."""
    config = AppConfig.get_instance()
    return config.get_thumbnail_quality()


def set_thumbnail_quality(quality: int) -> bool:
    """Legacy function for backward compatibility."""
    config = AppConfig.get_instance()
    return config.set_thumbnail_quality(quality)


# --- Legacy constants for backward compatibility ---
config = AppConfig.get_instance()

SUPPORTED_ARCHIVE_EXTENSIONS = config.supported_archive_extensions
SUPPORTED_PREVIEW_EXTENSIONS = config.supported_preview_extensions
PREDEFINED_COLORS_FILTER = config.predefined_colors_filter
MIN_THUMBNAIL_SIZE = config.min_thumbnail_size
MAX_THUMBNAIL_SIZE = config.max_thumbnail_size
DEFAULT_THUMBNAIL_SIZE = config.default_thumbnail_size

# Parametry cache dla skanera
SCANNER_MAX_CACHE_ENTRIES = config.scanner_max_cache_entries
SCANNER_MAX_CACHE_AGE_SECONDS = config.scanner_max_cache_age_seconds
