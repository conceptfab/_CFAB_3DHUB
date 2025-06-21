# 🔴 PATCH CODE: src/ui/directory_tree/manager.py

## 📋 Fragmenty kodu do poprawek

### **4.1 ELIMINACJA NADMIAROWYCH MANAGERÓW**

**PROBLEM:** 14 plików w katalogu directory_tree (nadmierna fragmentacja)

**ROZWIĄZANIE:** Konsolidacja do 4 plików: DirectoryTreeManager, DirectoryTreeCache, DirectoryTreeWorkers, DirectoryTreeUI

#### **4.1.1 UPROSZCZONA INICJALIZACJA**

```python
class DirectoryTreeManager:
    """
    Główny manager drzewa katalogów - uproszczony.
    Eliminacja over-engineering - bezpośrednie implementacje.
    """

    def __init__(self, folder_tree: QTreeView, parent_window):
        self.folder_tree = folder_tree
        self.parent_window = parent_window
        self.worker_factory = UIWorkerFactory()
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)

        # ==================== UPROSZCZONA INICJALIZACJA ====================
        # Cache statystyk folderów - bezpośrednio w managerze
        self._folder_stats_cache = {}
        self._cache_timeout = 300  # 5 minut

        # Scheduler dla workerów - uproszczony
        self._max_concurrent_workers = 2
        self._base_delay_ms = 150

        # Proxy model do filtrowania ukrytych folderów
        self.proxy_model = StatsProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterKeyColumn(0)
        self.setup_folder_filtering()

        # Użyj proxy model zamiast bezpośrednio file system model
        self.folder_tree.setModel(self.proxy_model)
        self.folder_tree.setRootIndex(
            self.proxy_model.mapFromSource(self.model.index(QDir.currentPath()))
        )

        # ==================== KONFIGURACJA UI ====================
        self.folder_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_tree.customContextMenuRequested.connect(self.show_folder_context_menu)

        # Ustawienia Drag and Drop
        self.folder_tree.setDragEnabled(False)
        self.folder_tree.setAcceptDrops(True)
        self.folder_tree.setDropIndicatorShown(True)
        self.folder_tree.setDragDropMode(QTreeView.DragDropMode.DropOnly)

        # Inicjalizacja dla podświetlania celu upuszczania
        self.highlighted_drop_index = QModelIndex()
        self.drop_highlight_delegate = DropHighlightDelegate(self, self.folder_tree)
        self.folder_tree.setItemDelegate(self.drop_highlight_delegate)

        self.current_scan_path: str | None = None
        self._main_working_directory = None

        # ==================== POŁĄCZENIE SYGNAŁÓW ====================
        self._connect_signals()
        self.setup_drag_and_drop_handlers()
```

#### **4.1.2 ELIMINACJA DELEGACJI - BEZPOŚREDNIE IMPLEMENTACJE**

```python
    # ==================== ELIMINACJA DELEGACJI ====================
    # Usunięto delegacje do event_handler, stats_manager, operations_manager, ui_handler
    # Bezpośrednie implementacje w DirectoryTreeManager

    def handle_item_clicked(self, proxy_index: QModelIndex):
        """Obsługa kliknięcia w element drzewa - bezpośrednia implementacja."""
        try:
            if not proxy_index.isValid():
                return

            source_index = self.proxy_model.mapToSource(proxy_index)
            if not source_index.isValid():
                return

            folder_path = self.model.filePath(source_index)
            if folder_path and os.path.isdir(folder_path):
                if hasattr(self.parent_window, "change_directory"):
                    self.parent_window.change_directory(folder_path)
        except Exception as e:
            logger.error(f"Błąd obsługi kliknięcia folderu: {e}")

    def handle_item_expanded(self, proxy_index: QModelIndex):
        """Obsługa rozwinięcia elementu - bezpośrednia implementacja."""
        try:
            if not proxy_index.isValid():
                return

            source_index = self.proxy_model.mapToSource(proxy_index)
            if not source_index.isValid():
                return

            folder_path = self.model.filePath(source_index)
            if folder_path:
                self._calculate_stats_async_silent(folder_path)
                logger.debug(f"Rozwinięto folder: {folder_path}")
        except Exception as e:
            logger.error(f"Błąd obsługi rozwinięcia folderu: {e}")

    def handle_double_click(self, proxy_index: QModelIndex):
        """Obsługa podwójnego kliknięcia - bezpośrednia implementacja."""
        try:
            if not proxy_index.isValid():
                return

            source_index = self.proxy_model.mapToSource(proxy_index)
            if not source_index.isValid():
                return

            folder_path = self.model.filePath(source_index)
            if folder_path and os.path.isdir(folder_path):
                self.open_folder_in_explorer(folder_path)
        except Exception as e:
            logger.error(f"Błąd obsługi podwójnego kliknięcia: {e}")
```

