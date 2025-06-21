"""
Centralizacja stylów dla kafelków plików.

Ten moduł definiuje style i ich parametry dla FileTileWidget i powiązanych komponentów.
Pozwala na spójne zarządzanie wyglądem kafelków w całej aplikacji.
"""

from PyQt6.QtGui import QColor


class TileColorScheme:
    """Schemat kolorów używanych w kafelkach plików."""

    # Kolory tła
    BACKGROUND = "#2D2D2D"
    BACKGROUND_HOVER = "#353535"

    # Kolory obramowania
    BORDER = "#404040"
    BORDER_HOVER = "#5A9FD4"

    # Kolory tekstu
    TEXT = "#E0E0E0"
    TEXT_HOVER = "#5A9FD4"

    # Kolory błędów i specjalnych stanów
    ERROR_COLOR = "#FF5555"
    LOADING_COLOR = "#555555"

    # Predefiniowane kolory dla tagów
    PREDEFINED_COLOR_TAGS = {
        "Brak": "",
        "Czerwony": "#E53935",
        "Zielony": "#43A047",
        "Niebieski": "#1E88E5",
        "Żółty": "#FDD835",
        "Fioletowy": "#8E24AA",
        "Czarny": "#000000",
    }


class TileStylesheet:
    """Style CSS dla komponentów kafelków plików."""

    @staticmethod
    def get_file_tile_stylesheet():
        """Zwraca stylesheet dla widgetu kafelka plików."""
        return f"""
            FileTileWidget {{
                background-color: {TileColorScheme.BACKGROUND};
                border: 1px solid {TileColorScheme.BORDER};
                border-radius: 6px;
                margin: 6px;
                padding: 8px;
                min-width: 150px;
                min-height: 190px;
            }}

            FileTileWidget:hover {{
                background-color: {TileColorScheme.BACKGROUND_HOVER};
                border: 1px solid {TileColorScheme.BORDER_HOVER};
            }}

            FileTileWidget QWidget {{
                background-color: transparent;
            }}
            
            FileTileWidget QFrame {{
                background-color: transparent;
                border: none;
            }}
        """

    @staticmethod
    def get_thumbnail_frame_stylesheet(color_hex=""):
        """Zwraca stylesheet dla ramki miniatury, opcjonalnie z kolorowym obramowaniem."""
        if color_hex and color_hex.strip():
            return f"""
                QFrame {{
                    border: 2px solid {color_hex};
                    border-radius: 4px;
                    padding: 0px;
                    margin: 0px;
                    background-color: transparent;
                }}
            """
        else:
            return """
                QFrame {
                    border: none;
                    border-radius: 4px;
                    padding: 0px;
                    margin: 0px;
                    background-color: transparent;
                }
            """

    @staticmethod
    def get_thumbnail_label_stylesheet():
        """Zwraca stylesheet dla etykiety miniatury."""
        return f"""
            QLabel {{
                border-radius: 3px;
                background-color: transparent;
                border: 1px solid {TileColorScheme.BORDER};
            }}
            QLabel:hover {{
                background-color: rgba(90, 159, 212, 0.1);
                border: 1px solid {TileColorScheme.BORDER_HOVER};
            }}
        """

    @staticmethod
    def get_filename_label_stylesheet(font_size=12):
        """Zwraca stylesheet dla etykiety nazwy pliku z dynamicznym rozmiarem czcionki."""
        return f"""
            QLabel {{
                color: {TileColorScheme.TEXT};
                font-weight: 400;
                font-size: {font_size}px;
                font-family: "Segoe UI", Arial, sans-serif;
                padding: 4px 2px;
                border-radius: 0px;
                background-color: transparent;
                text-align: center;
                border: none;
            }}

            QLabel:hover {{
                color: {TileColorScheme.TEXT_HOVER};
                font-weight: 400;
                background-color: transparent;
            }}
        """


class TileSizeConstants:
    """Stałe wymiarów dla kafelków plików."""

    # Domyślne wymiary kafelka
    DEFAULT_THUMBNAIL_SIZE = (250, 250)

    # Minimalne wymiary
    MIN_THUMBNAIL_WIDTH = 80
    MIN_THUMBNAIL_HEIGHT = 80

    # Odstępy i marginesy
    TILE_MARGIN = 6
    TILE_PADDING = 8

    # Wymiary nazwy pliku
    FILENAME_MAX_HEIGHT = 35

    # Wymiary kontrolek metadanych
    METADATA_MAX_HEIGHT = 24

    # Margines laoyutu
    LAYOUT_MARGINS = (8, 12, 8, 8)  # lewy, górny, prawy, dolny
    LAYOUT_SPACING = 4
