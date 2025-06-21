"""
Data Manager - zarządzanie danymi aplikacji.
Przeniesione z MainWindow w ramach refaktoryzacji.
"""

import logging
import os
from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem

from src.models.file_pair import FilePair


class DataManager:
    """
    Zarządza danymi aplikacji - pary plików, niesparowane pliki, cache.
    Przeniesione z MainWindow w ramach refaktoryzacji.
    """

    def __init__(self, main_window):
        """
        Inicjalizuje DataManager.

        Args:
            main_window: Referencja do głównego okna
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def clear_all_data_and_views(self):
        """Czyści wszystkie dane plików i odpowiednie widoki."""
        self.main_window.controller.clear_all_data_and_views()

    def clear_unpaired_files_lists(self):
        """Czyści listy niesparowanych plików w interfejsie użytkownika."""
        self.main_window.unpaired_archives_list_widget.clear()
        self.main_window.unpaired_previews_list_widget.clear()

        # Wyczyść kontener miniaturek
        while self.main_window.unpaired_previews_layout.count():
            widget_to_remove = self.main_window.unpaired_previews_layout.itemAt(
                0
            ).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)
                self.main_window.unpaired_previews_layout.removeWidget(widget_to_remove)

        sorted_archives = sorted(
            self.main_window.controller.unpaired_archives,
            key=lambda x: os.path.basename(x).lower(),
        )
        sorted_previews = sorted(
            self.main_window.controller.unpaired_previews,
            key=lambda x: os.path.basename(x).lower(),
        )

        # Aktualizuj listę archiwów (posortowane)
        for archive_path in sorted_archives:
            item = QListWidgetItem(os.path.basename(archive_path))
            item.setData(Qt.ItemDataRole.UserRole, archive_path)
            self.main_window.unpaired_archives_list_widget.addItem(item)

        # Aktualizuj miniaturki podglądów (posortowane)
        for preview_path in sorted_previews:
            # Dodaj do ukrytego QListWidget dla kompatybilności
            item = QListWidgetItem(os.path.basename(preview_path))
            item.setData(Qt.ItemDataRole.UserRole, preview_path)
            self.main_window.unpaired_previews_list_widget.addItem(item)

            # Dodaj miniaturkę przez manager unpaired files
            if hasattr(self.main_window, "unpaired_files_tab_manager"):
                manager = self.main_window.unpaired_files_tab_manager
                manager._add_preview_thumbnail(preview_path)

        logging.debug(
            f"Zaktualizowano listy niesparowanych: "
            f"{len(self.main_window.controller.unpaired_archives)} archiwów, "
            f"{len(self.main_window.controller.unpaired_previews)} podglądów."
        )

        # Deleguj update przycisku parowania do managera unpaired files
        if hasattr(self.main_window, "unpaired_files_tab_manager"):
            # BEZPOŚREDNIA AKTUALIZACJA jako FALLBACK
            logging.debug("FALLBACK: Bezpośrednia aktualizacja unpaired")
            self.update_unpaired_files_direct()

    def update_unpaired_files_direct(self):
        """Bezpośrednia aktualizacja niesparowanych plików przez manager."""
        try:
            logging.debug("FALLBACK: Rozpoczynam aktualizację unpaired przez manager")

            # NAPRAWKA: Użyj unpaired_files_tab_manager zamiast bezpośrednich widgetów
            if (
                hasattr(self.main_window, "unpaired_files_tab_manager")
                and self.main_window.unpaired_files_tab_manager
            ):
                self.main_window.unpaired_files_tab_manager.update_unpaired_files_lists()
                return

            # FALLBACK: Sprawdź czy mamy widgety przypisane bezpośrednio do main_window
            if (
                not hasattr(self.main_window, "unpaired_archives_list_widget")
                or not self.main_window.unpaired_archives_list_widget
            ):
                logging.warning("⚠️ FALLBACK: Brak widgetów - pomijam aktualizację")
                return

            # Wyczyść stare dane (stary sposób fallback)
            self.main_window.unpaired_archives_list_widget.clear()
            self.main_window.unpaired_previews_list_widget.clear()

            # NAPRAWKA FALLBACK: Sortuj alfabetycznie przed wyświetleniem
            sorted_archives = sorted(
                self.main_window.controller.unpaired_archives,
                key=lambda x: os.path.basename(x).lower(),
            )
            sorted_previews = sorted(
                self.main_window.controller.unpaired_previews,
                key=lambda x: os.path.basename(x).lower(),
            )

            # Dodaj archiwa (posortowane)
            for archive_path in sorted_archives:
                item = QListWidgetItem(os.path.basename(archive_path))
                item.setData(Qt.ItemDataRole.UserRole, archive_path)
                self.main_window.unpaired_archives_list_widget.addItem(item)

            # Dodaj podglądy (posortowane)
            for preview_path in sorted_previews:
                item = QListWidgetItem(os.path.basename(preview_path))
                item.setData(Qt.ItemDataRole.UserRole, preview_path)
                self.main_window.unpaired_previews_list_widget.addItem(item)

        except Exception as e:
            self.logger.error(f"FALLBACK ERROR: {e}")

    def force_refresh(self):
        """Wymusza ponowne skanowanie poprzez czyszczenie cache i usuwanie metadanych."""
        if self.main_window.controller.current_directory:
            import shutil

            from src.logic.scanner import clear_cache

            # Wyczyść cache skanowania
            clear_cache()

            # Fizycznie usuń folder .app_metadata
            metadata_folder = os.path.join(
                self.main_window.controller.current_directory, ".app_metadata"
            )
            metadata_removed = False
            if os.path.exists(metadata_folder):
                try:
                    shutil.rmtree(metadata_folder)
                    metadata_removed = True
                    logging.info(f"Usunięto folder metadanych: {metadata_folder}")
                except Exception as e:
                    logging.error(
                        f"Błąd podczas usuwania folderu metadanych {metadata_folder}: {e}"
                    )
            else:
                logging.debug("Folder .app_metadata nie istnieje - nie ma czego usuwać")

            # Wyczyść cache miniaturek
            if hasattr(self.main_window, "gallery_manager") and hasattr(
                self.main_window.gallery_manager, "thumbnail_cache"
            ):
                self.main_window.gallery_manager.thumbnail_cache.clear()
                logging.info("Wyczyszczono cache miniaturek")

            logging.info("Cache i metadane wyczyszczone - wymuszono ponowne skanowanie")

            # NAPRAWKA DEADLOCK: Zamiast change_directory() użyj bezpieczniejszego podejścia
            # change_directory() może powodować deadlock jeśli jest wywoływane z workera
            try:
                # Skanuj tylko bezpośrednie pliki w folderze (max_depth=0)
                scan_result = self.main_window.controller.scan_service.scan_directory(
                    self.main_window.controller.current_directory, max_depth=0
                )

                if scan_result.error_message:
                    logging.error(f"Błąd force_refresh: {scan_result.error_message}")
                    return

                # Zaktualizuj dane kontrolera
                self.main_window.controller.current_file_pairs = scan_result.file_pairs
                self.main_window.controller.unpaired_archives = (
                    scan_result.unpaired_archives
                )
                self.main_window.controller.unpaired_previews = (
                    scan_result.unpaired_previews
                )
                self.main_window.controller.special_folders = (
                    scan_result.special_folders
                )

                # Odśwież widoki BEZ uruchamiania nowych workerów
                self.main_window._apply_filters_and_update_view()

                # Aktualizuj niesparowane pliki
                if hasattr(self.main_window, "unpaired_files_tab_manager"):
                    self.main_window.unpaired_files_tab_manager.update_unpaired_files_lists()

                # Pokaż komunikat o tym co zostało wyczyszczone
                from PyQt6.QtWidgets import QMessageBox

                status_parts = ["Cache skanowania", "Cache miniaturek"]
                if metadata_removed:
                    status_parts.append("Metadane (.app_metadata)")

                status_message = f"Wyczyszczono: {', '.join(status_parts)}"
                QMessageBox.information(
                    self.main_window, "Cache wyczyszczony", status_message
                )

                logging.info("Force refresh zakończony pomyślnie bez deadlock")

            except Exception as e:
                logging.error(f"Błąd podczas force_refresh: {e}")
                # NAPRAWKA DEADLOCK: Nie używaj refresh_all_views() jako fallback
                # może powodować nieskończoną pętlę lub deadlock
                logging.warning("Pomijam odświeżanie z powodu błędu w force_refresh")

    def update_unpaired_lists(self, archives: List[str], previews: List[str]):
        """Aktualizuje listy niesparowanych plików."""
        self.main_window.controller.unpaired_archives = archives
        self.main_window.controller.unpaired_previews = previews
        if hasattr(self.main_window, "unpaired_files_tab_manager"):
            self.main_window.unpaired_files_tab_manager.update_unpaired_files_lists()

    def add_new_pair(self, new_pair: FilePair):
        """Dodaje nową parę do UI."""
        self.main_window.controller.current_file_pairs.append(new_pair)
        tile = self.main_window.tile_manager.create_tile_widget_for_pair(new_pair)
        if tile:
            self.main_window.gallery_manager.add_tile_widget(tile)

    def apply_filters_and_update_view(self):
        """Zbiera kryteria, filtruje pary i aktualizuje galerię."""
        if hasattr(self.main_window, "gallery_tab_manager"):
            self.main_window.gallery_tab_manager.apply_filters_and_update_view()
        elif hasattr(self.main_window, "gallery_manager") and hasattr(
            self.main_window, "controller"
        ):
            # Fallback: wywołaj bezpośrednio gallery_manager z argumentami z kontrolera
            all_file_pairs = getattr(
                self.main_window.controller, "current_file_pairs", []
            )
            filter_criteria = {}  # Domyślne kryteria filtrowania (wszystkie pliki)
            self.main_window.gallery_manager.apply_filters_and_update_view(
                all_file_pairs, filter_criteria
            )

    def update_gallery_view(self):
        """Aktualizuje widok galerii."""
        self.main_window.gallery_tab_manager.update_gallery_view()

    def refresh_all_views(self, new_selection=None):
        """Inteligentne odświeżanie widoków."""
        if not self.main_window.controller.current_directory:
            return

        # Zapobiegnij duplikowaniu operacji skanowania
        if (
            hasattr(self.main_window, "scan_thread")
            and self.main_window.scan_thread
            and self.main_window.scan_thread.isRunning()
        ):
            self.logger.info("Skanowanie już w toku - pomijanie refresh_all_views")
            return

        self.logger.info("Inteligentne odświeżanie widoków po operacji na plikach")

        try:
            # NAPRAWKA PAROWANIA: Przywrócono działanie refresh_all_views()
            # Poprzednio było wyłączone co powodowało że parowanie nie działało

            # Użyj ViewRefreshManager jeśli dostępny
            if hasattr(self.main_window, "view_refresh_manager"):
                manager = self.main_window.view_refresh_manager
                manager.request_refresh_all(force=False)
                self.logger.info("Użyto ViewRefreshManager do odświeżenia")
                return

            # Fallback - bezpośrednie odświeżenie widoków
            self.logger.info("Używam fallback odświeżenia widoków")

            # Odśwież galerię
            if hasattr(self.main_window, "_update_gallery_view"):
                self.main_window._update_gallery_view()
                self.logger.debug("Odświeżono galerię")

            # Odśwież niesparowane pliki
            if hasattr(self.main_window, "_update_unpaired_files_direct"):
                self.main_window._update_unpaired_files_direct()
                self.logger.debug("Odświeżono niesparowane pliki")

            # Odśwież filtry jeśli są aktywne
            if hasattr(self.main_window, "_apply_filters_and_update_view"):
                self.main_window._apply_filters_and_update_view()
                self.logger.debug("Zastosowano filtry")

            self.logger.info("Odświeżanie widoków zakończone pomyślnie")

        except Exception as e:
            self.logger.error(f"KRYTYCZNY BŁĄD w refresh_all_views: {e}")
            # Ostatnia deska ratunku - podstawowe odświeżenie
            try:
                if hasattr(self.main_window, "gallery_tab_manager"):
                    gallery_manager = self.main_window.gallery_tab_manager
                    gallery_manager.update_gallery_view()
                self.logger.info("Użyto ostatecznego fallback odświeżenia")
            except Exception as fallback_error:
                error_msg = f"Również fallback odświeżenie crashuje: {fallback_error}"
                self.logger.error(error_msg)
                # Nie rób nic więcej - lepiej nie crashować aplikacji

    def force_full_refresh(self):
        """Wymusza pełne ponowne skanowanie bieżącego katalogu."""
        current_folder = self.main_window.controller.current_directory
        if current_folder and os.path.isdir(current_folder):
            logging.info(f"Wymuszanie pełnego odświeżenia dla: {current_folder}")
            self.main_window._select_working_directory(current_folder)
        else:
            logging.warning(
                "Nie można wymusić odświeżenia - brak bieżącego katalogu roboczego."
            )
