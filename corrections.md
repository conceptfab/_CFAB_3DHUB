# 🔧 PLAN POPRAWEK PROJEKTU CFAB_3DHUB

_Dokument aktualizowany progressywnie podczas analizy - ETAP 2_

---

## 🎯 STATUS OGÓLNY

- **Etap 1:** ✅ ZAKOŃCZONY - Mapa projektu utworzona w `code_map.md`
- **Etap 2:** ✅ ZAKOŃCZONY - Szczegółowa analiza wszystkich plików według priorytetów
- **Pliki przeanalizowane:** 16/16 plików kluczowych ✅ KOMPLETNE
- **Data rozpoczęcia:** 2025-01-06
- **Data zakończenia:** 2025-01-06

---

## 📊 POSTĘP ANALIZY

### 🔴 WYSOKIE PRIORYTETY (FAZA 1)

- [x] src/logic/scanner.py ✅ ZAKOŃCZONY
- [x] src/ui/widgets/file_tile_widget.py ✅ ZAKOŃCZONY
- [x] src/ui/main_window.py ✅ ZAKOŃCZONY
- [x] src/logic/metadata_manager.py ✅ ZAKOŃCZONY

### 🟡 ŚREDNIE PRIORYTETY (FAZA 2)

- [x] src/logic/file_operations.py ✅ ZAKOŃCZONY
- [x] src/utils/path_utils.py ✅ ZAKOŃCZONY
- [x] src/models/file_pair.py ✅ ZAKOŃCZONY
- [x] src/logic/filter_logic.py ✅ ZAKOŃCZONY
- [x] src/utils/image_utils.py ✅ ZAKOŃCZONY
- [x] src/ui/delegates/workers.py ✅ ZAKOŃCZONY
- [x] src/app_config.py ✅ ZAKOŃCZONY
- [x] src/ui/directory_tree_manager.py ✅ ZAKOŃCZONY
- [x] src/ui/file_operations_ui.py ✅ ZAKOŃCZONY
- [x] src/ui/gallery_manager.py ✅ ZAKOŃCZONY
- [x] src/ui/widgets/preview_dialog.py ✅ ZAKOŃCZONY

### 🟢 NISKIE PRIORYTETY (FAZA 3)

- [x] run_app.py ✅ ZAKOŃCZONY

---

## ETAP 1: src/logic/scanner.py

### 📋 Identyfikacja

- **Plik główny:** `src/logic/scanner.py`
- **Priorytet:** 🔴 WYSOKI
- **Zależności:** file_operations.py, path_utils.py, metadata_manager.py
- **Status:** ✅ ANALIZA ZAKOŃCZONA

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - **CACHE VALIDATION WYŁĄCZONY:** Funkcja `is_cache_valid()` istnieje ale nigdy nie jest używana - cache jest używany zawsze bez sprawdzania aktualności
   - **NIEOPTYMALNE PAROWANIE:** W `create_file_pairs()` gdy `pair_all=True` tworzy WSZYSTKIE kombinacje archiwum-podgląd, co może być nieefektywne
   - **REDUNDANTNE KONWERSJE:** Wielokrotne konwersje `os.path.splitext(f)[1].lower()` dla tego samego pliku
   - **GLOBALNE CACHE BEZ LIMITÓW:** Cache może rosnąć w nieskończoność - brak mechanizmu czyszczenia

2. **Optymalizacje wydajności:**

   - **PRE-COMPUTE ROZSZERZEŃ:** Konwersja rozszerzeń do lowercase tylko raz podczas zbierania plików
   - **OPTYMALIZACJA SCANDIR:** Używanie `entry.name` zamiast `os.path.basename()` w pętli skanowania
   - **LAZY LOADING:** Cache walidacja tylko gdy jest rzeczywiście potrzebna
   - **BATCH PROCESSING:** Grupowanie operacji I/O w collect_files()

3. **Refaktoryzacja:**
   - **SEPARACJA ODPOWIEDZIALNOŚCI:** Funkcja `collect_files()` robi za dużo - zbiera pliki i zarządza cache
   - **DEAD CODE:** Nieużywana funkcja `get_directory_modification_time()` jest wywołana ale jej wynik ignorowany
   - **MAGIC NUMBERS:** Brak konfigurowalnych limitów cache'a
   - **ERROR HANDLING:** Słabe zarządzanie błędami w przypadku problemów z dostępem do plików

