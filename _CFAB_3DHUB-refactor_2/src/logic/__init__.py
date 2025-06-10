"""
Inicjalizacja pakietu logic.

Udostępnia główne komponenty logiki biznesowej aplikacji.
"""

from .filter_logic import filter_file_pairs
from .scanner import scan_folder_for_pairs

__all__ = ["scan_folder_for_pairs", "filter_file_pairs"]
