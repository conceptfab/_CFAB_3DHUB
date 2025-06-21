# 🔧 FRAGMENTY KODU - POPRAWKI KRYTYCZNE

## 1.1 POPRAWKA: processing_workers.py - Import QTimer

### 📍 Lokalizacja: `src/ui/delegates/workers/processing_workers.py:10`

#### **PRZED:**
```python
from PyQt6.QtCore import QObject, QThreadPool, pyqtSignal, pyqtSlot
```

#### **PO:**
```python
from PyQt6.QtCore import QObject, QThreadPool, QTimer, pyqtSignal, pyqtSlot
```

#### **Uzasadnienie:**
- Linia 503 używa `QTimer.singleShot()` bez importu
- Dodanie `QTimer` do istniejącego importu PyQt6.QtCore
- Minimalna zmiana - tylko dodanie jednego elementu do importu

---

## 1.2 POPRAWKA: file_operations_ui.py - Import QMessageBox

### 📍 Lokalizacja: `src/ui/file_operations_ui.py:8`

#### **PRZED:**
```python
from PyQt6.QtWidgets import QListWidget, QProgressDialog, QWidget
```

#### **PO:**
```python
from PyQt6.QtWidgets import QListWidget, QMessageBox, QProgressDialog, QWidget
```

#### **Uzasadnienie:**
- Linie 61, 85 używają `QMessageBox.critical()` i `QMessageBox.information()` bez importu
- Dodanie `QMessageBox` do istniejącego importu PyQt6.QtWidgets
- Zachowanie kolejności alfabetycznej w imporcie

---

## 1.3 POPRAWKA: main_window.py - Import QMessageBox

### 📍 Lokalizacja: `src/ui/main_window/main_window.py:7`

#### **PRZED:**
```python
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget
```

#### **PO:**
```python
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QMessageBox, QVBoxLayout, QWidget
```

#### **Uzasadnienie:**
- Linia 413 używa `QMessageBox.information()` bez importu
- Dodanie `QMessageBox` do istniejącego importu PyQt6.QtWidgets
- Zachowanie kolejności alfabetycznej w imporcie

---

## 1.4 POPRAWKA: worker_manager.py - Fix undefined worker

### 📍 Lokalizacja: `src/ui/main_window/worker_manager.py:317-326`

#### **ANALIZA PROBLEMU:**
Funkcja `start_bulk_delete_worker` ma błędną logikę - używa zmiennej `worker` która nie jest zdefiniowana w scope funkcji.

#### **PRZED:**
```python
def start_bulk_delete_worker(self, pairs_to_delete):
    """Uruchamia worker do usuwania wielu par plików."""
    # Połączenia dla ManuallyPairFilesWorker
    if isinstance(worker, ManuallyPairFilesWorker):
        worker.pairing_finished.connect(
            self.main_window.file_operations_coordinator.handle_manual_pairing_finished
        )
        worker.tile_widget_factory = (
            self.main_window.gallery_manager.create_tile_widget_for_pair
        )
```

#### **PO - OPCJA 1 (Usunięcie martwego kodu):**
```python
def start_bulk_delete_worker(self, pairs_to_delete):
    """Uruchamia worker do usuwania wielu par plików."""
    # TODO: Implementacja bulk delete worker
    # Aktualnie funkcja zawiera nieaktywny kod dla ManuallyPairFilesWorker
    pass
```

#### **PO - OPCJA 2 (Kompletna implementacja):**
```python
def start_bulk_delete_worker(self, pairs_to_delete):
    """Uruchamia worker do usuwania wielu par plików."""
    from src.ui.delegates.workers.bulk_workers import BulkDeleteWorker
    
    worker = BulkDeleteWorker(pairs_to_delete)
    
    # Połączenia sygnałów
    worker.deletion_finished.connect(
        self.main_window.file_operations_coordinator.handle_bulk_delete_finished
    )
    worker.deletion_progress.connect(
        self.main_window.progress_manager.update_progress
    )
    
    # Uruchomienie workera
    QThreadPool.globalInstance().start(worker)
    
    return worker
```

#### **REKOMENDACJA:** OPCJA 1 - usunięcie martwego kodu
**Uzasadnienie:**
- Kod jest niekompletny i błędny
- Brak implementacji BulkDeleteWorker
- Lepiej usunąć martwy kod niż naprawiać incomplete feature

