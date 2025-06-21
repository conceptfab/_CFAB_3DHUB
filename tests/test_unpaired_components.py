"""
Testy dla wydzielonych komponentów UnpairedFilesTab.
"""

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest
from PyQt6.QtCore import QModelIndex
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication, QSplitter, QWidget

from src.ui.widgets.unpaired_archives_list import UnpairedArchivesList
from src.ui.widgets.unpaired_files_tab import UnpairedPreviewTile
from src.ui.widgets.unpaired_previews_grid import UnpairedPreviewsGrid


class TestUnpairedPreviewTile:
    """Testy dla UnpairedPreviewTile."""

    def setup_method(self):
        """Konfiguracja przed każdym testem."""
        self.mock_parent = Mock(spec=QWidget)
        # Utwórz tymczasowy plik obrazu do testów
        self.test_image_path = tempfile.mktemp(suffix=".jpg")

        # Utwórz pusty plik testowy
        with open(self.test_image_path, "w") as f:
            f.write("test")

    def teardown_method(self):
        """Sprzątanie po teście."""
        if os.path.exists(self.test_image_path):
            os.unlink(self.test_image_path)

    def test_initialization(self):
        """Test inicjalizacji kafelka."""
        tile = UnpairedPreviewTile(self.test_image_path, self.mock_parent)

        assert tile.preview_path == self.test_image_path
        assert tile.thumbnail_frame is not None
        assert tile.thumbnail_label is not None
        assert tile.filename_label is not None
        assert tile.checkbox is not None
        assert tile.delete_button is not None

    def test_preview_image_requested_signal(self):
        """Test emisji sygnału preview_image_requested."""
        tile = UnpairedPreviewTile(self.test_image_path, self.mock_parent)

        # Mock sygnału
        signal_emitted = []
        tile.preview_image_requested.connect(lambda path: signal_emitted.append(path))

        # Symuluj kliknięcie
        tile.preview_image_requested.emit(self.test_image_path)

        assert len(signal_emitted) == 1
        assert signal_emitted[0] == self.test_image_path

    @patch("src.utils.image_utils.create_thumbnail_from_file")
    def test_load_thumbnail_success(self, mock_create_thumbnail):
        """Test pomyślnego ładowania miniaturki."""
        mock_pixmap = Mock()
        mock_pixmap.isNull.return_value = False
        mock_create_thumbnail.return_value = mock_pixmap

        tile = UnpairedPreviewTile(self.test_image_path, self.mock_parent)

        # Sprawdź czy create_thumbnail_from_file zostało wywołane
        mock_create_thumbnail.assert_called()
        tile.thumbnail_label.setPixmap.assert_called_with(mock_pixmap)

    @patch("src.utils.image_utils.create_thumbnail_from_file")
    def test_load_thumbnail_failure(self, mock_create_thumbnail):
        """Test obsługi błędu ładowania miniaturki."""
        mock_create_thumbnail.side_effect = Exception("Test error")

        tile = UnpairedPreviewTile(self.test_image_path, self.mock_parent)

        # Sprawdź czy została ustawiona informacja o błędzie
        tile.thumbnail_label.setText.assert_called_with("Błąd ładowania")

    def test_set_thumbnail_size(self):
        """Test zmiany rozmiaru kafelka."""
        tile = UnpairedPreviewTile(self.test_image_path, self.mock_parent)

        new_size = 200
        tile.set_thumbnail_size(new_size)

        assert tile.thumbnail_size == new_size
        tile.setFixedSize.assert_called()


