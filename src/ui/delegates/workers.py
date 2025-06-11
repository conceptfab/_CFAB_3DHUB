"""
Workers do obsługi zadań w tle.
"""

import logging
import os
import shutil
import time

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPixmap

from src.logic import metadata_manager
from src.models.file_pair import FilePair
from src.ui.delegates.scanner_worker import ScanFolderWorkerQRunnable
from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)


class BaseWorkerSignals(QObject):
    """
    Bazowe sygnały dla wszystkich workerów.
    """

    finished = pyqtSignal(object)  # uniwersalny typ wyniku
    error = pyqtSignal(str)  # komunikat błędu
    progress = pyqtSignal(int, str)  # procent, wiadomość
    interrupted = pyqtSignal()  # sygnał przerwania


class BaseWorker(QRunnable):
    """
    Bazowa klasa dla wszystkich workerów obsługujących zadania w tle.

    Zapewnia wspólną logikę dla:
    - Obsługi przerwań
    - Sygnałów komunikacji z UI
    - Logowania
    - Podstawowej obsługi błędów
    """

    def __init__(self):
        super().__init__()
        self.signals = BaseWorkerSignals()
        self._interrupted = False
        self._worker_name = self.__class__.__name__

    def check_interruption(self) -> bool:
        """
        Sprawdza czy worker został przerwany.

        Returns:
            True jeśli przerwano, False w przeciwnym razie
        """
        if self._interrupted:
            logger.debug(f"{self._worker_name}: Operacja przerwana")
            self.signals.interrupted.emit()
            return True
        return False

    def interrupt(self):
        """Przerywa wykonywanie workera."""
        self._interrupted = True
        logger.debug(f"{self._worker_name}: Otrzymano żądanie przerwania")

    def emit_progress(self, percent: int, message: str):
        """Emituje sygnał postępu z logowaniem."""
        logger.debug(f"{self._worker_name}: Postęp {percent}% - {message}")
        self.signals.progress.emit(percent, message)

    def emit_error(self, message: str, exception: Exception = None):
        """Emituje sygnał błędu z logowaniem."""
        if exception:
            logger.error(f"{self._worker_name}: {message}", exc_info=True)
        else:
            logger.error(f"{self._worker_name}: {message}")
        self.signals.error.emit(message)

    def emit_finished(self, result=None):
        """Emituje sygnał zakończenia z logowaniem."""
        logger.info(f"{self._worker_name}: Zakończono pomyślnie")
        self.signals.finished.emit(result)

    def emit_interrupted(self):
        """Emituje sygnał przerwania z logowaniem."""
        logger.info(f"{self._worker_name}: Operacja przerwana")
        self.signals.interrupted.emit()

    def run(self):
        """
        Główna metoda workera - do implementacji w klasach pochodnych.

        Powinny używać metod check_interruption(), emit_progress(), emit_error(), emit_finished()
        """
        raise NotImplementedError(
            "Metoda run() musi być zaimplementowana w klasie pochodnej"
        )


class UnifiedBaseWorker(QRunnable):
    """
    Zunifikowana klasa bazowa dla wszystkich workerów.

    Dodaje funkcjonalności:
    - Walidacja parametrów wejściowych w konstruktorze
    - Batching sygnałów postępu
    - Rozszerzone logowanie
    """

    def __init__(self):
        super().__init__()
        self.signals = BaseWorkerSignals()
        self._interrupted = False
        self._worker_name = self.__class__.__name__
        self._last_progress_time = 0
        self._progress_interval_ms = 100  # Minimalny odstęp między sygnałami (ms)
        # Walidacja w konstruktorze została przeniesiona do metody run

    def _validate_inputs(self):
        """Override w klasach pochodnych dla walidacji."""
        pass

    def check_interruption(self) -> bool:
        """
        Sprawdza czy worker został przerwany.

        Returns:
            True jeśli przerwano, False w przeciwnym razie
        """
        if self._interrupted:
            logger.debug(f"{self._worker_name}: Operacja przerwana")
            self.signals.interrupted.emit()
            return True
        return False

    def interrupt(self):
        """Przerywa wykonywanie workera."""
        self._interrupted = True
        logger.debug(f"{self._worker_name}: Otrzymano żądanie przerwania")

    def emit_progress(self, percent: int, message: str):
        """Emituje sygnał postępu z logowaniem."""
        logger.debug(f"{self._worker_name}: Postęp {percent}% - {message}")
        self.signals.progress.emit(percent, message)

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
            logger.error(f"{self._worker_name}: {message}", exc_info=True)
        else:
            logger.error(f"{self._worker_name}: {message}")
        self.signals.error.emit(message)

    def emit_finished(self, result=None):
        """Emituje sygnał zakończenia z logowaniem."""
        logger.info(f"{self._worker_name}: Zakończono pomyślnie")
        self.signals.finished.emit(result)

    def emit_interrupted(self):
        """Emituje sygnał przerwania z logowaniem."""
        logger.info(f"{self._worker_name}: Operacja przerwana")
        self.signals.interrupted.emit()

    def run(self):
        """
        Główna metoda workera - do implementacji w klasach pochodnych.

        Powinny używać metod check_interruption(), emit_progress(), emit_error(), emit_finished()
        """
        raise NotImplementedError(
            "Metoda run() musi być zaimplementowana w klasie pochodnej"
        )


class TransactionalWorker(UnifiedBaseWorker):
    """
    Worker z możliwością wykonywania operacji z automatycznym rollbackiem.

    Pozwala na bezpieczne wykonanie sekwencji operacji z gwarancją, że w przypadku
    błędu wszystkie wykonane wcześniej operacje zostaną cofnięte w odwrotnej kolejności.
    """

    def __init__(self):
        super().__init__()
        self._operations_log = []  # Log wykonanych operacji

    def execute_with_rollback(self, operation_func, rollback_func, *args, **kwargs):
        """
        Wykonuje operację z możliwością cofnięcia.

        Args:
            operation_func: Funkcja wykonująca operację
            rollback_func: Funkcja cofająca operację
            *args, **kwargs: Argumenty przekazywane do operation_func

        Returns:
            Wynik działania operation_func

        Raises:
            Exception: Gdy operation_func rzuci wyjątek, po wykonaniu rollbacku
        """
        try:
            result = operation_func(*args, **kwargs)
            self._operations_log.append(
                (operation_func, rollback_func, args, kwargs, result)
            )
            return result
        except Exception as e:
            logger.error(f"Błąd podczas wykonywania operacji: {e}", exc_info=True)
            self._rollback_operations()
            raise e

    def _rollback_operations(self):
        """Cofa wykonane operacje w odwrotnej kolejności."""
        logger.info(f"Rozpoczęcie wycofywania {len(self._operations_log)} operacji")

        for i, (op_func, rollback_func, args, kwargs, result) in enumerate(
            reversed(self._operations_log)
        ):
            try:
                logger.debug(
                    f"Wycofywanie operacji {len(self._operations_log)-i}/{len(self._operations_log)}"
                )
                rollback_func(result, *args, **kwargs)
            except Exception as e:
                logger.error(f"Błąd podczas cofania operacji: {e}", exc_info=True)
                # Kontynuuj próby rollbacku dla pozostałych operacji

        # Wyczyść log po rollbacku
        self._operations_log.clear()
        logger.info("Zakończono wycofywanie operacji")


class CreateFolderWorker(UnifiedBaseWorker):
    """
    Worker do tworzenia folderu w osobnym wątku.
    """

    def __init__(self, parent_directory: str, folder_name: str):
        self.parent_directory = parent_directory
        self.folder_name = folder_name
        super().__init__()

    def _validate_inputs(self):
        """Walidacja parametrów wejściowych."""
        if not self.parent_directory or not isinstance(self.parent_directory, str):
            raise ValueError("Katalog nadrzędny musi być poprawnym ciągiem znaków")

        if not self.folder_name or not isinstance(self.folder_name, str):
            raise ValueError("Nazwa folderu musi być poprawnym ciągiem znaków")

    def run(self):
        """Wykonuje operację tworzenia folderu."""
        try:
            # Normalizacja ścieżek
            from src.utils.path_utils import is_valid_filename, normalize_path

            parent_dir = normalize_path(self.parent_directory)
            if not os.path.isdir(parent_dir):
                self.emit_error(f"Katalog nadrzędny '{parent_dir}' nie istnieje.")
                return

            if not is_valid_filename(self.folder_name):
                self.emit_error(
                    f"Nazwa folderu '{self.folder_name}' jest nieprawidłowa lub pusta."
                )
                return

            if self.check_interruption():
                return

            folder_path = normalize_path(os.path.join(parent_dir, self.folder_name))

            self.emit_progress(0, f"Tworzenie folderu: {folder_path}")

            if self.check_interruption():  # Sprawdzenie przed operacją I/O
                return

            os.makedirs(folder_path, exist_ok=True)

            if self.check_interruption():  # Sprawdzenie po operacji
                # W tym przypadku, jeśli folder został utworzony, nie cofamy tego,
                # ale sygnalizujemy przerwanie.
                return

            logger.info(f"Folder '{folder_path}' został utworzony lub już istniał.")
            self.emit_progress(100, f"Utworzono folder: {folder_path}")
            self.emit_finished(folder_path)

        except OSError as e:
            logger.error(
                f"Nie udało się utworzyć folderu '{self.folder_name}' w '{self.parent_directory}': {e}"
            )
            self.emit_error(f"Błąd tworzenia folderu '{self.folder_name}': {e}")
        except Exception as e:
            logger.error(
                f"Nieoczekiwany błąd podczas tworzenia folderu '{self.folder_name}': {e}",
                exc_info=True,
            )
            self.emit_error(f"Nieoczekiwany błąd tworzenia folderu: {e}")