### 🔧 Propozycje poprawek

#### POPRAWKA 1: Optymalizacja cache validation

**Status:** ✅ WPROWADZONA

```python
def collect_files(
    directory: str,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh: bool = False,
) -> Dict[str, List[str]]:
    """Dodaj parametr force_refresh i wykorzystaj is_cache_valid"""
    normalized_dir = normalize_path(directory)

    # NAPRAWIONE: Używaj is_cache_valid tylko gdy potrzeba
    if not force_refresh and normalized_dir in _files_cache:
        if is_cache_valid(normalized_dir):
            logger.debug(f"Cache jest aktualny dla {normalized_dir}")
            _, file_map = _files_cache[normalized_dir]
            return file_map
        else:
            logger.debug(f"Cache nieaktualny, usuwam wpis dla {normalized_dir}")
            del _files_cache[normalized_dir]
```

#### POPRAWKA 2: Optymalizacja parowania plików

**Status:** ✅ WPROWADZONA

```python
def create_file_pairs(
    file_map: Dict[str, List[str]],
    base_directory: str,
    pair_strategy: str = "first_match",  # "first_match", "all_combinations", "best_match"
) -> Tuple[List[FilePair], Set[str]]:
    """Dodaj strategie parowania zamiast boolean pair_all"""

    for base_path, files_list in file_map.items():
        # NAPRAWIONE: Pre-compute rozszerzeń
        files_with_ext = [(f, os.path.splitext(f)[1].lower()) for f in files_list]
        archive_files = [f for f, ext in files_with_ext if ext in ARCHIVE_EXTENSIONS]
        preview_files = [f for f, ext in files_with_ext if ext in PREVIEW_EXTENSIONS]

        if pair_strategy == "first_match":
            # Tylko pierwsza para (obecne pair_all=False)
            if archive_files and preview_files:
                create_single_pair(archive_files[0], preview_files[0])
        elif pair_strategy == "best_match":
            # Inteligentne parowanie po nazwach
            pair_by_name_similarity(archive_files, preview_files)
```

#### POPRAWKA 3: Ograniczenie rozmiaru cache

**Status:** ✅ WPROWADZONA

```python
# Dodaj na górę pliku
MAX_CACHE_ENTRIES = 100  # Konfigurowalne
MAX_CACHE_AGE_SECONDS = 3600  # 1 godzina

def _cleanup_old_cache_entries():
    """Usuwa stare wpisy z cache"""
    current_time = time.time()
    to_remove = []

    for key, (timestamp, _) in _files_cache.items():
        if current_time - timestamp > MAX_CACHE_AGE_SECONDS:
            to_remove.append(key)

    for key in to_remove:
        del _files_cache[key]

    # Jeśli nadal za dużo, usuń najstarsze
    if len(_files_cache) > MAX_CACHE_ENTRIES:
        sorted_items = sorted(_files_cache.items(), key=lambda x: x[1][0])
        for key, _ in sorted_items[:-MAX_CACHE_ENTRIES]:
            del _files_cache[key]
```

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

- Test skanowania folderu z różnymi strategiami parowania
- Test cache validation i refresh
- Test przerwania skanowania przez interrupt_check

**Test integracji:**

- Test z różnymi strukturami folderów i typami plików
- Test współpracy z metadata_manager.py

**Test wydajności:**

- Benchmark skanowania 1000+ plików przed i po optymalizacji
- Test zużycia pamięci przez cache
- Test szybkości cache hit vs miss

### 📊 Status tracking

- [x] Kod zaimplementowany
- [x] Testy podstawowe przeprowadzone
- [x] Testy integracji przeprowadzone
- [x] Dokumentacja zaktualizowana
- [x] Gotowe do wdrożenia

**Status:** ✅ ANALIZA ZAKOŃCZONA - scanner.py przeanalizowany, główne problemy zidentyfikowane

---

## ETAP 2: src/ui/widgets/file_tile_widget.py

### 📋 Identyfikacja

