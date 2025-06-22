"""
Workery do przetwarzania i generowania danych (miniaturek, metadanych).
"""

import logging
import os
from typing import List, Tuple

from src.models.file_pair import FilePair

from .base_workers import AsyncUnifiedBaseWorker, UnifiedBaseWorker, WorkerPriority

logger = logging.getLogger(__name__)


class ThumbnailGenerationWorker(UnifiedBaseWorker):
    """
    UNIFIED: Worker do generowania miniaturek z simplified architecture.
    """

    def __init__(
        self, path: str, width: int, height: int, priority: int = WorkerPriority.NORMAL
    ):
        super().__init__(timeout_seconds=30, priority=priority)
        self.path = path
        self.width = width
        self.height = height
        # Pre-validate inputs in constructor for fail-fast behavior
        self._validate_inputs()

    def _validate_inputs(self):
        """Enhanced validation with detailed error messages."""
        if not self.path:
            raise ValueError("Path cannot be empty")
        if not os.path.exists(self.path):
            raise ValueError(f"File does not exist: {self.path}")
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"Invalid dimensions: {self.width}x{self.height}")

        # Check file size for large files (>50MB)
        try:
            file_size = os.path.getsize(self.path)
            if file_size > 50 * 1024 * 1024:  # 50MB
                logger.warning(
                    f"Large file detected: {file_size//1024//1024}MB - {self.path}"
                )
        except OSError:
            pass

    def _run_implementation(self):
        """OPTIMIZED: Single cache check pattern."""
        from src.ui.widgets.thumbnail_cache import ThumbnailCache
        from src.utils.image_utils import create_thumbnail_from_file

        cache = ThumbnailCache.get_instance()

        # SINGLE CACHE CHECK - reduce overhead
        cached_pixmap = cache.get_thumbnail(self.path, self.width, self.height)
        if cached_pixmap is not None:
            self.signals.thumbnail_finished.emit(
                cached_pixmap, self.path, self.width, self.height
            )
            return

        # Generate thumbnail with progress reporting
        self.emit_progress(25, f"Loading {os.path.basename(self.path)}...")

        try:
            pixmap = create_thumbnail_from_file(self.path, self.width, self.height)

            if pixmap.isNull():
                raise ValueError("Failed to create thumbnail - invalid image")

            # Add to cache atomically
            cache.add_thumbnail(self.path, self.width, self.height, pixmap)

            self.emit_progress(100, "Thumbnail generated successfully")
            self.signals.thumbnail_finished.emit(
                pixmap, self.path, self.width, self.height
            )

        except Exception as e:
            error_msg = f"Thumbnail generation failed: {str(e)}"
            self.signals.thumbnail_error.emit(
                error_msg, self.path, self.width, self.height
            )
            raise


class BatchThumbnailWorker(UnifiedBaseWorker):
    """
    UNIFIED: Worker do generowania wielu miniaturek jednocześnie z adaptive batch size.
    """

    def __init__(
        self,
        thumbnail_requests: List[Tuple[str, int, int]],
        priority: int = WorkerPriority.HIGH,
    ):
        super().__init__(timeout_seconds=300, priority=priority)
        self.thumbnail_requests = thumbnail_requests
        self._validate_inputs()

    def _validate_inputs(self):
        if not self.thumbnail_requests:
            raise ValueError("Lista żądań miniaturek jest pusta")

    def _run_implementation(self):
        from src.ui.widgets.thumbnail_cache import ThumbnailCache
        from src.utils.image_utils import create_thumbnail_from_file

        cache = ThumbnailCache.get_instance()
        total_requests = len(self.thumbnail_requests)
        self.emit_progress(0, f"Rozpoczęto generowanie {total_requests} miniatur...")
        batch_size = self._calculate_adaptive_batch_size(total_requests)
        processed_count = 0
        for idx, (path, width, height) in enumerate(self.thumbnail_requests):
            if self.check_interruption():
                return
            cached_pixmap = cache.get_thumbnail(path, width, height)
            if cached_pixmap is not None:
                self.signals.thumbnail_finished.emit(cached_pixmap, path, width, height)
            else:
                try:
                    pixmap = create_thumbnail_from_file(path, width, height)
                    if pixmap.isNull():
                        raise ValueError("Failed to create thumbnail - invalid image")
                    cache.add_thumbnail(path, width, height, pixmap)
                    self.signals.thumbnail_finished.emit(pixmap, path, width, height)
                except Exception as e:
                    error_msg = f"Thumbnail generation failed: {str(e)}"
                    self.signals.thumbnail_error.emit(error_msg, path, width, height)
            processed_count += 1
            if processed_count % batch_size == 0 or processed_count == total_requests:
                percent = int((processed_count / total_requests) * 100)
                self.emit_progress(
                    percent, f"Processed {processed_count}/{total_requests} thumbnails"
                )

    def _calculate_adaptive_batch_size(self, total: int) -> int:
        if total <= 50:
            return 5
        elif total <= 500:
            return 20
        elif total <= 2000:
            return 50
        else:
            return 100


