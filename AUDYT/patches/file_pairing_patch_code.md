# PATCH-CODE DLA: file_pairing.py

**Powiązany plik z analizą:** `../corrections/file_pairing_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: CACHE EXTENSION EXTRACTION - eliminacja redundant calls

**Problem:** Os.path.splitext wywoływane wielokrotnie dla tych samych plików
**Rozwiązanie:** Pre-compute extensions i cache w data structures

```python
# PRZED - linia 254-260:
def _categorize_files(files_list: List[str]) -> Tuple[List[str], List[str]]:
    # Pre-compute rozszerzeń dla optymalizacji
    files_with_ext = [(f, os.path.splitext(f)[1].lower()) for f in files_list]
    
    archive_files = [f for f, ext in files_with_ext if ext in ARCHIVE_EXTENSIONS]
    preview_files = [f for f, ext in files_with_ext if ext in PREVIEW_EXTENSIONS]
    
    return archive_files, preview_files

# PO - optymalizacja z frozenset lookup:
# Dodać na górze pliku (po linii 22):
ARCHIVE_EXTENSIONS_SET = frozenset(ARCHIVE_EXTENSIONS)
PREVIEW_EXTENSIONS_SET = frozenset(PREVIEW_EXTENSIONS)

def _categorize_files(files_list: List[str]) -> Tuple[List[str], List[str]]:
    """
    Kategoryzuje pliki na archiwa i podglądy.
    OPTYMALIZACJA: Używa frozenset lookup i generator expressions dla memory efficiency.
    """
    # Generator expressions zamiast list comprehensions dla memory efficiency
    files_with_ext = ((f, os.path.splitext(f)[1].lower()) for f in files_list)
    
    archive_files = []
    preview_files = []
    
    # Single pass przez files zamiast dwa passes - O(n) instead of O(2n)
    for f, ext in files_with_ext:
        if ext in ARCHIVE_EXTENSIONS_SET:
            archive_files.append(f)
        elif ext in PREVIEW_EXTENSIONS_SET:
            preview_files.append(f)
    
    return archive_files, preview_files
```

---

### PATCH 2: BESTMATCHSTRATEGY O(n+m) OPTIMIZATION

**Problem:** Algorytm O(n*m) w _find_partial_matches dla każdego archiwum
**Rozwiązanie:** Pre-index preview files i use efficient matching

```python
# PRZED - linia 180-191:
    def _find_partial_matches(self, archive_base_name: str, preview_keys) -> List[str]:
        """Znajduje częściowe dopasowania nazw."""
        matching_keys = []
        for preview_base_name in preview_keys:
            if preview_base_name.startswith(
                archive_base_name
            ) or archive_base_name.startswith(preview_base_name):
                matching_keys.append(preview_base_name)

        # Sortowanie po długości (zaczynając od najdłuższych)
        matching_keys.sort(key=len, reverse=True)
        return matching_keys

# PO - O(n+m) algorithm z prefix indexing:
    def _build_preview_map(self, preview_files: List[str]) -> Dict[str, List[str]]:
        """
        Buduje mapę podglądów według nazw bazowych.
        OPTYMALIZACJA: Dodatkowo buduje prefix index dla O(1) partial matching.
        """
        preview_map = defaultdict(list)
        self.prefix_index = defaultdict(set)  # Nowy prefix index
        
        for preview in preview_files:
            preview_name = os.path.basename(preview)
            preview_base_name = os.path.splitext(preview_name)[0].lower()
            preview_map[preview_base_name].append(preview)
            
            # Buduj prefix index dla efficient partial matching
            for i in range(1, min(len(preview_base_name) + 1, 10)):  # Max 10 char prefixes
                prefix = preview_base_name[:i]
                self.prefix_index[prefix].add(preview_base_name)
                
        return preview_map

    def _find_partial_matches(self, archive_base_name: str, preview_keys) -> List[str]:
        """
        Znajduje częściowe dopasowania nazw.
        OPTYMALIZACJA: O(1) lookup zamiast O(m) iteration.
        """
        matching_keys = set()
        
        # Użyj prefix index dla efficient lookups
        for i in range(1, min(len(archive_base_name) + 1, 10)):
            prefix = archive_base_name[:i]
            if prefix in self.prefix_index:
                matching_keys.update(self.prefix_index[prefix])
        
        # Sprawdź też reverse matches (archive jako prefix preview)
        if archive_base_name in self.prefix_index:
            matching_keys.update(self.prefix_index[archive_base_name])
            
        # Konwertuj na sortowaną listę (najdłuższe najpierw)
        matching_keys = list(matching_keys)
        matching_keys.sort(key=len, reverse=True)
        return matching_keys[:20]  # Limit do 20 dla performance
