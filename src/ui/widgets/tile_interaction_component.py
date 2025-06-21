"""
TileInteractionComponent - obsługa interakcji użytkownika w refaktoryzacji FileTileWidget.

STAGE 5: Separacja logiki obsługi user interactions z monolitycznego FileTileWidget.
"""

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Optional

from PyQt6.QtCore import QMimeData, QObject, QPoint, QSize, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QKeyEvent, QMouseEvent, QPixmap
from PyQt6.QtWidgets import QApplication, QWidget

from src.models.file_pair import FilePair
from src.ui.widgets.tile_config import TileConfig, TileEvent
from src.ui.widgets.tile_event_bus import TileEventBus


class InteractionType(Enum):
    """Typy interakcji użytkownika."""

    MOUSE_CLICK = auto()
    MOUSE_DRAG = auto()
    KEYBOARD_PRESS = auto()
    CONTEXT_MENU = auto()


class DragState(Enum):
    """Stany procesu drag & drop."""

    IDLE = auto()
    PRESS_DETECTED = auto()
    DRAG_ACTIVE = auto()


class ClickTarget(Enum):
    """Cele kliknięć w kafelku."""

    THUMBNAIL = auto()
    FILENAME = auto()
    BACKGROUND = auto()
    UNKNOWN = auto()


@dataclass
class DragContext:
    """Kontekst operacji drag & drop."""

    state: DragState = DragState.IDLE
    press_position: Optional[QPoint] = None
    drag_distance: int = 0
    threshold: int = 0