class RenameFolderWorker(UnifiedBaseWorker):
    """
    Worker do zmiany nazwy folderu w osobnym wątku.
    """

    def __init__(self, folder_path: str, new_folder_name: str):
        self.folder_path = folder_path
        self.new_folder_name = new_folder_name
        super().__init__()

    def _validate_inputs(self):
        """Walidacja parametrów wejściowych."""
        if not self.folder_path or not isinstance(self.folder_path, str):
            raise ValueError("Ścieżka folderu musi być poprawnym ciągiem znaków")

        if not self.new_folder_name or not isinstance(self.new_folder_name, str):
            raise ValueError("Nowa nazwa folderu musi być poprawnym ciągiem znaków")

    def run(self):
        """Wykonuje operację zmiany nazwy folderu."""
        from src.utils.path_utils import is_valid_filename, normalize_path

        try:
            original_path_normalized = normalize_path(self.folder_path)

            self.emit_progress(
                0, f"Rozpoczęto zmianę nazwy folderu: {original_path_normalized}"
            )

            if not os.path.isdir(original_path_normalized):
                self.emit_error(
                    f"Folder '{original_path_normalized}' nie istnieje lub nie jest folderem."
                )
                return

            if not is_valid_filename(self.new_folder_name):
                self.emit_error(
                    f"Nowa nazwa folderu '{self.new_folder_name}' jest nieprawidłowa lub pusta."
                )
                return

            if self.check_interruption():
                return

            parent_dir = os.path.dirname(original_path_normalized)
            new_folder_path_normalized = normalize_path(
                os.path.join(parent_dir, self.new_folder_name)
            )

            if os.path.exists(new_folder_path_normalized):
                self.emit_error(
                    f"Folder o nazwie '{new_folder_path_normalized}' już istnieje."
                )
                return

            self.emit_progress(
                50,
                f"Zmiana nazwy z '{original_path_normalized}' na '{new_folder_path_normalized}'",
            )

            if self.check_interruption():  # Sprawdzenie przed operacją I/O
                return

            os.rename(original_path_normalized, new_folder_path_normalized)

            if self.check_interruption():  # Sprawdzenie po operacji
                # Jeśli operacja została przerwana, ale już wykonana,
                # można rozważać przywrócenie poprzedniej nazwy, ale to komplikuje.
                # Na razie sygnalizujemy przerwanie.
                logger.warning(
                    f"Operacja zmiany nazwy folderu na '{new_folder_path_normalized}' została przerwana po wykonaniu."
                )
                # Mimo przerwania, operacja się udała, więc można też wysłać finished.
                # Lub dedykowany sygnał "finished_but_interrupted".
                # Dla uproszczenia, jeśli doszło do rename, to finished.
                # self.emit_finished(new_folder_path_normalized) # Rozważ to
                return

            logger.info(
                f"Zmieniono nazwę folderu z '{original_path_normalized}' na '{new_folder_path_normalized}'."
            )
            self.emit_progress(100, f"Zmieniono nazwę na: {new_folder_path_normalized}")
            self.emit_finished(new_folder_path_normalized)

        except OSError as e:
            logger.error(
                f"Nie udało się zmienić nazwy folderu '{self.folder_path}' na '{self.new_folder_name}': {e}"
            )
            self.emit_error(f"Błąd zmiany nazwy folderu '{self.folder_path}': {e}")
        except Exception as e:
            logger.error(
                f"Nieoczekiwany błąd podczas zmiany nazwy folderu '{self.folder_path}': {e}",
                exc_info=True,
            )
            self.emit_error(f"Nieoczekiwany błąd zmiany nazwy folderu: {e}")


class DeleteFolderWorker(UnifiedBaseWorker):
    """
    Worker do usuwania folderu w osobnym wątku.
    """

    def __init__(self, folder_path: str, delete_content: bool):
        self.folder_path = folder_path
        self.delete_content = delete_content
        super().__init__()

    def _validate_inputs(self):
        """Walidacja parametrów wejściowych."""
        if not self.folder_path or not isinstance(self.folder_path, str):
            raise ValueError("Ścieżka folderu musi być poprawnym ciągiem znaków")

        if not isinstance(self.delete_content, bool):
            raise ValueError(
                "Parametr delete_content musi być wartością logiczną (bool)"
            )

    def run(self):
        """Wykonuje operację usuwania folderu."""
        from src.utils.path_utils import normalize_path

        try:
            folder_path_normalized = normalize_path(self.folder_path)
            self.emit_progress(
                0, f"Rozpoczęto usuwanie folderu: {folder_path_normalized}"
            )

            if not os.path.exists(folder_path_normalized):
                logger.warning(
                    f"Element '{folder_path_normalized}' nie istnieje, nie można usunąć."
                )
                self.emit_finished(
                    folder_path_normalized
                )  # Uznajemy za sukces, jeśli elementu nie ma
                return

            if not os.path.isdir(folder_path_normalized):
                self.emit_error(
                    f"Ścieżka '{folder_path_normalized}' nie jest folderem."
                )
                return

            if self.check_interruption():
                return

            if self.delete_content:
                self.emit_progress(
                    25, f"Usuwanie zawartości folderu: {folder_path_normalized}"
                )
                # Przerwanie shutil.rmtree jest trudne; sprawdzamy tylko przed
                if self.check_interruption():
                    return
                shutil.rmtree(folder_path_normalized)
                logger.info(
                    f"Folder '{folder_path_normalized}' i jego zawartość zostały usunięte."
                )
                self.emit_progress(
                    100, f"Usunięto folder i zawartość: {folder_path_normalized}"
                )
                self.emit_finished(folder_path_normalized)
            else:
                if not os.listdir(
                    folder_path_normalized
                ):  # Sprawdź czy folder jest pusty
                    if self.check_interruption():
                        return
                    os.rmdir(folder_path_normalized)
                    logger.info(
                        f"Pusty folder '{folder_path_normalized}' został usunięty."
                    )
                    self.emit_progress(
                        100, f"Usunięto pusty folder: {folder_path_normalized}"
                    )
                    self.emit_finished(folder_path_normalized)
                else:
                    logger.error(
                        f"Folder '{folder_path_normalized}' nie jest pusty. Aby usunąć, ustaw delete_content=True."
                    )
                    self.emit_error(
                        f"Folder '{folder_path_normalized}' nie jest pusty."
                    )
                    return  # Zwracamy, bo to błąd użytkownika, a nie systemu

        except OSError as e:
            logger.error(f"Nie udało się usunąć folderu '{self.folder_path}': {e}")
            self.emit_error(f"Błąd usuwania folderu '{self.folder_path}': {e}")
        except Exception as e:
            logger.error(
                f"Nieoczekiwany błąd podczas usuwania folderu '{self.folder_path}': {e}",
                exc_info=True,
            )
            self.emit_error(f"Nieoczekiwany błąd usuwania folderu: {e}")


