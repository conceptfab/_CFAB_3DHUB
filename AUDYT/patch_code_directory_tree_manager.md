# 🔧 FRAGMENTY KODU - POPRAWKI directory_tree/manager.py

## 1. BŁĘDY KRYTYCZNE

### 1.1 Eliminacja over-engineering - konsolidacja managerów

**Problematyczny kod - 25 metod delegujących:**
```python
def get_cached_folder_statistics(self, folder_path: str) -> Optional[FolderStatistics]:
    """Pobiera statystyki z cache - deleguje do data_manager."""
    return self.data_manager.load_directory_data(folder_path)

def show_folder_statistics(self, folder_path: str):
    """Deleguje do stats_manager."""
    return self.stats_manager.show_folder_statistics(folder_path)

def create_folder(self, parent_folder_path: str):
    """Deleguje do operations_manager."""
    return self.operations_manager.create_folder(parent_folder_path)
# ... i 22 kolejne metody delegujące
```

**Poprawiony kod - bezpośrednia implementacja:**
```python
class DirectoryTreeManager:
    """Simplified directory tree manager without over-engineering."""
    
    def __init__(self, folder_tree: QTreeView, parent_window):
        self.folder_tree = folder_tree
        self.parent_window = parent_window
        self.model = QFileSystemModel()
        
        # Tylko podstawowe komponenty
        self._folder_stats_cache = FolderStatsCache(max_entries=100, timeout_seconds=300)
        self._worker_scheduler = ThrottledWorkerScheduler(max_concurrent_workers=2, base_delay_ms=150)
        self._current_working_directory = None
        self.highlighted_drop_index = QModelIndex()
        
        # Setup podstawowy
        self._setup_model()
        self._setup_ui()
        self._connect_signals()
    
    def get_cached_folder_statistics(self, folder_path: str) -> Optional[FolderStatistics]:
        """Pobiera statystyki z cache - bezpośrednia implementacja."""
        return self._folder_stats_cache.get(folder_path)

    def cache_folder_statistics(self, folder_path: str, stats: FolderStatistics):
        """Zapisuje statystyki do cache - bezpośrednia implementacja."""
        self._folder_stats_cache.set(folder_path, stats)

    def show_folder_statistics(self, folder_path: str):
        """Pokazuje statystyki folderu - bezpośrednia implementacja."""
        stats = self.get_cached_folder_statistics(folder_path)
        if not stats:
            self.calculate_folder_statistics_async(folder_path, 
                lambda s: self._display_folder_statistics(s, folder_path))
            return
        self._display_folder_statistics(stats, folder_path)
```

### 1.2 Redukcja zależności - uproszczenie importów

**Problematyczne importy (22 importy):**
```python
# Zbyt dużo lokalnych importów
from .cache import FolderStatsCache
from .data_classes import FolderStatistics
from .data_manager import DirectoryTreeDataManager
from .delegates import DropHighlightDelegate
from .event_handler import DirectoryTreeEventHandler
from .drag_drop_handler import DirectoryTreeDragDropHandler
from .operations_manager import DirectoryTreeOperationsManager
from .stats_manager import DirectoryTreeStatsManager
from .ui_handler import DirectoryTreeUIHandler
from .models import FolderStatsDelegate, StatsProxyModel
from .throttled_scheduler import ThrottledWorkerScheduler
from .worker_coordinator import DirectoryTreeWorkerCoordinator
from .workers import FolderScanWorker, FolderStatisticsWorker
```

**Uproszczone importy (tylko niezbędne):**
```python
import logging
import os
import subprocess
import time
from typing import List, Optional, Dict, Callable
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import QDir, QModelIndex, Qt, QTimer, QItemSelectionModel, QObject, pyqtSignal
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import (
    QHBoxLayout, QInputDialog, QMenu, QMessageBox, QProgressDialog, 
    QPushButton, QToolBar, QTreeView, QWidget
)

from src.factories.worker_factory import UIWorkerFactory
from src.logic import file_operations
from src.utils.path_validator import PathValidator

# Tylko podstawowe lokalne komponenty
from .cache import FolderStatsCache
from .data_classes import FolderStatistics
from .workers import FolderScanWorker, FolderStatisticsWorker
```

### 1.3 Async I/O dla skanowania folderów

