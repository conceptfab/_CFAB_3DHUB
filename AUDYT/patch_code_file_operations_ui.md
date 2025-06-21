# 🔧 FRAGMENTY KODU - POPRAWKI file_operations_ui.py

## 1. BŁĘDY KRYTYCZNE

### 1.1 Eliminacja pustej fasady - bezpośrednia implementacja

**Problematyczny kod - pusta delegacja:**
```python
class FileOperationsUI:
    def __init__(self, parent_window):
        # 8 komponentów tylko do delegacji
        self.basic_operations = BasicFileOperations(...)
        self.drag_drop_handler = DragDropHandler(...)
        self.pairing_manager = ManualPairingManager(...)
        # ... i 5 kolejnych

    def rename_file_pair(self, file_pair, widget):
        """Deleguje operację rename do BasicFileOperations."""
        self.basic_operations.rename_file_pair(file_pair, widget)  # TYLKO DELEGACJA!

    def delete_file_pair(self, file_pair, widget):
        """Deleguje operację delete do BasicFileOperations."""
        self.basic_operations.delete_file_pair(file_pair, widget)  # TYLKO DELEGACJA!
```

**Poprawiony kod - bezpośrednia implementacja:**
```python
import logging
from typing import List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QListWidget, QProgressDialog, QWidget, QMessageBox, 
    QInputDialog, QMenu, QApplication
)

from src.controllers.file_operations_controller import FileOperationsController
from src.models.file_pair import FilePair

logger = logging.getLogger(__name__)


class FileOperationsManager(QObject):
    """
    Simplified file operations manager without over-engineering.
    Combines functionality of 8 previous components into one cohesive class.
    """
    
    # Signals for progress reporting
    operation_progress = pyqtSignal(int, str)  # percent, message
    operation_completed = pyqtSignal(str)      # success message
    operation_error = pyqtSignal(str)          # error message
    
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self.controller = FileOperationsController()
        
        # Simple thread pool for operations
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="FileOps")
        self._active_operations = set()
        
        # Connect signals to handlers
        self.operation_progress.connect(self._handle_progress)
        self.operation_completed.connect(self._handle_completion)
        self.operation_error.connect(self._handle_error)
    
    def rename_file_pair(self, file_pair: FilePair, widget: QWidget = None) -> bool:
        """Rename file pair - direct implementation."""
        try:
            current_name = file_pair.get_base_name()
            new_name, ok = QInputDialog.getText(
                self.parent_window,
                "Zmień nazwę",
                f"Nowa nazwa dla '{current_name}':",
                text=current_name
            )
            
            if not ok or not new_name or new_name == current_name:
                return False
            
            # Validate new name
            if not self._validate_filename(new_name):
                QMessageBox.warning(
                    self.parent_window,
                    "Błędna nazwa",
                    "Nazwa pliku zawiera niedozwolone znaki."
                )
                return False
            
            # Perform rename operation
            success = self.controller.rename_file_pair(file_pair, new_name)
            
            if success:
                logger.info(f"Renamed '{current_name}' to '{new_name}'")
                self.operation_completed.emit(f"Zmieniono nazwę na '{new_name}'")
                self._refresh_views()
                return True
            else:
                self.operation_error.emit("Nie udało się zmienić nazwy pliku")
                return False
                
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            self.operation_error.emit(f"Błąd zmiany nazwy: {str(e)}")
            return False

    def delete_file_pair(self, file_pair: FilePair, widget: QWidget = None) -> bool:
        """Delete file pair - direct implementation."""
        try:
            # Confirmation dialog
            reply = QMessageBox.question(
                self.parent_window,
                "Potwierdzenie usunięcia",
                f"Czy na pewno chcesz usunąć '{file_pair.get_base_name()}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return False
            
            # Perform delete operation
            success = self.controller.delete_file_pair(file_pair)
            
            if success:
                logger.info(f"Deleted file pair: {file_pair.get_base_name()}")
                self.operation_completed.emit(f"Usunięto '{file_pair.get_base_name()}'")
                self._refresh_views()
                return True
            else:
                self.operation_error.emit("Nie udało się usunąć pliku")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            self.operation_error.emit(f"Błąd usuwania: {str(e)}")
            return False
```

