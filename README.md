# Zamiast C:\_cloud\_CFAB_3DHUB użyj:

cd /mnt/c/_cloud/_CFAB_3DHUB

# CFAB_3DHUB

Aplikacja do zarządzania i przeglądania sparowanych plików archiwów i odpowiadających im plików podglądu.

## Opis projektu

CFAB_3DHUB to aplikacja desktopowa w Pythonie z interfejsem użytkownika opartym na PyQt6. Służy do efektywnego zarządzania i przeglądania sparowanych plików archiwów (np. RAR, ZIP) i odpowiadających im plików podglądu (np. JPEG, PNG) znajdujących się w wybranym folderze roboczym i jego podfolderach.

## Wymagania systemowe

- Python 3.8 lub nowszy
- Biblioteki wymienione w pliku `requirements.txt`

## Instalacja

1. Sklonuj to repozytorium

2. Utwórz wirtualne środowisko Pythona:

   ```
   python -m venv .venv
   ```

3. Aktywuj wirtualne środowisko:

   - Windows:
     ```
     .venv\Scripts\activate
     ```
   - Linux/MacOS:
     ```
     source .venv/bin/activate
     ```

4. Zainstaluj wymagane biblioteki:
   ```
   pip install -r requirements.txt
   ```

## Uruchomienie aplikacji

Aby uruchomić aplikację, wykonaj następujące polecenie z głównego katalogu projektu:

```
python src/main.py
```

## Funkcjonalności

✅ **Aplikacja po kompletnej refaktoryzacji** - wszystkie główne funkcjonalności zaimplementowane:

- ✅ Wybór i skanowanie folderu roboczego
- ✅ Rekursywne skanowanie w poszukiwaniu par plików (archiwum + podgląd)
- ✅ Wyświetlanie podglądów jako kafelków w galerii z wirtualizacją
- ✅ Tagowanie plików (gwiazdki, kolory) z trwałymi metadanymi
- ✅ Operacje na plikach (usuwanie, przenoszenie, zmiana nazwy)
- ✅ Operacje zbiorcze na zaznaczonych plikach
- ✅ Filtrowanie i sortowanie według różnych kryteriów
- ✅ Drzewo katalogów z statystykami folderów
- ✅ Eksplorację plików z integracją narzędzi
- ✅ System workerów dla operacji w tle
- ✅ Cache z zaawansowaną optymalizacją
- ✅ Narzędzia specjalne (SBSAR extractor, konwersja WebP)

## 🏗️ Architektura po audycie

Aplikacja posiada teraz solidną architekturę warstwową:
- **UI Layer** - PyQt6 komponenty interfejsu
- **Controllers** - Logika kontrolerów (MainWindow, Gallery, FileOperations, Statistics)
- **Services** - Serwisy biznesowe (Scanning, FileOperations, ThreadCoordinator)
- **Logic** - Logika podstawowa (Scanner, MetadataManager, FilePariring)
- **Models** - Modele danych (FilePair, SpecialFolder)
- **Utils** - Narzędzia pomocnicze (PathValidator, Logging, ImageUtils)

## Struktura projektu

```
CFAB_3DHUB/
├── .venv/                  # Wirtualne środowisko Pythona
├── src/                    # Główny kod źródłowy aplikacji
│   ├── controllers/        # Kontrolery (Gallery, FileOperations, Statistics)
│   ├── services/           # Serwisy biznesowe (Scanning, FileOperations)
│   ├── logic/              # Logika podstawowa (Scanner, Metadata, Pairing)
│   ├── models/             # Modele danych (FilePair, SpecialFolder)
│   ├── ui/                 # Komponenty interfejsu użytkownika
│   ├── utils/              # Narzędzia pomocnicze (PathValidator, Logging)
│   ├── config/             # Konfiguracja aplikacji
│   ├── interfaces/         # Interfejsy i abstrakcje
│   ├── factories/          # Fabryki obiektów
│   └── resources/          # Zasoby (style, obrazy)
├── __tools/                # Narzędzia pomocnicze projektu
├── logs/                   # Logi aplikacji
├── _AUDIT_ARCHIVE/         # Archiwum audytu (analiza, poprawki, raporty)
├── requirements.txt        # Zależności projektu
├── pytest.ini             # Konfiguracja testów
└── run_app.py              # Główny punkt wejścia
```

## 📊 Archiwum audytu

W folderze `_AUDIT_ARCHIVE/` znajduje się kompletna dokumentacja przeprowadzonego audytu:
- **analysis/** - Analiza biznesowa i architektoniczna
- **corrections/** - Lista i implementacja wszystkich 19 poprawek  
- **reports/** - Raporty techniczne i analizy wydajności
- **temp_files/** - Pliki tymczasowe i narzędzia audytu

Wszystkie 19 zidentyfikowanych problemów zostało rozwiązane - aplikacja ma teraz solidną architekturę!

## Licencja

[Należy dodać informacje o licencji]

## Autorzy

CONCEPTFAB
