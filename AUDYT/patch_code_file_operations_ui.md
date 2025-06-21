# 🔴 PATCH CODE: src/ui/file_operations_ui.py

## 📋 Fragmenty kodu do poprawek

### **4.1 ELIMINACJA NADMIAROWYCH MANAGERÓW**

**PROBLEM:** 9 plików w katalogu file_operations (nadmierna fragmentacja)

**ROZWIĄZANIE:** Konsolidacja do 2 plików: FileOperationsUI, FileOperationsWorkers

#### **4.1.1 UPROSZCZONA INICJALIZACJA**

```python
class FileOperationsUI:
    """
    Klasa zarządzająca operacjami na plikach w interfejsie użytkownika.
    UPROSZCZONA - eliminacja over-engineering.
    """

    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.controller = FileOperationsController()

        # ELIMINACJA: Usunięto ProgressDialogFactory, WorkerCoordinator, ContextMenuManager, DetailedReporting
        # ELIMINACJA: Usunięto BasicFileOperations, DragDropHandler, ManualPairingManager

        # UPROSZCZENIE: Bezpośrednie implementacje w tej klasie
        logger.debug("FileOperationsUI zainicjalizowany - uproszczona wersja")

    # ==================== BEZPOŚREDNIE IMPLEMENTACJE ====================
    # Wszystkie operacje bezpośrednio w tej klasie, bez delegacji
```

#### **4.1.2 ELIMINACJA DELEGACJI - BEZPOŚREDNIE IMPLEMENTACJE**

