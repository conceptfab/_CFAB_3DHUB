"""
Centralna konfiguracja dla FileTileWidget - tile_config.py
🚀 ETAP 3: Architectural Split - komponent konfiguracji
"""

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)


class TileState(Enum):
    """Stany cyklu życia kafelka."""

    INITIALIZING = auto()
    LOADING_THUMBNAIL = auto()
    READY = auto()
    ERROR = auto()
    DISPOSED = auto()


class TileEvent(Enum):
    """Wydarzenia emitowane przez komponenty kafelka."""

    THUMBNAIL_LOADED = auto()
    THUMBNAIL_ERROR = auto()
    DATA_UPDATED = auto()
    STATE_CHANGED = auto()
    USER_INTERACTION = auto()
    SIZE_CHANGED = auto()
    METADATA_CHANGED = auto()


@dataclass
class TileConfig:
    """
    Centralna konfiguracja dla FileTileWidget.
    Eliminuje magic numbers i centralizuje wszystkie parametry.
    """

    # === WYMIARY PODSTAWOWE ===
    thumbnail_size: Tuple[int, int] = (250, 250)  # Rozmiar całego kafelka
    padding: int = 16  # Padding wewnętrzny kafelka
    tile_margin: int = 6  # Margines zewnętrzny

    # === WYMIARY KOMPONENTÓW ===
    filename_max_height: int = 35  # Max wysokość nazwy pliku
    metadata_max_height: int = 24  # Max wysokość kontrolek metadanych
    min_thumbnail_width: int = 80  # Minimalny rozmiar miniatury
    min_thumbnail_height: int = 80

    # === CZCIONKA ===
    font_size_range: Tuple[int, int] = (8, 18)  # Min/max rozmiar czcionki
    font_scale_factor: int = 12  # Współczynnik skalowania czcionki

    # === LAYOUTY ===
    layout_margins: Tuple[int, int, int, int] = (
        8,
        12,
        8,
        8,
    )  # left, top, right, bottom
    layout_spacing: int = 4
    border_radius: int = 6
    border_width: int = 1
    color_border_width: int = 2  # Szerokość kolorowej obwódki

    # === WYDAJNOŚĆ ===
    enable_animations: bool = True
    enable_caching: bool = True
    enable_progressive_loading: bool = True
    max_memory_per_tile_mb: int = 8  # Zwiększono z 5 na 8 dla SBSAR
    thumbnail_quality: int = 85  # Jakość JPEG dla miniaturek
    animation_duration_ms: int = 200
    debounce_interval_ms: int = 33  # Zmniejszono z 100 na 33ms (~30fps)
    debounce_delay_ms: int = 50  # Zmniejszono z 150 na 50ms dla szybszej reakcji

    # === ASYNC LOADING ===
    async_loading: bool = True
    enable_webp: bool = True
    enable_lazy_loading: bool = True
    max_concurrent_loads: int = 3  # Max równoczesnych ładowań miniaturek
    thumbnail_timeout_ms: int = 5000  # Timeout dla ładowania miniaturek

    # === CACHE ===
    cache_size_mb: int = 300  # Zwiększono z 100 na 300 dla SBSAR
    cache_ttl_seconds: int = 3600  # TTL dla cache entries
    enable_disk_cache: bool = True

    # === DEBUG ===
    enable_debug_logging: bool = False
    enable_performance_monitoring: bool = False
    log_memory_usage: bool = False

    # === DRAG & DROP ===
    drag_threshold_px: int = 5  # Próg rozpoczęcia drag&drop
    drag_pixmap_size: Tuple[int, int] = (100, 100)  # Rozmiar pixmap podczas drag

    def __post_init__(self):
        """Walidacja konfiguracji po inicjalizacji."""
        self._validate_config()

        if self.enable_debug_logging:
            logger.debug(f"TileConfig utworzona: {self}")

    def _validate_config(self):
        """Waliduje parametry konfiguracji."""
        errors = []

        # Validate wymiary
        if self.thumbnail_size[0] < self.min_thumbnail_width:
            errors.append(
                f"thumbnail_size width ({self.thumbnail_size[0]}) < min_thumbnail_width ({self.min_thumbnail_width})"
            )

        if self.thumbnail_size[1] < self.min_thumbnail_height:
            errors.append(
                f"thumbnail_size height ({self.thumbnail_size[1]}) < min_thumbnail_height ({self.min_thumbnail_height})"
            )

        # Validate font
        if self.font_size_range[0] > self.font_size_range[1]:
            errors.append(
                f"font_size_range min ({self.font_size_range[0]}) > max ({self.font_size_range[1]})"
            )

        # Validate performance
        if self.max_memory_per_tile_mb <= 0:
            errors.append(
                f"max_memory_per_tile_mb must be > 0, got {self.max_memory_per_tile_mb}"
            )

        if self.max_concurrent_loads <= 0:
            errors.append(
                f"max_concurrent_loads must be > 0, got {self.max_concurrent_loads}"
            )

        # Validate intervals
        if self.debounce_interval_ms < 0:
            errors.append(
                f"debounce_interval_ms must be >= 0, got {self.debounce_interval_ms}"
            )

        if errors:
            raise ValueError(f"TileConfig validation errors: {'; '.join(errors)}")

    def get_calculated_thumbnail_dimension(self) -> int:
        """
        Oblicza rzeczywisty wymiar miniatury na podstawie rozmiaru kafelka.
        Replaces magic number calculations z oryginalnego kodu.
        """
        # Original logic z file_tile_widget.py linie 240-248
        thumb_dimension = min(
            self.thumbnail_size[0] - self.padding * 2,
            self.thumbnail_size[1]
            - self.filename_max_height
            - self.metadata_max_height
            - self.padding * 2,
        )

        # Zabezpieczenie przed ujemnymi wymiarami
        return max(thumb_dimension, self.min_thumbnail_width)

    def get_calculated_font_size(self, tile_width: int) -> int:
        """
        Oblicza rozmiar czcionki na podstawie szerokości kafelka.
        Replaces magic number calculation z oryginalnego kodu.
        """
        # Original logic z file_tile_widget.py linie 134-139
        base_font_size = max(
            self.font_size_range[0],
            min(self.font_size_range[1], int(tile_width / self.font_scale_factor)),
        )
        return base_font_size

    def calculate_memory_target_bytes(self) -> int:
        """Oblicza target memory usage w bajtach."""
        return self.max_memory_per_tile_mb * 1024 * 1024

    def is_memory_usage_acceptable(self, current_bytes: int) -> bool:
        """Sprawdza czy current memory usage jest w akceptowalnych granicach."""
        target_bytes = self.calculate_memory_target_bytes()
        return current_bytes <= target_bytes

    def get_debug_info(self) -> Dict[str, Any]:
        """Zwraca informacje debug o konfiguracji."""
        return {
            "thumbnail_dimension": self.get_calculated_thumbnail_dimension(),
            "memory_target_mb": self.max_memory_per_tile_mb,
            "memory_target_bytes": self.calculate_memory_target_bytes(),
            "async_enabled": self.async_loading,
            "cache_enabled": self.enable_caching,
            "animations_enabled": self.enable_animations,
        }


