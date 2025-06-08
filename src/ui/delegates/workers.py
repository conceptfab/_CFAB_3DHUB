"""
Workers do obsługi zadań w tle.
"""

import logging
import os
import shutil

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal

from src.logic import metadata_manager
from src.models.file_pair import FilePair
from src.ui.delegates.scanner_worker import ScanFolderWorkerQRunnable
from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)


class FileOperationSignals(QObject):
    """
    Sygnały dla operacji na plikach wykonywanych w tle.
    """

    finished = pyqtSignal(
        object
    )  # Sygnał emitowany po pomyślnym zakończeniu, zwraca wynik operacji
    error = pyqtSignal(str)  # Sygnał emitowany w przypadku błędu
    progress = pyqtSignal(
        int, str
    )  # Sygnał emitowany do raportowania postępu (procent, wiadomość)
    interrupted = pyqtSignal()  # Sygnał emitowany po przerwaniu operacji


class CreateFolderWorker(QRunnable):
    """
    Worker do tworzenia folderu w osobnym wątku.
    """

    def __init__(self, parent_directory: str, folder_name: str):
        super().__init__()
        self.signals = FileOperationSignals()
        self.parent_directory = parent_directory
        self.folder_name = folder_name
        self._is_interrupted = False

    def run(self):
        """Wykonuje operację tworzenia folderu."""
        try:
            # Walidacja (część walidacji może pozostać w funkcji inicjującej operację)
            # Normalizacja ścieżek
            from src.utils.path_utils import is_valid_filename, normalize_path

            parent_dir = normalize_path(self.parent_directory)
            if not os.path.isdir(parent_dir):
                self.signals.error.emit(
                    f" katalog nadrzędny '{parent_dir}' nie istnieje."
                )
                return

            if not is_valid_filename(self.folder_name):
                self.signals.error.emit(
                    f" nazwa folderu '{self.folder_name}' jest nieprawidłowa lub pusta."
                )
                return

            if self._is_interrupted:
                self.signals.interrupted.emit()
                return

            folder_path = normalize_path(os.path.join(parent_dir, self.folder_name))

            self.signals.progress.emit(0, f"Tworzenie folderu: {folder_path}")

            # Symulacja postępu dla krótkiej operacji
            # W rzeczywistych długich operacjach, postęp byłby emitowany w pętli

            if self._is_interrupted:  # Sprawdzenie przed operacją I/O
                self.signals.interrupted.emit()
                return

            os.makedirs(folder_path, exist_ok=True)

            if (
                self._is_interrupted
            ):  # Sprawdzenie po operacji, na wypadek gdyby przerwanie przyszło w trakcie
                # chociaż dla makedirs to mało prawdopodobne
                # W tym przypadku, jeśli folder został utworzony, nie cofamy tego,
                # ale sygnalizujemy przerwanie.
                self.signals.interrupted.emit()
                # Można by rozważyć usunięcie folderu, jeśli został utworzony,
                # ale to komplikuje logikę. Na razie zakładamy, że przerwanie
                # oznacza "nie kontynuuj, ale to co się stało, to się stało".
                return

            logger.info(f"Folder '{folder_path}' został utworzony lub już istniał.")
            self.signals.progress.emit(100, f"Utworzono folder: {folder_path}")
            self.signals.finished.emit(folder_path)

        except OSError as e:
            logger.error(
                f"Nie udało się utworzyć folderu '{self.folder_name}' w '{self.parent_directory}': {e}"
            )
            self.signals.error.emit(f"Błąd tworzenia folderu '{self.folder_name}': {e}")
        except Exception as e:
            logger.error(
                f"Nieoczekiwany błąd podczas tworzenia folderu '{self.folder_name}': {e}",
                exc_info=True,
            )
            self.signals.error.emit(f"Nieoczekiwany błąd tworzenia folderu: {e}")

    def interrupt(self):
        """Ustawia flagę przerwania dla workera."""
        self._is_interrupted = True
        logger.debug(f"Zażądano przerwania dla CreateFolderWorker ({self.folder_name})")


