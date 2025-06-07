#!/usr/bin/env python3
"""
Test sygnałów UI dla metadanych
"""
import os
import sys

# Dodaj projekt do ścieżki
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

# Ustawienie logowania
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

from src.models.file_pair import FilePair
from src.ui.widgets.file_tile_widget import FileTileWidget
from src.ui.widgets.metadata_controls_widget import MetadataControlsWidget


class SignalTester(QObject):
    """Klasa testująca sygnały"""

    def __init__(self):
        super().__init__()
        self.favorite_received = False
        self.stars_received = False
        self.color_received = False

    def on_favorite_changed(self, file_pair):
        print(
            f"🔥 SYGNAŁ FAVORITE OTRZYMANY: {file_pair.get_base_name()} -> {file_pair.is_favorite}"
        )
        self.favorite_received = True

    def on_stars_changed(self, file_pair, stars):
        print(f"🔥 SYGNAŁ STARS OTRZYMANY: {file_pair.get_base_name()} -> {stars}")
        self.stars_received = True

    def on_color_changed(self, file_pair, color):
        print(f"🔥 SYGNAŁ COLOR OTRZYMANY: {file_pair.get_base_name()} -> {color}")
        self.color_received = True


def test_signals():
    """Test sygnałów UI"""
    app = QApplication(sys.argv)

    print("🧪 Test sygnałów UI")

    # Stwórz testowy katalog i FilePair
    test_dir = r"c:\_cloud\_CFAB_3DHUB\test_data"
    os.makedirs(test_dir, exist_ok=True)

    test_archive = os.path.join(test_dir, "test.zip")
    with open(test_archive, "w") as f:
        f.write("test")

    file_pair = FilePair(test_archive, None, test_dir)
    # Stwórz FileTileWidget
    tile_widget = FileTileWidget(file_pair)

    # Użyj MetadataControlsWidget z FileTileWidget (nie twórz nowej instancji!)
    metadata_widget = tile_widget.metadata_controls

    # Stwórz tester sygnałów
    tester = SignalTester()

    # Podłącz sygnały
    tile_widget.favorite_toggled.connect(tester.on_favorite_changed)
    tile_widget.stars_changed.connect(tester.on_stars_changed)
    tile_widget.color_tag_changed.connect(tester.on_color_changed)

    print("🔌 Sygnały podłączone")
    # Symuluj kliknięcia
    print("🖱️ Symulacja kliknięcia favorite...")
    print(f"   File pair w metadata_widget: {metadata_widget._file_pair}")
    print(
        f"   Current favorite status: {metadata_widget._file_pair.is_favorite if metadata_widget._file_pair else 'None'}"
    )
    metadata_widget.favorite_button.click()

    print("🖱️ Symulacja kliknięcia stars...")
    print(
        f"   Current stars: {metadata_widget._file_pair.get_stars() if metadata_widget._file_pair else 'None'}"
    )
    metadata_widget.star_buttons[2].click()  # 3 gwiazdki

    print("🖱️ Symulacja zmiany koloru...")
    print(
        f"   Current color: {metadata_widget._file_pair.get_color_tag() if metadata_widget._file_pair else 'None'}"
    )
    metadata_widget.color_tag_combo.setCurrentIndex(1)  # Czerwony
    metadata_widget._on_color_combo_activated(1)

    # Przetwórz eventy
    app.processEvents()

    print(f"✅ Test zakończony:")
    print(f"   Favorite signal: {tester.favorite_received}")
    print(f"   Stars signal: {tester.stars_received}")
    print(f"   Color signal: {tester.color_received}")

    return tester.favorite_received and tester.stars_received and tester.color_received


if __name__ == "__main__":
    success = test_signals()
    print(f"🎯 Test {'PASSED' if success else 'FAILED'}")