class ManuallyPairFilesWorker(UnifiedBaseWorker):
    """
    Worker do ręcznego parowania plików archiwum i podglądu w osobnym wątku.
    Może wymagać zmiany nazwy pliku podglądu.
    """

    def __init__(self, archive_path: str, preview_path: str, working_directory: str):
        self.archive_path = archive_path
        self.preview_path = preview_path
        self.working_directory = working_directory
        self._original_preview_path_if_renamed = None  # Do ewentualnego rollbacku
        super().__init__()

    def _validate_inputs(self):
        """Walidacja parametrów wejściowych."""
        if not self.archive_path or not isinstance(self.archive_path, str):
            raise ValueError("Ścieżka pliku archiwum musi być poprawnym ciągiem znaków")

        if not self.preview_path or not isinstance(self.preview_path, str):
            raise ValueError("Ścieżka pliku podglądu musi być poprawnym ciągiem znaków")

        if not self.working_directory or not isinstance(self.working_directory, str):
            raise ValueError("Katalog roboczy musi być poprawnym ciągiem znaków")

    def run(self):
        """Wykonuje operację ręcznego parowania plików."""
        from src.models.file_pair import FilePair
        from src.utils.path_utils import is_valid_filename, normalize_path

        try:
            archive_path_norm = normalize_path(self.archive_path)
            preview_path_norm = normalize_path(self.preview_path)
            working_dir_norm = normalize_path(self.working_directory)

            self.emit_progress(
                0,
                f"Rozpoczęto ręczne parowanie: A='{archive_path_norm}', P='{preview_path_norm}'",
            )

            if not os.path.exists(archive_path_norm):
                self.emit_error(f"Plik archiwum '{archive_path_norm}' nie istnieje.")
                return
            if not os.path.exists(preview_path_norm):
                self.emit_error(f"Plik podglądu '{preview_path_norm}' nie istnieje.")
                return

            if self.check_interruption():
                return

            # Analiza nazw bazowych
            archive_base_name, _ = os.path.splitext(os.path.basename(archive_path_norm))
            preview_base_name, preview_extension = os.path.splitext(
                os.path.basename(preview_path_norm)
            )
            current_preview_path_for_pairing = preview_path_norm
            renamed_preview = False

            # Porównanie nazw bazowych z ignorowaniem wielkości liter
            if archive_base_name.lower() != preview_base_name.lower():
                self.emit_progress(
                    25,
                    f"Nazwy bazowe różne ('{archive_base_name}' vs '{preview_base_name}'). Zmiana nazwy podglądu...",
                )

                new_preview_filename = archive_base_name + preview_extension
                if not is_valid_filename(new_preview_filename):
                    self.emit_error(
                        f"Nowa nazwa pliku podglądu '{new_preview_filename}' jest nieprawidłowa."
                    )
                    return

                new_preview_path = normalize_path(
                    os.path.join(
                        os.path.dirname(preview_path_norm), new_preview_filename
                    )
                )

                # Sprawdzenie istnienia pliku docelowego
                if (
                    os.path.exists(new_preview_path)
                    and new_preview_path.lower() != preview_path_norm.lower()
                ):
                    self.emit_error(
                        f"Plik o nazwie '{new_preview_filename}' już istnieje."
                    )
                    return

                if self.check_interruption():
                    return

                try:
                    # Zmiana nazwy tylko jeśli nowa ścieżka jest inna niż stara
                    if new_preview_path != preview_path_norm:
                        self._original_preview_path_if_renamed = preview_path_norm
                        os.rename(preview_path_norm, new_preview_path)
                        current_preview_path_for_pairing = new_preview_path
                        renamed_preview = True
                        logger.info(
                            f"Zmieniono nazwę pliku podglądu z '{os.path.basename(preview_path_norm)}' na '{new_preview_filename}'"
                        )
                        self.emit_progress(
                            50, f"Zmieniono nazwę podglądu na: {new_preview_filename}"
                        )
                    else:
                        # Nazwy różniły się tylko wielkością liter, system plików case-insensitive
                        logger.debug(
                            f"Plik podglądu '{preview_path_norm}' ma już docelową nazwę. Używam '{new_preview_path}'."
                        )
                        current_preview_path_for_pairing = new_preview_path
                        self.emit_progress(
                            50,
                            "Nazwy plików różnią się tylko wielkością liter. Nazwy nie zmieniono.",
                        )
                except OSError as e_rename:
                    self.emit_error(
                        f"Nie udało się zmienić nazwy pliku podglądu '{preview_path_norm}' na '{new_preview_path}': {e_rename}"
                    )
                    return
            else:
                self.emit_progress(
                    50, "Nazwy bazowe plików zgodne. Pomijanie zmiany nazwy podglądu."
                )

            if self.check_interruption():
                self._rollback_rename_if_needed(
                    current_preview_path_for_pairing, renamed_preview
                )
                return

            # Tworzenie obiektu FilePair
            try:
                self.emit_progress(75, "Tworzenie obiektu FilePair...")
                paired_file = FilePair(
                    archive_path=archive_path_norm,
                    preview_path=current_preview_path_for_pairing,
                    working_directory=working_dir_norm,
                )
                logger.info(
                    f"Pomyślnie ręcznie sparowano: A='{paired_file.get_relative_archive_path()}', P='{paired_file.get_relative_preview_path()}'"
                )
                self.emit_progress(100, "Pomyślnie sparowano pliki.")
                self.emit_finished(paired_file)
            except Exception as e_pair:
                logger.error(f"Błąd tworzenia obiektu FilePair: {e_pair}")
                self._rollback_rename_if_needed(
                    current_preview_path_for_pairing, renamed_preview
                )
                self.emit_error(f"Błąd tworzenia obiektu FilePair: {e_pair}")

        except Exception as e:
            logger.error(
                f"Nieoczekiwany błąd podczas ręcznego parowania plików: {e}",
                exc_info=True,
            )
            # Próba cofnięcia zmiany nazwy w przypadku krytycznego błędu
            try:
                if (
                    self._original_preview_path_if_renamed
                    and "current_preview_path_for_pairing" in locals()
                    and os.path.exists(current_preview_path_for_pairing)
                ):
                    os.rename(
                        current_preview_path_for_pairing,
                        self._original_preview_path_if_renamed,
                    )
                    logger.info(
                        f"Przywrócono oryginalną nazwę podglądu: {self._original_preview_path_if_renamed}"
                    )
            except Exception as e_rollback:
                logger.error(
                    f"Nie udało się przywrócić nazwy podglądu po krytycznym błędzie: {e_rollback}"
                )
            self.emit_error(f"Nieoczekiwany błąd parowania: {e}")

    def _rollback_rename_if_needed(self, current_preview_path: str, was_renamed: bool):
        """Pomocnicza metoda do cofania zmiany nazwy."""
        if was_renamed and self._original_preview_path_if_renamed:
            logger.info(
                f"Próba przywrócenia nazwy podglądu z '{current_preview_path}' na '{self._original_preview_path_if_renamed}'"
            )
            try:
                os.rename(current_preview_path, self._original_preview_path_if_renamed)
                logger.info(
                    f"Przywrócono oryginalną nazwę podglądu: {self._original_preview_path_if_renamed}"
                )
            except OSError as e_rollback:
                logger.error(
                    f"Nie udało się przywrócić oryginalnej nazwy podglądu: {e_rollback}"
                )


