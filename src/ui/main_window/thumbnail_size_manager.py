"""
ThumbnailSizeManager - zarządzanie rozmiarem miniaturek.
🚀 ETAP 2 REFAKTORYZACJI: Wydzielenie logiki miniaturek z main_window.py
"""

import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional, Protocol

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMainWindow


@dataclass
class ThumbnailSizeConfig:
    """Konfiguracja dla thumbnail size management."""

    min_size: int = 100
    max_size: int = 500
    default_size: int = 200
    debounce_delay_ms: int = 150  # milliseconds
    validation_enabled: bool = True


class GalleryManagerProtocol(Protocol):
    """Protocol dla gallery manager dependency."""

    def update_thumbnail_size(self, size: int) -> None:
        """Updates thumbnail size in gallery."""
        ...


class ConfigManagerProtocol(Protocol):
    """Protocol dla config manager dependency."""

    def set_thumbnail_slider_position(self, position: int) -> None:
        """Saves slider position to config."""
        ...


class SizeCalculator:
    """Helper class dla business logic obliczania rozmiarów."""

    def __init__(self, config: ThumbnailSizeConfig):
        self.config = config
        self._lock = threading.RLock()

    def calculate_size_from_slider(self, slider_value: int) -> int:
        """
        Oblicza rozmiar miniaturki na podstawie pozycji suwaka.

        Args:
            slider_value: Pozycja suwaka (0-100)

        Returns:
            Rozmiar miniaturki w pikselach

        Raises:
            ValueError: Gdy slider_value jest poza zakresem
        """
        with self._lock:
            if self.config.validation_enabled:
                if not (0 <= slider_value <= 100):
                    raise ValueError(f"Slider value {slider_value} outside range 0-100")

            # Clamp value to safe range
            slider_value = max(0, min(100, slider_value))

            size_range = self.config.max_size - self.config.min_size

            if size_range <= 0:
                return self.config.min_size

            # Calculate proportional size
            calculated_size = self.config.min_size + int(
                (size_range * slider_value) / 100
            )

            # Ensure result is within bounds
            return max(self.config.min_size, min(self.config.max_size, calculated_size))

    def validate_size(self, size: int) -> bool:
        """Waliduje czy rozmiar jest w dozwolonym zakresie."""
        return self.config.min_size <= size <= self.config.max_size


