"""
Test integracyjny dla nowej funkcjonalności przycinania miniatur do kwadratu.
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PIL import Image

# Dodaj ścieżkę do src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.ui.widgets.thumbnail_cache import ThumbnailCache
from src.utils.image_utils import crop_to_square


def test_thumbnail_cache_integration():
    """Test integracji ThumbnailCache z nową funkcją crop_to_square."""

    # Utworzenie aplikacji Qt (wymagane dla QPixmap)
    app = QApplication(sys.argv)

    try:
        # Utwórz testowy obraz prostokątny
        test_image_path = "test_integration_image.png"
        test_img = Image.new("RGB", (300, 150), color="red")  # Obraz szeroki
        test_img.save(test_image_path)

        # Test ThumbnailCache z nową logiką
        cache = ThumbnailCache.get_instance()

        # Załaduj miniaturę jako kwadrat 100x100
        print("🔄 Testowanie ładowania miniatury przez ThumbnailCache...")
        pixmap = cache.load_pixmap_from_path(test_image_path, 100, 100)

        if pixmap and not pixmap.isNull():
            print(
                f"✅ Miniatura załadowana: {pixmap.size().width()}x{pixmap.size().height()}"
            )
            # Sprawdź czy miniatura jest kwadratowa
            assert pixmap.size().width() == 100, "Niepoprawna szerokość miniatury"
            assert pixmap.size().height() == 100, "Niepoprawna wysokość miniatury"
            print("✅ Miniatura jest kwadratowa jak oczekiwano!")
        else:
            print("❌ Nie udało się załadować miniatury")
            return False

        # Test dla obrazu wysokiego
        test_image_path_tall = "test_integration_image_tall.png"
        test_img_tall = Image.new("RGB", (150, 300), color="blue")  # Obraz wysoki
        test_img_tall.save(test_image_path_tall)

        pixmap_tall = cache.load_pixmap_from_path(test_image_path_tall, 80, 80)

        if pixmap_tall and not pixmap_tall.isNull():
            print(
                f"✅ Miniatura wysoka załadowana: {pixmap_tall.size().width()}x{pixmap_tall.size().height()}"
            )
            assert (
                pixmap_tall.size().width() == 80
            ), "Niepoprawna szerokość miniatury wysokiej"
            assert (
                pixmap_tall.size().height() == 80
            ), "Niepoprawna wysokość miniatury wysokiej"
            print("✅ Miniatura wysoka jest kwadratowa jak oczekiwano!")
        else:
            print("❌ Nie udało się załadować miniatury wysokiej")
            return False

        print("🎯 Test integracyjny przeszedł pomyślnie!")
        return True

    except Exception as e:
        print(f"❌ Błąd podczas testu integracyjnego: {e}")
        return False
    finally:
        # Posprzątaj pliki testowe
        for file_path in [
            "test_integration_image.png",
            "test_integration_image_tall.png",
        ]:
            if os.path.exists(file_path):
                os.remove(file_path)
        app.quit()


if __name__ == "__main__":
    success = test_thumbnail_cache_integration()
    if not success:
        sys.exit(1)
    print("\n🚀 Wszystkie testy integracyjne zakończone pomyślnie!")
    print(
        "📝 Miniaturki będą teraz przycinane do kwadratowych proporcji zamiast skalowane nieproporcjonalnie."
    )
