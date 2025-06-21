"""
Pakiet zarządzania metadanymi CFAB_3DHUB - zrefaktoryzowana wersja.
🚀 ETAP 3: Refaktoryzacja MetadataManager na mniejsze komponenty
"""

from .metadata_core import MetadataManager
from .metadata_validator import MetadataValidator

# Backward compatibility - eksportuj główną klasę
__all__ = ['MetadataManager', 'MetadataValidator'] 