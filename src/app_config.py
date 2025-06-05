# src/app_config.py
from collections import OrderedDict

# Lista obsługiwanych rozszerzeń plików archiwów
SUPPORTED_ARCHIVE_EXTENSIONS = [".rar", ".zip", ".7z", ".tar", ".gz", ".bz2"]

# Lista obsługiwanych rozszerzeń plików podglądów (obrazów)
SUPPORTED_PREVIEW_EXTENSIONS = []
SUPPORTED_PREVIEW_EXTENSIONS.append(".jpg")
SUPPORTED_PREVIEW_EXTENSIONS.append(".jpeg")
SUPPORTED_PREVIEW_EXTENSIONS.append(".png")
SUPPORTED_PREVIEW_EXTENSIONS.append(".gif")
SUPPORTED_PREVIEW_EXTENSIONS.append(".bmp")
SUPPORTED_PREVIEW_EXTENSIONS.append(".tiff")

# --- Dodane stałe konfiguracyjne dla UI ---

# Kolory do filtrowania w MainWindow
PREDEFINED_COLORS_FILTER = OrderedDict(
    [
        ("Wszystkie kolory", "ALL"),
        ("Brak koloru", "__NONE__"),  # Specjalny identyfikator dla braku koloru
        ("Czerwony", "#E53935"),
        ("Zielony", "#43A047"),
        ("Niebieski", "#1E88E5"),
        ("Żółty", "#FDD835"),
        ("Fioletowy", "#8E24AA"),
        ("Czarny", "#000000"),
    ]
)

# Rozmiary miniatur dla MainWindow
# Domyślny rozmiar (szerokość, wysokość) w px
DEFAULT_THUMBNAIL_SIZE = (150, 150)
MIN_THUMBNAIL_SIZE = (50, 50)  # Minimalny rozmiar (px)
MAX_THUMBNAIL_SIZE = (300, 300)  # Maksymalny rozmiar (px)
