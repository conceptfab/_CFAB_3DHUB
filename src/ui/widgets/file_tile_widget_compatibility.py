"""
ETAP 5: Backward compatibility adapter dla FileTileWidget.

Wydzielony z file_tile_widget.py dla lepszej organizacji kodu.
Zapewnia 100% kompatybilność z legacy API.
"""

import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .file_tile_widget import FileTileWidget


@dataclass
class CompatibilityAdapter:
    """
    ETAP 9: Adapter pattern dla backward compatibility.

    Mapuje stare metody API na nową architekturę komponentową.
    ETAP 5: Wydzielony z głównego pliku dla lepszej organizacji.
    """

    widget: "FileTileWidget"

    def __post_init__(self):
        self._deprecation_warnings_shown = set()

    def show_deprecation_warning(self, old_method: str, new_method: str = None):
        """Pokazuje deprecation warning tylko raz na metodę."""
        if old_method not in self._deprecation_warnings_shown:
            message = f"FileTileWidget.{old_method}() is deprecated."
            if new_method:
                message += f" Use {new_method}() instead."
            warnings.warn(message, DeprecationWarning, stacklevel=3)
            self._deprecation_warnings_shown.add(old_method)

    # Legacy API method mappings (nie używane - update_data ma własny deprecation warning)

    def change_thumbnail_size_legacy(self, size):
        """Legacy method - maps to set_thumbnail_size()"""
        self.show_deprecation_warning("change_thumbnail_size", "set_thumbnail_size")
        return self.widget.set_thumbnail_size(size)

    def refresh_thumbnail_legacy(self):
        """Legacy method - maps to reload_thumbnail()"""
        self.show_deprecation_warning("refresh_thumbnail", "reload_thumbnail")
        return self.widget.reload_thumbnail()

    def get_file_data_legacy(self):
        """Legacy method - maps to file_pair property"""
        self.show_deprecation_warning("get_file_data", "file_pair property")
        return self.widget.file_pair

    def set_selection_legacy(self, selected: bool):
        """Legacy method - maps to set_selected()"""
        self.show_deprecation_warning("set_selection", "set_selected")
        return self.widget.set_selected(selected)