---

## 1.5 POPRAWKA: special_folder.py - Import create_placeholder_pixmap

### 📍 Lokalizacja: `src/models/special_folder.py:13`

#### **PRZED:**
```python
from src.config import AppConfig
from src.utils.path_utils import normalize_path
```

#### **PO:**
```python
from src.config import AppConfig
from src.utils.image_utils import create_placeholder_pixmap
from src.utils.path_utils import normalize_path
```

#### **Uzasadnienie:**
- Linia 217 używa `create_placeholder_pixmap()` bez importu
- Funkcja istnieje w `src.utils.image_utils`
- Dodanie importu w poprawnym miejscu alfabetycznie

---

## 2.1 REFAKTORYZACJA: file_pairing.py - create_file_pairs

### 📍 Lokalizacja: `src/logic/file_pairing.py:24-końcowa`

#### **STRATEGIA REFAKTORYZACJI:**
Podział funkcji `create_file_pairs` na mniejsze, bardziej czytelne komponenty.

#### **NOWA STRUKTURA:**

```python
def create_file_pairs(
    file_map: Dict[str, List[str]],
    base_directory: str,
    pair_strategy: str = "first_match",
) -> Tuple[List[FilePair], Set[str]]:
    """
    Tworzy pary plików na podstawie zebranych danych.
    
    Zrefaktoryzowana wersja - używa strategy pattern dla lepszej czytelności.
    """
    strategy = _get_pairing_strategy(pair_strategy)
    return strategy.create_pairs(file_map, base_directory)


class PairingStrategy:
    """Bazowa klasa dla strategii parowania plików."""
    
    def create_pairs(self, file_map: Dict[str, List[str]], base_directory: str) -> Tuple[List[FilePair], Set[str]]:
        raise NotImplementedError


class FirstMatchStrategy(PairingStrategy):
    """Strategia: tylko pierwsza znaleziona para."""
    
    def create_pairs(self, file_map: Dict[str, List[str]], base_directory: str) -> Tuple[List[FilePair], Set[str]]:
        found_pairs: List[FilePair] = []
        processed_files: Set[str] = set()
        
        for base_path, files_list in file_map.items():
            pairs = self._create_pairs_for_base_path(base_path, files_list, base_directory)
            found_pairs.extend(pairs)
            processed_files.update(self._get_processed_files(pairs))
            
        return found_pairs, processed_files
    
    def _create_pairs_for_base_path(self, base_path: str, files_list: List[str], base_directory: str) -> List[FilePair]:
        """Tworzy pary dla pojedynczej ścieżki bazowej."""
        # Implementacja dla first_match strategy
        # ... (uproszczona logika z oryginalnej funkcji)
        pass
    
    def _get_processed_files(self, pairs: List[FilePair]) -> Set[str]:
        """Zwraca zbiór przetworzonych plików z par."""
        processed = set()
        for pair in pairs:
            processed.add(pair.archive_path)
            if pair.preview_path:
                processed.add(pair.preview_path)
        return processed


class AllCombinationsStrategy(PairingStrategy):
    """Strategia: wszystkie możliwe kombinacje archiwum-podgląd."""
    
    def create_pairs(self, file_map: Dict[str, List[str]], base_directory: str) -> Tuple[List[FilePair], Set[str]]:
        # Implementacja dla all_combinations strategy
        pass


class BestMatchStrategy(PairingStrategy):
    """Strategia: inteligentne parowanie po nazwach."""
    
    def create_pairs(self, file_map: Dict[str, List[str]], base_directory: str) -> Tuple[List[FilePair], Set[str]]:
        # Implementacja dla best_match strategy
        pass


def _get_pairing_strategy(strategy_name: str) -> PairingStrategy:
    """Factory function dla strategii parowania."""
    strategies = {
        "first_match": FirstMatchStrategy(),
        "all_combinations": AllCombinationsStrategy(),
        "best_match": BestMatchStrategy(),
    }
    
    if strategy_name not in strategies:
        logger.warning(f"Nieznana strategia '{strategy_name}', używam 'first_match'")
        strategy_name = "first_match"
    
    return strategies[strategy_name]
```

