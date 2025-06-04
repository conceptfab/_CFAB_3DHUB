# Dokument Wymagań Produktu (PRD) dla Aplikacji "CFAB_3DHUB"

**Wersja:** 1.0
**Data:** 2023-10-27
**Autor:** CONCEPTFAB

---

## 1. Wprowadzenie i Cel Produktu

Celem tego dokumentu jest zdefiniowanie wymagań dla aplikacji desktopowej w Pythonie z interfejsem użytkownika opartym na `PyQt6`, nazwanej roboczo "Przeglądarka Archiwów z Podglądem". Aplikacja ma na celu ułatwienie zarządzania i przeglądania sparowanych plików archiwów (np. RAR, ZIP) i odpowiadających im plików podglądu (np. JPEG, PNG) znajdujących się w wybranym folderze roboczym i jego podfolderach. Rozwój będzie prowadzony metodologią zwinną, zaczynając od MVP (Minimum Viable Product) i iteracyjnie dodając kolejne funkcjonalności. Dokument ten służy jako plan dla modeli AI wspomagających proces tworzenia kodu.

---

## 2. Główne Założenia i Cele Biznesowe

*   Umożliwienie efektywnego zarządzania dużymi kolekcjami plików archiwów i ich podglądów.
*   Intuicyjny interfejs użytkownika ułatwiający nawigację i organizację.
*   Zapewnienie modularności kodu dla łatwej rozbudowy i konserwacji.
*   Wysoka wydajność przy obsłudze folderów o dużej objętości (kilka TB).

---

## 3. Definicje Kluczowych Pojęć

*   **Folder Roboczy:** Główny folder wybrany przez użytkownika, w którym aplikacja będzie operować, włącznie ze wszystkimi jego podfolderami.
*   **Para Plików:** Zestaw składający się z pliku archiwum (np. `.rar`, `.zip`) i odpowiadającego mu pliku podglądu (np. `.jpg`, `.jpeg`, `.png`), które mają identyczną nazwę pliku (bez rozszerzenia).
*   **Klasa `FilePair`:** Dedykowana klasa w Pythonie odpowiedzialna za zarządzanie operacjami na Parze Plików, zapewniając spójność działań na obu plikach.
*   **Podgląd (Kafelek):** Element UI reprezentujący plik podglądu, wyświetlający miniaturę obrazu, nazwę pliku (bez rozszerzenia), rozmiar pliku archiwum oraz opcje tagowania.
*   **Tagi:** Metadane przypisywane do Par Plików (np. "ulubione", gwiazdki, kolory) umożliwiające ich kategoryzację i filtrowanie.

---

## 4. Użytkownicy Docelowi

*   Osoby pracujące z dużymi zbiorami archiwów graficznych, projektowych, dokumentacyjnych.
*   Archiwiści cyfrowi.
*   Graficy, projektanci, fotografowie.

---

## 5. Metodologia Rozwoju (Zwinna z Vibe Coding)

Rozwój aplikacji będzie przebiegał w iteracyjnych etapach, z częstym dostarczaniem działających przyrostów funkcjonalności. Każdy etap będzie obejmował:
1.  **Planowanie:** Definicja zakresu etapu na podstawie tego PRD.
2.  **Implementacja (z pomocą AI):** Generowanie kodu przez modele AI na podstawie szczegółowych instrukcji dla danego etapu/podetapu.
3.  **Testowanie:** Przygotowanie i wykonanie testów jednostkowych, integracyjnych i UI.
4.  **Przegląd i Refaktoryzacja:** Ocena kodu, wdrożenie poprawek, optymalizacja.
5.  **Dokumentacja:** Bieżące uzupełnianie dokumentacji technicznej i komentarzy w kodzie.
6.  **Raportowanie:** Regularne raporty o postępie, napotkanych problemach i proponowanych rozwiązaniach.

---

## 6. Wymagania Funkcjonalne (Podział na Etapy)