# === PREDEFINIOWANE KONFIGURACJE ===


def create_default_config() -> TileConfig:
    """Tworzy domyślną konfigurację."""
    return TileConfig()


def create_performance_config() -> TileConfig:
    """Konfiguracja zoptymalizowana pod performance."""
    return TileConfig(
        enable_animations=False,
        max_memory_per_tile_mb=3,  # Agresywna optymalizacja pamięci
        thumbnail_quality=70,  # Niższa jakość = mniej pamięci
        max_concurrent_loads=5,  # Więcej równoczesnych ładowań
        debounce_interval_ms=50,  # Szybszy debouncing
        enable_performance_monitoring=True,
        log_memory_usage=True,
    )


def create_quality_config() -> TileConfig:
    """Konfiguracja zoptymalizowana pod jakość."""
    return TileConfig(
        enable_animations=True,
        max_memory_per_tile_mb=8,  # Więcej pamięci na jakość
        thumbnail_quality=95,  # Wysoka jakość
        max_concurrent_loads=2,  # Mniej równoczesnych = stabilność
        debounce_interval_ms=200,  # Dłuższy debouncing = stabilność
        enable_debug_logging=True,
    )


def create_testing_config() -> TileConfig:
    """Konfiguracja dla testów."""
    return TileConfig(
        thumbnail_size=(100, 100),  # Małe kafelki dla testów
        enable_animations=False,  # Bez animacji w testach
        async_loading=False,  # Synchroniczne loading dla testów
        enable_caching=False,  # Bez cache w testach
        enable_debug_logging=True,
        enable_performance_monitoring=True,
        thumbnail_timeout_ms=1000,  # Krótki timeout
    )


# === LEGACY COMPATIBILITY ===

# Mapowanie starych stałych na nową konfigurację
# For backward compatibility z istniejącym kodem
DEFAULT_CONFIG = create_default_config()

# Legacy constants - deprecated ale zachowane dla compatibility
LEGACY_DEFAULT_THUMBNAIL_SIZE = DEFAULT_CONFIG.thumbnail_size
LEGACY_MIN_THUMBNAIL_WIDTH = DEFAULT_CONFIG.min_thumbnail_width
LEGACY_TILE_PADDING = DEFAULT_CONFIG.padding
LEGACY_FILENAME_MAX_HEIGHT = DEFAULT_CONFIG.filename_max_height
LEGACY_METADATA_MAX_HEIGHT = DEFAULT_CONFIG.metadata_max_height