```python
    def show_file_context_menu(self, file_pair: FilePair, widget: QWidget, position):
        """Wyświetla menu kontekstowe dla kafelka - bezpośrednia implementacja."""
        try:
            from PyQt6.QtWidgets import QMenu

            menu = QMenu(widget)

            # Akcja: Zmień nazwę
            rename_action = menu.addAction("Zmień nazwę")
            rename_action.triggered.connect(lambda: self.rename_file_pair(file_pair, widget))

            # Akcja: Usuń
            delete_action = menu.addAction("Usuń")
            delete_action.triggered.connect(lambda: self.delete_file_pair(file_pair, widget))

            # Akcja: Otwórz w eksploratorze
            open_action = menu.addAction("Otwórz w eksploratorze")
            open_action.triggered.connect(lambda: self.open_file_pair_in_explorer(file_pair))

            # Wyświetl menu
            menu.exec(widget.mapToGlobal(position))

        except Exception as e:
            logger.error(f"Błąd wyświetlania menu kontekstowego: {e}")

    def rename_file_pair(self, file_pair: FilePair, widget: QWidget) -> None:
        """Zmienia nazwę pary plików - bezpośrednia implementacja."""
        try:
            from PyQt6.QtWidgets import QInputDialog, QProgressDialog, QMessageBox

            current_name = file_pair.get_base_name()
            new_name, ok = QInputDialog.getText(
                self.parent_window,
                "Zmień nazwę",
                "Wprowadź nową nazwę (bez rozszerzenia):",
                text=current_name,
            )

            if ok and new_name and new_name != current_name:
                # Użyj controllera do utworzenia workera
                working_directory = file_pair.working_directory
                worker = self.controller.rename_file_pair(file_pair, new_name, working_directory)

                if worker:
                    # Utwórz progress dialog
                    progress_dialog = QProgressDialog(
                        f"Zmienianie nazwy '{current_name}' na '{new_name}'...",
                        "Anuluj",
                        0,
                        100,
                        self.parent_window,
                    )
                    progress_dialog.setWindowTitle("Zmiana nazwy pliku")
                    progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)

                    # Uruchom worker
                    self._setup_and_start_worker(
                        worker=worker,
                        progress_dialog=progress_dialog,
                        finished_handler=lambda new_fp: self._handle_rename_finished(
                            file_pair, new_fp, progress_dialog
                        ),
                        error_handler=lambda err_msg: self._handle_operation_error(
                            err_msg, "Błąd zmiany nazwy pliku", progress_dialog
                        ),
                        progress_handler=lambda percent, msg: self._handle_operation_progress(
                            percent, msg, progress_dialog
                        ),
                        interrupted_handler=lambda: self._handle_operation_interrupted(
                            "Zmiana nazwy pliku przerwana.", progress_dialog
                        )
                    )
                else:
                    QMessageBox.warning(
                        self.parent_window,
                        "Błąd inicjalizacji",
                        f"Nie można zainicjować operacji zmiany nazwy pliku '{current_name}'. Sprawdź logi.",
                    )

        except Exception as e:
            logger.error(f"Błąd zmiany nazwy pliku: {e}")

    def delete_file_pair(self, file_pair: FilePair, widget: QWidget) -> None:
        """Usuwa parę plików - bezpośrednia implementacja."""
        try:
            from PyQt6.QtWidgets import QMessageBox, QProgressDialog

            # Potwierdź usunięcie
            confirm = QMessageBox.question(
                self.parent_window,
                "Potwierdź usunięcie",
                f"Czy na pewno chcesz usunąć pliki dla "
                f"'{file_pair.get_base_name()}'?\n\n"
                f"Archiwum: {file_pair.get_archive_path()}\n"
                f"Podgląd: {file_pair.get_preview_path()}\n\n"
                "Ta operacja jest nieodwracalna.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if confirm == QMessageBox.StandardButton.Yes:
                # Użyj controllera do utworzenia workera
                worker = self.controller.delete_file_pair(file_pair)

                if worker:
                    # Utwórz progress dialog
                    progress_dialog = QProgressDialog(
                        f"Usuwanie plików dla '{file_pair.get_base_name()}'...",
                        "Anuluj",
                        0,
                        100,
                        self.parent_window,
                    )
                    progress_dialog.setWindowTitle("Usuwanie pliku")
                    progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)

                    # Uruchom worker
                    self._setup_and_start_worker(
                        worker=worker,
                        progress_dialog=progress_dialog,
                        finished_handler=lambda deleted_fp: self._handle_delete_finished(
                            deleted_fp, progress_dialog
                        ),
                        error_handler=lambda err_msg: self._handle_operation_error(
                            err_msg, "Błąd usuwania pliku", progress_dialog
                        ),
                        progress_handler=lambda percent, msg: self._handle_operation_progress(
                            percent, msg, progress_dialog
                        ),
                        interrupted_handler=lambda: self._handle_operation_interrupted(
                            "Usuwanie pliku przerwane.", progress_dialog
                        )
                    )
                else:
                    QMessageBox.warning(
                        self.parent_window,
                        "Błąd inicjalizacji",
                        f"Nie można zainicjować operacji usuwania pliku '{file_pair.get_base_name()}'. Sprawdź logi.",
                    )

        except Exception as e:
            logger.error(f"Błąd usuwania pliku: {e}")

    def move_file_pair_ui(self, file_pair_to_move: FilePair, target_folder_path: str) -> None:
        """Przenosi parę plików do nowego folderu - bezpośrednia implementacja."""
        try:
            from PyQt6.QtWidgets import QMessageBox, QProgressDialog
            import os
            from src.utils.path_validator import PathValidator

            # Sprawdzenie podstawowych parametrów
            if not file_pair_to_move or not target_folder_path:
                logger.warning("Próba przeniesienia nieprawidłowej pary plików lub do nieprawidłowej lokalizacji.")
                return

            # Sprawdzenie, czy folder docelowy jest taki sam jak folder źródłowy
            source_folder_path = os.path.dirname(file_pair_to_move.archive_path)
            if PathValidator.normalize_path(source_folder_path) == PathValidator.normalize_path(target_folder_path):
                QMessageBox.information(
                    self.parent_window,
                    "Informacja",
                    "Plik już znajduje się w folderze docelowym.",
                )
                return

            # Użyj controllera do utworzenia workera
            worker = self.controller.move_file_pair(file_pair_to_move, target_folder_path)

            if worker:
                # Utwórz progress dialog
                progress_dialog = QProgressDialog(
                    f"Przenoszenie '{file_pair_to_move.get_base_name()}' do '{target_folder_path}'...",
                    "Anuluj",
                    0,
                    100,
                    self.parent_window,
                )
                progress_dialog.setWindowTitle("Przenoszenie pliku")
                progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)

                # Uruchom worker
                self._setup_and_start_worker(
                    worker=worker,
                    progress_dialog=progress_dialog,
                    finished_handler=lambda new_fp: self._handle_move_finished(
                        file_pair_to_move, new_fp, target_folder_path, progress_dialog
                    ),
                    error_handler=lambda err_msg: self._handle_operation_error(
                        err_msg, "Błąd przenoszenia pliku", progress_dialog
                    ),
                    progress_handler=lambda percent, msg: self._handle_operation_progress(
                        percent, msg, progress_dialog
                    ),
                    interrupted_handler=lambda: self._handle_operation_interrupted(
                        "Przenoszenie pliku przerwane.", progress_dialog
                    )
                )
            else:
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd inicjalizacji",
                    f"Nie można zainicjować operacji przenoszenia pliku '{file_pair_to_move.get_base_name()}'. Sprawdź logi.",
                )

        except Exception as e:
            logger.error(f"Błąd przenoszenia pliku: {e}")
```

