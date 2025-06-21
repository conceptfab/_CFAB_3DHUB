#!/usr/bin/env python3
"""
BASELINE TESTS - FileTileWidget ETAP 0
"""

import sys
import unittest
from pathlib import Path

# Add src to path - must be before app imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from PyQt6.QtWidgets import QApplication

    from src.models.file_pair import FilePair
    from src.ui.widgets.file_tile_widget import FileTileWidget
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


class TestFileTileBaseline(unittest.TestCase):
    """Baseline testy dla FileTileWidget"""

    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication([])

    def test_api_exists(self):
        """Test czy wszystkie wymagane API istnieją"""
        # Utwórz test FilePair z absolutnymi ścieżkami
        file_pair = FilePair(
            archive_path=str(project_root / "test.blend"),
            preview_path=str(project_root / "test.jpg"),
            working_directory=str(project_root),
        )

        # Create tile
        tile = FileTileWidget(file_pair)

        # Test metod
        required_methods = ["update_data", "set_thumbnail_size", "set_file_pair"]
        for method in required_methods:
            self.assertTrue(hasattr(tile, method), f"Missing method: {method}")

        # Test sygnałów
        required_signals = ["archive_open_requested", "preview_image_requested"]
        for signal in required_signals:
            self.assertTrue(hasattr(tile, signal), f"Missing signal: {signal}")

        print("✅ API baseline test passed")


if __name__ == "__main__":
    unittest.main()
