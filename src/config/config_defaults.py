"""
ConfigDefaults - domyślne wartości konfiguracji.
🚀 ETAP 2: Refaktoryzacja AppConfig - komponent domyślnych wartości
"""


class ConfigDefaults:
    """
    Domyślne wartości konfiguracji aplikacji.
    
    Centralizuje wszystkie domyślne ustawienia w jednym miejscu
    dla łatwiejszego zarządzania i modyfikacji.
    """

    DEFAULT_CONFIG = {
        # UI
        "thumbnail_size": 250,
        "thumbnail_slider_position": 50,
        "min_thumbnail_size": 100,
        "max_thumbnail_size": 600,  # Zwiększono z 400
        # Obsługiwane rozszerzenia
        "supported_archive_extensions": [".rar", ".zip", ".7z", ".tar", ".gz", ".bz2"],
        "supported_preview_extensions": [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".tiff",
            ".webp",
        ],
        # Kolory do filtrowania
        "predefined_colors": {
            "Wszystkie kolory": "ALL",
            "Brak koloru": "__NONE__",
            "Czerwony": "#E53935",
            "Zielony": "#43A047",
            "Niebieski": "#1E88E5",
            "Żółty": "#FDD835",
            "Fioletowy": "#8E24AA",
            "Czarny": "#000000",
        },
        # Parametry cache dla scanera
        "scanner_max_cache_entries": 500,
        "scanner_max_cache_age_seconds": 3600,  # 1 godzina
        # Parametry cache dla miniaturek
        "thumbnail_cache_max_entries": 2000,
        "thumbnail_cache_max_memory_mb": 500,
        "thumbnail_cache_enable_disk": False,
        "thumbnail_cache_cleanup_threshold": 0.8,
        # Thumbnail format settings - NOWE
        "thumbnail_format": "WEBP",  # WEBP, JPEG, PNG
        "thumbnail_quality": 80,     # 1-100 dla lossy formatów
        "thumbnail_webp_method": 6,  # 0-6, wyższa wartość = lepsza kompresja
        "thumbnail_preserve_transparency": True,  # Zachowaj przezroczystość w WebP/PNG
        # Parametry okna i timerów
        "window_min_width": 800,  # Minimalna szerokość okna
        "window_min_height": 600,  # Minimalna wysokość okna
        "resize_timer_delay_ms": 150,  # Opóźnienie timera resize galerii (ms)
        "progress_hide_delay_ms": 3000,  # Czas wyświetlania postępu po zakończeniu (ms)
        "thread_wait_timeout_ms": 1000,  # Timeout oczekiwania na zakończenie wątku (ms)
        "preferences_status_display_ms": 3000,  # Czas wyświetlania statusu preferencji (ms)
        # Ochrona ustawień
    }

    @classmethod
    def get_default_config(cls) -> dict:
        """
        Pobiera kopię domyślnej konfiguracji.
        
        Returns:
            Kopia słownika z domyślnymi wartościami
        """
        return cls.DEFAULT_CONFIG.copy()

    @classmethod
    def get_default_value(cls, key: str, fallback=None):
        """
        Pobiera domyślną wartość dla konkretnego klucza.
        
        Args:
            key: Klucz konfiguracji
            fallback: Wartość fallback jeśli klucz nie istnieje
            
        Returns:
            Domyślna wartość lub fallback
        """
        return cls.DEFAULT_CONFIG.get(key, fallback)

    @classmethod
    def has_default(cls, key: str) -> bool:
        """
        Sprawdza czy istnieje domyślna wartość dla klucza.
        
        Args:
            key: Klucz konfiguracji
            
        Returns:
            True jeśli istnieje domyślna wartość
        """
        return key in cls.DEFAULT_CONFIG

    @classmethod
    def get_all_keys(cls) -> list:
        """
        Pobiera listę wszystkich kluczy domyślnej konfiguracji.
        
        Returns:
            Lista kluczy konfiguracji
        """
        return list(cls.DEFAULT_CONFIG.keys()) 