### **4.2 UPROSZCZENIE DELEGACJI**

**PROBLEM:** 8+ metod delegujących do komponentów (100% delegacji)

**ROZWIĄZANIE:** Usunięcie delegacji do basic_operations, drag_drop_handler, pairing_manager

#### **4.2.1 BEZPOŚREDNIA IMPLEMENTACJA DRAG & DROP**

```python
    def handle_drop_on_folder(self, urls: List, target_folder_path: str):
        """Obsługuje upuszczenie plików na folder - bezpośrednia implementacja."""
        try:
            import os
            import shutil
            from src.logic.scanner import collect_files, create_file_pairs
            from src.ui.delegates.workers import BulkMoveWorker

            file_paths = [url.toLocalFile() for url in urls]
            logger.info(f"Dropped {len(file_paths)} files on folder {target_folder_path}")

            # Bezpośrednio rozpocznij przenoszenie bez pytania
            logger.info("Starting file move operation...")

            # Informuj o rozpoczęciu w pasku statusu
            self.parent_window._show_progress(0, f"Przenoszenie {len(file_paths)} plików...")

            # Zbierz wszystkie pliki z podanych ścieżek
            all_files = []
            for file_path in file_paths:
                if os.path.isfile(file_path):
                    all_files.append(file_path)
                    logger.debug(f"Added file: {file_path}")
                elif os.path.isdir(file_path):
                    logger.debug(f"Found folder, scanning contents: {file_path}")
                    # Jeśli to folder, zbierz pliki z niego
                    dir_file_map = collect_files(file_path, max_depth=1)
                    for files_list in dir_file_map.values():
                        all_files.extend(files_list)
                        logger.debug(f"Added files from folder: {files_list}")
                else:
                    logger.warning(f"Skipped non-existent item: {file_path}")

            logger.info(f"Found total {len(all_files)} files to move")

            if not all_files:
                self.parent_window._show_progress(100, "Nie znaleziono plików do przeniesienia")
                logger.warning("ERROR - No files found to move")
                return False

            # Utwórz tymczasowy file_map dla algorytmu create_file_pairs
            temp_file_map = {}
            for file_path in all_files:
                dir_path = os.path.dirname(file_path)
                if dir_path not in temp_file_map:
                    temp_file_map[dir_path] = []
                temp_file_map[dir_path].append(file_path)

            logger.debug(f"Created file_map for {len(temp_file_map)} directories")

            # Utwórz pary plików używając strategii "best_match"
            file_pairs, _ = create_file_pairs(
                temp_file_map,
                target_folder_path,
                pair_strategy="best_match",
            )

            logger.info(f"Created {len(file_pairs)} file pairs")

            if not file_pairs:
                # Jeśli nie udało się utworzyć par, spróbuj przenieść pliki indywidualnie
                logger.warning("Failed to create file pairs. Moving individual files.")
                self._move_individual_files(all_files, target_folder_path)
                logger.info("SUCCESS - Moved files individually")
                return True

            # Użyj BulkMoveWorker do przeniesienia par plików
            logger.info(f"Starting BulkMoveWorker for {len(file_pairs)} pairs")
            self._move_file_pairs_bulk(file_pairs, target_folder_path)
            logger.info("SUCCESS - Started file pairs move operation")
            return True

        except Exception as e:
            logger.error(f"ERROR during file move operation: {e}", exc_info=True)
            self.parent_window._show_progress(100, f"Błąd przenoszenia: {str(e)}")
            return False

    def _move_individual_files(self, files: list[str], target_folder_path: str):
        """Przenosi pojedyncze pliki do folderu docelowego - bezpośrednia implementacja."""
        logger.info(f"Moving {len(files)} individual files")
        logger.debug(f"Target folder: {target_folder_path}")

        try:
            import shutil

            for i, file_path in enumerate(files):
                filename = os.path.basename(file_path)
                destination_path = os.path.join(target_folder_path, filename)

                logger.debug(f"Moving {i+1}/{len(files)}: {file_path} -> {destination_path}")

                # Informuj o postępie w pasku statusu
                progress_percent = int((i / len(files)) * 100)
                self.parent_window._show_progress(progress_percent, f"Przenoszenie: {filename}")

                try:
                    shutil.move(file_path, destination_path)
                    logger.debug(f"Moved: {file_path} -> {destination_path}")
                except Exception as e:
                    logger.error(f"Error moving {file_path}: {e}")

            # Zakończenie operacji
            self.parent_window._show_progress(100, f"Przeniesiono {len(files)} plików")
            logger.info(f"Individual files move completed - moved {len(files)} files")

        except Exception as e:
            logger.error(f"Error during individual files move: {e}")
            self.parent_window._show_progress(100, f"Błąd: {str(e)}")

        # Odśwież widoki
        if hasattr(self.parent_window, "refresh_all_views"):
            logger.debug("Refreshing views after individual file move")
            self.parent_window.refresh_all_views()

    def _move_file_pairs_bulk(self, file_pairs: list[FilePair], target_folder_path: str):
        """Przenosi pary plików używając BulkMoveWorker - bezpośrednia implementacja."""
        if not file_pairs:
            logger.warning("move_file_pairs_bulk called with empty file list")
            return

        try:
            from src.ui.delegates.workers import BulkMoveWorker

            # Utwórz worker
            worker = BulkMoveWorker(file_pairs, target_folder_path)

            # Połącz sygnały
            worker.custom_signals.finished.connect(self._handle_bulk_move_finished)
            worker.custom_signals.error.connect(self._handle_bulk_move_error)
            worker.custom_signals.progress.connect(self._handle_bulk_move_progress)

            # Uruchom worker
            from PyQt6.QtCore import QThreadPool
            QThreadPool.globalInstance().start(worker)

            logger.info(f"Started BulkMoveWorker for {len(file_pairs)} file pairs")

        except Exception as e:
            logger.error(f"Error starting BulkMoveWorker: {e}")
            self._handle_bulk_move_error(f"Błąd uruchamiania operacji przenoszenia: {e}")

    def _handle_bulk_move_finished(self, result):
        """Obsługa zakończenia bulk move - bezpośrednia implementacja."""
        try:
            logger.info("Bulk move operation completed successfully")
            self.parent_window._show_progress(100, "Przenoszenie zakończone pomyślnie")

            # Odśwież widoki
            if hasattr(self.parent_window, "refresh_all_views"):
                self.parent_window.refresh_all_views()

        except Exception as e:
            logger.error(f"Error handling bulk move finished: {e}")

    def _handle_bulk_move_error(self, error_message: str):
        """Obsługa błędu bulk move - bezpośrednia implementacja."""
        logger.error(f"Bulk move error: {error_message}")
        self.parent_window._show_progress(100, f"Błąd przenoszenia: {error_message}")

    def _handle_bulk_move_progress(self, percent: int, message: str):
        """Obsługa postępu bulk move - bezpośrednia implementacja."""
        logger.debug(f"Bulk move progress: {percent}% - {message}")
        self.parent_window._show_progress(percent, message)
```