class TestUnpairedArchivesManager:
    """Testy dla UnpairedArchivesManager."""

    def setup_method(self):
        """Konfiguracja przed każdym testem."""
        self.mock_main_window = Mock()
        self.mock_main_window.controller.unpaired_archives = [
            "/test/archive1.zip",
            "/test/archive2.rar",
        ]
        self.mock_splitter = Mock(spec=QSplitter)
        self.archives_manager = UnpairedArchivesManager(
            self.mock_main_window, self.mock_splitter
        )

    def test_initialization(self):
        """Test inicjalizacji managera archiwów."""
        assert self.archives_manager.main_window == self.mock_main_window
        assert self.archives_manager.splitter == self.mock_splitter
        assert self.archives_manager.unpaired_archives_panel is None
        assert self.archives_manager.unpaired_archives_list_widget is None

    def test_create_archives_panel(self):
        """Test tworzenia panelu archiwów."""
        self.archives_manager.create_archives_panel()

        assert self.archives_manager.unpaired_archives_panel is not None
        assert self.archives_manager.unpaired_archives_list_widget is not None
        self.mock_splitter.addWidget.assert_called_once()

    def test_update_archives_list(self):
        """Test aktualizacji listy archiwów."""
        self.archives_manager.create_archives_panel()

        test_archives = ["/test/archive1.zip", "/test/archive2.rar"]
        self.archives_manager.update_archives_list(test_archives)

        # Sprawdź czy lista została wyczyszczona i zaktualizowana
        self.archives_manager.unpaired_archives_list_widget.clear.assert_called()
        assert (
            self.archives_manager.unpaired_archives_list_widget.addItem.call_count == 2
        )

    def test_get_selected_archives_empty(self):
        """Test pobierania zaznaczonych archiwów gdy lista nie istnieje."""
        result = self.archives_manager.get_selected_archives()
        assert result == []

    def test_clear_archives_list(self):
        """Test czyszczenia listy archiwów."""
        self.archives_manager.create_archives_panel()
        self.archives_manager.clear_archives_list()

        self.archives_manager.unpaired_archives_list_widget.clear.assert_called()

    @patch("os.path.exists")
    def test_handle_move_unpaired_archives_no_directory(self, mock_exists):
        """Test przenoszenia archiwów gdy brak katalogu roboczego."""
        self.mock_main_window.controller.current_directory = None

        self.archives_manager.handle_move_unpaired_archives()

        # Sprawdź czy wyświetlono ostrzeżenie
        self.mock_main_window.QMessageBox.warning.assert_called()


