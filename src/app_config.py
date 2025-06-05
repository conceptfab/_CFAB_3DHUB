# src/app_config.py
import json
import os
from collections import OrderedDict

# --- Ścieżka do pliku konfiguracyjnego ---
CONFIG_FILE_NAME = "config.json"
# Używamy katalogu domowego użytkownika do przechowywania konfiguracji
APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".CFAB_3DHUB")
CONFIG_FILE_PATH = os.path.join(APP_DATA_DIR, CONFIG_FILE_NAME)

# --- Domyślne wartości konfiguracyjne ---
DEFAULT_CONFIG = {
    "thumbnail_size": 150,
    "thumbnail_slider_position": 50,
}

# --- Funkcje do zarządzania konfiguracją ---


def _load_config():
    """Wczytuje konfigurację z pliku JSON."""
    if not os.path.exists(CONFIG_FILE_PATH):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            # Uzupełnij o brakujące klucze, jeśli plik konfiguracyjny jest stary
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
    except (json.JSONDecodeError, IOError):
        return DEFAULT_CONFIG.copy()


def _save_config(config):
    """Zapisuje konfigurację do pliku JSON."""
    try:
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except IOError:
        # Logowanie błędu może być tutaj przydatne
        pass


# --- Inicjalizacja konfiguracji przy starcie modułu ---
_config = _load_config()

# --- Funkcje publiczne do zarządzania konfiguracją ---


def set_thumbnail_slider_position(position: int):
    """Zapisuje pozycję suwaka do konfiguracji."""
    _config["thumbnail_slider_position"] = position
    _save_config(_config)


# --- Istniejące stałe i te, które stają się konfigurowalne ---

# Lista obsługiwanych rozszerzeń plików archiwów
SUPPORTED_ARCHIVE_EXTENSIONS = [".rar", ".zip", ".7z", ".tar", ".gz", ".bz2"]

# Lista obsługiwanych rozszerzeń plików podglądów (obrazów)
SUPPORTED_PREVIEW_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tiff",
]

# Kolory do filtrowania w MainWindow
PREDEFINED_COLORS_FILTER = OrderedDict(
    [
        ("Wszystkie kolory", "ALL"),
        ("Brak koloru", "__NONE__"),
        ("Czerwony", "#E53935"),
        ("Zielony", "#43A047"),
        ("Niebieski", "#1E88E5"),
        ("Żółty", "#FDD835"),
        ("Fioletowy", "#8E24AA"),
        ("Czarny", "#000000"),
    ]
)

# Rozmiary miniatur dla MainWindow
MIN_THUMBNAIL_SIZE = (50, 50)
MAX_THUMBNAIL_SIZE = (300, 300)

# --- Obliczanie początkowego rozmiaru na podstawie konfiguracji ---
_slider_pos = _config.get("thumbnail_slider_position", 50)
_size_range = MAX_THUMBNAIL_SIZE[0] - MIN_THUMBNAIL_SIZE[0]
_initial_width = MIN_THUMBNAIL_SIZE[0] + int((_size_range * _slider_pos) / 100)
DEFAULT_THUMBNAIL_SIZE = (_initial_width, _initial_width)
