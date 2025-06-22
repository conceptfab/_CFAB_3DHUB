# PROMPT: OPTYMALIZACJA PROCESÓW BIZNESOWYCH CFAB_3DHUB

## KONTEKST

CFAB_3DHUB to aplikacja desktopowa do zarządzania sparowanymi plikami archiwów i podglądów. Aplikacja przeszła kompletną refaktoryzację i ma solidną architekturę warstwową, ale wymaga optymalizacji procesów biznesowych dla lepszej wydajności i UX.

## CEL OPTYMALIZACJI

Zidentyfikuj i zoptymalizuj główne procesy biznesowe aplikacji, aby:

### 1️⃣ **WYDAJNOŚĆ** ⚡

- Optymalizacja czasu wykonania
- Redukcja zużycia pamięci
- Eliminacja wąskich gardeł (bottlenecks)
- Usprawnienie operacji I/O i przetwarzania danych
- Minimalizacja niepotrzebnych operacji

### 2️⃣ **STABILNOŚĆ** 🛡️

- Niezawodność działania aplikacji
- Proper error handling i recovery
- Thread safety i bezpieczeństwo wielowątkowe
- Eliminacja memory leaks i deadlocków
- Przewidywalność zachowania

### 3️⃣ **WYELIMINOWANIE OVER-ENGINEERING** 🎯

- Uproszczenie nadmiernie skomplikowanych rozwiązań
- Eliminacja niepotrzebnych abstrakcji i wzorców
- Redukcja liczby warstw i zależności
- Konsolidacja rozproszonej funkcjonalności
- Zastąpienie skomplikowanych rozwiązań prostszymi

### 4️⃣ **DODATKOWE CELE**

- Przyspieszenie operacji na dużych zbiorach plików (1000+ par)
- Poprawa responsywności UI
- Zwiększenie stabilności aplikacji
- Ułatwienie dodawania nowych funkcjonalności

## PROCESY DO OPTYMALIZACJI

### 1. PROCES SKANOWANIA I PAROWANIA

**Aktualny stan**: Rekursywne skanowanie z cache, algorytmy parowania z różnymi strategiami
**Problemy**: Wolne skanowanie dużych folderów, duże zużycie pamięci przy cache
**Zadanie**: Zaproponuj optymalizacje dla:

- Skanowania strumieniowego z progresywnym parowaniem
- Inteligentnego cache z LRU i TTL
- Równoległego przetwarzania podfolderów
- Optymalizacji algorytmów parowania

### 2. PROCES METADANYCH

**Aktualny stan**: Buforowanie z asynchronicznym zapisem, singleton per directory
**Problemy**: Potencjalne utraty danych przy crash, duplikacja w cache
**Zadanie**: Zaproponuj optymalizacje dla:

- Atomic writes z backup/rollback
- Kompresji metadanych
- Batch operations z transakcjami
- Lazy loading metadanych

### 3. PROCES OPERACJI NA PLIKACH

**Aktualny stan**: Workery z progress monitoring, walidacja przed operacjami
**Problemy**: Wolne operacje bulk, brak undo/redo
**Zadanie**: Zaproponuj optymalizacje dla:

- Pipeline processing dla bulk operations
- Systemu undo/redo z checkpointami
- Preflight validation z parallel processing
- Optimistic locking dla concurrent operations

### 4. PROCES GALERII

**Aktualny stan**: Wirtualizacja z cache miniaturek, batch processing
**Problemy**: Opóźnienia przy scroll, memory leaks w cache
**Zadanie**: Zaproponuj optymalizacje dla:

- Predictive loading miniaturek
- Adaptive cache sizing
- GPU acceleration dla thumbnail generation
- Lazy rendering z viewport culling

### 5. PROCES ZARZĄDZANIA WĄTKAMI

**Aktualny stan**: WorkerManager z pool, UnifiedBaseWorker pattern
**Problemy**: Potencjalne deadlocks, memory leaks przy workerach
**Zadanie**: Zaproponuj optymalizacje dla:

- Work stealing scheduler
- Priority-based worker queue
- Automatic resource cleanup
- Circuit breaker pattern dla failed workers

### 6. PROCES KONFIGURACJI

**Aktualny stan**: Singleton z property mapping, backward compatibility
**Problemy**: Synchronizacja między wątkami, validation overhead
**Zadanie**: Zaproponuj optymalizacje dla:

- Immutable configuration objects
- Schema validation z caching
- Hot reloading konfiguracji
- Configuration versioning

### 7. PROCES ZDARZEŃ UI

**Aktualny stan**: EventBus z delegacją, ViewRefreshManager
**Problemy**: Event storming, cascading updates
**Zadanie**: Zaproponuj optymalizacje dla:

- Event batching i debouncing
- Selective UI updates
- Event replay dla debugging
- Performance monitoring

## WYMAGANIA TECHNICZNE

### ARCHITEKTURA

- Zachowaj istniejącą architekturę warstwową (UI → Controllers → Services → Logic → Models)
- Użyj wzorców projektowych: Strategy, Factory, Observer, Command
- Implementuj dependency injection gdzie możliwe
- Zachowaj backward compatibility

### WYDAJNOŚĆ

- Czas odpowiedzi UI < 100ms dla operacji standardowych
- Memory usage < 500MB dla 1000 par plików
- CPU usage < 30% podczas normalnej pracy
- Startup time < 3 sekundy

### STABILNOŚĆ

- Zero memory leaks
- Graceful degradation przy błędach
- Automatic recovery z failed operations
- Comprehensive error handling

### TESTOWALNOŚĆ

- Unit tests dla każdej optymalizacji
- Performance benchmarks
- Memory profiling
- Integration tests dla workflow

## FORMAT WYJŚCIA

Dla każdego procesu podaj:

1. **ANALIZA PROBLEMÓW** - zidentyfikowane bottlenecky i problemy
2. **STRATEGIA OPTYMALIZACJI** - ogólne podejście do optymalizacji
3. **KONKRETNE ROZWIĄZANIA** - szczegółowe implementacje z kodem
4. **METRYKI SUKCESU** - mierzalne wskaźniki poprawy
5. **PLAN IMPLEMENTACJI** - etapy wdrożenia z priorytetami
6. **RYZYKA I MITIGACJE** - potencjalne problemy i sposoby ich uniknięcia

## DODATKOWE UWAGI

- Uwzględnij specyfikę aplikacji (duże zbiory plików, operacje I/O, UI responsiveness)
- Zaproponuj rozwiązania skalowalne (od 100 do 10000+ par plików)
- Rozważ trade-offs między wydajnością a złożonością kodu
- Uwzględnij doświadczenia użytkowników (UX improvements)
- Zaproponuj monitoring i alerting dla optymalizacji

## PRIORYTETYZACJA

### WYSOKI PRIORYTET (Krytyczne bottlenecky)

1. **WYDAJNOŚĆ** - Skanowanie dużych folderów, operacje bulk
2. **STABILNOŚĆ** - Memory leaks, thread safety
3. **OVER-ENGINEERING** - Nadmiernie skomplikowane komponenty

### ŚREDNI PRIORYTET (Ważne usprawnienia)

4. **UI RESPONSIVENESS** - Galeria, progress bars
5. **METADANE** - Zapisywanie i synchronizacja
6. **KONFIGURACJA** - Hot reloading, validation

### NISKI PRIORYTET (Nice to have)

7. **MONITORING** - Performance tracking
8. **DEBUGGING** - Event replay, logging

Zacznij od analizy najkrytyczniejszych procesów (skanowanie, metadane, operacje na plikach) i przejdź do mniej krytycznych w kolejnych iteracjach.
