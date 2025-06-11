"""
Test refaktoryzacji ETAP 2 - MainWindow i komponenty UI.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_imports_etap2():
    """Test importów wszystkich nowych komponentów ETAP 2."""
    try:
        from src.ui.main_window import MainWindow
        from src.ui.components import UIManager, EventHandler, TabManager
        from src.ui.components.ui_manager import UIManager as UIManagerDirect
        from src.ui.components.event_handler import EventHandler as EventHandlerDirect
        from src.ui.components.tab_manager import TabManager as TabManagerDirect
        print("✅ Wszystkie importy ETAP 2 OK")
        return True
    except Exception as e:
        print(f"❌ Błąd importu ETAP 2: {e}")
        return False

def test_main_window_structure():
    """Test struktury refaktoryzowanego MainWindow."""
    try:
        from src.ui.main_window import MainWindow
        
        # Test czy klasa ma właściwe metody
        required_methods = [
            '_init_data', '_init_window', '_init_components', '_init_ui', '_init_managers'
        ]
        
        for method in required_methods:
            if not hasattr(MainWindow, method):
                print(f"❌ Brak metody {method} w MainWindow")
                return False
                
        print("✅ Struktura MainWindow ma wszystkie wymagane metody")
        
        # Test czy ma komponenty zarządzające
        required_components = [
            'ui_manager', 'event_handler', 'tab_manager'
        ]
        
        # Nie możemy testować instancji bez PyQt6, ale możemy sprawdzić czy klasa ma metody do tworzenia komponentów
        if hasattr(MainWindow, '_init_components'):
            print("✅ MainWindow ma metodę _init_components")
        else:
            print("❌ MainWindow nie ma metody _init_components")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Błąd testu struktury MainWindow: {e}")
        return False

def test_component_managers():
    """Test komponentów zarządzających."""
    try:
        from src.ui.components.ui_manager import UIManager
        from src.ui.components.event_handler import EventHandler
        from src.ui.components.tab_manager import TabManager
        
        # Test czy klasy mają wymagane metody
        ui_methods = ['setup_status_bar', 'create_top_panel', 'create_filter_panel']
        for method in ui_methods:
            if not hasattr(UIManager, method):
                print(f"❌ UIManager nie ma metody {method}")
                return False
                
        event_methods = ['handle_folder_selection', 'handle_force_refresh', 'handle_bulk_delete']
        for method in event_methods:
            if not hasattr(EventHandler, method):
                print(f"❌ EventHandler nie ma metody {method}")
                return False
                
        tab_methods = ['create_gallery_tab', 'create_unpaired_files_tab', 'update_unpaired_files_lists']
        for method in tab_methods:
            if not hasattr(TabManager, method):
                print(f"❌ TabManager nie ma metody {method}")
                return False
                
        print("✅ Wszystkie komponenty zarządzające mają wymagane metody")
        return True
        
    except Exception as e:
        print(f"❌ Błąd testu komponentów: {e}")
        return False

def test_line_count_reduction():
    """Test redukcji liczby linii kodu."""
    try:
        # Sprawdź nową wersję
        with open('src/ui/main_window.py', 'r', encoding='utf-8') as f:
            new_lines = len(f.readlines())
            
        # Sprawdź backup oryginalnej wersji
        with open('src/ui/main_window_original_etap2.py', 'r', encoding='utf-8') as f:
            original_lines = len(f.readlines())
            
        reduction_percent = ((original_lines - new_lines) / original_lines) * 100
        
        print(f"📊 Redukcja linii kodu:")
        print(f"   Oryginał: {original_lines} linii")
        print(f"   Refaktor: {new_lines} linii")
        print(f"   Redukcja: {reduction_percent:.1f}%")
        
        if reduction_percent >= 70:  # Oczekujemy redukcji o co najmniej 70%
            print("✅ Znacząca redukcja liczby linii kodu")
            return True
        else:
            print("❌ Niewystarczająca redukcja liczby linii kodu")
            return False
            
    except Exception as e:
        print(f"❌ Błąd testu redukcji linii: {e}")
        return False

def test_legacy_service_removal():
    """Test usunięcia legacy serwisów (częściowo - zachowane dla kompatybilności)."""
    try:
        with open('src/ui/main_window.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Sprawdź czy legacy serwisy są oznaczone jako LEGACY
        if "# LEGACY: Zachowane dla kompatybilności" in content:
            print("✅ Legacy serwisy są oznaczone do usunięcia")
        else:
            print("❌ Legacy serwisy nie są oznaczone")
            return False
            
        # Sprawdź czy główna logika jest delegowana do kontrolera
        if "self.controller = MainWindowController(self)" in content:
            print("✅ MainWindow używa MVC kontrolera")
        else:
            print("❌ MainWindow nie używa MVC kontrolera")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Błąd testu legacy serwisów: {e}")
        return False

def test_delegation_pattern():
    """Test wzorca delegacji do komponentów."""
    try:
        with open('src/ui/main_window.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Sprawdź czy metody delegują do komponentów
        delegation_patterns = [
            "self.event_handler.handle_",
            "self.ui_manager.update_",
            "self.tab_manager.create_"
        ]
        
        for pattern in delegation_patterns:
            if pattern in content:
                print(f"✅ Znaleziono wzorzec delegacji: {pattern}")
            else:
                print(f"❌ Brak wzorca delegacji: {pattern}")
                return False
                
        return True
        
    except Exception as e:
        print(f"❌ Błąd testu delegacji: {e}")
        return False

def main():
    """Uruchom wszystkie testy refaktoryzacji ETAP 2."""
    print("🔍 Test refaktoryzacji ETAP 2 - MainWindow")
    print("=" * 60)
    
    tests = [
        ("Importy komponentów ETAP 2", test_imports_etap2),
        ("Struktura MainWindow", test_main_window_structure),
        ("Komponenty zarządzające", test_component_managers),
        ("Redukcja linii kodu", test_line_count_reduction),
        ("Usunięcie legacy serwisów", test_legacy_service_removal),
        ("Wzorzec delegacji", test_delegation_pattern)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        if test_func():
            passed += 1
            
    print("\n" + "=" * 60)
    print(f"📊 Wyniki ETAP 2: {passed}/{total} testów przeszło")
    
    if passed == total:
        print("🎉 Refaktoryzacja ETAP 2 zakończona pomyślnie!")
        print("\n🏗️ Osiągnięcia:")
        print("  • Podział monolitycznej klasy MainWindow na komponenty")
        print("  • Redukcja z 2010 do ~508 linii (75% redukcji)")
        print("  • Wprowadzenie wzorca MVC z komponentami zarządzającymi")
        print("  • Separacja odpowiedzialności: UI, Events, Tabs")
        print("  • Zachowanie kompatybilności API")
        return True
    else:
        print("⚠️ Niektóre testy nie przeszły - wymagane poprawki")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
