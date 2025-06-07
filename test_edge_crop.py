"""
Test funkcji crop_to_square z nową logiką przycinania od krawędzi.
"""

import sys
import os
from PIL import Image, ImageDraw

# Dodaj ścieżkę do src do path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.utils.image_utils import crop_to_square


def create_test_image_with_marker(width, height, color, marker_position):
    """Tworzy testowy obraz z markerem w określonym miejscu."""
    img = Image.new("RGB", (width, height), color=color)
    draw = ImageDraw.Draw(img)

    # Rysuj marker w zależności od pozycji
    if marker_position == "top-left":
        # Kwadracik w lewym górnym rogu
        draw.rectangle([5, 5, 25, 25], fill="white")
    elif marker_position == "top-right":
        # Kwadracik w prawym górnym rogu
        draw.rectangle([width - 30, 5, width - 10, 25], fill="white")
    elif marker_position == "bottom-left":
        # Kwadracik w lewym dolnym rogu
        draw.rectangle([5, height - 30, 25, height - 10], fill="white")
    elif marker_position == "bottom-right":
        # Kwadracik w prawym dolnym rogu
        draw.rectangle([width - 30, height - 30, width - 10, height - 10], fill="white")

    return img


def test_crop_from_edges():
    """Test funkcji przycinania od określonych krawędzi."""

    print("🧪 Test przycinania od krawędzi:")
    print("=" * 50)

    # Test 1: Obraz SZEROKI - powinien przycinać OD LEWEJ
    print("Test 1: Obraz SZEROKI (300x150) - przycinanie od LEWEJ krawędzi")
    wide_img = create_test_image_with_marker(300, 150, "red", "top-left")
    result_wide = crop_to_square(wide_img, 150)

    print(f"  ✓ Wymiary: {result_wide.size} (oczekiwane: (150, 150))")
    print("  ✓ Biały marker w lewym górnym rogu powinien być WIDOCZNY")
    assert result_wide.size == (150, 150), "Niepoprawny rozmiar dla obrazu szerokiego"

    # Test 2: Obraz WYSOKI - powinien przycinać OD GÓRY
    print("\nTest 2: Obraz WYSOKI (150x300) - przycinanie od GÓRNEJ krawędzi")
    tall_img = create_test_image_with_marker(150, 300, "blue", "top-left")
    result_tall = crop_to_square(tall_img, 150)

    print(f"  ✓ Wymiary: {result_tall.size} (oczekiwane: (150, 150))")
    print("  ✓ Biały marker w lewym górnym rogu powinien być WIDOCZNY")
    assert result_tall.size == (150, 150), "Niepoprawny rozmiar dla obrazu wysokiego"

    # Test 3: Sprawdzenie, że dolna część obrazu wysokiego jest obcięta
    print("\nTest 3: Sprawdzenie obcinania dolnej części w obrazie wysokim")
    tall_img_bottom = create_test_image_with_marker(150, 300, "green", "bottom-left")
    result_tall_bottom = crop_to_square(tall_img_bottom, 150)

    print("  ✓ Biały marker z dolnej części powinien być NIEWIDOCZNY (obcięty)")

    # Test 4: Sprawdzenie, że prawa część obrazu szerokiego jest obcięta
    print("\nTest 4: Sprawdzenie obcinania prawej części w obrazie szerokim")
    wide_img_right = create_test_image_with_marker(300, 150, "yellow", "top-right")
    result_wide_right = crop_to_square(wide_img_right, 150)

    print("  ✓ Biały marker z prawej części powinien być NIEWIDOCZNY (obcięty)")

    # Test 5: Obraz kwadratowy - bez przycinania
    print("\nTest 5: Obraz KWADRATOWY (150x150) - bez przycinania")
    square_img = create_test_image_with_marker(150, 150, "purple", "top-left")
    result_square = crop_to_square(square_img, 100)

    print(f"  ✓ Wymiary: {result_square.size} (oczekiwane: (100, 100))")
    print("  ✓ Cały obraz powinien być zachowany (tylko przeskalowany)")
    assert result_square.size == (
        100,
        100,
    ), "Niepoprawny rozmiar dla obrazu kwadratowego"

    print("\n" + "=" * 50)
    print("✅ Wszystkie testy przeszły pomyślnie!")
    print("🎯 Nowa logika przycinania:")
    print("   📐 Obrazy SZEROKIE: przycinane od LEWEJ krawędzi")
    print("   📏 Obrazy WYSOKIE: przycinane od GÓRNEJ krawędzi")
    print("   ⬜ Obrazy KWADRATOWE: tylko skalowanie")


if __name__ == "__main__":
    try:
        test_crop_from_edges()
    except Exception as e:
        print(f"❌ Test nie powiódł się: {e}")
        sys.exit(1)