class DataProcessingWorker(UnifiedBaseWorker):
    """
    UNIFIED: Data processing worker converted to UnifiedBaseWorker.
    Eliminates QObject moveToThread pattern for better performance.
    """

    tile_data_ready = None  # sygnały będą podpinane dynamicznie przez signals
    tiles_batch_ready = None
    tiles_refresh_needed = None

    def __init__(
        self, working_directory: str, file_pairs: List, timeout_seconds: int = 300
    ):
        super().__init__(timeout_seconds=timeout_seconds, priority=WorkerPriority.HIGH)
        self.working_directory = working_directory
        self.file_pairs = file_pairs or []
        self._metadata_loaded = False
        self._validate_inputs()

    def _validate_inputs(self):
        if not self.working_directory:
            raise ValueError("Working directory cannot be empty")
        if not self.file_pairs:
            raise ValueError("File pairs list cannot be empty")

    def _run_implementation(self):
        total_pairs = len(self.file_pairs)
        batch_size = self._calculate_adaptive_batch_size(total_pairs)
        self.emit_progress(0, f"Processing {total_pairs} file pairs...")
        processed_pairs = []
        current_batch = []
        for i, file_pair in enumerate(self.file_pairs):
            if self.check_interruption():
                return
            current_batch.append(file_pair)
            processed_pairs.append(file_pair)
            if len(current_batch) >= batch_size:
                self._emit_batch_with_metadata(current_batch.copy())
                current_batch.clear()
                progress = int((i / total_pairs) * 90)
                self.emit_progress(progress, f"Processed {i+1}/{total_pairs} pairs")
        if current_batch:
            self._emit_batch_with_metadata(current_batch)
        self.emit_progress(100, f"Completed processing {total_pairs} file pairs")
        self.signals.finished.emit(processed_pairs)

    def _calculate_adaptive_batch_size(self, total_pairs: int) -> int:
        if total_pairs <= 50:
            return 5
        elif total_pairs <= 500:
            return 20
        elif total_pairs <= 2000:
            return 50
        else:
            return 100

    def _emit_batch_with_metadata(self, batch: List):
        self.signals.tiles_batch_ready.emit(batch)
        self._load_metadata_async(batch)

    def _load_metadata_async(self, file_pairs: List):
        try:
            from src.logic.metadata_manager import MetadataManager

            metadata_manager = MetadataManager.get_instance(self.working_directory)
            metadata_applied = metadata_manager.apply_metadata_to_file_pairs(file_pairs)
            if metadata_applied:
                self.signals.tiles_refresh_needed.emit(file_pairs)
        except Exception as e:
            logger.error(f"Async metadata loading failed: {e}")


