"""
Testy jednostkowe dla modułu filter_logic.py.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.logic.filter_logic import (
    COLOR_FILTER_ALL,
    COLOR_FILTER_NONE,
    _check_color_match,
    _validate_filter_criteria,
    filter_file_pairs,
)
from src.models.file_pair import FilePair


class TestFilterLogic(unittest.TestCase):
    """Testy dla funkcji filtrowania w module filter_logic.py."""

    def setUp(self):
        """Przygotowanie danych testowych."""
        # Przygotowanie mock obiektów FilePair
        self.pairs = []

        # Pair 1: 5 gwiazdek, czerwony, w katalogu "project/models"
        pair1 = MagicMock(spec=FilePair)
        pair1.get_stars.return_value = 5
        pair1.get_color_tag.return_value = "#FF0000"  # czerwony
        pair1.get_archive_path.return_value = "/data/project/models/model1.zip"
        pair1.get_base_name.return_value = "model1"
        self.pairs.append(pair1)

        # Pair 2: 3 gwiazdki, niebieski, w katalogu "project/textures"
        pair2 = MagicMock(spec=FilePair)
        pair2.get_stars.return_value = 3
        pair2.get_color_tag.return_value = "#0000FF"  # niebieski
        pair2.get_archive_path.return_value = "/data/project/textures/texture1.zip"
        pair2.get_base_name.return_value = "texture1"
        self.pairs.append(pair2)

        # Pair 3: 1 gwiazdka, brak koloru, w katalogu "project/materials"
        pair3 = MagicMock(spec=FilePair)
        pair3.get_stars.return_value = 1
        pair3.get_color_tag.return_value = None
        pair3.get_archive_path.return_value = "/data/project/materials/material1.zip"
        pair3.get_base_name.return_value = "material1"
        self.pairs.append(pair3)

        # Pair 4: 0 gwiazdek, zielony, w katalogu "backup/models"
        pair4 = MagicMock(spec=FilePair)
        pair4.get_stars.return_value = 0
        pair4.get_color_tag.return_value = "#00FF00"  # zielony
        pair4.get_archive_path.return_value = "/data/backup/models/model2.zip"
        pair4.get_base_name.return_value = "model2"
        self.pairs.append(pair4)

        # Pair 5: 4 gwiazdki, pusty string jako kolor, w katalogu "project/misc"
        pair5 = MagicMock(spec=FilePair)
        pair5.get_stars.return_value = 4
        pair5.get_color_tag.return_value = ""  # pusty string
        pair5.get_archive_path.return_value = "/data/project/misc/misc1.zip"
        pair5.get_base_name.return_value = "misc1"
        self.pairs.append(pair5)

    def test_validate_filter_criteria(self):
        """Test walidacji kryteriów filtrowania."""
        # Test poprawnych kryteriów
        criteria = {
            "min_stars": 3,
            "required_color_tag": "#FF0000",
            "path_prefix": "/data/project",
        }
        validated = _validate_filter_criteria(criteria)
        self.assertEqual(validated["min_stars"], 3)
        self.assertEqual(validated["required_color_tag"], "#FF0000")
        self.assertEqual(validated["path_prefix"], "/data/project")

        # Test niepoprawnych kryteriów
        criteria = {
            "min_stars": "invalid",
            "required_color_tag": None,
            "path_prefix": 123,
        }
        validated = _validate_filter_criteria(criteria)
        self.assertEqual(validated["min_stars"], 0)
        self.assertEqual(validated["required_color_tag"], COLOR_FILTER_ALL)
        self.assertEqual(validated["path_prefix"], "123")

        # Test ujemnej wartości min_stars
        criteria = {"min_stars": -5}
        validated = _validate_filter_criteria(criteria)
        self.assertEqual(validated["min_stars"], 0)

    def test_check_color_match(self):
        """Test sprawdzania zgodności tagów kolorów."""
        # Test COLOR_FILTER_ALL
        self.assertTrue(_check_color_match("#FF0000", COLOR_FILTER_ALL))
        self.assertTrue(_check_color_match(None, COLOR_FILTER_ALL))
        self.assertTrue(_check_color_match("", COLOR_FILTER_ALL))

        # Test COLOR_FILTER_NONE
        self.assertFalse(_check_color_match("#FF0000", COLOR_FILTER_NONE))
        self.assertTrue(_check_color_match(None, COLOR_FILTER_NONE))
        self.assertTrue(_check_color_match("", COLOR_FILTER_NONE))

        # Test konkretnego koloru
        self.assertTrue(_check_color_match("#FF0000", "#ff0000"))
        self.assertTrue(_check_color_match(" #FF0000 ", "#ff0000"))
        self.assertFalse(_check_color_match("#00FF00", "#ff0000"))
        self.assertFalse(_check_color_match(None, "#ff0000"))

    @patch("src.logic.filter_logic.normalize_path")
    def test_filter_by_min_stars(self, mock_normalize_path):
        """Test filtrowania po minimalnej liczbie gwiazdek."""
        # Konfiguracja mocka dla normalize_path
        mock_normalize_path.side_effect = lambda x: x

        # Test bez filtrowania gwiazdek (min_stars = 0)
        filtered = filter_file_pairs(self.pairs, {"min_stars": 0})
        self.assertEqual(len(filtered), 5)

        # Test z filtrowaniem >= 3 gwiazdki
        filtered = filter_file_pairs(self.pairs, {"min_stars": 3})
        self.assertEqual(len(filtered), 3)
        for pair in filtered:
            self.assertTrue(pair.get_stars() >= 3)

        # Test z filtrowaniem > 5 gwiazdek (powinno zwrócić pustą listę)
        filtered = filter_file_pairs(self.pairs, {"min_stars": 6})
        self.assertEqual(len(filtered), 0)

    @patch("src.logic.filter_logic.normalize_path")
    def test_filter_by_color_tag(self, mock_normalize_path):
        """Test filtrowania po tagu koloru."""
        # Konfiguracja mocka dla normalize_path
        mock_normalize_path.side_effect = lambda x: x

        # Test dla COLOR_FILTER_ALL
        filtered = filter_file_pairs(
            self.pairs, {"required_color_tag": COLOR_FILTER_ALL}
        )
        self.assertEqual(len(filtered), 5)

        # Test dla COLOR_FILTER_NONE
        filtered = filter_file_pairs(
            self.pairs, {"required_color_tag": COLOR_FILTER_NONE}
        )
        self.assertEqual(len(filtered), 2)  # para 3 (None) i para 5 (pusty string)

        # Test dla konkretnego koloru (czerwony)
        filtered = filter_file_pairs(self.pairs, {"required_color_tag": "#FF0000"})
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].get_color_tag(), "#FF0000")

        # Test dla koloru, który nie istnieje
        filtered = filter_file_pairs(self.pairs, {"required_color_tag": "#FFFF00"})
        self.assertEqual(len(filtered), 0)

    @patch("src.logic.filter_logic.normalize_path")
    def test_filter_by_path_prefix(self, mock_normalize_path):
        """Test filtrowania po prefiksie ścieżki."""
        # Konfiguracja mocka dla normalize_path
        mock_normalize_path.side_effect = lambda x: x

        # Test dla katalogu "project"
        filtered = filter_file_pairs(self.pairs, {"path_prefix": "/data/project"})
        self.assertEqual(len(filtered), 4)

        # Test dla podkatalogu "project/models"
        filtered = filter_file_pairs(
            self.pairs, {"path_prefix": "/data/project/models"}
        )
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].get_base_name(), "model1")

        # Test dla katalogu, który nie zawiera żadnych plików
        filtered = filter_file_pairs(self.pairs, {"path_prefix": "/nonexistent"})
        self.assertEqual(len(filtered), 0)

    @patch("src.logic.filter_logic.normalize_path")
    def test_combined_filters(self, mock_normalize_path):
        """Test kombinacji różnych filtrów."""
        # Konfiguracja mocka dla normalize_path
        mock_normalize_path.side_effect = lambda x: x

        # Test min_stars + color_tag
        filtered = filter_file_pairs(
            self.pairs, {"min_stars": 3, "required_color_tag": "#FF0000"}
        )
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].get_base_name(), "model1")

        # Test min_stars + path_prefix
        filtered = filter_file_pairs(
            self.pairs, {"min_stars": 3, "path_prefix": "/data/project"}
        )
        self.assertEqual(len(filtered), 3)

        # Test color_tag + path_prefix
        filtered = filter_file_pairs(
            self.pairs,
            {"required_color_tag": COLOR_FILTER_NONE, "path_prefix": "/data/project"},
        )
        self.assertEqual(len(filtered), 2)

        # Test wszystkie trzy filtry
        filtered = filter_file_pairs(
            self.pairs,
            {
                "min_stars": 4,
                "required_color_tag": COLOR_FILTER_NONE,
                "path_prefix": "/data/project",
            },
        )
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].get_base_name(), "misc1")

    def test_empty_input(self):
        """Test dla pustej listy wejściowej."""
        filtered = filter_file_pairs([], {"min_stars": 3})
        self.assertEqual(filtered, [])

    def test_empty_criteria(self):
        """Test dla pustych kryteriów filtrowania."""
        filtered = filter_file_pairs(self.pairs, {})
        self.assertEqual(len(filtered), 5)
        self.assertEqual(filtered, self.pairs)


if __name__ == "__main__":
    unittest.main()