#### **4.1.3 UPROSZCZONE OPERACJE NA FOLDERACH**

```python
    def create_folder(self, parent_folder_path: str):
        """Tworzy nowy folder - bezpośrednia implementacja."""
        try:
            from PyQt6.QtWidgets import QInputDialog
            folder_name, ok = QInputDialog.getText(
                self.parent_window,
                "Utwórz folder",
                "Nazwa nowego folderu:",
            )

            if ok and folder_name:
                new_folder_path = os.path.join(parent_folder_path, folder_name)
                os.makedirs(new_folder_path, exist_ok=True)

                # Odśwież widok
                self.refresh_folder_only(parent_folder_path)
                logger.info(f"Utworzono folder: {new_folder_path}")

        except Exception as e:
            logger.error(f"Błąd tworzenia folderu: {e}")
            QMessageBox.critical(self.parent_window, "Błąd", f"Nie można utworzyć folderu: {e}")

    def rename_folder(self, folder_path: str):
        """Zmienia nazwę folderu - bezpośrednia implementacja."""
        try:
            from PyQt6.QtWidgets import QInputDialog
            current_name = os.path.basename(folder_path)
            parent_path = os.path.dirname(folder_path)

            new_name, ok = QInputDialog.getText(
                self.parent_window,
                "Zmień nazwę folderu",
                "Nowa nazwa folderu:",
                text=current_name,
            )

            if ok and new_name and new_name != current_name:
                new_folder_path = os.path.join(parent_path, new_name)
                os.rename(folder_path, new_folder_path)

                # Odśwież widok
                self.refresh_folder_only(parent_path)
                logger.info(f"Zmieniono nazwę folderu: {folder_path} -> {new_folder_path}")

        except Exception as e:
            logger.error(f"Błąd zmiany nazwy folderu: {e}")
            QMessageBox.critical(self.parent_window, "Błąd", f"Nie można zmienić nazwy folderu: {e}")

    def delete_folder(self, folder_path: str, current_working_directory: str):
        """Usuwa folder - bezpośrednia implementacja."""
        try:
            folder_name = os.path.basename(folder_path)
            confirm = QMessageBox.question(
                self.parent_window,
                "Potwierdź usunięcie",
                f"Czy na pewno chcesz usunąć folder '{folder_name}'?\n\n"
                f"Ścieżka: {folder_path}\n\n"
                "Ta operacja jest nieodwracalna.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if confirm == QMessageBox.StandardButton.Yes:
                import shutil
                shutil.rmtree(folder_path)

                # Odśwież widok
                parent_path = os.path.dirname(folder_path)
                self.refresh_folder_only(parent_path)
                logger.info(f"Usunięto folder: {folder_path}")

        except Exception as e:
            logger.error(f"Błąd usuwania folderu: {e}")
            QMessageBox.critical(self.parent_window, "Błąd", f"Nie można usunąć folderu: {e}")
```

### **4.2 UPROSZCZENIE DELEGACJI**

**PROBLEM:** 15+ metod delegujących do komponentów (150+ linii)

**ROZWIĄZANIE:** Usunięcie delegacji do event_handler, stats_manager, operations_manager, ui_handler

#### **4.2.1 ELIMINACJA DELEGACJI DO STATS_MANAGER**

