"""
SelectionManager - zarządzanie selekcją kafelków.
Przeniesione z main_window.py w ramach refaktoryzacji.
"""

import logging

from src.models.file_pair import FilePair


class SelectionManager:
    """Zarządzanie selekcją kafelków w galerii."""

    def __init__(self, main_window):
        """
        Inicjalizuje SelectionManager.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def handle_tile_selection_changed(self, file_pair: FilePair, is_selected: bool):
        """Obsługuje zmianę selekcji kafelka."""
        # Delegacja do EventHandler
        self.main_window.event_handler.handle_tile_selection_changed(
            file_pair, is_selected
        )

    def update_bulk_operations_visibility(self):
        """
        Updates visibility of bulk operations controls based on selection count.
        """
        has_selection = len(self.main_window.controller.selection_manager.selected_tiles) > 0
        if hasattr(self.main_window, "bulk_operations_panel"):
            self.main_window.bulk_operations_panel.setVisible(has_selection)
            if hasattr(self.main_window, "selected_count_label"):
                count = len(self.main_window.controller.selection_manager.selected_tiles)
                self.main_window.selected_count_label.setText(f"Zaznaczone: {count}")

    def clear_all_selections(self):
        """Clears all tile selections."""
        self.main_window.controller.selection_manager.selected_tiles.clear()

        # Update all visible tiles to reflect cleared selection
        if (
            hasattr(self.main_window, "gallery_manager")
            and self.main_window.gallery_manager
        ):
            for tile_widget in self.main_window.gallery_manager.get_all_tile_widgets():
                if hasattr(tile_widget, "metadata_controls"):
                    tile_widget.metadata_controls.update_selection_display(False)

        self.update_bulk_operations_visibility()
        logging.debug("Cleared all tile selections")

    def select_all_tiles(self):
        """Selects all currently visible tiles."""
        if (
            hasattr(self.main_window, "gallery_manager")
            and self.main_window.gallery_manager
        ):
            for tile_widget in self.main_window.gallery_manager.get_all_tile_widgets():
                if hasattr(tile_widget, "file_pair") and tile_widget.file_pair:
                    self.main_window.controller.selection_manager.selected_tiles.add(
                        tile_widget.file_pair
                    )
                    if hasattr(tile_widget, "metadata_controls"):
                        tile_widget.metadata_controls.update_selection_display(True)

            self.update_bulk_operations_visibility()
            selected_count = len(self.main_window.controller.selection_manager.selected_tiles)
            logging.debug(f"Selected all {selected_count} visible tiles")

    def update_bulk_operations_visibility_with_count(self, selected_count: int):
        """
        Updates bulk operations visibility with specific count.

        Args:
            selected_count: Number of selected items
        """
        has_selection = selected_count > 0
        if hasattr(self.main_window, "bulk_operations_panel"):
            self.main_window.bulk_operations_panel.setVisible(has_selection)
            if hasattr(self.main_window, "selected_count_label"):
                self.main_window.selected_count_label.setText(
                    f"Zaznaczone: {selected_count}"
                )