class RenameFolderWorker(QRunnable):
    """
    Worker do zmiany nazwy folderu w osobnym wątku.
    """

    def __init__(self, folder_path: str, new_folder_name: str):
        super().__init__()
        self.signals = FileOperationSignals()
        self.folder_path = folder_path
        self.new_folder_name = new_folder_name
        self._is_interrupted = False

    def run(self):
        """Wykonuje operację zmiany nazwy folderu."""
        from src.utils.path_utils import is_valid_filename, normalize_path

        try:
            original_path_normalized = normalize_path(self.folder_path)

            self.signals.progress.emit(
                0, f"Rozpoczęto zmianę nazwy folderu: {original_path_normalized}"
            )

            if not os.path.isdir(original_path_normalized):
                self.signals.error.emit(
                    f"Folder '{original_path_normalized}' nie istnieje lub nie jest folderem."
                )
                return

            if not is_valid_filename(self.new_folder_name):
                self.signals.error.emit(
                    f"Nowa nazwa folderu '{self.new_folder_name}' jest nieprawidłowa lub pusta."
                )
                return

            if self._is_interrupted:
                self.signals.interrupted.emit()
                return

            parent_dir = os.path.dirname(original_path_normalized)
            new_folder_path_normalized = normalize_path(
                os.path.join(parent_dir, self.new_folder_name)
            )

            if os.path.exists(new_folder_path_normalized):
                self.signals.error.emit(
                    f"Folder o nazwie '{new_folder_path_normalized}' już istnieje."
                )
                return

            self.signals.progress.emit(
                50,
                f"Zmiana nazwy z '{original_path_normalized}' na '{new_folder_path_normalized}'",
            )

            if self._is_interrupted:  # Sprawdzenie przed operacją I/O
                self.signals.interrupted.emit()
                return

            os.rename(original_path_normalized, new_folder_path_normalized)

            if self._is_interrupted:  # Sprawdzenie po operacji
                # Jeśli operacja została przerwana, ale już wykonana,
                # można rozważać przywrócenie poprzedniej nazwy, ale to komplikuje.
                # Na razie sygnalizujemy przerwanie.
                logger.warning(
                    f"Operacja zmiany nazwy folderu na '{new_folder_path_normalized}' została przerwana po wykonaniu."
                )
                self.signals.interrupted.emit()
                # Mimo przerwania, operacja się udała, więc można też wysłać finished.
                # Lub dedykowany sygnał "finished_but_interrupted".
                # Dla uproszczenia, jeśli doszło do rename, to finished.
                # self.signals.finished.emit(new_folder_path_normalized) # Rozważ to
                return

            logger.info(
                f"Zmieniono nazwę folderu z '{original_path_normalized}' na '{new_folder_path_normalized}'."
            )
            self.signals.progress.emit(
                100, f"Zmieniono nazwę na: {new_folder_path_normalized}"
            )
            self.signals.finished.emit(new_folder_path_normalized)

        except OSError as e:
            logger.error(
                f"Nie udało się zmienić nazwy folderu '{self.folder_path}' na '{self.new_folder_name}': {e}"
            )
            self.signals.error.emit(
                f"Błąd zmiany nazwy folderu '{self.folder_path}': {e}"
            )
        except Exception as e:
            logger.error(
                f"Nieoczekiwany błąd podczas zmiany nazwy folderu '{self.folder_path}': {e}",
                exc_info=True,
            )
            self.signals.error.emit(f"Nieoczekiwany błąd zmiany nazwy folderu: {e}")

    def interrupt(self):
        """Ustawia flagę przerwania dla workera."""
        self._is_interrupted = True
        logger.debug(
            f"Zażądano przerwania dla RenameFolderWorker ({self.folder_path} -> {self.new_folder_name})"
        )


class DeleteFolderWorker(QRunnable):
    """
    Worker do usuwania folderu w osobnym wątku.
    """

    def __init__(self, folder_path: str, delete_content: bool):
        super().__init__()
        self.signals = FileOperationSignals()
        self.folder_path = folder_path
        self.delete_content = delete_content
        self._is_interrupted = False

    def run(self):
        """Wykonuje operację usuwania folderu."""
        import shutil

        from src.utils.path_utils import normalize_path

        try:
            folder_path_normalized = normalize_path(self.folder_path)
            self.signals.progress.emit(
                0, f"Rozpoczęto usuwanie folderu: {folder_path_normalized}"
            )

            if not os.path.exists(
                folder_path_normalized
            ):  # Zmieniono z isdir na exists, aby obsłużyć pliki/linki
                logger.warning(
                    f"Element '{folder_path_normalized}' nie istnieje, nie można usunąć."
                )
                self.signals.finished.emit(
                    folder_path_normalized
                )  # Uznajemy za sukces, jeśli elementu nie ma, zwracamy ścieżkę
                return

            if not os.path.isdir(folder_path_normalized):
                self.signals.error.emit(
                    f"Ścieżka '{folder_path_normalized}' nie jest folderem."
                )
                return

            if self._is_interrupted:
                self.signals.interrupted.emit()
                return

            if self.delete_content:
                self.signals.progress.emit(
                    25, f"Usuwanie zawartości folderu: {folder_path_normalized}"
                )
                # Przerwanie shutil.rmtree jest trudne; sprawdzamy tylko przed
                if self._is_interrupted:
                    self.signals.interrupted.emit()
                    return
                shutil.rmtree(folder_path_normalized)
                logger.info(
                    f"Folder '{folder_path_normalized}' i jego zawartość zostały usunięte."
                )
                self.signals.progress.emit(
                    100, f"Usunięto folder i zawartość: {folder_path_normalized}"
                )
                self.signals.finished.emit(
                    folder_path_normalized
                )  # Zmieniono z True na folder_path_normalized
            else:
                if not os.listdir(
                    folder_path_normalized
                ):  # Sprawdź czy folder jest pusty
                    if self._is_interrupted:
                        self.signals.interrupted.emit()
                        return
                    os.rmdir(folder_path_normalized)
                    logger.info(
                        f"Pusty folder '{folder_path_normalized}' został usunięty."
                    )
                    self.signals.progress.emit(
                        100, f"Usunięto pusty folder: {folder_path_normalized}"
                    )
                    self.signals.finished.emit(
                        folder_path_normalized
                    )  # Zmieniono z True na folder_path_normalized
                else:
                    logger.error(
                        f"Folder '{folder_path_normalized}' nie jest pusty. Aby usunąć, ustaw delete_content=True."
                    )
                    self.signals.error.emit(
                        f"Folder '{folder_path_normalized}' nie jest pusty."
                    )
                    return  # Zwracamy, bo to błąd użytkownika, a nie systemu

        except OSError as e:
            logger.error(f"Nie udało się usunąć folderu '{self.folder_path}': {e}")
            self.signals.error.emit(f"Błąd usuwania folderu '{self.folder_path}': {e}")
        except Exception as e:
            logger.error(
                f"Nieoczekiwany błąd podczas usuwania folderu '{self.folder_path}': {e}",
                exc_info=True,
            )
            self.signals.error.emit(f"Nieoczekiwany błąd usuwania folderu: {e}")

    def interrupt(self):
        """Ustawia flagę przerwania dla workera."""
        self._is_interrupted = True
        logger.debug(f"Zażądano przerwania dla DeleteFolderWorker ({self.folder_path})")