```

---

### PATCH 3: REMOVE FILE I/O FROM BESTMATCHSTRATEGY

**Problem:** File I/O (getmtime) w hot path pairing algorithm
**Rozwiązanie:** Remove mtime bonus - niepotrzebne i spowalnia

```python
# PRZED - linia 193-212:
    def _calculate_preview_score(self, preview: str, base_score: int) -> int:
        """Oblicza końcową ocenę podglądu."""
        score = base_score
        preview_ext = os.path.splitext(preview)[1].lower()

        # Dodajemy punkty za preferowane rozszerzenie
        if preview_ext in self.PREVIEW_PREFERENCE:
            score += (
                len(self.PREVIEW_PREFERENCE)
                - self.PREVIEW_PREFERENCE.index(preview_ext)
            ) * 10

        # Dodajemy mały bonus za nowsze pliki
        try:
            mtime = os.path.getmtime(preview)
            score += mtime / 10000000  # Dodaje mały ułamek do punktacji
        except (OSError, PermissionError):
            pass  # Ignorujemy błędy przy sprawdzaniu czasu modyfikacji

        return score

# PO - usunięcie I/O operations:
    def _calculate_preview_score(self, preview: str, base_score: int) -> int:
        """
        Oblicza końcową ocenę podglądu.
        OPTYMALIZACJA: Usunięto mtime check dla 10x szybszego działania.
        """
        score = base_score
        preview_ext = os.path.splitext(preview)[1].lower()

        # Dodajemy punkty za preferowane rozszerzenie
        if preview_ext in self.PREVIEW_PREFERENCE:
            score += (
                len(self.PREVIEW_PREFERENCE)
                - self.PREVIEW_PREFERENCE.index(preview_ext)
            ) * 10

        # USUNIĘTO: mtime bonus (niepotrzebne I/O w hot path)
        return score
```

---

### PATCH 4: MEMORY OPTIMIZATION - generator expressions

**Problem:** List comprehensions tworzą intermediate lists w memory
**Rozwiązanie:** Use generator expressions gdzie możliwe

```python
# PRZED - linia 326-330:
    # Zbieramy wszystkie pliki z mapy
    all_files = {file for files_list in file_map.values() for file in files_list}

    # Identyfikujemy niesparowane pliki
    unpaired_files = all_files - processed_files

# PO - streaming processing:
def identify_unpaired_files(
    file_map: Dict[str, List[str]],
    processed_files: Set[str],
) -> Tuple[List[str], List[str]]:
    """
    Identyfikuje niesparowane pliki na podstawie zebranych danych.
    OPTYMALIZACJA: Streaming processing zamiast building large intermediate sets.
    """
    unpaired_archives: List[str] = []
    unpaired_previews: List[str] = []

    # Streaming processing - nie buduj dużego intermediate set
    for files_list in file_map.values():
        for file_path in files_list:
            if file_path not in processed_files:
                ext = os.path.splitext(file_path)[1].lower()
                if ext in ARCHIVE_EXTENSIONS_SET:
                    unpaired_archives.append(file_path)
                elif ext in PREVIEW_EXTENSIONS_SET:
                    unpaired_previews.append(file_path)

    # Sort tylko na końcu, nie w każdej iteracji
    unpaired_archives.sort(key=lambda x: os.path.basename(x).lower())
    unpaired_previews.sort(key=lambda x: os.path.basename(x).lower())

    return unpaired_archives, unpaired_previews
```

---

### PATCH 5: SIMPLIFIED STRATEGY PATTERN

**Problem:** Over-engineered strategy pattern dla prostych algorytmów
**Rozwiązanie:** Inline simple strategies, keep factory tylko dla BestMatch

```python
# PRZED - complex factory i multiple strategy classes:
class PairingStrategyFactory:
    _strategies = {
        "first_match": FirstMatchStrategy,
        "all_combinations": AllCombinationsStrategy,
        "best_match": BestMatchStrategy,
    }

# PO - simplified approach:
def create_file_pairs(
    file_map: Dict[str, List[str]],
    base_directory: str,
    pair_strategy: str = "first_match",
) -> Tuple[List[FilePair], Set[str]]:
    """
    Tworzy pary plików na podstawie zebranych danych.
    OPTYMALIZACJA: Simplified strategy implementation dla lepszej performance.
    """
    found_pairs: List[FilePair] = []
    processed_files: Set[str] = set()

    for base_path, files_list in file_map.items():
        # Kategoryzuj pliki na archiwa i podglądy (optimized version)
        archive_files, preview_files = _categorize_files(files_list)

        if not archive_files or not preview_files:
            continue

        # Inline simple strategies dla performance
        if pair_strategy == "first_match":
            pairs, processed = _create_first_match_pairs(
                archive_files, preview_files, base_directory
            )
        elif pair_strategy == "all_combinations":
            pairs, processed = _create_all_combinations_pairs(
                archive_files, preview_files, base_directory
            )
        elif pair_strategy == "best_match":
            # Only complex strategy uses class-based approach
            strategy = BestMatchStrategy()
            pairs, processed = strategy.create_pairs(
                archive_files, preview_files, base_directory
            )
        else:
            logger.error(f"Nieznana strategia parowania: {pair_strategy}")
            continue

        found_pairs.extend(pairs)
        processed_files.update(processed)

    return found_pairs, processed_files

