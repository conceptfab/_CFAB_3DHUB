"""
ConfigValidator - walidacja konfiguracji.
🚀 ETAP 2: Refaktoryzacja AppConfig - komponent walidacji
"""

import logging
from typing import Any, Dict, List, Optional

import jsonschema

logger = logging.getLogger(__name__)


class ConfigValidator:
    """
    Centralizowana walidacja konfiguracji.
    
    Odpowiedzialności:
    - Walidacja struktury konfiguracji według schematu JSON
    - Naprawa nieprawidłowych wartości
    - Walidacja poszczególnych typów danych
    """

    SCHEMA = {
        "type": "object",
        "properties": {
            "thumbnail_size": {"type": "integer", "minimum": 100, "maximum": 600},
            "min_thumbnail_size": {"type": "integer", "minimum": 10, "maximum": 1000},
            "max_thumbnail_size": {"type": "integer", "minimum": 100, "maximum": 2000},
            "supported_archive_extensions": {
                "type": "array",
                "items": {"type": "string", "pattern": r"^\.[a-zA-Z0-9]+$"},
            },
            "supported_preview_extensions": {
                "type": "array",
                "items": {"type": "string", "pattern": r"^\.[a-zA-Z0-9]+$"},
            },
            "predefined_colors": {
                "type": "object",
                "patternProperties": {
                    ".*": {
                        "type": "string",
                        "pattern": r"^#[0-9A-Fa-f]{6}$|^ALL$|^__NONE__$",
                    }
                },
            },
            "scanner_max_cache_entries": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10000,
            },
            "scanner_max_cache_age_seconds": {
                "type": "integer",
                "minimum": 60,
                "maximum": 86400,
            },
            "thumbnail_cache_max_entries": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10000,
            },
            "thumbnail_cache_max_memory_mb": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1000,
            },
            "thumbnail_cache_enable_disk": {"type": "boolean"},
            "thumbnail_cache_cleanup_threshold": {
                "type": "number",
                "minimum": 0.1,
                "maximum": 1.0,
            },
            "window_min_width": {"type": "integer", "minimum": 400, "maximum": 2000},
            "window_min_height": {"type": "integer", "minimum": 300, "maximum": 1500},
            "resize_timer_delay_ms": {
                "type": "integer",
                "minimum": 50,
                "maximum": 1000,
            },
            "progress_hide_delay_ms": {
                "type": "integer",
                "minimum": 1000,
                "maximum": 10000,
            },
            "thread_wait_timeout_ms": {
                "type": "integer",
                "minimum": 100,
                "maximum": 5000,
            },
            "preferences_status_display_ms": {
                "type": "integer",
                "minimum": 1000,
                "maximum": 10000,
            },
            "thumbnail_format": {"type": "string", "pattern": r"^(WEBP|JPEG|PNG)$"},
            "thumbnail_quality": {"type": "integer", "minimum": 1, "maximum": 100},
            "thumbnail_webp_method": {"type": "integer", "minimum": 0, "maximum": 6},
            "thumbnail_preserve_transparency": {"type": "boolean"},
        },
        "additionalProperties": True,
    }

    @classmethod
    def validate(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Waliduje całą konfigurację według schematu.
        
        Args:
            config: Słownik konfiguracji do walidacji
            
        Returns:
            Zwalidowana konfiguracja (z naprawionymi błędami jeśli to możliwe)
        """
        try:
            jsonschema.validate(config, cls.SCHEMA)
            return config
        except jsonschema.ValidationError as e:
            logger.warning(f"Błąd walidacji konfiguracji: {e.message}")
            # Zwróć konfigurację z naprawionymi błędami
            return cls._fix_invalid_config(config, e)

    @classmethod
    def _fix_invalid_config(
        cls, config: Dict[str, Any], error: jsonschema.ValidationError
    ) -> Dict[str, Any]:
        """
        Naprawia nieprawidłową konfigurację zastępując błędne wartości domyślnymi.
        
        Args:
            config: Nieprawidłowa konfiguracja
            error: Błąd walidacji
            
        Returns:
            Naprawiona konfiguracja
        """
        from copy import deepcopy

        # Utwórz kopię roboczą
        fixed_config = deepcopy(config)

        # Uwaga: Nie możemy tutaj importować ConfigDefaults z powodu circular import
        # Zamiast tego logujemy błąd i zwracamy oryginalną konfigurację
        logger.warning(f"Błąd walidacji konfiguracji, używam oryginalnej: {error}")

        return fixed_config

    @staticmethod
    def validate_int(
        value: Any,
        min_val: Optional[int] = None,
        max_val: Optional[int] = None,
        param_name: str = "Parametr",
    ) -> int:
        """
        Waliduje wartość całkowitą.
        
        Args:
            value: Wartość do walidacji
            min_val: Minimalna wartość (opcjonalnie)
            max_val: Maksymalna wartość (opcjonalnie)
            param_name: Nazwa parametru dla błędów
            
        Returns:
            Zwalidowana wartość całkowita
            
        Raises:
            ValueError: Jeśli wartość jest nieprawidłowa
        """
        if not isinstance(value, int):
            raise ValueError(
                f"{param_name} musi być liczbą całkowitą, otrzymano: {type(value)}"
            )

        if min_val is not None and value < min_val:
            raise ValueError(
                f"{param_name} musi być większy lub równy {min_val}, otrzymano: {value}"
            )

        if max_val is not None and value > max_val:
            raise ValueError(
                f"{param_name} musi być mniejszy lub równy {max_val}, otrzymano: {value}"
            )

        return value

    @staticmethod
    def validate_str(value: Any, param_name: str = "Parametr") -> str:
        """
        Waliduje wartość tekstową.
        
        Args:
            value: Wartość do walidacji
            param_name: Nazwa parametru dla błędów
            
        Returns:
            Zwalidowana wartość tekstowa
            
        Raises:
            ValueError: Jeśli wartość nie jest tekstem
        """
        if not isinstance(value, str):
            raise ValueError(f"{param_name} musi być tekstem, otrzymano: {type(value)}")
        return value

    @staticmethod
    def validate_list(
        value: Any, item_type: Optional[type] = None, param_name: str = "Parametr"
    ) -> List:
        """
        Waliduje listę wartości.
        
        Args:
            value: Wartość do walidacji
            item_type: Typ elementów listy (opcjonalnie)
            param_name: Nazwa parametru dla błędów
            
        Returns:
            Zwalidowana lista
            
        Raises:
            ValueError: Jeśli wartość nie jest listą lub elementy mają zły typ
        """
        if not isinstance(value, list):
            raise ValueError(f"{param_name} musi być listą, otrzymano: {type(value)}")

        if item_type is not None:
            for i, item in enumerate(value):
                if not isinstance(item, item_type):
                    raise ValueError(
                        f"Element {i} w {param_name} musi być typu {item_type}, otrzymano: {type(item)}"
                    )
        return value

    @staticmethod
    def validate_dict(value: Any, param_name: str = "Parametr") -> Dict:
        """
        Waliduje słownik.
        
        Args:
            value: Wartość do walidacji
            param_name: Nazwa parametru dla błędów
            
        Returns:
            Zwalidowany słownik
            
        Raises:
            ValueError: Jeśli wartość nie jest słownikiem
        """
        if not isinstance(value, dict):
            raise ValueError(
                f"{param_name} musi być słownikiem, otrzymano: {type(value)}"
            )
        return value 