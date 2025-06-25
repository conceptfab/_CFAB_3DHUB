"""
Persistent Disk Cache Manager - zapisuje cache na dysku w folderze .cache

Każdy folder ma swój folder .cache z:
- scan_results.json - wyniki skanowania (pary plików, metadane)
- cache_index.json - indeks cache z mtime validation
- metadata.json - metadane kafelków (gwiazdki, tagi kolorów)
"""

import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from src.models.file_pair import FilePair
from src.models.special_folder import SpecialFolder
from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)


@dataclass
class CacheIndexEntry:
    """Wpis w indeksie cache."""
    timestamp: float
    directory_mtime: float
    file_count: int
    pairs_count: int
    cache_size_bytes: int
    strategy: str
    version: str = "1.0"


@dataclass
class PersistentCacheConfig:
    """Konfiguracja persistent cache."""
    max_cache_age_days: int = 30
    cache_folder_name: str = ".cache"


class PersistentCacheManager:
    """Manager persistent disk cache z folderem .cache w każdym katalogu."""
    
    def __init__(self, config: Optional[PersistentCacheConfig] = None):
        self.config = config or PersistentCacheConfig()
        self._cache_index: Dict[str, CacheIndexEntry] = {}
        self._loaded_cache_paths: set = set()
        
    def get_cache_path(self, directory: str) -> Path:
        """Zwraca ścieżkę do folderu cache dla danego katalogu."""
        normalized_dir = normalize_path(directory)
        return Path(normalized_dir) / self.config.cache_folder_name
    
    def get_cache_index_path(self, directory: str) -> Path:
        """Zwraca ścieżkę do pliku indeksu cache."""
        cache_path = self.get_cache_path(directory)
        return cache_path / "cache_index.json"
    
    def get_scan_results_path(self, directory: str, strategy: str) -> Path:
        """Zwraca ścieżkę do pliku wyników skanowania."""
        cache_path = self.get_cache_path(directory)
        return cache_path / f"scan_results_{strategy}.json"
    
    def get_metadata_path(self, directory: str) -> Path:
        """Zwraca ścieżkę do pliku metadanych."""
        cache_path = self.get_cache_path(directory)
        return cache_path / "metadata.json"
    
    def _load_cache_index(self, directory: str) -> bool:
        """Ładuje indeks cache z dysku."""
        index_path = self.get_cache_index_path(directory)
        
        if not index_path.exists():
            return False
            
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._cache_index[directory] = CacheIndexEntry(**data)
            return True
        except Exception as e:
            logger.error(f"Błąd ładowania indeksu cache dla {directory}: {e}")
            return False
    
    def _save_cache_index(self, directory: str, entry: CacheIndexEntry):
        """Zapisuje indeks cache na dysk."""
        cache_path = self.get_cache_path(directory)
        cache_path.mkdir(exist_ok=True)
        
        index_path = self.get_cache_index_path(directory)
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(entry), f, indent=2)
        except Exception as e:
            logger.error(f"Błąd zapisywania indeksu cache dla {directory}: {e}")
    
    def _get_directory_mtime(self, directory: str) -> float:
        """Pobiera najnowszy mtime z katalogu i jego plików."""
        try:
            # Sprawdź mtime katalogu
            dir_mtime = os.path.getmtime(directory)
            max_mtime = dir_mtime
            
            # Sprawdź mtime wszystkich plików w katalogu
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    try:
                        file_mtime = os.path.getmtime(file_path)
                        max_mtime = max(max_mtime, file_mtime)
                    except OSError:
                        continue  # Pomiń pliki z błędami
                        
            return max_mtime
        except OSError:
            return 0.0
    
    def _is_cache_valid(self, directory: str, strategy: str) -> bool:
        """Sprawdza czy cache jest aktualny."""
        if directory not in self._cache_index:
            return False
            
        entry = self._cache_index[directory]
        current_mtime = self._get_directory_mtime(directory)
        current_time = time.time()
        
        # Sprawdź czy cache nie wygasł
        if current_time - entry.timestamp > (self.config.max_cache_age_days * 24 * 3600):
            logger.debug(f"Cache expired for {directory}")
            return False
            
        # Sprawdź czy katalog się zmienił
        if current_mtime > entry.directory_mtime:
            logger.debug(f"Directory modified for {directory} (mtime: {current_mtime} > {entry.directory_mtime})")
            return False
            
        # Sprawdź czy strategia się zgadza
        if entry.strategy != strategy:
            logger.debug(f"Strategy mismatch for {directory} ({entry.strategy} != {strategy})")
            return False
            
        return True
    
    def get_scan_result(self, directory: str, strategy: str) -> Optional[Tuple[List[FilePair], List[str], List[str], List[SpecialFolder]]]:
        """Pobiera wynik skanowania z persistent cache."""
        normalized_dir = normalize_path(directory)
        
        # Sprawdź czy cache jest aktualny
        if not self._is_cache_valid(normalized_dir, strategy):
            return None
            
        # Ładuj indeks jeśli nie jest załadowany
        if normalized_dir not in self._cache_index:
            if not self._load_cache_index(normalized_dir):
                return None
        
        scan_results_path = self.get_scan_results_path(normalized_dir, strategy)
        if not scan_results_path.exists():
            return None
            
        try:
            with open(scan_results_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Rekonstruuj obiekty z JSON
            file_pairs = [FilePair.from_dict(pair_data) for pair_data in data.get('file_pairs', [])]
            # FILTRUJ uszkodzone FilePair
            file_pairs = [fp for fp in file_pairs if fp and hasattr(fp, 'archive_path') and fp.archive_path]
            unpaired_archives = data.get('unpaired_archives', [])
            unpaired_previews = data.get('unpaired_previews', [])
            
            # Rekonstruuj special folders
            special_folders = []
            for folder_data in data.get('special_folders', []):
                special_folders.append(SpecialFolder.from_dict(folder_data))
                
            logger.info(f"Cache HIT: Załadowano {len(file_pairs)} par z persistent cache dla {directory}")
            return file_pairs, unpaired_archives, unpaired_previews, special_folders
            
        except Exception as e:
            logger.error(f"Błąd ładowania scan result z cache dla {directory}: {e}")
            return None
    
    def save_scan_result(self, directory: str, strategy: str, 
                        file_pairs: List[FilePair], 
                        unpaired_archives: List[str], 
                        unpaired_previews: List[str],
                        special_folders: List[SpecialFolder]):
        """Zapisuje wynik skanowania do persistent cache."""
        normalized_dir = normalize_path(directory)
        cache_path = self.get_cache_path(normalized_dir)
        cache_path.mkdir(exist_ok=True)
        
        # Przygotuj dane do zapisu
        data = {
            'file_pairs': [pair.to_dict() for pair in file_pairs],
            'unpaired_archives': unpaired_archives,
            'unpaired_previews': unpaired_previews,
            'special_folders': [folder.to_dict() for folder in special_folders],
            'cached_at': datetime.now().isoformat(),
            'strategy': strategy
        }
        
        # Zapisz scan results
        scan_results_path = self.get_scan_results_path(normalized_dir, strategy)
        try:
            with open(scan_results_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Błąd zapisywania scan result do cache dla {directory}: {e}")
            return
        
        # Zaktualizuj indeks cache
        current_mtime = self._get_directory_mtime(normalized_dir)
        cache_size = scan_results_path.stat().st_size
        
        entry = CacheIndexEntry(
            timestamp=time.time(),
            directory_mtime=current_mtime,
            file_count=len(file_pairs) * 2 + len(unpaired_archives) + len(unpaired_previews),
            pairs_count=len(file_pairs),
            cache_size_bytes=cache_size,
            strategy=strategy
        )
        
        self._cache_index[normalized_dir] = entry
        self._save_cache_index(normalized_dir, entry)
        
        logger.info(f"Cache SAVE: Zapisano {len(file_pairs)} par do persistent cache dla {directory}")
    
    def clear_cache(self, directory: str):
        """Czyści cache dla danego katalogu."""
        cache_path = self.get_cache_path(directory)
        if cache_path.exists():
            try:
                shutil.rmtree(cache_path)
                logger.info(f"Wyczyszczono cache dla {directory}")
            except Exception as e:
                logger.error(f"Błąd czyszczenia cache dla {directory}: {e}")
        
        # Usuń z indeksu
        self._cache_index.pop(directory, None)
    
    def get_cache_stats(self, directory: str) -> Dict[str, Any]:
        """Zwraca statystyki cache dla katalogu."""
        cache_path = self.get_cache_path(directory)
        
        if not cache_path.exists():
            return {'exists': False}
        
        try:
            stats = {
                'exists': True,
                'cache_size_bytes': 0,
                'files_count': 0
            }
            
            # Oblicz rozmiar całego cache
            for root, dirs, files in os.walk(cache_path):
                for file in files:
                    file_path = Path(root) / file
                    stats['cache_size_bytes'] += file_path.stat().st_size
                    stats['files_count'] += 1
            
            # Dodaj informacje z indeksu
            if directory in self._cache_index:
                entry = self._cache_index[directory]
                stats.update({
                    'cached_at': datetime.fromtimestamp(entry.timestamp).isoformat(),
                    'pairs_count': entry.pairs_count,
                    'strategy': entry.strategy,
                    'age_days': (time.time() - entry.timestamp) / (24 * 3600)
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Błąd pobierania statystyk cache dla {directory}: {e}")
            return {'exists': False, 'error': str(e)}
    
    def cleanup_old_cache(self, max_age_days: Optional[int] = None):
        """Czyści stare cache."""
        max_age = max_age_days or self.config.max_cache_age_days
        cutoff_time = time.time() - (max_age * 24 * 3600)
        
        cleaned_count = 0
        for directory in list(self._cache_index.keys()):
            entry = self._cache_index[directory]
            if entry.timestamp < cutoff_time:
                self.clear_cache(directory)
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Wyczyszczono {cleaned_count} starych cache'ów")


# Singleton instance
_persistent_cache_manager = None

def get_persistent_cache_manager() -> PersistentCacheManager:
    """Zwraca singleton instance PersistentCacheManager."""
    global _persistent_cache_manager
    if _persistent_cache_manager is None:
        _persistent_cache_manager = PersistentCacheManager()
    return _persistent_cache_manager 