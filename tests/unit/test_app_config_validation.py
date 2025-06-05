# tests/unit/test_app_config_validation.py
"""
Testy walidacji dla modułu app_config.py.
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.app_config import AppConfig


class TestAppConfigValidation(unittest.TestCase):
    """Klasa testowa dla funkcjonalności walidacji w app_config."""

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

    def test_input_validation(self):
        """Test walidacji danych wejściowych."""
        # Poprawna wartość
        self.assertTrue(self.app_config.set_thumbnail_slider_position(80))

        # Niepoprawne wartości - powinny rzucić wyjątek ValueError
        with self.assertRaises(ValueError):
            self.app_config.set_thumbnail_slider_position("niepoprawna")

        with self.assertRaises(ValueError):
            self.app_config.set_thumbnail_slider_position(-10)

        with self.assertRaises(ValueError):
            self.app_config.set_thumbnail_slider_position(110)

    def test_supported_extensions(self):
        """Test obsługi rozszerzeń plików."""
        # Test pobierania rozszerzeń
        archive_exts = self.app_config.get_supported_extensions("archive")
        preview_exts = self.app_config.get_supported_extensions("preview")

        self.assertIsInstance(archive_exts, list)
        self.assertIsInstance(preview_exts, list)

        # Test ustawiania rozszerzeń
        new_archive_exts = [".zip", ".rar"]
        self.app_config.set_supported_extensions("archive", new_archive_exts)

        # Sprawdź czy wartości zostały zaktualizowane
        self.assertEqual(self.app_config.supported_archive_extensions, new_archive_exts)

        # Test normalizacji rozszerzeń
        unnormalized_exts = ["png", "jpg", ".gif"]
        expected_exts = [".png", ".jpg", ".gif"]
        self.app_config.set_supported_extensions("preview", unnormalized_exts)
        self.assertEqual(self.app_config.supported_preview_extensions, expected_exts)


if __name__ == "__main__":
    unittest.main()