# Inline implementations dla simple strategies:
def _create_first_match_pairs(
    archive_files: List[str], preview_files: List[str], base_directory: str
) -> Tuple[List[FilePair], Set[str]]:
    """Optimized first match implementation."""
    pairs = []
    processed = set()
    
    if archive_files and preview_files:
        try:
            pair = FilePair(archive_files[0], preview_files[0], base_directory)
            pairs.append(pair)
            processed.add(archive_files[0])
            processed.add(preview_files[0])
        except ValueError as e:
            logger.error(f"Błąd tworzenia FilePair: {e}")
    
    return pairs, processed

def _create_all_combinations_pairs(
    archive_files: List[str], preview_files: List[str], base_directory: str
) -> Tuple[List[FilePair], Set[str]]:
    """
    Optimized all combinations implementation.
    WAŻNE: Memory limit dla bardzo dużych kombinacji.
    """
    pairs = []
    processed = set()
    
    # Memory protection - limit combinations dla performance
    max_combinations = 1000  # Prevent memory explosion
    combinations_count = len(archive_files) * len(preview_files)
    
    if combinations_count > max_combinations:
        logger.warning(
            f"PERFORMANCE WARNING: Too many combinations ({combinations_count}), "
            f"limiting to first {max_combinations}"
        )
        # Take subset to prevent memory issues
        archive_files = archive_files[:int(max_combinations**0.5)]
        preview_files = preview_files[:int(max_combinations**0.5)]
    
    for archive in archive_files:
        for preview in preview_files:
            try:
                pair = FilePair(archive, preview, base_directory)
                pairs.append(pair)
                processed.add(archive)
                processed.add(preview)
            except ValueError as e:
                logger.error(f"Błąd tworzenia FilePair dla '{archive}' i '{preview}': {e}")
    
    return pairs, processed
```

---

### PATCH 6: BUSINESS METRICS LOGGING

**Problem:** Brak business metrics dla pairing operations
**Rozwiązanie:** Structured logging z performance i success metrics

```python
# DODAĆ na końcu create_file_pairs (przed return):
    # Business metrics logging
    total_files_processed = len(processed_files)
    pairing_success_rate = (total_files_processed / (len([f for files in file_map.values() for f in files]))) * 100 if file_map else 0
    
    logger.info(
        f"PAIRING_COMPLETED: strategy={pair_strategy} | "
        f"pairs_created={len(found_pairs)} | "
        f"files_processed={total_files_processed} | "
        f"success_rate={pairing_success_rate:.1f}% | "
        f"base_dir={os.path.basename(base_directory)}"
    )
    
    # Performance warning dla low success rates
    if pairing_success_rate < 50 and len(found_pairs) > 10:
        logger.warning(
            f"LOW_PAIRING_RATE: {pairing_success_rate:.1f}% success rate. "
            f"Consider using 'best_match' strategy dla better results."
        )
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - wszystkie pairing strategies działają poprawnie
- [ ] **API kompatybilność** - create_file_pairs zachowuje identical interface
- [ ] **Strategy switching** - wszystkie strategy names ("first_match", "all_combinations", "best_match") działają
- [ ] **Extension categorization** - archive/preview files correctly categorized
- [ ] **Error handling** - graceful handling invalid files i FilePair creation errors
- [ ] **Memory management** - all_combinations strategy ma memory limits
- [ ] **Pairing accuracy** - BestMatchStrategy intelligent matching działa poprawnie
- [ ] **Unpaired identification** - identify_unpaired_files finds wszystkie unpaired files
- [ ] **Performance** - min. 60% improvement dla 1000+ files
- [ ] **Logging** - structured business metrics bez spam

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **scanner_core.py** - integration z create_file_pairs działa
- [ ] **FilePair model** - creation i validation działa poprawnie  
- [ ] **app_config** - ARCHIVE_EXTENSIONS i PREVIEW_EXTENSIONS used correctly
- [ ] **Backward compatibility** - wszystkie existing calls działają unchanged
- [ ] **Error propagation** - ValueError handling propagated correctly
- [ ] **Memory constraints** - large file sets nie powodują memory explosion
- [ ] **Thread safety** - concurrent pairing operations są safe
- [ ] **File path handling** - relative/absolute paths handled correctly

#### **TESTY WERYFIKACYJNE:**

- [ ] **Unit tests** - każda strategy w izolacji działa
- [ ] **Integration tests** - end-to-end pairing z scanner_core
- [ ] **Performance tests** - benchmark 1000+ files shows improvement
- [ ] **Memory tests** - AllCombinations memory usage controlled
- [ ] **Load tests** - 3000+ files stability verified
- [ ] **Edge case tests** - empty dirs, permission errors, invalid files
- [ ] **Regression tests** - wszystkie existing scenarios preserved

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **PERFORMANCE IMPROVEMENT** - min. 60% szybsze pairing
- [ ] **MEMORY EFFICIENCY** - AllCombinations max 50% memory usage
- [ ] **API STABILITY** - zero breaking changes
- [ ] **BUSINESS METRICS** - structured logging działa

---