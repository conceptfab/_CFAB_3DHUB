1. Poprawki UI - porogress bary indetyczne


1. Zawartość (Tekst i/lub Ikona)
To najbardziej podstawowy element. Przycisk musi być co najmniej tak duży, aby zmieścić swój tekst i/lub ikonę, uwzględniając czcionkę i jej rozmiar. Właściwość minimumSizeHint() przycisku oblicza ten "rozsądny" minimalny rozmiar na podstawie zawartości.
2. Stylowanie za pomocą Arkuszy Stylów (QSS)
To jest kluczowy element, o który pytasz. Kiedy stosujesz style QSS, pewne właściwości bezpośrednio wpływają na obliczany rozmiar przycisku, efektywnie tworząc dla niego nowe "minimum". Najważniejsze z nich to:
padding (wypełnienie wewnętrzne): To jest przestrzeń wewnątrz obramowania przycisku, pomiędzy krawędzią a jego treścią (tekstem/ikoną). Zwiększenie padding bezpośrednio zwiększa minimalny rozmiar przycisku.
border (obramowanie): Grubość samego obramowania również dodaje się do całkowitego rozmiaru przycisku. Grubsze obramowanie to większy przycisk.
min-width i min-height: Możesz wprost zdefiniować minimalną szerokość i wysokość w QSS. Jest to najczęstszy sposób na "twarde" ustawienie minimalnych wymiarów za pomocą stylów.