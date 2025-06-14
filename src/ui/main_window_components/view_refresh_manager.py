"""
🚀 OPTYMALIZACJA: ViewRefreshManager - inteligentne odświeżanie widoków
Odświeża tylko to co się zmieniło, eliminuje niepotrzebne przeładowania.
"""

import logging
import time
from typing import Any, Dict, Optional, Set

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)


class ViewRefreshManager(QObject):
    """
    Manager odpowiedzialny za inteligentne odświeżanie widoków.
    Odświeża tylko te widoki które rzeczywiście wymagają aktualizacji.
    """

    # Sygnały
    refresh_started = pyqtSignal(str)  # Nazwa widoku
    refresh_finished = pyqtSignal(str, bool)  # Nazwa widoku, sukces

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._last_refresh_state: Dict[str, Dict[str, Any]] = {}
        self._pending_refreshes: Set[str] = set()
        self._refresh_timer = QTimer()
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._perform_scheduled_refreshes)
        self._refresh_delay = (
            50  # NAPRAWKA PERFORMANCE: Zmniejszone opóźnienie dla szybszego UI
        )

        # Definicje widoków do odświeżania
        self._view_definitions = {
            "gallery": {
                "refresh_method": "_refresh_gallery_view",
                "state_keys": ["folder", "filter", "thumbnail_size", "file_count"],
            },
            "unpaired_files": {
                "refresh_method": "_refresh_unpaired_files_view",
                "state_keys": ["folder", "unpaired_archives", "unpaired_previews"],
            },
            "directory_tree": {
                "refresh_method": "_refresh_directory_tree_view",
                "state_keys": ["working_directory", "expanded_folders"],
            },
            "metadata": {
                "refresh_method": "_refresh_metadata_view",
                "state_keys": ["folder", "metadata_modified_time"],
            },
        }

    def request_refresh(self, view_name: str, force: bool = False, delay: bool = True):
        """
        Żąda odświeżenia konkretnego widoku.

        Args:
            view_name: Nazwa widoku do odświeżenia
            force: Czy wymusić odświeżenie bez sprawdzania zmian
            delay: Czy użyć opóźnienia (batching)
        """
        if view_name not in self._view_definitions:
            logger.warning(f"Nieznany widok do odświeżenia: {view_name}")
            return

        current_state = self._get_view_state(view_name)

        # Sprawdź czy odświeżenie jest potrzebne
        if not force and not self._is_refresh_needed(view_name, current_state):
            logger.debug(f"Pomijam odświeżanie {view_name} - brak zmian")
            return

        if delay:
            self._schedule_refresh(view_name)
        else:
            self._refresh_view_immediately(view_name)

    def request_refresh_all(self, force: bool = False):
        """Żąda odświeżenia wszystkich widoków."""
        for view_name in self._view_definitions.keys():
            self.request_refresh(view_name, force=force, delay=True)

    def _is_refresh_needed(self, view_name: str, current_state: Dict[str, Any]) -> bool:
        """Sprawdza czy odświeżenie jest potrzebne porównując stany."""
        last_state = self._last_refresh_state.get(view_name)

        if last_state is None:
            return True  # Pierwszy raz - odśwież

        # Porównaj tylko kluczowe pola
        view_def = self._view_definitions[view_name]
        for key in view_def["state_keys"]:
            if current_state.get(key) != last_state.get(key):
                logger.debug(
                    f"Zmiana w {view_name}.{key}: {last_state.get(key)} -> {current_state.get(key)}"
                )
                return True

        return False

    def _get_view_state(self, view_name: str) -> Dict[str, Any]:
        """Pobiera aktualny stan widoku do porównania."""
        try:
            if view_name == "gallery":
                return self._get_gallery_state()
            elif view_name == "unpaired_files":
                return self._get_unpaired_files_state()
            elif view_name == "directory_tree":
                return self._get_directory_tree_state()
            elif view_name == "metadata":
                return self._get_metadata_state()
            else:
                return {}
        except Exception as e:
            logger.error(f"Błąd pobierania stanu {view_name}: {e}")
            return {}

    def _get_gallery_state(self) -> Dict[str, Any]:
        """Pobiera stan galerii."""
        current_folder = getattr(self.main_window.controller, "current_directory", None)
        current_filter = None
        thumbnail_size = getattr(self.main_window, "current_thumbnail_size", 200)
        file_count = 0

        # Sprawdź filter panel
        if hasattr(self.main_window, "filter_panel"):
            try:
                current_filter = self.main_window.filter_panel.get_filter_criteria()
            except Exception:
                pass

        # Sprawdź liczbę plików
        if hasattr(self.main_window, "controller") and hasattr(
            self.main_window.controller, "current_file_pairs"
        ):
            file_count = len(self.main_window.controller.current_file_pairs or [])

        return {
            "folder": current_folder,
            "filter": current_filter,
            "thumbnail_size": thumbnail_size,
            "file_count": file_count,
        }

    def _get_unpaired_files_state(self) -> Dict[str, Any]:
        """Pobiera stan niesparowanych plików."""
        current_folder = getattr(self.main_window.controller, "current_directory", None)
        unpaired_archives = []
        unpaired_previews = []

        if hasattr(self.main_window.controller, "unpaired_archives"):
            unpaired_archives = list(
                self.main_window.controller.unpaired_archives or []
            )
        if hasattr(self.main_window.controller, "unpaired_previews"):
            unpaired_previews = list(
                self.main_window.controller.unpaired_previews or []
            )

        return {
            "folder": current_folder,
            "unpaired_archives": len(unpaired_archives),
            "unpaired_previews": len(unpaired_previews),
        }

    def _get_directory_tree_state(self) -> Dict[str, Any]:
        """Pobiera stan drzewa katalogów."""
        working_dir = getattr(self.main_window.controller, "working_directory", None)
        expanded_folders = []

        # Można dodać sprawdzanie rozszerzonych folderów jeśli potrzebne

        return {
            "working_directory": working_dir,
            "expanded_folders": len(expanded_folders),
        }

    def _get_metadata_state(self) -> Dict[str, Any]:
        """Pobiera stan metadanych."""
        current_folder = getattr(self.main_window.controller, "current_directory", None)
        modified_time = 0

        # Można dodać sprawdzanie czasu modyfikacji metadanych

        return {"folder": current_folder, "metadata_modified_time": modified_time}

    def _schedule_refresh(self, view_name: str):
        """Planuje odświeżenie z opóźnieniem (batching)."""
        self._pending_refreshes.add(view_name)

        # Restart timer dla batching
        if self._refresh_timer.isActive():
            self._refresh_timer.stop()
        self._refresh_timer.start(self._refresh_delay)

    def _perform_scheduled_refreshes(self):
        """Wykonuje wszystkie zaplanowane odświeżenia."""
        if not self._pending_refreshes:
            return

        logger.debug(
            f"Wykonuję odświeżenie widoków: {', '.join(self._pending_refreshes)}"
        )

        for view_name in self._pending_refreshes.copy():
            self._refresh_view_immediately(view_name)

        self._pending_refreshes.clear()

    def _refresh_view_immediately(self, view_name: str):
        """Wykonuje natychmiastowe odświeżenie widoku."""
        self.refresh_started.emit(view_name)
        start_time = time.time()

        try:
            view_def = self._view_definitions[view_name]
            refresh_method_name = view_def["refresh_method"]

            if hasattr(self, refresh_method_name):
                refresh_method = getattr(self, refresh_method_name)
                success = refresh_method()
            else:
                logger.warning(
                    f"Brak metody {refresh_method_name} dla widoku {view_name}"
                )
                success = False

            # Zapisz stan po odświeżeniu
            if success:
                self._last_refresh_state[view_name] = self._get_view_state(view_name)

            elapsed = time.time() - start_time
            logger.debug(
                f"Odświeżenie {view_name} zakończone w {elapsed:.3f}s (sukces: {success})"
            )

            self.refresh_finished.emit(view_name, success)

        except Exception as e:
            logger.error(f"Błąd odświeżania {view_name}: {e}")
            self.refresh_finished.emit(view_name, False)

    def _refresh_gallery_view(self) -> bool:
        """Odświeża widok galerii."""
        try:
            # NAPRAWKA: Użyj istniejącej metody zamiast nieistniejącej refresh_gallery()
            if hasattr(self.main_window, "_update_gallery_view"):
                self.main_window._update_gallery_view()
                return True
        except Exception as e:
            logger.error(f"Błąd odświeżania galerii: {e}")
        return False

    def _refresh_unpaired_files_view(self) -> bool:
        """Odświeża widok niesparowanych plików."""
        try:
            # NAPRAWKA: Użyj istniejącej metody zamiast nieistniejącej refresh_lists()
            if hasattr(self.main_window, "_update_unpaired_files_direct"):
                self.main_window._update_unpaired_files_direct()
                return True
        except Exception as e:
            logger.error(f"Błąd odświeżania niesparowanych plików: {e}")
        return False

    def _refresh_directory_tree_view(self) -> bool:
        """Odświeża widok drzewa katalogów."""
        try:
            # NAPRAWKA: Nie odświeżamy drzewa bo nie ma bezpiecznej metody
            # Drzewo jest odświeżane automatycznie podczas skanowania
            logger.debug("Pomijam odświeżanie drzewa katalogów - nie jest potrzebne")
            return True
        except Exception as e:
            logger.error(f"Błąd odświeżania drzewa katalogów: {e}")
        return False

    def _refresh_metadata_view(self) -> bool:
        """Odświeża widok metadanych."""
        try:
            # Metadane są zwykle odświeżane automatycznie
            return True
        except Exception as e:
            logger.error(f"Błąd odświeżania metadanych: {e}")
        return False

    def invalidate_view_cache(self, view_name: str = None):
        """Invaliduje cache stanu widoku."""
        if view_name:
            self._last_refresh_state.pop(view_name, None)
            logger.debug(f"Invalidowano cache dla {view_name}")
        else:
            self._last_refresh_state.clear()
            logger.debug("Invalidowano cache wszystkich widoków")

    def get_refresh_stats(self) -> Dict[str, Any]:
        """Zwraca statystyki odświeżania (do debugowania)."""
        return {
            "cached_states": len(self._last_refresh_state),
            "pending_refreshes": len(self._pending_refreshes),
            "available_views": list(self._view_definitions.keys()),
            "timer_active": self._refresh_timer.isActive(),
        }
