"""
Testy jednostkowe dla modułu app_config.py
"""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, mock_open, patch

from src.app_config import AppConfig


class TestAppConfig(unittest.TestCase):
    """Testy dla klasy AppConfig"""

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

    def test_init_with_default_paths(self):
        """Test inicjalizacji z domyślnymi ścieżkami"""
        with patch("os.path.exists", return_value=False):
            config = AppConfig()
            # Sprawdzenie, czy konfig zawiera domyślne wartości
            self.assertEqual(config.get("thumbnail_slider_position"), 50)

    def test_init_with_custom_paths(self):
        """Test inicjalizacji z niestandardowymi ścieżkami"""
        with patch("os.path.exists", return_value=False):
            config = AppConfig(config_dir=self.config_dir, config_file=self.config_file)
            # Sprawdzenie, czy konfig zawiera domyślne wartości
            self.assertEqual(config.get("thumbnail_slider_position"), 50)
            self.assertTrue(config._config_file_path.endswith(self.config_file))

    def test_load_config_file_not_exists(self):
        """Test ładowania konfiguracji, gdy plik nie istnieje"""
        with patch("os.path.exists", return_value=False):
            config = AppConfig(self.config_dir, self.config_file)
            # Powinien używać domyślnych wartości
            self.assertEqual(config.get("thumbnail_slider_position"), 50)

    def test_load_config_file_exists(self):
        """Test ładowania konfiguracji z istniejącego pliku"""
        test_config = {"thumbnail_slider_position": 75}

        # Symulacja istniejącego pliku konfiguracyjnego
        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=json.dumps(test_config))
        ):
            config = AppConfig(self.config_dir, self.config_file)
            # Powinien wczytać wartość z pliku
            self.assertEqual(config.get("thumbnail_slider_position"), 75)

    def test_load_config_missing_keys(self):
        """Test uzupełniania brakujących kluczy"""
        # Konfig z brakującymi kluczami
        test_config = {"thumbnail_slider_position": 75}

        # Symulacja istniejącego pliku konfiguracyjnego
        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=json.dumps(test_config))
        ):
            config = AppConfig(self.config_dir, self.config_file)
            # Powinien uzupełnić brakujące klucze domyślnymi wartościami
            self.assertEqual(config.get("thumbnail_slider_position"), 75)  # Z pliku
            self.assertEqual(config.get("min_thumbnail_size"), 100)  # Domyślna wartość

    def test_load_config_json_error(self):
        """Test obsługi błędów JSON przy ładowaniu konfiguracji"""
        # Nieprawidłowy JSON
        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data="Invalid JSON")
        ):
            config = AppConfig(self.config_dir, self.config_file)
            # Powinien używać domyślnych wartości
            self.assertEqual(config.get("thumbnail_slider_position"), 50)

    def test_load_config_io_error(self):
        """Test obsługi błędów IO przy ładowaniu konfiguracji"""
        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", side_effect=IOError("Test IO Error")
        ):
            config = AppConfig(self.config_dir, self.config_file)
            # Powinien używać domyślnych wartości
            self.assertEqual(config.get("thumbnail_slider_position"), 50)

    def test_save_config_success(self):
        """Test zapisu konfiguracji - sukces"""
        m = mock_open()
        with patch("os.path.exists", return_value=False), patch("os.makedirs"), patch(
            "builtins.open", m
        ):
            config = AppConfig(self.config_dir, self.config_file)
            result = config.set("test_key", "test_value")
            self.assertTrue(result)
            m.assert_called_once()

    def test_save_config_io_error(self):
        """Test zapisu konfiguracji - błąd IO"""
        with patch("os.path.exists", return_value=False), patch("os.makedirs"), patch(
            "builtins.open", side_effect=IOError("Test IO Error")
        ):
            config = AppConfig(self.config_dir, self.config_file)
            result = config.set("test_key", "test_value")
            self.assertFalse(result)

    def test_save_config_permission_error(self):
        """Test zapisu konfiguracji - błąd uprawnień przy tworzeniu katalogu"""
        with patch("os.path.exists", return_value=False), patch(
            "os.makedirs", side_effect=PermissionError("Permission denied")
        ):
            config = AppConfig(self.config_dir, self.config_file)
            result = config.set("test_key", "test_value")
            self.assertFalse(result)

    def test_get_nonexistent_key(self):
        """Test pobierania nieistniejącego klucza"""
        with patch("os.path.exists", return_value=False):
            config = AppConfig(self.config_dir, self.config_file)
            # Powinien zwrócić wartość domyślną
            self.assertIsNone(config.get("nonexistent_key"))
            self.assertEqual(config.get("nonexistent_key", "default"), "default")

    def test_set_thumbnail_slider_position_valid(self):
        """Test ustawiania pozycji suwaka - wartość poprawna"""
        with patch("os.path.exists", return_value=False), patch(
            "src.app_config.AppConfig._save_config", return_value=True
        ):
            config = AppConfig(self.config_dir, self.config_file)
            result = config.set_thumbnail_slider_position(75)
            self.assertTrue(result)
            self.assertEqual(config.get("thumbnail_slider_position"), 75)

    def test_set_thumbnail_slider_position_invalid(self):
        """Test ustawiania pozycji suwaka - wartość niepoprawna"""
        with patch("os.path.exists", return_value=False):
            config = AppConfig(self.config_dir, self.config_file)
            # Wartość spoza zakresu
            with self.assertRaises(ValueError):
                config.set_thumbnail_slider_position(101)
            # Nieprawidłowy typ
            with self.assertRaises(ValueError):
                config.set_thumbnail_slider_position("not a number")

    def test_update_derived_values(self):
        """Test aktualizacji pochodnych wartości"""
        with patch("os.path.exists", return_value=False), patch(
            "src.app_config.AppConfig._save_config", return_value=True
        ):
            config = AppConfig(self.config_dir, self.config_file)

            # Ustawienie wartości i sprawdzenie aktualizacji _thumbnail_size
            config.set("thumbnail_slider_position", 75)
            min_size = config.get("min_thumbnail_size")
            max_size = config.get("max_thumbnail_size")
            expected_size = min_size + int(0.75 * (max_size - min_size))

            self.assertEqual(config.thumbnail_size, (expected_size, expected_size))

    def test_set_thumbnail_size_range_valid(self):
        """Test ustawiania zakresu rozmiarów miniatur - wartości poprawne"""
        with patch("os.path.exists", return_value=False), patch(
            "src.app_config.AppConfig._save_config", return_value=True
        ):
            config = AppConfig(self.config_dir, self.config_file)
            result = config.set_thumbnail_size_range(150, 500)
            self.assertTrue(result)
            self.assertEqual(config.get("min_thumbnail_size"), 150)
            self.assertEqual(config.get("max_thumbnail_size"), 500)

    def test_set_thumbnail_size_range_invalid(self):
        """Test ustawiania zakresu rozmiarów miniatur - wartości niepoprawne"""
        with patch("os.path.exists", return_value=False):
            config = AppConfig(self.config_dir, self.config_file)
            # min > max
            with self.assertRaises(ValueError):
                config.set_thumbnail_size_range(500, 150)
            # min < 10
            with self.assertRaises(ValueError):
                config.set_thumbnail_size_range(5, 500)
            # max > 2000
            with self.assertRaises(ValueError):
                config.set_thumbnail_size_range(150, 2500)

    def test_get_supported_extensions(self):
        """Test pobierania obsługiwanych rozszerzeń"""
        with patch("os.path.exists", return_value=False):
            config = AppConfig(self.config_dir, self.config_file)

            # Testowanie znanych typów
            self.assertIsInstance(config.get_supported_extensions("archive"), list)
            self.assertIsInstance(config.get_supported_extensions("preview"), list)

            # Testowanie nieznanego typu
            self.assertEqual(config.get_supported_extensions("unknown"), [])

    def test_set_supported_extensions(self):
        """Test ustawiania obsługiwanych rozszerzeń"""
        with patch("os.path.exists", return_value=False), patch(
            "src.app_config.AppConfig._save_config", return_value=True
        ):
            config = AppConfig(self.config_dir, self.config_file)

            # Ustawienie dla znanego typu z normalizacją
            result = config.set_supported_extensions("archive", ["zip", ".rar"])
            self.assertTrue(result)
            self.assertEqual(
                config.get_supported_extensions("archive"), [".zip", ".rar"]
            )

            # Ustawienie dla nieznanego typu
            result = config.set_supported_extensions("unknown", [".xyz"])
            self.assertFalse(result)

    def test_properties(self):
        """Test właściwości konfiguracji"""
        with patch("os.path.exists", return_value=False):
            config = AppConfig(self.config_dir, self.config_file)

            # Test wszystkich właściwości
            self.assertIsInstance(config.thumbnail_size, tuple)
            self.assertIsInstance(config.min_thumbnail_size, int)
            self.assertIsInstance(config.max_thumbnail_size, int)
            self.assertIsInstance(config.supported_archive_extensions, list)
            self.assertIsInstance(config.supported_preview_extensions, list)
            self.assertIsInstance(config.predefined_colors_filter, OrderedDict)
            self.assertIsInstance(config.scanner_max_cache_entries, int)
            self.assertIsInstance(config.scanner_max_cache_age_seconds, int)
            self.assertIsInstance(config.thumbnail_cache_max_entries, int)
            self.assertIsInstance(config.thumbnail_cache_max_memory_mb, int)
            self.assertIsInstance(config.thumbnail_cache_enable_disk, bool)
            self.assertIsInstance(config.thumbnail_cache_cleanup_threshold, float)


if __name__ == "__main__":
    from collections import OrderedDict

    unittest.main()
