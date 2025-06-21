"""
Controller zarządzający logiką galerii.
Centralny punkt dla wszystkich operacji galerii w aplikacji.
"""

import logging
from typing import List, Dict, Any

from src.logic.filter_logic import filter_file_pairs
from src.models.file_pair import FilePair
from src.services.scanning_service import ScanningService

logger = logging.getLogger(__name__)


class GalleryController:
    """Controller obsługujący logikę galerii"""
    
    def __init__(self):
        self.scanning_service = ScanningService()
        self._current_files: List[FilePair] = []
        self._active_filters: Dict[str, Any] = {}
    
    def load_gallery(self, directory: str) -> bool:
        """
        Ładuje pliki dla galerii z katalogu.
        
        Args:
            directory: Ścieżka do katalogu do przeskanowania
            
        Returns:
            True jeśli operacja się powiodła, False w przeciwnym przypadku
        """
        try:
            self._current_files = self.scanning_service.scan_directory(directory)
            return True
        except Exception as e:
            logger.error(f"Błąd podczas ładowania galerii z {directory}: {e}")
            return False
    
    def apply_filters(self, all_file_pairs: List[FilePair], filter_criteria: Dict[str, Any]) -> List[FilePair]:
        """
        Aplikuje filtry do podanych plików.
        
        Args:
            all_file_pairs: Lista wszystkich par plików
            filter_criteria: Kryteria filtrowania
            
        Returns:
            Lista przefiltrowanych par plików
        """
        try:
            self._active_filters = filter_criteria
            filtered_pairs = filter_file_pairs(all_file_pairs, filter_criteria)
            logger.debug(f"Przefiltrowano {len(all_file_pairs)} plików do {len(filtered_pairs)}")
            return filtered_pairs
        except Exception as e:
            logger.error(f"Błąd podczas filtrowania plików: {e}")
            return all_file_pairs  # Zwróć wszystkie pliki w przypadku błędu
    
    def get_current_files(self) -> List[FilePair]:
        """
        Zwraca aktualne pliki galerii.
        
        Returns:
            Lista aktualnych par plików
        """
        return self._current_files
    
    def get_active_filters(self) -> Dict[str, Any]:
        """
        Zwraca aktualnie aktywne filtry.
        
        Returns:
            Słownik z aktywnymi filtrami
        """
        return self._active_filters.copy()
    
    def refresh_gallery(self, all_file_pairs: List[FilePair]) -> List[FilePair]:
        """
        Odświeża galerię z aktualnymi filtrami.
        
        Args:
            all_file_pairs: Lista wszystkich par plików
            
        Returns:
            Lista przefiltrowanych par plików
        """
        return self.apply_filters(all_file_pairs, self._active_filters)
    
    def clear_filters(self):
        """Czyści wszystkie aktywne filtry."""
        self._active_filters.clear()
        logger.debug("Wyczyszczono wszystkie filtry galerii")