"""
ETAP 8: PERFORMANCE OPTIMIZATION - TileCacheOptimizer
Inteligentny system cache optimization dla maksymalnej wydajności.
"""

import time
import threading
import hashlib
import weakref
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union, Callable, List, Set
from enum import Enum, auto

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap

import logging
logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Strategie cache management."""
    LRU = auto()  # Least Recently Used
    LFU = auto()  # Least Frequently Used
    TTL = auto()  # Time To Live
    ADAPTIVE = auto()  # Adaptive based on usage patterns


@dataclass
class CacheEntry:
    """Entry w cache z metadanymi."""
    key: str
    value: Any
    size_bytes: int
    access_count: int = 0
    last_access_time: float = field(default_factory=time.time)
    creation_time: float = field(default_factory=time.time)
    ttl_seconds: Optional[float] = None
    
    def is_expired(self) -> bool:
        """Sprawdza czy entry jest expired."""
        if self.ttl_seconds is None:
            return False
        return (time.time() - self.creation_time) > self.ttl_seconds
    
    def touch(self):
        """Aktualizuje access time i count."""
        self.access_count += 1
        self.last_access_time = time.time()
    
    def get_age_seconds(self) -> float:
        """Zwraca wiek entry w sekundach."""
        return time.time() - self.creation_time


@dataclass
class CacheStats:
    """Statystyki cache performance."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0
    avg_access_time_ms: float = 0.0
    
    def get_hit_rate(self) -> float:
        """Zwraca cache hit rate w procentach."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    def get_memory_usage_mb(self) -> float:
        """Zwraca zużycie pamięci w MB."""
        return self.total_size_bytes / (1024 * 1024)


class EvictionPolicy:
    """Base class dla eviction policies."""
    
    def select_for_eviction(self, entries: Dict[str, CacheEntry], 
                          target_count: int) -> List[str]:
        """Wybiera klucze do eviction."""
        raise NotImplementedError


class LRUEvictionPolicy(EvictionPolicy):
    """Least Recently Used eviction policy."""
    
    def select_for_eviction(self, entries: Dict[str, CacheEntry], 
                          target_count: int) -> List[str]:
        # Sort by last_access_time (oldest first)
        sorted_entries = sorted(
            entries.items(),
            key=lambda x: x[1].last_access_time
        )
        return [key for key, _ in sorted_entries[:target_count]]


class LFUEvictionPolicy(EvictionPolicy):
    """Least Frequently Used eviction policy."""
    
    def select_for_eviction(self, entries: Dict[str, CacheEntry], 
                          target_count: int) -> List[str]:
        # Sort by access_count (least accessed first)
        sorted_entries = sorted(
            entries.items(),
            key=lambda x: x[1].access_count
        )
        return [key for key, _ in sorted_entries[:target_count]]


class TTLEvictionPolicy(EvictionPolicy):
    """Time To Live eviction policy."""
    
    def select_for_eviction(self, entries: Dict[str, CacheEntry], 
                          target_count: int) -> List[str]:
        # First remove expired entries
        expired_keys = [key for key, entry in entries.items() if entry.is_expired()]
        
        if len(expired_keys) >= target_count:
            return expired_keys[:target_count]
        
        # If not enough expired, use LRU for remaining
        remaining_count = target_count - len(expired_keys)
        non_expired = {k: v for k, v in entries.items() if not v.is_expired()}
        
        lru_policy = LRUEvictionPolicy()
        additional_keys = lru_policy.select_for_eviction(non_expired, remaining_count)
        
        return expired_keys + additional_keys


class AdaptiveEvictionPolicy(EvictionPolicy):
    """Adaptive eviction policy based na access patterns."""
    
    def __init__(self):
        self.lru_policy = LRUEvictionPolicy()
        self.lfu_policy = LFUEvictionPolicy()
        self.ttl_policy = TTLEvictionPolicy()
    
    def select_for_eviction(self, entries: Dict[str, CacheEntry], 
                          target_count: int) -> List[str]:
        # Analyze access patterns
        total_entries = len(entries)
        if total_entries == 0:
            return []
        
        # Calculate stats
        access_counts = [entry.access_count for entry in entries.values()]
        avg_access_count = sum(access_counts) / len(access_counts)
        
        current_time = time.time()
        ages = [current_time - entry.creation_time for entry in entries.values()]
        avg_age = sum(ages) / len(ages)
        
        # Choose strategy based na patterns
        expired_count = sum(1 for entry in entries.values() if entry.is_expired())
        
        if expired_count > target_count * 0.5:  # Lots of expired entries
            return self.ttl_policy.select_for_eviction(entries, target_count)
        elif avg_access_count < 2:  # Low reuse rate
            return self.lru_policy.select_for_eviction(entries, target_count)
        else:  # High reuse rate
            return self.lfu_policy.select_for_eviction(entries, target_count)


class TileCacheOptimizer(QObject):
    """
    Inteligentny cache optimizer dla FileTileWidget ecosystem.
    
    Features:
    - Multiple eviction strategies (LRU, LFU, TTL, Adaptive)
    - Intelligent cache sizing based na memory pressure
    - Cache warming dla predictive loading
    - Performance monitoring i hit rate optimization
    - Memory pressure detection
    - Automatic cache tuning
    """
    
    # Sygnały
    cache_stats_updated = pyqtSignal(object)  # CacheStats
    memory_pressure_detected = pyqtSignal(float)  # memory_usage_mb
    cache_warmed = pyqtSignal(str, int)  # cache_name, entries_loaded
    
    def __init__(self, 
                 max_size_mb: float = 100.0,
                 max_entries: int = 1000,
                 strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
                 enable_cache_warming: bool = True):
        super().__init__()
        
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.max_entries = max_entries
        self.strategy = strategy
        self.enable_cache_warming = enable_cache_warming
        
        # Multiple caches dla różnych typów danych
        self._caches: Dict[str, Dict[str, CacheEntry]] = {
            'thumbnails': {},
            'metadata': {},
            'pixmaps': {},
            'layout': {},
            'style': {}
        }
        
        # Cache statistics
        self._stats: Dict[str, CacheStats] = defaultdict(CacheStats)
        
        # Eviction policies
        self._eviction_policies = {
            CacheStrategy.LRU: LRUEvictionPolicy(),
            CacheStrategy.LFU: LFUEvictionPolicy(),
            CacheStrategy.TTL: TTLEvictionPolicy(),
            CacheStrategy.ADAPTIVE: AdaptiveEvictionPolicy(),
        }
        
        # Cache warming
        self._warming_queue: List[Callable] = []
        self._warming_timer = QTimer()
        self._warming_timer.timeout.connect(self._process_warming_queue)
        if enable_cache_warming:
            self._warming_timer.start(1000)  # Process every second
        
        # Cleanup timer
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._periodic_cleanup)
        self._cleanup_timer.start(30000)  # Cleanup every 30 seconds
        
        # Threading
        self._lock = threading.RLock()
        
        # Weak references dla automatic cleanup
        self._cache_users: Set[weakref.ref] = set()
        
        logger.info(f"TileCacheOptimizer initialized (max_size: {max_size_mb}MB, "
                   f"max_entries: {max_entries}, strategy: {strategy.name})")
    
    # === CORE CACHE OPERATIONS ===
    
    def get(self, cache_name: str, key: str) -> Optional[Any]:
        """Pobiera wartość z cache."""
        start_time = time.perf_counter()
        
        with self._lock:
            cache = self._caches.get(cache_name, {})
            entry = cache.get(key)
            
            if entry is None or entry.is_expired():
                # Cache miss
                self._stats[cache_name].misses += 1
                if entry and entry.is_expired():
                    # Remove expired entry
                    del cache[key]
                return None
            
            # Cache hit
            entry.touch()
            self._stats[cache_name].hits += 1
            
            # Update access time stats
            access_time_ms = (time.perf_counter() - start_time) * 1000
            stats = self._stats[cache_name]
            # Simple moving average
            alpha = 0.1
            stats.avg_access_time_ms = (
                alpha * access_time_ms + 
                (1 - alpha) * stats.avg_access_time_ms
            )
            
            return entry.value
    
    def put(self, cache_name: str, key: str, value: Any, 
            size_bytes: Optional[int] = None, ttl_seconds: Optional[float] = None) -> bool:
        """Dodaje wartość do cache."""
        if size_bytes is None:
            size_bytes = self._estimate_size(value)
        
        with self._lock:
            # Ensure cache exists
            if cache_name not in self._caches:
                self._caches[cache_name] = {}
            
            cache = self._caches[cache_name]
            
            # Check if we need eviction
            if self._needs_eviction(cache_name, size_bytes):
                self._perform_eviction(cache_name, size_bytes)
            
            # Create entry
            entry = CacheEntry(
                key=key,
                value=value,
                size_bytes=size_bytes,
                ttl_seconds=ttl_seconds
            )
            
            # Remove old entry if exists
            if key in cache:
                old_entry = cache[key]
                self._stats[cache_name].total_size_bytes -= old_entry.size_bytes
                self._stats[cache_name].entry_count -= 1
            
            # Add new entry
            cache[key] = entry
            self._stats[cache_name].total_size_bytes += size_bytes
            self._stats[cache_name].entry_count += 1
            
            return True
    
    def remove(self, cache_name: str, key: str) -> bool:
        """Usuwa entry z cache."""
        with self._lock:
            cache = self._caches.get(cache_name, {})
            if key not in cache:
                return False
            
            entry = cache[key]
            del cache[key]
            
            # Update stats
            self._stats[cache_name].total_size_bytes -= entry.size_bytes
            self._stats[cache_name].entry_count -= 1
            
            return True
    
    def clear(self, cache_name: Optional[str] = None):
        """Czyści cache."""
        with self._lock:
            if cache_name:
                self._caches[cache_name] = {}
                self._stats[cache_name] = CacheStats()
            else:
                self._caches.clear()
                self._stats.clear()
        
        logger.info(f"Cache cleared: {cache_name or 'all'}")
    
    # === EVICTION LOGIC ===
    
    def _needs_eviction(self, cache_name: str, new_size_bytes: int) -> bool:
        """Sprawdza czy potrzebna eviction."""
        total_size = sum(stats.total_size_bytes for stats in self._stats.values())
        total_entries = sum(stats.entry_count for stats in self._stats.values())
        
        return (
            total_size + new_size_bytes > self.max_size_bytes or
            total_entries >= self.max_entries
        )
    
    def _perform_eviction(self, cache_name: str, new_size_bytes: int):
        """Wykonuje eviction dla zrobienia miejsca."""
        policy = self._eviction_policies[self.strategy]
        
        # Calculate how many entries to evict
        total_size = sum(stats.total_size_bytes for stats in self._stats.values())
        total_entries = sum(stats.entry_count for stats in self._stats.values())
        
        target_size = max(1, int((total_size + new_size_bytes - self.max_size_bytes) * 1.2))
        target_entries = max(1, total_entries - self.max_entries + 1)
        
        # Evict from largest caches first
        cache_sizes = [(name, stats.total_size_bytes) for name, stats in self._stats.items()]
        cache_sizes.sort(key=lambda x: x[1], reverse=True)
        
        bytes_to_evict = target_size
        entries_to_evict = target_entries
        
        for cache_name_to_evict, _ in cache_sizes:
            if bytes_to_evict <= 0 and entries_to_evict <= 0:
                break
            
            cache = self._caches[cache_name_to_evict]
            if not cache:
                continue
            
            # Calculate how many entries from this cache
            entries_from_this_cache = min(
                len(cache),
                max(1, int(entries_to_evict * 0.3))  # Max 30% from any single cache
            )
            
            keys_to_evict = policy.select_for_eviction(cache, entries_from_this_cache)
            
            # Remove selected entries
            for key in keys_to_evict:
                if key in cache:
                    entry = cache[key]
                    del cache[key]
                    
                    # Update stats
                    self._stats[cache_name_to_evict].total_size_bytes -= entry.size_bytes
                    self._stats[cache_name_to_evict].entry_count -= 1
                    self._stats[cache_name_to_evict].evictions += 1
                    
                    bytes_to_evict -= entry.size_bytes
                    entries_to_evict -= 1
        
        logger.debug(f"Eviction completed for {cache_name}")
    
    # === CACHE WARMING ===
    
    def add_to_warming_queue(self, load_func: Callable, priority: int = 0):
        """Dodaje funkcję do cache warming queue."""
        if not self.enable_cache_warming:
            return
        
        # Insert at correct position based na priority
        inserted = False
        for i, (existing_priority, _) in enumerate(self._warming_queue):
            if priority > existing_priority:
                self._warming_queue.insert(i, (priority, load_func))
                inserted = True
                break
        
        if not inserted:
            self._warming_queue.append((priority, load_func))
    
    def _process_warming_queue(self):
        """Przetwarza cache warming queue."""
        if not self._warming_queue:
            return
        
        # Process one item per timer tick to avoid blocking
        priority, load_func = self._warming_queue.pop(0)
        
        try:
            result = load_func()
            if result:
                logger.debug(f"Cache warming completed: {load_func.__name__}")
        except Exception as e:
            logger.error(f"Cache warming error: {e}")
    
    def warm_thumbnails(self, file_paths: List[str], size: tuple):
        """Rozgrzewa cache miniaturek dla podanych plików."""
        for file_path in file_paths:
            cache_key = self._generate_thumbnail_key(file_path, size)
            
            # Skip if already in cache
            if self.get('thumbnails', cache_key) is not None:
                continue
            
            # Add to warming queue
            def load_thumbnail():
                # Actual thumbnail loading logic would go here
                # For now just simulate
                time.sleep(0.01)  # Simulate loading time
                return f"thumbnail_data_for_{file_path}"
            
            self.add_to_warming_queue(load_thumbnail, priority=1)
    
    # === UTILITIES ===
    
    def _estimate_size(self, value: Any) -> int:
        """Szacuje rozmiar obiektu w bajtach."""
        if isinstance(value, QPixmap):
            # Estimate QPixmap size
            if not value.isNull():
                return value.width() * value.height() * 4  # RGBA
            return 0
        elif isinstance(value, (str, bytes)):
            return len(value)
        elif isinstance(value, dict):
            return sum(len(str(k)) + len(str(v)) for k, v in value.items())
        else:
            # Fallback estimation
            return 1024  # 1KB default
    
    def _generate_thumbnail_key(self, file_path: str, size: tuple) -> str:
        """Generuje klucz dla thumbnail cache."""
        key_data = f"{file_path}_{size[0]}x{size[1]}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _periodic_cleanup(self):
        """Periodic cleanup of expired entries."""
        current_time = time.time()
        
        with self._lock:
            for cache_name, cache in self._caches.items():
                expired_keys = []
                
                for key, entry in cache.items():
                    if entry.is_expired():
                        expired_keys.append(key)
                
                # Remove expired entries
                for key in expired_keys:
                    entry = cache[key]
                    del cache[key]
                    
                    # Update stats
                    self._stats[cache_name].total_size_bytes -= entry.size_bytes
                    self._stats[cache_name].entry_count -= 1
                
                if expired_keys:
                    logger.debug(f"Cleaned {len(expired_keys)} expired entries from {cache_name}")
        
        # Check memory pressure
        total_size_mb = sum(stats.total_size_bytes for stats in self._stats.values()) / (1024 * 1024)
        max_size_mb = self.max_size_bytes / (1024 * 1024)
        
        if total_size_mb > max_size_mb * 0.9:  # 90% full
            self.memory_pressure_detected.emit(total_size_mb)
        
        # Emit stats update
        self.cache_stats_updated.emit(self.get_cache_stats())
    
    # === STATS & REPORTING ===
    
    def get_cache_stats(self, cache_name: Optional[str] = None) -> Union[CacheStats, Dict[str, CacheStats]]:
        """Zwraca cache statistics."""
        if cache_name:
            return self._stats.get(cache_name, CacheStats())
        return dict(self._stats)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Zwraca comprehensive performance summary."""
        total_hits = sum(stats.hits for stats in self._stats.values())
        total_misses = sum(stats.misses for stats in self._stats.values())
        total_size_mb = sum(stats.total_size_bytes for stats in self._stats.values()) / (1024 * 1024)
        total_entries = sum(stats.entry_count for stats in self._stats.values())
        
        overall_hit_rate = (total_hits / (total_hits + total_misses) * 100) if (total_hits + total_misses) > 0 else 0
        
        return {
            'overall_hit_rate': overall_hit_rate,
            'total_size_mb': total_size_mb,
            'max_size_mb': self.max_size_bytes / (1024 * 1024),
            'total_entries': total_entries,
            'max_entries': self.max_entries,
            'memory_usage_percent': (total_size_mb / (self.max_size_bytes / (1024 * 1024))) * 100,
            'strategy': self.strategy.name,
            'cache_breakdown': {
                name: {
                    'hit_rate': stats.get_hit_rate(),
                    'size_mb': stats.get_memory_usage_mb(),
                    'entry_count': stats.entry_count,
                    'avg_access_time_ms': stats.avg_access_time_ms,
                } for name, stats in self._stats.items()
            }
        }
    
    def optimize_cache_sizes(self):
        """Automatically optimizes cache sizes based na usage patterns."""
        summary = self.get_performance_summary()
        
        # If overall hit rate is low, increase cache size
        if summary['overall_hit_rate'] < 80 and summary['memory_usage_percent'] < 90:
            self.max_size_bytes = int(self.max_size_bytes * 1.2)
            logger.info(f"Increased cache size to {self.max_size_bytes / (1024*1024):.1f}MB")
        
        # If memory usage is high but hit rate is good, keep current size
        elif summary['overall_hit_rate'] > 95 and summary['memory_usage_percent'] > 90:
            # Cache is efficient, no changes needed
            pass
        
        # If hit rate is very low, try different strategy
        elif summary['overall_hit_rate'] < 60:
            old_strategy = self.strategy
            if self.strategy != CacheStrategy.ADAPTIVE:
                self.strategy = CacheStrategy.ADAPTIVE
                logger.info(f"Switched cache strategy from {old_strategy.name} to ADAPTIVE")
    
    def register_cache_user(self, user_obj):
        """Rejestruje użytkownika cache dla automatic cleanup."""
        user_ref = weakref.ref(user_obj, self._cleanup_cache_user)
        self._cache_users.add(user_ref)
    
    def _cleanup_cache_user(self, user_ref):
        """Cleanup gdy cache user zostaje usunięty."""
        self._cache_users.discard(user_ref)
    
    def cleanup(self):
        """Cleanup cache optimizer."""
        self._cleanup_timer.stop()
        if hasattr(self, '_warming_timer'):
            self._warming_timer.stop()
        
        self.clear()  # Clear all caches
        self._cache_users.clear()
        
        logger.info("TileCacheOptimizer cleaned up")


# === GLOBAL INSTANCE ===

_cache_optimizer_instance: Optional[TileCacheOptimizer] = None
_cache_optimizer_lock = threading.Lock()


def get_cache_optimizer(max_size_mb: float = 100.0) -> TileCacheOptimizer:
    """Singleton access do TileCacheOptimizer."""
    global _cache_optimizer_instance
    
    with _cache_optimizer_lock:
        if _cache_optimizer_instance is None:
            _cache_optimizer_instance = TileCacheOptimizer(max_size_mb=max_size_mb)
        return _cache_optimizer_instance


def cleanup_cache_optimizer():
    """Cleanup singleton instance."""
    global _cache_optimizer_instance
    
    with _cache_optimizer_lock:
        if _cache_optimizer_instance is not None:
            _cache_optimizer_instance.cleanup()
            _cache_optimizer_instance = None 