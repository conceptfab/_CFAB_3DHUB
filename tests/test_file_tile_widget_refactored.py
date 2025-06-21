"""
ETAP 6: Testy automatyczne dla zrefaktoryzowanych modułów FileTileWidget.

Veryfikuje wszystkie zmiany z ETAPÓW 1-5:
- SafePerformanceMetric z graceful degradation
- CompatibilityAdapter z backward compatibility
- ThumbnailOperations z delegacją
- FileTileWidget z modułową architekturą
"""

import threading
import time
from unittest.mock import MagicMock, Mock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication, QWidget

from src.models.file_pair import FilePair
from src.ui.widgets.file_tile_widget import FileTileWidget
from src.ui.widgets.file_tile_widget_compatibility import CompatibilityAdapter

# Import testowanych modułów
from src.ui.widgets.file_tile_widget_performance import (
    SafePerformanceMetric,
    get_performance_metric,
)
from src.ui.widgets.file_tile_widget_thumbnail import ThumbnailOperations


class TestSafePerformanceMetric:
    """ETAP 1: Testy SafePerformanceMetric z graceful degradation."""

    def test_safe_performance_metric_available(self):
        """Test czy SafePerformanceMetric inicjalizuje się prawidłowo."""
        metric = SafePerformanceMetric()
        assert isinstance(metric, SafePerformanceMetric)
        # Może być True lub False w zależności od dostępności modułu
        assert isinstance(metric.is_available(), bool)

    def test_safe_performance_metric_no_crash_when_unavailable(self):
        """Test czy SafePerformanceMetric nie crashuje gdy moduł niedostępny."""
        with patch(
            "src.ui.widgets.file_tile_widget_performance.SafePerformanceMetric._initialize"
        ):
            metric = SafePerformanceMetric()
            metric._available = False
            metric._metric = None

            # Nie powinno crashować
            assert not metric.is_available()
            assert metric.create_metric("test") is None
            assert metric.safe_call("test_method") is None

    def test_global_performance_metric_instance(self):
        """Test czy globalna instancja działa."""
        metric1 = get_performance_metric()
        metric2 = get_performance_metric()
        assert metric1 is metric2  # Powinny być tą samą instancją


class TestCompatibilityAdapter:
    """ETAP 9: Testy CompatibilityAdapter z backward compatibility."""

    def setup_method(self):
        """Setup przed każdym testem."""
        self.mock_widget = Mock()
        self.adapter = CompatibilityAdapter(self.mock_widget)

    def test_compatibility_adapter_initialization(self):
        """Test czy CompatibilityAdapter inicjalizuje się prawidłowo."""
        assert self.adapter.widget is self.mock_widget
        assert hasattr(self.adapter, "_deprecation_warnings_shown")
        assert isinstance(self.adapter._deprecation_warnings_shown, set)

    def test_legacy_method_change_thumbnail_size(self):
        """Test czy legacy metoda change_thumbnail_size deleguje prawidłowo."""
        test_size = (150, 150)

        with patch("warnings.warn") as mock_warn:
            result = self.adapter.change_thumbnail_size_legacy(test_size)

            # Sprawdź czy wywołano prawidłową metodę na widget
            self.mock_widget.set_thumbnail_size.assert_called_once_with(test_size)

            # Sprawdź czy pokazano deprecation warning
            mock_warn.assert_called_once()
            warning_message = mock_warn.call_args[0][0]
            assert "change_thumbnail_size" in warning_message
            assert "deprecated" in warning_message

    def test_deprecation_warning_shown_only_once(self):
        """Test czy deprecation warning pokazuje się tylko raz na metodę."""
        with patch("warnings.warn") as mock_warn:
            # Pierwsze wywołanie - powinno pokazać warning
            self.adapter.change_thumbnail_size_legacy((100, 100))
            assert mock_warn.call_count == 1

            # Drugie wywołanie - NIE powinno pokazać warning
            self.adapter.change_thumbnail_size_legacy((200, 200))
            assert mock_warn.call_count == 1  # Nadal 1