class RenameFilePairWorker(TransactionalWorker):
    """
    Worker do zmiany nazwy pary plików.
    """

    def __init__(self, file_pair: FilePair, new_base_name: str, working_directory: str):
        self.file_pair = file_pair
        self.new_base_name = new_base_name
        self.working_directory = working_directory

        # Obliczanie ścieżek źródłowych i docelowych
        self._original_archive_path = file_pair.archive_path
        self._original_preview_path = file_pair.preview_path

        archive_ext = os.path.splitext(self._original_archive_path)[1]
        preview_ext = (
            os.path.splitext(self._original_preview_path)[1]
            if self._original_preview_path
            else ""
        )

        new_archive_name = self.new_base_name + archive_ext
        new_preview_name = (
            self.new_base_name + preview_ext if self._original_preview_path else None
        )

        self._new_archive_path = os.path.join(self.working_directory, new_archive_name)
        self._new_preview_path = (
            os.path.join(self.working_directory, new_preview_name)
            if new_preview_name
            else None
        )

        super().__init__()

        logger.debug(
            f"RenameFilePairWorker initialized for: {file_pair.archive_path} -> {self._new_archive_path} and {file_pair.preview_path} -> {self._new_preview_path}"
        )

    def _validate_inputs(self):
        """Walidacja parametrów wejściowych."""
        if not self.file_pair:
            raise ValueError("Wymagany jest obiekt FilePair")

        if not self.new_base_name or not isinstance(self.new_base_name, str):
            raise ValueError("Nowa nazwa bazowa musi być poprawnym ciągiem znaków")

        if not self.working_directory or not isinstance(self.working_directory, str):
            raise ValueError("Katalog roboczy musi być poprawnym ciągiem znaków")

        # Sprawdzenie poprawności nazwy bazowej
        from src.utils.path_utils import is_valid_filename

        if not is_valid_filename(self.new_base_name):
            raise ValueError(
                f"Nowa nazwa bazowa '{self.new_base_name}' jest nieprawidłowa"
            )

    def _rename_file(self, source_path, target_path):
        """Zmiana nazwy pliku z obsługą transakcji."""
        if source_path != target_path and os.path.exists(source_path):
            os.rename(source_path, target_path)
            return target_path
        return source_path

    def _rollback_rename(self, result_path, original_path, *args, **kwargs):
        """Cofnięcie zmiany nazwy pliku."""
        if (
            result_path != original_path
            and os.path.exists(result_path)
            and not os.path.exists(original_path)
        ):
            os.rename(result_path, original_path)
            logger.info(f"Przywrócono oryginalną nazwę pliku: {original_path}")

    def run(self):
        """Wykonuje operację zmiany nazwy pary plików."""
        logger.info(
            f"Rozpoczęcie zmiany nazwy pary plików: '{self.file_pair.base_name}' na '{self.new_base_name}'"
        )
        self.emit_progress(
            0, f"Zmiana nazwy '{self.file_pair.base_name}' na '{self.new_base_name}'..."
        )

        try:
            # Walidacja plików źródłowych i docelowych
            if not os.path.exists(self._original_archive_path):
                self.emit_error(
                    f"Plik archiwum '{self._original_archive_path}' nie istnieje."
                )
                return

            if self._original_preview_path and not os.path.exists(
                self._original_preview_path
            ):
                self.emit_error(
                    f"Plik podglądu '{self._original_preview_path}' nie istnieje."
                )
                return

            if (
                self._original_archive_path != self._new_archive_path
                and os.path.exists(self._new_archive_path)
            ):
                self.emit_error(
                    f"Docelowy plik archiwum '{self._new_archive_path}' już istnieje."
                )
                return

            if (
                self._original_preview_path
                and self._new_preview_path
                and self._original_preview_path != self._new_preview_path
                and os.path.exists(self._new_preview_path)
            ):
                self.emit_error(
                    f"Docelowy plik podglądu '{self._new_preview_path}' już istnieje."
                )
                return

            if self.check_interruption():
                return

            # Zmiana nazwy pliku archiwum
            if self._original_archive_path != self._new_archive_path:
                logger.debug(
                    f"Zmiana nazwy pliku archiwum z '{self._original_archive_path}' na '{self._new_archive_path}'"
                )
                self.emit_progress(25, f"Zmiana nazwy pliku archiwum...")

                try:
                    self.execute_with_rollback(
                        self._rename_file,
                        self._rollback_rename,
                        self._original_archive_path,
                        self._new_archive_path,
                    )
                    logger.info(
                        f"Zmieniono nazwę pliku archiwum na '{self._new_archive_path}'"
                    )
                    self.emit_progress(
                        50,
                        f"Zmieniono nazwę pliku archiwum na {os.path.basename(self._new_archive_path)}",
                    )
                except Exception as e:
                    self.emit_error(f"Błąd zmiany nazwy archiwum: {e}")
                    return
            else:
                logger.info(
                    f"Nazwa pliku archiwum '{self._original_archive_path}' nie wymaga zmiany."
                )
                self.emit_progress(50, "Nazwa pliku archiwum bez zmian.")

            if self.check_interruption():
                # TransactionalWorker automatycznie wykona rollback przeprowadzonych operacji
                return

            # Zmiana nazwy pliku podglądu (jeśli istnieje)
            if self._original_preview_path and self._new_preview_path:
                if self._original_preview_path != self._new_preview_path:
                    logger.debug(
                        f"Zmiana nazwy pliku podglądu z '{self._original_preview_path}' na '{self._new_preview_path}'"
                    )
                    self.emit_progress(75, f"Zmiana nazwy pliku podglądu...")

                    try:
                        self.execute_with_rollback(
                            self._rename_file,
                            self._rollback_rename,
                            self._original_preview_path,
                            self._new_preview_path,
                        )
                        logger.info(
                            f"Zmieniono nazwę pliku podglądu na '{self._new_preview_path}'"
                        )
                        self.emit_progress(
                            90,
                            f"Zmieniono nazwę pliku podglądu na {os.path.basename(self._new_preview_path)}",
                        )
                    except Exception as e:
                        self.emit_error(f"Błąd zmiany nazwy podglądu: {e}")
                        return
                else:
                    logger.info(
                        f"Nazwa pliku podglądu '{self._original_preview_path}' nie wymaga zmiany."
                    )
                    self.emit_progress(90, "Nazwa pliku podglądu bez zmian.")

            if self.check_interruption():
                # TransactionalWorker automatycznie wykona rollback przeprowadzonych operacji
                return

            # Tworzenie zaktualizowanego obiektu FilePair
            updated_file_pair = FilePair(
                archive_path=self._new_archive_path,
                preview_path=self._new_preview_path,
                working_directory=self.working_directory,
            )

            logger.info(
                f"Pomyślnie zmieniono nazwę pary plików na '{self.new_base_name}'."
            )
            self.emit_progress(100, "Pomyślnie zmieniono nazwę pary plików.")
            self.emit_finished(updated_file_pair)

        except Exception as e:
            logger.error(
                f"Nieoczekiwany błąd podczas zmiany nazwy pary plików: {e}",
                exc_info=True,
            )
            self.emit_error(f"Nieoczekiwany błąd: {e}")


class DeleteFilePairWorker(UnifiedBaseWorker):
    """
    Worker do usuwania pary plików.
    """

    def __init__(self, file_pair: FilePair):
        self.file_pair = file_pair
        super().__init__()
        logger.debug(
            f"DeleteFilePairWorker initialized for: {self.file_pair.archive_path} and {self.file_pair.preview_path}"
        )

    def _validate_inputs(self):
        """Walidacja parametrów wejściowych."""
        if not self.file_pair:
            raise ValueError("Wymagany jest obiekt FilePair")

    def run(self):
        """Wykonuje operację usuwania pary plików."""
        logger.info(f"Rozpoczęcie usuwania pary plików: '{self.file_pair.base_name}'")
        self.emit_progress(0, f"Usuwanie pary plików '{self.file_pair.base_name}'...")

        archive_deleted = False
        preview_deleted = False

        original_archive_path = self.file_pair.archive_path
        original_preview_path = self.file_pair.preview_path

        try:
            # Usuwanie pliku archiwum
            if os.path.exists(original_archive_path):
                logger.debug(
                    f"Próba usunięcia pliku archiwum: '{original_archive_path}'"
                )

                if self.check_interruption():
                    return

                os.remove(original_archive_path)
                archive_deleted = True
                logger.info(f"Usunięto plik archiwum: '{original_archive_path}'")
                self.emit_progress(
                    50,
                    f"Usunięto plik archiwum: {os.path.basename(original_archive_path)}",
                )
            else:
                logger.info(
                    f"Plik archiwum '{original_archive_path}' nie istnieje, pomijanie."
                )
                archive_deleted = True  # Uznajemy za "usunięty" jeśli nie istnieje
                self.emit_progress(
                    50,
                    f"Plik archiwum {os.path.basename(original_archive_path)} nie istniał.",
                )

            if self.check_interruption():
                return

            # Usuwanie pliku podglądu, jeśli istnieje
            if original_preview_path and os.path.exists(original_preview_path):
                logger.debug(
                    f"Próba usunięcia pliku podglądu: '{original_preview_path}'"
                )

                if self.check_interruption():
                    return

                os.remove(original_preview_path)
                preview_deleted = True
                logger.info(f"Usunięto plik podglądu: '{original_preview_path}'")
                self.emit_progress(
                    90,
                    f"Usunięto plik podglądu: {os.path.basename(original_preview_path)}",
                )
            else:
                if original_preview_path:
                    logger.info(
                        f"Plik podglądu '{original_preview_path}' nie istnieje, pomijanie."
                    )
                    preview_deleted = True  # Uznajemy za "usunięty" jeśli nie istnieje
                    self.emit_progress(
                        90,
                        f"Plik podglądu {os.path.basename(original_preview_path)} nie istniał.",
                    )
                else:
                    logger.info("Brak pliku podglądu do usunięcia.")
                    preview_deleted = True
                    self.emit_progress(90, "Brak pliku podglądu do usunięcia.")

            if self.check_interruption():
                return

            logger.info(
                f"Pomyślnie zakończono operację usuwania dla pary '{self.file_pair.base_name}'. Archiwum usunięte: {archive_deleted}, Podgląd usunięty: {preview_deleted}"
            )
            self.emit_progress(
                100, "Pomyślnie usunięto parę plików (lub nie istniały)."
            )
            self.emit_finished(
                {
                    "archive_deleted": archive_deleted,
                    "preview_deleted": preview_deleted,
                    "file_pair_path": self.file_pair.archive_path,
                }
            )

        except OSError as e:
            logger.error(
                f"Błąd OS podczas usuwania pary plików '{self.file_pair.base_name}': {e}",
                exc_info=True,
            )
            self.emit_error(
                f"Błąd usuwania: {e}. Archiwum: {'usunięto' if archive_deleted else 'nie usunięto'}, Podgląd: {'usunięto' if preview_deleted else 'nie usunięto'}"
            )
        except Exception as e:
            logger.error(
                f"Nieoczekiwany błąd podczas usuwania pary plików '{self.file_pair.base_name}': {e}",
                exc_info=True,
            )
            self.emit_error(
                f"Nieoczekiwany błąd: {e}. Archiwum: {'usunięto' if archive_deleted else 'nie usunięto'}, Podgląd: {'usunięto' if preview_deleted else 'nie usunięto'}"
            )