class ManuallyPairFilesWorker(QRunnable):
    """
    Worker do ręcznego parowania plików archiwum i podglądu w osobnym wątku.
    Może wymagać zmiany nazwy pliku podglądu.
    """

    def __init__(self, archive_path: str, preview_path: str, working_directory: str):
        super().__init__()
        self.signals = FileOperationSignals()
        self.archive_path = archive_path
        self.preview_path = preview_path
        self.working_directory = working_directory
        self._is_interrupted = False
        self._original_preview_path_if_renamed: str | None = (
            None  # Do ewentualnego rollbacku
        )

    def run(self):
        """Wykonuje operację ręcznego parowania plików."""
        from src.models.file_pair import FilePair
        from src.utils.path_utils import is_valid_filename, normalize_path

        try:
            archive_path_norm = normalize_path(self.archive_path)
            preview_path_norm = normalize_path(self.preview_path)
            working_dir_norm = normalize_path(self.working_directory)

            self.signals.progress.emit(
                0,
                f"Rozpoczęto ręczne parowanie: A='{archive_path_norm}', P='{preview_path_norm}'",
            )

            if not os.path.exists(archive_path_norm):
                self.signals.error.emit(
                    f"Plik archiwum '{archive_path_norm}' nie istnieje."
                )
                return
            if not os.path.exists(preview_path_norm):
                self.signals.error.emit(
                    f"Plik podglądu '{preview_path_norm}' nie istnieje."
                )
                return

            if self._is_interrupted:
                self.signals.interrupted.emit()
                return

            archive_base_name, _ = os.path.splitext(os.path.basename(archive_path_norm))
            preview_base_name, preview_extension = os.path.splitext(
                os.path.basename(preview_path_norm)
            )

            current_preview_path_for_pairing = preview_path_norm
            renamed_preview = False

            # Porównanie nazw bazowych z ignorowaniem wielkości liter
            if archive_base_name.lower() != preview_base_name.lower():
                self.signals.progress.emit(
                    25,
                    f"Nazwy bazowe różne ('{archive_base_name}' vs '{preview_base_name}'). Zmiana nazwy podglądu...",
                )

                new_preview_filename = archive_base_name + preview_extension
                if not is_valid_filename(new_preview_filename):
                    self.signals.error.emit(
                        f"Nowa nazwa pliku podglądu '{new_preview_filename}' jest nieprawidłowa."
                    )
                    return

                new_preview_path_potential = normalize_path(
                    os.path.join(
                        os.path.dirname(preview_path_norm), new_preview_filename
                    )
                )

                # Sprawdzenie istnienia pliku docelowego z ignorowaniem wielkości liter
                # To jest złożone: os.path.exists może być case-sensitive lub nie, zależnie od OS.
                # Bezpieczniej jest sprawdzić, czy *jakikolwiek* plik o tej nazwie (różniący się tylko wielkością liter)
                # istnieje, jeśli nie jest to ten sam plik, z którym pracujemy.
                target_exists_flag = False
                if os.path.exists(new_preview_path_potential):
                    # Jeśli ścieżka docelowa (po normalizacji) jest inna niż bieżąca ścieżka podglądu (po normalizacji)
                    # to znaczy, że plik o tej nazwie już istnieje i nie jest to ten sam plik (nawet jeśli różni się tylko wielkością liter)
                    if new_preview_path_potential.lower() != preview_path_norm.lower():
                        target_exists_flag = True

                if target_exists_flag:
                    self.signals.error.emit(
                        f"Plik o nazwie '{new_preview_filename}' ('{new_preview_path_potential}') już istnieje."
                    )
                    return

                if self._is_interrupted:
                    self.signals.interrupted.emit()
                    return

                try:
                    # Zmiana nazwy tylko jeśli nowa ścieżka (case-sensitive) jest inna niż stara
                    if new_preview_path_potential != preview_path_norm:
                        os.rename(preview_path_norm, new_preview_path_potential)
                        logger.info(
                            f"Zmieniono nazwę pliku podglądu z '{os.path.basename(preview_path_norm)}' na '{new_preview_filename}'"
                        )
                        self._original_preview_path_if_renamed = (
                            preview_path_norm  # Zapisz dla rollbacku
                        )
                        current_preview_path_for_pairing = new_preview_path_potential
                        renamed_preview = True
                    else:
                        # Nazwy różniły się tylko wielkością liter, a system plików jest case-insensitive
                        # lub plik już ma docelową nazwę. Używamy ścieżki z poprawną wielkością liter.
                        logger.debug(
                            f"Plik podglądu '{preview_path_norm}' ma już docelową nazwę (możliwe różnice wielkości liter). Używam '{new_preview_path_potential}'."
                        )
                        current_preview_path_for_pairing = new_preview_path_potential

                    self.signals.progress.emit(
                        50, f"Zmieniono nazwę podglądu na: {new_preview_filename}"
                    )
                except OSError as e_rename:
                    self.signals.error.emit(
                        f"Nie udało się zmienić nazwy pliku podglądu '{preview_path_norm}' na '{new_preview_path_potential}': {e_rename}"
                    )
                    return
            else:
                self.signals.progress.emit(
                    50, "Nazwy bazowe plików zgodne. Pomijanie zmiany nazwy podglądu."
                )

            if self._is_interrupted:
                if renamed_preview and self._original_preview_path_if_renamed:
                    logger.info(
                        f"Operacja przerwana. Próba przywrócenia nazwy podglądu z '{current_preview_path_for_pairing}' na '{self._original_preview_path_if_renamed}'"
                    )
                    try:
                        os.rename(
                            current_preview_path_for_pairing,
                            self._original_preview_path_if_renamed,
                        )
                        logger.info(
                            f"Przywrócono oryginalną nazwę podglądu: {self._original_preview_path_if_renamed}"
                        )
                    except OSError as e_rollback:
                        logger.error(
                            f"Nie udało się przywrócić oryginalnej nazwy podglądu po przerwaniu: {e_rollback}"
                        )
                        # Mimo to emitujemy interrupted, ale z ostrzeżeniem o stanie plików
                self.signals.interrupted.emit()
                return

            try:
                self.signals.progress.emit(75, "Tworzenie obiektu FilePair...")
                paired_file = FilePair(
                    archive_path=archive_path_norm,
                    preview_path=current_preview_path_for_pairing,
                    working_directory=working_dir_norm,
                )
                logger.info(
                    f"Pomyślnie ręcznie sparowano: A='{paired_file.get_relative_archive_path()}', P='{paired_file.get_relative_preview_path()}'"
                )
                self.signals.progress.emit(100, "Pomyślnie sparowano pliki.")
                self.signals.finished.emit(paired_file)
            except Exception as e_pair:
                logger.error(f"Błąd tworzenia obiektu FilePair: {e_pair}")
                # Jeśli doszło do zmiany nazwy, próbujemy ją cofnąć
                if renamed_preview and self._original_preview_path_if_renamed:
                    logger.info(
                        f"Błąd po zmianie nazwy. Próba przywrócenia nazwy podglądu z '{current_preview_path_for_pairing}' na '{self._original_preview_path_if_renamed}'"
                    )
                    try:
                        os.rename(
                            current_preview_path_for_pairing,
                            self._original_preview_path_if_renamed,
                        )
                        logger.info(
                            f"Przywrócono oryginalną nazwę podglądu: {self._original_preview_path_if_renamed}"
                        )
                    except OSError as e_rollback:
                        logger.error(
                            f"Nie udało się przywrócić oryginalnej nazwy podglądu po błędzie tworzenia pary: {e_rollback}"
                        )
                self.signals.error.emit(f"Błąd tworzenia obiektu FilePair: {e_pair}")

        except Exception as e:
            logger.error(
                f"Nieoczekiwany błąd podczas ręcznego parowania plików: {e}",
                exc_info=True,
            )
            # Tutaj też można by próbować cofnąć zmianę nazwy, jeśli self._original_preview_path_if_renamed jest ustawione
            if self._original_preview_path_if_renamed and os.path.exists(
                current_preview_path_for_pairing
            ):
                try:
                    os.rename(
                        current_preview_path_for_pairing,
                        self._original_preview_path_if_renamed,
                    )
                    logger.info(
                        f"Przywrócono oryginalną nazwę podglądu po nieoczekiwanym błędzie: {self._original_preview_path_if_renamed}"
                    )
                except OSError as e_rollback_critical:
                    logger.error(
                        f"Krytyczny: Nie udało się przywrócić nazwy podglądu po nieoczekiwanym błędzie: {e_rollback_critical}"
                    )
            self.signals.error.emit(f"Nieoczekiwany błąd parowania: {e}")

    def interrupt(self):
        """Ustawia flagę przerwania dla workera."""
        self._is_interrupted = True
        logger.debug(
            f"Zażądano przerwania dla ManuallyPairFilesWorker ({self.archive_path}, {self.preview_path})"
        )


