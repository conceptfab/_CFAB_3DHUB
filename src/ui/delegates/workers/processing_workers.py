"""
Workery do przetwarzania i generowania danych (miniaturek, metadanych).
"""

import logging
import os
import time
from typing import List, Tuple

from PyQt6.QtCore import QObject, QThreadPool, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPixmap

from src.logic.metadata_manager import MetadataManager
from src.models.file_pair import FilePair
from src.utils.image_utils import create_thumbnail_from_file

from .base_workers import AsyncUnifiedBaseWorker, UnifiedBaseWorker, WorkerPriority

# Usuwamy import ThumbnailCache z poziomu modułu
# from src.ui.widgets.thumbnail_cache import ThumbnailCache

logger = logging.getLogger(__name__)


class ThumbnailGenerationWorker(UnifiedBaseWorker):
    """
    Worker do generowania miniaturek w tle z optymalizacjami.

    Ta klasa jest zoptymalizowaną wersją, która:
    1. Używa proper context management dla obiektów PIL.Image
    2. Ogranicza nadmierne logowanie
    3. Sprawdza cache tylko raz przed tworzeniem miniatury
    4. Używa resource protection dla thumbnail cache
    5. Obsługuje timeout dla długotrwałych operacji
    """

    def __init__(
        self, path: str, width: int, height: int, priority: int = WorkerPriority.NORMAL
    ):
        """
        Inicjalizuje worker do generowania miniaturek.

        Args:
            path: Ścieżka do pliku graficznego
            width: Pożądana szerokość miniaturki
            height: Pożądana wysokość miniaturki
            priority: Priorytet workera
        """
        # Timeout 30s dla pojedynczej miniaturki
        super().__init__(timeout_seconds=30, priority=priority)
        self.path = path
        self.width = width
        self.height = height

    def _validate_inputs(self):
        """Waliduje parametry wejściowe."""
        if not self.path or not os.path.exists(self.path):
            raise ValueError(f"Plik nie istnieje: {self.path}")
        if self.width <= 0 or self.height <= 0:
            raise ValueError(
                f"Nieprawidłowe wymiary miniaturki: {self.width}x{self.height}"
            )

    def emit_finished(self, pixmap: QPixmap):
        """Emituje sygnał zakończenia generowania miniaturki."""
        logger.debug(f"Miniatura wygenerowana: {self.path}")
        self.signals.thumbnail_finished.emit(pixmap, self.path, self.width, self.height)

    def emit_error(self, message: str):
        """Emituje sygnał błędu generowania miniaturki."""
        logger.error(f"Błąd generowania miniatury: {message}")
        self.signals.thumbnail_error.emit(message, self.path, self.width, self.height)

    def _run_implementation(self):
        """Generuje miniaturkę dla określonego pliku."""
        try:
            self._validate_inputs()

            # Opóźniony import ThumbnailCache
            from src.ui.widgets.thumbnail_cache import ThumbnailCache

            # Sprawdź w cache z resource protection
            def get_from_cache():
                cache = ThumbnailCache.get_instance()
                return cache.get_thumbnail(self.path, self.width, self.height)

            cached_pixmap = self.with_thumbnail_cache_lock(get_from_cache)

            if cached_pixmap is not None:
                logger.debug(
                    f"Użyto miniatury z cache dla {os.path.basename(self.path)}"
                )
                self.emit_finished(cached_pixmap)
                return

            # Nie znaleziono w cache, generuj miniaturkę
            self.emit_progress(
                10, f"Generowanie miniatury dla {os.path.basename(self.path)}..."
            )

            # Sprawdź timeout przed długotrwałą operacją
            if self.check_interruption():
                return

            # Generowanie miniaturki z proper context management
            try:
                pixmap = create_thumbnail_from_file(self.path, self.width, self.height)

                if pixmap.isNull():
                    self.emit_error(f"Nie udało się utworzyć miniatury dla {self.path}")
                    return

                # Zapisz do cache z resource protection
                def save_to_cache():
                    cache = ThumbnailCache.get_instance()
                    cache.add_thumbnail(self.path, self.width, self.height, pixmap)

                self.with_thumbnail_cache_lock(save_to_cache)

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
    Worker do generowania wielu miniaturek jednocześnie z optymalizacjami.

    Optymalizuje wydajność przetwarzając wiele miniaturek w jednym zadaniu,
    co eliminuje overhead tworzenia nowych wątków dla każdej miniaturki.
    """

    def __init__(
        self,
        thumbnail_requests: List[Tuple[str, int, int]],
        priority: int = WorkerPriority.HIGH,
    ):
        """
        Inicjalizuje worker do generowania wsadowego miniaturek.

        Args:
            thumbnail_requests: Lista krotek (ścieżka, szerokość, wysokość)
            priority: Priorytet workera (domyślnie HIGH dla batch operations)
        """
        # Timeout 5 minut dla batch operations
        super().__init__(timeout_seconds=300, priority=priority)
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

    def _run_implementation(self):
        """Generuje wszystkie miniaturki z listy żądań."""
        try:
            self._validate_inputs()

            # Opóźniony import ThumbnailCache
            from src.ui.widgets.thumbnail_cache import ThumbnailCache

            total_requests = len(self.thumbnail_requests)
            self.emit_progress(
                0, f"Rozpoczęto generowanie {total_requests} miniatur..."
            )

            processed_count = 0

            for idx, (path, width, height) in enumerate(self.thumbnail_requests):
                if self.check_interruption():
                    return

                # Emituj progress co 10% lub co 5 miniaturek
                if idx % max(1, total_requests // 10) == 0 or idx % 5 == 0:
                    percent = int((idx / total_requests) * 100)
                    self.emit_progress(
                        percent, f"Generowanie miniatur: {idx}/{total_requests}..."
                    )

                try:
                    # Sprawdź w cache z resource protection
                    def get_from_cache():
                        cache = ThumbnailCache.get_instance()
                        return cache.get_thumbnail(path, width, height)

                    cached_pixmap = self.with_thumbnail_cache_lock(get_from_cache)

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
                        self.emit_error(
                            "Nie udało się utworzyć miniatury", path, width, height
                        )
                        continue

                    # Zapisz do cache z resource protection
                    def save_to_cache():
                        cache = ThumbnailCache.get_instance()
                        cache.add_thumbnail(path, width, height, pixmap)

                    self.with_thumbnail_cache_lock(save_to_cache)

                    # Wyemituj sygnał dla każdej miniaturki osobno
                    self.emit_finished(pixmap, path, width, height)
                    processed_count += 1

                except Exception as e:
                    self.emit_error(f"Błąd: {str(e)}", path, width, height)

            # Zakończ cały worker
            self.emit_progress(
                100,
                f"Zakończono generowanie miniatur. "
                f"Sukces: {processed_count}/{total_requests}",
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

    UWAGA: Ta klasa nadal dziedziczy po QObject dla kompatybilności z moveToThread.
    W przyszłości powinna zostać zunifikowana z UnifiedBaseWorker.
    """

    # Bezpośrednie sygnały
    tile_data_ready = pyqtSignal(FilePair)
    tiles_batch_ready = pyqtSignal(list)  # NOWY: sygnał dla batch'y kafelków
    tiles_refresh_needed = pyqtSignal(
        list
    )  # NOWY: sygnał do odświeżenia istniejących kafelków
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    interrupted = pyqtSignal()
    timeout = pyqtSignal(str)  # Nowy sygnał timeout

    def __init__(
        self,
        working_directory: str,
        file_pairs: list[FilePair],
        timeout_seconds: int = 1800,  # NAPRAWKA: 30 minut timeout dla dużych folderów
    ):
        """
        Inicjalizuje worker do przetwarzania danych.

        Args:
            working_directory: Katalog roboczy aplikacji
            file_pairs: Lista par plików do przetworzenia
            timeout_seconds: Timeout dla całej operacji (domyślnie 10 minut)
        """
        super().__init__()
        self.working_directory = working_directory
        self.file_pairs = file_pairs
        self._interrupted = False
        self._last_progress_time = 0
        self._progress_interval_ms = 50  # NAPRAWKA PROGRESS BAR: Zmniejszony odstęp dla płynniejszego progress bara
        self._start_time = None
        self._timeout_seconds = timeout_seconds

    def check_interruption(self) -> bool:
        """
        Sprawdza czy worker został przerwany lub przekroczył timeout.

        Returns:
            True jeśli przerwano lub timeout, False w przeciwnym razie
        """
        if self._interrupted:
            logger.debug("DataProcessingWorker: Operacja przerwana")
            self.interrupted.emit()
            return True

        # Sprawdź timeout
        if self._timeout_seconds and self._start_time:
            elapsed = time.time() - self._start_time
            if elapsed > self._timeout_seconds:
                logger.warning(
                    f"DataProcessingWorker: Przekroczono timeout "
                    f"({self._timeout_seconds}s)"
                )
                self.timeout.emit(
                    f"Przetwarzanie danych przekroczyło limit czasu "
                    f"({self._timeout_seconds}s)"
                )
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
        """NAPRAWKA PROGRESS BAR: Emituje postęp z inteligentnym throttling dla wydajności."""
        # Oblicz realny procent postępu
        percent = int((current / max(total, 1)) * 100)

        if total <= 100:
            # Małe foldery: emituj co 5 kafelków dla płynnego progress bara
            should_emit = current == 1 or current == total or current % 5 == 0
        elif total <= 500:
            # Średnie foldery: emituj co 10 kafelków
            should_emit = current == 1 or current == total or current % 10 == 0
        else:
            # Duże foldery: emituj co 25 kafelków ale minimum co 2% postępu
            progress_step = max(25, total // 50)  # Minimum 25, maksimum co 2%
            should_emit = (
                current == 1 or current == total or current % progress_step == 0
            )

        if should_emit:
            self.emit_progress(percent, message)

    def emit_error(self, message: str, exception: Exception = None):
        """Emituje sygnał błędu z logowaniem."""
        if exception:
            logger.error(f"DataProcessingWorker: {message}", exc_info=True)
        else:
            logger.error(f"DataProcessingWorker: {message}")
        self.error.emit(message)

    def emit_finished(self, result=None):
        """Emituje sygnał zakończenia z logowaniem."""
        if self._start_time:
            elapsed = time.time() - self._start_time
            logger.debug(f"DataProcessingWorker: OK w {elapsed:.2f}s")
        else:
            logger.debug("DataProcessingWorker: OK")
        self.finished.emit(result)

    @pyqtSlot()
    def run(self):
        """Przetwarza dane i emituje sygnały dla kafelków."""
        self._start_time = time.time()

        try:
            # NAPRAWKA PROGRESS BAR: Wymuś progress 0% na samym początku
            self.emit_progress(0, "Rozpoczynanie ładowania...")

            # NAPRAWKA PERFORMANCE: Szybkie ładowanie galerii bez metadanych
            self.emit_progress(
                0, f"Szybkie ładowanie {len(self.file_pairs)} kafelków..."
            )

            # NAPRAWKA PERFORMANCE: POMIŃ metadane podczas ładowania galerii!
            # Metadane będą załadowane asynchronicznie w tle przez osobny worker
            # To drastycznie przyspiesza ładowanie galerii po refaktoryzacji MetadataManager
            logger.debug(
                f"DataProcessingWorker: Pomijam metadane dla szybkiego ładowania {len(self.file_pairs)} par"
            )
            metadata_applied = True  # Symuluj sukces żeby nie blokować UI

            processed_pairs = []
            total_pairs = len(self.file_pairs)

            # NAPRAWKA PERFORMANCE: Dynamiczny batch size w zależności od liczby kafelków
            # Dla małych folderów (do 100 par) - batch_size = 5
            # Dla średnich folderów (100-500 par) - batch_size = 20
            # Dla dużych folderów (500+ par) - batch_size = 50
            if total_pairs <= 100:
                batch_size = 5
            elif total_pairs <= 500:
                batch_size = 20
            else:
                batch_size = 50  # Większy batch dla dużych folderów żeby zmniejszyć liczbę sygnałów
            current_batch = []

            # Tuż przed pętlą - zastosuj metadane do wszystkich par
            self._load_metadata_sync()

            for i, file_pair in enumerate(self.file_pairs):
                if self.check_interruption():
                    return

                # OPTYMALIZACJA: Emituj progress rzadziej (co 25 kafelków)
                if (i + 1) % 25 == 0:
                    self.emit_progress_batched(
                        i + 1,
                        total_pairs,
                        f"Przygotowywanie danych: {i + 1}/{total_pairs}...",
                    )

                # Dodaj do batch'a
                current_batch.append(file_pair)
                processed_pairs.append(file_pair)

                # Wyemituj batch gdy osiągnie odpowiedni rozmiar
                if len(current_batch) >= batch_size:
                    self.tiles_batch_ready.emit(current_batch.copy())
                    current_batch.clear()

            # Wyemituj pozostałe pliki w batch'u
            if current_batch:
                self.tiles_batch_ready.emit(current_batch)

            # NAPRAWKA PROGRESS BAR: NIE ustawiaj na 100% tutaj!
            # Kafelki są tworzone dopiero w _create_tile_widgets_batch
            self.emit_progress(
                90,
                f"Przygotowano {len(processed_pairs)} par plików. Tworzenie kafelków...",
            )
            # NAPRAWKA METADANYCH: Wczytaj metadane PRZED emit_finished żeby UI miało aktualne dane
            self._load_metadata_sync()

            self.emit_finished(processed_pairs)

        except Exception as e:
            self.emit_error(f"Błąd podczas przetwarzania danych: {str(e)}", e)

    def _load_metadata_sync(self):
        """Wczytuje metadane synchronicznie PRZED tworzeniem UI."""
        try:
            from src.logic.metadata_manager import MetadataManager

            metadata_manager = MetadataManager.get_instance(self.working_directory)

            # DEBUG: Sprawdź ile plików ma metadane przed załadowaniem
            files_with_stars_before = sum(
                1 for fp in self.file_pairs if fp.get_stars() > 0
            )
            files_with_colors_before = sum(
                1 for fp in self.file_pairs if fp.get_color_tag()
            )
            logger.debug(
                f"SYNC LOAD BEFORE: {files_with_stars_before} plików z gwiazdkami, "
                f"{files_with_colors_before} z kolorami"
            )

            metadata_applied = metadata_manager.apply_metadata_to_file_pairs(
                self.file_pairs
            )

            # DEBUG: Sprawdź ile plików ma metadane po załadowaniu
            files_with_stars_after = sum(
                1 for fp in self.file_pairs if fp.get_stars() > 0
            )
            files_with_colors_after = sum(
                1 for fp in self.file_pairs if fp.get_color_tag()
            )
            logger.debug(
                f"SYNC LOAD AFTER: {files_with_stars_after} plików z gwiazdkami, "
                f"{files_with_colors_after} z kolorami. Applied: {metadata_applied}"
            )

            # NAPRAWKA: Emituj sygnał odświeżenia kafelków jeśli metadane zostały załadowane
            if metadata_applied and (
                files_with_stars_after > 0 or files_with_colors_after > 0
            ):
                self.tiles_refresh_needed.emit(self.file_pairs)
                logger.debug(
                    "SYNC: Wysłano sygnał odświeżenia kafelków po załadowaniu metadanych"
                )

        except Exception as e:
            logger.error(f"Błąd synchronicznego ładowania metadanych: {e}")

    def _load_metadata_async(self, file_pairs):
        """Asynchronicznie ładuje metadane dla listy par plików."""
        try:
            metadata_manager = MetadataManager.get_instance()
            metadata_manager.apply_metadata_to_file_pairs(file_pairs)
            QTimer.singleShot(0, lambda: self.tiles_batch_ready.emit(file_pairs))
        except Exception as e:
            logger.error(f"Błąd podczas ładowania metadanych: {e}")

    def _save_metadata_async(self, file_pairs):
        """Asynchronicznie zapisuje metadane dla listy par plików."""
        try:
            metadata_manager = MetadataManager.get_instance()
            metadata_manager.save_metadata()
            metadata_manager.force_save()
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania metadanych: {e}")

    def stop(self):
        """Zatrzymuje worker - kompatybilność z main_window."""
        self.interrupt()


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
