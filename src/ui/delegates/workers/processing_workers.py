"""
Workery do przetwarzania i generowania danych (miniaturek, metadanych).
"""

import logging
import os
import time
from typing import List, Tuple

from PyQt6.QtCore import QObject, QThreadPool, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPixmap

from .base_workers import UnifiedBaseWorker
from src.models.file_pair import FilePair
from src.logic import metadata_manager
from src.utils.image_utils import create_thumbnail_from_file

# Usuwamy import ThumbnailCache z poziomu modułu
# from src.ui.widgets.thumbnail_cache import ThumbnailCache

logger = logging.getLogger(__name__)


class ThumbnailGenerationWorker(UnifiedBaseWorker):
    """
    Worker do generowania miniaturek w tle.

    Ta klasa jest zoptymalizowaną wersją, która:
    1. Używa proper context management dla obiektów PIL.Image
    2. Ogranicza nadmierne logowanie
    3. Sprawdza cache tylko raz przed tworzeniem miniatury
    """

    def __init__(self, path: str, width: int, height: int):
        """
        Inicjalizuje worker do generowania miniaturek.

        Args:
            path: Ścieżka do pliku graficznego
            width: Pożądana szerokość miniaturki
            height: Pożądana wysokość miniaturki
        """
        super().__init__()
        self.path = path
        self.width = width
        self.height = height

    def _validate_inputs(self):
        """Waliduje parametry wejściowe."""
        if not self.path or not os.path.exists(self.path):
            raise ValueError(f"Plik nie istnieje: {self.path}")
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"Nieprawidłowe wymiary miniaturki: {self.width}x{self.height}")

    def emit_finished(self, pixmap: QPixmap):
        """Emituje sygnał zakończenia generowania miniaturki."""
        logger.debug(f"Miniatura wygenerowana: {self.path}")
        self.signals.thumbnail_finished.emit(pixmap, self.path, self.width, self.height)

    def emit_error(self, message: str):
        """Emituje sygnał błędu generowania miniaturki."""
        logger.error(f"Błąd generowania miniatury: {message}")
        self.signals.thumbnail_error.emit(message, self.path, self.width, self.height)

    def run(self):
        """Generuje miniaturkę dla określonego pliku."""
        try:
            self._validate_inputs()

            # Opóźniony import ThumbnailCache
            from src.ui.widgets.thumbnail_cache import ThumbnailCache
            
            # Sprawdź w cache
            cache = ThumbnailCache.get_instance()
            cached_pixmap = cache.get_thumbnail(self.path, self.width, self.height)
            
            if cached_pixmap is not None:
                logger.debug(f"Użyto miniatury z cache dla {os.path.basename(self.path)}")
                self.emit_finished(cached_pixmap)
                return

            # Nie znaleziono w cache, generuj miniaturkę
            self.emit_progress(10, f"Generowanie miniatury dla {os.path.basename(self.path)}...")
            
            # Generowanie miniaturki z proper context management
            try:
                pixmap = create_thumbnail_from_file(self.path, self.width, self.height)
                
                if pixmap.isNull():
                    self.emit_error(f"Nie udało się utworzyć miniatury dla {self.path}")
                    return
                
                # Zapisz do cache
                cache.add_thumbnail(self.path, self.width, self.height, pixmap)
                
                self.emit_progress(100, "Miniatura wygenerowana pomyślnie.")
                self.emit_finished(pixmap)
                
            except Exception as e:
                self.emit_error(f"Błąd podczas generowania miniatury: {str(e)}")
        
        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Nieoczekiwany błąd: {str(e)}")


