"""
TileMetadataComponent - zarządzanie metadanymi kafelka w refaktoryzacji FileTileWidget.

Ten komponent jest częścią STAGE 4 rozbicia monolitycznego FileTileWidget na mniejsze,
odpowiedzialne komponenty. Zarządza stanem metadanych (stars, color tags, selection)
i śledzeniem zmian.

Autor: Refaktoryzacja FileTileWidget - STAGE 4
Data: 2025-06-20
"""

import logging
import threading
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, Optional, Set

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from src.models.file_pair import FilePair
from src.ui.widgets.tile_config import TileConfig
from src.ui.widgets.tile_event_bus import TileEvent, TileEventBus


class MetadataState(Enum):
    """Stan metadanych kafelka."""

    UNINITIALIZED = auto()
    LOADING = auto()
    READY = auto()
    UPDATING = auto()
    ERROR = auto()


class MetadataChangeType(Enum):
    """Typ zmiany metadanych."""

    STARS_CHANGED = auto()
    COLOR_TAG_CHANGED = auto()
    SELECTION_CHANGED = auto()
    FILE_PAIR_UPDATED = auto()


@dataclass
class MetadataSnapshot:
    """Snapshot stanu metadanych w określonym momencie."""

    stars: int = 0
    color_tag: str = ""
    is_selected: bool = False
    file_pair_id: Optional[str] = None
    timestamp: float = 0.0