**Problematyczny kod - sync I/O w UI thread:**
```python
def _scan_folders_with_files(self, root_folder: str) -> List[str]:
    """Skanuje foldery w poszukiwaniu tych zawierających pliki."""
    folders_with_files = []
    try:
        for root, dirs, files in os.walk(root_folder):  # BLOCKING!
            # Pomiń ukryte foldery
            dirs[:] = [d for d in dirs if not d.startswith(".") and self.should_show_folder(d)]
            
            if files:
                folders_with_files.append(root)
                
            depth = root[len(root_folder):].count(os.sep)
            if depth >= 3:
                dirs.clear()
    except Exception as e:
        logger.error(f"Błąd skanowania folderów: {e}")
    
    return folders_with_files
```

**Poprawiony kod - async I/O:**
```python
from concurrent.futures import ThreadPoolExecutor
import asyncio

class DirectoryTreeManager:
    def __init__(self, ...):
        # ...
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="DirScan")
        self._scan_in_progress = False
    
    def scan_folders_with_files_async(self, root_folder: str, callback: Callable[[List[str]], None]):
        """Asynchroniczne skanowanie folderów bez blokowania UI."""
        if self._scan_in_progress:
            logger.warning("Skanowanie już w toku")
            return
            
        self._scan_in_progress = True
        
        def scan_worker():
            try:
                folders_with_files = []
                max_depth = 3
                max_folders = 1000  # Limit bezpieczeństwa
                
                for root, dirs, files in os.walk(root_folder):
                    # Quick exit conditions
                    if len(folders_with_files) >= max_folders:
                        break
                        
                    # Filter hidden folders efficiently
                    dirs[:] = [d for d in dirs if self._is_folder_visible(d)]
                    
                    if files:
                        folders_with_files.append(root)
                    
                    # Depth control
                    depth = root[len(root_folder):].count(os.sep)
                    if depth >= max_depth:
                        dirs.clear()
                
                return folders_with_files
                
            except Exception as e:
                logger.error(f"Błąd skanowania folderów: {e}")
                return []
        
        def on_scan_complete(future):
            self._scan_in_progress = False
            try:
                result = future.result()
                # Call callback in main thread
                QTimer.singleShot(0, lambda: callback(result))
            except Exception as e:
                logger.error(f"Błąd w callback skanowania: {e}")
                QTimer.singleShot(0, lambda: callback([]))
        
        # Submit to thread pool
        future = self._executor.submit(scan_worker)
        future.add_done_callback(on_scan_complete)
    
    def _is_folder_visible(self, folder_name: str) -> bool:
        """Szybka sprawdzenie widoczności folderu."""
        if folder_name.startswith('.'):
            return False
        return folder_name not in {
            "__pycache__", ".git", ".svn", ".hg", "node_modules", 
            ".alg_meta", "tex", "textures", "texture", ".app_metadata"
        }
```

### 1.4 Usunięcie niepotrzebnego proxy model

**Problematyczny kod - niepotrzebna warstwa abstrakcji:**
```python
# Proxy model do filtrowania ukrytych folderów I wyświetlania statystyk
self.proxy_model = StatsProxyModel(self)
self.proxy_model.setSourceModel(self.model)
self.proxy_model.setFilterKeyColumn(0)
self.setup_folder_filtering()

# Użyj proxy model zamiast bezpośrednio file system model
self.folder_tree.setModel(self.proxy_model)
self.folder_tree.setRootIndex(
    self.proxy_model.mapFromSource(self.model.index(QDir.currentPath()))
)
```

**Poprawiony kod - bezpośrednie filtrowanie:**
```python
class DirectoryTreeManager:
    def __init__(self, ...):
        # Bezpośrednie użycie QFileSystemModel z custom filtrowaniem
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)
        
        # Custom filtering przez nameFilters zamiast proxy model
        self._setup_folder_filtering()
        
        # Bezpośrednie ustawienie modelu
        self.folder_tree.setModel(self.model)
        self.folder_tree.setRootIndex(self.model.index(QDir.currentPath()))
    
    def _setup_folder_filtering(self):
        """Prostsze filtrowanie bez proxy model."""
        # Użyj built-in możliwości QFileSystemModel
        hidden_patterns = [
            ".app_metadata", "__pycache__", ".git", ".svn", ".hg",
            "node_modules", ".alg_meta", "tex", "textures", "texture"
        ]
        
        # Set name filters to hide specific folders
        self.model.setNameFilters([f"*{pattern}" for pattern in hidden_patterns])
        self.model.setNameFilterDisables(False)  # Hide instead of disable
```

## 2. OPTYMALIZACJE WYDAJNOŚCI