class BatchThumbnailWorker(UnifiedBaseWorker):
    """
    Worker do generowania wielu miniaturek jednocześnie.
    
    Optymalizuje wydajność przetwarzając wiele miniaturek w jednym zadaniu,
    co eliminuje overhead tworzenia nowych wątków dla każdej miniaturki.
    """

    def __init__(self, thumbnail_requests: list[tuple[str, int, int]]):
        """
        Inicjalizuje worker do generowania wsadowego miniaturek.

        Args:
            thumbnail_requests: Lista krotek (ścieżka, szerokość, wysokość)
        """
        super().__init__()
        self.thumbnail_requests = thumbnail_requests

    def _validate_inputs(self):
        """Waliduje parametry wejściowe."""
        if not self.thumbnail_requests:
            raise ValueError("Lista żądań miniaturek jest pusta")

    def emit_finished(self, pixmap, path, width, height):
        """Emituje sygnał zakończenia generowania pojedynczej miniaturki."""
        logger.debug(f"Miniatura wygenerowana w batch: {path}")
        self.signals.thumbnail_finished.emit(pixmap, path, width, height)

    def emit_error(self, message, path, width, height):
        """Emituje sygnał błędu generowania pojedynczej miniaturki."""
        logger.error(f"Błąd generowania miniatury w batch: {message}")
        self.signals.thumbnail_error.emit(message, path, width, height)

    def run(self):
        """Generuje wszystkie miniaturki z listy żądań."""
        try:
            self._validate_inputs()

            # Opóźniony import ThumbnailCache
            from src.ui.widgets.thumbnail_cache import ThumbnailCache
            
            total_requests = len(self.thumbnail_requests)
            self.emit_progress(0, f"Rozpoczęto generowanie {total_requests} miniatur...")

            cache = ThumbnailCache.get_instance()
            processed_count = 0

            for idx, (path, width, height) in enumerate(self.thumbnail_requests):
                if self.check_interruption():
                    return

                # Emituj progress co 10% lub co 5 miniaturek
                if idx % max(1, total_requests // 10) == 0 or idx % 5 == 0:
                    percent = int((idx / total_requests) * 100)
                    self.emit_progress(percent, f"Generowanie miniatur: {idx}/{total_requests}...")

                try:
                    # Sprawdź w cache
                    cached_pixmap = cache.get_thumbnail(path, width, height)
                    if cached_pixmap is not None:
                        self.emit_finished(cached_pixmap, path, width, height)
                        processed_count += 1
                        continue

                    # Generuj miniaturkę
                    if not os.path.exists(path):
                        self.emit_error(f"Plik nie istnieje", path, width, height)
                        continue

                    pixmap = create_thumbnail_from_file(path, width, height)
                    
                    if pixmap.isNull():
                        self.emit_error("Nie udało się utworzyć miniatury", path, width, height)
                        continue
                    
                    # Zapisz do cache
                    cache.add_thumbnail(path, width, height, pixmap)
                    
                    # Wyemituj sygnał dla każdej miniaturki osobno
                    self.emit_finished(pixmap, path, width, height)
                    processed_count += 1
                    
                except Exception as e:
                    self.emit_error(f"Błąd: {str(e)}", path, width, height)
            
            # Zakończ cały worker
            self.emit_progress(
                100, 
                f"Zakończono generowanie miniatur. Sukces: {processed_count}/{total_requests}"
            )
            self.emit_finished(processed_count)

        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}", "", 0, 0)
        except Exception as e:
            self.emit_error(f"Nieoczekiwany błąd: {str(e)}", "", 0, 0)


