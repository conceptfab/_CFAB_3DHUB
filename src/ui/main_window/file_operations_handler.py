"""
FileOperationsHandler - obsługa operacji na plikach.
🚀 ETAP 6 REFAKTORYZACJI: Wydzielenie operacji na plikach z main_window.py
"""

import logging
import os
import subprocess

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMenu, QWidget

from src.models.file_pair import FilePair
from src.ui.delegates.workers.bulk_workers import BulkMoveFilesWorker


class FileOperationsHandler:
    """
    Manager odpowiedzialny za obsługę operacji na plikach.
    Obsługuje otwieranie archiwów, menu kontekstowe i drag & drop.
    """

    def __init__(self, main_window):
        """
        Inicjalizuje FileOperationsHandler.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def open_archive(self, file_pair: FilePair):
        """
        Otwiera archiwum w domyślnej aplikacji systemu.

        Args:
            file_pair: Para plików z archiwum do otwarcia
        """
        archive_path = file_pair.archive_path
        if not archive_path or not os.path.exists(archive_path):
            self.main_window.dialog_manager.show_error_message(
                "Błąd", "Plik archiwum nie istnieje lub ścieżka jest nieprawidłowa."
            )
            return

        try:
            # Użyj subprocess.run zamiast os.startfile dla lepszej kontroli
            if os.name == "nt":  # Windows
                subprocess.run(["start", "", archive_path], shell=True, check=True)
            elif os.name == "posix":  # macOS/Linux
                subprocess.run(
                    [
                        "open" if os.uname().sysname == "Darwin" else "xdg-open",
                        archive_path,
                    ],
                    check=True,
                )

            self.logger.info(f"Otwarto archiwum: {archive_path}")

        except subprocess.CalledProcessError as e:
            error_message = f"Nie udało się otworzyć archiwum: {e}"
            self.logger.error(error_message)
            self.main_window.dialog_manager.show_error_message(
                "Błąd Otwierania", error_message
            )
        except Exception as e:
            error_message = f"Nieoczekiwany błąd podczas otwierania archiwum: {e}"
            self.logger.error(error_message)
            self.main_window.dialog_manager.show_error_message("Błąd", error_message)

    def show_file_context_menu(self, file_pair: FilePair, widget: QWidget, position):
        """
        Wyświetla menu kontekstowe dla pary plików.

        Args:
            file_pair: Para plików
            widget: Widget na którym wyświetlić menu
            position: Pozycja menu
        """
        context_menu = QMenu(widget)

        # Akcja podglądu
        preview_action = context_menu.addAction("Pokaż podgląd")
        preview_action.triggered.connect(
            lambda: self.main_window._show_preview_dialog(file_pair)
        )

        # Akcja otwierania archiwum
        open_action = context_menu.addAction("Otwórz archiwum")
        open_action.triggered.connect(lambda: self.open_archive(file_pair))

        # Separator
        context_menu.addSeparator()

        # Akcja kopiowania ścieżki archiwum
        copy_archive_action = context_menu.addAction("Kopiuj ścieżkę archiwum")
        copy_archive_action.triggered.connect(
            lambda: self._copy_path_to_clipboard(file_pair.archive_path)
        )

        # Akcja kopiowania ścieżki podglądu
        if file_pair.preview_path:
            copy_preview_action = context_menu.addAction("Kopiuj ścieżkę podglądu")
            copy_preview_action.triggered.connect(
                lambda: self._copy_path_to_clipboard(file_pair.preview_path)
            )

        # Separator
        context_menu.addSeparator()

        # Akcja otwierania folderu w eksploratorze
        open_folder_action = context_menu.addAction("Otwórz folder w eksploratorze")
        open_folder_action.triggered.connect(
            lambda: self._open_folder_in_explorer(file_pair)
        )

        # Wyświetl menu
        context_menu.exec(widget.mapToGlobal(position))

    def handle_file_drop_on_folder(
        self, source_file_paths: list[str], target_folder_path: str
    ):
        """
        Obsługuje przenoszenie plików poprzez drag & drop na folder.

        Args:
            source_file_paths: Lista ścieżek plików źródłowych
            target_folder_path: Ścieżka folderu docelowego
        """
        if not source_file_paths:
            self.logger.warning("Brak plików do przeniesienia")
            return

        if not os.path.exists(target_folder_path) or not os.path.isdir(
            target_folder_path
        ):
            self.main_window.dialog_manager.show_error_message(
                "Błąd", f"Folder docelowy nie istnieje: {target_folder_path}"
            )
            return

        # USUNIĘTO: Potwierdzenie operacji - drag & drop powinien działać bez pytań

        # Utwórz worker do przenoszenia
        worker = BulkMoveFilesWorker(source_file_paths, target_folder_path)

        # Podłącz sygnały
        self.main_window.worker_manager.setup_worker_connections(worker)
        worker.signals.finished.connect(self._on_file_drop_finished)
        worker.signals.error.connect(self._on_file_drop_error)

        # Uruchom worker
        self.main_window._show_progress(
            0, f"Przenoszenie {len(source_file_paths)} plików..."
        )
        self.main_window.thread_pool.start(worker)

    def _copy_path_to_clipboard(self, file_path: str):
        """
        Kopiuje ścieżkę pliku do schowka.

        Args:
            file_path: Ścieżka pliku do skopiowania
        """
        try:
            from PyQt6.QtWidgets import QApplication

            clipboard = QApplication.clipboard()
            clipboard.setText(file_path)

            self.logger.info(f"Skopiowano ścieżkę do schowka: {file_path}")

            # Pokaż krótką informację
            self.main_window.dialog_manager.show_progress_info(
                "Skopiowano",
                f"Ścieżka została skopiowana do schowka:\n{file_path}",
                auto_close_ms=2000,
            )

        except Exception as e:
            error_message = f"Nie udało się skopiować ścieżki: {e}"
            self.logger.error(error_message)
            self.main_window.dialog_manager.show_error_message(
                "Błąd kopiowania", error_message
            )

    def _open_folder_in_explorer(self, file_pair: FilePair):
        """
        Otwiera folder zawierający pliki pary w eksploratorze systemu.

        Args:
            file_pair: Para plików
        """
        archive_folder = os.path.dirname(file_pair.archive_path)

        if not os.path.exists(archive_folder):
            self.main_window.dialog_manager.show_error_message(
                "Błąd", f"Folder nie istnieje: {archive_folder}"
            )
            return

        try:
            if os.name == "nt":  # Windows
                subprocess.run(["explorer", archive_folder], check=True)
            elif os.name == "posix":  # macOS/Linux
                if os.uname().sysname == "Darwin":  # macOS
                    subprocess.run(["open", archive_folder], check=True)
                else:  # Linux
                    subprocess.run(["xdg-open", archive_folder], check=True)

            self.logger.info(f"Otwarto folder w eksploratorze: {archive_folder}")

        except subprocess.CalledProcessError as e:
            error_message = f"Nie udało się otworzyć folderu: {e}"
            self.logger.error(error_message)
            self.main_window.dialog_manager.show_error_message(
                "Błąd otwierania folderu", error_message
            )
        except Exception as e:
            error_message = f"Nieoczekiwany błąd podczas otwierania folderu: {e}"
            self.logger.error(error_message)
            self.main_window.dialog_manager.show_error_message("Błąd", error_message)

    def _on_file_drop_finished(self, result):
        """
        Obsługuje zakończenie operacji drag & drop.

        Args:
            result: Wynik operacji przenoszenia
        """
        if isinstance(result, dict):
            moved_files = result.get("moved_files", [])
            errors = result.get("errors", [])

            success_count = len(moved_files)
            error_count = len(errors)

            self.main_window._hide_progress()

            if success_count > 0:
                # USUNIĘTO: Okno informacyjne po drag & drop - ma działać cicho

                # Odśwież folder źródłowy po drag & drop
                if hasattr(self.main_window, "_refresh_source_folder_after_move"):
                    self.main_window._refresh_source_folder_after_move()
                else:
                    # Fallback - odśwież widok po pewnym czasie
                    QTimer.singleShot(500, self.main_window.refresh_all_views)

            if error_count > 0:
                error_details = "\n".join([f"• {error}" for error in errors[:5]])
                if error_count > 5:
                    error_details += f"\n... i {error_count - 5} więcej błędów"

                self.main_window.dialog_manager.show_error_message(
                    f"Błędy podczas przenoszenia ({error_count})",
                    f"Wystąpiły błędy podczas przenoszenia plików:\n\n{error_details}",
                )
        else:
            # Fallback dla starych formatów wyniku
            self.main_window._hide_progress()
            # USUNIĘTO: Okno informacyjne po drag & drop - ma działać cicho

            # Odśwież folder źródłowy po drag & drop
            if hasattr(self.main_window, "_refresh_source_folder_after_move"):
                self.main_window._refresh_source_folder_after_move()

    def _on_file_drop_error(self, error_message: str):
        """
        Obsługuje błędy podczas operacji drag & drop.

        Args:
            error_message: Komunikat błędu
        """
        self.main_window._hide_progress()
        self.logger.error(f"Błąd podczas drag & drop: {error_message}")
        self.main_window.dialog_manager.show_error_message(
            "Błąd przenoszenia plików",
            f"Wystąpił błąd podczas przenoszenia plików:\n\n{error_message}",
        )