class RenameFilePairWorker(QRunnable):
    def __init__(self, file_pair: FilePair, new_base_name: str, working_directory: str):
        super().__init__()
        self.signals = FileOperationSignals()
        self.file_pair = file_pair
        self.new_base_name = new_base_name
        self.working_directory = working_directory  # Może być redundantne jeśli file_pair ma working_directory

        self._original_archive_path = file_pair.archive_path
        self._original_preview_path = file_pair.preview_path

        archive_ext = os.path.splitext(self._original_archive_path)[1]
        preview_ext = os.path.splitext(self._original_preview_path)[1]

        new_archive_name = self.new_base_name + archive_ext
        new_preview_name = self.new_base_name + preview_ext

        self._new_archive_path = os.path.join(self.working_directory, new_archive_name)
        self._new_preview_path = os.path.join(self.working_directory, new_preview_name)

        self._interrupted = False
        self._archive_renamed = False
        self._preview_renamed = False
        logger.debug(
            f"RenameFilePairWorker initialized for: {file_pair.archive_path} -> {self._new_archive_path} and {file_pair.preview_path} -> {self._new_preview_path}"
        )

    def run(self):
        logger.info(
            f"Rozpoczęcie zmiany nazwy pary plików: '{self.file_pair.base_name}' na '{self.new_base_name}'"
        )
        self.signals.progress.emit(
            0, f"Zmiana nazwy '{self.file_pair.base_name}' na '{self.new_base_name}'..."
        )

        try:
            # Walidacja
            if not os.path.exists(self._original_archive_path):
                self.signals.error.emit(
                    f"Plik archiwum '{self._original_archive_path}' nie istnieje."
                )
                logger.error(
                    f"Plik archiwum '{self._original_archive_path}' nie istnieje."
                )
                return

            if not os.path.exists(self._original_preview_path):
                self.signals.error.emit(
                    f"Plik podglądu '{self._original_preview_path}' nie istnieje."
                )
                logger.error(
                    f"Plik podglądu '{self._original_preview_path}' nie istnieje."
                )
                return

            if (
                self._original_archive_path != self._new_archive_path
                and os.path.exists(self._new_archive_path)
            ):
                self.signals.error.emit(
                    f"Docelowy plik archiwum '{self._new_archive_path}' już istnieje."
                )
                logger.error(
                    f"Docelowy plik archiwum '{self._new_archive_path}' już istnieje."
                )
                return

            if (
                self._original_preview_path != self._new_preview_path
                and os.path.exists(self._new_preview_path)
            ):
                self.signals.error.emit(
                    f"Docelowy plik podglądu '{self._new_preview_path}' już istnieje."
                )
                logger.error(
                    f"Docelowy plik podglądu '{self._new_preview_path}' już istnieje."
                )
                return

            if self._interrupted:
                logger.info(
                    "Przerwanie operacji zmiany nazwy pary plików przed rozpoczęciem."
                )
                self.signals.interrupted.emit()
                return

            # Zmiana nazwy pliku archiwum
            if self._original_archive_path != self._new_archive_path:
                logger.debug(
                    f"Próba zmiany nazwy pliku archiwum z '{self._original_archive_path}' na '{self._new_archive_path}'"
                )
                os.rename(self._original_archive_path, self._new_archive_path)
                self._archive_renamed = True
                logger.info(
                    f"Zmieniono nazwę pliku archiwum na '{self._new_archive_path}'"
                )
                self.signals.progress.emit(
                    50,
                    f"Zmieniono nazwę pliku archiwum na {os.path.basename(self._new_archive_path)}",
                )
            else:
                logger.info(
                    f"Nazwa pliku archiwum '{self._original_archive_path}' nie wymaga zmiany."
                )
                self.signals.progress.emit(50, "Nazwa pliku archiwum bez zmian.")

            if self._interrupted:
                logger.info("Przerwanie operacji po zmianie nazwy pliku archiwum.")
                self._rollback()
                self.signals.interrupted.emit()
                return

            # Zmiana nazwy pliku podglądu
            if self._original_preview_path != self._new_preview_path:
                logger.debug(
                    f"Próba zmiany nazwy pliku podglądu z '{self._original_preview_path}' na '{self._new_preview_path}'"
                )
                os.rename(self._original_preview_path, self._new_preview_path)
                self._preview_renamed = True
                logger.info(
                    f"Zmieniono nazwę pliku podglądu na '{self._new_preview_path}'"
                )
                self.signals.progress.emit(
                    90,
                    f"Zmieniono nazwę pliku podglądu na {os.path.basename(self._new_preview_path)}",
                )
            else:
                logger.info(
                    f"Nazwa pliku podglądu '{self._original_preview_path}' nie wymaga zmiany."
                )
                self.signals.progress.emit(90, "Nazwa pliku podglądu bez zmian.")

            if self._interrupted:
                logger.info("Przerwanie operacji po zmianie nazwy pliku podglądu.")
                self._rollback()
                self.signals.interrupted.emit()
                return

            updated_file_pair = FilePair(
                archive_path=self._new_archive_path,
                preview_path=self._new_preview_path,
                working_directory=self.working_directory,
            )
            logger.info(
                f"Pomyślnie zmieniono nazwę pary plików na '{self.new_base_name}'. Nowa para: {updated_file_pair}"
            )
            self.signals.progress.emit(100, "Pomyślnie zmieniono nazwę pary plików.")
            self.signals.finished.emit(updated_file_pair)

        except OSError as e:
            logger.error(
                f"Błąd OS podczas zmiany nazwy pary plików: {e}", exc_info=True
            )
            self._rollback()
            self.signals.error.emit(f"Błąd zmiany nazwy: {e}")
        except Exception as e:
            logger.error(
                f"Nieoczekiwany błąd podczas zmiany nazwy pary plików: {e}",
                exc_info=True,
            )
            self._rollback()
            self.signals.error.emit(f"Nieoczekiwany błąd: {e}")

    def _rollback(self):
        logger.info("Rozpoczęcie wycofywania zmian nazw plików.")
        if (
            self._archive_renamed
            and os.path.exists(self._new_archive_path)
            and not os.path.exists(self._original_archive_path)
        ):
            try:
                logger.debug(
                    f"Wycofywanie zmiany nazwy pliku archiwum z '{self._new_archive_path}' na '{self._original_archive_path}'"
                )
                os.rename(self._new_archive_path, self._original_archive_path)
                self._archive_renamed = False
                logger.info(
                    f"Pomyślnie przywrócono nazwę pliku archiwum na '{self._original_archive_path}'"
                )
            except OSError as e:
                logger.error(
                    f"Nie udało się przywrócić nazwy pliku archiwum '{self._original_archive_path}': {e}",
                    exc_info=True,
                )

        if (
            self._preview_renamed
            and os.path.exists(self._new_preview_path)
            and not os.path.exists(self._original_preview_path)
        ):
            try:
                logger.debug(
                    f"Wycofywanie zmiany nazwy pliku podglądu z '{self._new_preview_path}' na '{self._original_preview_path}'"
                )
                os.rename(self._new_preview_path, self._original_preview_path)
                self._preview_renamed = False
                logger.info(
                    f"Pomyślnie przywrócono nazwę pliku podglądu na '{self._original_preview_path}'"
                )
            except OSError as e:
                logger.error(
                    f"Nie udało się przywrócić nazwy pliku podglądu '{self._original_preview_path}': {e}",
                    exc_info=True,
                )
        logger.info("Zakończono wycofywanie zmian nazw plików.")

    def interrupt(self):
        logger.info(
            f"RenameFilePairWorker: Otrzymano żądanie przerwania dla pary '{self.file_pair.base_name}'."
        )
        self._interrupted = True


