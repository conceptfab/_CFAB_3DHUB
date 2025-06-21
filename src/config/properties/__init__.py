"""
Package properties - wydzielone kategorie właściwości konfiguracji.
ETAP 3.1: Podział na kategorie właściwości.

Eksport wszystkich klas właściwości dla łatwego importu.
"""

from .color_properties import ColorProperties
from .extension_properties import ExtensionProperties
from .format_properties import FormatProperties
from .thumbnail_properties import ThumbnailProperties

__all__ = [
    "ThumbnailProperties",
    "ExtensionProperties",
    "ColorProperties",
    "FormatProperties",
]
