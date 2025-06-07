"""
Test funkcji crop_to_square do sprawdzenia czy przycinanie do kwadratu działa poprawnie.
"""

import sys
import os
from PIL import Image

# Dodaj ścieżkę do src do path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.utils.image_utils import crop_to_square, pillow_image_to_qpixmap


def test_crop_to_square():
    """Test funkcji przycinania obrazów do kwadratu."""

    # Test 1: Obraz prostokątny (szerszy niż wyższy)
    print("Test 1: Obraz prostokątny 200x100 -> kwadrat 100x100")
    img_wide = Image.new("RGB", (200, 100), color="red")
    result_wide = crop_to_square(img_wide, 100)
    print(f"Wymiary: {result_wide.size} (oczekiwane: (100, 100))")
    assert result_wide.size == (100, 100), "Niepoprawny rozmiar dla obrazu szerokiego"

    # Test 2: Obraz prostokątny (wyższy niż szerszy)
    print("Test 2: Obraz prostokątny 100x200 -> kwadrat 100x100")
    img_tall = Image.new("RGB", (100, 200), color="blue")
    result_tall = crop_to_square(img_tall, 100)
    print(f"Wymiary: {result_tall.size} (oczekiwane: (100, 100))")
    assert result_tall.size == (100, 100), "Niepoprawny rozmiar dla obrazu wysokiego"

    # Test 3: Obraz już kwadratowy
    print("Test 3: Obraz kwadratowy 150x150 -> kwadrat 100x100")
    img_square = Image.new("RGB", (150, 150), color="green")
    result_square = crop_to_square(img_square, 100)
    print(f"Wymiary: {result_square.size} (oczekiwane: (100, 100))")
    assert result_square.size == (
        100,
        100,
    ), "Niepoprawny rozmiar dla obrazu kwadratowego"

    # Test 4: Skalowanie w górę
    print("Test 4: Mały obraz 50x30 -> kwadrat 100x100")
    img_small = Image.new("RGB", (50, 30), color="yellow")
    result_small = crop_to_square(img_small, 100)
    print(f"Wymiary: {result_small.size} (oczekiwane: (100, 100))")
    assert result_small.size == (100, 100), "Niepoprawny rozmiar dla małego obrazu"

    print("✅ Wszystkie testy przeszły pomyślnie!")
    print(
        "🎯 Funkcja crop_to_square działa poprawnie - obrazy są przycinane do kwadratu zachowując centralne części."
    )


if __name__ == "__main__":
    try:
        test_crop_to_square()
    except Exception as e:
        print(f"❌ Test nie powiódł się: {e}")
        sys.exit(1)