class TileMetadataComponent(QObject):
    """
    Komponent zarządzający metadanymi kafelka.

    Odpowiedzialności:
    - Zarządzanie stanem metadanych (stars, color tags, selection)
    - Śledzenie zmian i ich propagacja
    - Thread-safe state management
    - Change history i rollback functionality
    - Batch updates dla wydajności

    Używa dependency injection dla konfiguracji i event bus.
    """

    # Qt signals dla komunikacji z UI
    metadata_changed = pyqtSignal(str, object)  # (change_type, new_value)
    state_changed = pyqtSignal(str)  # MetadataState enum name
    batch_update_ready = pyqtSignal(dict)  # Batch of changes

    def __init__(
        self,
        config: TileConfig,
        event_bus: TileEventBus,
        file_pair: Optional[FilePair] = None,
        parent: QObject = None,
    ):
        """
        Inicjalizuje MetadataComponent.

        Args:
            config: Konfiguracja tile'a
            event_bus: Centralny event bus dla komunikacji
            file_pair: Para plików do zarządzania
            parent: Rodzic Qt
        """
        super().__init__(parent)

        # Dependency injection
        self.config = config
        self.event_bus = event_bus

        # Logger
        self.logger = logging.getLogger(f"{__name__}.{id(self)}")

        # State management
        self._state = MetadataState.UNINITIALIZED
        self._file_pair: Optional[FilePair] = None
        self._metadata_snapshot = MetadataSnapshot()

        # Thread safety
        self._lock = threading.RLock()

        # Change tracking
        self._change_history: list[tuple[MetadataChangeType, Any, float]] = []
        self._pending_changes: Dict[MetadataChangeType, Any] = {}
        self._change_listeners: Dict[MetadataChangeType, Set[Callable]] = defaultdict(
            set
        )

        # Batch updates
        self._batch_timer = QTimer()
        self._batch_timer.setSingleShot(True)
        self._batch_timer.timeout.connect(self._process_batch_updates)

        # Memory tracking
        self._memory_usage = 0

        # Setup
        self._setup_event_subscriptions()
        if file_pair:
            self.set_file_pair(file_pair)

        self.logger.debug(
            f"MetadataComponent initialized with config: {config.thumbnail_size}"
        )

    def _setup_event_subscriptions(self):
        """Konfiguruje subskrypcje na zdarzenia w event bus."""
        # Subscribe to relevant tile events
        self.event_bus.subscribe(TileEvent.DATA_UPDATED, self._on_data_updated)
        self.event_bus.subscribe(TileEvent.STATE_CHANGED, self._on_state_changed)

    def set_file_pair(self, file_pair: Optional[FilePair]):
        """
        Ustawia parę plików i inicjalizuje metadane.

        Args:
            file_pair: Para plików lub None
        """
        with self._lock:
            self._file_pair = file_pair

            if file_pair:
                self._state = MetadataState.LOADING
                self._load_metadata_from_file_pair()
                self._state = MetadataState.READY

                self.logger.debug(f"File pair set: {file_pair.get_base_name()}")
            else:
                self._state = MetadataState.UNINITIALIZED
                self._reset_metadata()

                self.logger.debug("File pair cleared")

            # Emit state change
            self.state_changed.emit(self._state.name)
            self.event_bus.emit_event(TileEvent.DATA_UPDATED, self)

    def _load_metadata_from_file_pair(self):
        """Ładuje metadane z FilePair do wewnętrznego stanu."""
        if not self._file_pair:
            return

        # Load current values
        self._metadata_snapshot.stars = self._file_pair.get_stars()
        self._metadata_snapshot.color_tag = self._file_pair.get_color_tag() or ""
        self._metadata_snapshot.is_selected = False  # Default
        self._metadata_snapshot.file_pair_id = self._file_pair.get_base_name()
        self._metadata_snapshot.timestamp = self._get_current_timestamp()

        # Clear pending changes
        self._pending_changes.clear()

        self.logger.debug(
            f"Loaded metadata: stars={self._metadata_snapshot.stars}, "
            f"color_tag={self._metadata_snapshot.color_tag}"
        )

    def _reset_metadata(self):
        """Resetuje metadane do wartości domyślnych."""
        self._metadata_snapshot = MetadataSnapshot()
        self._pending_changes.clear()
        self._change_history.clear()

    # ---- Public API for metadata management ----

    def get_stars(self) -> int:
        """Zwraca aktualną liczbę gwiazdek."""
        with self._lock:
            # Check pending changes first
            if MetadataChangeType.STARS_CHANGED in self._pending_changes:
                return self._pending_changes[MetadataChangeType.STARS_CHANGED]
            return self._metadata_snapshot.stars

    def set_stars(self, stars: int):
        """
        Ustawia liczbę gwiazdek.

        Args:
            stars: Liczba gwiazdek (0-5)
        """
        stars = max(0, min(5, stars))  # Validate range

        with self._lock:
            if self.get_stars() == stars:
                return  # No change

            self._pending_changes[MetadataChangeType.STARS_CHANGED] = stars
            self._track_change(MetadataChangeType.STARS_CHANGED, stars)

            # Update FilePair if available
            if self._file_pair:
                self._file_pair.set_stars(stars)

            self.logger.debug(f"Stars changed to: {stars}")

            # Schedule batch update or emit immediately based on config
            if getattr(self.config, "enable_batch_updates", False):
                self._schedule_batch_update()
            else:
                self.metadata_changed.emit("stars", stars)
                self.event_bus.emit_event(TileEvent.USER_INTERACTION, "stars", stars)

    def get_color_tag(self) -> str:
        """Zwraca aktualny tag koloru."""
        with self._lock:
            # Check pending changes first
            if MetadataChangeType.COLOR_TAG_CHANGED in self._pending_changes:
                return self._pending_changes[MetadataChangeType.COLOR_TAG_CHANGED]
            return self._metadata_snapshot.color_tag

    def set_color_tag(self, color_tag: str):
        """
        Ustawia tag koloru.

        Args:
            color_tag: Kod koloru hex lub pusty string
        """
        color_tag = color_tag or ""

        with self._lock:
            if self.get_color_tag() == color_tag:
                return  # No change

            self._pending_changes[MetadataChangeType.COLOR_TAG_CHANGED] = color_tag
            self._track_change(MetadataChangeType.COLOR_TAG_CHANGED, color_tag)

            # Update FilePair if available
            if self._file_pair:
                self._file_pair.set_color_tag(color_tag)

            self.logger.debug(f"Color tag changed to: {color_tag}")

            # Schedule batch update or emit immediately
            if getattr(self.config, "enable_batch_updates", False):
                self._schedule_batch_update()
            else:
                self.metadata_changed.emit("color_tag", color_tag)
                self.event_bus.emit_event(
                    TileEvent.USER_INTERACTION, "color_tag", color_tag
                )

    def get_selection(self) -> bool:
        """Zwraca stan selekcji."""
        with self._lock:
            # Check pending changes first
            if MetadataChangeType.SELECTION_CHANGED in self._pending_changes:
                return self._pending_changes[MetadataChangeType.SELECTION_CHANGED]
            return self._metadata_snapshot.is_selected

    def set_selection(self, is_selected: bool):
        """
        Ustawia stan selekcji.

        Args:
            is_selected: Czy kafelek jest zaznaczony
        """
        with self._lock:
            if self.get_selection() == is_selected:
                return  # No change

            self._pending_changes[MetadataChangeType.SELECTION_CHANGED] = is_selected
            self._track_change(MetadataChangeType.SELECTION_CHANGED, is_selected)

            self.logger.debug(f"Selection changed to: {is_selected}")

            # Selection changes should be immediate (no batching)
            self.metadata_changed.emit("selection", is_selected)
            self.event_bus.emit_event(
                TileEvent.USER_INTERACTION, "selection", is_selected
            )

    def get_metadata_snapshot(self) -> MetadataSnapshot:
        """Zwraca snapshot aktualnego stanu metadanych."""
        with self._lock:
            snapshot = MetadataSnapshot(
                stars=self.get_stars(),
                color_tag=self.get_color_tag(),
                is_selected=self.get_selection(),
                file_pair_id=self._metadata_snapshot.file_pair_id,
                timestamp=self._get_current_timestamp(),
            )
            return snapshot

    def apply_metadata_snapshot(self, snapshot: MetadataSnapshot):
        """
        Aplikuje snapshot metadanych.

        Args:
            snapshot: Snapshot do zastosowania
        """
        with self._lock:
            self.set_stars(snapshot.stars)
            self.set_color_tag(snapshot.color_tag)
            self.set_selection(snapshot.is_selected)

            self.logger.debug(f"Applied metadata snapshot from {snapshot.timestamp}")

    # ---- Change tracking and history ----

    def _track_change(self, change_type: MetadataChangeType, value: Any):
        """Śledzi zmianę w historii."""
        timestamp = self._get_current_timestamp()
        self._change_history.append((change_type, value, timestamp))

        # Keep history limited
        max_history = getattr(self.config, "max_change_history", 100)
        if len(self._change_history) > max_history:
            self._change_history = self._change_history[-max_history:]

        # Notify listeners
        for listener in self._change_listeners[change_type]:
            try:
                listener(value, timestamp)
            except Exception as e:
                self.logger.warning(f"Change listener error: {e}")

    def add_change_listener(self, change_type: MetadataChangeType, callback: Callable):
        """Dodaje listener dla zmian określonego typu."""
        self._change_listeners[change_type].add(callback)

    def remove_change_listener(
        self, change_type: MetadataChangeType, callback: Callable
    ):
        """Usuwa listener dla zmian określonego typu."""
        self._change_listeners[change_type].discard(callback)

    def get_change_history(self) -> list[tuple[MetadataChangeType, Any, float]]:
        """Zwraca historię zmian."""
        with self._lock:
            return list(self._change_history)

    def rollback_last_change(self, change_type: Optional[MetadataChangeType] = None):
        """
        Cofa ostatnią zmianę określonego typu lub ogólnie.

        Args:
            change_type: Typ zmiany do cofnięcia, None dla ostatniej dowolnej
        """
        with self._lock:
            if not self._change_history:
                return

            if change_type:
                # Find last change of specific type
                for i in range(len(self._change_history) - 1, -1, -1):
                    if self._change_history[i][0] == change_type:
                        change_type_found, old_value, timestamp = (
                            self._change_history.pop(i)
                        )

                        # Apply rollback
                        if change_type_found == MetadataChangeType.STARS_CHANGED:
                            self.set_stars(old_value)
                        elif change_type_found == MetadataChangeType.COLOR_TAG_CHANGED:
                            self.set_color_tag(old_value)
                        elif change_type_found == MetadataChangeType.SELECTION_CHANGED:
                            self.set_selection(old_value)

                        self.logger.debug(
                            f"Rolled back {change_type_found.name} to {old_value}"
                        )
                        break
            else:
                # Rollback last change
                change_type_found, old_value, timestamp = self._change_history.pop()

                if change_type_found == MetadataChangeType.STARS_CHANGED:
                    self.set_stars(old_value)
                elif change_type_found == MetadataChangeType.COLOR_TAG_CHANGED:
                    self.set_color_tag(old_value)
                elif change_type_found == MetadataChangeType.SELECTION_CHANGED:
                    self.set_selection(old_value)

                self.logger.debug(
                    f"Rolled back last change {change_type_found.name} to {old_value}"
                )

    # ---- Batch updates ----

    def _schedule_batch_update(self):
        """Planuje batch update."""
        batch_delay = getattr(self.config, "batch_update_delay_ms", 200)
        self._batch_timer.start(batch_delay)

    def _process_batch_updates(self):
        """Przetwarza zaległe batch updates."""
        with self._lock:
            if not self._pending_changes:
                return

            # Prepare batch
            batch_changes = dict(self._pending_changes)

            # Apply to snapshot
            for change_type, value in batch_changes.items():
                if change_type == MetadataChangeType.STARS_CHANGED:
                    self._metadata_snapshot.stars = value
                elif change_type == MetadataChangeType.COLOR_TAG_CHANGED:
                    self._metadata_snapshot.color_tag = value
                elif change_type == MetadataChangeType.SELECTION_CHANGED:
                    self._metadata_snapshot.is_selected = value

            # Clear pending
            self._pending_changes.clear()

            # Emit batch update
            self.batch_update_ready.emit(batch_changes)

            self.logger.debug(
                f"Processed batch update with {len(batch_changes)} changes"
            )

    def force_update(self):
        """Wymusza natychmiastowe przetworzenie pending changes."""
        self._batch_timer.stop()
        self._process_batch_updates()

    # ---- State management ----

    def get_state(self) -> MetadataState:
        """Zwraca aktualny stan komponentu."""
        return self._state

    def is_ready(self) -> bool:
        """Sprawdza czy komponent jest gotowy do użycia."""
        return self._state == MetadataState.READY

    def has_pending_changes(self) -> bool:
        """Sprawdza czy są nieprzetworzone zmiany."""
        with self._lock:
            return bool(self._pending_changes)

    # ---- Memory and performance ----

    def get_memory_usage(self) -> int:
        """Zwraca przybliżone użycie pamięci w bajtach."""
        # Rough estimation
        size = 0
        size += len(self._change_history) * 50  # Approximate per entry
        size += len(self._pending_changes) * 30
        size += len(str(self._metadata_snapshot)) * 2

        self._memory_usage = size
        return size

    def optimize_memory(self):
        """Optymalizuje użycie pamięci."""
        with self._lock:
            # Trim change history if too long
            max_history = getattr(self.config, "max_change_history", 50)
            if len(self._change_history) > max_history:
                self._change_history = self._change_history[-max_history:]

            # Clear old pending changes (shouldn't happen normally)
            if len(self._pending_changes) > 10:
                self.force_update()

            self.logger.debug("Memory optimized")

    # ---- Event handlers ----

    def _on_data_updated(self, source_component):
        """Handler dla zdarzenia aktualizacji danych."""
        if source_component == self:
            self.logger.debug("Ignoruję DATA_UPDATED event z tego samego komponentu")
            return

        if self.has_pending_changes():
            self.logger.debug("Ignoruję DATA_UPDATED event - mam pending changes")
            return

        if self._file_pair:
            self.logger.debug("Przeładowuję metadane z powodu external update")
            self._load_metadata_from_file_pair()

    def _on_state_changed(self, new_state_name: str):
        """Handler dla zdarzenia zmiany stanu."""
        # React to global state changes if needed
        pass

    # ---- Cleanup ----

    def cleanup(self):
        """Czyści zasoby komponentu."""
        with self._lock:
            # Process any pending changes
            self.force_update()

            # Clear data
            self._change_history.clear()
            self._pending_changes.clear()
            self._change_listeners.clear()

            # Stop timers
            if self._batch_timer.isActive():
                self._batch_timer.stop()

            # Unsubscribe from events
            self.event_bus.unsubscribe(TileEvent.DATA_UPDATED, self._on_data_updated)
            self.event_bus.unsubscribe(TileEvent.STATE_CHANGED, self._on_state_changed)

            self._state = MetadataState.UNINITIALIZED

            self.logger.debug("MetadataComponent cleaned up")

    # ---- Utilities ----

    def _get_current_timestamp(self) -> float:
        """Zwraca aktualny timestamp."""
        import time

        return time.time()

    def __del__(self):
        """Destruktor - cleanup resources."""
        try:
            self.cleanup()
        except Exception as e:
            # Suppress exceptions in destructor
            pass
