"""
Centralna walidacja ścieżek dla całej aplikacji.
Eliminuje duplikację walidacji między ScanManager i ScanningService.
"""

import os
from pathlib import Path
from typing import List, Optional

import logging

logger = logging.getLogger(__name__)


class PathValidator:
    """Centralna walidacja ścieżek dla całej aplikacji"""
    
    @staticmethod
    def validate_directory_path(path: str) -> bool:
        """
        Waliduje czy ścieżka do katalogu jest poprawna.
        
        Args:
            path: Ścieżka do katalogu
            
        Returns:
            True jeśli ścieżka jest poprawna, False w przeciwnym przypadku
        """
        if not path or not isinstance(path, str):
            return False
        
        try:
            path_obj = Path(path)
            return path_obj.exists() and path_obj.is_dir()
        except (OSError, ValueError):
            return False
    
    @staticmethod
    def validate_file_path(path: str) -> bool:
        """
        Waliduje czy ścieżka do pliku jest poprawna.
        
        Args:
            path: Ścieżka do pliku
            
        Returns:
            True jeśli ścieżka jest poprawna, False w przeciwnym przypadku
        """
        if not path or not isinstance(path, str):
            return False
        
        try:
            path_obj = Path(path)
            return path_obj.exists() and path_obj.is_file()
        except (OSError, ValueError):
            return False
    
    @staticmethod
    def normalize_path(path: str) -> Optional[str]:
        """
        Normalizuje ścieżkę do standardowego formatu.
        
        Args:
            path: Ścieżka do normalizacji
            
        Returns:
            Znormalizowana ścieżka lub None w przypadku błędu
        """
        if not path:
            return None
        
        try:
            return str(Path(path).resolve())
        except (OSError, ValueError):
            return None
    
    @staticmethod
    def get_safe_directory_paths(paths: List[str]) -> List[str]:
        """
        Zwraca tylko bezpieczne, zwalidowane ścieżki do katalogów.
        
        Args:
            paths: Lista ścieżek do walidacji
            
        Returns:
            Lista bezpiecznych ścieżek do katalogów
        """
        safe_paths = []
        for path in paths:
            normalized = PathValidator.normalize_path(path)
            if normalized and PathValidator.validate_directory_path(normalized):
                safe_paths.append(normalized)
            else:
                logger.debug(f"Odrzucono niepoprawną ścieżkę katalogu: {path}")
        return safe_paths
    
    @staticmethod
    def get_safe_file_paths(paths: List[str]) -> List[str]:
        """
        Zwraca tylko bezpieczne, zwalidowane ścieżki do plików.
        
        Args:
            paths: Lista ścieżek do walidacji
            
        Returns:
            Lista bezpiecznych ścieżek do plików
        """
        safe_paths = []
        for path in paths:
            normalized = PathValidator.normalize_path(path)
            if normalized and PathValidator.validate_file_path(normalized):
                safe_paths.append(normalized)
            else:
                logger.debug(f"Odrzucono niepoprawną ścieżkę pliku: {path}")
        return safe_paths
    
    @staticmethod
    def is_path_accessible(path: str) -> bool:
        """
        Sprawdza czy ścieżka jest dostępna do odczytu.
        
        Args:
            path: Ścieżka do sprawdzenia
            
        Returns:
            True jeśli ścieżka jest dostępna, False w przeciwnym przypadku
        """
        if not path:
            return False
        
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                return False
            
            # Sprawdź uprawnienia do odczytu
            return os.access(path, os.R_OK)
        except (OSError, ValueError):
            return False
    
    @staticmethod
    def is_path_writable(path: str) -> bool:
        """
        Sprawdza czy ścieżka jest dostępna do zapisu.
        
        Args:
            path: Ścieżka do sprawdzenia
            
        Returns:
            True jeśli ścieżka jest dostępna do zapisu, False w przeciwnym przypadku
        """
        if not path:
            return False
        
        try:
            path_obj = Path(path)
            
            # Jeśli ścieżka istnieje, sprawdź uprawnienia
            if path_obj.exists():
                return os.access(path, os.W_OK)
            
            # Jeśli ścieżka nie istnieje, sprawdź katalog nadrzędny
            parent = path_obj.parent
            return parent.exists() and os.access(parent, os.W_OK)
        except (OSError, ValueError):
            return False
    
    @staticmethod
    def get_parent_directory(path: str) -> Optional[str]:
        """
        Zwraca katalog nadrzędny dla podanej ścieżki.
        
        Args:
            path: Ścieżka
            
        Returns:
            Ścieżka do katalogu nadrzędnego lub None w przypadku błędu
        """
        if not path:
            return None
        
        try:
            return str(Path(path).parent)
        except (OSError, ValueError):
            return None
    
    @staticmethod
    def ensure_directory_exists(path: str) -> bool:
        """
        Zapewnia, że katalog istnieje (tworzy go jeśli nie istnieje).
        
        Args:
            path: Ścieżka do katalogu
            
        Returns:
            True jeśli katalog istnieje lub został utworzony, False w przeciwnym przypadku
        """
        if not path:
            return False
        
        try:
            path_obj = Path(path)
            if path_obj.exists():
                return path_obj.is_dir()
            
            # Utwórz katalog wraz z katalogami nadrzędnymi
            path_obj.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Utworzono katalog: {path}")
            return True
        except (OSError, ValueError) as e:
            logger.error(f"Nie można utworzyć katalogu {path}: {e}")
            return False