### 1.2 Konsolidacja komponentów w jednej klasie

**Kontynuacja klasy FileOperationsManager:**
```python
    def move_file_pair(self, file_pair: FilePair, target_folder: str) -> bool:
        """Move file pair to target folder - direct implementation."""
        try:
            if not os.path.exists(target_folder):
                self.operation_error.emit("Folder docelowy nie istnieje")
                return False
            
            # Create progress dialog
            progress = self._create_progress_dialog("Przenoszenie pliku...")
            progress.show()
            
            def move_operation():
                try:
                    success = self.controller.move_file_pair(file_pair, target_folder)
                    return success, None
                except Exception as e:
                    return False, str(e)
            
            # Execute in background
            future = self._executor.submit(move_operation)
            self._active_operations.add(future)
            
            # Handle completion
            def on_complete():
                self._active_operations.discard(future)
                progress.close()
                try:
                    success, error = future.result()
                    if success:
                        self.operation_completed.emit(f"Przeniesiono do {target_folder}")
                        self._refresh_views()
                    else:
                        self.operation_error.emit(error or "Błąd przenoszenia")
                except Exception as e:
                    self.operation_error.emit(f"Błąd operacji: {str(e)}")
            
            # Use timer for UI update
            QTimer.singleShot(100, on_complete)
            return True
            
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            self.operation_error.emit(f"Błąd przenoszenia: {str(e)}")
            return False

    def show_context_menu(self, file_pair: FilePair, widget: QWidget, position):
        """Show context menu - direct implementation."""
        menu = QMenu(widget)
        
        # Add actions
        rename_action = menu.addAction("Zmień nazwę")
        delete_action = menu.addAction("Usuń")
        menu.addSeparator()
        open_action = menu.addAction("Otwórz folder")
        
        # Connect actions
        rename_action.triggered.connect(lambda: self.rename_file_pair(file_pair, widget))
        delete_action.triggered.connect(lambda: self.delete_file_pair(file_pair, widget))
        open_action.triggered.connect(lambda: self._open_file_location(file_pair))
        
        # Show menu
        menu.exec(widget.mapToGlobal(position))

    def handle_drop_on_folder(self, urls: List, target_folder: str) -> bool:
        """Handle drag & drop operation - direct implementation."""
        try:
            if not urls:
                return False
                
            valid_files = []
            for url in urls:
                file_path = url.toLocalFile() if hasattr(url, 'toLocalFile') else str(url)
                if os.path.exists(file_path):
                    valid_files.append(file_path)
            
            if not valid_files:
                self.operation_error.emit("Nie znaleziono prawidłowych plików")
                return False
            
            # Create progress dialog
            progress = self._create_progress_dialog(f"Kopiowanie {len(valid_files)} plików...")
            progress.setMaximum(len(valid_files))
            progress.show()
            
            def copy_operation():
                try:
                    for i, file_path in enumerate(valid_files):
                        # Update progress
                        self.operation_progress.emit(
                            int((i / len(valid_files)) * 100),
                            f"Kopiowanie {os.path.basename(file_path)}..."
                        )
                        
                        # Perform copy
                        success = self.controller.copy_file_to_folder(file_path, target_folder)
                        if not success:
                            return False, f"Błąd kopiowania {os.path.basename(file_path)}"
                    
                    return True, None
                except Exception as e:
                    return False, str(e)
            
            # Execute in background
            future = self._executor.submit(copy_operation)
            self._active_operations.add(future)
            
            # Handle completion
            def on_complete():
                self._active_operations.discard(future)
                progress.close()
                try:
                    success, error = future.result()
                    if success:
                        self.operation_completed.emit(f"Skopiowano {len(valid_files)} plików")
                        self._refresh_views()
                    else:
                        self.operation_error.emit(error or "Błąd kopiowania")
                except Exception as e:
                    self.operation_error.emit(f"Błąd operacji: {str(e)}")
            
            QTimer.singleShot(100, on_complete)
            return True
            
        except Exception as e:
            logger.error(f"Error in drop operation: {e}")
            self.operation_error.emit(f"Błąd operacji: {str(e)}")
            return False
```