class SaveMetadataWorker(AsyncUnifiedBaseWorker):
    """
    Worker do zapisywania metadanych z obsługą operacji asynchronicznych.
    """

    def __init__(
        self,
        working_directory: str,
        file_pairs: list[FilePair],
        unpaired_archives: list[str] = None,
        unpaired_previews: list[str] = None,
    ):
        """
        Inicjalizuje worker do zapisywania metadanych.

        Args:
            working_directory: Katalog roboczy
            file_pairs: Lista par plików
            unpaired_archives: Lista niesparowanych archiwów
            unpaired_previews: Lista niesparowanych podglądów
        """
        # Timeout 2 minuty dla operacji metadanych
        super().__init__(timeout_seconds=120, priority=WorkerPriority.HIGH)
        self.working_directory = working_directory
        self.file_pairs = file_pairs or []
        self.unpaired_archives = unpaired_archives or []
        self.unpaired_previews = unpaired_previews or []

    def _validate_inputs(self):
        """Waliduje parametry wejściowe."""
        if not self.working_directory:
            raise ValueError("Katalog roboczy nie może być pusty")

    def _run_implementation(self):
        """Zapisuje metadane z resource protection."""
        try:
            self._validate_inputs()

            self.emit_progress(0, "Rozpoczęto zapisywanie metadanych...")

            # Zapisz metadane z resource protection + FORCE SAVE
            def save_metadata():
                from src.logic.metadata_manager import MetadataManager

                metadata_manager = MetadataManager.get_instance(self.working_directory)

                # DEBUG: Sprawdź co jest zapisywane
                logger = logging.getLogger(__name__)

                for i, file_pair in enumerate(
                    self.file_pairs[:3]
                ):  # Tylko pierwsze 3 dla debug
                    stars = file_pair.get_stars()
                    color = file_pair.get_color_tag()
                    logger.debug(
                        f"DEBUG SAVE [{i}]: {file_pair.get_base_name()} - "
                        f"Stars: {stars}, Color: '{color}'"
                    )

                # KROK 1: Dodaj do bufora
                metadata_manager.save_metadata(
                    self.file_pairs, self.unpaired_archives, self.unpaired_previews
                )

                # KROK 2: WYMUŚ NATYCHMIASTOWY ZAPIS DO PLIKU!
                metadata_manager.force_save()

                return True

            # Użyj resource protection dla metadata_manager
            result = self.with_metadata_lock(save_metadata)

            if result:
                self.emit_progress(100, "Metadane zapisane pomyślnie")
                self.emit_finished("Metadane zapisane pomyślnie")
            else:
                self.emit_error("Nie udało się zapisać metadanych")

        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Błąd podczas zapisywania metadanych: {str(e)}", e)


class StreamingMetadataWorker(AsyncUnifiedBaseWorker):
    """
    NEW: Streaming metadata worker for non-blocking metadata operations.
    """

    def __init__(self, working_directory: str, file_pairs: List, chunk_size: int = 50):
        super().__init__(timeout_seconds=300, priority=WorkerPriority.HIGH)
        self.working_directory = working_directory
        self.file_pairs = file_pairs or []
        self.chunk_size = chunk_size
        self._validate_inputs()

    def _validate_inputs(self):
        if not self.working_directory:
            raise ValueError("Working directory cannot be empty")
        if not self.file_pairs:
            raise ValueError("File pairs list cannot be empty")
        if self.chunk_size <= 0:
            raise ValueError("Chunk size must be positive")

    def _run_implementation(self):
        from src.logic.metadata_manager import MetadataManager

        total = len(self.file_pairs)
        processed = 0
        metadata_manager = MetadataManager.get_instance(self.working_directory)
        while processed < total:
            chunk = self.file_pairs[processed : processed + self.chunk_size]
            metadata_dict = metadata_manager.get_metadata_for_file_pairs(chunk)
            self.signals.metadata_chunk_ready.emit(chunk, metadata_dict)
            processed += len(chunk)
            percent = int((processed / total) * 100)
            self.emit_progress(percent, f"Załadowano metadane: {processed}/{total}")
        self.signals.metadata_streaming_finished.emit(total)
