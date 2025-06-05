# tests/unit/test_app_config_basic.py
"""
Podstawowe testy jednostkowe dla modułu app_config.py.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.app_config import AppConfig


class TestAppConfigBasic(unittest.TestCase):
    """Klasa testowa dla podstawowej funkcjonalności app_config."""

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

    def test_default_config(self):
        """Test wczytywania domyślnej konfiguracji gdy plik nie istnieje."""
        # Plik nie powinien istnieć po inicjalizacji
        self.assertFalse(os.path.exists(self.test_config_path))

        # Sprawdź czy konfiguracja zawiera domyślne wartości
        self.assertEqual(self.app_config.get_thumbnail_slider_position(), 50)
        self.assertIsInstance(self.app_config.supported_archive_extensions, list)
        self.assertIsInstance(self.app_config.supported_preview_extensions, list)

    def test_save_and_load_config(self):
        """Test zapisywania i wczytywania konfiguracji z pliku."""
        # Zmodyfikuj konfigurację
        test_position = 75
        self.app_config.set_thumbnail_slider_position(test_position)

        # Sprawdź czy plik został utworzony
        self.assertTrue(os.path.exists(self.test_config_path))

        # Utwórz nową instancję do wczytania konfiguracji
        new_config = AppConfig(
            config_dir=self.test_config_dir, config_file=self.test_config_file
        )

        # Sprawdź czy wartość została poprawnie zapisana i wczytana
        self.assertEqual(new_config.get_thumbnail_slider_position(), test_position)

    def test_update_single_parameter(self):
        """Test aktualizacji pojedynczego parametru."""
        # Zmodyfikuj pojedynczy parametr
        self.app_config.set("thumbnail_size", 200)

        # Sprawdź czy wartość została zaktualizowana
        self.assertEqual(self.app_config.get("thumbnail_size"), 200)

        # Sprawdź czy wartość została zapisana do pliku
        with open(self.test_config_path, "r") as f:
            saved_config = json.load(f)
            self.assertEqual(saved_config["thumbnail_size"], 200)


if __name__ == "__main__":
    unittest.main()