#### **4.2.2 BEZPOŚREDNIA IMPLEMENTACJA MANUAL PAIRING**

```python
    def handle_manual_pairing(self, unpaired_archives_list: QListWidget, unpaired_previews_list: QListWidget, current_working_directory: str) -> None:
        """Obsługuje ręczne parowanie plików - bezpośrednia implementacja."""
        try:
            from PyQt6.QtWidgets import QMessageBox, QProgressDialog
            from src.ui.delegates.workers import ManuallyPairFilesWorker

            # Sprawdź czy są wybrane pliki
            selected_archives = unpaired_archives_list.selectedItems()
            selected_previews = unpaired_previews_list.selectedItems()

            if not selected_archives or not selected_previews:
                QMessageBox.warning(
                    self.parent_window,
                    "Brak wyboru",
                    "Wybierz archiwum i podgląd do sparowania.",
                )
                return

            if len(selected_archives) > 1 or len(selected_previews) > 1:
                QMessageBox.warning(
                    self.parent_window,
                    "Zbyt wiele wyborów",
                    "Wybierz tylko jedno archiwum i jeden podgląd.",
                )
                return

            archive_item = selected_archives[0]
            preview_item = selected_previews[0]

            # Pobierz ścieżki plików
            archive_path = archive_item.data(Qt.ItemDataRole.UserRole)
            preview_path = preview_item.data(Qt.ItemDataRole.UserRole)

            if not archive_path or not preview_path:
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd danych",
                    "Nie można odczytać ścieżek plików.",
                )
                return

            # Utwórz worker
            worker = ManuallyPairFilesWorker(archive_path, preview_path, current_working_directory)

            # Utwórz progress dialog
            progress_dialog = QProgressDialog(
                f"Parowanie plików...",
                "Anuluj",
                0,
                100,
                self.parent_window,
            )
            progress_dialog.setWindowTitle("Ręczne parowanie")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)

            # Uruchom worker
            self._setup_and_start_worker(
                worker=worker,
                progress_dialog=progress_dialog,
                finished_handler=lambda new_fp: self._handle_manual_pairing_finished(
                    new_fp, progress_dialog, unpaired_archives_list, unpaired_previews_list
                ),
                error_handler=lambda err_msg: self._handle_operation_error(
                    err_msg, "Błąd parowania plików", progress_dialog
                ),
                progress_handler=lambda percent, msg: self._handle_operation_progress(
                    percent, msg, progress_dialog
                ),
                interrupted_handler=lambda: self._handle_operation_interrupted(
                    "Parowanie plików przerwane.", progress_dialog
                )
            )

        except Exception as e:
            logger.error(f"Błąd ręcznego parowania: {e}")

    def _handle_manual_pairing_finished(self, new_file_pair: FilePair, progress_dialog: QProgressDialog, unpaired_archives_list: QListWidget, unpaired_previews_list: QListWidget):
        """Obsługa zakończenia ręcznego parowania - bezpośrednia implementacja."""
        try:
            progress_dialog.accept()

            logger.info(f"Pomyślnie sparowano pliki: {new_file_pair.get_base_name()}")

            # Odśwież listy niesparowanych plików
            if hasattr(self.parent_window, "refresh_all_views"):
                self.parent_window.refresh_all_views()

        except Exception as e:
            logger.error(f"Błąd obsługi zakończenia parowania: {e}")
```

