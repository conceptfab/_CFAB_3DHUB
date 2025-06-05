# tests/unit/test_app_config.py
"""
Testy jednostkowe dla modułu app_config.py.
"""

import json
import os
import shutil

# Import testowanego modułu
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.app_config import AppConfig


class TestAppConfig(unittest.TestCase):
    """Klasa testowa dla modułu app_config."""

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
