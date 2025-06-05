# tests/unit/test_app_config_properties.py
"""
Testy właściwości i metod dla modułu app_config.py.
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.app_config import AppConfig


class TestAppConfigProperties(unittest.TestCase):
    """Klasa testowa dla właściwości i metod w app_config."""

    def setUp(self):
        """Przygotowanie środowiska przed każdym testem."""
        # Stwórz tymczasowy katalog na pliki konfiguracyjne
        self.test_config_dir = tempfile.mkdtemp()
        self.test_config_file = "test_config.json"
        self.test_config_path = os.path.join(
            self.test_config_dir, self.test_config_file
        )

        # Instancja obiektu konfiguracji dla testów
        self.app_config = AppConfig(
            config_dir=self.test_config_dir, config_file=self.test_config_file
        )

    def tearDown(self):
        """Czyszczenie po każdym teście."""
        # Usuń tymczasowy katalog i wszystkie pliki
        shutil.rmtree(self.test_config_dir)

    def test_thumbnail_size(self):
        """Test obliczania rozmiaru miniatur."""
        # Ustaw pozycję suwaka na 0 (minimalny rozmiar)
        self.app_config.set_thumbnail_slider_position(0)
        self.assertEqual(
            self.app_config.thumbnail_size,
            (self.app_config.min_thumbnail_size, self.app_config.min_thumbnail_size),
        )

        # Ustaw pozycję suwaka na 100 (maksymalny rozmiar)
        self.app_config.set_thumbnail_slider_position(100)
        self.assertEqual(
            self.app_config.thumbnail_size,
            (self.app_config.max_thumbnail_size, self.app_config.max_thumbnail_size),
        )

        # Ustaw pozycję suwaka na 50 (środkowa wartość)
        self.app_config.set_thumbnail_slider_position(50)
        expected_size = self.app_config.min_thumbnail_size + int(
            (self.app_config.max_thumbnail_size - self.app_config.min_thumbnail_size)
            * 0.5
        )
        self.assertEqual(self.app_config.thumbnail_size, (expected_size, expected_size))

    def test_predefined_colors(self):
        """Test obsługi predefiniowanych kolorów."""
        # Pobierz domyślne kolory
        colors = self.app_config.get_predefined_colors()
        self.assertIsInstance(colors, dict)
        self.assertIn("Czerwony", colors)

        # Zmodyfikuj kolory
        new_colors = {"Zielony": "#00FF00", "Niebieski": "#0000FF"}
        self.app_config.set_predefined_colors(new_colors)

        # Sprawdź czy wartości zostały zaktualizowane
        self.assertEqual(self.app_config.get_predefined_colors(), new_colors)


if __name__ == "__main__":
    unittest.main()