### 1.3 Usunięcie dead code i helper methods

**Dodanie helper methods i cleanup:**
```python
    def handle_manual_pairing(self, unpaired_archives: QListWidget, 
                             unpaired_previews: QListWidget, 
                             working_directory: str) -> bool:
        """Handle manual file pairing - direct implementation."""
        try:
            # Get selected items
            archive_items = unpaired_archives.selectedItems()
            preview_items = unpaired_previews.selectedItems()
            
            if not archive_items or not preview_items:
                QMessageBox.information(
                    self.parent_window,
                    "Wybierz pliki",
                    "Wybierz po jednym pliku z każdej listy do sparowania."
                )
                return False
            
            if len(archive_items) != 1 or len(preview_items) != 1:
                QMessageBox.warning(
                    self.parent_window,
                    "Zbyt wiele plików",
                    "Wybierz dokładnie po jednym pliku z każdej listy."
                )
                return False
            
            # Get file paths
            archive_path = archive_items[0].data(Qt.ItemDataRole.UserRole)
            preview_path = preview_items[0].data(Qt.ItemDataRole.UserRole)
            
            # Perform pairing
            success = self.controller.create_manual_pairing(
                archive_path, preview_path, working_directory
            )
            
            if success:
                self.operation_completed.emit("Sparowano pliki ręcznie")
                self._refresh_views()
                return True
            else:
                self.operation_error.emit("Nie udało się sparować plików")
                return False
                
        except Exception as e:
            logger.error(f"Error in manual pairing: {e}")
            self.operation_error.emit(f"Błąd sparowania: {str(e)}")
            return False

    # Helper methods
    def _create_progress_dialog(self, title: str) -> QProgressDialog:
        """Create standardized progress dialog."""
        progress = QProgressDialog(title, "Anuluj", 0, 0, self.parent_window)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setAutoClose(True)
        progress.setAutoReset(True)
        return progress

    def _validate_filename(self, filename: str) -> bool:
        """Validate filename for illegal characters."""
        illegal_chars = '<>:"/\\|?*'
        return not any(char in filename for char in illegal_chars)

    def _open_file_location(self, file_pair: FilePair):
        """Open file location in system explorer."""
        try:
            import subprocess
            import platform
            
            folder_path = os.path.dirname(file_pair.get_archive_path())
            
            if platform.system() == "Windows":
                subprocess.run(['explorer', folder_path])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(['open', folder_path])
            else:  # Linux
                subprocess.run(['xdg-open', folder_path])
                
        except Exception as e:
            logger.error(f"Error opening file location: {e}")
            self.operation_error.emit("Nie udało się otworzyć lokalizacji pliku")

    def _refresh_views(self):
        """Refresh application views after operations."""
        try:
            if hasattr(self.parent_window, 'refresh_all_views'):
                self.parent_window.refresh_all_views()
            elif hasattr(self.parent_window, 'refresh_gallery'):
                self.parent_window.refresh_gallery()
        except Exception as e:
            logger.error(f"Error refreshing views: {e}")

    # Signal handlers
    def _handle_progress(self, percent: int, message: str):
        """Handle progress updates."""
        logger.debug(f"Operation progress: {percent}% - {message}")

    def _handle_completion(self, message: str):
        """Handle operation completion."""
        logger.info(f"Operation completed: {message}")
        # Could show status bar message here

    def _handle_error(self, error_message: str):
        """Handle operation errors."""
        logger.error(f"Operation error: {error_message}")
        QMessageBox.critical(self.parent_window, "Błąd operacji", error_message)

    def cleanup(self):
        """Cleanup resources on shutdown."""
        try:
            # Cancel active operations
            for future in list(self._active_operations):
                future.cancel()
            self._active_operations.clear()
            
            # Shutdown thread pool
            self._executor.shutdown(wait=False)
            
            logger.debug("FileOperationsManager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def __del__(self):
        """Destructor."""
        self.cleanup()
```