### Etap 0: Przygotowanie Środowiska i Fundamenty (AI: Inicjalizacja Projektu)

*   **Cel:** Stworzenie podstawowej struktury projektu i konfiguracji.
*   **Zadania dla AI:**
    1.  Stworzenie struktury folderów projektu (np. `src/`, `tests/`, `ui/`).
    2.  Inicjalizacja wirtualnego środowiska Pythona.
    3.  Instalacja `PyQt6` i innych niezbędnych bibliotek (np. `Pillow` do obsługi obrazów, `patool` lub `zipfile`/`rarfile` do archiwów).
    4.  Stworzenie pustego głównego okna aplikacji `PyQt6` (`QMainWindow`).
    5.  Zdefiniowanie szkieletu klasy `FilePair` (początkowo tylko przechowującej ścieżki do plików).
    6.  Konfiguracja podstawowego systemu logowania.
*   **Testy:** Uruchomienie pustego okna aplikacji.
*   **Dokumentacja:** `README.md` z instrukcją uruchomienia.
*   **Raportowanie:** Potwierdzenie gotowości środowiska.

---

### Etap 1: MVP - Skanowanie Folderu, Parowanie Plików i Podstawowe Wyświetlanie (AI: Rdzeń Logiki i UI)

*   **Cel:** Implementacja podstawowej funkcjonalności parowania plików i wyświetlania ich listy w UI.
*   **Podetapy:**
    1.  **Logika Biznesowa (AI):**
        *   Implementacja funkcji wyboru folderu roboczego przez użytkownika (np. `QFileDialog`).
        *   Implementacja funkcji rekursywnego skanowania wybranego folderu i jego podfolderów w poszukiwaniu plików archiwów i podglądów.
        *   Implementacja logiki parowania plików na podstawie identycznej nazwy (bez rozszerzenia) i obsługiwanych rozszerzeń.
        *   Rozbudowa klasy `FilePair` o przechowywanie ścieżki do pliku archiwum i pliku podglądu.
        *   Przechowywanie znalezionych Par Plików w pamięci (np. lista obiektów `FilePair`).
    2.  **Interfejs Użytkownika (AI):**
        *   Dodanie przycisku "Wybierz Folder Roboczy".
        *   Dodanie obszaru (np. `QListWidget` lub prosty `QTableView`) do wyświetlania listy nazw sparowanych plików (na razie tylko nazwy, bez miniaturek).
        *   Połączenie logiki skanowania z UI – po wybraniu folderu lista powinna się zapełnić.
*   **Testy (AI powinno pomóc w ich tworzeniu):**
    *   Jednostkowe: dla funkcji skanowania folderów.
    *   Jednostkowe: dla logiki parowania plików (różne przypadki, np. brak pary, wiele podglądów do jednego archiwum – na razie wybieramy pierwszy pasujący).
    *   Manualne UI: sprawdzenie wyboru folderu i wyświetlania listy.
*   **Dokumentacja:** Docstringi dla nowych funkcji i klas. Opis logiki parowania.
*   **Raportowanie:** Liczba znalezionych i sparowanych plików, ewentualne problemy z parowaniem.

---

### Etap 2: Wyświetlanie Podglądów (Kafelki) i Informacji (AI: Ulepszenie UI i Danych)

*   **Cel:** Wyświetlanie miniaturek podglądów w formie kafelków wraz z podstawowymi informacjami.
*   **Podetapy:**
    1.  **Logika Biznesowa (AI):**
        *   Rozbudowa klasy `FilePair` o przechowywanie miniatury podglądu (np. jako `QPixmap`) i rozmiaru pliku archiwum.
        *   Implementacja funkcji wczytywania obrazu podglądu i tworzenia jego miniatury.
        *   Implementacja funkcji pobierania rozmiaru pliku archiwum.
    2.  **Interfejs Użytkownika (AI):**
        *   Zmiana sposobu wyświetlania z listy nazw na galerię kafelków (np. użycie `QListView` z własnym delegatem lub `QGraphicsView`).
        *   Każdy kafelek powinien wyświetlać:
            *   Miniaturę pliku podglądu.
            *   Nazwę pliku (bez rozszerzenia).
            *   Rozmiar pliku archiwum (np. w KB/MB).
        *   Dodanie suwaka (np. `QSlider`) umożliwiającego skalowanie rozmiaru wyświetlanych kafelków.