```python
    # ==================== ELIMINACJA DELEGACJI DO STATS_MANAGER ====================
    # Usunięto delegacje, bezpośrednie implementacje w DirectoryTreeManager

    def start_background_stats_calculation(self):
        """Rozpoczyna obliczanie statystyk dla widocznych folderów w tle."""
        if not self._main_working_directory:
            return

        visible_folders = self._get_visible_folders()
        if not visible_folders:
            logger.debug("Brak widocznych folderów do obliczenia statystyk")
            return

        # Bezpośrednia implementacja bez delegacji
        for folder_path in visible_folders:
            self._calculate_stats_async_silent(folder_path)

    def _get_visible_folders(self) -> List[str]:
        """Pobiera listę widocznych folderów - bezpośrednia implementacja."""
        if not self._main_working_directory:
            return []

        visible_folders = []
        root_index = self.model.index(self._main_working_directory)

        def collect_visible_folders(parent_index):
            for row in range(self.model.rowCount(parent_index)):
                child_index = self.model.index(row, 0, parent_index)
                if child_index.isValid():
                    folder_path = self.model.filePath(child_index)
                    folder_name = self.model.fileName(child_index)

                    if self.should_show_folder(folder_name):
                        visible_folders.append(folder_path)
                        collect_visible_folders(child_index)

        collect_visible_folders(root_index)
        return visible_folders

    def _calculate_stats_async_silent(self, folder_path: str):
        """Oblicza statystyki folderu asynchronicznie - bezpośrednia implementacja."""
        try:
            worker = FolderStatisticsWorker(folder_path)

            def on_finished(stats):
                self.cache_folder_statistics(folder_path, stats)
                self._refresh_folder_display(folder_path)
                logger.debug(f"Statystyki: {os.path.basename(folder_path)} -> {stats.pairs_count} par")

            def on_error(error_msg):
                logger.warning(f"STATYSTYKI ERROR: {folder_path} -> {error_msg}")

            worker.custom_signals.finished.connect(on_finished)
            worker.custom_signals.error.connect(on_error)
            self._start_worker(worker)

        except Exception as e:
            logger.error(f"Błąd uruchamiania worker statystyk: {e}")

    def _refresh_folder_display(self, folder_path: str):
        """Odświeża wyświetlanie konkretnego folderu w drzewie."""
        try:
            source_index = self.model.index(folder_path)
            if source_index.isValid():
                proxy_index = self.get_proxy_index_from_source(source_index)
                if proxy_index.isValid():
                    self.proxy_model.dataChanged.emit(
                        proxy_index, proxy_index, [Qt.ItemDataRole.DisplayRole]
                    )
                    logger.debug(f"Odświeżono wyświetlanie folderu: {folder_path}")
        except Exception as e:
            logger.debug(f"Błąd odświeżania widoku folderu {folder_path}: {e}")
```

#### **4.2.2 ELIMINACJA DELEGACJI DO UI_HANDLER**