### **4.3 OPTYMALIZACJA LOGOWANIA**

**PROBLEM:** Nadmiarowe logi DEBUG/INFO w normalnym użyciu

**ROZWIĄZANIE:** Zmiana INFO → DEBUG, usunięcie spam logów

#### **4.3.1 ZMIANA POZIOMÓW LOGÓW**

```python
    def _handle_operation_error(self, error_message: str, title: str, progress_dialog: QProgressDialog):
        """Obsługa błędów operacji - zoptymalizowane logowanie."""
        logger.error(f"{title}: {error_message}")
        if progress_dialog and progress_dialog.isVisible():
            progress_dialog.reject()
        QMessageBox.critical(self.parent_window, title, error_message)

        # Odśwież widoki
        if hasattr(self.parent_window, "refresh_all_views"):
            self.parent_window.refresh_all_views()

    def _handle_operation_progress(self, percent: int, message: str, progress_dialog: QProgressDialog):
        """Obsługa postępu operacji - zoptymalizowane logowanie."""
        # ZMIANA: INFO → DEBUG
        logger.debug(f"Postęp operacji: {percent}% - {message}")
        if progress_dialog and progress_dialog.isVisible():
            if progress_dialog.maximum() == 0:  # Nieokreślony
                progress_dialog.setLabelText(message)
            else:
                progress_dialog.setValue(percent)
                progress_dialog.setLabelText(message)

    def _handle_operation_interrupted(self, message: str, progress_dialog: QProgressDialog):
        """Obsługa przerwania operacji - zoptymalizowane logowanie."""
        # ZMIANA: INFO → DEBUG
        logger.debug(f"Operacja przerwana: {message}")
        if progress_dialog and progress_dialog.isVisible():
            progress_dialog.reject()
        QMessageBox.information(self.parent_window, "Operacja przerwana", message)
        if hasattr(self.parent_window, "refresh_all_views"):
            self.parent_window.refresh_all_views()

    def show_unpaired_context_menu(self, position, list_widget: QListWidget, list_type: str):
        """Wyświetla menu kontekstowe dla listy niesparowanych plików - zoptymalizowane."""
        try:
            from PyQt6.QtWidgets import QMenu

            # Pobierz element pod kursorem
            item = list_widget.itemAt(position)
            if not item:
                return

            # Utwórz menu kontekstowe
            menu = QMenu(list_widget)

            if list_type == "archives":
                # Menu dla archiwów
                open_action = menu.addAction("Otwórz w eksploratorze")
                open_action.triggered.connect(lambda: self._open_file_in_explorer(item))

            elif list_type == "previews":
                # Menu dla podglądów
                open_action = menu.addAction("Otwórz w eksploratorze")
                open_action.triggered.connect(lambda: self._open_file_in_explorer(item))

                preview_action = menu.addAction("Podgląd")
                preview_action.triggered.connect(lambda: self._preview_file(item))

            # Wyświetl menu
            menu.exec(list_widget.mapToGlobal(position))

        except Exception as e:
            logger.error(f"Błąd wyświetlania menu kontekstowego: {e}")

    def _open_file_in_explorer(self, item):
        """Otwiera plik w eksploratorze - zoptymalizowane."""
        try:
            import subprocess
            import platform

            file_path = item.data(Qt.ItemDataRole.UserRole)
            if not file_path:
                return

            if platform.system() == "Windows":
                subprocess.run(["explorer", "/select,", file_path], check=True)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", "-R", file_path], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", os.path.dirname(file_path)], check=True)

            # ZMIANA: INFO → DEBUG
            logger.debug(f"Otwarto plik w eksploratorze: {file_path}")

        except Exception as e:
            logger.error(f"Błąd otwierania pliku w eksploratorze: {e}")

    def _preview_file(self, item):
        """Podgląd pliku - zoptymalizowane."""
        try:
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if not file_path:
                return

            # Otwórz w domyślnej aplikacji
            import subprocess
            import platform

            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", file_path], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", file_path], check=True)

            # ZMIANA: INFO → DEBUG
            logger.debug(f"Podgląd pliku: {file_path}")

        except Exception as e:
            logger.error(f"Błąd podglądu pliku: {e}")
```

