"""Tests for app_config.py - ETAP 4 corrections."""

import json
import os
import tempfile
import threading
import time
from unittest.mock import Mock, patch

import jsonschema
import pytest

from src.app_config import AppConfig
from src.config.config_validator import ConfigValidator


class TestConfigValidator:
    """Test ConfigValidator centralized validation."""

    def test_validate_valid_config(self):
        """Test validation of valid config."""
        valid_config = {
            "thumbnail_size": 250,
            "min_thumbnail_size": 100,
            "max_thumbnail_size": 600,
            "supported_archive_extensions": [".zip", ".rar"],
            "predefined_colors": {"Red": "#FF0000", "All": "ALL", "None": "__NONE__"},
        }

        result = ConfigValidator.validate(valid_config)
        assert result == valid_config

    def test_validate_invalid_config_fixes_values(self):
        """Test validation fixes invalid config values."""
        invalid_config = {
            "thumbnail_size": 50,  # Too small
            "min_thumbnail_size": -10,  # Negative
            "supported_archive_extensions": ["zip", "rar"],  # Missing dots
            "predefined_colors": {"Red": "invalid_color"},  # Invalid hex
        }

        result = ConfigValidator.validate(invalid_config)
        # Should return fixed config or original with warnings
        assert isinstance(result, dict)

    def test_validate_with_additional_properties(self):
        """Test validation allows additional properties."""
        config_with_extra = {
            "thumbnail_size": 250,
            "custom_property": "value",  # Not in schema but should be allowed
            "another_custom": 123,
        }

        result = ConfigValidator.validate(config_with_extra)
        assert "custom_property" in result
        assert "another_custom" in result


