## Sposoby Zapisywania Danych Roboczych

Wybór metody zapisu danych roboczych zależy od etapu rozwoju aplikacji, ilości danych i wymagań dotyczących wydajności. Oto główne podejścia i rekomendacje:

---

### Gdzie Przechowywać Dane Robocze?

Najlepiej przechowywać dane robocze **wewnątrz folderu roboczego wybranego przez użytkownika**, w dedykowanym, być może ukrytym, podfolderze.

*   **Proponowana nazwa podfolderu:** `.app_metadata` (kropka na początku sugeruje ukryty folder w systemach Unix-like i jest dobrą konwencją).
*   **Zalety:**
    *   **Przenośność:** Jeśli użytkownik przeniesie folder roboczy, metadane przeniosą się razem z nim.
    *   **Samoopisujący się folder:** Wszystko dotyczące zbioru plików jest w jednym miejscu.
    *   **Unikanie konfliktów:** Każdy folder roboczy ma własny zestaw metadanych.
    *   **Łatwość backupu:** Backup folderu roboczego obejmuje metadane aplikacji.

---

### Jakie Dane Będziemy Zapisywać?

1.  **Metadane Par Plików:**
    *   Ścieżka do pliku archiwum (najlepiej względna do folderu roboczego).
    *   Ścieżka do pliku podglądu (najlepiej względna).
    *   Status "ulubione" (boolean).
    *   Ocena w gwiazdkach (integer, np. 0-5).
    *   Tag kolorystyczny (string, np. nazwa koloru lub kod hex).
    *   Rozmiar pliku archiwum (można odczytywać na bieżąco, cache'owanie może przyspieszyć).
    *   Data ostatniej modyfikacji (przydatna do synchronizacji).
2.  **Informacje o Plikach Niesparowanych:**
    *   Lista ścieżek do plików archiwów bez podglądów.
    *   Lista ścieżek do plików podglądów bez archiwów.
3.  **Cache Miniaturek (opcjonalnie, ale zalecane dla wydajności):**
    *   Jeśli generowanie miniaturek jest czasochłonne, warto je cache'ować.
4.  **Ustawienia Specyficzne dla Folderu Roboczego (opcjonalnie):**
    *   Np. ostatnio używane filtry, poziom skalowania kafelków.

---

### Formaty Zapisu Danych Roboczych (Metadane i Pliki Niesparowane)

#### Opcja 1: Pliki JSON (Dobra na początek, dla MVP i pierwszych etapów)

*   **Struktura:**
    *   W folderze `.app_metadata` można trzymać jeden główny plik, np. `metadata.json`.
    *   Plik zawierałby słownik, gdzie kluczem jest unikalny identyfikator pary (np. ścieżka względna pliku archiwum), a wartością jest obiekt z metadanymi. Osobna sekcja dla plików niesparowanych.

    ```json
    // .app_metadata/metadata.json
    {
      "file_pairs": {
        "subfolder1/archive1.zip": {
          "archive_path": "subfolder1/archive1.zip",
          "preview_path": "subfolder1/archive1.jpg",
          "is_favorite": true,
          "stars": 5,
          "color_tag": "red",
          "archive_size_bytes": 1024000 // Opcjonalnie
        },
        // ... więcej par
      },
      "unpaired_archives": [
        "orphans/lonely_archive.zip"
      ],
      "unpaired_previews": [
        "orphans/mystery_image.jpg"
      ]
    }
    ```

*   **Zalety:**
    *   Łatwy do implementacji w Pythonie (moduł `json`).
    *   Czytelny dla człowieka.
    *   Dobry dla struktur zagnieżdżonych.
*   **Wady:**
    *   **Wydajność przy dużych zbiorach:** Cały plik musi być wczytany/zapisany. Dla dziesiątek tysięcy plików może być wolne.
    *   **Ryzyko uszkodzenia:** Awaria podczas zapisu może uszkodzić plik (minimalizowane przez zapis do pliku tymczasowego).

#### Opcja 2: Baza Danych SQLite (Rekomendowana dla skalowalności i wydajności)

*   **Struktura:**
    *   W folderze `.app_metadata` tworzymy plik bazy danych, np. `metadata.sqlite`.
    *   Definiujemy tabele, np.:
        *   `file_pairs` (kolumny: `id` INTEGER PRIMARY KEY, `archive_path` TEXT UNIQUE, `preview_path` TEXT, `is_favorite` BOOLEAN, `stars` INTEGER, `color_tag` TEXT, `archive_size_bytes` INTEGER).
        *   `unpaired_files` (kolumny: `id` INTEGER PRIMARY KEY, `file_path` TEXT UNIQUE, `type` TEXT CHECK(type IN ('archive', 'preview'))).
    *   Indeksy na kolumnach używanych do filtrowania znacznie przyspieszą zapytania.

*   **Zalety:**
    *   **Wydajność:** SQLite jest bardzo szybki, pozwala na operacje na fragmentach danych.
    *   **Transakcyjność (ACID):** Chroni przed uszkodzeniem danych.
    *   **Obsługa dużych danych:** Radzi sobie z milionami rekordów.
    *   **Język SQL:** Potężne możliwości zapytań.
    *   **Wbudowany w Pythona:** Moduł `sqlite3`.
*   **Wady:**
    *   Nieco większy próg wejścia niż JSON (SQL lub ORM).
    *   Dane nie są bezpośrednio czytelne bez narzędzi (np. DB Browser for SQLite).

---

### Cache Miniaturek

*   Niezależnie od formatu metadanych, miniaturki najlepiej przechowywać jako osobne pliki obrazów.
*   **Lokalizacja:** `.app_metadata/thumbnails/`
*   **Nazewnictwo:** Używać hasha oryginalnej ścieżki pliku podglądu jako nazwy pliku miniaturki (np. `md5(subfolder1/archive1.jpg).png`) dla unikalności.
*   Metadane (JSON/SQLite) mogłyby przechowywać informację o wygenerowaniu miniaturki lub ścieżkę do niej.

---

### Ustawienia Globalne Aplikacji (niezależne od folderu roboczego)

*   Takie jak rozmiar okna, pozycja, globalne preferencje.
*   **PyQt6 oferuje `QSettings`:** Standardowy sposób przechowywania ustawień aplikacji (rejestr Windows, .plist macOS, .ini Linux).
*   Alternatywnie: prosty plik JSON w folderze konfiguracyjnym użytkownika (np. `~/.config/AppName/settings.json` lub `%APPDATA%/AppName/settings.json`).

---

### Rekomendacja dla Twojego Projektu (zgodnie z PRD)

1.  **Etap MVP i Początkowe Iteracje (Etapy 1-3, może 4):**
    *   Zacznij od **plików JSON** dla metadanych (`.app_metadata/metadata.json`).
    *   Cache miniaturek w `.app_metadata/thumbnails/`.
    *   Globalne ustawienia aplikacji za pomocą `QSettings`.
    *   **AI powinno być w stanie wygenerować kod do obsługi JSON.**

2.  **Późniejsze Etapy (Optymalizacja Wydajności, Etap 6-7):**
    *   Gdy wydajność JSON stanie się problemem, przejdź na **SQLite** (`.app_metadata/metadata.sqlite`).
    *   Przygotuj skrypt migracji danych z JSON do SQLite.
    *   **AI może pomóc w generowaniu schematu bazy danych, zapytań SQL lub kodu ORM.**

---

### Implementacja (dla AI)

*   **Klasa `MetadataManager`:** Odpowiedzialna za odczyt, zapis i modyfikację metadanych, hermetyzująca logikę dostępu (JSON/SQLite).
*   **Ścieżki względne:** Zawsze przechowuj ścieżki do plików jako względne do korzenia folderu roboczego.
*   **Obsługa błędów:** Solidna obsługa błędów przy operacjach I/O.
*   **Operacje atomowe (lub symulacja):** Przy zapisie JSON, używaj techniki "zapisz do tymczasowego, potem zamień". SQLite zapewnia to przez transakcje.

To podejście pozwoli zacząć szybko z prostszym rozwiązaniem i skalować je w miarę potrzeb, zgodnie z filozofią zwinną.