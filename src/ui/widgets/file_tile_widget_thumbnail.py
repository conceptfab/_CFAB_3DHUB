"""
Thumbnail operations dla FileTileWidget.

Zarządza wszystkimi operacjami thumbnail loading.
"""

import hashlib
import logging
import os
from typing import TYPE_CHECKING, Optional

from PyQt6.QtGui import QPixmap

if TYPE_CHECKING:
    from .file_tile_widget import FileTileWidget


class ThumbnailOperations:
    """Zarządza wszystkimi operacjami thumbnail dla FileTileWidget."""

    def __init__(self, widget: "FileTileWidget"):
        self.widget = widget

    def load_thumbnail_with_resource_management(self, path: str):
        """Streamlined performance thumbnail loading z reduced overhead."""
        try:
            cache_key = self.generate_thumbnail_cache_key(path)
            if self.widget._cache_optimizer:
                cached_thumbnail = self.widget._cache_optimizer.get(
                    "thumbnails", cache_key
                )
                if cached_thumbnail:
                    self.on_cached_thumbnail_loaded(cached_thumbnail)
                    return

            self.load_thumbnail_direct(path, cache_key)

        except Exception as e:
            self.load_thumbnail_fallback(path)

    def load_thumbnail_direct(self, path: str, cache_key: str):
        """Direct thumbnail loading z minimal resource overhead."""
        try:
            worker_id = None
            if (
                self.widget._resource_manager
                and self.widget._resource_manager.can_start_worker()
            ):
                worker_id = self.widget._resource_manager.register_worker()
            elif self.widget._resource_manager:
                self.defer_thumbnail_load(path, cache_key)
                return

            from .file_tile_widget_performance import get_performance_metric

            performance_metric = get_performance_metric()

            if performance_metric.is_available() and self.widget._performance_monitor:
                load_metric = performance_metric.create_metric("THUMBNAIL_LOAD_TIME")
                if load_metric:
                    with self.widget._performance_monitor.measure_operation(
                        load_metric, {"path": path}
                    ):
                        self.execute_thumbnail_load(path, cache_key, worker_id)
                    return

            self.execute_thumbnail_load(path, cache_key, worker_id)

        except Exception as e:
            if worker_id and self.widget._resource_manager:
                self.widget._resource_manager.unregister_worker(worker_id)
            raise

    def execute_thumbnail_load(
        self, path: str, cache_key: str, worker_id: Optional[int]
    ):
        """Core thumbnail loading execution."""
        try:
            if not os.path.exists(path):
                return

            if hasattr(self.widget, "_thumbnail_component"):
                self.widget._thumbnail_component.load_thumbnail(
                    path=path, size=self.widget.thumbnail_size
                )
            else:
                raise RuntimeError("Thumbnail component unavailable")

            self.cache_thumbnail_if_loaded(cache_key)

        except Exception as e:
            if not ("does not exist" in str(e) or "File not found" in str(e)):
                logger = logging.getLogger(__name__)
                logger.warning(f"Thumbnail loading error: {e}")
        finally:
            if worker_id and self.widget._resource_manager:
                self.widget._resource_manager.unregister_worker(worker_id)

    def defer_thumbnail_load(self, path: str, cache_key: str):
        """Intelligent thumbnail load deferring."""
        if self.widget._async_ui_manager:
            self.widget._async_ui_manager.schedule_thumbnail_load(
                lambda: self.load_thumbnail_direct(path, cache_key),
                path,
                callback=None,
            )

    def cache_thumbnail_if_loaded(self, cache_key: str):
        """Simplified thumbnail caching."""
        if not cache_key or not self.widget._cache_optimizer:
            return

        try:
            if hasattr(self.widget, "thumbnail_label"):
                thumbnail_pixmap = self.widget.thumbnail_label.pixmap()
                if thumbnail_pixmap and not thumbnail_pixmap.isNull():
                    estimated_size = (
                        thumbnail_pixmap.width() * thumbnail_pixmap.height() * 4
                    )
                    self.widget._cache_optimizer.put(
                        "thumbnails", cache_key, thumbnail_pixmap, estimated_size
                    )
        except Exception:
            pass

    def load_thumbnail_fallback(self, path: str):
        """Minimal fallback thumbnail loading."""
        try:
            if hasattr(self.widget, "_thumbnail_component"):
                self.widget._thumbnail_component.load_thumbnail(
                    path=path, size=self.widget.thumbnail_size
                )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Fallback thumbnail loading failed: {e}")

    def generate_thumbnail_cache_key(self, path: str) -> str:
        """Optimized cache key generation z minimal overhead."""
        if not path:
            return f"empty_{id(self.widget)}"

        try:
            size_str = "default"
            if hasattr(self.widget, "thumbnail_size") and self.widget.thumbnail_size:
                try:
                    size_str = f"{self.widget.thumbnail_size[0]}x{self.widget.thumbnail_size[1]}"
                except (IndexError, TypeError):
                    pass

            key_data = f"{path}_{size_str}"
            return hashlib.md5(key_data.encode("utf-8", errors="replace")).hexdigest()

        except Exception:
            return f"fallback_{abs(hash(path)) % 1000000}_{id(self.widget) % 1000}"

    def on_cached_thumbnail_loaded(self, cached_thumbnail):
        """Obsługuje załadowaną cached thumbnail."""
        if isinstance(cached_thumbnail, QPixmap) and hasattr(
            self.widget, "thumbnail_label"
        ):
            self.widget.thumbnail_label.setPixmap(cached_thumbnail)
        else:
            logger = logging.getLogger(__name__)
            logger.warning("Invalid cached thumbnail type")

    def on_async_thumbnail_loaded(self, result):
        """Callback dla async thumbnail loading."""
        pass

    def do_thumbnail_load(
        self,
        path: str,
        worker_id: Optional[int] = None,
        cache_key: Optional[str] = None,
    ):
        """Legacy compatibility wrapper - deleguje do nowej implementacji."""
        self.execute_thumbnail_load(path, cache_key or "", worker_id)
