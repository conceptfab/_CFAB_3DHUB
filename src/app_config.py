# src/app_config.py
import json
import logging
import os
from collections import OrderedDict

from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)


class AppConfig:
    """
    Klasa zarządzająca konfiguracją aplikacji.

    Umożliwia odczyt i zapis parametrów konfiguracyjnych,
    z walidacją danych i obsługą błędów.
    """

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
        "scanner_max_cache_entries": 100,
        "scanner_max_cache_age_seconds": 3600,  # 1 godzina
        # Parametry cache dla miniaturek
        "thumbnail_cache_max_entries": 500,  # Maksymalna liczba miniaturek w cache
        "thumbnail_cache_max_memory_mb": 100,  # Maksymalna pamięć w MB (przybliżone)
        "thumbnail_cache_enable_disk": False,  # Czy używać cache na dysku
        "thumbnail_cache_cleanup_threshold": 0.8,  # Próg czyszczenia (80% limitu)
    }

    def __init__(self, config_dir=None, config_file=None):
        """
        Inicjalizuje obiekt konfiguracji.

        Args:
            config_dir (str, optional): Katalog konfiguracji. Jeśli None, używa domyślny.
            config_file (str, optional): Nazwa pliku konfiguracji. Jeśli None, używa domyślny.
        """
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

    def _update_derived_values(self):
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

    def _load_config(self):
        """
        Wczytuje konfigurację z pliku JSON.

        Returns:
            dict: Konfiguracja aplikacji.
        """
        if not os.path.exists(self._config_file_path):
            logger.debug(
                f"Plik konfiguracyjny nie istnieje: {self._config_file_path}. Używam domyślnych ustawień."
            )
            return self.DEFAULT_CONFIG.copy()

        try:
            with open(self._config_file_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Uzupełnij brakujące klucze
            updated = False
            for key, value in self.DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
                    updated = True

            if updated:
                logger.info("Zaktualizowano konfigurację o nowe parametry domyślne.")

            return config

        except json.JSONDecodeError as e:
            logger.error(
                f"Błąd dekodowania pliku JSON: {e}. Używam domyślnych ustawień."
            )
            return self.DEFAULT_CONFIG.copy()
        except IOError as e:
            logger.error(
                f"Błąd dostępu do pliku konfiguracyjnego: {e}. Używam domyślnych ustawień."
            )
            return self.DEFAULT_CONFIG.copy()

    def _save_config(self):
        """
        Zapisuje konfigurację do pliku JSON.

        Returns:
            bool: True jeśli zapis się powiódł, False w przeciwnym razie.
        """
        try:
            os.makedirs(self._app_data_dir, exist_ok=True)
            with open(self._config_file_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4)

            logger.debug(f"Konfiguracja zapisana do: {self._config_file_path}")
            return True

        except IOError as e:
            logger.error(f"Błąd zapisu konfiguracji: {e}")
            return False

    # --- Walidatory dla różnych typów danych ---

    @staticmethod
    def _validate_int(value, min_val=None, max_val=None, param_name="Parametr"):
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
    def _validate_str(value, param_name="Parametr"):
        """Waliduje wartość tekstową."""
        if not isinstance(value, str):
            raise ValueError(f"{param_name} musi być tekstem, otrzymano: {type(value)}")
        return value

    @staticmethod
    def _validate_list(value, item_type=None, param_name="Parametr"):
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
    def _validate_dict(value, param_name="Parametr"):
        """Waliduje słownik."""
        if not isinstance(value, dict):
            raise ValueError(
                f"{param_name} musi być słownikiem, otrzymano: {type(value)}"
            )
        return value

    # --- Publiczne API do zarządzania konfiguracją ---

    def get(self, key, default=None):
        """
        Pobiera wartość parametru konfiguracyjnego.

        Args:
            key (str): Klucz parametru.
            default: Wartość domyślna, jeśli parametr nie istnieje.

        Returns:
            Wartość parametru lub wartość domyślna.
        """
        return self._config.get(key, default)

    def set(self, key, value):
        """
        Ustawia wartość parametru konfiguracyjnego i zapisuje konfigurację.

        Args:
            key (str): Klucz parametru.
            value: Wartość parametru.

        Returns:
            bool: True jeśli zapisano pomyślnie, False w przeciwnym razie.
        """
        self._config[key] = value
        result = self._save_config()
        if result:
            # Aktualizuj wartości pochodne jeśli zapis się udał
            self._update_derived_values()
        return result

    def set_thumbnail_slider_position(self, position):
        """
        Ustawia pozycję suwaka miniatur i zapisuje konfigurację.

        Args:
            position (int): Pozycja suwaka (0-100).

        Returns:
            bool: True jeśli zapisano pomyślnie, False w przeciwnym razie.
        """
        position = self._validate_int(position, 0, 100, "Pozycja suwaka")
        return self.set("thumbnail_slider_position", position)

    def get_thumbnail_slider_position(self):
        """
        Pobiera pozycję suwaka miniatur.

        Returns:
            int: Pozycja suwaka (0-100).
        """
        return self.get("thumbnail_slider_position", 50)

    @property
    def predefined_colors_filter(self):
        """
        Pobiera słownik predefiniowanych kolorów do filtrowania.

        Returns:
            OrderedDict: Słownik kolorów.
        """
        colors_dict = self.get_predefined_colors()
        return OrderedDict(colors_dict.items())

    @property
    def scanner_max_cache_entries(self):
        """
        Pobiera maksymalną liczbę wpisów w cache skanera.

        Returns:
            int: Maksymalna liczba wpisów w cache.
        """
        return self.get("scanner_max_cache_entries", 100)

    @property
    def scanner_max_cache_age_seconds(self):
        """
        Pobiera maksymalny wiek wpisów w cache skanera w sekundach.

        Returns:
            int: Maksymalny wiek wpisów w cache w sekundach.
        """
        return self.get("scanner_max_cache_age_seconds", 3600)

    def set_thumbnail_size_range(self, min_size, max_size):
        """
        Ustawia zakres rozmiarów miniatur.

        Args:
            min_size (int): Minimalny rozmiar miniatury.
            max_size (int): Maksymalny rozmiar miniatury.

        Returns:
            bool: True jeśli zapisano pomyślnie, False w przeciwnym razie.
        """
        min_size = self._validate_int(min_size, 10, 1000, "Minimalny rozmiar miniatury")
        max_size = self._validate_int(
            max_size, min_size, 2000, "Maksymalny rozmiar miniatury"
        )

        success = True
        success &= self.set("min_thumbnail_size", min_size)
        success &= self.set("max_thumbnail_size", max_size)
        return success

    def get_supported_extensions(self, extension_type):
        """
        Pobiera listę obsługiwanych rozszerzeń.

        Args:
            extension_type (str): Typ rozszerzeń ("archive" lub "preview").

        Returns:
            list: Lista obsługiwanych rozszerzeń.
        """
        if extension_type == "archive":
            return self.get("supported_archive_extensions", [])
        elif extension_type == "preview":
            return self.get("supported_preview_extensions", [])
        else:
            logger.warning(f"Nieznany typ rozszerzeń: {extension_type}")
            return []

    def set_supported_extensions(self, extension_type, extensions):
        """
        Ustawia listę obsługiwanych rozszerzeń.

        Args:
            extension_type (str): Typ rozszerzeń ("archive" lub "preview").
            extensions (list): Lista obsługiwanych rozszerzeń.

        Returns:
            bool: True jeśli zapisano pomyślnie, False w przeciwnym razie.
        """
        extensions = self._validate_list(
            extensions, str, f"Lista rozszerzeń {extension_type}"
        )

        # Upewnij się, że wszystkie rozszerzenia zaczynają się od kropki
        normalized_extensions = [
            ext if ext.startswith(".") else f".{ext}" for ext in extensions
        ]

        if extension_type == "archive":
            return self.set("supported_archive_extensions", normalized_extensions)
        elif extension_type == "preview":
            return self.set("supported_preview_extensions", normalized_extensions)
        else:
            logger.warning(f"Nieznany typ rozszerzeń: {extension_type}")
            return False

    def get_predefined_colors(self):
        """
        Pobiera słownik predefiniowanych kolorów do filtrowania.

        Returns:
            dict: Słownik kolorów (nazwa: kod).
        """
        return self.get("predefined_colors", {})

    def set_predefined_colors(self, colors):
        """
        Ustawia słownik predefiniowanych kolorów do filtrowania.

        Args:
            colors (dict): Słownik kolorów (nazwa: kod).

        Returns:
            bool: True jeśli zapisano pomyślnie, False w przeciwnym razie.
        """
        colors = self._validate_dict(colors, "Słownik kolorów")
        return self.set("predefined_colors", colors)

    # --- Właściwości dla często używanych wartości ---

    @property
    def thumbnail_size(self):
        """
        Rozmiar miniatur obliczony na podstawie pozycji suwaka.

        Returns:
            tuple: Rozmiar miniatur (szerokość, wysokość).
        """
        return self._thumbnail_size

    @property
    def min_thumbnail_size(self):
        """
        Minimalny rozmiar miniatury.

        Returns:
            int: Minimalny rozmiar.
        """
        return self.get("min_thumbnail_size", 50)

    @property
    def max_thumbnail_size(self):
        """
        Maksymalny rozmiar miniatury.

        Returns:
            int: Maksymalny rozmiar.
        """
        return self.get("max_thumbnail_size", self.DEFAULT_CONFIG["max_thumbnail_size"])

    @property
    def default_thumbnail_size(self):
        """
        Domyślny rozmiar miniatury (obliczony lub z DEFAULT_CONFIG).

        Returns:
            int: Domyślny rozmiar miniatury.
        """
        # Zwraca obliczony _thumbnail_size[0] jeśli dostępny,
        # w przeciwnym razie wartość z DEFAULT_CONFIG.
        if hasattr(self, "_thumbnail_size") and self._thumbnail_size:
            return self._thumbnail_size[0]
        return self.DEFAULT_CONFIG["thumbnail_size"]

    @property
    def supported_archive_extensions(self):
        """
        Lista obsługiwanych rozszerzeń archiwów.

        Returns:
            list: Lista rozszerzeń.
        """
        return self.get_supported_extensions("archive")

    @property
    def supported_preview_extensions(self):
        """
        Lista obsługiwanych rozszerzeń podglądów (obrazów).

        Returns:
            list: Lista rozszerzeń.
        """
        return self.get_supported_extensions("preview")

    @property
    def predefined_colors_filter(self):
        """
        Słownik predefiniowanych kolorów do filtrowania.

        Returns:
            OrderedDict: Słownik kolorów.
        """
        colors_dict = self.get_predefined_colors()
        return OrderedDict(colors_dict.items())

    @property
    def scanner_max_cache_entries(self):
        """
        Pobiera maksymalną liczbę wpisów w cache skanera.

        Returns:
            int: Maksymalna liczba wpisów w cache.
        """
        return self.get("scanner_max_cache_entries", 100)

    @property
    def scanner_max_cache_age_seconds(self):
        """
        Pobiera maksymalny wiek wpisów w cache skanera w sekundach.

        Returns:
            int: Maksymalny wiek wpisów w cache w sekundach.
        """
        return self.get("scanner_max_cache_age_seconds", 3600)

    @property
    def thumbnail_cache_max_entries(self):
        """
        Pobiera maksymalną liczbę miniaturek w cache.

        Returns:
            int: Maksymalna liczba miniaturek w cache.
        """
        return self.get("thumbnail_cache_max_entries", 500)

    @property
    def thumbnail_cache_max_memory_mb(self):
        """
        Pobiera maksymalną ilość pamięci dla cache miniaturek w MB.

        Returns:
            int: Maksymalna pamięć w MB.
        """
        return self.get("thumbnail_cache_max_memory_mb", 100)

    @property
    def thumbnail_cache_enable_disk(self):
        """
        Sprawdza czy cache na dysku jest włączony dla miniaturek.

        Returns:
            bool: True jeśli cache na dysku jest włączony.
        """
        return self.get("thumbnail_cache_enable_disk", False)

    @property
    def thumbnail_cache_cleanup_threshold(self):
        """
        Pobiera próg czyszczenia cache miniaturek (wartość od 0.0 do 1.0).

        Returns:
            float: Próg czyszczenia cache.
        """
        return self.get("thumbnail_cache_cleanup_threshold", 0.8)


# --- Inicjalizacja domyślnej instancji konfiguracji ---
config = AppConfig()

# --- Eksport funkcji i stałych dla kompatybilności wstecznej ---
# Te funkcje i stałe są utrzymywane dla kompatybilności wstecznej
# z istniejącym kodem, który ich używa.


def set_thumbnail_slider_position(position: int):
    """
    Zapisuje pozycję suwaka do konfiguracji.

    Args:
        position (int): Pozycja suwaka (0-100).
    """
    return config.set_thumbnail_slider_position(position)


# Stałe eksportowane dla kompatybilności wstecznej
SUPPORTED_ARCHIVE_EXTENSIONS = config.supported_archive_extensions
SUPPORTED_PREVIEW_EXTENSIONS = config.supported_preview_extensions
PREDEFINED_COLORS_FILTER = config.predefined_colors_filter
MIN_THUMBNAIL_SIZE = config.min_thumbnail_size  # Zmieniono na int
MAX_THUMBNAIL_SIZE = config.max_thumbnail_size  # Zmieniono na int
DEFAULT_THUMBNAIL_SIZE = config.default_thumbnail_size  # Użycie nowej właściwości

# Parametry cache dla skanera
SCANNER_MAX_CACHE_ENTRIES = config.scanner_max_cache_entries
SCANNER_MAX_CACHE_AGE_SECONDS = config.scanner_max_cache_age_seconds