class DataProcessingWorker(QObject):
    """
    Worker do przetwarzania danych w tle. Odpowiedzialny za:
    1. Zastosowanie metadanych do par plików (operacja I/O).
    2. Emitowanie sygnałów do tworzenia kafelków w głównym wątku.

    Ta klasa dziedziczy po QObject aby umożliwić przenoszenie do wątku za pomocą moveToThread.
    """

    # Bezpośrednie sygnały
    tile_data_ready = pyqtSignal(FilePair)
    tiles_batch_ready = pyqtSignal(list)  # NOWY: sygnał dla batch'y kafelków
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    interrupted = pyqtSignal()

    def __init__(self, working_directory: str, file_pairs: list[FilePair]):
        """
        Inicjalizuje worker do przetwarzania danych.
        
        Args:
            working_directory: Katalog roboczy aplikacji
            file_pairs: Lista par plików do przetworzenia
        """
        super().__init__()
        self.working_directory = working_directory
        self.file_pairs = file_pairs
        self._interrupted = False
        self._last_progress_time = 0
        self._progress_interval_ms = 100  # Minimalny odstęp między sygnałami (ms)

    def check_interruption(self) -> bool:
        """
        Sprawdza czy worker został przerwany.
        
        Returns:
            True jeśli przerwano, False w przeciwnym razie
        """
        if self._interrupted:
            logger.debug("DataProcessingWorker: Operacja przerwana")
            self.interrupted.emit()
            return True
        return False

    def interrupt(self):
        """Przerywa wykonywanie workera."""
        self._interrupted = True
        logger.debug("DataProcessingWorker: Otrzymano żądanie przerwania")

    def emit_progress(self, percent: int, message: str):
        """Emituje sygnał postępu z logowaniem."""
        logger.debug(f"DataProcessingWorker: Postęp {percent}% - {message}")
        self.progress.emit(percent, message)

    def emit_progress_batched(self, current: int, total: int, message: str):
        """Emituje sygnał postępu z limitem częstotliwości."""
        current_time = time.time() * 1000  # Czas w milisekundach

        # Zawsze emituj pierwszy (0%) i ostatni (100%) progress oraz co _progress_interval_ms
        percent = int((current / max(total, 1)) * 100)
        is_first = current == 0
        is_last = current >= total

        if (
            is_first
            or is_last
            or (current_time - self._last_progress_time) >= self._progress_interval_ms
        ):
            self.emit_progress(percent, message)
            self._last_progress_time = current_time

    def emit_error(self, message: str, exception: Exception = None):
        """Emituje sygnał błędu z logowaniem."""
        if exception:
            logger.error(f"DataProcessingWorker: {message}", exc_info=True)
        else:
            logger.error(f"DataProcessingWorker: {message}")
        self.error.emit(message)

    def emit_finished(self, result=None):
        """Emituje sygnał zakończenia z logowaniem."""
        logger.info("DataProcessingWorker: Zakończono pomyślnie")
        self.finished.emit(result)

    @pyqtSlot()
    def run(self):
        """Przetwarza dane i emituje sygnały dla kafelków."""
        try:
            processed_pairs = []
            total_pairs = len(self.file_pairs)
            
            # Przetwarzanie wsadowe - generuj kafelki w grupach
            batch_size = 10  # Rozmiar wsadu
            current_batch = []
            
            for i, file_pair in enumerate(self.file_pairs):
                if self.check_interruption():
                    return
                
                # Emituj progress co 10% lub co 5 plików
                self.emit_progress_batched(i, total_pairs, f"Przetwarzanie: {i}/{total_pairs}")
                
                try:
                    # Dodaj parę do bieżącej partii
                    current_batch.append(file_pair)
                    processed_pairs.append(file_pair)
                    
                    # Jeśli osiągnięto rozmiar partii lub jest to ostatni element, wyemituj sygnał
                    if len(current_batch) >= batch_size or i == total_pairs - 1:
                        # Wyślij sygnał z całą partią
                        self.tiles_batch_ready.emit(current_batch)
                        # Wyczyść partię
                        current_batch = []
                    
                except Exception as e:
                    self.emit_error(f"Błąd przetwarzania pliku {file_pair}: {str(e)}", e)
            
            # Zakończ przetwarzanie
            self.emit_progress(100, f"Zakończono przetwarzanie {len(processed_pairs)}/{total_pairs} plików")
            self.emit_finished(processed_pairs)
            
        except Exception as e:
            self.emit_error(f"Nieoczekiwany błąd: {str(e)}", e)

    def stop(self):
        """Zatrzymuje wykonywanie workera."""
        self.interrupt()


class SaveMetadataWorker(UnifiedBaseWorker):
    """
    Worker do zapisywania metadanych w tle.
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
            working_directory: Katalog roboczy aplikacji
            file_pairs: Lista par plików
            unpaired_archives: Lista niepowiązanych archiwów
            unpaired_previews: Lista niepowiązanych podglądów
        """
        super().__init__()
        self.working_directory = working_directory
        self.file_pairs = file_pairs
        self.unpaired_archives = unpaired_archives or []
        self.unpaired_previews = unpaired_previews or []

    def _validate_inputs(self):
        """Waliduje parametry wejściowe."""
        if not os.path.isdir(self.working_directory):
            raise ValueError(f"Katalog roboczy nie istnieje: {self.working_directory}")

    def run(self):
        """Zapisuje metadane w pliku JSON."""
        try:
            self._validate_inputs()
            
            # Normalizacja ścieżki katalogu roboczego
            working_dir = self.working_directory
            
            # Liczba par i plików do zapisania
            total_items = len(self.file_pairs) + len(self.unpaired_archives) + len(self.unpaired_previews)
            
            self.emit_progress(10, f"Zapisywanie metadanych dla {total_items} elementów...")
            
            try:
                # Główna operacja zapisywania metadanych
                metadata_manager.save_metadata(
                    working_dir,
                    self.file_pairs,
                    self.unpaired_archives,
                    self.unpaired_previews
                )
                
                self.emit_progress(100, "Metadane zapisane pomyślnie.")
                self.emit_finished(True)
                
            except Exception as e:
                self.emit_error(f"Błąd podczas zapisywania metadanych: {str(e)}", e)
                
        except ValueError as ve:
            self.emit_error(f"Błąd walidacji: {str(ve)}")
        except Exception as e:
            self.emit_error(f"Nieoczekiwany błąd: {str(e)}", e) 