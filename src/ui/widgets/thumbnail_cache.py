import logging

from PIL import Image
from PyQt6.QtCore import QDir, QSize, Qt
from PyQt6.QtGui import QIcon, QImage, QPixmap

from src.utils.image_utils import crop_to_square, pillow_image_to_qpixmap

logger = logging.getLogger(__name__)


class ThumbnailCache:
    _instance = None
    _cache = {}  # key: (path, width, height) -> QPixmap
    _error_icon = None  # Cache for a generic error icon

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def get_error_icon(cls, width: int, height: int) -> QPixmap | None:
        if cls._error_icon is None:
            # Try to load a standard Qt icon or a custom one if available
            # SP_MessageBoxWarning is a good candidate for an error/warning icon
            try:
                style = QDir.searchPaths(
                    "qtstyleplugins"
                )  # Placeholder, proper way to get style
                # In a real Qt app, you'd use self.style() or QApplication.style()
                # For now, let's try to create a simple one if standard icons are hard to get
                # This part is tricky without QApplication instance or widget context for style()
                # Fallback: create a simple pixmap with a red X or similar
                # As a placeholder, we'll return None, expecting UI to handle it
                # Ideally, load from a resource file:
                # cls._error_icon = QPixmap(":/icons/error_thumbnail.png")
                # If not available, create a simple one:
                pixmap = QPixmap(QSize(64, 64))
                pixmap.fill(Qt.GlobalColor.transparent)
                # painter = QPainter(pixmap)
                # pen = QPen(Qt.GlobalColor.red, 2)
                # painter.setPen(pen)
                # painter.drawLine(10, 10, 54, 54)
                # painter.drawLine(10, 54, 54, 10)
                # painter.end()
                # cls._error_icon = pixmap # Actual drawing commented out for simplicity
                # For now, let's assume no generic error icon is easily creatable here
                # and let the caller handle None.
                # A better approach is to have a resource file with a dedicated error image.                pass  # No generic icon generation for now
            except Exception as e:
                logger.error(f"Nie można załadować standardowej ikony błędu: {e}")

        if cls._error_icon:
            return cls._error_icon.scaled(
                QSize(width, height),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return None

    def load_pixmap_from_path(
        self, path: str, width: int, height: int
    ) -> QPixmap | None:
        """
        Ładuje i przycina miniaturę z podanej ścieżki do kwadratowych proporcji.
        Zwraca QPixmap lub None jeśli ładowanie się nie powiedzie.
        """
        if not path:
            logger.warning("Próba załadowania miniatury z pustej ścieżki.")
            return None
        try:
            # Jeśli docelowy rozmiar to kwadrat (width == height), użyj crop_to_square
            if width == height:
                with Image.open(path) as img:
                    cropped_img = crop_to_square(img, width)
                    return pillow_image_to_qpixmap(cropped_img)
            else:
                # Fallback dla niekwadratowych rozmiarów - użyj starej metody
                pixmap = QPixmap()
                # Attempt to load directly with QPixmap
                if not pixmap.load(path):
                    # Fallback to QImage if direct QPixmap loading fails
                    image = QImage()
                    if not image.load(path):
                        logger.warning(
                            f"Nie można załadować miniatury (QImage) z: {path}"
                        )
                        return None
                    pixmap = QPixmap.fromImage(image)

                if pixmap.isNull():
                    logger.warning(
                        f"Nie można załadować miniatury (pusta po konwersji) z: {path}"
                    )
                    return None

                return pixmap.scaled(
                    QSize(width, height),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
        except Exception as e:
            logger.error(f"Błąd podczas ładowania miniatury {path}: {e}")
            return None

    def get_thumbnail(self, path: str, width: int, height: int) -> QPixmap | None:
        """
        Pobiera miniaturę z cache. Zwraca None jeśli nie ma w cache.
        Nie ładuje z dysku.
        """
        cache_key = (path, width, height)
        return self._cache.get(cache_key)

    def add_thumbnail(self, path: str, width: int, height: int, pixmap: QPixmap):
        """Dodaje załadowaną miniaturę do cache."""
        if path and pixmap and not pixmap.isNull():
            cache_key = (path, width, height)
            self._cache[cache_key] = pixmap
            logger.debug(f"Dodano do cache: {path} ({width}x{height})")
        else:
            logger.warning(
                f"Próba dodania nieprawidłowej miniatury do cache dla: {path}"
            )

    def clear_cache(self):
        """Czyści całą pamięć podręczną miniatur."""
        self._cache.clear()
        logger.info("Pamięć podręczna miniatur została wyczyszczona.")

    def remove_thumbnail(self, path: str, width: int, height: int):
        """Usuwa konkretną miniaturę z cache."""
        cache_key = (path, width, height)
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.debug(f"Usunięto z cache: {path} ({width}x{height})")

    def get_cache_size(self) -> int:
        """Zwraca liczbę elementów w cache."""
        return len(self._cache)


# Przykład użycia (do testów)
# if __name__ == "__main__":
#     # To jest tylko do testowania modułu, nie uruchamiaj w aplikacji
#     # Wymaga kontekstu aplikacji Qt do pełnego działania QPixmap
#     from PyQt6.QtWidgets import QApplication
#     import sys
#
#     app = QApplication(sys.argv)
#
#     cache = ThumbnailCache.get_instance()
#
#     # Ścieżka do przykładowego obrazka (zmień na istniejący)
#     # test_image_path = "path/to/your/image.jpg"
#     test_image_path = "C:/Users/miczi/OneDrive/Pictures/tapety/japan-night.png" # Przykładowa ścieżka
#
#     # Spróbuj załadować i dodać
#     loaded_pixmap = cache.load_pixmap_from_path(test_image_path, 100, 100)
#     if loaded_pixmap:
#         cache.add_thumbnail(test_image_path, 100, 100, loaded_pixmap)
#         print(f"Załadowano i dodano do cache: {test_image_path}")
#     else:
#         print(f"Nie udało się załadować: {test_image_path}")
#
#     # Spróbuj pobrać z cache
#     cached_pixmap = cache.get_thumbnail(test_image_path, 100, 100)
#     if cached_pixmap:
#         print(f"Pobrano z cache: {test_image_path}, Rozmiar: {cached_pixmap.size()}")
#     else:
#         print(f"Nie znaleziono w cache: {test_image_path}")
#
#     print(f"Rozmiar cache: {cache.get_cache_size()}")
#     cache.clear_cache()
#     print(f"Rozmiar cache po wyczyszczeniu: {cache.get_cache_size()}")
#
#     # app.exec() # Nie jest potrzebne dla testu logiki cache, chyba że wyświetlasz coś
#     # sys.exit()