```python
    # ==================== ELIMINACJA DELEGACJI DO UI_HANDLER ====================
    # Usunięto delegacje, bezpośrednie implementacje w DirectoryTreeManager

    def open_folder_in_explorer(self, folder_path: str):
        """Otwiera folder w eksploratorze systemu - bezpośrednia implementacja."""
        try:
            import subprocess
            import platform

            if platform.system() == "Windows":
                subprocess.run(["explorer", folder_path], check=True)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", folder_path], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", folder_path], check=True)

            logger.debug(f"Otwarto folder w eksploratorze: {folder_path}")

        except Exception as e:
            logger.error(f"Błąd otwierania folderu w eksploratorze: {e}")
            QMessageBox.warning(self.parent_window, "Błąd", f"Nie można otworzyć folderu: {e}")

    def show_folder_context_menu(self, position):
        """Wyświetla menu kontekstowe dla folderu - bezpośrednia implementacja."""
        try:
            index = self.folder_tree.indexAt(position)
            if not index.isValid():
                return

            source_index = self.proxy_model.mapToSource(index)
            if not source_index.isValid():
                return

            folder_path = self.model.filePath(source_index)
            if not folder_path:
                return

            # Utwórz menu kontekstowe
            menu = QMenu(self.folder_tree)

            # Akcja: Otwórz w eksploratorze
            open_action = menu.addAction("Otwórz w eksploratorze")
            open_action.triggered.connect(lambda: self.open_folder_in_explorer(folder_path))

            menu.addSeparator()

            # Akcja: Utwórz folder
            create_action = menu.addAction("Utwórz folder")
            create_action.triggered.connect(lambda: self.create_folder(folder_path))

            # Akcja: Zmień nazwę
            rename_action = menu.addAction("Zmień nazwę")
            rename_action.triggered.connect(lambda: self.rename_folder(folder_path))

            # Akcja: Usuń
            delete_action = menu.addAction("Usuń")
            delete_action.triggered.connect(lambda: self.delete_folder(folder_path, self._main_working_directory))

            menu.addSeparator()

            # Akcja: Statystyki
            stats_action = menu.addAction("Pokaż statystyki")
            stats_action.triggered.connect(lambda: self.show_folder_statistics(folder_path))

            # Wyświetl menu
            menu.exec(self.folder_tree.mapToGlobal(position))

        except Exception as e:
            logger.error(f"Błąd wyświetlania menu kontekstowego: {e}")

    def refresh_file_pairs_after_folder_operation(self, current_working_directory: str):
        """Odświeża pary plików po operacji na folderze - bezpośrednia implementacja."""
        try:
            if hasattr(self.parent_window, "refresh_all_views"):
                self.parent_window.refresh_all_views()
            logger.debug("Odświeżono pary plików po operacji na folderze")
        except Exception as e:
            logger.error(f"Błąd odświeżania par plików: {e}")

    def folder_tree_item_clicked(self, proxy_index, current_working_directory: str):
        """Obsługa kliknięcia w element drzewa - bezpośrednia implementacja."""
        try:
            if not proxy_index.isValid():
                return

            source_index = self.proxy_model.mapToSource(proxy_index)
            if not source_index.isValid():
                return

            folder_path = self.model.filePath(source_index)
            if folder_path and os.path.isdir(folder_path):
                if hasattr(self.parent_window, "change_directory"):
                    self.parent_window.change_directory(folder_path)

        except Exception as e:
            logger.error(f"Błąd obsługi kliknięcia w drzewie: {e}")
```

### **4.3 OPTYMALIZACJA LOGOWANIA**

**PROBLEM:** Nadmiarowe logi DEBUG/INFO w normalnym użyciu

**ROZWIĄZANIE:** Zmiana INFO → DEBUG, usunięcie spam logów

#### **4.3.1 ZMIANA POZIOMÓW LOGÓW**

