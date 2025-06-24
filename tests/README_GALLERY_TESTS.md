# 🧪 ŚRODOWISKO TESTOWE REALNEJ GALERII

## 📋 PRZEGLĄD

Środowisko testowe dla realnej galerii umożliwia automatyczne testowanie aplikacji CFAB_3DHUB na rzeczywistych danych z folderu `_test_gallery`.

### 📊 ZAWARTOŚĆ GALERII TESTOWEJ

- **321 plików WebP** (podglądy)
- **4 archiwa** w folderze `_bez_pary_` (ZIP, RAR)
- **643 pliki ogółem** w głównym folderze
- **Folder `.app_metadata`** z istniejącymi metadanymi

## 🚀 URUCHAMIANIE TESTÓW

### Szybki start

```bash
# Uruchom kompleksowy zestaw testów
python tests/run_gallery_tests.py

# Lub uruchom pojedyncze testy pytest
pytest tests/test_gallery_environment.py -v
```

### Testy pytest

```bash
# Wszystkie testy galerii
pytest tests/test_gallery_environment.py::TestRealGalleryEnvironment -v

# Konkretny test
pytest tests/test_gallery_environment.py::TestRealGalleryEnvironment::test_gallery_exists -v
```

## 📁 STRUKTURA PLIKÓW

```
tests/
├── test_gallery_environment.py    # Główny moduł testowy
├── run_gallery_tests.py          # Skrypt uruchamiający
└── README_GALLERY_TESTS.md       # Ta dokumentacja

_test_gallery/                    # Galeria testowa
├── *.webp                        # 321 plików podglądu
├── _bez_pary_/                   # Archiwa bez pary
│   ├── *.zip
│   └── *.rar
└── .app_metadata/                # Metadane
    └── metadata.json
```

## 🧪 RODZAJE TESTÓW

### 1. Testy Statystyk Galerii

- Sprawdza czy galeria testowa istnieje
- Liczy pliki WebP i archiwa
- Weryfikuje strukturę folderów

### 2. Testy Wydajności Skanowania

- Mierzy czas skanowania 321+ plików
- Sprawdza poprawność parowania
- Testuje algorytm parowania na realnych danych

### 3. Testy Wydajności GalleryManager

- Mierzy czas ładowania galerii
- Testuje tworzenie kafelków
- Sprawdza responsywność UI

### 4. Testy Tworzenia Kafelków

- Mierzy czas tworzenia pojedynczych kafelków
- Testuje próbkę 10-20 kafelków
- Sprawdza stabilność pamięci

### 5. Testy Użycia Pamięci

- Monitoruje wzrost użycia pamięci
- Sprawdza wycieki pamięci
- Testuje pod obciążeniem

## 📊 METRYKI WYDAJNOŚCI

### Oczekiwane Wyniki

| Test           | Metryka        | Oczekiwana Wartość        |
| -------------- | -------------- | ------------------------- |
| Skanowanie     | Czas           | < 10 sekund               |
| GalleryManager | Czas ładowania | < 5 sekund                |
| Kafelki        | Czas tworzenia | < 1 sekunda (10 kafelków) |
| Pamięć         | Wzrost         | < 500 MB                  |

### Przykładowe Wyniki

```
📊 WYNIKI TESTÓW:
✅ gallery_statistics: OK
   📊 Pliki WebP: 321
   📊 Archiwa: 4

✅ scan_performance: OK
   📊 Skanowanie: 2.45ms
   📊 Znalezione pary: 45

✅ gallery_performance: OK
   📊 Galeria: 1.23ms
   📊 Pamięć: 45.67MB

✅ tile_performance: OK
   📊 Kafelki: 0.89ms
   📊 Średni czas/kafelek: 0.089ms

✅ memory_usage: OK
   📊 Wzrost pamięci: 23.45MB
```

## 🔧 KONFIGURACJA

### Wymagania Systemowe

- **Python 3.8+**
- **PyQt6**
- **psutil** (opcjonalnie, dla monitorowania pamięci)
- **pytest** (dla testów jednostkowych)

### Instalacja Zależności

```bash
pip install psutil pytest
```

### Konfiguracja Galerii Testowej

1. **Utwórz folder `_test_gallery`** w głównym katalogu projektu
2. **Dodaj pliki WebP** (podglądy) do głównego folderu
3. **Utwórz folder `_bez_pary_`** i dodaj archiwa (ZIP, RAR)
4. **Opcjonalnie** dodaj folder `.app_metadata` z metadanymi

## 🐛 ROZWIĄZYWANIE PROBLEMÓW

### Błędy Częste

#### 1. "Galeria testowa nie istnieje"

```bash
# Utwórz folder
mkdir _test_gallery
# Dodaj pliki testowe
```

#### 2. "Brak plików WebP"

```bash
# Dodaj pliki .webp do _test_gallery
cp /ścieżka/do/plików/*.webp _test_gallery/
```

#### 3. "Import error"

```bash
# Sprawdź czy jesteś w głównym katalogu projektu
cd /ścieżka/do/CFAB_3DHUB
# Uruchom testy
python tests/run_gallery_tests.py
```

#### 4. "QApplication error"

```bash
# Upewnij się że PyQt6 jest zainstalowane
pip install PyQt6
```

### Debugowanie

#### Włączanie Szczegółowych Logów

```python
# W test_gallery_environment.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Testowanie Pojedynczych Komponentów

```python
# Test tylko skanowania
env = RealGalleryTestEnvironment()
env.setup_test_environment()
stats = env.test_full_gallery_scan()
print(stats)
```

## 📈 ROZSZERZANIE TESTÓW

### Dodawanie Nowych Testów

1. **Dodaj metodę testową** do klasy `RealGalleryTestEnvironment`
2. **Dodaj test pytest** do klasy `TestRealGalleryEnvironment`
3. **Zaktualizuj** `run_comprehensive_test_suite()`

### Przykład Nowego Testu

```python
def test_custom_performance(self) -> Dict[str, float]:
    """Test niestandardowej wydajności"""
    start_time = time.time()

    # Wykonaj test
    result = self.perform_custom_operation()

    test_time_ms = (time.time() - start_time) * 1000

    return {
        'operation_time_ms': test_time_ms,
        'result': result
    }
```

## 🔄 CI/CD INTEGRACJA

### GitHub Actions

```yaml
name: Gallery Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install psutil pytest
      - name: Run gallery tests
        run: python tests/run_gallery_tests.py
```

### Lokalny CI

```bash
#!/bin/bash
# run_gallery_tests.sh

echo "🧪 Uruchamianie testów galerii..."
python tests/run_gallery_tests.py

if [ $? -eq 0 ]; then
    echo "✅ Testy przeszły pomyślnie"
    exit 0
else
    echo "❌ Testy nie przeszły"
    exit 1
fi
```

## 📝 NOTATKI ROZWOJOWE

### Optymalizacje

- **Progressive loading** dla dużych galerii
- **Cache miniaturek** dla szybszych testów
- **Memory monitoring** dla wykrywania wycieków
- **Parallel testing** dla skrócenia czasu

### Limity

- **Testy UI** wymagają QApplication
- **Pamięć** może wzrosnąć przy dużych galeriach
- **Czas wykonania** zależy od sprzętu

### Przyszłe Rozszerzenia

- **Benchmarking** różnych algorytmów
- **Stress testing** z 1000+ plików
- **Regression testing** dla wydajności
- **Automated reporting** z wykresami

---

**📧 Kontakt:** W przypadku problemów z testami, sprawdź logi i dokumentację.