class MoveFilePairWorker(TransactionalWorker):
    """
    Worker do przenoszenia pary plików do nowego katalogu.
    """

    def __init__(self, file_pair: FilePair, new_target_directory: str):
        self.file_pair = file_pair
        self.new_target_directory = normalize_path(new_target_directory)

        self._original_archive_path = self.file_pair.archive_path
        self._original_preview_path = self.file_pair.preview_path

        self._new_archive_path = normalize_path(
            os.path.join(
                self.new_target_directory, os.path.basename(self._original_archive_path)
            )
        )
        self._new_preview_path = None
        if self._original_preview_path:
            self._new_preview_path = normalize_path(
                os.path.join(
                    self.new_target_directory,
                    os.path.basename(self._original_preview_path),
                )
            )

        super().__init__()

        logger.debug(
            f"MoveFilePairWorker initialized for '{self.file_pair.base_name}' to '{self.new_target_directory}'"
        )

    def _validate_inputs(self):
        """Walidacja parametrów wejściowych."""
        if not self.file_pair:
            raise ValueError("Wymagany jest obiekt FilePair")

        if not self.new_target_directory or not isinstance(
            self.new_target_directory, str
        ):
            raise ValueError("Katalog docelowy musi być poprawnym ciągiem znaków")

        if not os.path.isdir(self.new_target_directory):
            raise ValueError(
                f"Katalog docelowy '{self.new_target_directory}' nie istnieje"
            )

    def _move_file(self, source_path, target_path):
        """Przeniesienie pliku z obsługą transakcji."""
        if source_path != target_path and os.path.exists(source_path):
            shutil.move(source_path, target_path)
            return target_path
        return source_path

    def _rollback_move(self, result_path, original_path, *args, **kwargs):
        """Cofnięcie przeniesienia pliku."""
        if (
            result_path != original_path
            and os.path.exists(result_path)
            and not os.path.exists(original_path)
        ):
            shutil.move(result_path, original_path)
            logger.info(f"Przywrócono plik do oryginalnej lokalizacji: {original_path}")

    def run(self):
        """Wykonuje operację przenoszenia pary plików."""
        logger.info(
            f"Rozpoczęcie przenoszenia pary plików '{self.file_pair.base_name}' do '{self.new_target_directory}'"
        )
        self.emit_progress(
            0,
            f"Przenoszenie '{self.file_pair.base_name}' do '{os.path.basename(self.new_target_directory)}'...",
        )

        try:
            # Sprawdzenie istnienia plików źródłowych
            if not os.path.exists(self._original_archive_path):
                self.emit_error(
                    f"Plik archiwum '{self._original_archive_path}' nie istnieje."
                )
                return

            if self._original_preview_path and not os.path.exists(
                self._original_preview_path
            ):
                self.emit_error(
                    f"Plik podglądu '{self._original_preview_path}' nie istnieje."
                )
                return

            # Sprawdzenie kolizji w miejscu docelowym
            if (
                os.path.exists(self._new_archive_path)
                and self._new_archive_path != self._original_archive_path
            ):
                self.emit_error(
                    f"Plik archiwum '{self._new_archive_path}' już istnieje w katalogu docelowym."
                )
                return

            if (
                self._new_preview_path
                and os.path.exists(self._new_preview_path)
                and self._new_preview_path != self._original_preview_path
            ):
                self.emit_error(
                    f"Plik podglądu '{self._new_preview_path}' już istnieje w katalogu docelowym."
                )
                return

            if self.check_interruption():
                return

            # Przeniesienie pliku archiwum
            if self._original_archive_path != self._new_archive_path:
                logger.debug(
                    f"Przenoszenie pliku archiwum z '{self._original_archive_path}' do '{self._new_archive_path}'"
                )
                self.emit_progress(25, f"Przenoszenie pliku archiwum...")

                try:
                    self.execute_with_rollback(
                        self._move_file,
                        self._rollback_move,
                        self._original_archive_path,
                        self._new_archive_path,
                    )
                    logger.info(
                        f"Przeniesiono plik archiwum do '{self._new_archive_path}'"
                    )
                    self.emit_progress(
                        50,
                        f"Przeniesiono plik archiwum: {os.path.basename(self._new_archive_path)}",
                    )
                except Exception as e:
                    self.emit_error(f"Błąd przenoszenia pliku archiwum: {e}")
                    return
            else:
                logger.info(
                    f"Plik archiwum '{self._original_archive_path}' jest już w docelowej lokalizacji."
                )
                self.emit_progress(50, "Plik archiwum bez zmian lokalizacji.")

            if self.check_interruption():
                # TransactionalWorker automatycznie wykona rollback przeprowadzonych operacji
                return

            # Przeniesienie pliku podglądu (jeśli istnieje)
            if self._original_preview_path and self._new_preview_path:
                if self._original_preview_path != self._new_preview_path:
                    logger.debug(
                        f"Przenoszenie pliku podglądu z '{self._original_preview_path}' do '{self._new_preview_path}'"
                    )
                    self.emit_progress(75, f"Przenoszenie pliku podglądu...")

                    try:
                        self.execute_with_rollback(
                            self._move_file,
                            self._rollback_move,
                            self._original_preview_path,
                            self._new_preview_path,
                        )
                        logger.info(
                            f"Przeniesiono plik podglądu do '{self._new_preview_path}'"
                        )
                        self.emit_progress(
                            90,
                            f"Przeniesiono plik podglądu: {os.path.basename(self._new_preview_path)}",
                        )
                    except Exception as e:
                        self.emit_error(f"Błąd przenoszenia pliku podglądu: {e}")
                        return
                else:
                    logger.info(
                        f"Plik podglądu '{self._original_preview_path}' jest już w docelowej lokalizacji."
                    )
                    self.emit_progress(90, "Plik podglądu bez zmian lokalizacji.")
            else:
                logger.info("Brak pliku podglądu do przeniesienia.")
                self.emit_progress(90, "Brak pliku podglądu.")

            if self.check_interruption():
                # TransactionalWorker automatycznie wykona rollback przeprowadzonych operacji
                return

            # Tworzenie zaktualizowanego obiektu FilePair
            updated_file_pair = FilePair(
                archive_path=self._new_archive_path,
                preview_path=self._new_preview_path,
                working_directory=self.new_target_directory,
            )

            logger.info(
                f"Pomyślnie przeniesiono parę plików '{self.file_pair.base_name}' do '{self.new_target_directory}'."
            )
            self.emit_progress(100, "Pomyślnie przeniesiono parę plików.")
            self.emit_finished(updated_file_pair)

        except Exception as e:
            logger.error(
                f"Nieoczekiwany błąd podczas przenoszenia pary plików: {e}",
                exc_info=True,
            )
            self.emit_error(f"Nieoczekiwany błąd: {e}")

    def _rollback(self):
        logger.info(
            f"Rozpoczęcie wycofywania operacji przenoszenia dla '{self.file_pair.base_name}'."
        )
        # Wycofaj przeniesienie pliku podglądu, jeśli został przeniesiony
        if (
            self._preview_moved
            and self._original_preview_path
            and os.path.exists(self._new_preview_path)
            and not os.path.exists(self._original_preview_path)
        ):
            try:
                logger.debug(
                    f"Wycofywanie przeniesienia pliku podglądu z '{self._new_preview_path}' na '{self._original_preview_path}'"
                )
                shutil.move(self._new_preview_path, self._original_preview_path)
                self._preview_moved = False
                logger.info(
                    f"Pomyślnie przywrócono plik podglądu na '{self._original_preview_path}'"
                )
            except OSError as e:
                logger.error(
                    f"Nie udało się przywrócić pliku podglądu '{self._original_preview_path}': {e}",
                    exc_info=True,
                )

        # Wycofaj przeniesienie pliku archiwum, jeśli został przeniesiony
        if (
            self._archive_moved
            and os.path.exists(self._new_archive_path)
            and not os.path.exists(self._original_archive_path)
        ):
            try:
                logger.debug(
                    f"Wycofywanie przeniesienia pliku archiwum z '{self._new_archive_path}' na '{self._original_archive_path}'"
                )
                shutil.move(self._new_archive_path, self._original_archive_path)
                self._archive_moved = False
                logger.info(
                    f"Pomyślnie przywrócono plik archiwum na '{self._original_archive_path}'"
                )
            except OSError as e:
                logger.error(
                    f"Nie udało się przywrócić pliku archiwum '{self._original_archive_path}': {e}",
                    exc_info=True,
                )
        logger.info(
            f"Zakończono wycofywanie operacji przenoszenia dla '{self.file_pair.base_name}'."
        )


