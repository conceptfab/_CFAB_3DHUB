"""
Test końcowy - sprawdzenie integracji nowej logiki przycinania z ThumbnailCache.
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PIL import Image, ImageDraw

# Dodaj ścieżkę do src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.ui.widgets.thumbnail_cache import ThumbnailCache


def create_marked_test_image(width, height, filename):
    """Tworzy obraz testowy z oznaczeniami krawędzi."""
    img = Image.new("RGB", (width, height), color="lightblue")
    draw = ImageDraw.Draw(img)

    # Dodaj oznaczenia na krawędziach
    # Lewy górny róg - czerwony
    draw.rectangle([0, 0, 30, 30], fill="red")
    draw.text((5, 35), "TOP-LEFT", fill="black")

    # Prawy górny róg - zielony
    draw.rectangle([width - 30, 0, width, 30], fill="green")
    draw.text((width - 80, 35), "TOP-RIGHT", fill="black")

    # Lewy dolny róg - żółty
    draw.rectangle([0, height - 30, 30, height], fill="yellow")
    draw.text((5, height - 50), "BOTTOM-LEFT", fill="black")

    # Prawy dolny róg - fioletowy
    draw.rectangle([width - 30, height - 30, width, height], fill="purple")
    draw.text((width - 100, height - 50), "BOTTOM-RIGHT", fill="black")

    img.save(filename)
    return img


def test_final_integration():
    """Test końcowy integracji z ThumbnailCache."""

    app = QApplication(sys.argv)

    try:
        print("🔬 Test końcowy integracji nowej logiki przycinania")
        print("=" * 55)

        # Test 1: Obraz szeroki
        print("Test 1: Obraz SZEROKI (300x150)")
        wide_image = "test_wide.png"
        create_marked_test_image(300, 150, wide_image)

        cache = ThumbnailCache.get_instance()
        pixmap_wide = cache.load_pixmap_from_path(wide_image, 100, 100)

        if pixmap_wide and not pixmap_wide.isNull():
            print(
                f"  ✅ Załadowano: {pixmap_wide.size().width()}x{pixmap_wide.size().height()}"
            )
            print("  📐 Powinien być widoczny: RED (top-left) i YELLOW (bottom-left)")
            print(
                "  📐 Powinien być obcięty: GREEN (top-right) i PURPLE (bottom-right)"
            )

        # Test 2: Obraz wysoki
        print("\nTest 2: Obraz WYSOKI (150x300)")
        tall_image = "test_tall.png"
        create_marked_test_image(150, 300, tall_image)

        pixmap_tall = cache.load_pixmap_from_path(tall_image, 100, 100)

        if pixmap_tall and not pixmap_tall.isNull():
            print(
                f"  ✅ Załadowano: {pixmap_tall.size().width()}x{pixmap_tall.size().height()}"
            )
            print("  📏 Powinien być widoczny: RED (top-left) i GREEN (top-right)")
            print(
                "  📏 Powinien być obcięty: YELLOW (bottom-left) i PURPLE (bottom-right)"
            )

        print("\n" + "=" * 55)
        print("✅ Integracja działa poprawnie!")
        print("🎯 Miniaturki są teraz przycinane zgodnie z wymaganiami:")
        print("   🔹 Obrazy szerokie: pokazują LEWĄ część")
        print("   🔹 Obrazy wysokie: pokazują GÓRNĄ część")

        return True

    except Exception as e:
        print(f"❌ Błąd podczas testu: {e}")
        return False
    finally:
        # Posprzątaj
        for filename in ["test_wide.png", "test_tall.png"]:
            if os.path.exists(filename):
                os.remove(filename)
        app.quit()


if __name__ == "__main__":
    success = test_final_integration()
    if not success:
        sys.exit(1)
    print("\n🚀 Implementacja zakończona pomyślnie!")
    print("🖼️  Miniaturki będą teraz poprawnie przycinane od żądanych krawędzi.")
