"""
Testy jednostkowe dla metadata_manager.py
Sprawdzają funkcjonalność thread-safe metadata management z cache.
"""

import json
import os
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from src.logic.metadata_manager import (
    MetadataManager,
    _validate_metadata_structure,
    get_absolute_path,
    get_lock_path,
    get_metadata_path,
    get_relative_path,
    load_metadata,
    save_metadata,
)


class TestMetadataManager(unittest.TestCase):
    """Test cases for MetadataManager thread-safe functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.working_directory = os.path.join(self.temp_dir, "test_working_dir")
        os.makedirs(self.working_directory, exist_ok=True)

        # Clear singleton instances for clean tests
        MetadataManager._instances.clear()

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        MetadataManager._instances.clear()

    def test_singleton_pattern(self):
        """Test that MetadataManager uses singleton pattern per directory."""
        manager1 = MetadataManager.get_instance(self.working_directory)
        manager2 = MetadataManager.get_instance(self.working_directory)

        self.assertIs(manager1, manager2)

        # Different directory should get different instance
        other_dir = os.path.join(self.temp_dir, "other_dir")
        os.makedirs(other_dir, exist_ok=True)
        manager3 = MetadataManager.get_instance(other_dir)

        self.assertIsNot(manager1, manager3)

    def test_thread_safety_buffer(self):
        """Test thread-safe access to changes buffer."""
        manager = MetadataManager.get_instance(self.working_directory)

        # Mock file pair
        mock_file_pair = Mock()
        mock_file_pair.archive_path = os.path.join(self.working_directory, "test.zip")
        mock_file_pair.get_stars.return_value = 3
        mock_file_pair.get_color_tag.return_value = "red"

        # Test concurrent access
        results = []

        def save_metadata_thread():
            try:
                result = manager.save_metadata([mock_file_pair], [], [])
                results.append(result)
            except Exception as e:
                results.append(e)

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=save_metadata_thread)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All operations should succeed
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertTrue(result)

    def test_cache_functionality(self):
        """Test metadata caching with TTL."""
        manager = MetadataManager.get_instance(self.working_directory)

        # First load should hit the file
        metadata1 = manager.load_metadata()
        self.assertIsNotNone(metadata1)

        # Second load within cache timeout should use cache
        with patch("src.logic.metadata_manager._load_metadata_direct") as mock_load:
            metadata2 = manager.load_metadata()
            mock_load.assert_not_called()

        self.assertEqual(metadata1, metadata2)

        # After cache invalidation, should hit file again
        manager._invalidate_cache()
        with patch("src.logic.metadata_manager._load_metadata_direct") as mock_load:
            mock_load.return_value = {
                "file_pairs": {},
                "unpaired_archives": [],
                "unpaired_previews": [],
            }
            metadata3 = manager.load_metadata()
            mock_load.assert_called_once()

    def test_atomic_write(self):
        """Test atomic write functionality."""
        manager = MetadataManager.get_instance(self.working_directory)

        test_metadata = {
            "file_pairs": {"test.zip": {"stars": 3, "color_tag": "red"}},
            "unpaired_archives": [],
            "unpaired_previews": [],
            "timestamp": time.time(),
        }

        # Test atomic write
        result = manager._atomic_write(test_metadata)
        self.assertTrue(result)

        # Verify file was written correctly
        metadata_path = manager.get_metadata_path()
        self.assertTrue(os.path.exists(metadata_path))

        with open(metadata_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        self.assertEqual(saved_data["file_pairs"], test_metadata["file_pairs"])

    def test_force_save(self):
        """Test force save functionality."""
        manager = MetadataManager.get_instance(self.working_directory)

        # Mock file pair
        mock_file_pair = Mock()
        mock_file_pair.archive_path = os.path.join(self.working_directory, "test.zip")
        mock_file_pair.get_stars.return_value = 4
        mock_file_pair.get_color_tag.return_value = "blue"

        # Add to buffer but don't trigger automatic save
        with manager._buffer_lock:
            manager._changes_buffer.update(
                {
                    "file_pairs": {"test.zip": {"stars": 4, "color_tag": "blue"}},
                    "unpaired_archives": [],
                    "unpaired_previews": [],
                    "timestamp": time.time(),
                }
            )

        # Force save should flush immediately
        manager.force_save()

        # Verify buffer is empty
        self.assertEqual(len(manager._changes_buffer), 0)


class TestMetadataHelperFunctions(unittest.TestCase):
    """Test cases for metadata helper functions."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_metadata_path(self):
        """Test metadata path generation."""
        working_dir = os.path.join(self.temp_dir, "work")
        metadata_path = get_metadata_path(working_dir)

        expected_path = os.path.join(working_dir, ".app_metadata", "metadata.json")
        self.assertEqual(
            os.path.normpath(metadata_path), os.path.normpath(expected_path)
        )

    def test_get_lock_path(self):
        """Test lock path generation."""
        working_dir = os.path.join(self.temp_dir, "work")
        lock_path = get_lock_path(working_dir)

        expected_path = os.path.join(working_dir, ".app_metadata", "metadata.lock")
        self.assertEqual(os.path.normpath(lock_path), os.path.normpath(expected_path))

    def test_get_relative_path(self):
        """Test relative path calculation."""
        base_path = os.path.join(self.temp_dir, "base")
        abs_path = os.path.join(base_path, "subfolder", "file.txt")

        relative = get_relative_path(abs_path, base_path)
        expected = os.path.join("subfolder", "file.txt")

        self.assertEqual(os.path.normpath(relative), os.path.normpath(expected))

    def test_get_absolute_path(self):
        """Test absolute path calculation."""
        base_path = os.path.join(self.temp_dir, "base")
        relative_path = os.path.join("subfolder", "file.txt")

        absolute = get_absolute_path(relative_path, base_path)
        expected = os.path.join(base_path, "subfolder", "file.txt")

        self.assertEqual(os.path.normpath(absolute), os.path.normpath(expected))

    def test_validate_metadata_structure(self):
        """Test metadata structure validation."""
        # Valid structure
        valid_metadata = {
            "file_pairs": {"test.zip": {"stars": 3, "color_tag": "red"}},
            "unpaired_archives": ["file1.zip"],
            "unpaired_previews": ["preview1.jpg"],
        }
        self.assertTrue(_validate_metadata_structure(valid_metadata))

        # Invalid structure - missing key
        invalid_metadata = {
            "file_pairs": {},
            "unpaired_archives": [],
            # missing unpaired_previews
        }
        self.assertFalse(_validate_metadata_structure(invalid_metadata))

        # Invalid structure - wrong type
        invalid_metadata2 = {
            "file_pairs": [],  # should be dict
            "unpaired_archives": [],
            "unpaired_previews": [],
        }
        self.assertFalse(_validate_metadata_structure(invalid_metadata2))