### 2.1 Cache'owanie mapowania indeksów

**Problematyczny kod - O(n) operacji mapowania:**
```python
def _expand_folders_with_files(self, folders_with_files: List[str]):
    """Rozwija foldery zawierające pliki w drzewie."""
    try:
        for folder_path in folders_with_files:
            source_index = self.model.index(folder_path)  # Każda iteracja to nowy lookup
            if source_index.isValid():
                proxy_index = self.proxy_model.mapFromSource(source_index)
                if proxy_index.isValid():
                    self.folder_tree.expand(proxy_index)
    except Exception as e:
        logger.error(f"Błąd rozwijania folderów: {e}")
```

**Poprawiony kod - batch operations z cache:**
```python
def _expand_folders_with_files(self, folders_with_files: List[str]):
    """Rozwija foldery z optymalizacją batch."""
    if not folders_with_files:
        return
        
    try:
        # Batch cache lookup
        valid_indices = []
        
        # Phase 1: Collect valid indices
        for folder_path in folders_with_files:
            index = self.model.index(folder_path)
            if index.isValid():
                valid_indices.append(index)
        
        # Phase 2: Batch expand with UI updates disabled
        if valid_indices:
            self.folder_tree.setUpdatesEnabled(False)
            try:
                for index in valid_indices:
                    self.folder_tree.expand(index)
            finally:
                self.folder_tree.setUpdatesEnabled(True)
                
        logger.debug(f"Rozwinięto {len(valid_indices)} folderów")
        
    except Exception as e:
        logger.error(f"Błąd rozwijania folderów: {e}")
```

### 2.2 Batch UI updates

**Problematyczny kod - wielokrotne odświeżanie UI:**
```python
def set_current_directory(self, directory_path: str):
    # ... validation ...
    
    # 6 oddzielnych operacji UI - każda powoduje repaint
    self.folder_tree.setCurrentIndex(proxy_index)           # UI update 1
    self.folder_tree.scrollTo(proxy_index, ...)             # UI update 2
    self.folder_tree.selectionModel().select(...)           # UI update 3
    self.folder_tree.expand(proxy_index)                    # UI update 4
    self.invalidate_folder_cache(directory_path)            # Cache operation
    self._calculate_stats_async_silent(directory_path)      # Async operation
    self.folder_tree.update()                               # UI update 5
```

**Poprawiony kod - batch UI updates:**
```python
def set_current_directory(self, directory_path: str):
    """Ustawia katalog z batch UI updates."""
    if not directory_path or not os.path.isdir(directory_path):
        logger.warning(f"Nieprawidłowy katalog: {directory_path}")
        return
        
    directory_path = PathValidator.normalize_path(directory_path)
    self._current_working_directory = directory_path
    
    try:
        # Find index
        source_index = self.model.index(directory_path)
        if not source_index.isValid():
            logger.warning(f"Nie można znaleźć indeksu dla: {directory_path}")
            return
        
        # BATCH UI UPDATES - disable updates during operations
        self.folder_tree.setUpdatesEnabled(False)
        try:
            # Expand parent if needed
            parent_path = os.path.dirname(directory_path)
            parent_index = self.model.index(parent_path)
            if parent_index.isValid():
                self.folder_tree.expand(parent_index)
            
            # Set current, select, and scroll in one batch
            self.folder_tree.setCurrentIndex(source_index)
            self.folder_tree.selectionModel().select(
                source_index, 
                QItemSelectionModel.SelectionFlag.ClearAndSelect
            )
            self.folder_tree.expand(source_index)
            self.folder_tree.scrollTo(source_index, QTreeView.ScrollHint.PositionAtCenter)
            
        finally:
            # Single UI update at the end
            self.folder_tree.setUpdatesEnabled(True)
        
        # Background operations
        self.current_scan_path = directory_path
        self._invalidate_and_refresh_async(directory_path)
        
        logger.info(f"Ustawiono katalog: {directory_path}")
        
    except Exception as e:
        logger.error(f"Błąd ustawiania katalogu: {e}", exc_info=True)

def _invalidate_and_refresh_async(self, directory_path: str):
    """Background cache invalidation and stats refresh."""
    def background_work():
        try:
            # Cache operations in background
            self._folder_stats_cache.invalidate(directory_path)
            self.calculate_folder_statistics_async(directory_path)
        except Exception as e:
            logger.error(f"Błąd background refresh: {e}")
    
    # Submit to thread pool
    self._executor.submit(background_work)
```

