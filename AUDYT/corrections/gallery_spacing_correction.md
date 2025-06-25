**⚠️ KRYTYCZNE: Przed rozpoczęciem pracy zapoznaj się z ogólnymi zasadami refaktoryzacji, poprawek i testowania opisanymi w pliku [refactoring_rules.md](refactoring_rules.md).**

# 🔧 POPRAWKA: Stałe odstępy 20px między kaflami w galerii

## 📋 **ANALIZA PROBLEMU**

### **Zidentyfikowane miejsca wpływające na odstępy:**

1. **`gallery_tab.py:337`** - `tiles_layout.setSpacing(20)` ✅ **Już prawidłowe**
2. **`tile_styles.py:149`** - `TILE_MARGIN = 6` ❌ **Dodatkowy margines**
3. **`tile_styles.py:52`** - `margin: 6px` w CSS ❌ **Podwójny margines**
4. **`gallery_manager.py:958-961`** - Obliczenia geometrii uwzględniają spacing

### **Problem główny:**
Kafelki mają **podwójny margines**:
- Layout spacing: 20px (poprawne)
- CSS margin na kafelku: 6px (niepotrzebne)
- To daje łącznie: 20px + 6px + 6px = **32px** odstępu

## 🎯 **ROZWIĄZANIE**

### **1. Usunąć margines CSS z kafelków**
### **2. Zapewnić stały spacing 20px niezależnie od skali**  
### **3. Zaktualizować konfigurację**

## 📁 **PLIKI DO MODYFIKACJI**

### **File 1: `src/ui/widgets/tile_styles.py`**
### **File 2: `src/ui/widgets/tile_config.py`**
### **File 3: `src/ui/gallery_manager.py`** (weryfikacja)

## ✅ **OCZEKIWANY REZULTAT**

Po zastosowaniu poprawki:
- Odstępy między kaflami będą **dokładnie 20px**
- Spacing pozostanie **stały niezależnie od skali kafli**
- Nie będzie **podwójnych marginesów**
- Layout będzie **responsywny ale konsystentny**

## 🔄 **KOLEJNE KROKI**

1. Zastosować poprawki w plikach
2. Przetestować różne rozmiary kafli
3. Zweryfikować responsywność layoutu
4. Upewnić się że spacing pozostaje 20px przy skalowaniu