"""
Inicjalizacja pakietu logic.

Udostępnia główne komponenty logiki biznesowej aplikacji.
"""

from .filter_logic import filter_file_pairs
from .scanner import scan_folder_for_pairs, collect_files_streaming, clear_cache, get_scan_statistics, ScanningInterrupted

__all__ = [
    "scan_folder_for_pairs", 
    "collect_files_streaming",
    "clear_cache",
    "get_scan_statistics", 
    "ScanningInterrupted",
    "filter_file_pairs"
]