class TestLegacyFunctions(unittest.TestCase):
    """Test cases for legacy function compatibility."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.working_directory = os.path.join(self.temp_dir, "test_working_dir")
        os.makedirs(self.working_directory, exist_ok=True)
        MetadataManager._instances.clear()

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        MetadataManager._instances.clear()

    def test_legacy_load_metadata(self):
        """Test legacy load_metadata function."""
        # Should work without existing metadata file
        metadata = load_metadata(self.working_directory)
        self.assertIsInstance(metadata, dict)
        self.assertIn("file_pairs", metadata)
        self.assertIn("unpaired_archives", metadata)
        self.assertIn("unpaired_previews", metadata)

    def test_legacy_save_metadata(self):
        """Test legacy save_metadata function."""
        # Mock file pair
        mock_file_pair = Mock()
        mock_file_pair.archive_path = os.path.join(self.working_directory, "test.zip")
        mock_file_pair.get_stars.return_value = 2
        mock_file_pair.get_color_tag.return_value = "green"

        # Test save
        result = save_metadata(self.working_directory, [mock_file_pair], [], [])
        self.assertTrue(result)

        # Verify file was created
        metadata_path = get_metadata_path(self.working_directory)
        # Note: File might not exist immediately due to buffering
        # Force flush by getting manager instance and calling force_save
        manager = MetadataManager.get_instance(self.working_directory)
        manager.force_save()

        # Now check if metadata was saved
        saved_metadata = load_metadata(self.working_directory)
        self.assertIn("test.zip", saved_metadata["file_pairs"])


if __name__ == "__main__":
    unittest.main()
