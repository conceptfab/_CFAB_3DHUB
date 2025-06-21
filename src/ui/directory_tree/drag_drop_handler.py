"""
Handler obsługi drag & drop dla drzewa katalogów.
Wydzielony z głównego managera w ramach refaktoryzacji.
"""

import logging
import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import QModelIndex
from PyQt6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent

if TYPE_CHECKING:
    from .manager import DirectoryTreeManager

logger = logging.getLogger(__name__)


class DirectoryTreeDragDropHandler:
    """
    Handler obsługi drag & drop dla drzewa katalogów.
    Wydzielony z głównego managera dla lepszej separacji odpowiedzialności.
    """

    def __init__(self, manager: "DirectoryTreeManager"):
        self.manager = manager
        self.folder_tree = manager.folder_tree
        self._highlighted_drop_target = None

    def setup_drag_and_drop_handlers(self):
        """Konfiguruje obsługę drag and drop dla drzewa folderów."""
        # Zastąp standardowe handlery własnymi
        self.folder_tree.dragEnterEvent = self._drag_enter_event
        self.folder_tree.dragMoveEvent = self._drag_move_event
        self.folder_tree.dragLeaveEvent = self._drag_leave_event
        self.folder_tree.dropEvent = self._drop_event
        logger.debug("Drag and drop handlers skonfigurowane")

    def _drag_enter_event(self, event: QDragEnterEvent):
        """Obsługuje rozpoczęcie przeciągania nad drzewem folderów."""
        try:
            logger.debug(f"DRAG ENTER: hasUrls={event.mimeData().hasUrls()}")
            if event.mimeData().hasUrls():
                urls = event.mimeData().urls()
                logger.debug(
                    f"DRAG ENTER: {len(urls)} plików: {[url.toLocalFile() for url in urls[:3]]}"
                )
                event.acceptProposedAction()
                logger.debug("DRAG ENTER: Akceptowano przeciąganie plików")
            else:
                logger.debug("DRAG ENTER: Brak URLs - ignoruję")
                event.ignore()
        except Exception as e:
            logger.error(f"Błąd drag enter: {e}")
            event.ignore()

    def _drag_move_event(self, event: QDragMoveEvent):
        """Obsługuje ruch podczas przeciągania nad drzewem folderów."""
        try:
            if event.mimeData().hasUrls():
                # Znajdź folder pod kursorem
                index = self.folder_tree.indexAt(event.position().toPoint())
                logger.debug(f"DRAG MOVE: index valid={index.isValid()}")
                if index.isValid():
                    # Podświetl folder jako cel
                    source_index = self.manager.get_source_index_from_proxy(index)
                    if source_index.isValid():
                        folder_path = self.manager.model.filePath(source_index)
                        logger.debug(f"DRAG MOVE: folder_path={folder_path}")
                        if os.path.isdir(folder_path):
                            current_target = getattr(
                                self, "_highlighted_drop_target", None
                            )
                            if current_target != folder_path:
                                self._highlighted_drop_target = folder_path
                                # NAPRAWKA: Synchronizuj z managerem żeby delegate mógł to przeczytać
                                self.manager._highlighted_drop_target = folder_path
                                logger.debug(
                                    f"DRAG MOVE: Podświetlam folder: {folder_path}"
                                )
                                # Wymuś ponowne rysowanie tylko jeśli folder się zmienił
                                self.folder_tree.viewport().update()
                            event.acceptProposedAction()
                            return

            event.ignore()
        except Exception as e:
            logger.error(f"Błąd drag move: {e}")
            event.ignore()

    def _drag_leave_event(self, event: QDragLeaveEvent):
        """Obsługuje opuszczenie obszaru podczas przeciągania."""
        try:
            # Usuń podświetlenie
            if hasattr(self, "_highlighted_drop_target"):
                delattr(self, "_highlighted_drop_target")
                # NAPRAWKA: Usuń też z managera
                if hasattr(self.manager, "_highlighted_drop_target"):
                    delattr(self.manager, "_highlighted_drop_target")
                self.folder_tree.viewport().update()
            event.accept()
        except Exception as e:
            logger.error(f"Błąd drag leave: {e}")

    def _drop_event(self, event: QDropEvent):
        """Obsługuje upuszczenie plików na folder."""
        try:
            if event.mimeData().hasUrls():
                # Znajdź docelowy folder
                index = self.folder_tree.indexAt(event.position().toPoint())
                if index.isValid():
                    source_index = self.manager.get_source_index_from_proxy(index)
                    if source_index.isValid():
                        target_folder = self.manager.model.filePath(source_index)
                        if os.path.isdir(target_folder):
                            # Pobierz ścieżki upuszczonych plików
                            dropped_files = []
                            for url in event.mimeData().urls():
                                file_path = url.toLocalFile()
                                if os.path.exists(file_path):
                                    dropped_files.append(file_path)

                            if dropped_files:
                                # Sygnalizuj głównemu oknu operację move/copy
                                if hasattr(
                                    self.manager.parent_window, "handle_file_drop_on_folder"
                                ):
                                    self.manager.parent_window.handle_file_drop_on_folder(
                                        dropped_files, target_folder
                                    )
                                    logger.debug(
                                        f"DRAG&DROP: Wywołano handle_file_drop_on_folder z {len(dropped_files)} plikami"
                                    )
                                else:
                                    logger.error(
                                        "DRAG&DROP ERROR: Brak metody handle_file_drop_on_folder w parent_window"
                                    )
                                event.acceptProposedAction()

            # Usuń podświetlenie
            if hasattr(self, "_highlighted_drop_target"):
                delattr(self, "_highlighted_drop_target")
                # NAPRAWKA: Usuń też z managera
                if hasattr(self.manager, "_highlighted_drop_target"):
                    delattr(self.manager, "_highlighted_drop_target")
                self.folder_tree.viewport().update()

        except Exception as e:
            logger.error(f"Błąd drop event: {e}")
            event.ignore()

    def get_highlighted_drop_target(self) -> str:
        """Zwraca aktualnie podświetlony cel upuszczania."""
        return getattr(self, "_highlighted_drop_target", None)