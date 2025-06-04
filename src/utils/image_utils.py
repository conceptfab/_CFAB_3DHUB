"""
Funkcje pomocnicze do operacji na obrazach.
"""

import logging
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
        img = Image.new('RGB', (width, height), color=color)
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
    
    Args:
        pil_image (PIL.Image): Obiekt obrazu z biblioteki Pillow
        
    Returns:
        QPixmap: Obiekt QPixmap utworzony z obrazu Pillow
    """
    try:
        # Konwersja do RGB jeśli obraz jest w trybie RGBA (zapobieganie problemom z przezroczystością)
        if pil_image.mode == 'RGBA':
            background = Image.new('RGBA', pil_image.size, (255, 255, 255))
            composite = Image.alpha_composite(background, pil_image)
            pil_image = composite.convert('RGB')
        elif pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Zapis do bufora w pamięci
        buffer = BytesIO()
        pil_image.save(buffer, format='JPEG')
        buffer.seek(0)
        
        # Konwersja do QImage i dalej do QPixmap
        q_image = QImage()
        q_image.loadFromData(buffer.getvalue())
        q_pixmap = QPixmap.fromImage(q_image)
        
        return q_pixmap
    
    except Exception as e:
        logging.error(f"Błąd konwersji obrazu Pillow do QPixmap: {e}")
        return QPixmap()