class TileInteractionComponent(QObject):
    """
    Komponent zarządzający interakcjami użytkownika z kafelkiem.

    Odpowiedzialności:
    - Obsługa zdarzeń myszy (click, drag)
    - Obsługa klawiatury
    - Zarządzanie drag & drop operations
    - Context menu handling
    """

    # Qt signals dla komunikacji z UI
    thumbnail_clicked = pyqtSignal(FilePair)
    filename_clicked = pyqtSignal(FilePair)
    drag_started = pyqtSignal(FilePair)
    drag_completed = pyqtSignal(FilePair, int)
    context_menu_requested = pyqtSignal(FilePair, QWidget, object)

    def __init__(
        self,
        config: TileConfig,
        event_bus: TileEventBus,
        parent_widget: QWidget,
        file_pair: Optional[FilePair] = None,
    ):
        """
        Inicjalizuje InteractionComponent.

        Args:
            config: Konfiguracja tile'a
            event_bus: Centralny event bus
            parent_widget: Widget rodzica (FileTileWidget)
            file_pair: Para plików
        """
        super().__init__(parent_widget)

        # Dependency injection
        self.config = config
        self.event_bus = event_bus
        self.parent_widget = parent_widget

        # Logger
        self.logger = logging.getLogger(f"{__name__}.{id(self)}")

        # File pair
        self._file_pair: Optional[FilePair] = file_pair

        # Interaction state
        self._interaction_enabled = True
        self._drag_enabled = True
        self._context_menu_enabled = True

        # Drag & drop state
        self._drag_context = DragContext()

        # Target widgets (będą ustawione przez parent)
        self._thumbnail_widget: Optional[QWidget] = None
        self._filename_widget: Optional[QWidget] = None

        # Setup
        self._setup_drag_threshold()

        self.logger.debug(f"InteractionComponent initialized")

    def _setup_drag_threshold(self):
        """Ustawia próg dla drag & drop."""
        app = QApplication.instance()
        if app:
            self._drag_context.threshold = app.startDragDistance()
        else:
            self._drag_context.threshold = 5

    # ---- Configuration ----

    def set_target_widgets(
        self, thumbnail_widget: QWidget = None, filename_widget: QWidget = None
    ):
        """Ustawia widgets będące celami interakcji."""
        self._thumbnail_widget = thumbnail_widget
        self._filename_widget = filename_widget

    def set_file_pair(self, file_pair: Optional[FilePair]):
        """Ustawia parę plików."""
        self._file_pair = file_pair
        self._drag_context = DragContext()
        self._setup_drag_threshold()

    def set_interaction_enabled(self, enabled: bool):
        """Włącza/wyłącza obsługę interakcji."""
        self._interaction_enabled = enabled

    def set_drag_enabled(self, enabled: bool):
        """Włącza/wyłącza drag & drop."""
        self._drag_enabled = enabled
        if not enabled:
            self._reset_drag_state()

    # ---- Mouse Event Handling ----

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        """Obsługuje naciśnięcie przycisku myszy."""
        if not self._interaction_enabled:
            return False

        # Handle left button press for potential drag
        if event.button() == Qt.MouseButton.LeftButton and self._drag_enabled:
            self._drag_context.state = DragState.PRESS_DETECTED
            self._drag_context.press_position = event.pos()
            self._drag_context.drag_distance = 0

            self.logger.debug(f"Mouse press detected at {event.pos()}")
            return True

        # Handle right button for context menu
        elif (
            event.button() == Qt.MouseButton.RightButton and self._context_menu_enabled
        ):
            self._handle_context_menu_request(event)
            return True

        return False

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        """Obsługuje ruch myszy."""
        if not self._interaction_enabled or not self._drag_enabled:
            return False

        # Check if we're in press state
        if self._drag_context.state != DragState.PRESS_DETECTED:
            return False

        # Check if left button is still pressed
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            self._reset_drag_state()
            return False

        # Calculate distance
        if self._drag_context.press_position:
            distance = (
                event.pos() - self._drag_context.press_position
            ).manhattanLength()
            self._drag_context.drag_distance = distance

            # Check if threshold is reached
            if distance >= self._drag_context.threshold:
                return self._start_drag_operation(event)

        return False

    def handle_mouse_release(self, event: QMouseEvent) -> bool:
        """Obsługuje zwolnienie przycisku myszy."""
        if not self._interaction_enabled:
            return False

        # Handle left button release
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if this was a clean click (no drag started)
            if (
                self._drag_context.state == DragState.PRESS_DETECTED
                and self._drag_context.press_position is not None
            ):

                # Verify click is close to press position
                distance = (
                    event.pos() - self._drag_context.press_position
                ).manhattanLength()
                if distance < self._drag_context.threshold:
                    handled = self._handle_click_action(event.pos())
                    self._reset_drag_state()
                    return handled

            self._reset_drag_state()

        return False

    # ---- Drag & Drop Implementation ----

    def _start_drag_operation(self, event: QMouseEvent) -> bool:
        """Rozpoczyna operację drag & drop."""
        if not self._file_pair or not self._drag_enabled:
            return False

        # Validate file pair
        if not self._file_pair.archive_path or not self._file_pair.preview_path:
            self.logger.warning("Cannot start drag - incomplete file pair")
            return False

        self._drag_context.state = DragState.DRAG_ACTIVE

        # Create drag object
        drag = QDrag(self.parent_widget)

        # Setup mime data
        mime_data = QMimeData()
        urls = [
            QUrl.fromLocalFile(self._file_pair.archive_path),
            QUrl.fromLocalFile(self._file_pair.preview_path),
        ]
        mime_data.setUrls(urls)
        drag.setMimeData(mime_data)

        # Setup drag pixmap
        pixmap = self._create_drag_pixmap()
        if pixmap:
            drag.setPixmap(pixmap)
            drag.setHotSpot(pixmap.rect().center())

        # Emit drag started signal
        self.drag_started.emit(self._file_pair)

        self.logger.debug(
            f"Starting drag operation for: {self._file_pair.get_base_name()}"
        )

        # Execute drag
        drop_action = drag.exec(Qt.DropAction.MoveAction)

        # Handle completion
        drop_action_value = (
            drop_action.value if hasattr(drop_action, "value") else int(drop_action)
        )
        self.drag_completed.emit(self._file_pair, drop_action_value)

        self.logger.debug(f"Drag operation completed with action: {drop_action}")

        # Reset state
        self._reset_drag_state()

        return True

    def _create_drag_pixmap(self) -> Optional[QPixmap]:
        """Tworzy pixmap dla operacji drag & drop."""
        # Try to get pixmap from thumbnail widget
        if self._thumbnail_widget and hasattr(self._thumbnail_widget, "pixmap"):
            pixmap = self._thumbnail_widget.pixmap()
            if pixmap and not pixmap.isNull():
                # Scale to drag size
                scaled_pixmap = pixmap.scaled(
                    QSize(100, 100),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                return scaled_pixmap

        # Fallback - create placeholder
        placeholder = QPixmap(QSize(100, 100))
        placeholder.fill(QColor("#444444"))
        return placeholder

    def _reset_drag_state(self):
        """Resetuje stan drag & drop."""
        self._drag_context = DragContext()
        self._setup_drag_threshold()

    # ---- Click Handling ----

    def _handle_click_action(self, position: QPoint) -> bool:
        """Obsługuje akcję kliknięcia."""
        if not self._file_pair:
            return False

        target = self._identify_click_target(position)

        # Handle different targets
        if target == ClickTarget.THUMBNAIL:
            self.thumbnail_clicked.emit(self._file_pair)
            self.logger.debug(f"Thumbnail clicked: {self._file_pair.get_base_name()}")
            return True

        elif target == ClickTarget.FILENAME:
            self.filename_clicked.emit(self._file_pair)
            self.logger.debug(f"Filename clicked: {self._file_pair.get_base_name()}")
            return True

        return False

    def _identify_click_target(self, position: QPoint) -> ClickTarget:
        """Identyfikuje cel kliknięcia na podstawie pozycji."""
        if not self.parent_widget:
            return ClickTarget.UNKNOWN

        # Get widget at position
        child_widget = self.parent_widget.childAt(position)

        if child_widget == self._thumbnail_widget:
            return ClickTarget.THUMBNAIL
        elif child_widget == self._filename_widget:
            return ClickTarget.FILENAME
        elif child_widget == self.parent_widget:
            return ClickTarget.BACKGROUND
        else:
            return ClickTarget.UNKNOWN

    # ---- Context Menu ----

    def _handle_context_menu_request(self, event: QMouseEvent):
        """Obsługuje żądanie context menu."""
        if not self._file_pair or not self._context_menu_enabled:
            return

        # Emit signal for parent to handle
        self.context_menu_requested.emit(self._file_pair, self.parent_widget, event)

        self.logger.debug(
            f"Context menu requested for: {self._file_pair.get_base_name()}"
        )

    # ---- Keyboard Handling ----

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Obsługuje naciśnięcie klawisza."""
        if not self._interaction_enabled:
            return False

        # Handle common shortcuts
        if self._file_pair:
            key = event.key()
            modifiers = event.modifiers()

            # Ctrl+O - Open file
            if key == Qt.Key.Key_O and modifiers == Qt.KeyboardModifier.ControlModifier:
                self.filename_clicked.emit(self._file_pair)
                return True

            # Ctrl+P - Preview
            elif (
                key == Qt.Key.Key_P and modifiers == Qt.KeyboardModifier.ControlModifier
            ):
                self.thumbnail_clicked.emit(self._file_pair)
                return True

            # Enter/Return - Default action (preview)
            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.thumbnail_clicked.emit(self._file_pair)
                return True

            # Space - Alternative action (open)
            elif key == Qt.Key.Key_Space:
                self.filename_clicked.emit(self._file_pair)
                return True

        return False

    # ---- State Management ----

    def get_drag_state(self) -> DragState:
        """Zwraca aktualny stan drag & drop."""
        return self._drag_context.state

    def is_dragging(self) -> bool:
        """Sprawdza czy trwa operacja drag."""
        return self._drag_context.state == DragState.DRAG_ACTIVE

    # ---- Cleanup ----

    def cleanup(self):
        """Czyści zasoby komponentu."""
        self._reset_drag_state()
        self.logger.debug("InteractionComponent cleaned up")

    def __del__(self):
        """Destruktor - cleanup resources."""
        try:
            self.cleanup()
        except Exception:
            pass