*   **Testy (AI):**
    *   Jednostkowe: dla funkcji wczytywania obrazów i tworzenia miniatur.
    *   Jednostkowe: dla funkcji pobierania rozmiaru pliku.
    *   Manualne UI: sprawdzenie wyświetlania kafelków, informacji i działania suwaka skalowania.
*   **Dokumentacja:** Aktualizacja opisu klasy `FilePair`. Opis implementacji kafelków.
*   **Raportowanie:** Potwierdzenie działania wyświetlania kafelków, wydajność ładowania miniatur.

---

### Etap 3: Interakcje z Plikami i Podstawowe Tagowanie (AI: Funkcjonalności Użytkownika)

*   **Cel:** Umożliwienie otwierania plików archiwów, wyświetlania większego podglądu oraz podstawowego tagowania ("ulubione").
*   **Podetapy:**
    1.  **Logika Biznesowa (AI):**
        *   Implementacja funkcji otwierania pliku archiwum w domyślnym programie systemowym po kliknięciu na jego nazwę na kafelku.
        *   Rozbudowa klasy `FilePair` o atrybut `is_favorite` (boolean).
        *   Implementacja mechanizmu zapisu/odczytu metadanych (w tym tagu "ulubione") dla Par Plików. Początkowo może to być prosty plik JSON/XML w folderze roboczym lub w podfolderze `.app_data` (należy zadbać o wydajność i unikanie konfliktów przy zapisie). W przyszłości można rozważyć SQLite.
    2.  **Interfejs Użytkownika (AI):**
        *   Implementacja reakcji na kliknięcie nazwy pliku na kafelku (otwarcie archiwum).
        *   Implementacja wyświetlania większego podglądu obrazu po kliknięciu na miniaturę na kafelku (np. w osobnym oknie dialogowym lub dedykowanym obszarze UI).
        *   Dodanie ikony/przycisku "Ulubione" (np. gwiazdka) na każdym kafelku, umożliwiającej przełączanie statusu `is_favorite`. Wizualne oznaczenie ulubionych kafelków.
*   **Testy (AI):**
    *   Jednostkowe: dla funkcji otwierania archiwum.
    *   Jednostkowe: dla zapisu/odczytu statusu "ulubione".
    *   Manualne UI: testowanie interakcji z kafelkami (otwieranie, duży podgląd, tagowanie).
*   **Dokumentacja:** Opis mechanizmu zapisu metadanych.
*   **Raportowanie:** Status implementacji interakcji i tagowania.

---

### Etap 4: Zaawansowane Tagowanie i Filtrowanie (AI: Organizacja i Wyszukiwanie)

*   **Cel:** Dodanie zaawansowanych opcji tagowania (gwiazdki, kolory) i filtrowania widoku na ich podstawie.
*   **Podetapy:**
    1.  **Logika Biznesowa (AI):**
        *   Rozbudowa klasy `FilePair` o atrybuty dla gwiazdek (np. integer 0-5) i tagu kolorystycznego (np. string z nazwą koloru lub kodem hex).
        *   Aktualizacja mechanizmu zapisu/odczytu metadanych o nowe tagi.
        *   Implementacja logiki filtrowania listy wyświetlanych Par Plików na podstawie wybranych tagów (ulubione, gwiazdki, kolory).
    2.  **Interfejs Użytkownika (AI):**
        *   Dodanie kontrolek na kafelkach lub w menu kontekstowym do przypisywania gwiazdek (np. 5 klikalnych gwiazdek) i wyboru koloru etykiety (np. z predefiniowanej palety).
        *   Dodanie panelu filtrowania w UI (np. checkboxy, listy rozwijane) umożliwiającego wybór kryteriów filtrowania (np. "Pokaż tylko ulubione", "Pokaż z oceną >= 3 gwiazdki", "Pokaż z zieloną etykietą").
        *   Aktualizacja widoku kafelków w odpowiedzi na zmiany filtrów.
