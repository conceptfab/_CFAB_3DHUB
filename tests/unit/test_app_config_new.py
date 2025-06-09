"""
Dodatkowe testy jednostkowe dla modułu app_config.py
"""

import json
import os
import tempfile
import unittest
from collections import OrderedDict
from unittest.mock import MagicMock, mock_open, patch

from src.app_config import AppConfig


class TestAppConfigNewFeatures(unittest.TestCase):
    """Testy dla klasy AppConfig - nowe funkcjonalności"""

    def setUp(self):
        """Przygotowanie środowiska testowego"""
        # Tworzenie tymczasowego katalogu na pliki konfiguracyjne
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = self.temp_dir.name
        self.config_file = "test_config.json"
        self.config_path = os.path.join(self.config_dir, self.config_file)

    def tearDown(self):
        """Czyszczenie po testach"""
        self.temp_dir.cleanup()

    def test_config_loaded_from_defaults_flag(self):
        """Test flagi _config_loaded_from_defaults"""
        # Kiedy plik nie istnieje, flaga powinna być False
        with patch("os.path.exists", return_value=False):
            config = AppConfig(self.config_dir, self.config_file)
            self.assertFalse(config._config_loaded_from_defaults)

        # Kiedy jest błąd JSON, flaga powinna być True
        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data="Invalid JSON")
        ):
            config = AppConfig(self.config_dir, self.config_file)
            self.assertTrue(config._config_loaded_from_defaults)

    def test_backup_creation_on_save(self):
        """Test tworzenia kopii zapasowej przy zapisie, gdy wcześniej był błąd"""
        # Przygotowanie testu - najpierw wczytanie z błędnym JSON
        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data="Invalid JSON")
        ):
            config = AppConfig(self.config_dir, self.config_file)
            self.assertTrue(config._config_loaded_from_defaults)

        # Teraz test zapisu i tworzenia backupu
        with patch("os.path.exists", return_value=True), patch("os.makedirs"), patch(
            "shutil.copy2"
        ) as mock_copy, patch("builtins.open", mock_open()):
            config._save_config()
            # Sprawdź czy wywołano copy2 do utworzenia kopii
            mock_copy.assert_called_once()

    def test_makedirs_error_handling(self):
        """Test obsługi błędów przy tworzeniu katalogu konfiguracyjnego"""
        with patch("os.path.exists", return_value=False), patch(
            "os.makedirs", side_effect=PermissionError("Test error")
        ), patch("builtins.open", mock_open()):
            config = AppConfig(self.config_dir, self.config_file)
            result = config._save_config()
            self.assertFalse(
                result
            )  # Powinno zwrócić False przy błędzie tworzenia katalogu

    def test_optimized_set_thumbnail_size_range(self):
        """Test zoptymalizowanej metody set_thumbnail_size_range"""
        with patch("os.path.exists", return_value=False), patch(
            "src.app_config.AppConfig._save_config"
        ) as mock_save:

            config = AppConfig(self.config_dir, self.config_file)

            # Skonfigurowanie mock_save aby symulować pomyślny zapis
            mock_save.return_value = True

            # Wywołanie testowanej metody
            result = config.set_thumbnail_size_range(150, 500)

            # Sprawdź, czy save_config zostało wywołane tylko raz
            self.assertEqual(mock_save.call_count, 1)

            # Sprawdź, czy wartości są prawidłowo ustawione w konfiguracji
            self.assertEqual(config.get("min_thumbnail_size"), 150)
            self.assertEqual(config.get("max_thumbnail_size"), 500)

            # Sprawdź, czy metoda zwróciła True (sukces)
            self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