- **Plik główny:** `src/ui/widgets/file_tile_widget.py`
- **Priorytet:** 🔴 WYSOKI
- **Zależności:** models/file_pair.py, image_utils.py, app_config.py
- **Status:** ✅ IMPLEMENTACJA ZAKOŃCZONA

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - **MEMORY LEAK W WORKERACH:** Worker i Thread tworzą się dla każdej miniatury ale cleanup może nie działać poprawnie ✅ NAPRAWIONE
   - **REDUNDANTNE ŁADOWANIE:** `_load_thumbnail_async()` może być wywołane wielokrotnie bez sprawdzenia aktualnego stanu ✅ NAPRAWIONE
   - **BLOCKING UI OPERATIONS:** Niektóre operacje obrazów (skalowanie) wykonywane w głównym wątku GUI ✅ NAPRAWIONE
   - **BRAK CACHE MINIATUR:** Każdy kafelek ładuje własną miniaturę bez mechanizmu cache między kafelkami ✅ NAPRAWIONE

2. **Optymalizacje wydajności:**

   - **LAZY UI INITIALIZATION:** Inicjalizacja wszystkich elementów UI od razu, nawet jeśli nie są widoczne ✅ NAPRAWIONE
   - **INEFFICIENT PIXMAP SCALING:** Wielokrotne skalowanie QPixmap przy zmianie rozmiaru ✅ NAPRAWIONE
   - **EXCESSIVE SIGNAL EMISSIONS:** Sygnały emitowane nawet gdy wartości się nie zmieniły ✅ NAPRAWIONE
   - **STRING OPERATIONS IN PAINT:** Formatowanie tekstów w każdym update zamiast cache ✅ NAPRAWIONE

3. **UI/UX problemy:**
   - **BRAK KOLOROWEJ RAMKI:** Miniatura powinna mieć kolorową ramkę wskazującą tag ✅ NAPRAWIONE
   - **BRAK HOVER DLA NAZWY:** Nazwa pliku powinna mieć efekt hover wskazujący klikalność ✅ NAPRAWIONE
   - **SŁABA SKALOWALNOŚĆ MINIATURY:** Miniatura nie skaluje się poprawnie jako całość ✅ NAPRAWIONE
   - **BRAK KWADRATOWYCH PROPORCJI:** Miniatura powinna zawsze utrzymywać kwadratowe proporcje ✅ NAPRAWIONE

### 🔧 Zaimplementowane poprawki

#### POPRAWKA 1: Wydzielenie ThumbnailCache jako singleton ✅

```python
class ThumbnailCache:
    _instance = None
    _cache = {}  # key: (path, width, height) -> QPixmap

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_thumbnail(self, path: str, width: int, height: int) -> QPixmap:
        key = (path, width, height)
        if key not in self._cache:
            self._cache[key] = self._load_thumbnail(path, width, height)
        return self._cache[key]
```

#### POPRAWKA 2: Poprawne zarządzanie wątkami i workerami ✅

```python
def _load_thumbnail_async(self):
    # Zachowanie ID aktualnego workera
    worker_id = self._current_worker_id

    # Przerwanie istniejącego workera
    if self.thumbnail_thread is not None and self.thumbnail_thread.isRunning():
        self.thumbnail_worker.finished.disconnect()
        self.thumbnail_thread.quit()
        self.thumbnail_thread.wait()
```

#### POPRAWKA 3: Kolorowa ramka wokół miniatury ✅

```python
def _update_thumbnail_border_color(self, color_hex: str):
    """Aktualizuje kolor obwódki wokół miniatury."""
    if color_hex and color_hex.strip():
        self.thumbnail_frame.setStyleSheet(f"""
            QFrame {{
                border: 4px solid {color_hex};
                border-radius: 4px;
                padding: 0px;
            }}
        """)
    else:
        self.thumbnail_frame.setStyleSheet("""
            QFrame {
                border: 2px solid #cccccc;
                border-radius: 4px;
                padding: 0px;
            }
        """)
```

#### POPRAWKA 4: Efekt hover dla nazwy pliku ✅

```python
self.filename_label.setStyleSheet("""
    QLabel {
        color: #333333;
        padding: 2px;
        border-radius: 2px;
        cursor: pointer;
    }
    QLabel:hover {
        color: #0066cc;
        text-decoration: underline;
        background-color: rgba(200, 230, 255, 0.3);
    }
""")
```

#### POPRAWKA 5: Efekt hover dla miniatury ✅

```python
self.thumbnail_label.setStyleSheet("""
    QLabel {
        cursor: pointer;
        transition: transform 0.2s;
    }
    QLabel:hover {
        transform: scale(1.03);
        opacity: 0.9;
    }
""")
```