*   **Testy (AI):**
    *   Jednostkowe: dla logiki filtrowania.
    *   Manualne UI: testowanie przypisywania tagów i działania filtrów.
*   **Dokumentacja:** Aktualizacja opisu klasy `FilePair` i mechanizmu metadanych. Opis logiki filtrowania.
*   **Raportowanie:** Działanie zaawansowanego tagowania i filtrowania.

---

### Etap 5: Zarządzanie Strukturą Folderów i Plikami (AI: Operacje Plikowe)

*   **Cel:** Implementacja widoku drzewa katalogów, operacji na folderach oraz operacji na Parach Plików (w tym drag & drop).
*   **Podetapy:**
    1.  **Logika Biznesowa (AI):**
        *   Rozbudowa klasy `FilePair` o metody do:
            *   Zmiany nazwy (musi zmieniać nazwę obu plików: archiwum i podglądu).
            *   Usuwania (musi usuwać oba pliki).
            *   Przenoszenia (musi przenosić oba pliki do nowego folderu).
        *   Implementacja funkcji do tworzenia, usuwania i zmiany nazwy folderów w obrębie folderu roboczego.
    2.  **Interfejs Użytkownika (AI):**
        *   Dodanie widoku drzewa katalogów folderu roboczego (np. `QTreeView` z `QFileSystemModel` odpowiednio skonfigurowanym).
        *   Implementacja funkcji drag & drop dla Par Plików (reprezentowanych przez kafelki) do folderów w widoku drzewa (powoduje przeniesienie Pary Plików).
        *   Dodanie opcji w menu kontekstowym (dla folderów w drzewie i kafelków) lub przycisków do:
            *   Tworzenia nowego folderu.
            *   Zmiany nazwy folderu/Pary Plików.
            *   Usuwania folderu/Pary Plików.
*   **Testy (AI):**
    *   Jednostkowe: dla metod klasy `FilePair` (zmiana nazwy, usuwanie, przenoszenie).
    *   Jednostkowe: dla operacji na folderach.
    *   Integracyjne: sprawdzenie, czy operacje UI poprawnie wywołują logikę i modyfikują system plików.
    *   Manualne UI: testowanie D&D, menu kontekstowych i operacji na plikach/folderach.
*   **Dokumentacja:** Szczegółowy opis metod klasy `FilePair` zarządzających plikami. Opis interakcji D&D.
*   **Raportowanie:** Status implementacji zarządzania plikami i folderami. Potencjalne problemy z uprawnieniami do plików.

---

### Etap 6: Obsługa Plików Niesparowanych i Wydajność (AI: Uzupełnienia i Optymalizacja)

*   **Cel:** Wyświetlanie listy plików, które nie mają pary, oraz umożliwienie ich ręcznego dopasowania. Wstępna optymalizacja wydajności.
*   **Podetapy:**
    1.  **Logika Biznesowa (AI):**
        *   Modyfikacja logiki skanowania folderu, aby identyfikowała pliki archiwów bez podglądów i pliki podglądów bez archiwów.
        *   Implementacja mechanizmu ręcznego parowania (np. użytkownik wybiera plik archiwum i plik podglądu, a system tworzy z nich Parę Plików – może wymagać zmiany nazwy jednego z plików).
        *   Analiza potencjalnych wąskich gardeł wydajnościowych przy skanowaniu dużych folderów i ładowaniu danych (np. buforowanie miniatur, asynchroniczne ładowanie danych).
    2.  **Interfejs Użytkownika (AI):**
        *   Dodanie osobnego widoku/listy (np. w zakładce lub panelu) wyświetlającej pliki niesparowane (osobno archiwa, osobno podglądy).
        *   Dodanie interfejsu do ręcznego parowania (np. po wybraniu dwóch plików z list niesparowanych, przycisk "Sparuj").
