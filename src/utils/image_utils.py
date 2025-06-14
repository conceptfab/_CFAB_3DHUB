"""
Funkcje pomocnicze do operacji na obrazach.
"""

import logging
import os
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap


def create_placeholder_pixmap(width, height, color="#E0E0E0", text="Brak podglądu"):
    """
    Tworzy domyślny obrazek zastępczy w przypadku braku lub błędu wczytywania obrazu.

    Args:
        width (int): Szerokość obrazka w pikselach
        height (int): Wysokość obrazka w pikselach
        color (str): Kolor tła w formacie HTML (np. "#E0E0E0")
        text (str): Tekst do wyświetlenia na obrazku

    Returns:
        QPixmap: Utworzony obrazek zastępczy jako obiekt QPixmap
    """
    try:
        # Tworzenie obrazu przy użyciu biblioteki PIL
        img = Image.new("RGB", (width, height), color=color)
        draw = ImageDraw.Draw(img)

        # Próba użycia domyślnej czcionki
        try:
            # Użyj domyślnej czcionki systemowej lub alternatywnej
            font = ImageFont.load_default()

            # Obliczanie pozycji tekstu (przybliżone wyśrodkowanie)
            text_width = len(text) * 6  # Przybliżona szerokość tekstu
            text_x = (width - text_width) / 2
            text_y = height / 2 - 5  # 5 to przybliżona połowa wysokości czcionki

            # Narysowanie tekstu
            draw.text((text_x, text_y), text, fill="black", font=font)
        except Exception as e:
            logging.warning(f"Nie udało się narysować tekstu na placeholderze: {e}")

        # Konwersja obrazu PIL do QPixmap
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        q_image = QImage()
        q_image.loadFromData(buffer.getvalue())
        return QPixmap.fromImage(q_image)

    except Exception as e:
        logging.error(f"Błąd tworzenia placeholdera: {e}")
        # W przypadku błędu, zwróć pusty QPixmap o zadanych wymiarach
        return QPixmap(width, height)


def pillow_image_to_qpixmap(pil_image):
    """
    Konwertuje obiekt obrazu Pillow (PIL.Image) na QPixmap (PyQt6).

    NAPRAWKA: Używa konfigurowalnego formatu miniaturek z AppConfig.
    Domyślnie WebP dla lepszej kompresji i jakości (25-34% mniejsze pliki).

    Args:
        pil_image (PIL.Image): Obiekt obrazu z biblioteki Pillow

    Returns:
        QPixmap: Obiekt QPixmap utworzony z obrazu Pillow
    """
    try:
        from src.app_config import AppConfig

        config = AppConfig.get_instance()

        # Pobierz ustawienia formatu z konfiguracji
        thumbnail_format = config.get_thumbnail_format()
        thumbnail_quality = config.get_thumbnail_quality()
        webp_method = config.get_thumbnail_webp_method()
        preserve_transparency = config.get_thumbnail_preserve_transparency()

        # Przygotuj obraz w zależności od formatu i ustawień przezroczystości
        if thumbnail_format == "WEBP" and preserve_transparency:
            # WebP obsługuje przezroczystość - zachowaj RGBA
            if pil_image.mode not in ("RGB", "RGBA"):
                if pil_image.mode in ("LA", "PA"):
                    pil_image = pil_image.convert("RGBA")
                else:
                    pil_image = pil_image.convert("RGB")
        elif thumbnail_format == "PNG" and preserve_transparency:
            # PNG obsługuje przezroczystość - zachowaj RGBA
            if pil_image.mode not in ("RGB", "RGBA"):
                if pil_image.mode in ("LA", "PA"):
                    pil_image = pil_image.convert("RGBA")
                else:
                    pil_image = pil_image.convert("RGB")
        else:
            # JPEG nie obsługuje przezroczystości - konwertuj na RGB
            if pil_image.mode == "RGBA":
                background = Image.new("RGB", pil_image.size, (255, 255, 255))
                pil_image = Image.alpha_composite(
                    Image.new("RGBA", pil_image.size, (255, 255, 255, 255)), pil_image
                ).convert("RGB")
            elif pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")

        # Zapis do bufora w pamięci używając wybranego formatu
        buffer = BytesIO()

        if thumbnail_format == "WEBP":
            # WebP z konfigurowalnymi ustawieniami
            pil_image.save(
                buffer, format="WEBP", quality=thumbnail_quality, method=webp_method
            )
        elif thumbnail_format == "PNG":
            # PNG lossless - jakość nie ma znaczenia
            pil_image.save(buffer, format="PNG", optimize=True)
        else:  # JPEG
            # JPEG z konfigurowalnymi ustawieniami
            pil_image.save(
                buffer, format="JPEG", quality=thumbnail_quality, optimize=True
            )

        buffer.seek(0)

        # Konwersja do QImage i dalej do QPixmap
        q_image = QImage()
        q_image.loadFromData(buffer.getvalue())
        q_pixmap = QPixmap.fromImage(q_image)

        return q_pixmap

    except Exception as e:
        logging.error(
            f"Błąd konwersji obrazu Pillow do QPixmap ({thumbnail_format}): {e}"
        )
        # Fallback na JPEG jeśli wybrany format nie działa
        try:
            logging.warning("Próba fallback na JPEG...")
            if pil_image.mode == "RGBA":
                background = Image.new("RGB", pil_image.size, (255, 255, 255))
                pil_image = Image.alpha_composite(
                    Image.new("RGBA", pil_image.size, (255, 255, 255, 255)), pil_image
                ).convert("RGB")
            elif pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")

            buffer = BytesIO()
            pil_image.save(buffer, format="JPEG", quality=80, optimize=True)
            buffer.seek(0)

            q_image = QImage()
            q_image.loadFromData(buffer.getvalue())
            q_pixmap = QPixmap.fromImage(q_image)

            return q_pixmap
        except Exception as fallback_error:
            logging.error(f"Błąd fallback JPEG: {fallback_error}")
            return QPixmap()


