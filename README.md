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

Aktualnie aplikacja znajduje się w fazie początkowej (Etap 0) i posiada tylko podstawową strukturę. Planowane funkcjonalności obejmują:

- Wybór folderu roboczego
- Rekursywne skanowanie w poszukiwaniu par plików (archiwum + podgląd)
- Wyświetlanie podglądów jako kafelków w interfejsie
- Tagowanie plików (ulubione, gwiazdki, kolory)
- Filtrowanie i sortowanie
- Podgląd i operacje na plikach

## Struktura projektu

```
CFAB_3DHUB/
├── .venv/                  # Wirtualne środowisko Pythona
├── src/                    # Główny kod źródłowy aplikacji
│   ├── models/             # Modele danych
│   ├── logic/              # Logika biznesowa
│   ├── ui/                 # Komponenty interfejsu użytkownika
│   └── utils/              # Narzędzia pomocnicze
├── tests/                  # Testy
├── ui_files/               # Pliki .ui z Qt Designer (opcjonalnie)
└── requirements.txt        # Zależności projektu
```

## Licencja

[Należy dodać informacje o licencji]

## Autorzy

CONCEPTFAB
