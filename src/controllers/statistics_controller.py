"""
Controller zarządzający statystykami folderów.
Centralizuje logikę biznesową statystyk, oddziela od UI.
"""

import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

from src.models.file_pair import FilePair
from src.services.scanning_service import ScanningService
from src.utils.path_validator import PathValidator

logger = logging.getLogger(__name__)


@dataclass
class FolderStats:
    """Statystyki folderu - wersja controller."""
    
    folder_path: str
    total_files: int = 0
    paired_files: int = 0
    unpaired_archives: int = 0
    unpaired_previews: int = 0
    total_size_bytes: int = 0
    subfolders_count: int = 0
    
    @property
    def total_size_gb(self) -> float:
        """Rozmiar w GB."""
        return self.total_size_bytes / (1024**3)
    
    @property
    def pairing_ratio(self) -> float:
        """Stosunek sparowanych do wszystkich plików."""
        if self.total_files == 0:
            return 0.0
        return self.paired_files / self.total_files


class StatisticsController:
    """Controller obsługujący statystyki folderów."""
    
    def __init__(self):
        self.scanning_service = ScanningService()
        self._stats_cache: Dict[str, FolderStats] = {}
    
    def calculate_folder_statistics(self, folder_path: str) -> Optional[FolderStats]:
        """
        Oblicza statystyki dla folderu.
        
        Args:
            folder_path: Ścieżka do folderu
            
        Returns:
            FolderStats lub None w przypadku błędu
        """
        if not PathValidator.validate_directory_path(folder_path):
            logger.error(f"Nieprawidłowa ścieżka folderu: {folder_path}")
            return None
        
        normalized_path = PathValidator.normalize_path(folder_path)
        if not normalized_path:
            return None
        
        # Sprawdź cache
        if normalized_path in self._stats_cache:
            logger.debug(f"Zwracam statystyki z cache: {normalized_path}")
            return self._stats_cache[normalized_path]
        
        try:
            # Przeskanuj folder
            scan_result = self.scanning_service.scan_directory(
                normalized_path, max_depth=0
            )
            
            if scan_result.error_message:
                logger.error(f"Błąd skanowania {normalized_path}: {scan_result.error_message}")
                return None
            
            # Oblicz statystyki
            stats = FolderStats(
                folder_path=normalized_path,
                paired_files=len(scan_result.file_pairs) * 2,  # para = 2 pliki
                unpaired_archives=len(scan_result.unpaired_archives),
                unpaired_previews=len(scan_result.unpaired_previews),
                total_files=len(scan_result.file_pairs) * 2 + 
                           len(scan_result.unpaired_archives) + 
                           len(scan_result.unpaired_previews)
            )
            
            # Oblicz rozmiar plików
            stats.total_size_bytes = self._calculate_total_size(scan_result.file_pairs, 
                                                               scan_result.unpaired_archives,
                                                               scan_result.unpaired_previews)
            
            # Zapisz do cache
            self._stats_cache[normalized_path] = stats
            
            logger.debug(f"Obliczono statystyki dla {normalized_path}: {stats.total_files} plików")
            return stats
            
        except Exception as e:
            logger.error(f"Błąd obliczania statystyk dla {normalized_path}: {e}")
            return None
    
    def _calculate_total_size(self, file_pairs: List[FilePair], 
                            unpaired_archives: List[str],
                            unpaired_previews: List[str]) -> int:
        """Oblicza całkowity rozmiar plików w bajtach."""
        import os
        total_size = 0
        
        # Rozmiar par plików
        for pair in file_pairs:
            try:
                if pair.archive_path and os.path.exists(pair.archive_path):
                    total_size += os.path.getsize(pair.archive_path)
                if pair.preview_path and os.path.exists(pair.preview_path):
                    total_size += os.path.getsize(pair.preview_path)
            except OSError:
                continue
        
        # Rozmiar niesprarowanych archiwów
        for archive_path in unpaired_archives:
            try:
                if os.path.exists(archive_path):
                    total_size += os.path.getsize(archive_path)
            except OSError:
                continue
        
        # Rozmiar niesparowanych podglądów
        for preview_path in unpaired_previews:
            try:
                if os.path.exists(preview_path):
                    total_size += os.path.getsize(preview_path)
            except OSError:
                continue
        
        return total_size
    
    def get_multiple_folder_statistics(self, folder_paths: List[str]) -> Dict[str, FolderStats]:
        """
        Oblicza statystyki dla wielu folderów.
        
        Args:
            folder_paths: Lista ścieżek do folderów
            
        Returns:
            Słownik {ścieżka: statystyki}
        """
        results = {}
        
        for folder_path in folder_paths:
            stats = self.calculate_folder_statistics(folder_path)
            if stats:
                results[folder_path] = stats
        
        return results
    
    def get_summary_statistics(self, folder_paths: List[str]) -> FolderStats:
        """
        Oblicza sumaryczne statystyki dla wielu folderów.
        
        Args:
            folder_paths: Lista ścieżek do folderów
            
        Returns:
            Sumaryczne statystyki
        """
        summary = FolderStats(folder_path="SUMMARY")
        
        for folder_path in folder_paths:
            stats = self.calculate_folder_statistics(folder_path)
            if stats:
                summary.total_files += stats.total_files
                summary.paired_files += stats.paired_files
                summary.unpaired_archives += stats.unpaired_archives
                summary.unpaired_previews += stats.unpaired_previews
                summary.total_size_bytes += stats.total_size_bytes
                summary.subfolders_count += 1
        
        return summary
    
    def invalidate_cache(self, folder_path: str = None):
        """
        Usuwa statystyki z cache.
        
        Args:
            folder_path: Ścieżka do folderu (None = wyczyść cały cache)
        """
        if folder_path:
            normalized_path = PathValidator.normalize_path(folder_path)
            if normalized_path and normalized_path in self._stats_cache:
                del self._stats_cache[normalized_path]
                logger.debug(f"Usunięto z cache statystyki: {normalized_path}")
        else:
            self._stats_cache.clear()
            logger.debug("Wyczyszczono cały cache statystyk")
    
    def get_cache_info(self) -> Dict[str, int]:
        """
        Zwraca informacje o cache statystyk.
        
        Returns:
            Słownik z informacjami o cache
        """
        return {
            'cached_folders': len(self._stats_cache),
            'total_cached_files': sum(stats.total_files for stats in self._stats_cache.values()),
            'total_cached_size_gb': sum(stats.total_size_gb for stats in self._stats_cache.values())
        }
    
    def calculate_statistics_async(self, folder_path: str, callback: Callable[[Optional[FolderStats]], None]):
        """
        Oblicza statystyki asynchronicznie (dla kompatybilności z UI).
        
        Args:
            folder_path: Ścieżka do folderu
            callback: Funkcja zwrotna wywoływana z wynikami
        """
        # Dla uproszczenia, wykonujemy synchronicznie
        # W przyszłości można dodać rzeczywiste przetwarzanie asynchroniczne
        stats = self.calculate_folder_statistics(folder_path)
        callback(stats)
    
    def compare_folders(self, folder_path1: str, folder_path2: str) -> Dict[str, any]:
        """
        Porównuje statystyki dwóch folderów.
        
        Args:
            folder_path1: Pierwszy folder
            folder_path2: Drugi folder
            
        Returns:
            Słownik z porównaniem
        """
        stats1 = self.calculate_folder_statistics(folder_path1)
        stats2 = self.calculate_folder_statistics(folder_path2)
        
        if not stats1 or not stats2:
            return {}
        
        return {
            'folder1': stats1,
            'folder2': stats2,
            'files_diff': stats1.total_files - stats2.total_files,
            'size_diff_gb': stats1.total_size_gb - stats2.total_size_gb,
            'pairing_ratio_diff': stats1.pairing_ratio - stats2.pairing_ratio,
            'larger_folder': folder_path1 if stats1.total_size_gb > stats2.total_size_gb else folder_path2
        }