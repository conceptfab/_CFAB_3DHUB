import logging
import os
import time
from collections import OrderedDict
from typing import Optional

from PIL import Image
from PyQt6.QtCore import Q_ARG, QDir, QMetaObject, QObject, QSize, Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QIcon, QImage, QPixmap

from src.app_config import config
from src.utils.image_utils import (
    create_placeholder_pixmap,
    crop_to_square,
    pillow_image_to_qpixmap,
)
from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)


class ThumbnailCache(QObject):
    _instance = None
    _error_icon = None  # Klasa statyczna dla error icon - NAPRAWKA błędu AttributeError

    def __init__(self):
        super().__init__()
        # Używamy OrderedDict dla mechanizmu LRU
        self._cache = (
            OrderedDict()
        )  # key: (normalized_path, width, height) -> (QPixmap, timestamp, size_bytes)
        self._total_memory_bytes = 0  # Przybliżony rozmiar cache w bajtach
        self._cleanup_pending = False  # Flaga zapobiegająca zbyt częstym cleanupom

        # Parametry z konfiguracji
        self._max_entries = config.thumbnail_cache_max_entries
        self._max_memory_mb = config.thumbnail_cache_max_memory_mb
        self._cleanup_threshold = config.thumbnail_cache_cleanup_threshold

        # Inicjalizacja timera dla asynchronicznego czyszczenia cache
        self._cleanup_timer = QTimer()
        self._cleanup_timer.setSingleShot(True)
        self._cleanup_timer.timeout.connect(self._perform_cleanup)
        self._cleanup_interval_ms = 5000  # 5 sekund między cleanupami

        logger.debug(
            f"ThumbnailCache zainicjalizowany: max_entries={self._max_entries}, max_memory={self._max_memory_mb}MB"
        )

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def get_error_icon(cls, width: int, height: int) -> Optional[QPixmap]:
        """Zwraca ikonę błędu lub None jeśli nie udało się jej utworzyć."""
        if cls._error_icon is None:
            try:
                # Użyj prostego placeholdera zamiast skomplikowanej logiki
                cls._error_icon = create_placeholder_pixmap(
                    64, 64, color="#FF5555", text="Błąd"
                )
                logger.debug("Utworzono ikonę błędu dla cache miniaturek")
            except Exception as e:
                logger.error(f"Nie można utworzyć ikony błędu: {e}")
                return None

        if cls._error_icon and not cls._error_icon.isNull():
            return cls._error_icon.scaled(
                QSize(width, height),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return None

    def load_pixmap_from_path(
        self, path: str, width: int, height: int
    ) -> Optional[QPixmap]:
        """
        Ładuje i przycina miniaturę z podanej ścieżki do kwadratowych proporcji.

        UWAGA: Ta metoda jest synchroniczna i może blokować UI!
        Zalecane jest używanie asynchronicznych workerów do ładowania miniaturek.

        Returns:
            QPixmap lub None jeśli ładowanie się nie powiedzie.
        """
        logger.warning(
            "load_pixmap_from_path: Synchroniczne ładowanie miniatury - może blokować UI!"
        )

        if not path:
            logger.warning("Próba załadowania miniatury z pustej ścieżki.")
            return None

        if not os.path.exists(path):
            logger.warning(f"Plik nie istnieje: {path}")
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

    def get_thumbnail(self, path: str, width: int, height: int) -> Optional[QPixmap]:
        """
        Pobiera miniaturę z cache. Zwraca None jeśli nie ma w cache.
        Aktualizuje pozycję w LRU cache przy dostępie.
        """
        cache_key = self._normalize_cache_key(path, width, height)

        if cache_key in self._cache:
            # Aktualizuj pozycję w LRU
            self._update_cache_access(cache_key)
            pixmap, timestamp, size_bytes = self._cache[cache_key]
            logger.debug(f"Cache HIT: {path} ({width}x{height})")
            return pixmap

        logger.debug(f"Cache MISS: {path} ({width}x{height})")
        return None

    def add_thumbnail(self, path: str, width: int, height: int, pixmap: QPixmap):
        """Dodaje załadowaną miniaturę do cache z obsługą LRU."""
        if not path or not pixmap or pixmap.isNull():
            logger.warning(
                f"Próba dodania nieprawidłowej miniatury do cache dla: {path}"
            )
            return

        cache_key = self._normalize_cache_key(path, width, height)
        size_bytes = self._estimate_pixmap_size(pixmap)
        timestamp = time.time()

        # Usuń starą wersję jeśli istnieje
        if cache_key in self._cache:
            old_pixmap, old_timestamp, old_size = self._cache[cache_key]
            self._total_memory_bytes -= old_size

        # Dodaj nową miniaturę
        self._cache[cache_key] = (pixmap, timestamp, size_bytes)
        self._total_memory_bytes += size_bytes

        logger.debug(
            f"Dodano do cache: {path} ({width}x{height}), rozmiar: {size_bytes//1024}KB"
        )

        # Zaplanuj czyszczenie cache tylko jeśli jest potrzebne i nie jest już zaplanowane
        self._schedule_cleanup()

    def clear_cache(self):
        """Czyści całą pamięć podręczną miniatur."""
        self._cache.clear()
        self._total_memory_bytes = 0
        self._cleanup_pending = False
        # Bezpiecznie zatrzymaj timer z dowolnego wątku
        QMetaObject.invokeMethod(
            self, "_stop_cleanup_timer", Qt.ConnectionType.QueuedConnection
        )
        logger.info("Pamięć podręczna miniatur została wyczyszczona.")

    def remove_thumbnail(self, path: str, width: int, height: int):
        """Usuwa konkretną miniaturę z cache."""
        cache_key = self._normalize_cache_key(path, width, height)
        if cache_key in self._cache:
            pixmap, timestamp, size_bytes = self._cache[cache_key]
            del self._cache[cache_key]
            self._total_memory_bytes -= size_bytes
            logger.debug(f"Usunięto z cache: {path} ({width}x{height})")

    def get_cache_size(self) -> int:
        """Zwraca liczbę elementów w cache."""
        return len(self._cache)

    def get_cache_memory_usage(self) -> dict:
        """Zwraca statystyki użycia pamięci cache."""
        return {
            "entries": len(self._cache),
            "memory_bytes": self._total_memory_bytes,
            "memory_mb": self._total_memory_bytes / (1024 * 1024),
            "max_entries": self._max_entries,
            "max_memory_mb": self._max_memory_mb,
        }

    def update_limits(self, max_entries: int, max_memory_mb: int):
        """Aktualizuje limity cache i wymusza cleanup jeśli potrzeba."""
        old_entries = self._max_entries
        old_memory = self._max_memory_mb

        self._max_entries = max_entries
        self._max_memory_mb = max_memory_mb

        logger.info(
            f"Zaktualizowano limity cache: entries {old_entries}→{max_entries}, "
            f"memory {old_memory}→{max_memory_mb}MB"
        )

        # Jeśli nowe limity są mniejsze, wymuś cleanup
        if max_entries < old_entries or max_memory_mb < old_memory:
            self._schedule_cleanup()

    def _normalize_cache_key(self, path: str, width: int, height: int) -> tuple:
        """
        Tworzy znormalizowany klucz cache.
        NAPRAWKA: Uwzględnia format miniaturek w kluczu cache.
        """
        try:
            from src.app_config import AppConfig

            config = AppConfig.get_instance()
            thumbnail_format = config.get_thumbnail_format()
            thumbnail_quality = config.get_thumbnail_quality()
        except Exception:
            # Fallback jeśli nie można pobrać konfiguracji
            thumbnail_format = "WEBP"
            thumbnail_quality = 80

        normalized_path = normalize_path(path) if path else ""
        # Klucz cache uwzględnia format i jakość aby różne ustawienia nie kolidowały
        return (normalized_path, width, height, thumbnail_format, thumbnail_quality)

    def _estimate_pixmap_size(self, pixmap: QPixmap) -> int:
        """
        Szacuje rozmiar QPixmap w bajtach.
        Używa bardziej realistycznego współczynnika dla formatu pixmapy.
        """
        if not pixmap or pixmap.isNull():
            return 0

        # Próbuj użyć metody sizeInBytes jeśli jest dostępna w nowszych wersjach Qt
        try:
            # To nie jest standardowa metoda w Qt5/Qt6, ale może się pojawić w przyszłości
            if hasattr(pixmap, "sizeInBytes"):
                return pixmap.sizeInBytes()
        except Exception:
            pass

        # Lepsze przybliżenie: uwzględniamy format i kompresję
        # Stosujemy współczynnik korekcji 0.5 dla lepszego przybliżenia
        # (większość QPixmap używa kompresji formatów)
        compression_factor = 0.5
        return int(pixmap.width() * pixmap.height() * 4 * compression_factor)

    def _schedule_cleanup(self):
        """Planuje asynchroniczne czyszczenie cache jeśli potrzebne."""
        max_memory_bytes = self._max_memory_mb * 1024 * 1024
        cleanup_entries_threshold = int(self._max_entries * self._cleanup_threshold)
        cleanup_memory_threshold = int(max_memory_bytes * self._cleanup_threshold)

        # Używamy wyższego progu (95%) dla wyzwalania cleanup
        high_threshold = 0.95
        cleanup_entries_high = int(self._max_entries * high_threshold)
        cleanup_memory_high = int(max_memory_bytes * high_threshold)

        # POPRAWKA ETAP 1: Monitoring memory usage w realtime
        self._log_memory_usage_realtime()

        # Sprawdź czy cache wymaga natychmiastowego czyszczenia (krytyczny poziom)
        critical_cleanup = (
            len(self._cache) > cleanup_entries_high
            or self._total_memory_bytes > cleanup_memory_high
        )

        # Sprawdź czy cache wymaga planowanego czyszczenia
        needs_cleanup = (
            len(self._cache) > cleanup_entries_threshold
            or self._total_memory_bytes > cleanup_memory_threshold
        )

        # Jeśli przekroczony krytyczny poziom, wykonaj czyszczenie natychmiast
        if critical_cleanup:
            # Bezpiecznie zatrzymaj timer z dowolnego wątku
            QMetaObject.invokeMethod(
                self, "_stop_cleanup_timer", Qt.ConnectionType.QueuedConnection
            )
            # Bezpiecznie wykonaj cleanup z głównego wątku
            QMetaObject.invokeMethod(
                self, "_perform_cleanup", Qt.ConnectionType.QueuedConnection
            )
        # W przeciwnym razie zaplanuj czyszczenie, tylko jeśli jest potrzebne i nie jest już zaplanowane
        elif needs_cleanup and not self._cleanup_pending:
            logger.debug(
                f"Zaplanowano cleanup cache za {self._cleanup_interval_ms/1000}s"
            )
            self._cleanup_pending = True
            # Bezpiecznie zaplanuj cleanup z głównego wątku
            QMetaObject.invokeMethod(
                self, "_start_cleanup_timer", Qt.ConnectionType.QueuedConnection
            )

    @pyqtSlot()
    def _stop_cleanup_timer(self):
        """Zatrzymuje timer cleanup - wywoływane tylko z głównego wątku."""
        if self._cleanup_timer.isActive():
            self._cleanup_timer.stop()

    @pyqtSlot()
    def _start_cleanup_timer(self):
        """Startuje timer cleanup - wywoływane tylko z głównego wątku."""
        if not self._cleanup_timer.isActive():
            self._cleanup_timer.start(self._cleanup_interval_ms)

    def _log_memory_usage_realtime(self):
        """POPRAWKA ETAP 1: Monitoring memory usage w realtime."""
        memory_usage_mb = self._total_memory_bytes / (1024 * 1024)
        memory_usage_percent = (
            self._total_memory_bytes / (self._max_memory_mb * 1024 * 1024)
        ) * 100

        # Log tylko jeśli przekroczono próg lub co 100 wywołań
        if not hasattr(self, "_memory_log_counter"):
            self._memory_log_counter = 0

        self._memory_log_counter += 1
        should_log = (
            memory_usage_percent > 80  # Wysokie zużycie
            or self._memory_log_counter % 100 == 0  # Co 100 wywołań
        )

        if should_log:
            logger.debug(
                f"Thumbnail cache memory: {memory_usage_mb:.1f}MB "
                f"({memory_usage_percent:.1f}%), "
                f"entries: {len(self._cache)}/{self._max_entries}"
            )

            # Alert przy krytycznym zużyciu
            if memory_usage_percent > 95:
                logger.warning(
                    f"Thumbnail cache memory critical: {memory_usage_mb:.1f}MB "
                    f"({memory_usage_percent:.1f}%)"
                )

    def get_memory_statistics(self) -> dict:
        """POPRAWKA ETAP 1: Zwraca szczegółowe statystyki pamięci."""
        memory_usage_mb = self._total_memory_bytes / (1024 * 1024)
        max_memory_mb = self._max_memory_mb
        memory_usage_percent = (
            (memory_usage_mb / max_memory_mb) * 100 if max_memory_mb > 0 else 0
        )

        return {
            "memory_usage_mb": memory_usage_mb,
            "max_memory_mb": max_memory_mb,
            "memory_usage_percent": memory_usage_percent,
            "cache_entries": len(self._cache),
            "max_entries": self._max_entries,
            "cache_full_percent": (
                (len(self._cache) / self._max_entries) * 100
                if self._max_entries > 0
                else 0
            ),
        }

    @pyqtSlot()
    def _perform_cleanup(self):
        """Wykonuje faktyczne czyszczenie cache według strategii LRU."""
        self._cleanup_pending = False

        max_memory_bytes = self._max_memory_mb * 1024 * 1024
        cleanup_entries_threshold = int(self._max_entries * self._cleanup_threshold)
        cleanup_memory_threshold = int(max_memory_bytes * self._cleanup_threshold)

        # Sprawdź czy potrzeba czyszczenia
        needs_cleanup = (
            len(self._cache) > cleanup_entries_threshold
            or self._total_memory_bytes > cleanup_memory_threshold
        )

        if not needs_cleanup:
            return

        initial_count = len(self._cache)
        initial_memory = self._total_memory_bytes

        # Usuń najstarsze elementy (LRU) aż będziemy poniżej progów
        target_entries = int(self._max_entries * 0.7)  # Usuń do 70% limitu
        target_memory = int(max_memory_bytes * 0.7)

        removed_count = 0
        while (
            len(self._cache) > target_entries
            or self._total_memory_bytes > target_memory
        ) and self._cache:
            # OrderedDict.popitem(last=False) usuwa najstarszy element (FIFO = LRU)
            key, (pixmap, timestamp, size_bytes) = self._cache.popitem(last=False)
            self._total_memory_bytes -= size_bytes
            removed_count += 1

        if removed_count > 0:
            logger.info(
                f"Cache cleanup: usunięto {removed_count} miniaturek. "
                f"Rozmiar: {initial_count}→{len(self._cache)} elementów, "
                f"Pamięć: {initial_memory//1024//1024}→{self._total_memory_bytes//1024//1024}MB"
            )

    def _update_cache_access(self, cache_key: tuple):
        """Aktualizuje pozycję w LRU cache przy dostępie."""
        if cache_key in self._cache:
            value = self._cache.pop(cache_key)
            self._cache[cache_key] = value


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