class DeleteFilePairWorker(QRunnable):
    def __init__(self, file_pair: FilePair):
        super().__init__()
        self.signals = FileOperationSignals()
        self.file_pair = file_pair
        self._interrupted = False
        logger.debug(
            f"DeleteFilePairWorker initialized for: {self.file_pair.archive_path} and {self.file_pair.preview_path}"
        )

    def run(self):
        logger.info(f"Rozpoczęcie usuwania pary plików: '{self.file_pair.base_name}'")
        self.signals.progress.emit(
            0, f"Usuwanie pary plików '{self.file_pair.base_name}'..."
        )

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
                if self._interrupted:
                    logger.info("Przerwano operację przed usunięciem pliku archiwum.")
                    self.signals.interrupted.emit()
                    return
                os.remove(original_archive_path)
                archive_deleted = True
                logger.info(f"Usunięto plik archiwum: '{original_archive_path}'")
                self.signals.progress.emit(
                    50,
                    f"Usunięto plik archiwum: {os.path.basename(original_archive_path)}",
                )
            else:
                logger.info(
                    f"Plik archiwum '{original_archive_path}' nie istnieje, pomijanie."
                )
                archive_deleted = True  # Uznajemy za "usunięty" jeśli nie istnieje
                self.signals.progress.emit(
                    50,
                    f"Plik archiwum {os.path.basename(original_archive_path)} nie istniał.",
                )

            if self._interrupted:
                logger.info(
                    "Przerwano operację po usunięciu pliku archiwum (lub stwierdzeniu jego braku)."
                )
                # W tym przypadku nie ma rollbacku dla usunięcia.
                self.signals.interrupted.emit()
                return

            # Usuwanie pliku podglądu
            if os.path.exists(original_preview_path):
                logger.debug(
                    f"Próba usunięcia pliku podglądu: '{original_preview_path}'"
                )
                if (
                    self._interrupted
                ):  # Dodatkowe sprawdzenie, chociaż poprzednie powinno wystarczyć
                    logger.info("Przerwano operację przed usunięciem pliku podglądu.")
                    self.signals.interrupted.emit()
                    return
                os.remove(original_preview_path)
                preview_deleted = True
                logger.info(f"Usunięto plik podglądu: '{original_preview_path}'")
                self.signals.progress.emit(
                    90,
                    f"Usunięto plik podglądu: {os.path.basename(original_preview_path)}",
                )
            else:
                logger.info(
                    f"Plik podglądu '{original_preview_path}' nie istnieje, pomijanie."
                )
                preview_deleted = True  # Uznajemy za "usunięty" jeśli nie istnieje
                self.signals.progress.emit(
                    90,
                    f"Plik podglądu {os.path.basename(original_preview_path)} nie istniał.",
                )

            if self._interrupted:  # Ostateczne sprawdzenie
                logger.info("Przerwano operację po przetworzeniu obu plików.")
                self.signals.interrupted.emit()
                return

            logger.info(
                f"Pomyślnie zakończono operację usuwania dla pary '{self.file_pair.base_name}'. Archiwum usunięte: {archive_deleted}, Podgląd usunięty: {preview_deleted}"
            )
            self.signals.progress.emit(
                100, "Pomyślnie usunięto parę plików (lub nie istniały)."
            )
            self.signals.finished.emit(
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
            # Zwracamy stan usunięcia, aby UI wiedziało co się stało
            self.signals.error.emit(
                f"Błąd usuwania plików: {e}. Archiwum: {'usunięto' if archive_deleted else 'nie usunięto'}, Podgląd: {'usunięto' if preview_deleted else 'nie usunięto'}"
            )
        except Exception as e:
            logger.error(
                f"Nieoczekiwany błąd podczas usuwania pary plików '{self.file_pair.base_name}': {e}",
                exc_info=True,
            )
            self.signals.error.emit(
                f"Nieoczekiwany błąd: {e}. Archiwum: {'usunięto' if archive_deleted else 'nie usunięto'}, Podgląd: {'usunięto' if preview_deleted else 'nie usunięto'}"
            )

    def interrupt(self):
        logger.info(
            f"DeleteFilePairWorker: Otrzymano żądanie przerwania dla pary '{self.file_pair.base_name}'."
        )
        self._interrupted = True


class MoveFilePairWorker(QRunnable):
    def __init__(self, file_pair: FilePair, new_target_directory: str):
        super().__init__()
        self.signals = FileOperationSignals()
        self.file_pair = file_pair
        self.new_target_directory = normalize_path(new_target_directory)
        self._interrupted = False

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

        self._archive_moved = False
        self._preview_moved = False
        logger.debug(
            f"MoveFilePairWorker initialized for '{self.file_pair.base_name}' to '{self.new_target_directory}'"
        )

    def run(self):
        logger.info(
            f"Rozpoczęcie przenoszenia pary plików '{self.file_pair.base_name}' do '{self.new_target_directory}'"
        )
        self.signals.progress.emit(
            0,
            f"Przenoszenie '{self.file_pair.base_name}' do '{os.path.basename(self.new_target_directory)}'...",
        )

        try:
            if not os.path.isdir(self.new_target_directory):
                self.signals.error.emit(
                    f"Katalog docelowy '{self.new_target_directory}' nie istnieje lub nie jest katalogiem."
                )
                logger.error(
                    f"Katalog docelowy '{self.new_target_directory}' nie istnieje."
                )
                return

            # Sprawdzenie istnienia plików źródłowych
            if not os.path.exists(self._original_archive_path):
                self.signals.error.emit(
                    f"Plik archiwum '{self._original_archive_path}' nie istnieje."
                )
                logger.error(
                    f"Plik archiwum '{self._original_archive_path}' nie istnieje."
                )
                return
            if self._original_preview_path and not os.path.exists(
                self._original_preview_path
            ):
                self.signals.error.emit(
                    f"Plik podglądu '{self._original_preview_path}' nie istnieje."
                )
                logger.error(
                    f"Plik podglądu '{self._original_preview_path}' nie istnieje."
                )
                # Kontynuujemy, jeśli tylko podgląd nie istnieje? Czy to błąd krytyczny?
                # Na razie traktujemy jako błąd i przerywamy.
                return

            # Sprawdzenie kolizji w miejscu docelowym
            if (
                os.path.exists(self._new_archive_path)
                and self._new_archive_path != self._original_archive_path
            ):
                self.signals.error.emit(
                    f"Plik archiwum '{self._new_archive_path}' już istnieje w katalogu docelowym."
                )
                logger.error(
                    f"Plik archiwum '{self._new_archive_path}' już istnieje w katalogu docelowym."
                )
                return
            if (
                self._new_preview_path
                and os.path.exists(self._new_preview_path)
                and self._new_preview_path != self._original_preview_path
            ):
                self.signals.error.emit(
                    f"Plik podglądu '{self._new_preview_path}' już istnieje w katalogu docelowym."
                )
                logger.error(
                    f"Plik podglądu '{self._new_preview_path}' już istnieje w katalogu docelowym."
                )
                return

            if self._interrupted:
                logger.info(
                    "Przerwanie operacji przenoszenia pary plików przed rozpoczęciem."
                )
                self.signals.interrupted.emit()
                return

            # Przeniesienie pliku archiwum
            if self._original_archive_path != self._new_archive_path:
                logger.debug(
                    f"Próba przeniesienia pliku archiwum z '{self._original_archive_path}' na '{self._new_archive_path}'"
                )
                shutil.move(self._original_archive_path, self._new_archive_path)
                self._archive_moved = True
                logger.info(f"Przeniesiono plik archiwum na '{self._new_archive_path}'")
                self.signals.progress.emit(
                    50,
                    f"Przeniesiono plik archiwum: {os.path.basename(self._new_archive_path)}",
                )
            else:
                logger.info(
                    f"Plik archiwum '{self._original_archive_path}' jest już w docelowej lokalizacji."
                )
                self.signals.progress.emit(50, "Plik archiwum bez zmian lokalizacji.")

            if self._interrupted:
                logger.info("Przerwanie operacji po przeniesieniu pliku archiwum.")
                self._rollback()
                self.signals.interrupted.emit()
                return

            # Przeniesienie pliku podglądu
            if (
                self._original_preview_path
                and self._new_preview_path
                and self._original_preview_path != self._new_preview_path
            ):
                logger.debug(
                    f"Próba przeniesienia pliku podglądu z '{self._original_preview_path}' na '{self._new_preview_path}'"
                )
                shutil.move(self._original_preview_path, self._new_preview_path)
                self._preview_moved = True
                logger.info(f"Przeniesiono plik podglądu na '{self._new_preview_path}'")
                self.signals.progress.emit(
                    90,
                    f"Przeniesiono plik podglądu: {os.path.basename(self._new_preview_path)}",
                )
            elif self._original_preview_path:
                logger.info(
                    f"Plik podglądu '{self._original_preview_path}' jest już w docelowej lokalizacji lub nie wymaga przenoszenia."
                )
                self.signals.progress.emit(90, "Plik podglądu bez zmian lokalizacji.")
            else:
                logger.info("Brak pliku podglądu do przeniesienia.")
                self.signals.progress.emit(90, "Brak pliku podglądu.")

            if self._interrupted:
                logger.info("Przerwanie operacji po przeniesieniu pliku podglądu.")
                self._rollback()
                self.signals.interrupted.emit()
                return

            updated_file_pair = FilePair(
                archive_path=self._new_archive_path,
                preview_path=(
                    self._new_preview_path if self._original_preview_path else None
                ),  # Użyj None jeśli oryginał był None
                working_directory=self.new_target_directory,  # Aktualizujemy working_directory na katalog docelowy
            )
            logger.info(
                f"Pomyślnie przeniesiono parę plików '{self.file_pair.base_name}' do '{self.new_target_directory}'. Nowa para: {updated_file_pair}"
            )
            self.signals.progress.emit(100, "Pomyślnie przeniesiono parę plików.")
            self.signals.finished.emit(updated_file_pair)

        except OSError as e:
            logger.error(
                f"Błąd OS podczas przenoszenia pary plików '{self.file_pair.base_name}': {e}",
                exc_info=True,
            )
            self._rollback()
            self.signals.error.emit(f"Błąd przenoszenia: {e}")
        except Exception as e:
            logger.error(
                f"Nieoczekiwany błąd podczas przenoszenia pary plików '{self.file_pair.base_name}': {e}",
                exc_info=True,
            )
            self._rollback()
            self.signals.error.emit(f"Nieoczekiwany błąd: {e}")

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

    def interrupt(self):
        logger.info(
            f"MoveFilePairWorker: Otrzymano żądanie przerwania dla pary '{self.file_pair.base_name}' do '{self.new_target_directory}'."
        )
        self._interrupted = True


# Koniec dodawania MoveFilePairWorker


class ScanFolderWorker(QObject):
    """
    Worker do skanowania folderu w osobnym wątku.

    Ta klasa jest kompatybilna wstecz z istniejącym kodem, ale wewnętrznie
    wykorzystuje nową implementację ScanFolderWorkerQRunnable.
    """

    # Sygnały emitowane przez worker
    finished = pyqtSignal(
        list, list, list
    )  # found_pairs, unpaired_archives, unpaired_previews
    error = pyqtSignal(str)  # komunikat błędu
    progress = pyqtSignal(int, str)  # procent, wiadomość
    interrupted = pyqtSignal()  # sygnał przerwania

    def __init__(self, parent=None):
        super().__init__(parent)
        self.directory_to_scan = None
        self._should_stop = False
        self._thread_pool = QThreadPool()
        self._current_worker = None

    def run(self):
        """
        Wykonuje skanowanie folderu.

        Wewnętrznie używa ScanFolderWorkerQRunnable uruchamianego w QThreadPool.
        """
        if not self.directory_to_scan:
            self.error.emit("Nie określono folderu do skanowania.")
            return

        if self._should_stop:
            self.interrupted.emit()
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
            if self._should_stop:
                self._current_worker.interrupt()

            # Uruchamiamy worker w puli wątków
            self._thread_pool.start(self._current_worker)

        except Exception as e:
            logging.error(f"Błąd podczas uruchamiania skanowania: {e}", exc_info=True)
            self.error.emit(f"Wystąpił błąd podczas uruchamiania skanowania: {str(e)}")

    def _on_worker_finished(self, found_pairs, unpaired_archives, unpaired_previews):
        """Obsługuje sygnał zakończenia pracy workera."""
        if not self._should_stop:
            self.finished.emit(found_pairs, unpaired_archives, unpaired_previews)

    def _on_worker_error(self, error_message):
        """Obsługuje sygnał błędu z workera."""
        self.error.emit(error_message)

    def _on_worker_progress(self, percent, message):
        """Obsługuje sygnał postępu z workera."""
        self.progress.emit(percent, message)

    def _on_worker_interrupted(self):
        """Obsługuje sygnał przerwania z workera."""
        self.interrupted.emit()

    def stop(self):
        """Przerywa wykonywanie skanowania."""
        self._should_stop = True
        if self._current_worker:
            self._current_worker.interrupt()


class DataProcessingWorker(QObject):
    """
    Worker do przetwarzania danych w tle. Odpowiedzialny za:
    1. Zastosowanie metadanych do par plików (operacja I/O).
    2. Emitowanie sygnałów do tworzenia kafelków w głównym wątku.
    """

    tile_data_ready = pyqtSignal(FilePair)
    finished = pyqtSignal()

    def __init__(self, working_directory: str, file_pairs: list[FilePair], parent=None):
        super().__init__(parent)
        self.working_directory = working_directory
        self.file_pairs = file_pairs

    def run(self):
        """Główna metoda workera."""
        try:
            # 1. Zastosuj metadane (ciężka operacja I/O)
            if self.file_pairs:
                logging.info("DataProcessingWorker: Rozpoczynam stosowanie metadanych.")
                metadata_manager.apply_metadata_to_file_pairs(
                    self.working_directory, self.file_pairs
                )
                logging.info("DataProcessingWorker: Zakończono stosowanie metadanych.")

            # 2. Emituj sygnały do tworzenia kafelków
            if self.file_pairs:
                logging.debug(
                    f"DataProcessingWorker: Rozpoczynam przygotowanie "
                    f"{len(self.file_pairs)} kafelków."
                )
                for file_pair in self.file_pairs:
                    self.tile_data_ready.emit(file_pair)
            else:
                logging.debug("DataProcessingWorker: Brak par plików do przetworzenia.")

        except Exception as e:
            logging.error(f"Błąd w DataProcessingWorker: {e}")
        finally:
            self.finished.emit()
