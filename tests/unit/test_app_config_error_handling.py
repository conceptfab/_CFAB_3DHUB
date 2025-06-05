# tests/unit/test_app_config_error_handling.py
"""
Testy obsługi błędów dla modułu app_config.py.
"""

import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.app_config import AppConfig


class TestAppConfigErrorHandling(unittest.TestCase):
    """Klasa testowa dla obsługi błędów w app_config."""

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

    def test_invalid_config_file(self):
        """Test obsługi uszkodzonego pliku konfiguracyjnego."""
        # Zapisz nieprawidłowy JSON do pliku konfiguracyjnego
        os.makedirs(self.test_config_dir, exist_ok=True)
        with open(self.test_config_path, "w", encoding="utf-8") as f:
            f.write('{"invalid": json')

        # Utwórz nową instancję - powinna wczytać domyślną konfigurację
        with patch("src.app_config.logger") as mock_logger:
            new_config = AppConfig(
                config_dir=self.test_config_dir, config_file=self.test_config_file
            )

            # Sprawdź czy użyto domyślnej konfiguracji
            self.assertEqual(new_config.get_thumbnail_slider_position(), 50)

            # Sprawdź czy zalogowano błąd
            mock_logger.error.assert_called()

    def test_save_error_handling(self):
        """Test obsługi błędów przy zapisie konfiguracji."""
        # Zasymuluj błąd przy tworzeniu katalogu
        with patch("src.app_config.os.makedirs") as mock_makedirs:
            mock_makedirs.side_effect = OSError("Test błędu zapisu")

            # Próba zapisu powinna zwrócić False
            result = self.app_config.set_thumbnail_slider_position(30)
            self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