def crop_to_square(pil_image, size):
    """
    Przycina obraz PIL do kwadratowych proporcji i skaluje do zadanego rozmiaru.

    Logika przycinania:
    - Dla obrazów WYSOKICH (height > width): przycina OD GÓRY
    - Dla obrazów SZEROKICH (width > height): przycina OD LEWEJ KRAWĘDZI
    - Dla obrazów kwadratowych: brak przycinania, tylko skalowanie

    Args:
        pil_image (PIL.Image): Obraz do przycięcia
        size (int): Docelowy rozmiar kwadratu (szerokość = wysokość)

    Returns:
        PIL.Image: Przycięty i przeskalowany obraz kwadratowy
    """
    try:
        # Pobierz wymiary oryginalnego obrazu
        width, height = pil_image.size

        # Oblicz rozmiar kwadratu do wycięcia (minimum z szerokości i wysokości)
        crop_size = min(width, height)

        if width > height:
            # Obraz SZEROKI - przycinaj OD LEWEJ KRAWĘDZI
            left = 0  # Zaczynaj od lewej krawędzi
            top = 0  # Zachowaj całą wysokość
            right = crop_size  # Szerokość = wysokość obrazu
            bottom = height  # Cała wysokość

        elif height > width:
            # Obraz WYSOKI - przycinaj OD GÓRY
            left = 0  # Zachowaj całą szerokość
            top = 0  # Zaczynaj od górnej krawędzi
            right = width  # Cała szerokość
            bottom = crop_size  # Wysokość = szerokość obrazu

        else:
            # Obraz KWADRATOWY - brak przycinania
            left = 0
            top = 0
            right = width
            bottom = height

        # Wytnij kwadrat zgodnie z obliczonymi współrzędnymi
        cropped_image = pil_image.crop((left, top, right, bottom))

        # Przeskaluj do docelowego rozmiaru
        resized_image = cropped_image.resize((size, size), Image.LANCZOS)

        return resized_image

    except Exception as e:
        logging.error(f"Błąd podczas przycinania obrazu do kwadratu: {e}")
        # W przypadku błędu, zwróć oryginalny obraz przeskalowany (fallback)
        return pil_image.resize((size, size), Image.LANCZOS)


def create_thumbnail_from_file(file_path, width, height):
    """
    Tworzy miniaturkę (QPixmap) na podstawie pliku graficznego.

    Wykorzystuje proper context management dla obrazów PIL i optymalizuje
    generowanie miniatur.

    Args:
        file_path: Ścieżka do pliku graficznego
        width: Szerokość miniaturki w pikselach
        height: Wysokość miniaturki w pikselach

    Returns:
        QPixmap: Utworzona miniaturka lub pusty QPixmap w przypadku błędu
    """
    try:
        # Sprawdzenie czy plik istnieje
        if not os.path.exists(file_path):
            logging.warning(f"Plik nie istnieje: {file_path}")
            return create_placeholder_pixmap(width, height, text="Brak pliku")

        # Utworzenie miniaturki z proper context management
        with Image.open(file_path) as img:
            # Jeśli miniaturka ma być kwadratowa, przytnij obraz
            if width == height:
                img_resized = crop_to_square(img, width)
            else:
                # W przeciwnym razie zachowaj proporcje
                img_resized = img.copy()
                img_resized.thumbnail((width, height), Image.LANCZOS)

            # Konwersja na QPixmap
            pixmap = pillow_image_to_qpixmap(img_resized)

            if pixmap and not pixmap.isNull():
                return pixmap
            else:
                # W przypadku nieudanej konwersji
                return create_placeholder_pixmap(width, height, text="Błąd konwersji")

    except Exception as e:
        logging.error(f"Błąd podczas tworzenia miniatury dla {file_path}: {e}")
        # Zwróć placeholder w przypadku błędu
        return create_placeholder_pixmap(width, height, text="Błąd")