*   **Testy (AI):**
    *   Jednostkowe: dla logiki identyfikacji plików niesparowanych.
    *   Manualne UI: testowanie wyświetlania list niesparowanych i funkcji ręcznego parowania.
    *   Wstępne testy wydajnościowe: pomiar czasu skanowania dużego folderu testowego.
*   **Dokumentacja:** Opis obsługi plików niesparowanych. Zidentyfikowane obszary do optymalizacji.
*   **Raportowanie:** Działanie funkcji dla niesparowanych plików. Wyniki wstępnych testów wydajnościowych.

---

### Etap 7: Refaktoryzacja, Optymalizacja i Finalizacja (AI: Poprawa Jakości i Przygotowanie do Wydania)

*   **Cel:** Przegląd i poprawa jakości kodu, dalsza optymalizacja wydajności, finalne testy i przygotowanie aplikacji.
*   **Podetapy:**
    1.  **Refaktoryzacja (AI może sugerować zmiany):**
        *   Przegląd całego kodu pod kątem czytelności, spójności i modularności (ścisłe oddzielenie UI od logiki biznesowej).
        *   Usprawnienie nazw zmiennych, funkcji, klas.
        *   Eliminacja powtórzeń kodu (DRY).
    2.  **Optymalizacja Wydajności (AI może pomóc w profilowaniu):**
        *   Implementacja zidentyfikowanych optymalizacji (np. asynchroniczne operacje, inteligentne cache'owanie danych i miniatur, optymalizacja zapytań do systemu plików, jeśli używany jest mechanizm indeksowania).
        *   Rozważenie użycia bazy danych SQLite do przechowywania metadanych i indeksu plików dla bardzo dużych kolekcji, zamiast plików JSON/XML, w celu przyspieszenia wyszukiwania i filtrowania.
    3.  **Testowanie (AI):**
        *   Kompleksowe testy regresji.
        *   Testy wydajnościowe na folderach o pojemności kilku TB (symulowane lub rzeczywiste).
        *   Testy użyteczności (manualne).
    4.  **Dokumentacja (AI):**
        *   Finalizacja dokumentacji technicznej.
        *   Uzupełnienie komentarzy w kodzie i docstringów.
        *   Przygotowanie podstawowej dokumentacji użytkownika (jeśli AI może w tym pomóc).
*   **Raportowanie:** Końcowy raport jakości kodu, wyniki testów wydajnościowych, status gotowości aplikacji.

---

## 7. Wymagania Niefunkcjonalne

*   **Wydajność:** Aplikacja musi działać płynnie i responsywnie, nawet podczas pracy z folderami zawierającymi dziesiątki tysięcy plików i zajmującymi kilka TB. Skanowanie folderów i ładowanie danych powinno być zoptymalizowane.
*   **Modularność:** Kod musi być podzielony na logiczne moduły (np. UI, logika biznesowa, obsługa plików, zarządzanie danymi), aby ułatwić rozwój, testowanie i konserwację. UI musi być wyraźnie oddzielone od logiki biznesowej.
*   **Użyteczność:** Interfejs użytkownika musi być intuicyjny i łatwy w obsłudze.
*   **Stabilność:** Aplikacja powinna być stabilna i odporna na błędy (np. gracefully handle brakujące pliki, błędy odczytu/zapisu).
*   **Rozszerzalność:** Architektura aplikacji powinna umożliwiać łatwe dodawanie nowych funkcjonalności w przyszłości (np. obsługa nowych formatów plików, integracja z chmurą).
*   **Platforma:** Aplikacja desktopowa dla systemu Windows (docelowo można rozważyć macOS, Linux).

---

## 8. Stos Technologiczny

*   **Język programowania:** Python (preferowana najnowsza stabilna wersja, np. 3.9+).
*   **Biblioteka UI:** `PyQt6`.
*   **Obsługa obrazów:** `Pillow` (PIL Fork).
*   **Obsługa archiwów:** `zipfile` (dla ZIP), `patool` lub `python-unrar` (dla RAR - uwzględnić licencje i zależności).
*   **System kontroli wersji:** Git.

---

## 9. Strategia Testowania (Zalecenia dla AI)

*   **Testy Jednostkowe (`unittest` lub `pytest`):**
    *   AI powinno generować testy jednostkowe dla każdej funkcji logiki biznesowej, metod klasy `FilePair`, funkcji parowania, filtrowania, operacji na plikach.
    *   Testy powinny pokrywać przypadki brzegowe i typowe scenariusze.
*   **Testy Integracyjne:**
    *   Testowanie interakcji między modułem UI a logiką biznesową.
    *   Sprawdzanie, czy akcje użytkownika w UI poprawnie wywołują odpowiednie funkcje w backendzie i czy dane są poprawnie przekazywane.
*   **Testy UI (początkowo manualne, AI może pomóc w scenariuszach):**
    *   Sprawdzanie poprawności wyświetlania elementów, responsywności, obsługi zdarzeń.
    *   W przyszłości można rozważyć narzędzia do automatyzacji testów UI dla PyQt (np. `pytest-qt`).
*   **Testy Wydajnościowe:**
    *   Manualne lub oskryptowane testy na dużych zbiorach danych (np. folder >1TB z tysiącami plików).
    *   Mierzenie czasu skanowania, ładowania, filtrowania.
*   **Pokrycie Kodu:** Dążenie do wysokiego pokrycia kodu testami.

---

## 10. Plan Dokumentacji (Zalecenia dla AI)

*   **Komentarze w Kodzie:** AI powinno generować zwięzłe i jasne komentarze wyjaśniające złożone fragmenty kodu.
*   **Docstringi:** Wszystkie moduły, klasy, funkcje i metody powinny mieć wyczerpujące docstringi w standardzie (np. Google, reStructuredText).
*   **`README.md`:** Powinien zawierać opis projektu, instrukcję instalacji, uruchomienia i podstawowego użytkowania.
*   **Dokumentacja Architektury:** Opis głównych komponentów systemu i ich interakcji (może być częścią `README` lub osobnym dokumentem).
*   **Ten PRD:** Będzie aktualizowany w miarę postępu prac.

---

## 11. Raportowanie Statusu i Komunikacja (Interakcja z AI)

*   **Częstotliwość:** Po zakończeniu każdego podetapu lub znaczącego zadania w ramach etapu, AI powinno przedstawić raport.
*   **Treść Raportu:**
    *   Zrealizowane zadania.
    *   Wygenerowany kod (link do commita/diffa).
    *   Utworzone/zaktualizowane testy.
    *   Napotkane problemy i sposób ich rozwiązania (lub prośba o pomoc).
    *   Sugestie dotyczące dalszych kroków lub potencjalnych ulepszeń.
    *   Status zgodności z PRD.
*   **Logowanie:** AI powinno intensywnie korzystać z systemu logowania do śledzenia swojego działania i ewentualnych błędów podczas generowania/testowania kodu.

---

## 12. Przyszłe Możliwości Rozbudowy (Poza MVP i kolejnymi etapami)

*   Obsługa dodatkowych formatów archiwów i podglądów.
*   Integracja z usługami chmurowymi do przechowywania plików.
*   Zaawansowane wyszukiwanie pełnotekstowe w metadanych lub nazwach plików.
*   Możliwość edycji metadanych EXIF dla obrazów.
*   System pluginów rozszerzających funkcjonalność.
*   Wersje dla innych systemów operacyjnych (macOS, Linux).
*   Automatyczne tagowanie na podstawie zawartości obrazu (AI).

---