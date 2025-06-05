"""
Testy integracyjne dla modułu path_utils.
Sprawdzają interakcję funkcji path_utils z innymi modułami aplikacji.
"""

import os
import sys
import unittest
from pathlib import Path

# Import testowanych modułów
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.app_config import AppConfig
from src.utils.path_utils import (
    get_path_type,
    is_path_valid,
    normalize_path,
    safe_join_paths,
    to_absolute_path,
    to_relative_path,
)


class TestPathUtilsIntegration(unittest.TestCase):
    """Testy integracyjne dla modułu path_utils."""

    def setUp(self):
        """Przygotowanie środowiska do testów."""
        # Inicjalizacja konfiguracji aplikacji
        self.config = AppConfig()

        # Ustawiamy tymczasowe ścieżki konfiguracyjne dla testów
        self.config.config_dir = os.path.join(os.path.dirname(__file__), "test_config")
        self.config.config_path = os.path.join(self.config.config_dir, "config.json")
        self.config.thumbnails_dir = os.path.join(self.config.config_dir, "thumbnails")

        # Tworzenie przykładowych ścieżek z różnymi formatami do testów
        self.test_paths = [
            "config/settings.json",
            "data\\files\\example.txt",
            "/absolute/path/file.txt",
            "C:\\Windows\\System32\\drivers" if sys.platform == "win32" else "/etc",
            "relative/./path/../file.txt",
        ]

        # Tworzenie tymczasowego katalogu testowego
        self.test_dir = os.path.join(os.path.dirname(__file__), "temp_test_dir")
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        """Czyszczenie po testach."""
        # Usuwanie tymczasowego katalogu
        if os.path.exists(self.test_dir):
            if not os.listdir(self.test_dir):  # Sprawdzamy, czy jest pusty
                os.rmdir(self.test_dir)

    def test_normalize_path_with_config_paths(self):
        """
        Test integracji normalize_path z ścieżkami z konfiguracji.
        Sprawdza spójność normalizacji ścieżek używanych w konfiguracji.
        """
        # Pobieramy ścieżki z konfiguracji
        config_dir = self.config.config_dir
        thumbs_dir = self.config.thumbnails_dir

        # Normalizujemy ścieżki
        normalized_config_dir = normalize_path(config_dir)
        normalized_thumbs_dir = normalize_path(thumbs_dir)

        # Weryfikujemy, że normalizacja zachowuje względne położenie
        # (thumbs_dir jest podkatalogiem config_dir)
        self.assertTrue(
            normalized_thumbs_dir.startswith(normalized_config_dir)
            or os.path.abspath(thumbs_dir).startswith(os.path.abspath(config_dir))
        )

    def test_path_joining_with_config(self):
        """
        Test integracji safe_join_paths z ścieżkami konfiguracyjnymi.
        """
        # Łączenie ścieżek
        base_dir = self.config.config_dir
        joined_path = safe_join_paths(base_dir, "settings.json")

        # Sprawdzenie poprawności ścieżki
        self.assertTrue(joined_path.endswith("settings.json"))
        normalized_base = normalize_path(base_dir)
        self.assertTrue(
            normalized_base in joined_path,
            f"Base dir '{normalized_base}' not found in joined path '{joined_path}'",
        )
        # Weryfikacja normalizacji
        self.assertEqual(
            joined_path, normalize_path(os.path.join(base_dir, "settings.json"))
        )

    def test_relative_paths_in_config_context(self):
        """
        Test konwersji ścieżek względnych z kontekstem konfiguracji.
        """
        # Bazowa ścieżka konfiguracji
        config_dir = self.config.config_dir

        # Tworzenie ścieżki absolutnej
        test_path = os.path.join(config_dir, "subfolder", "file.txt")

        # Konwersja na ścieżkę względną
        rel_path = to_relative_path(test_path, config_dir)

        # Sprawdzenie poprawności konwersji
        self.assertEqual(normalize_path(rel_path), "subfolder/file.txt")

        # Konwersja z powrotem do ścieżki absolutnej
        abs_path = to_absolute_path(rel_path, config_dir)

        # Sprawdzenie spójności konwersji
        self.assertEqual(normalize_path(abs_path), normalize_path(test_path))

    def test_path_validation_with_app_specific_paths(self):
        """
        Test walidacji ścieżek specyficznych dla aplikacji.
        """
        # Standardowe ścieżki aplikacji z konfiguracji
        config_path = self.config.config_path
        thumbs_dir = self.config.thumbnails_dir

        # Walidacja ścieżek
        self.assertTrue(is_path_valid(config_path))
        self.assertTrue(is_path_valid(thumbs_dir))

        # Sprawdzenie typu ścieżek
        self.assertEqual(get_path_type(config_path), "file")
        self.assertEqual(get_path_type(thumbs_dir), "file")

        # Walidacja nieprawidłowych ścieżek w kontekście aplikacji
        invalid_path = os.path.join(config_path, "invalid*file.txt")
        if sys.platform == "win32":
            self.assertFalse(is_path_valid(invalid_path))


if __name__ == "__main__":
    unittest.main()