class ThumbnailWorkerSignals(QObject):
    """
    Dedykowane sygnały dla ThumbnailGenerationWorker.
    """

    finished = pyqtSignal(QPixmap, str, int, int)  # pixmap, path, width, height
    error = pyqtSignal(str, str, int, int)  # error_message, path, width, height
    progress = pyqtSignal(int, str)  # procent, wiadomość
    interrupted = pyqtSignal()  # sygnał przerwania


class ThumbnailGenerationWorker(UnifiedBaseWorker):
    """
    Worker do asynchronicznego generowania miniaturek z integracją z ThumbnailCache.

    Funkcjonalność:
    - Sprawdza cache przed ładowaniem
    - Ładuje i przetwarza obraz w tle
    - Dodaje wynik do cache
    - Obsługuje błędy gracefully
    """

    def __init__(self, path: str, width: int, height: int):
        super().__init__()
        # Specjalne sygnały dla thumbnail workera
        self.signals = ThumbnailWorkerSignals()
        self.path = path
        self.width = width
        self.height = height

    def _validate_inputs(self):
        """Walidacja parametrów wejściowych."""
        if not self.path:
            raise ValueError("Ścieżka do pliku nie może być pusta")
        if self.width <= 0 or self.height <= 0:
            raise ValueError(
                f"Nieprawidłowe wymiary miniatury: {self.width}x{self.height}"
            )

    def emit_finished(self, pixmap: QPixmap):
        """Emituje sygnał zakończenia z pixmap."""
        logger.debug(f"{self._worker_name}: Zakończono pomyślnie dla {self.path}")
        self.signals.finished.emit(pixmap, self.path, self.width, self.height)

    def emit_error(self, message: str):
        """Emituje sygnał błędu."""
        logger.error(f"{self._worker_name}: {message}")
        self.signals.error.emit(message, self.path, self.width, self.height)

    def run(self):
        """Wykonuje ładowanie miniatury w tle."""
        from PIL import Image

        from src.ui.widgets.thumbnail_cache import ThumbnailCache
        from src.utils.image_utils import (
            create_placeholder_pixmap,
            crop_to_square,
            pillow_image_to_qpixmap,
        )

        logger.debug(
            f"ThumbnailWorker: Rozpoczęcie ładowania {self.path} ({self.width}x{self.height})"
        )

        try:
            # Sprawdź cache ponownie (może inny worker już załadował)
            cache = ThumbnailCache.get_instance()
            cached_pixmap = cache.get_thumbnail(self.path, self.width, self.height)

            if cached_pixmap:
                logger.debug(f"ThumbnailWorker: Cache HIT dla {self.path}")
                self.signals.finished.emit(
                    cached_pixmap, self.path, self.width, self.height
                )
                return

            if self.check_interruption():
                logger.debug(f"ThumbnailWorker: Przerwano ładowanie {self.path}")
                return

            # Sprawdź czy plik istnieje
            if not self.path or not os.path.exists(self.path):
                logger.warning(f"ThumbnailWorker: Plik nie istnieje: {self.path}")
                error_pixmap = cache.get_error_icon(self.width, self.height)
                if error_pixmap:
                    cache.add_thumbnail(
                        self.path, self.width, self.height, error_pixmap
                    )
                    self.emit_finished(error_pixmap)
                else:
                    self.emit_error(f"Plik nie istnieje: {self.path}")
                return

            # Ładuj i przetwarzaj obraz
            try:
                if self.width == self.height:
                    # Kwadratowa miniatura - użyj crop_to_square
                    with Image.open(self.path) as img:
                        if self.check_interruption():
                            return
                        cropped_img = crop_to_square(img, self.width)
                        pixmap = pillow_image_to_qpixmap(cropped_img)
                else:
                    # Niekwadratowa - standardowe skalowanie
                    with Image.open(self.path) as img:
                        if self.check_interruption():
                            return
                        img.thumbnail(
                            (self.width, self.height), Image.Resampling.LANCZOS
                        )
                        pixmap = pillow_image_to_qpixmap(img)

                if pixmap and not pixmap.isNull():
                    # Dodaj do cache i wyślij sygnał
                    cache.add_thumbnail(self.path, self.width, self.height, pixmap)
                    logger.debug(
                        f"ThumbnailWorker: Załadowano i dodano do cache {self.path}"
                    )
                    self.emit_finished(pixmap)
                else:
                    raise ValueError("Wygenerowany QPixmap jest pusty")

            except Exception as img_error:
                logger.error(
                    f"ThumbnailWorker: Błąd przetwarzania obrazu {self.path}: {img_error}"
                )
                # Użyj ikony błędu jako fallback
                error_pixmap = cache.get_error_icon(self.width, self.height)
                if error_pixmap:
                    cache.add_thumbnail(
                        self.path, self.width, self.height, error_pixmap
                    )
                    self.emit_finished(error_pixmap)
                else:
                    self.emit_error(f"Błąd ładowania: {img_error}")

        except Exception as e:
            logger.error(
                f"ThumbnailWorker: Nieoczekiwany błąd dla {self.path}: {e}",
                exc_info=True,
            )
            self.emit_error(f"Nieoczekiwany błąd: {e}")


# Koniec dodawania ThumbnailGenerationWorker


class ScanFolderSignals(QObject):
    """Dedykowane sygnały dla ScanFolderWorker."""

    finished = pyqtSignal(
        list, list, list
    )  # found_pairs, unpaired_archives, unpaired_previews
    error = pyqtSignal(str)  # komunikat błędu
    progress = pyqtSignal(int, str)  # procent, wiadomość
    interrupted = pyqtSignal()  # sygnał przerwania


class ScanFolderWorker(UnifiedBaseWorker):
    """
    Worker do skanowania folderu w osobnym wątku.

    Ta klasa jest kompatybilna wstecz z istniejącym kodem, ale wewnętrznie
    wykorzystuje nową implementację ScanFolderWorkerQRunnable.
    """

    def __init__(self, directory_to_scan=None):
        super().__init__()
        # Specjalne sygnały dla scan folder workera
        self.custom_signals = ScanFolderSignals()
        self.directory_to_scan = directory_to_scan
        self._thread_pool = QThreadPool()
        self._current_worker = None

    def _validate_inputs(self):
        """Walidacja parametrów wejściowych."""
        # Walidacja będzie wykonana w run(), bo directory_to_scan może być ustawiony później    def run(self):
        """
        Wykonuje skanowanie folderu.

        Wewnętrznie używa ScanFolderWorkerQRunnable uruchamianego w QThreadPool.
        """
        if not self.directory_to_scan:
            self.custom_signals.error.emit("Nie określono folderu do skanowania.")
            return

        if self.check_interruption():
            self.custom_signals.interrupted.emit()
            return

        try:
            logging.debug(
                f"Rozpoczynanie skanowania folderu: "
                f"{self.directory_to_scan} w wątku."
            )

            # Tworzymy i konfigurujemy worker
            self._current_worker = ScanFolderWorkerQRunnable(
                directory=self.directory_to_scan,
                max_depth=0,  # Domyślnie skanujemy tylko bieżący folder
                pair_strategy="first_match",
            )

            # Podłączamy sygnały
            self._current_worker.signals.finished.connect(self._on_worker_finished)
            self._current_worker.signals.error.connect(self._on_worker_error)
            self._current_worker.signals.progress.connect(self._on_worker_progress)
            self._current_worker.signals.interrupted.connect(
                self._on_worker_interrupted
            )

            # Jeśli już ustawiono flagę przerwania, przekazujemy ją do workera
            if self._interrupted:
                self._current_worker.interrupt()

            # Uruchamiamy worker w puli wątków
            self._thread_pool.start(self._current_worker)

        except Exception as e:
            logging.error(f"Błąd podczas uruchamiania skanowania: {e}", exc_info=True)
            self.custom_signals.error.emit(
                f"Wystąpił błąd podczas uruchamiania skanowania: {str(e)}"
            )

    def _on_worker_finished(self, found_pairs, unpaired_archives, unpaired_previews):
        """Obsługuje sygnał zakończenia pracy workera."""
        if not self._interrupted:
            self.custom_signals.finished.emit(
                found_pairs, unpaired_archives, unpaired_previews
            )
            self.emit_finished((found_pairs, unpaired_archives, unpaired_previews))

    def _on_worker_error(self, error_message):
        """Obsługuje sygnał błędu z workera."""
        self.custom_signals.error.emit(error_message)
        self.emit_error(error_message)

    def _on_worker_progress(self, percent, message):
        """Obsługuje sygnał postępu z workera."""
        self.custom_signals.progress.emit(percent, message)
        self.emit_progress(percent, message)

    def _on_worker_interrupted(self):
        """Obsługuje sygnał przerwania z workera."""
        self.custom_signals.interrupted.emit()
        self.emit_interrupted()

    def stop(self):
        """Przerywa wykonywanie skanowania."""
        self.interrupt()
        if self._current_worker:
            self._current_worker.interrupt()


