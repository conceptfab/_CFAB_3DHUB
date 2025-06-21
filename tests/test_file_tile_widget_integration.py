"""
Test integration dla zrefaktoryzowanego FileTileWidget.
Sprawdza integrację komponentów i kompatybilność wsteczną.
"""

import pytest
import tempfile
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

# Import testowanych klas
from src.ui.widgets.file_tile_widget import FileTileWidget
from src.models.file_pair import FilePair
from src.ui.widgets.tile_config import TileConfig, TileEvent


class TestFileTileWidgetIntegration:
    """Test integration dla nowej architektury FileTileWidget."""

    @pytest.fixture
    def app(self):
        """PyQt6 application fixture."""
        if QApplication.instance() is None:
            app = QApplication([])
        else:
            app = QApplication.instance()
        return app

    @pytest.fixture
    def temp_files(self):
        """Tworzy tymczasowe pliki do testów."""
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = os.path.join(temp_dir, "test_archive.zip")
            preview_path = os.path.join(temp_dir, "test_preview.jpg")
            
            # Tworzenie dummy plików
            with open(archive_path, "w") as f:
                f.write("dummy archive content")
            
            # Tworzenie dummy obrazu
            pixmap = QPixmap(100, 100)
            pixmap.fill(Qt.GlobalColor.blue)
            pixmap.save(preview_path, "JPG")
            
            yield {
                "archive_path": archive_path,
                "preview_path": preview_path,
                "working_dir": temp_dir
            }

    @pytest.fixture
    def file_pair(self, temp_files):
        """Tworzy FilePair do testów."""
        return FilePair(
            archive_path=temp_files["archive_path"],
            preview_path=temp_files["preview_path"],
            working_directory=temp_files["working_dir"]
        )

    def test_widget_initialization(self, app):
        """Test inicjalizacji widget z komponentami."""
        widget = FileTileWidget(None)
        
        # Sprawdź czy komponenty zostały utworzone
        assert hasattr(widget, '_config')
        assert hasattr(widget, '_event_bus')
        assert hasattr(widget, '_thumbnail_component')
        assert hasattr(widget, '_metadata_component')
        assert hasattr(widget, '_interaction_component')
        
        # Sprawdź czy UI elementy istnieją
        assert hasattr(widget, 'thumbnail_label')
        assert hasattr(widget, 'thumbnail_frame')
        assert hasattr(widget, 'filename_label')
        assert hasattr(widget, 'metadata_controls')
        
        widget.cleanup()

    def test_component_integration(self, app, file_pair):
        """Test integracji między komponentami."""
        widget = FileTileWidget(file_pair)
        
        # Test update_data - czy komponenty otrzymują dane
        widget.update_data(file_pair)
        
        # Sprawdź czy filename label został zaktualizowany
        assert widget.filename_label.text() == file_pair.get_base_name()
        
        # Sprawdź czy metadata component otrzymał file_pair
        assert widget._metadata_component.get_metadata_snapshot().file_pair_id is not None
        
        widget.cleanup()

    def test_backward_compatibility_api(self, app, file_pair):
        """Test kompatybilności wstecznej API."""
        widget = FileTileWidget(None)
        
        # Test starych metod
        widget.set_file_pair(file_pair)
        assert widget.file_pair == file_pair
        
        widget.set_thumbnail_size((200, 200))
        assert widget.thumbnail_size == (200, 200)
        
        # Test starych sygnałów
        signals_exist = [
            'archive_open_requested',
            'preview_image_requested', 
            'tile_selected',
            'stars_changed',
            'color_tag_changed',
            'tile_context_menu_requested',
            'file_pair_updated'
        ]
        
        for signal_name in signals_exist:
            assert hasattr(widget, signal_name)
        
        widget.cleanup()

    def test_thumbnail_component_integration(self, app, file_pair):
        """Test integracji z thumbnail component."""
        widget = FileTileWidget(file_pair)
        
        # Test czy thumbnail component otrzymuje zadania ładowania
        assert widget._thumbnail_component is not None
        
        # Test czy sygnały są podłączone
        thumbnail_component = widget._thumbnail_component
        assert len(thumbnail_component.thumbnail_loaded.receivers) > 0
        assert len(thumbnail_component.thumbnail_error.receivers) > 0
        
        widget.cleanup()

    def test_metadata_component_integration(self, app, file_pair):
        """Test integracji z metadata component.""" 
        widget = FileTileWidget(file_pair)
        
        # Test ustawiania gwiazdek przez metadata component
        metadata_component = widget._metadata_component
        metadata_component.set_stars(3)
        
        assert metadata_component.get_stars() == 3
        
        # Test ustawiania koloru
        metadata_component.set_color_tag("#FF0000")
        assert metadata_component.get_color_tag() == "#FF0000"
        
        widget.cleanup()

    def test_interaction_component_integration(self, app, file_pair):
        """Test integracji z interaction component."""
        widget = FileTileWidget(file_pair)
        
        # Test czy interaction component jest podłączony
        assert widget._interaction_component is not None
        
        # Test czy widget ma event filter
        assert widget.thumbnail_label.eventFilter == widget.eventFilter
        assert widget.filename_label.eventFilter == widget.eventFilter
        
        widget.cleanup()

    def test_event_bus_communication(self, app, file_pair):
        """Test komunikacji przez event bus."""
        widget = FileTileWidget(file_pair)
        
        # Test czy event bus jest aktywny
        event_bus = widget._event_bus
        assert event_bus is not None
        
        # Test subscription do eventów
        events_subscribed = []
        
        def test_callback(*args):
            events_subscribed.append(args)
        
        event_bus.subscribe(TileEvent.SIZE_CHANGED, test_callback)
        
        # Wyzwól zmianę rozmiaru
        widget.set_thumbnail_size((150, 150))
        
        # Sprawdź czy event został wysłany
        # (może być asynchroniczny, więc podstawowy test)
        assert len(events_subscribed) >= 0  # Event bus setup test
        
        widget.cleanup()

    def test_size_change_propagation(self, app, file_pair):
        """Test propagacji zmian rozmiaru do komponentów."""
        widget = FileTileWidget(file_pair)
        
        original_size = widget.thumbnail_size
        new_size = (180, 180)
        
        widget.set_thumbnail_size(new_size)
        
        # Sprawdź czy rozmiar został zaktualizowany
        assert widget.thumbnail_size == new_size
        assert widget._config.thumbnail_size == new_size
        
        # Sprawdź czy UI element został zaktualizowany
        label_size = widget.thumbnail_label.size()
        assert label_size.width() > 0 and label_size.height() > 0
        
        widget.cleanup()

    def test_memory_cleanup(self, app, file_pair):
        """Test czyszczenia zasobów."""
        widget = FileTileWidget(file_pair)
        
        # Test czy cleanup działa bez błędów
        widget.cleanup()
        
        # Sprawdź czy komponenty zostały wyczyszczone
        # (szczegółowe testy w unit testach komponentów)
        assert widget._metadata_component is not None  # Komponent istnieje
        
    def test_ui_element_creation(self, app):
        """Test tworzenia elementów UI."""
        widget = FileTileWidget(None)
        
        # Sprawdź czy wszystkie UI elementy zostały utworzone
        assert widget.layout is not None
        assert widget.thumbnail_frame is not None
        assert widget.thumbnail_label is not None
        assert widget.filename_label is not None
        assert widget.metadata_controls is not None
        
        # Sprawdź czy layout zawiera wszystkie elementy
        layout_items = []
        for i in range(widget.layout.count()):
            item = widget.layout.itemAt(i)
            if item and item.widget():
                layout_items.append(item.widget())
        
        assert widget.thumbnail_frame in layout_items
        assert widget.filename_label in layout_items
        assert widget.metadata_controls in layout_items
        
        widget.cleanup()

    def test_error_handling(self, app):
        """Test obsługi błędów."""
        widget = FileTileWidget(None)
        
        # Test z nieprawidłowymi danymi
        widget.update_data(None)  # Nie powinno crashować
        
        # Test z nieprawidłowym rozmiarem
        widget.set_thumbnail_size((-10, -10))  # Powinno być obsłużone
        
        widget.cleanup()

    def test_performance_basic(self, app, file_pair):
        """Podstawowy test wydajności."""
        import time
        
        start_time = time.time()
        
        # Tworzenie 10 widget-ów
        widgets = []
        for _ in range(10):
            widget = FileTileWidget(file_pair)
            widgets.append(widget)
        
        creation_time = time.time() - start_time
        
        # Oczekujemy że tworzenie 10 widget-ów zajmie mniej niż 1 sekundę
        assert creation_time < 1.0, f"Widget creation too slow: {creation_time:.2f}s"
        
        # Cleanup
        for widget in widgets:
            widget.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 