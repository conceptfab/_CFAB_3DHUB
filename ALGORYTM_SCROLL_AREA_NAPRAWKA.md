# NAPRAWKA ALGORYTMU SCROLL AREA W GALERII

## Problem

Aktualny algorytm obliczania wysokości scroll area generował zbyt długie obszary przewijania z powodu błędnego wzoru matematycznego.

## Stary algorytm (błędny)

```python
total_rows = math.ceil(total_items / cols)
total_height = total_rows * tile_height_spacing
```

Problem: Obliczał wysokość WSZYSTKICH wierszy zamiast tylko potrzebnej wysokości dla układu kafelków.

## Nowy algorytm (poprawny)

Zgodnie z propozycją użytkownika:

**Wzór matematyczny:**

- `n` = ilość par w folderze
- `y` = wysokość kafla (thumbnail)
- `x` = przerwa między kaflami (spacing + margines na tekst)
- `k` = ilość kolumn
- `z` = ilość par w kolumnie (zaokrąglony w górę)
- `A` = wysokość scroll area

```
z = ceil(n / k)
A = z * (y + x)
```

**UWAGA:** Pierwotnie wzór zawierał `+ y` na końcu, ale okazało się że dodaje za dużo miejsca na końcu galerii.

## Implementacja

Poprawki wprowadzone w `src/ui/gallery_manager.py`:

### 1. Metoda `update_gallery_view()` (linie ~530-540)

```python
# NOWY ALGORYTM wg propozycji użytkownika:
n = total_items  # ilość par w folderze
k = cols         # ilość kolumn
y = self.current_thumbnail_size  # wysokość kafla (thumbnail)
x = self.tiles_layout.spacing() + 40  # przerwa między kaflami

z = math.ceil(n / k)  # ilość par w kolumnie (zaokrąglony w górę)
total_height = z * (y + x)  # A = z * (y + x) - usunięto +y
```

### 2. Metoda `force_create_all_tiles()` (linie ~860-870)

```python
# Ustaw wysokość kontenera - NOWY ALGORYTM wg propozycji użytkownika
n = len(all_items)  # ilość par w folderze
k = cols  # ilość kolumn
y = self.current_thumbnail_size  # wysokość kafla (thumbnail)
x = self.tiles_layout.spacing() + 40  # przerwa między kaflami

z = math.ceil(n / k)  # ilość par w kolumnie (zaokrąglony w górę)
total_height = z * (y + x)  # A = z * (y + x) - usunięto +y
```

## Efekt

- **Precyzyjne obliczanie** wysokości scroll area
- **Eliminacja zbędnej przestrzeni** na dole galerii
- **Lepsze UX** - scroll area ma dokładnie potrzebny rozmiar
- **Spójność** między różnymi metodami obliczania wysokości

## Status

✅ **WPROWADZONA** - 2025-01-28

- Poprawiono obie metody obliczania wysokości
- Zachowano komentarze objaśniające algorytm
- Aplikacja testowana i działa poprawnie

## Zmienne w algorytmie

- `n` = `total_items` lub `len(all_items)`
- `k` = `cols` (obliczone z szerokości kontenera)
- `y` = `self.current_thumbnail_size`
- `x` = `self.tiles_layout.spacing() + 40`
- `z` = `math.ceil(n / k)`
- `A` = `z * (y + x)`

Algorytm zapewnia matematycznie poprawne obliczanie wysokości scroll area bez nadmiarowej przestrzeni.