class TestThumbnailOperations:
    """ETAP 5: Testy ThumbnailOperations z delegacją."""

    def setup_method(self):
        """Setup przed każdym testem."""
        self.mock_widget = Mock()
        # Konfiguracja mock widget
        self.mock_widget._cache_optimizer = Mock()
        self.mock_widget._resource_manager = Mock()
        self.mock_widget._performance_monitor = Mock()
        self.mock_widget._async_ui_manager = Mock()
        self.mock_widget._thumbnail_component = Mock()
        self.mock_widget.thumbnail_size = (150, 150)
        self.mock_widget.thumbnail_label = Mock()

        self.thumbnail_ops = ThumbnailOperations(self.mock_widget)

    def test_thumbnail_operations_initialization(self):
        """Test czy ThumbnailOperations inicjalizuje się prawidłowo."""
        assert self.thumbnail_ops.widget is self.mock_widget
        assert hasattr(self.thumbnail_ops, "logger")

    def test_generate_thumbnail_cache_key_valid_path(self):
        """Test generowania cache key dla prawidłowej ścieżki."""
        test_path = "/test/path/image.jpg"
        cache_key = self.thumbnail_ops.generate_thumbnail_cache_key(test_path)

        assert isinstance(cache_key, str)
        assert len(cache_key) == 32  # MD5 hash length

        # Test czy ta sama ścieżka zwraca ten sam key
        cache_key2 = self.thumbnail_ops.generate_thumbnail_cache_key(test_path)
        assert cache_key == cache_key2

    def test_generate_thumbnail_cache_key_empty_path(self):
        """Test generowania cache key dla pustej ścieżki."""
        cache_key = self.thumbnail_ops.generate_thumbnail_cache_key("")
        assert isinstance(cache_key, str)
        assert cache_key.startswith("empty_")

    def test_generate_thumbnail_cache_key_none_path(self):
        """Test generowania cache key dla None path."""
        cache_key = self.thumbnail_ops.generate_thumbnail_cache_key(None)
        assert isinstance(cache_key, str)
        assert cache_key.startswith("empty_")

    def test_load_thumbnail_with_cache_hit(self):
        """Test ładowania thumbnail z cache hit."""
        test_path = "/test/image.jpg"
        mock_pixmap = Mock(spec=QPixmap)

        # Konfiguruj cache hit
        self.mock_widget._cache_optimizer.get.return_value = mock_pixmap

        with patch.object(
            self.thumbnail_ops, "on_cached_thumbnail_loaded"
        ) as mock_cached:
            self.thumbnail_ops.load_thumbnail_with_resource_management(test_path)

            # Sprawdź czy wywołano cached thumbnail handler
            mock_cached.assert_called_once_with(mock_pixmap)

            # Sprawdź czy NIE wywołano direct loading
            self.mock_widget._thumbnail_component.load_thumbnail.assert_not_called()

    def test_load_thumbnail_cache_miss(self):
        """Test ładowania thumbnail z cache miss."""
        test_path = "/test/image.jpg"

        # Konfiguruj cache miss
        self.mock_widget._cache_optimizer.get.return_value = None
        self.mock_widget._resource_manager.can_start_worker.return_value = True
        self.mock_widget._resource_manager.register_worker.return_value = 123

        with patch.object(self.thumbnail_ops, "execute_thumbnail_load") as mock_execute:
            self.thumbnail_ops.load_thumbnail_with_resource_management(test_path)

            # Sprawdź czy wywołano direct loading
            mock_execute.assert_called_once()


class TestFileTileWidgetIntegration:
    """ETAP 5: Testy integracji FileTileWidget z nowymi modułami."""

    @pytest.fixture(autouse=True)
    def setup_qt_app(self, qapp):
        """Setup QApplication dla testów widget."""
        self.qapp = qapp

    def test_file_tile_widget_creates_modules(self):
        """Test czy FileTileWidget tworzy wszystkie wymagane moduły."""
        # Mock dependencies żeby nie tworzyć prawdziwych komponentów
        with patch("src.ui.widgets.file_tile_widget.get_resource_manager"), patch(
            "src.ui.widgets.file_tile_widget.TileConfig"
        ), patch("src.ui.widgets.file_tile_widget.TileEventBus"), patch(
            "src.ui.widgets.file_tile_widget.ThumbnailComponent"
        ), patch(
            "src.ui.widgets.file_tile_widget.TileMetadataComponent"
        ), patch(
            "src.ui.widgets.file_tile_widget.TileInteractionComponent"
        ):

            widget = FileTileWidget(file_pair=None)

            # Sprawdź czy moduły zostały utworzone
            assert hasattr(widget, "_compatibility_adapter")
            assert hasattr(widget, "_thumbnail_ops")
            assert isinstance(widget._compatibility_adapter, CompatibilityAdapter)
            assert isinstance(widget._thumbnail_ops, ThumbnailOperations)

    def test_file_tile_widget_delegates_to_modules(self):
        """Test czy FileTileWidget deleguje metody do odpowiednich modułów."""
        with patch("src.ui.widgets.file_tile_widget.get_resource_manager"), patch(
            "src.ui.widgets.file_tile_widget.TileConfig"
        ), patch("src.ui.widgets.file_tile_widget.TileEventBus"), patch(
            "src.ui.widgets.file_tile_widget.ThumbnailComponent"
        ), patch(
            "src.ui.widgets.file_tile_widget.TileMetadataComponent"
        ), patch(
            "src.ui.widgets.file_tile_widget.TileInteractionComponent"
        ):

            widget = FileTileWidget(file_pair=None)

            # Mock thumbnail operations
            widget._thumbnail_ops = Mock()

            # Test delegacji
            test_path = "/test/image.jpg"
            widget.load_thumbnail_with_resource_management(test_path)

            # Sprawdź czy wywołano metodę na module
            widget._thumbnail_ops.load_thumbnail_with_resource_management.assert_called_once_with(
                test_path
            )