## 3. REFAKTORYZACJA STRUKTURALNA

### 3.1 Uproszczony konstruktor

**Problematyczny kod - 76 linii konstruktora:**
```python
def __init__(self, folder_tree: QTreeView, parent_window):
    self.folder_tree = folder_tree
    self.parent_window = parent_window
    self.worker_factory = UIWorkerFactory()
    # ... 70 kolejnych linii inicjalizacji ...
    self._connect_signals()
    self.drag_drop_handler.setup_drag_and_drop_handlers()
```

**Poprawiony kod - krótki konstruktor z pomocniczymi metodami:**
```python
def __init__(self, folder_tree: QTreeView, parent_window):
    """Simplified constructor."""
    self.folder_tree = folder_tree
    self.parent_window = parent_window
    
    # Core components only
    self._init_core_components()
    self._setup_model()
    self._setup_ui()
    self._connect_signals()

def _init_core_components(self):
    """Initialize only essential components."""
    self.model = QFileSystemModel()
    self._folder_stats_cache = FolderStatsCache(max_entries=100, timeout_seconds=300)
    self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="DirTree")
    self._current_working_directory = None
    self._scan_in_progress = False

def _setup_model(self):
    """Setup file system model."""
    self.model.setRootPath(QDir.rootPath())
    self.model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)
    self.folder_tree.setModel(self.model)

def _setup_ui(self):
    """Setup UI components."""
    self.folder_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    self.folder_tree.setAcceptDrops(True)
    self.folder_tree.setDropIndicatorShown(True)
    
    # Hide columns except name
    for i in range(1, self.model.columnCount()):
        self.folder_tree.hideColumn(i)
    self.folder_tree.header().hide()

def _connect_signals(self):
    """Connect Qt signals."""
    self.folder_tree.clicked.connect(self._on_item_clicked)
    self.folder_tree.doubleClicked.connect(self._on_double_click)
    self.folder_tree.customContextMenuRequested.connect(self._show_context_menu)
```

### 3.2 Bezpośrednia implementacja event handlers

**Zamiast delegacji do event_handler, bezpośrednia implementacja:**
```python
def _on_item_clicked(self, index: QModelIndex):
    """Handle item click directly."""
    if not index.isValid():
        return
        
    folder_path = self.model.filePath(index)
    if folder_path and os.path.isdir(folder_path):
        self.set_current_directory(folder_path)
        # Notify parent window
        if hasattr(self.parent_window, 'on_directory_changed'):
            self.parent_window.on_directory_changed(folder_path)

def _on_double_click(self, index: QModelIndex):
    """Handle double click - expand/collapse."""
    if not index.isValid():
        return
        
    if self.folder_tree.isExpanded(index):
        self.folder_tree.collapse(index)
    else:
        self.folder_tree.expand(index)

def _show_context_menu(self, position):
    """Show context menu directly."""
    index = self.folder_tree.indexAt(position)
    if not index.isValid():
        return
        
    folder_path = self.model.filePath(index)
    menu = QMenu(self.folder_tree)
    
    # Add actions
    menu.addAction("Otwórz w eksploratorze", lambda: self._open_in_explorer(folder_path))
    menu.addAction("Pokaż statystyki", lambda: self.show_folder_statistics(folder_path))
    menu.addSeparator()
    menu.addAction("Utwórz folder", lambda: self._create_folder(folder_path))
    menu.addAction("Zmień nazwę", lambda: self._rename_folder(folder_path))
    menu.addAction("Usuń", lambda: self._delete_folder(folder_path))
    
    menu.exec(self.folder_tree.mapToGlobal(position))
```

### 3.3 Cleanup resources

**Dodanie proper cleanup:**
```python
def cleanup(self):
    """Cleanup resources on shutdown."""
    try:
        # Cancel ongoing operations
        self._scan_in_progress = False
        
        # Shutdown thread pool
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
        
        # Clear cache
        if hasattr(self, '_folder_stats_cache'):
            self._folder_stats_cache.clear()
        
        logger.debug("DirectoryTreeManager cleanup completed")
        
    except Exception as e:
        logger.error(f"Błąd podczas cleanup: {e}")

def __del__(self):
    """Destructor."""
    self.cleanup()
```

---

*Wersja: 1.0*
*Data: 2024-06-21*
*Priorytet: ⚫⚫⚫⚫ KRYTYCZNY - GRUNTOWNA REFAKTORYZACJA*