class ThumbnailSizeManager:
    """
    Manager odpowiedzialny za zarządzanie rozmiarem miniaturek.
    Obsługuje suwak rozmiaru, resize okna i aktualizację miniaturek.
    """

    def __init__(
        self,
        main_window,
        gallery_manager: Optional[GalleryManagerProtocol] = None,
        config_manager: Optional[ConfigManagerProtocol] = None,
        size_config: Optional[ThumbnailSizeConfig] = None,
    ):
        """
        Inicjalizuje ThumbnailSizeManager z dependency injection.

        Args:
            main_window: Referencja do głównego okna aplikacji
            gallery_manager: Optional injected gallery manager
            config_manager: Optional injected config manager
            size_config: Optional size configuration
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

        # Dependency injection with fallbacks
        self._gallery_manager = gallery_manager or getattr(
            main_window, "gallery_manager", None
        )
        self._config_manager = config_manager or getattr(
            main_window, "app_config", None
        )

        # Configuration
        self.size_config = size_config or ThumbnailSizeConfig()
        self.size_calculator = SizeCalculator(self.size_config)

        # Debouncing
        self._debounce_timer: Optional[QTimer] = None
        self._pending_update = False
        self._lock = threading.RLock()

        # Cache frequently accessed attributes
        self._cached_attributes = self._cache_main_window_attributes()

        # Performance tracking
        self._last_update_time = 0.0
        self._update_count = 0

    def _cache_main_window_attributes(self) -> dict:
        """Cache frequently accessed main_window attributes."""
        return {
            "has_size_slider": hasattr(self.main_window, "size_slider"),
            "has_resize_timer": hasattr(self.main_window, "resize_timer"),
            "has_min_thumbnail_size": hasattr(self.main_window, "min_thumbnail_size"),
            "has_max_thumbnail_size": hasattr(self.main_window, "max_thumbnail_size"),
            "has_current_thumbnail_size": hasattr(
                self.main_window, "current_thumbnail_size"
            ),
        }

    def update_thumbnail_size(self):
        """
        Aktualizuje rozmiar miniatur w galerii na podstawie suwaka z debouncing.
        """
        with self._lock:
            start_time = time.time()

            try:
                if not self._cached_attributes["has_size_slider"]:
                    self.logger.warning("Size slider not available in main_window")
                    return

                slider_value = self.main_window.size_slider.value()

                # Validate slider value
                try:
                    new_size = self.size_calculator.calculate_size_from_slider(
                        slider_value
                    )
                except ValueError as e:
                    self.logger.error(f"Invalid slider value: {e}")
                    return

                # Update main_window state
                if self._cached_attributes["has_current_thumbnail_size"]:
                    self.main_window.current_thumbnail_size = new_size

                # Save to config if available
                if self._config_manager:
                    try:
                        self._config_manager.set_thumbnail_slider_position(slider_value)
                    except Exception as e:
                        self.logger.warning(f"Failed to save slider position: {e}")

                # Start debounced update
                self._start_debounced_update()

                # Performance logging
                self._update_count += 1
                elapsed = time.time() - start_time

                if self._update_count % 10 == 0:  # Log every 10th update
                    self.logger.info(
                        f"Thumbnail size update #{self._update_count}: {new_size}px "
                        f"(slider: {slider_value}%) in {elapsed:.3f}s"
                    )
                else:
                    self.logger.debug(
                        f"New thumbnail size: {new_size}px (slider: {slider_value}%)"
                    )

            except Exception as e:
                self.logger.error(f"Error in update_thumbnail_size: {e}", exc_info=True)

    def _start_debounced_update(self):
        """Uruchamia debounced update timer."""
        with self._lock:
            if not self._debounce_timer:
                self._debounce_timer = QTimer()
                self._debounce_timer.setSingleShot(True)
                self._debounce_timer.timeout.connect(self._execute_debounced_update)

            # Reset timer on each call (debouncing effect)
            self._debounce_timer.stop()
            self._debounce_timer.start(self.size_config.debounce_delay_ms)
            self._pending_update = True

    def _execute_debounced_update(self):
        """Wykonuje rzeczywistą aktualizację po debounce delay."""
        with self._lock:
            if not self._pending_update:
                return

            self._pending_update = False

            try:
                # Start resize timer if available
                if self._cached_attributes["has_resize_timer"]:
                    self.main_window.resize_timer.start()

                self.logger.debug("Executed debounced thumbnail size update")

            except Exception as e:
                self.logger.error(f"Error in debounced update: {e}", exc_info=True)

    def handle_resize_event(self, event):
        """
        Obsługuje zdarzenie zmiany rozmiaru okna z improved error handling.

        Args:
            event: QResizeEvent z Qt
        """
        try:
            # Wywołaj oryginalną metodę resizeEvent z QMainWindow
            QMainWindow.resizeEvent(self.main_window, event)

            # Validate event
            if not event or not hasattr(event, "size"):
                self.logger.warning("Invalid resize event received")
                return

            # Start debounced resize update
            self._start_debounced_resize()

            # Log resize for debugging
            new_size = event.size()
            self.logger.debug(
                f"Window resized to: {new_size.width()}x{new_size.height()}"
            )

        except Exception as e:
            self.logger.error(f"Error handling resize event: {e}", exc_info=True)

    def _start_debounced_resize(self):
        """Uruchamia debounced resize update."""
        with self._lock:
            if self._cached_attributes["has_resize_timer"]:
                self.main_window.resize_timer.start()
            else:
                # Fallback - direct update if no timer available
                self._execute_resize_update()

    def _execute_resize_update(self):
        """Wykonuje update po resize z fallback mechanism."""
        try:
            if self._cached_attributes["has_current_thumbnail_size"]:
                current_size = getattr(
                    self.main_window,
                    "current_thumbnail_size",
                    self.size_config.default_size,
                )
                self._update_gallery_thumbnail_size(current_size)

        except Exception as e:
            self.logger.error(f"Error in resize update: {e}", exc_info=True)

    def on_resize_timer_timeout(self):
        """
        Aktualizuje widok galerii po zakończeniu zmiany rozmiaru.
        OPTYMALIZACJA: Używa dependency injection z fallback.
        """
        start_time = time.time()

        try:
            current_size = self._get_current_thumbnail_size()

            if not self.size_calculator.validate_size(current_size):
                self.logger.warning(
                    f"Invalid thumbnail size {current_size}, using default {self.size_config.default_size}"
                )
                current_size = self.size_config.default_size

            self._update_gallery_thumbnail_size(current_size)

            elapsed = time.time() - start_time
            self.logger.debug(
                f"Resize timeout update completed in {elapsed:.3f}s: {current_size}px"
            )

        except Exception as e:
            self.logger.error(f"Error in resize timeout: {e}", exc_info=True)

    def _get_current_thumbnail_size(self) -> int:
        """Bezpiecznie pobiera aktualny rozmiar miniaturek."""
        if self._cached_attributes["has_current_thumbnail_size"]:
            return getattr(
                self.main_window,
                "current_thumbnail_size",
                self.size_config.default_size,
            )
        return self.size_config.default_size

    def _update_gallery_thumbnail_size(self, size: int):
        """Aktualizuje rozmiar miniaturek w galerii i zakładce parowania."""
        # Aktualizuj galerię
        if self._gallery_manager:
            try:
                self._gallery_manager.update_thumbnail_size(size)
                self.logger.debug(f"Gallery thumbnail size updated to: {size}px")
            except Exception as e:
                self.logger.error(f"Failed to update gallery thumbnail size: {e}")
        elif (
            hasattr(self.main_window, "gallery_manager")
            and self.main_window.gallery_manager
        ):
            try:
                self.main_window.gallery_manager.update_thumbnail_size(size)
                self.logger.debug(
                    f"Gallery thumbnail size updated via fallback: {size}px"
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to update gallery thumbnail size via fallback: {e}"
                )
        else:
            self.logger.warning(
                "No gallery manager available for thumbnail size update"
            )

        # Aktualizuj zakładkę parowania
        if hasattr(self.main_window, "unpaired_files_tab_manager"):
            try:
                self.main_window.unpaired_files_tab_manager.update_thumbnail_size(size)
                self.logger.debug(
                    f"Unpaired files tab thumbnail size updated to: {size}px"
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to update unpaired files tab thumbnail size: {e}"
                )
        elif hasattr(self.main_window, "unpaired_files_tab"):
            try:
                self.main_window.unpaired_files_tab.update_thumbnail_size(size)
                self.logger.debug(
                    f"Unpaired files tab thumbnail size updated via fallback: {size}px"
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to update unpaired files tab thumbnail size via fallback: {e}"
                )
        else:
            self.logger.debug(
                "No unpaired files tab available for thumbnail size update"
            )

    def cleanup(self):
        """Czyści zasoby managera."""
        with self._lock:
            try:
                if self._debounce_timer:
                    self._debounce_timer.stop()
                    self._debounce_timer.deleteLater()
                    self._debounce_timer = None

                self._pending_update = False
                self.logger.debug("ThumbnailSizeManager cleanup completed")

            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")

    def get_performance_stats(self) -> dict:
        """Zwraca statystyki wydajności."""
        with self._lock:
            return {
                "update_count": self._update_count,
                "last_update_time": self._last_update_time,
                "config": {
                    "min_size": self.size_config.min_size,
                    "max_size": self.size_config.max_size,
                    "debounce_delay_ms": self.size_config.debounce_delay_ms,
                },
                "has_debounce_timer": self._debounce_timer is not None,
                "pending_update": self._pending_update,
            }

    def invalidate_cache(self):
        """Odświeża cache atrybutów main_window."""
        with self._lock:
            self._cached_attributes = self._cache_main_window_attributes()
            self.logger.debug("Main window attributes cache invalidated")

    def force_update(self):
        """Wymusza natychmiastową aktualizację bez debouncing."""
        with self._lock:
            try:
                # Stop any pending debounced updates
                if self._debounce_timer:
                    self._debounce_timer.stop()

                self._pending_update = False

                # Execute immediate update
                current_size = self._get_current_thumbnail_size()
                self._update_gallery_thumbnail_size(current_size)

                self.logger.debug(f"Force update completed: {current_size}px")

            except Exception as e:
                self.logger.error(f"Error in force update: {e}", exc_info=True)

    def __del__(self):
        """Destruktor - cleanup resources."""
        try:
            self.cleanup()
        except Exception:
            pass  # Avoid exceptions in destructor
