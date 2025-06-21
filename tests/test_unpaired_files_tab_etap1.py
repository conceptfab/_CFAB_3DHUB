"""
Test automatyczny dla ETAP 1 refaktoryzacji unpaired_files_tab.py
Sprawdza czy wydzielenie UnpairedPreviewTile działa poprawnie.
"""

import os
import shutil
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QWidget

# Import testowanych klas
from src.ui.widgets.unpaired_files_tab import UnpairedFilesTab
from src.ui.widgets.unpaired_preview_tile import UnpairedPreviewTile


class TestEtap1Refaktoryzacja:
    """Testy dla ETAP 1 - wydzielenie UnpairedPreviewTile"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Przygotowanie środowiska testowego"""
        # Upewnij się że QApplication istnieje
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

        # Mock głównego okna
        self.main_window = Mock()
        self.main_window.controller = Mock()
        self.main_window.controller.current_working_directory = "/test/path"
        self.main_window.worker_manager = Mock()

        # Utworz tymczasowy folder z plikami testowymi
        self.temp_dir = tempfile.mkdtemp()

        # Utwórz testowe pliki obrazów
        self.test_image_paths = []
        for i in range(3):
            image_path = os.path.join(self.temp_dir, f"test_image_{i}.jpg")
            # Utwórz pusty plik (nie jest to prawdziwy obraz, ale wystarczy do testów)
            with open(image_path, "w") as f:
                f.write("fake image data")
            self.test_image_paths.append(image_path)

        yield

        # Cleanup
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_unpaired_preview_tile_creation(self):
        """Test 1: Tworzenie UnpairedPreviewTile"""
        # Given
        preview_path = self.test_image_paths[0]

        # When
        tile = UnpairedPreviewTile(preview_path)

        # Then
        assert tile is not None
        assert tile.preview_path == preview_path
        assert hasattr(tile, "checkbox")
        assert hasattr(tile, "delete_button")
        assert hasattr(tile, "thumbnail_label")
        assert hasattr(tile, "filename_label")

        print("✅ Test 1 PASSED: UnpairedPreviewTile tworzy się poprawnie")

    def test_unpaired_preview_tile_signals(self):
        """Test 2: Sygnały UnpairedPreviewTile"""
        # Given
        preview_path = self.test_image_paths[0]
        tile = UnpairedPreviewTile(preview_path)

        # Mock callback
        signal_received = Mock()
        tile.preview_image_requested.connect(signal_received)

        # When
        tile.thumbnail_clicked()

        # Then
        signal_received.assert_called_once_with(preview_path)

        print("✅ Test 2 PASSED: Sygnały UnpairedPreviewTile działają")

    def test_unpaired_files_tab_uses_new_tile(self):
        """Test 3: UnpairedFilesTab używa nowej klasy UnpairedPreviewTile"""
        # Given
        tab = UnpairedFilesTab(self.main_window)
        tab.create_unpaired_files_tab()

        # Mock danych kontrolera
        self.main_window.controller.unpaired_archives = []
        self.main_window.controller.unpaired_previews = self.test_image_paths

        # When
        tab.update_unpaired_files_lists()

        # Then
        assert len(tab.preview_tile_widgets) == len(self.test_image_paths)

        # Sprawdź czy wszystkie kafelki to instancje UnpairedPreviewTile
        for tile in tab.preview_tile_widgets:
            assert isinstance(tile, UnpairedPreviewTile)

        print(
            "✅ Test 3 PASSED: UnpairedFilesTab używa nowej klasy UnpairedPreviewTile"
        )

    def test_thumbnail_size_update(self):
        """Test 4: Aktualizacja rozmiaru miniaturek"""
        # Given
        preview_path = self.test_image_paths[0]
        tile = UnpairedPreviewTile(preview_path)
        original_size = tile.thumbnail_size
        new_size = 200

        # When
        tile.set_thumbnail_size(new_size)

        # Then
        assert tile.thumbnail_size == new_size
        assert tile.thumbnail_size != original_size

        print("✅ Test 4 PASSED: Aktualizacja rozmiaru miniaturek działa")

    def test_checkbox_functionality(self):
        """Test 5: Funkcjonalność checkbox w kafelku"""
        # Given
        tab = UnpairedFilesTab(self.main_window)
        tab.create_unpaired_files_tab()

        # Mock danych
        self.main_window.controller.unpaired_archives = ["test_archive.zip"]
        self.main_window.controller.unpaired_previews = self.test_image_paths[:2]

        tab.update_unpaired_files_lists()

        # When - zaznacz pierwszy checkbox
        first_tile = tab.preview_tile_widgets[0]
        first_tile.checkbox.setChecked(True)

        # Symuluj wywołanie callback'a
        tab._on_preview_checkbox_changed(
            first_tile.checkbox, first_tile.preview_path, Qt.CheckState.Checked.value
        )

        # Then - sprawdź czy tylko jeden jest zaznaczony
        checked_count = sum(
            1 for tile in tab.preview_tile_widgets if tile.checkbox.isChecked()
        )
        assert checked_count == 1

        print("✅ Test 5 PASSED: Checkbox functionality działa poprawnie")

    def test_preview_dialog_integration(self):
        """Test 6: Integracja z PreviewDialog"""
        # Given
        preview_path = self.test_image_paths[0]
        tile = UnpairedPreviewTile(preview_path)

        # Mock PreviewDialog
        with patch("src.ui.widgets.unpaired_files_tab.PreviewDialog") as mock_dialog:
            mock_instance = Mock()
            mock_dialog.return_value = mock_instance

            tab = UnpairedFilesTab(self.main_window)

            # When
            tab._show_preview_dialog(preview_path)

            # Then
            mock_dialog.assert_called_once_with(preview_path, self.main_window)
            mock_instance.exec.assert_called_once()

        print("✅ Test 6 PASSED: Integracja z PreviewDialog działa")

    def test_delete_functionality(self):
        """Test 7: Funkcjonalność usuwania podglądu"""
        # Given
        tab = UnpairedFilesTab(self.main_window)
        tab.create_unpaired_files_tab()

        # Mock danych
        self.main_window.controller.unpaired_archives = []
        self.main_window.controller.unpaired_previews = [self.test_image_paths[0]]

        tab.update_unpaired_files_lists()
        initial_count = len(tab.preview_tile_widgets)

        # When
        tab._delete_preview_file(self.test_image_paths[0])

        # Then
        # Plik powinien być usunięty z layoutu
        final_count = len(tab.preview_tile_widgets)
        assert final_count < initial_count

        print("✅ Test 7 PASSED: Funkcjonalność usuwania działa")

    def test_backward_compatibility(self):
        """Test 8: Zachowanie kompatybilności wstecznej"""
        # Given
        tab = UnpairedFilesTab(self.main_window)
        widgets = tab.create_unpaired_files_tab()

        # Then - sprawdź czy wszystkie wymagane atrybuty istnieją
        required_attributes = [
            "unpaired_files_tab",
            "unpaired_archives_list_widget",
            "unpaired_previews_list_widget",
            "pair_manually_button",
            "preview_tile_widgets",
        ]

        for attr in required_attributes:
            assert hasattr(tab, attr), f"Brak atrybutu: {attr}"

        # Sprawdź czy metody publiczne istnieją
        required_methods = [
            "update_unpaired_files_lists",
            "clear_unpaired_files_lists",
            "update_thumbnail_size",
            "get_widgets_for_main_window",
        ]

        for method in required_methods:
            assert hasattr(tab, method), f"Brak metody: {method}"
            assert callable(getattr(tab, method)), f"Metoda {method} nie jest callable"

        print("✅ Test 8 PASSED: Kompatybilność wsteczna zachowana")

    def test_performance_with_many_tiles(self):
        """Test 9: Wydajność z wieloma kafelkami"""
        # Given
        tab = UnpairedFilesTab(self.main_window)
        tab.create_unpaired_files_tab()

        # Utwórz więcej testowych plików
        many_images = []
        for i in range(20):  # 20 kafelków
            image_path = os.path.join(self.temp_dir, f"perf_test_{i}.jpg")
            with open(image_path, "w") as f:
                f.write("fake image data")
            many_images.append(image_path)

        self.main_window.controller.unpaired_archives = []
        self.main_window.controller.unpaired_previews = many_images

        # When - measure time
        import time

        start_time = time.time()
        tab.update_unpaired_files_lists()
        end_time = time.time()

        # Then
        creation_time = end_time - start_time
        assert (
            creation_time < 2.0
        ), f"Tworzenie 20 kafelków trwało {creation_time:.2f}s (za długo!)"
        assert len(tab.preview_tile_widgets) == 20

        print(f"✅ Test 9 PASSED: Wydajność OK - 20 kafelków w {creation_time:.2f}s")

    def test_memory_cleanup(self):
        """Test 10: Czyszczenie pamięci"""
        # Given
        tab = UnpairedFilesTab(self.main_window)
        tab.create_unpaired_files_tab()

        self.main_window.controller.unpaired_archives = []
        self.main_window.controller.unpaired_previews = self.test_image_paths

        tab.update_unpaired_files_lists()
        initial_count = len(tab.preview_tile_widgets)

        # When
        tab.clear_unpaired_files_lists()

        # Then
        assert len(tab.preview_tile_widgets) == 0
        assert tab.unpaired_previews_list_widget.count() == 0

        print("✅ Test 10 PASSED: Czyszczenie pamięci działa poprawnie")


def run_etap1_tests():
    """Uruchom wszystkie testy dla ETAP 1"""
    print("🧪 ROZPOCZYNAM TESTY ETAP 1 - REFAKTORYZACJA UNPAIRED_FILES_TAB.PY")
    print("=" * 70)

    # Uruchom pytest dla tego pliku
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    print("=" * 70)

    if result.returncode == 0:
        print("🎉 WSZYSTKIE TESTY ETAP 1 PRZESZŁY POMYŚLNIE!")
        print("✅ ETAP 1 UKOŃCZONY - UnpairedPreviewTile wydzielony poprawnie")
        return True
    else:
        print("❌ NIEKTÓRE TESTY ETAP 1 NIE PRZESZŁY!")
        print("🔧 WYMAGANE POPRAWKI PRZED PRZEJŚCIEM DO ETAP 2")
        return False


if __name__ == "__main__":
    run_etap1_tests()