class DataProcessingWorker(QObject):
    """
    Worker do przetwarzania danych w tle. Odpowiedzialny za:
    1. Zastosowanie metadanych do par plików (operacja I/O).
    2. Emitowanie sygnałów do tworzenia kafelków w głównym wątku.

    Ta klasa dziedziczy po QObject aby umożliwić przenoszenie do wątku za pomocą moveToThread.
    """

    # Bezpośrednie sygnały
    tile_data_ready = pyqtSignal(FilePair)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    interrupted = pyqtSignal()

    def __init__(self, working_directory: str, file_pairs: list[FilePair]):
        super().__init__()
        self.working_directory = working_directory
        self.file_pairs = file_pairs
        self._interrupted = False
        self._worker_name = self.__class__.__name__
        self._last_progress_time = 0
        self._progress_interval_ms = 100  # Minimalny odstęp między sygnałami (ms)

    def check_interruption(self) -> bool:
        """
        Sprawdza czy worker został przerwany.

        Returns:
            True jeśli przerwano, False w przeciwnym razie
        """
        if self._interrupted:
            logging.debug(f"{self._worker_name}: Operacja przerwana")
            self.interrupted.emit()
            return True
        return False

    def interrupt(self):
        """Przerywa wykonywanie workera."""
        self._interrupted = True
        logging.debug(f"{self._worker_name}: Otrzymano żądanie przerwania")

    def emit_progress(self, percent: int, message: str):
        """Emituje sygnał postępu z logowaniem."""
        self.progress.emit(percent, message)

    def emit_progress_batched(self, current: int, total: int, message: str):
        """Emituje sygnał postępu z limitem częstotliwości."""
        now = time.time() * 1000
        if (
            now - self._last_progress_time >= self._progress_interval_ms
            or current == total
        ):
            percent = int((current / max(total, 1)) * 100)
            self.emit_progress(percent, message)
            self._last_progress_time = now

    def emit_error(self, message: str, exception: Exception = None):
        """Emituje sygnał błędu z logowaniem."""
        if exception:
            logging.error(f"{self._worker_name} Error: {message}", exc_info=True)
        else:
            logging.error(f"{self._worker_name} Error: {message}")
        self.error.emit(message)

    def emit_finished(self, result=None):
        """Emituje sygnał zakończenia z opcjonalnym wynikiem."""
        self.finished.emit(result)

    @pyqtSlot()
    def run(self):
        """Główna metoda workera."""
        try:
            # Walidacja w czasie wykonania
            if not self.working_directory:
                self.emit_error("Katalog roboczy nie może być pusty")
                return

            # 1. Zastosuj metadane (ciężka operacja I/O)
            if self.file_pairs:
                self.emit_progress(10, "Rozpoczynam stosowanie metadanych")
                logging.info("DataProcessingWorker: Rozpoczynam stosowanie metadanych.")
                metadata_manager.apply_metadata_to_file_pairs(
                    self.working_directory, self.file_pairs
                )
                logging.info("DataProcessingWorker: Zakończono stosowanie metadanych.")
                self.emit_progress(50, "Zakończono stosowanie metadanych")

            # 2. Emituj sygnały do tworzenia kafelków
            if self.file_pairs:
                logging.debug(
                    f"DataProcessingWorker: Rozpoczynam przygotowanie "
                    f"{len(self.file_pairs)} kafelków."
                )
                total = len(self.file_pairs)
                for i, file_pair in enumerate(self.file_pairs):
                    if self.check_interruption():
                        return

                    # Emituj sygnały
                    self.tile_data_ready.emit(file_pair)

                    # Aktualizuj postęp, ale nie przy każdej iteracji
                    self.emit_progress_batched(
                        i + 1, total, f"Przetwarzanie kafelków {i+1}/{total}"
                    )
                self.emit_progress(100, f"Przetworzono wszystkie {total} kafelki")
            else:
                logging.debug("DataProcessingWorker: Brak par plików do przetworzenia.")
                self.emit_progress(100, "Brak par plików do przetworzenia")

            # Zakończenie
            self.emit_finished(self.file_pairs)

        except Exception as e:
            logging.error(f"Błąd w DataProcessingWorker: {e}")
            self.emit_error(f"Wystąpił błąd podczas przetwarzania danych: {e}", e)
            self.finished.emit([])  # Zawsze emituj sygnał zakończenia

    def stop(self):
        """Przerywa wykonywanie workera - alias dla interrupt()."""
        self.interrupt()


class BulkDeleteWorker(UnifiedBaseWorker):
    """
    Worker do masowego usuwania par plików.
    Wykonuje operacje usuwania w tle, aby nie blokować głównego wątku UI.
    Używa zoptymalizowanego raportowania postępu dla lepszej wydajności.
    """

    def __init__(self, files_to_delete: list[FilePair]):
        """
        Inicjalizacja workera usuwającego wiele par plików.

        Args:
            files_to_delete: Lista obiektów FilePair do usunięcia
        """
        super().__init__()
        self.files_to_delete = files_to_delete

    def _validate_inputs(self):
        """Walidacja parametrów wejściowych."""
        if self.files_to_delete is None:
            raise ValueError("Lista plików do usunięcia nie może być None")

    def run(self):
        """Wykonuje operację masowego usuwania plików."""
        if not self.files_to_delete:
            self.emit_finished([])
            return

        total_count = len(self.files_to_delete)
        deleted_pairs = []
        failed_pairs = []

        # Początek operacji
        self.emit_progress(0, f"Rozpoczęto usuwanie {total_count} plików")

        for i, file_pair in enumerate(self.files_to_delete):
            # Sprawdź przerwanie
            if self.check_interruption():
                break

            try:
                # Oblicz i zaraportuj postęp - optymalizacja częstotliwości
                self.emit_progress_batched(
                    i + 1,
                    total_count,
                    f"Usuwanie {i+1}/{total_count}: {file_pair.get_base_name()}",
                )

                # Wykonaj operację usunięcia plików
                if os.path.exists(file_pair.archive_path):
                    os.remove(file_pair.archive_path)

                if file_pair.preview_path and os.path.exists(file_pair.preview_path):
                    os.remove(file_pair.preview_path)

                deleted_pairs.append(file_pair)
                logger.debug(f"Usunięto pliki dla {file_pair.get_base_name()}")

            except Exception as e:
                self.emit_error(
                    f"Nie udało się usunąć plików dla {file_pair.get_base_name()}: {str(e)}",
                    e,
                )
                failed_pairs.append(file_pair)

        # Zwróć listę pomyślnie usuniętych par
        self.emit_progress(100, f"Usunięto {len(deleted_pairs)} z {total_count} plików")
        self.emit_finished(deleted_pairs)


class BulkMoveWorker(UnifiedBaseWorker):
    """
    Worker do masowego przenoszenia par plików.
    Wykonuje operacje przenoszenia w tle, aby nie blokować głównego wątku UI.
    Używa zoptymalizowanego raportowania postępu dla lepszej wydajności.
    """

    def __init__(self, files_to_move: list[FilePair], destination_dir: str):
        """
        Inicjalizacja workera przenoszącego wiele par plików.

        Args:
            files_to_move: Lista obiektów FilePair do przeniesienia
            destination_dir: Katalog docelowy
        """
        super().__init__()
        self.files_to_move = files_to_move
        self.destination_dir = destination_dir

    def _validate_inputs(self):
        """Walidacja parametrów wejściowych."""
        if self.files_to_move is None:
            raise ValueError("Lista plików do przeniesienia nie może być None")
        if not self.destination_dir:
            raise ValueError("Katalog docelowy nie może być pusty")
        if not os.path.isdir(self.destination_dir):
            raise ValueError(f"Katalog docelowy '{self.destination_dir}' nie istnieje")

    def run(self):
        """Wykonuje operację masowego przenoszenia plików."""
        if not self.files_to_move:
            self.emit_finished([])
            return

        total_count = len(self.files_to_move)
        moved_pairs = []
        failed_pairs = []

        # Początek operacji
        self.emit_progress(0, f"Rozpoczęto przenoszenie {total_count} plików")

        for i, file_pair in enumerate(self.files_to_move):
            # Sprawdź przerwanie
            if self.check_interruption():
                break

            try:
                # Oblicz i zaraportuj postęp - optymalizacja częstotliwości
                self.emit_progress_batched(
                    i + 1,
                    total_count,
                    f"Przenoszenie {i+1}/{total_count}: {file_pair.get_base_name()}",
                )

                # Wykonaj operację przeniesienia plików
                import shutil

                # Przenieś plik archiwum
                if os.path.exists(file_pair.archive_path):
                    archive_name = os.path.basename(file_pair.archive_path)
                    new_archive_path = os.path.join(self.destination_dir, archive_name)
                    shutil.move(file_pair.archive_path, new_archive_path)

                # Przenieś plik podglądu (jeśli istnieje)
                if file_pair.preview_path and os.path.exists(file_pair.preview_path):
                    preview_name = os.path.basename(file_pair.preview_path)
                    new_preview_path = os.path.join(self.destination_dir, preview_name)
                    shutil.move(file_pair.preview_path, new_preview_path)

                moved_pairs.append(file_pair)
                logger.debug(
                    f"Przeniesiono pliki dla {file_pair.get_base_name()} do {self.destination_dir}"
                )

            except Exception as e:
                self.emit_error(
                    f"Nie udało się przenieść plików dla {file_pair.get_base_name()}: {str(e)}",
                    e,
                )
                failed_pairs.append(file_pair)

        # Zwróć listę pomyślnie przeniesionych par
        self.emit_progress(
            100, f"Przeniesiono {len(moved_pairs)} z {total_count} plików"
        )
        self.emit_finished(moved_pairs)