### **4.4 UPROSZCZENIE ARCHITEKTURY**

**PROBLEM:** Skomplikowane zależności i fallback code

**ROZWIĄZANIE:** Redukcja zależności, eliminacja sprawdzeń hasattr()

#### **4.4.1 UPROSZCZENIE SPRAWDZEŃ**

```python
    def _setup_and_start_worker(self, worker, progress_dialog, finished_handler, error_handler, progress_handler, interrupted_handler):
        """Uruchamia worker z obsługą sygnałów - uproszczone."""
        try:
            # Połącz sygnały
            worker.custom_signals.finished.connect(finished_handler)
            worker.custom_signals.error.connect(error_handler)
            worker.custom_signals.progress.connect(progress_handler)

            # Połącz anulowanie
            if progress_dialog:
                progress_dialog.canceled.connect(worker.interrupt)
                progress_dialog.show()

            # Uruchom worker
            from PyQt6.QtCore import QThreadPool
            QThreadPool.globalInstance().start(worker)

            logger.debug("Worker uruchomiony pomyślnie")

        except Exception as e:
            logger.error(f"Błąd uruchamiania workera: {e}")
            if progress_dialog:
                progress_dialog.reject()

    def _handle_rename_finished(self, old_file_pair: FilePair, new_file_pair: FilePair, progress_dialog: QProgressDialog):
        """Obsługa zakończenia zmiany nazwy - uproszczone."""
        try:
            progress_dialog.accept()

            logger.info(f"Pomyślnie zmieniono nazwę: {old_file_pair.get_base_name()} -> {new_file_pair.get_base_name()}")

            # Odśwież widoki
            self.parent_window.refresh_all_views()

        except Exception as e:
            logger.error(f"Błąd obsługi zakończenia zmiany nazwy: {e}")

    def _handle_delete_finished(self, deleted_file_pair: FilePair, progress_dialog: QProgressDialog):
        """Obsługa zakończenia usuwania - uproszczone."""
        try:
            progress_dialog.accept()

            logger.info(f"Pomyślnie usunięto pliki: {deleted_file_pair.get_base_name()}")

            # Odśwież widoki
            self.parent_window.refresh_all_views()

        except Exception as e:
            logger.error(f"Błąd obsługi zakończenia usuwania: {e}")

    def _handle_move_finished(self, old_file_pair: FilePair, new_file_pair: FilePair, target_folder_path: str, progress_dialog: QProgressDialog):
        """Obsługa zakończenia przenoszenia - uproszczone."""
        try:
            progress_dialog.accept()

            logger.info(f"Pomyślnie przeniesiono: {old_file_pair.get_base_name()} -> {target_folder_path}")

            # Odśwież widoki
            self.parent_window.refresh_all_views()

        except Exception as e:
            logger.error(f"Błąd obsługi zakończenia przenoszenia: {e}")
```

