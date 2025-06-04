"""
Testy jednostkowe dla modułu image_utils.py
"""
import os
import tempfile
import shutil
import pytest
from PIL import Image

from PyQt6.QtGui import QPixmap
from src.utils.image_utils import create_placeholder_pixmap, pillow_image_to_qpixmap


@pytest.mark.unit
def test_create_placeholder_pixmap():
    """Test tworzenia zastępczego obrazka."""
    width, height = 100, 100
    pixmap = create_placeholder_pixmap(width, height)
    
    # Sprawdź czy zwrócony obiekt jest typu QPixmap
    assert isinstance(pixmap, QPixmap)
    # Sprawdź czy ma odpowiednie wymiary
    assert pixmap.width() == width
    assert pixmap.height() == height
    # Sprawdź czy nie jest pusty
    assert not pixmap.isNull()


@pytest.mark.unit
def test_pillow_image_to_qpixmap():
    """Test konwersji obrazu PIL na QPixmap."""
    # Utwórz tymczasowy folder
    test_dir = tempfile.mkdtemp()
    
    try:
        # Utwórz testowy obraz
        test_image = Image.new('RGB', (50, 50), color='red')
        
        # Konwertuj na QPixmap
        pixmap = pillow_image_to_qpixmap(test_image)
        
        # Sprawdź rezultat
        assert isinstance(pixmap, QPixmap)
        assert pixmap.width() == 50
        assert pixmap.height() == 50
        assert not pixmap.isNull()
    
    finally:
        # Posprzątaj
        shutil.rmtree(test_dir)