class TestMemoryManagement:
    """ETAP 2: Testy zarządzania pamięcią i thread safety."""

    def test_thread_safe_cleanup(self):
        """Test czy cleanup jest thread-safe."""
        with patch("src.ui.widgets.file_tile_widget.get_resource_manager"), patch(
            "src.ui.widgets.file_tile_widget.TileConfig"
        ), patch("src.ui.widgets.file_tile_widget.TileEventBus"), patch(
            "src.ui.widgets.file_tile_widget.ThumbnailComponent"
        ), patch(
            "src.ui.widgets.file_tile_widget.TileMetadataComponent"
        ), patch(
            "src.ui.widgets.file_tile_widget.TileInteractionComponent"
        ):

            widget = FileTileWidget(file_pair=None)

            # Test wielowątkowego cleanup
            def cleanup_thread():
                widget.cleanup()

            threads = []
            for i in range(5):
                t = threading.Thread(target=cleanup_thread)
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            # Cleanup powinien się wykonać tylko raz
            assert widget._is_cleanup_done

    def test_event_tracking_cleanup(self):
        """Test czy event tracking jest prawidłowo wyczyszczony."""
        with patch("src.ui.widgets.file_tile_widget.get_resource_manager"), patch(
            "src.ui.widgets.file_tile_widget.TileConfig"
        ), patch("src.ui.widgets.file_tile_widget.TileEventBus"), patch(
            "src.ui.widgets.file_tile_widget.ThumbnailComponent"
        ), patch(
            "src.ui.widgets.file_tile_widget.TileMetadataComponent"
        ), patch(
            "src.ui.widgets.file_tile_widget.TileInteractionComponent"
        ):

            widget = FileTileWidget(file_pair=None)

            # Dodaj jakieś mock event subscriptions
            widget._event_subscriptions = [("test_event", lambda: None)]
            widget._signal_connections = [(Mock(), "test_signal", Mock())]
            widget._event_filters = [Mock()]

            # Wykonaj cleanup
            widget.cleanup()

            # Sprawdź czy wszystko zostało wyczyszczone
            assert len(widget._event_subscriptions) == 0
            assert len(widget._signal_connections) == 0
            assert len(widget._event_filters) == 0


class TestPerformanceOptimizations:
    """ETAP 3: Testy optymalizacji wydajności."""

    def test_cache_key_generation_performance(self):
        """Test wydajności generowania cache key."""
        thumbnail_ops = ThumbnailOperations(Mock())
        thumbnail_ops.widget.thumbnail_size = (150, 150)

        # Test na 1000 kluczy
        start_time = time.time()

        for i in range(1000):
            cache_key = thumbnail_ops.generate_thumbnail_cache_key(
                f"/test/path/{i}.jpg"
            )
            assert len(cache_key) == 32

        elapsed_time = time.time() - start_time

        # ETAP 3: Cache key generation powinno być < 10ms dla 1000 kluczy
        assert (
            elapsed_time < 0.01
        ), f"Cache key generation zbyt wolne: {elapsed_time:.3f}s"

    def test_thumbnail_operations_no_spam_logging(self):
        """Test czy thumbnail operations nie generują spam logging."""
        thumbnail_ops = ThumbnailOperations(Mock())

        with patch("src.ui.widgets.file_tile_widget_thumbnail.logging") as mock_logging:
            # Wykonaj operacje które wcześniej generowały spam
            for i in range(100):
                thumbnail_ops.generate_thumbnail_cache_key(f"/test/{i}.jpg")

            # Sprawdź czy nie ma zbyt dużo wywołań debug
            debug_calls = [call for call in mock_logging.debug.call_args_list]
            assert len(debug_calls) < 10, f"Zbyt dużo debug calls: {len(debug_calls)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