#### **KORZYŚCI REFAKTORYZACJI:**
- **Zmniejszona złożoność** - każda strategia w osobnej klasie
- **Lepsze testowanie** - łatwiejsze unit testy dla każdej strategii
- **Lepsza rozszerzalność** - łatwe dodawanie nowych strategii
- **Czytelność** - jasny podział odpowiedzialności

---

## 2.2 REFAKTORYZACJA: scanner_core.py - scan_folder_for_pairs

### 📍 Lokalizacja: `src/logic/scanner_core.py:266`

#### **STRATEGIA REFAKTORYZACJI:**
Podział funkcji na mniejsze komponenty i wprowadzenie ScanConfig.

#### **NOWA STRUKTURA:**

```python
@dataclass
class ScanConfig:
    """Konfiguracja dla skanowania folderów."""
    directory: str
    max_depth: int = -1
    use_cache: bool = True
    pair_strategy: str = "first_match"
    force_refresh_cache: bool = False
    
    def __post_init__(self):
        self.directory = normalize_path(self.directory)


class FolderScanner:
    """Klasa odpowiedzialna za skanowanie folderów i tworzenie par plików."""
    
    def __init__(self):
        self.cache_manager = ScannerCache()
    
    def scan_folder_for_pairs(
        self,
        config: ScanConfig,
        interrupt_check: Optional[Callable[[], bool]] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Tuple[List[FilePair], List[str], List[str], List[SpecialFolder]]:
        """
        Skanuje folder, tworzy pary i identyfikuje nieparowane pliki.
        Zrefaktoryzowana wersja z lepszą separacją odpowiedzialności.
        """
        # Sprawdzenie cache
        if config.use_cache and not config.force_refresh_cache:
            cached_result = self._try_get_from_cache(config)
            if cached_result:
                return cached_result
        
        # Skanowanie plików
        file_map = self._collect_files(config, interrupt_check, progress_callback)
        
        # Tworzenie par
        pairs, processed_files = create_file_pairs(
            file_map, config.directory, config.pair_strategy
        )
        
        # Identyfikacja nieparowanych plików
        unpaired_archives, unpaired_previews = self._identify_unpaired_files(
            file_map, processed_files
        )
        
        # Identyfikacja specjalnych folderów
        special_folders = self._identify_special_folders(config.directory)
        
        # Zapisanie do cache
        result = (pairs, unpaired_archives, unpaired_previews, special_folders)
        if config.use_cache:
            self._save_to_cache(config, result)
        
        return result
    
    def _try_get_from_cache(self, config: ScanConfig) -> Optional[Tuple]:
        """Próbuje pobrać wyniki z cache."""
        try:
            return self.cache_manager.get_cached_scan_result(
                config.directory, config.max_depth
            )
        except Exception as e:
            logger.debug(f"Cache miss dla {config.directory}: {e}")
            return None
    
    def _collect_files(
        self, 
        config: ScanConfig, 
        interrupt_check: Optional[Callable[[], bool]], 
        progress_callback: Optional[Callable[[int, str], None]]
    ) -> Dict[str, List[str]]:
        """Zbiera pliki z folderu."""
        return collect_files_streaming(
            config.directory,
            max_depth=config.max_depth,
            interrupt_check=interrupt_check,
            progress_callback=progress_callback,
        )
    
    def _identify_unpaired_files(
        self, file_map: Dict[str, List[str]], processed_files: Set[str]
    ) -> Tuple[List[str], List[str]]:
        """Identyfikuje nieparowane pliki."""
        unpaired_archives = []
        unpaired_previews = []
        
        for files_list in file_map.values():
            for file_path in files_list:
                if file_path not in processed_files:
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in ARCHIVE_EXTENSIONS:
                        unpaired_archives.append(file_path)
                    elif ext in PREVIEW_EXTENSIONS:
                        unpaired_previews.append(file_path)
        
        return unpaired_archives, unpaired_previews
    
    def _identify_special_folders(self, directory: str) -> List[SpecialFolder]:
        """Identyfikuje specjalne foldery (tex, textures)."""
        # Implementacja bez zmian z oryginalnej funkcji
        pass
    
    def _save_to_cache(self, config: ScanConfig, result: Tuple) -> None:
        """Zapisuje wyniki do cache."""
        try:
            self.cache_manager.cache_scan_result(
                config.directory, config.max_depth, result
            )
        except Exception as e:
            logger.warning(f"Nie udało się zapisać do cache: {e}")


# Funkcja wrapper dla backward compatibility
def scan_folder_for_pairs(
    directory: str,
    max_depth: int = -1,
    use_cache: bool = True,
    pair_strategy: str = "first_match",
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh_cache: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Tuple[List[FilePair], List[str], List[str], List[SpecialFolder]]:
    """Wrapper function dla backward compatibility."""
    config = ScanConfig(
        directory=directory,
        max_depth=max_depth,
        use_cache=use_cache,
        pair_strategy=pair_strategy,
        force_refresh_cache=force_refresh_cache,
    )
    
    scanner = FolderScanner()
    return scanner.scan_folder_for_pairs(config, interrupt_check, progress_callback)
```