class SaveMetadataWorker(UnifiedBaseWorker):
    """
    Worker do zapisu metadanych w tle.
    Wykonuje operację zapisu metadanych, aby nie blokować głównego wątku UI.
    """

    def __init__(
        self,
        working_directory: str,
        file_pairs: list[FilePair],
        unpaired_archives: list[str] = None,
        unpaired_previews: list[str] = None,
    ):
        """
        Inicjalizacja workera zapisującego metadane.

        Args:
            working_directory: Katalog roboczy aplikacji
            file_pairs: Lista par plików z metadanymi
            unpaired_archives: Lista niesparowanych plików archiwów
            unpaired_previews: Lista niesparowanych plików podglądu
        """
        super().__init__()
        self.working_directory = working_directory
        self.file_pairs = file_pairs
        self.unpaired_archives = unpaired_archives or []
        self.unpaired_previews = unpaired_previews or []

    def _validate_inputs(self):
        """Walidacja parametrów wejściowych."""
        # Walidacja przeniesiona do metody run
        pass

    def run(self):
        """Wykonuje operację zapisu metadanych."""
        try:
            # Walidacja w czasie wykonania
            if not hasattr(self, "working_directory") or not self.working_directory:
                self.emit_error("Katalog roboczy nie może być pusty")
                return

            logger.debug(
                f"{self._worker_name}: Sprawdzam katalog: {self.working_directory}"
            )

            if not os.path.isdir(self.working_directory):
                self.emit_error(
                    f"Katalog roboczy '{self.working_directory}' nie istnieje"
                )
                return

            if not hasattr(self, "file_pairs") or self.file_pairs is None:
                self.emit_error("Lista par plików nie może być None")
                return

            self.emit_progress(0, "Rozpoczęto zapis metadanych")

            # Sprawdź czy operacja została przerwana przed rozpoczęciem
            if self.check_interruption():
                return

            # Przygotujmy dane do zapisu
            self.emit_progress(30, "Przygotowywanie danych...")

            # Sprawdź czy operacja została przerwana przed zapisem
            if self.check_interruption():
                return

            # Wykonaj zapis metadanych
            self.emit_progress(
                50, f"Zapisywanie metadanych dla {len(self.file_pairs)} elementów..."
            )
            success = metadata_manager.save_metadata(
                self.working_directory,
                self.file_pairs,
                self.unpaired_archives,
                self.unpaired_previews,
            )

            if not success:
                self.emit_error("Nie udało się zapisać metadanych.")
                return

            self.emit_progress(100, "Metadane zapisane pomyślnie")
            self.emit_finished(True)

        except Exception as e:
            self.emit_error(f"Błąd podczas zapisu metadanych: {str(e)}", e)


class WorkerPriority:
    """Priorytety dla workerów."""

    LOW = 0
    NORMAL = 1
    HIGH = 2


class WorkerFactory:
    """
    Centralna fabryka do tworzenia workerów.

    Zapewnia spójny interfejs do tworzenia i konfigurowania różnych typów workerów,
    ukrywając szczegóły implementacyjne. Ułatwia też przyszłe zmiany w implementacji
    workerów bez konieczności modyfikacji kodu klientów.
    """

    @staticmethod
    def create_folder_worker(
        parent_directory: str, folder_name: str
    ) -> UnifiedBaseWorker:
        """Tworzy worker do tworzenia folderu."""
        worker = CreateFolderWorker(parent_directory, folder_name)
        return worker

    @staticmethod
    def create_rename_folder_worker(
        folder_path: str, new_folder_name: str
    ) -> UnifiedBaseWorker:
        """Tworzy worker do zmiany nazwy folderu."""
        worker = RenameFolderWorker(folder_path, new_folder_name)
        return worker

    @staticmethod
    def create_delete_folder_worker(
        folder_path: str, delete_content: bool
    ) -> UnifiedBaseWorker:
        """Tworzy worker do usuwania folderu."""
        worker = DeleteFolderWorker(folder_path, delete_content)
        return worker

    @staticmethod
    def create_manually_pair_files_worker(
        archive_path: str, preview_path: str, working_directory: str
    ) -> UnifiedBaseWorker:
        """Tworzy worker do ręcznego parowania plików."""
        worker = ManuallyPairFilesWorker(archive_path, preview_path, working_directory)
        return worker

    @staticmethod
    def create_rename_file_pair_worker(
        file_pair: FilePair, new_base_name: str, working_directory: str
    ) -> TransactionalWorker:
        """Tworzy worker do zmiany nazwy pary plików."""
        worker = RenameFilePairWorker(file_pair, new_base_name, working_directory)
        return worker

    @staticmethod
    def create_delete_file_pair_worker(file_pair: FilePair) -> UnifiedBaseWorker:
        """Tworzy worker do usuwania pary plików."""
        worker = DeleteFilePairWorker(file_pair)
        return worker

    @staticmethod
    def create_move_file_pair_worker(
        file_pair: FilePair, new_target_directory: str
    ) -> TransactionalWorker:
        """Tworzy worker do przenoszenia pary plików."""
        worker = MoveFilePairWorker(file_pair, new_target_directory)
        return worker

    @staticmethod
    def create_bulk_delete_worker(file_pairs: list[FilePair]) -> UnifiedBaseWorker:
        """Tworzy worker do masowego usuwania plików."""
        worker = BulkDeleteWorker(file_pairs)
        return worker

    @staticmethod
    def create_bulk_move_worker(
        file_pairs: list[FilePair], destination_dir: str
    ) -> UnifiedBaseWorker:
        """Tworzy worker do masowego przenoszenia plików."""

        worker = BulkMoveWorker(file_pairs, destination_dir)
        return worker

    @staticmethod
    def create_thumbnail_worker(
        path: str, width: int, height: int, priority: int = WorkerPriority.NORMAL
    ) -> ThumbnailGenerationWorker:
        """
        Tworzy worker do generowania miniatur.

        Args:
            path: Ścieżka do pliku źródłowego
            width: Szerokość miniatury
            height: Wysokość miniatury
            priority: Priorytet workera (WorkerPriority.LOW/NORMAL/HIGH)

        Returns:
            Skonfigurowany worker
        """
        worker = ThumbnailGenerationWorker(path, width, height)

        # Ustawienie priorytetu QRunnable
        if priority == WorkerPriority.HIGH:
            worker.setAutoDelete(True)
        elif priority == WorkerPriority.LOW:
            worker.setAutoDelete(True)

        return worker @ staticmethod

    def create_save_metadata_worker(
        working_directory: str,
        file_pairs: list[FilePair],
        unpaired_archives: list[str] = None,
        unpaired_previews: list[str] = None,
    ) -> UnifiedBaseWorker:
        """Tworzy worker do zapisu metadanych."""
        # Dodatkowa walidacja wejścia
        if not working_directory:
            raise ValueError("Katalog roboczy nie może być pusty")

        try:
            logger.debug(
                f"WorkerFactory: Tworzenie SaveMetadataWorker z katalogiem {working_directory}"
            )
            worker = SaveMetadataWorker(
                working_directory, file_pairs, unpaired_archives, unpaired_previews
            )

            # Dodatkowe zabezpieczenie - wymuszenie atrybutu
            worker.working_directory = working_directory

            # Wydrukuj debug sprawdzenie
            logger.debug(
                f"WorkerFactory: Utworzono SaveMetadataWorker: wd={working_directory}, hasattr={hasattr(worker, 'working_directory')}, value={getattr(worker, 'working_directory', 'BRAK')}"
            )

            return worker
        except Exception as e:
            logger.error(
                f"WorkerFactory: Błąd tworzenia SaveMetadataWorker: {e}", exc_info=True
            )
            raise