### 1.4 Proper encapsulation

**Finalne metody publiczne API:**
```python
class FileOperationsManager(QObject):
    """
    Simplified file operations manager - public API.
    Replaces 8 over-engineered components with one cohesive class.
    """
    
    # === PUBLIC API ===
    
    def rename_file_pair(self, file_pair: FilePair, widget: QWidget = None) -> bool:
        """Rename a file pair."""
        # Implementation above
        
    def delete_file_pair(self, file_pair: FilePair, widget: QWidget = None) -> bool:
        """Delete a file pair."""
        # Implementation above
        
    def move_file_pair(self, file_pair: FilePair, target_folder: str) -> bool:
        """Move file pair to target folder."""
        # Implementation above
        
    def show_context_menu(self, file_pair: FilePair, widget: QWidget, position):
        """Show context menu for file operations."""
        # Implementation above
        
    def handle_drop_on_folder(self, urls: List, target_folder: str) -> bool:
        """Handle drag & drop operation."""
        # Implementation above
        
    def handle_manual_pairing(self, unpaired_archives: QListWidget, 
                             unpaired_previews: QListWidget, 
                             working_directory: str) -> bool:
        """Handle manual file pairing."""
        # Implementation above
        
    def cleanup(self):
        """Cleanup resources."""
        # Implementation above
    
    # === PRIVATE METHODS ===
    # All helper methods prefixed with _ are private
```

## 2. REFAKTORYZACJA STRUKTURALNA

### 2.1 Uproszczona integracja z main window

**Przykład użycia w main window:**
```python
class MainWindow:
    def __init__(self):
        # OLD - 8 komponentów
        # self.file_operations_ui = FileOperationsUI(self)
        
        # NEW - 1 komponent
        self.file_operations = FileOperationsManager(self)
        
        # Connect signals if needed
        self.file_operations.operation_completed.connect(self.show_status_message)
        self.file_operations.operation_error.connect(self.show_error_message)
    
    def show_file_context_menu(self, file_pair, widget, position):
        """Simplified call."""
        # OLD - przez 2 warstwy delegacji
        # self.file_operations_ui.show_file_context_menu(file_pair, widget, position)
        
        # NEW - bezpośrednie wywołanie
        self.file_operations.show_context_menu(file_pair, widget, position)
    
    def cleanup(self):
        """Cleanup on shutdown."""
        self.file_operations.cleanup()
```

### 2.2 Performance comparison

**Przed refaktoryzacją:**
```
MainWindow → FileOperationsUI → BasicFileOperations → Controller
(3 warstwy delegacji + 8 obiektów w pamięci)
```

**Po refaktoryzacji:**
```
MainWindow → FileOperationsManager → Controller
(1 warstwa + 1 obiekt w pamięci)
```

**Korzyści:**
- 66% redukcja call depth
- 87.5% redukcja obiektów w pamięci (8→1)
- 100% eliminacja pustych delegacji
- Lepsze error handling i progress reporting
- Łatwiejsze unit testing

---

*Wersja: 1.0*
*Data: 2024-06-21*
*Priorytet: ⚫⚫⚫⚫ KRYTYCZNY - KOMPLETNA REFAKTORYZACJA*
*Typ: OVER-ENGINEERING ELIMINATION*