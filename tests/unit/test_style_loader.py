"""
Testy jednostkowe dla modułu style_loader.py
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from src.utils.style_loader import get_style_path, load_styles


class TestStyleLoader(unittest.TestCase):
    """Testy dla funkcji ładowania stylów"""

    def setUp(self):
        """Przygotowanie środowiska testowego"""
        # Tworzenie tymczasowego pliku ze stylami
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = self.temp_dir.name

        # Tworzenie pliku styles.qss w katalogu głównym
        self.root_style_path = os.path.join(self.project_root, "styles.qss")
        with open(self.root_style_path, "w", encoding="utf-8") as f:
            f.write("QLabel { color: red; }")

        # Tworzenie katalogu resources
        self.resources_dir = os.path.join(self.project_root, "src", "resources")
        os.makedirs(self.resources_dir, exist_ok=True)

        # Tworzenie pliku styles.qss w katalogu resources
        self.resources_style_path = os.path.join(self.resources_dir, "styles.qss")
        with open(self.resources_style_path, "w", encoding="utf-8") as f:
            f.write("QLabel { color: blue; }")

    def tearDown(self):
        """Czyszczenie po testach"""
        self.temp_dir.cleanup()

    def test_get_style_path_default(self):
        """Test domyślnej ścieżki do pliku stylów"""
        path = get_style_path(self.project_root)
        self.assertEqual(path, self.root_style_path)

    def test_get_style_path_custom(self):
        """Test niestandardowej ścieżki do pliku stylów"""
        custom_path = "custom_styles.qss"
        path = get_style_path(self.project_root, custom_path)
        self.assertEqual(path, os.path.join(self.project_root, custom_path))

    def test_get_style_path_custom_absolute(self):
        """Test niestandardowej absolutnej ścieżki do pliku stylów"""
        custom_path = os.path.join(self.project_root, "absolute_path.qss")
        path = get_style_path(self.project_root, custom_path)
        self.assertEqual(path, custom_path)

    def test_get_style_path_fallback(self):
        """Test ścieżki fallback gdy plik w katalogu głównym nie istnieje"""
        # Usuwamy plik z katalogu głównego
        os.remove(self.root_style_path)

        path = get_style_path(self.project_root)
        self.assertEqual(path, self.resources_style_path)

    def test_load_styles_success(self):
        """Test poprawnego ładowania stylów"""
        styles = load_styles(self.root_style_path)
        self.assertEqual(styles, "QLabel { color: red; }")

    @patch("logging.warning")
    def test_load_styles_file_not_found(self, mock_log):
        """Test ładowania nieistniejącego pliku stylów"""
        nonexistent_path = os.path.join(self.project_root, "nonexistent.qss")
        styles = load_styles(nonexistent_path)

        self.assertEqual(styles, "")
        mock_log.assert_called_once()

    @patch("logging.error")
    def test_load_styles_exception(self, mock_log):
        """Test obsługi wyjątku podczas ładowania stylów"""
        with patch("builtins.open", side_effect=Exception("Test error")):
            styles = load_styles(self.root_style_path)

            self.assertEqual(styles, "")
            mock_log.assert_called_once()


if __name__ == "__main__":
    unittest.main()
