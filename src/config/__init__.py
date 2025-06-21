"""
Pakiet konfiguracji CFAB_3DHUB - zrefaktoryzowana wersja.
🚀 ETAP 2: Refaktoryzacja AppConfig na mniejsze komponenty
"""

from .config_core import AppConfig
from .config_validator import ConfigValidator

# Backward compatibility - eksportuj główną klasę
__all__ = ['AppConfig', 'ConfigValidator'] 