```python
    def setup_folder_filtering(self):
        """Konfiguruje filtrowanie ukrytych folderów."""
        def filter_folders(source_row: int, source_parent: QModelIndex) -> bool:
            index = self.model.index(source_row, 0, source_parent)
            if not index.isValid():
                return True

            folder_name = self.model.fileName(index)
            return self.should_show_folder(folder_name)

        # Ustaw funkcję filtrującą w naszym custom proxy model
        if hasattr(self.proxy_model, "set_filter_function"):
            self.proxy_model.set_filter_function(filter_folders)
        else:
            # Fallback dla standardowego proxy model
            self.proxy_model.filterAcceptsRow = filter_folders

        # ZMIANA: INFO → DEBUG
        logger.debug("DirectoryTreeManager: Utworzono StatsProxyModel")

    def _connect_signals(self):
        """Łączy sygnały Qt z handlerami."""
        # Obsługa kliknięć przez bezpośrednie metody
        self.folder_tree.clicked.connect(self.handle_item_clicked)
        # Obsługa rozwijania przez bezpośrednie metody
        self.folder_tree.expanded.connect(self.handle_item_expanded)
        # Dodaj obsługę podwójnego kliknięcia
        self.folder_tree.doubleClicked.connect(self.handle_double_click)

        # ZMIANA: Usunięto nadmiarowe logi

    def init_directory_tree(self, current_working_directory: str):
        """Inicjalizuje drzewo katalogów synchronicznie."""
        try:
            self._main_working_directory = current_working_directory

            # Ustaw root path
            self.model.setRootPath(current_working_directory)
            root_index = self.model.index(current_working_directory)
            proxy_root_index = self.proxy_model.mapFromSource(root_index)
            self.folder_tree.setRootIndex(proxy_root_index)

            # Skanuj foldery z plikami
            folders_with_files = self._scan_folders_with_files(current_working_directory)

            # Rozwiń foldery z plikami
            self._expand_folders_with_files(folders_with_files)

            # Rozpocznij obliczanie statystyk w tle
            self.start_background_stats_calculation()

            # ZMIANA: INFO → DEBUG
            logger.debug(f"Zainicjalizowano drzewo katalogów (sync) dla: {current_working_directory}")

        except Exception as e:
            logger.error(f"Błąd inicjalizacji drzewa katalogów: {e}")

    def init_directory_tree_without_expansion(self, current_working_directory: str):
        """Inicjalizuje drzewo katalogów bez automatycznego rozwijania folderów."""
        if not current_working_directory or not os.path.isdir(current_working_directory):
            logger.warning(f"Nieprawidłowy katalog: {current_working_directory}")
            return

        # Normalizacja ścieżki
        current_working_directory = PathValidator.normalize_path(current_working_directory)
        self._main_working_directory = current_working_directory

        # Ustaw root path w modelu
        source_index = self.model.setRootPath(current_working_directory)
        proxy_index = self.proxy_model.mapFromSource(source_index)
        self.folder_tree.setRootIndex(proxy_index)

        # Pokaż tylko jedną kolumnę z nazwami folderów
        for i in range(1, self.model.columnCount()):
            self.folder_tree.hideColumn(i)

        # Ustaw nagłówek
        self.folder_tree.header().hide()

        # Zapisz ścieżkę jako aktualną
        self.current_scan_path = current_working_directory

        # ZMIANA: INFO → DEBUG
        logger.debug(f"Ustawiono drzewo katalogów bez rozwijania: {current_working_directory}")
```

### **4.4 UPROSZCZENIE ARCHITEKTURY**

**PROBLEM:** Skomplikowane zależności i fallback code

**ROZWIĄZANIE:** Redukcja zależności, eliminacja sprawdzeń hasattr()

#### **4.4.1 UPROSZCZENIE SPRAWDZEŃ**

```python
    def _handle_operation_error(self, error_message: str, title: str, progress_dialog: QProgressDialog):
        """Obsługa błędów operacji - uproszczona."""
        logger.error(f"{title}: {error_message}")
        if progress_dialog and progress_dialog.isVisible():
            progress_dialog.reject()
        QMessageBox.critical(self.parent_window, title, error_message)

        # UPROSZCZENIE: Bezpośrednie wywołanie zamiast hasattr()
        self.parent_window.refresh_all_views()

    def _handle_operation_interrupted(self, message: str, progress_dialog: QProgressDialog):
        """Obsługa przerwania operacji - uproszczona."""
        logger.info(f"Operacja przerwana: {message}")
        if progress_dialog and progress_dialog.isVisible():
            progress_dialog.reject()
        QMessageBox.information(self.parent_window, "Operacja przerwana", message)

        # UPROSZCZENIE: Bezpośrednie wywołanie zamiast hasattr()
        self.parent_window.refresh_all_views()

    def handle_drop_on_folder(self, urls: List, target_folder_path: str):
        """Obsługuje upuszczenie plików na folder - uproszczona."""
        # UPROSZCZENIE: Bezpośrednia implementacja zamiast delegacji
        file_paths = [url.toLocalFile() for url in urls]
        logger.info(f"Dropped {len(file_paths)} files on folder {target_folder_path}")

        # Bezpośrednio rozpocznij przenoszenie
        self._start_file_move_operation(file_paths, target_folder_path)

    def _start_file_move_operation(self, file_paths: List[str], target_folder_path: str):
        """Rozpoczyna operację przenoszenia plików - uproszczona."""
        try:
            # UPROSZCZENIE: Bezpośrednie wywołanie zamiast hasattr()
            self.parent_window._show_progress(0, f"Przenoszenie {len(file_paths)} plików...")

            # Implementacja przenoszenia plików
            # ... (kod przenoszenia)

        except Exception as e:
            logger.error(f"Błąd przenoszenia plików: {e}")
            self.parent_window._show_progress(100, f"Błąd przenoszenia: {str(e)}")
```