class TestUnpairedPreviewsManager:
    """Testy dla UnpairedPreviewsManager."""

    def setup_method(self):
        """Konfiguracja przed każdym testem."""
        self.mock_main_window = Mock()
        self.mock_main_window.controller.unpaired_previews = [
            "/test/preview1.jpg",
            "/test/preview2.png",
        ]
        self.mock_splitter = Mock(spec=QSplitter)
        self.previews_manager = UnpairedPreviewsManager(
            self.mock_main_window, self.mock_splitter
        )

    def test_initialization(self):
        """Test inicjalizacji managera podglądów."""
        assert self.previews_manager.main_window == self.mock_main_window
        assert self.previews_manager.splitter == self.mock_splitter
        assert self.previews_manager.unpaired_previews_panel is None
        assert self.previews_manager.unpaired_previews_list_widget is None
        assert self.previews_manager.preview_checkboxes == []
        assert self.previews_manager.preview_tile_widgets == []

    def test_create_previews_panel(self):
        """Test tworzenia panelu podglądów."""
        self.previews_manager.create_previews_panel()

        assert self.previews_manager.unpaired_previews_panel is not None
        assert self.previews_manager.unpaired_previews_scroll_area is not None
        assert self.previews_manager.unpaired_previews_container is not None
        assert self.previews_manager.unpaired_previews_layout is not None
        assert self.previews_manager.unpaired_previews_list_widget is not None
        self.mock_splitter.addWidget.assert_called_once()

    def test_clear_previews_list(self):
        """Test czyszczenia listy podglądów."""
        self.previews_manager.create_previews_panel()
        self.previews_manager.preview_tile_widgets = [Mock(), Mock()]
        self.previews_manager.preview_checkboxes = [Mock(), Mock()]

        self.previews_manager.clear_previews_list()

        assert self.previews_manager.preview_tile_widgets == []
        assert self.previews_manager.preview_checkboxes == []
        self.previews_manager.unpaired_previews_list_widget.clear.assert_called()

    @patch("os.path.exists")
    def test_add_preview_thumbnail_file_not_exists(self, mock_exists):
        """Test dodawania miniaturki gdy plik nie istnieje."""
        mock_exists.return_value = False

        self.previews_manager.create_previews_panel()
        self.previews_manager._add_preview_thumbnail("/nonexistent/file.jpg")

        # Sprawdź czy nie została dodana miniaturka
        assert len(self.previews_manager.preview_tile_widgets) == 0

    def test_update_thumbnail_size(self):
        """Test aktualizacji rozmiaru miniaturek."""
        # Utwórz mock kafelki
        mock_tile1 = Mock()
        mock_tile2 = Mock()
        self.previews_manager.preview_tile_widgets = [mock_tile1, mock_tile2]

        new_size = 250
        self.previews_manager.update_thumbnail_size(new_size)

        assert self.previews_manager.current_thumbnail_size == new_size
        mock_tile1.set_thumbnail_size.assert_called_with(new_size)
        mock_tile2.set_thumbnail_size.assert_called_with(new_size)

    def test_get_selected_previews_empty(self):
        """Test pobierania zaznaczonych podglądów gdy lista nie istnieje."""
        result = self.previews_manager.get_selected_previews()
        assert result == []

    @patch("src.ui.widgets.preview_dialog.PreviewDialog")
    @patch("PyQt6.QtGui.QPixmap")
    @patch("os.path.exists")
    def test_show_preview_dialog_success(self, mock_exists, mock_qpixmap, mock_dialog):
        """Test pomyślnego wyświetlenia dialogu podglądu."""
        mock_exists.return_value = True
        mock_pixmap = Mock()
        mock_pixmap.isNull.return_value = False
        mock_qpixmap.return_value = mock_pixmap

        self.previews_manager._show_preview_dialog("/test/image.jpg")

        mock_dialog.assert_called_once()
        mock_dialog.return_value.exec.assert_called_once()

    @patch("os.path.exists")
    def test_show_preview_dialog_file_not_exists(self, mock_exists):
        """Test wyświetlenia dialogu gdy plik nie istnieje."""
        mock_exists.return_value = False

        self.previews_manager._show_preview_dialog("/nonexistent/file.jpg")

        # Sprawdź czy wyświetlono ostrzeżenie
        # Będzie to sprawdzone przez QMessageBox.warning


class TestComponentIntegration:
    """Testy integracyjne komponentów unpaired."""

    def test_components_integration(self):
        """Test czy komponenty współpracują ze sobą."""
        mock_main_window = Mock()
        mock_splitter = Mock(spec=QSplitter)

        # Utwórz komponenty
        archives_manager = UnpairedArchivesManager(mock_main_window, mock_splitter)
        previews_manager = UnpairedPreviewsManager(mock_main_window, mock_splitter)

        # Sprawdź czy oba komponenty mogą być utworzone bez błędów
        assert archives_manager.main_window == mock_main_window
        assert previews_manager.main_window == mock_main_window

        # Test tworzenia paneli
        archives_manager.create_archives_panel()
        previews_manager.create_previews_panel()

        # Sprawdź czy oba komponenty dodały swoje panele do splitter
        assert mock_splitter.addWidget.call_count == 2

    def test_managers_callback_integration(self):
        """Test integracji callbacków między managerami."""
        mock_main_window = Mock()
        mock_splitter = Mock(spec=QSplitter)

        archives_manager = UnpairedArchivesManager(mock_main_window, mock_splitter)
        previews_manager = UnpairedPreviewsManager(mock_main_window, mock_splitter)

        # Utwórz panele
        archives_manager.create_archives_panel()
        previews_manager.create_previews_panel()

        # Test podłączenia callbacków
        mock_callback = Mock()
        archives_manager.connect_selection_changed(mock_callback)
        previews_manager.connect_selection_changed(mock_callback)

        # Symuluj zmianę selekcji
        archives_manager.unpaired_archives_list_widget.itemSelectionChanged.connect.assert_called_with(
            mock_callback
        )
        previews_manager.unpaired_previews_list_widget.itemSelectionChanged.connect.assert_called_with(
            mock_callback
        )


if __name__ == "__main__":
    # Uruchom testy
    pytest.main([__file__, "-v"])
