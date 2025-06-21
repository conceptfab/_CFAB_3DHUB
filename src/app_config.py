# src/app_config.py
"""
🚀 ETAP 2: Zrefaktoryzowany AppConfig - backward compatibility wrapper
Oryginalny plik został podzielony na komponenty w src/config/

Struktura komponentów:
- config_core.py - główna klasa AppConfig
- config_defaults.py - domyślne wartości
- config_validator.py - walidacja
- config_io.py - operacje I/O
- config_properties.py - właściwości i gettery/settery
"""

from typing import Any, Dict, List

# Import głównej klasy z nowego pakietu
from src.config import AppConfig

# --- Legacy global functions (backward compatibility) ---


def set_thumbnail_slider_position(position: int) -> bool:
    """Legacy function for backward compatibility."""
    config = AppConfig.get_instance()
    return config.set_thumbnail_slider_position(position)


def get_supported_extensions(extension_type: str) -> List[str]:
    """Legacy function for backward compatibility."""
    config = AppConfig.get_instance()
    return config.get_supported_extensions(extension_type)


def get_predefined_colors() -> Dict[str, str]:
    """Legacy function for backward compatibility."""
    config = AppConfig.get_instance()
    return config.get_predefined_colors()


def set_predefined_colors(colors: Dict[str, str]) -> bool:
    """Legacy function for backward compatibility."""
    config = AppConfig.get_instance()
    return config.set_predefined_colors(colors)


# --- Thumbnail format legacy functions ---


def get_thumbnail_format() -> str:
    """Legacy function for backward compatibility."""
    config = AppConfig.get_instance()
    return config.get_thumbnail_format()


def set_thumbnail_format(format_name: str) -> bool:
    """Legacy function for backward compatibility."""
    config = AppConfig.get_instance()
    return config.set_thumbnail_format(format_name)


def get_thumbnail_quality() -> int:
    """Legacy function for backward compatibility."""
    config = AppConfig.get_instance()
    return config.get_thumbnail_quality()


def set_thumbnail_quality(quality: int) -> bool:
    """Legacy function for backward compatibility."""
    config = AppConfig.get_instance()
    return config.set_thumbnail_quality(quality)


# --- Legacy constants for backward compatibility ---
config = AppConfig.get_instance()

SUPPORTED_ARCHIVE_EXTENSIONS = config.supported_archive_extensions
SUPPORTED_PREVIEW_EXTENSIONS = config.supported_preview_extensions
PREDEFINED_COLORS_FILTER = config.predefined_colors_filter
MIN_THUMBNAIL_SIZE = config.min_thumbnail_size
MAX_THUMBNAIL_SIZE = config.max_thumbnail_size
DEFAULT_THUMBNAIL_SIZE = config.default_thumbnail_size

# Parametry cache dla skanera
SCANNER_MAX_CACHE_ENTRIES = config.scanner_max_cache_entries
SCANNER_MAX_CACHE_AGE_SECONDS = config.scanner_max_cache_age_seconds

# Parametry timerów
resize_timer_delay_ms = config.get("resize_timer_delay_ms", 150)
