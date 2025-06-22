# Zamiast C:\_cloud_CFAB_3DHUB użyj:

cd /mnt/c/\_cloud/\_CFAB_3DHUB

# CFAB_3DHUB

Aplikacja do zarządzania i przeglądania sparowanych plików archiwów i odpowiadających im plików podglądu.

## Opis projektu

CFAB_3DHUB to aplikacja desktopowa w Pythonie z interfejsem użytkownika opartym na PyQt6. Służy do efektywnego zarządzania i wydajnego przeglądania sparowanych plików archiwów (np. RAR, ZIP) i odpowiadających im plików podglądu (np. JPEG, PNG) znajdujących się w wybranym folderze roboczym i jego podfolderach.

## 🏗️ Architektura i Logika Biznesowa

### Główne Komponenty Aplikacji

**1. Moduł Skanowania (Scanner Core)**

- Skanowanie katalogów w poszukiwaniu plików archiwów i podglądów
- Identyfikacja par plików (archiwum ↔ podgląd)
- Generowanie metadanych i cache'owanie wyników
- Obsługa różnych formatów plików (RAR, ZIP, JPEG, PNG, etc.)

**2. Moduł Parowania (File Pairing)**

- Algorytmy dopasowywania plików archiwów do plików podglądu
- Walidacja integralności par plików
- Zarządzanie relacjami między plikami

**3. Moduł Galerii (Gallery UI)**

- Wyświetlanie tysięcy plików w formie galerii
- Generowanie miniaturek (thumbnails) w czasie rzeczywistym
- Virtual scrolling dla wydajności przy dużych zbiorach danych
- Drag & drop operacje na plikach

**4. Moduł Zarządzania Metadanymi**

- Cache'owanie metadanych plików
- Indeksowanie dla szybkiego wyszukiwania
- Synchronizacja metadanych z systemem plików

### 🔥 Krytyczne Wymagania Wydajnościowe

**Obsługa Dużych Zbiorów Danych:**

- Aplikacja musi obsługiwać katalogi z **dziesiątkami tysięcy plików**
- Galeria musi wyświetlać **tysiące miniaturek** bez lagów
- Skanowanie musi być **asynchroniczne** i nie blokować UI
- Cache'owanie musi być **inteligentne** i oszczędzać pamięć

**Wydajność UI:**

- **Responsywność** - UI nie może się zawieszać podczas operacji
- **Thread safety** - wszystkie operacje UI muszą być thread-safe
- **Memory management** - brak wycieków pamięci przy długotrwałym użytkowaniu
- **Virtual scrolling** - renderowanie tylko widocznych elementów

**Operacje na Plikach:**

- **Asynchroniczne skanowanie** - nie blokuje głównego wątku
- **Batch processing** - przetwarzanie plików w grupach dla wydajności
- **Intelligent caching** - cache'owanie wyników skanowania
- **Background workers** - operacje w tle z progress indicators

### 🎯 Główne Procesy Biznesowe

**1. Skanowanie Katalogów**

- Rekurencyjne przeszukiwanie folderów
- Identyfikacja plików archiwów i podglądów
- Generowanie mapy par plików
- Aktualizacja metadanych

**2. Parowanie Plików**

- Dopasowywanie plików na podstawie nazw
- Walidacja integralności par
- Obsługa różnych formatów plików
- Zarządzanie relacjami

**3. Prezentacja w Galerii**

- Renderowanie tysięcy miniaturek
- Virtual scrolling dla wydajności
- Filtrowanie i sortowanie
- Drag & drop operacje

**4. Zarządzanie Cache'em**

- Cache'owanie miniaturek
- Cache'owanie metadanych
- Inteligentne zarządzanie pamięcią
- Synchronizacja z systemem plików

### 🚨 Krytyczne Obszary dla Audytu

**Wydajność:**

- Algorytmy skanowania katalogów
- Generowanie miniaturek
- Virtual scrolling w galerii
- Zarządzanie pamięcią

**Thread Safety:**

- Operacje UI vs background workers
- Synchronizacja między wątkami
- Bezpieczne aktualizacje UI
- Obsługa cancel operations

**Memory Management:**

- Cache'owanie miniaturek
- Zarządzanie dużymi zbiorami danych
- Cleanup zasobów
- Memory leaks prevention

**User Experience:**

- Responsywność interfejsu
- Progress indicators
- Error handling
- Intuitive navigation

### 📊 Metryki Wydajnościowe

**Oczekiwane Parametry:**

- Skanowanie: **1000+ plików/sekundę**
- Galeria: **1000+ miniaturek** bez lagów
- Memory usage: **<500MB** dla dużych zbiorów
- UI responsiveness: **<100ms** dla operacji UI
- Startup time: **<5 sekund** dla dużych katalogów

### 🔧 Technologie i Zależności

**UI Framework:**

- PyQt6 - główny framework UI
- QThread - wielowątkowość
- QPixmap - zarządzanie obrazami
- QListView/QTreeView - komponenty galerii

**Przetwarzanie Plików:**

- asyncio - asynchroniczne operacje
- pathlib - operacje na ścieżkach
- PIL/Pillow - przetwarzanie obrazów
- zipfile/rarfile - obsługa archiwów

**Wydajność:**

- concurrent.futures - thread pools
- functools.lru_cache - cache'owanie
- weakref - zarządzanie pamięcią
- gc - garbage collection

## Autorzy

CONCEPTFAB
