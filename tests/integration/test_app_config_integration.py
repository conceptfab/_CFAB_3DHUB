# tests/integration/test_app_config_integration.py
"""
Testy integracyjne dla modułu app_config.py.
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Importy testowanych modułów
from src.app_config import AppConfig
from src.utils.path_utils import normalize_path


class TestAppConfigIntegration(unittest.TestCase):
    """Klasa testowa dla integracji app_config z innymi modułami."""

    def setUp(self):
        """Przygotowanie środowiska przed każdym testem."""
        # Stwórz tymczasowy katalog na pliki konfiguracyjne
        self.test_config_dir = tempfile.mkdtemp()
        self.test_config_file = "test_config.json"

        # Instancja obiektu konfiguracji dla testów
        self.app_config = AppConfig(
            config_dir=self.test_config_dir, config_file=self.test_config_file
        )

    def tearDown(self):
        """Czyszczenie po każdym teście."""
        # Usuń tymczasowy katalog i wszystkie pliki
        shutil.rmtree(self.test_config_dir)

    def test_integration_with_path_utils(self):
        """Test integracji z modułem path_utils."""
        # Sprawdź czy ścieżki w konfiguracji są normalizowane
        test_path = os.path.join(self.test_config_dir, "test\\path\\with\\backslashes")
        expected_path = normalize_path(test_path)

        # Użyjmy atrybutu prywatnego bezpośrednio do testów
        self.assertEqual(
            normalize_path(self.app_config._config_file_path),
            self.app_config._config_file_path,
        )

        # Dodatkowa weryfikacja normalizacji ścieżek
        config_dir_normalized = normalize_path(self.test_config_dir)
        config_file_path = os.path.join(config_dir_normalized, self.test_config_file)
        config_file_path_normalized = normalize_path(config_file_path)

        self.assertTrue(
            self.app_config._config_file_path.startswith(config_dir_normalized)
        )
        self.assertEqual(
            normalize_path(os.path.basename(self.app_config._config_file_path)),
            normalize_path(self.test_config_file),
        )

    def test_thumbnail_size_calculations(self):
        """
        Test obliczania rozmiarów miniatur na podstawie konfiguracji.
        Sprawdza spójność obliczeń przy różnych wartościach suwaka.
        """
        # Test dla różnych pozycji suwaka
        test_positions = [0, 25, 50, 75, 100]

        for pos in test_positions:
            # Ustaw pozycję suwaka
            self.app_config.set_thumbnail_slider_position(pos)

            # Oblicz oczekiwany rozmiar
            min_size = self.app_config.min_thumbnail_size
            max_size = self.app_config.max_thumbnail_size
            expected_size = min_size + int(((max_size - min_size) * pos) / 100)

            # Sprawdź czy rozmiar miniatury jest zgodny z oczekiwanym
            self.assertEqual(
                self.app_config.thumbnail_size, (expected_size, expected_size)
            )


if __name__ == "__main__":
    unittest.main()