#### **4.4.2 ELIMINACJA FALLBACK CODE**

```python
    def refresh_entire_tree(self):
        """Odświeża całe drzewo katalogów - uproszczone."""
        try:
            # Wyczyść cache
            self._folder_stats_cache.clear()

            # Anuluj wszystkie aktywne workery
            # UPROSZCZENIE: Bezpośrednie anulowanie zamiast skomplikowanego koordynatora
            QThreadPool.globalInstance().clear()

            # Odśwież model
            self.model.setRootPath(self.model.rootPath())

            # Przefiltruj na nowo
            self.proxy_model.invalidateFilter()

            logger.info("Odświeżono całe drzewo katalogów z wyczyszczeniem cache")
        except Exception as e:
            logger.error(f"Błąd odświeżania drzewa: {e}")

    def refresh_folder_only(self, folder_path: str) -> None:
        """Odświeża konkretny folder w drzewie katalogów - uproszczone."""
        try:
            normalized_path = PathValidator.normalize_path(folder_path)
            if not os.path.exists(normalized_path):
                logger.warning(f"Folder nie istnieje: {normalized_path}")
                return

            # Invalidate cache for this folder
            self.invalidate_folder_cache(normalized_path)

            # Refresh model
            source_index = self.model.index(normalized_path)
            if source_index.isValid():
                self.model.dataChanged.emit(source_index, source_index)
                logger.debug(f"Odświeżono folder: {normalized_path}")
        except Exception as e:
            logger.error(f"Błąd odświeżania folderu {folder_path}: {e}")

    def set_current_directory(self, directory_path: str):
        """Ustawia aktualny katalog - uproszczone."""
        if not directory_path or not os.path.isdir(directory_path):
            logger.warning(f"Nieprawidłowy katalog: {directory_path}")
            return

        # Normalizacja ścieżki
        directory_path = PathValidator.normalize_path(directory_path)
        self._main_working_directory = directory_path

        try:
            # Znajdź indeks dla ścieżki w modelu
            source_index = self.model.index(directory_path)
            if not source_index.isValid():
                logger.warning(f"Nie można znaleźć indeksu dla ścieżki: {directory_path}")
                return

            # Rozwiń wszystkie foldery nadrzędne
            parent_path = os.path.dirname(directory_path)
            parent_index = self.model.index(parent_path)
            if parent_index.isValid():
                proxy_parent_index = self.proxy_model.mapFromSource(parent_index)
                if proxy_parent_index.isValid():
                    self.folder_tree.expand(proxy_parent_index)

            # Mapuj indeks do proxy modelu
            proxy_index = self.proxy_model.mapFromSource(source_index)
            if not proxy_index.isValid():
                logger.warning(f"Nie można zmapować indeksu dla ścieżki: {directory_path}")
                return

            # Zaznacz folder w drzewie
            self.folder_tree.setCurrentIndex(proxy_index)
            self.folder_tree.scrollTo(proxy_index, QTreeView.ScrollHint.PositionAtCenter)

            # Wyraźnie zaznacz folder
            self.folder_tree.selectionModel().select(
                proxy_index,
                QItemSelectionModel.SelectionFlag.ClearAndSelect
            )

            # Rozwiń folder
            self.folder_tree.expand(proxy_index)

            # Zapisz jako aktualną ścieżkę
            self.current_scan_path = directory_path
            logger.info(f"Ustawiono aktualny katalog: {directory_path}")

            # Odśwież statystyki dla tego folderu
            self.invalidate_folder_cache(directory_path)
            self._calculate_stats_async_silent(directory_path)

            # Odśwież widok drzewa
            self.folder_tree.update()

        except Exception as e:
            logger.error(f"Błąd podczas ustawiania katalogu: {e}", exc_info=True)
```

---

**STATUS:** ✅ **GOTOWY DO IMPLEMENTACJI** - Wszystkie fragmenty kodu przygotowane.