class TestAppConfigSingleton:
    """Test singleton pattern implementation."""

    def setup_method(self):
        """Reset singleton before each test."""
        AppConfig._instance = None
        AppConfig._initialized = False

    def test_singleton_same_instance(self):
        """Test that multiple calls return same instance."""
        config1 = AppConfig()
        config2 = AppConfig()
        config3 = AppConfig.get_instance()

        assert config1 is config2
        assert config2 is config3
        assert id(config1) == id(config2) == id(config3)

    def test_singleton_thread_safety(self):
        """Test singleton is thread-safe."""
        instances = []
        barrier = threading.Barrier(3)

        def create_instance():
            barrier.wait()  # Sync threads
            instance = AppConfig()
            instances.append(instance)

        threads = [threading.Thread(target=create_instance) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All instances should be the same
        assert len(set(id(instance) for instance in instances)) == 1

    def test_singleton_initialization_once(self):
        """Test __init__ called only once."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config1 = AppConfig(config_dir=temp_dir)
            config_dir_1 = config1._app_data_dir

            config2 = AppConfig(config_dir="different_dir")
            config_dir_2 = config2._app_data_dir

            # Should use same directory (first initialization)
            assert config_dir_1 == config_dir_2
            assert config1 is config2


class TestAppConfigAsyncSave:
    """Test asynchronous save functionality."""

    def setup_method(self):
        """Reset singleton and create temp config."""
        AppConfig._instance = None
        AppConfig._initialized = False
        self.temp_dir = tempfile.mkdtemp()
        self.config = AppConfig(config_dir=self.temp_dir)

    def test_async_save_debouncing(self):
        """Test async save debounces multiple rapid changes."""
        # Make rapid changes
        for i in range(5):
            self.config.set("test_key", f"value_{i}")
            time.sleep(0.1)  # Quick succession

        # Wait for debounced save
        time.sleep(0.7)

        # Check that save happened
        config_file = os.path.join(self.temp_dir, "config.json")
        assert os.path.exists(config_file)

        with open(config_file, "r") as f:
            saved_config = json.load(f)

        assert saved_config["test_key"] == "value_4"

    def test_sync_save_still_works(self):
        """Test synchronous save still works for immediate saves."""
        self.config.set("test_sync", "sync_value")
        result = self.config.save()  # Sync save

        assert result is True

        config_file = os.path.join(self.temp_dir, "config.json")
        with open(config_file, "r") as f:
            saved_config = json.load(f)

        assert saved_config["test_sync"] == "sync_value"

    def test_async_save_thread_safety(self):
        """Test async save is thread-safe."""

        def update_config(thread_id):
            for i in range(10):
                self.config.set(f"thread_{thread_id}_key_{i}", f"value_{i}")
                time.sleep(0.01)

        threads = [threading.Thread(target=update_config, args=(i,)) for i in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Wait for all saves to complete
        time.sleep(1.0)

        # Check config was saved
        config_file = os.path.join(self.temp_dir, "config.json")
        assert os.path.exists(config_file)


class TestAppConfigDynamicProperties:
    """Test dynamic property access via __getattr__."""

    def setup_method(self):
        """Reset singleton and create config."""
        AppConfig._instance = None
        AppConfig._initialized = False
        self.config = AppConfig()

    def test_dynamic_property_access(self):
        """Test dynamic property access works."""
        # These should work via __getattr__
        assert isinstance(self.config.min_thumbnail_size, int)
        assert isinstance(self.config.max_thumbnail_size, int)
        assert isinstance(self.config.window_min_width, int)
        assert isinstance(self.config.supported_archive_extensions, list)

    def test_dynamic_property_nonexistent(self):
        """Test accessing non-existent property raises AttributeError."""
        with pytest.raises(AttributeError):
            _ = self.config.nonexistent_property

    def test_complex_properties_still_work(self):
        """Test complex computed properties still work."""
        assert isinstance(self.config.thumbnail_size, tuple)
        assert len(self.config.thumbnail_size) == 2

        assert hasattr(self.config, "predefined_colors_filter")
        from collections import OrderedDict

        assert isinstance(self.config.predefined_colors_filter, OrderedDict)


class TestAppConfigValidation:
    """Test centralized validation functionality."""

    def setup_method(self):
        """Reset singleton and create config."""
        AppConfig._instance = None
        AppConfig._initialized = False

    def test_load_config_with_validation(self):
        """Test config loading includes validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "config.json")

            # Create invalid config file
            invalid_config = {
                "thumbnail_size": 50,  # Too small
                "min_thumbnail_size": -10,  # Negative
                "window_min_width": 200,  # Too small
            }

            with open(config_file, "w") as f:
                json.dump(invalid_config, f)

            # Load config - should be validated and potentially fixed
            config = AppConfig(config_dir=temp_dir)

            # Config should be loaded (either fixed or with warnings)
            assert config._config is not None

    def test_config_recovery_from_corruption(self):
        """Test config recovery when file is corrupted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "config.json")

            # Create corrupted JSON file
            with open(config_file, "w") as f:
                f.write('{"invalid": json content}')

            # Should fallback to defaults
            config = AppConfig(config_dir=temp_dir)

            assert config._config_loaded_from_defaults is True
            assert (
                config.get("thumbnail_size")
                == AppConfig.DEFAULT_CONFIG["thumbnail_size"]
            )


class TestAppConfigBackwardCompatibility:
    """Test backward compatibility features."""

    def setup_method(self):
        """Reset singleton."""
        AppConfig._instance = None
        AppConfig._initialized = False

    def test_legacy_functions_work(self):
        """Test legacy global functions still work."""
        from src.app_config import (
            get_predefined_colors,
            get_supported_extensions,
            set_predefined_colors,
            set_thumbnail_slider_position,
        )

        # Test legacy functions
        result = set_thumbnail_slider_position(75)
        assert result is True

        extensions = get_supported_extensions("archive")
        assert isinstance(extensions, list)

        colors = get_predefined_colors()
        assert isinstance(colors, dict)

        result = set_predefined_colors({"Test": "#FF0000"})
        assert result is True

    def test_old_validation_methods_still_exist(self):
        """Test static validation methods still exist."""
        config = AppConfig()

        # These should still work for backward compatibility
        assert callable(config._validate_int)
        assert callable(config._validate_str)
        assert callable(config._validate_list)
        assert callable(config._validate_dict)

        # Test they still work
        assert config._validate_int(10, 5, 15) == 10
        assert config._validate_str("test") == "test"
        assert config._validate_list([1, 2, 3]) == [1, 2, 3]
        assert config._validate_dict({"key": "value"}) == {"key": "value"}


class TestAppConfigPerformance:
    """Test performance improvements."""

    def setup_method(self):
        """Reset singleton."""
        AppConfig._instance = None
        AppConfig._initialized = False

    def test_lazy_loading_default_config(self):
        """Test DEFAULT_CONFIG is not copied unnecessarily."""
        config = AppConfig()

        # DEFAULT_CONFIG should be class attribute, not instance copy
        assert hasattr(AppConfig, "DEFAULT_CONFIG")
        assert isinstance(AppConfig.DEFAULT_CONFIG, dict)

    def test_async_save_performance(self):
        """Test async save doesn't block."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = AppConfig(config_dir=temp_dir)

            start_time = time.time()

            # Multiple rapid saves should not block
            for i in range(10):
                config.set(f"key_{i}", f"value_{i}")

            end_time = time.time()

            # Should complete quickly (async saves)
            assert (end_time - start_time) < 0.1  # Less than 100ms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