#### **KORZYŚCI REFAKTORYZACJI:**
- **Zmniejszona złożoność** - funkcja główna ma <10 linii
- **Lepsze testowanie** - każdy komponent testowany osobno
- **Configurability** - ScanConfig object zamiast 7 parametrów
- **Separation of concerns** - cache/scan/pair logic rozdzielone
- **Backward compatibility** - zachowana kompatybilność API

---

## ✅ CHECKLISTA FUNKCJONALNOŚCI I ZALEŻNOŚCI

### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - czy wszystkie moduły nadal działają
- [ ] **Import compatibility** - czy nowe importy nie powodują konfliktów
- [ ] **Qt integration** - czy nowe importy Qt działają poprawnie
- [ ] **Error handling** - czy obsługa błędów nadal działa
- [ ] **Worker functionality** - czy system workerów działa po zmianach
- [ ] **File pairing logic** - czy logika parowania działa po refaktoryzacji
- [ ] **Scanning functionality** - czy skanowanie folderów działa po refaktoryzacji
- [ ] **Cache system** - czy cache działa po zmianach w scanner_core
- [ ] **Progress reporting** - czy reporting działa po refaktoryzacji
- [ ] **UI responsiveness** - czy UI nadal responsywne po zmianach

### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **PyQt6 imports** - czy wszystkie nowe importy Qt są poprawne
- [ ] **Internal dependencies** - czy zależności między modułami działają
- [ ] **Image utils dependency** - czy import create_placeholder_pixmap działa
- [ ] **Strategy pattern dependencies** - czy nowe klasy strategy działają
- [ ] **Scanner dependencies** - czy FolderScanner działa z istniejącymi componentami
- [ ] **Backward compatibility** - czy stare API nadal działa
- [ ] **Worker factory integration** - czy worker system nadal działa
- [ ] **Cache integration** - czy cache system nadal działa
- [ ] **Metadata integration** - czy metadata system nadal działa
- [ ] **Config integration** - czy app_config nadal działa z refactored code

### **TESTY WERYFIKACYJNE:**

- [ ] **Import test** - test że wszystkie importy działają
- [ ] **Unit tests** - testy dla każdej naprawionej funkcji
- [ ] **Integration tests** - testy integracji między komponentami
- [ ] **Regression tests** - testy że nic się nie zepsuło
- [ ] **Performance tests** - testy że wydajność nie spadła
- [ ] **UI tests** - testy że UI nadal działa
- [ ] **Worker tests** - testy że workery działają
- [ ] **Pairing logic tests** - testy logiki parowania
- [ ] **Scanner tests** - testy skanowania folderów
- [ ] **Cache tests** - testy systemu cache

### **KRYTERIA SUKCESU:**

- **WSZYSTKIE IMPORTY DZIAŁAJĄ** - 0 błędów NameError
- **WSZYSTKIE TESTY PASS** - 100% success rate
- **ZŁOŻONOŚĆ <C** - dla wszystkich refactored funkcji  
- **WYDAJNOŚĆ ZACHOWANA** - <5% impact na performance
- **BACKWARD COMPATIBILITY** - wszystkie istniejące API działają

---

*Fragmenty kodu przygotowane: 2025-06-21*  
*Status: GOTOWE DO IMPLEMENTACJI*