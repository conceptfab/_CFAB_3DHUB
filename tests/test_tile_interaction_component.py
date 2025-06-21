"""
Testy dla TileInteractionComponent - STAGE 5 refaktoryzacji FileTileWidget.
"""

from unittest.mock import Mock, patch

import pytest
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QWidget

from src.models.file_pair import FilePair
from src.ui.widgets.tile_interaction_component import (
    DragState,
    TileInteractionComponent,
)


class TestTileInteractionComponent:
    """Testy dla TileInteractionComponent."""

    @pytest.fixture
    def config(self):
        """Mock konfiguracji."""
        config = Mock(spec=TileConfig)
        config.drag_threshold_px = 10
        return config

    @pytest.fixture
    def event_bus(self):
        """Mock event bus."""
        return Mock(spec=TileEventBus)

    @pytest.fixture
    def parent_widget(self, qtbot):
        """Mock parent widget."""
        widget = QWidget()
        qtbot.addWidget(widget)
        return widget

    @pytest.fixture
    def file_pair(self):
        """Mock file pair."""
        fp = Mock(spec=FilePair)
        fp.archive_path = "/test/archive.zip"
        fp.preview_path = "/test/preview.jpg"
        fp.get_base_name.return_value = "test_file"
        return fp

    @pytest.fixture
    def component(self, config, event_bus, parent_widget, file_pair):
        """TileInteractionComponent fixture."""
        return TileInteractionComponent(config, event_bus, parent_widget, file_pair)

    def test_initialization(
        self, component, config, event_bus, parent_widget, file_pair
    ):
        """Test inicjalizacji komponentu."""
        assert component.config == config
        assert component.event_bus == event_bus
        assert component.parent_widget == parent_widget
        assert component._file_pair == file_pair
        assert component._interaction_enabled is True
        assert component._drag_enabled is True
        assert component._context_menu_enabled is True

    def test_set_target_widgets(self, component, qtbot):
        """Test ustawiania target widgets."""
        thumb_widget = QWidget()
        filename_widget = QWidget()
        qtbot.addWidget(thumb_widget)
        qtbot.addWidget(filename_widget)

        component.set_target_widgets(thumb_widget, filename_widget)

        assert component._thumbnail_widget == thumb_widget
        assert component._filename_widget == filename_widget

    def test_set_file_pair(self, component):
        """Test ustawiania file pair."""
        new_fp = Mock(spec=FilePair)
        new_fp.get_base_name.return_value = "new_file"

        component.set_file_pair(new_fp)

        assert component._file_pair == new_fp
        assert component._drag_context.state == DragState.IDLE

    def test_set_interaction_enabled(self, component):
        """Test włączania/wyłączania interakcji."""
        component.set_interaction_enabled(False)
        assert component._interaction_enabled is False

        component.set_interaction_enabled(True)
        assert component._interaction_enabled is True

    def test_set_drag_enabled(self, component):
        """Test włączania/wyłączania drag & drop."""
        component.set_drag_enabled(False)
        assert component._drag_enabled is False

        component.set_drag_enabled(True)
        assert component._drag_enabled is True

    @patch("PyQt6.QtWidgets.QApplication.instance")
    def test_setup_drag_threshold(
        self, mock_app_instance, config, event_bus, parent_widget
    ):
        """Test ustawiania progu drag & drop."""
        mock_app = Mock()
        mock_app.startDragDistance.return_value = 15
        mock_app_instance.return_value = mock_app

        component = TileInteractionComponent(config, event_bus, parent_widget)

        assert component._drag_context.threshold == 15

    def test_handle_mouse_press_left_button(self, component):
        """Test obsługi naciśnięcia lewego przycisku myszy."""
        event = Mock(spec=QMouseEvent)
        event.button.return_value = Qt.MouseButton.LeftButton
        event.pos.return_value = QPoint(10, 20)

        result = component.handle_mouse_press(event)

        assert result is True
        assert component._drag_context.state == DragState.PRESS_DETECTED
        assert component._drag_context.press_position == QPoint(10, 20)
        assert component._drag_context.drag_distance == 0

    def test_handle_mouse_press_right_button(self, component):
        """Test obsługi naciśnięcia prawego przycisku myszy."""
        event = Mock(spec=QMouseEvent)
        event.button.return_value = Qt.MouseButton.RightButton
        event.pos.return_value = QPoint(10, 20)

        with patch.object(component, "_handle_context_menu_request") as mock_context:
            result = component.handle_mouse_press(event)

            assert result is True
            mock_context.assert_called_once_with(event)

    def test_handle_mouse_press_disabled(self, component):
        """Test obsługi myszy gdy interakcje są wyłączone."""
        component.set_interaction_enabled(False)

        event = Mock(spec=QMouseEvent)
        event.button.return_value = Qt.MouseButton.LeftButton

        result = component.handle_mouse_press(event)

        assert result is False

    def test_handle_mouse_move_drag_threshold(self, component):
        """Test obsługi ruchu myszy - przekroczenie progu."""
        # Setup press state
        component._drag_context.state = DragState.PRESS_DETECTED
        component._drag_context.press_position = QPoint(0, 0)
        component._drag_context.threshold = 5

        event = Mock(spec=QMouseEvent)
        event.buttons.return_value = Qt.MouseButton.LeftButton
        event.pos.return_value = QPoint(10, 0)  # Distance = 10 > threshold = 5

        with patch.object(
            component, "_start_drag_operation", return_value=True
        ) as mock_drag:
            component.handle_mouse_move(event)
            mock_drag.assert_called_once_with(event)
            assert component._drag_context.drag_distance == 10

    def test_handle_mouse_release_click(self, component, qtbot):
        """Test obsługi zwolnienia myszy - kliknięcie."""
        # Setup press state
        component._drag_context.state = DragState.PRESS_DETECTED
        component._drag_context.press_position = QPoint(10, 10)
        component._drag_context.threshold = 5

        event = Mock(spec=QMouseEvent)
        event.button.return_value = Qt.MouseButton.LeftButton
        event.pos.return_value = QPoint(11, 11)  # Distance = ~1.4 < threshold = 5

        with patch.object(
            component, "_handle_click_action", return_value=True
        ) as mock_click:
            result = component.handle_mouse_release(event)

            assert result is True
            mock_click.assert_called_once_with(QPoint(11, 11))
            assert component._drag_context.state == DragState.IDLE

    def test_identify_click_target_thumbnail(self, component, qtbot):
        """Test identyfikacji celu kliknięcia - miniatura."""
        thumb_widget = QWidget()
        qtbot.addWidget(thumb_widget)
        component.set_target_widgets(thumbnail_widget=thumb_widget)

        with patch.object(
            component.parent_widget, "childAt", return_value=thumb_widget
        ):
            target = component._identify_click_target(QPoint(10, 10))

            assert target == ClickTarget.THUMBNAIL

    def test_identify_click_target_filename(self, component, qtbot):
        """Test identyfikacji celu kliknięcia - nazwa pliku."""
        filename_widget = QWidget()
        qtbot.addWidget(filename_widget)
        component.set_target_widgets(filename_widget=filename_widget)

        with patch.object(
            component.parent_widget, "childAt", return_value=filename_widget
        ):
            target = component._identify_click_target(QPoint(10, 10))

            assert target == ClickTarget.FILENAME

    def test_handle_click_action_thumbnail(self, component, qtbot):
        """Test obsługi kliknięcia na miniaturę."""
        thumb_widget = QWidget()
        qtbot.addWidget(thumb_widget)
        component.set_target_widgets(thumbnail_widget=thumb_widget)

        with patch.object(
            component.parent_widget, "childAt", return_value=thumb_widget
        ):
            with patch.object(component, "thumbnail_clicked") as mock_signal:
                result = component._handle_click_action(QPoint(10, 10))

                assert result is True
                mock_signal.emit.assert_called_once_with(component._file_pair)

    def test_handle_click_action_filename(self, component, qtbot):
        """Test obsługi kliknięcia na nazwę pliku."""
        filename_widget = QWidget()
        qtbot.addWidget(filename_widget)
        component.set_target_widgets(filename_widget=filename_widget)

        with patch.object(
            component.parent_widget, "childAt", return_value=filename_widget
        ):
            with patch.object(component, "filename_clicked") as mock_signal:
                result = component._handle_click_action(QPoint(10, 10))

                assert result is True
                mock_signal.emit.assert_called_once_with(component._file_pair)

    def test_handle_key_press_ctrl_o(self, component):
        """Test obsługi Ctrl+O."""
        event = Mock(spec=QKeyEvent)
        event.key.return_value = Qt.Key.Key_O
        event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier

        with patch.object(component, "filename_clicked") as mock_signal:
            result = component.handle_key_press(event)

            assert result is True
            mock_signal.emit.assert_called_once_with(component._file_pair)

    def test_handle_key_press_ctrl_p(self, component):
        """Test obsługi Ctrl+P."""
        event = Mock(spec=QKeyEvent)
        event.key.return_value = Qt.Key.Key_P
        event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier

        with patch.object(component, "thumbnail_clicked") as mock_signal:
            result = component.handle_key_press(event)

            assert result is True
            mock_signal.emit.assert_called_once_with(component._file_pair)

    def test_get_drag_state(self, component):
        """Test pobierania stanu drag & drop."""
        assert component.get_drag_state() == DragState.IDLE

        component._drag_context.state = DragState.DRAG_ACTIVE
        assert component.get_drag_state() == DragState.DRAG_ACTIVE

    def test_is_dragging(self, component):
        """Test sprawdzania czy trwa drag."""
        assert component.is_dragging() is False

        component._drag_context.state = DragState.DRAG_ACTIVE
        assert component.is_dragging() is True

    def test_cleanup(self, component):
        """Test czyszczenia zasobów."""
        component._drag_context.state = DragState.DRAG_ACTIVE

        component.cleanup()

        assert component._drag_context.state == DragState.IDLE