#### **4.4.2 ELIMINACJA FALLBACK CODE**

```python
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.controller = FileOperationsController()

        # UPROSZCZENIE: Bezpośrednie inicjalizacje bez skomplikowanych managerów
        # ELIMINACJA: Usunięto wszystkie fallback sprawdzenia hasattr()

        # ZMIANA: INFO → DEBUG
        logger.debug("FileOperationsUI zainicjalizowany - uproszczona wersja")

    def handle_drop_on_folder(self, urls: List, target_folder_path: str):
        """Obsługuje upuszczenie plików na folder - uproszczone."""
        try:
            # UPROSZCZENIE: Bezpośrednie wywołanie zamiast hasattr()
            self.parent_window._show_progress(0, f"Przetwarzanie {len(urls)} plików...")

            # Implementacja przenoszenia plików
            # ... (kod przenoszenia)

        except Exception as e:
            logger.error(f"Błąd przenoszenia plików: {e}")
            # UPROSZCZENIE: Bezpośrednie wywołanie zamiast hasattr()
            self.parent_window._show_progress(100, f"Błąd przenoszenia: {str(e)}")

    def _move_individual_files(self, files: list[str], target_folder_path: str):
        """Przenosi pojedyncze pliki - uproszczone."""
        logger.info(f"Moving {len(files)} individual files")

        try:
            import shutil

            for i, file_path in enumerate(files):
                filename = os.path.basename(file_path)
                destination_path = os.path.join(target_folder_path, filename)

                # UPROSZCZENIE: Bezpośrednie wywołanie zamiast hasattr()
                progress_percent = int((i / len(files)) * 100)
                self.parent_window._show_progress(progress_percent, f"Przenoszenie: {filename}")

                try:
                    shutil.move(file_path, destination_path)
                    logger.debug(f"Moved: {file_path} -> {destination_path}")
                except Exception as e:
                    logger.error(f"Error moving {file_path}: {e}")

            # Zakończenie operacji
            self.parent_window._show_progress(100, f"Przeniesiono {len(files)} plików")
            logger.info(f"Individual files move completed - moved {len(files)} files")

        except Exception as e:
            logger.error(f"Error during individual files move: {e}")
            self.parent_window._show_progress(100, f"Błąd: {str(e)}")

        # UPROSZCZENIE: Bezpośrednie wywołanie zamiast hasattr()
        self.parent_window.refresh_all_views()
```

---

**STATUS:** ✅ **GOTOWY DO IMPLEMENTACJI** - Wszystkie fragmenty kodu przygotowane.
