"""
Monitor wydajności systemu cache dla CFAB_3DHUB.
Implementuje monitoring w czasie rzeczywistym dla optymalizacji z ETAP 1.
"""

import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class CacheMetrics:
    """Metryki wydajności cache."""
    timestamp: float
    cache_hits: int
    cache_misses: int
    total_requests: int
    hit_ratio: float
    cache_size: int
    memory_usage_mb: float


class CachePerformanceMonitor:
    """
    Monitor wydajności cache w czasie rzeczywistym.
    Śledzi trendy i wykrywa problemy wydajnościowe.
    """
    
    def __init__(self, history_size: int = 100):
        """
        Inicjalizuje monitor wydajności.
        
        Args:
            history_size: Liczba próbek historii do przechowywania
        """
        self.history_size = history_size
        self.metrics_history: deque[CacheMetrics] = deque(maxlen=history_size)
        self.last_report_time = time.time()
        self.report_interval = 300  # 5 minut
        
        # Progi alarmowe
        self.hit_ratio_threshold = 70.0  # Minimum hit ratio %
        self.memory_threshold_mb = 512   # Maximum memory usage MB
        self.response_time_threshold = 100  # Maximum response time ms
        
    def record_metrics(self, cache_instance) -> CacheMetrics:
        """
        Zapisuje metryki z instancji cache.
        
        Args:
            cache_instance: Instancja cache do monitorowania
            
        Returns:
            CacheMetrics: Aktualne metryki
        """
        try:
            current_time = time.time()
            
            # Pobierz podstawowe statystyki
            stats = cache_instance.get_statistics() if hasattr(cache_instance, 'get_statistics') else {}
            
            cache_hits = stats.get('cache_hits', getattr(cache_instance, 'cache_hits', 0))
            cache_misses = stats.get('cache_misses', getattr(cache_instance, 'cache_misses', 0))
            total_requests = cache_hits + cache_misses
            
            # Oblicz hit ratio
            hit_ratio = 0.0
            if total_requests > 0:
                hit_ratio = (cache_hits / total_requests) * 100
                
            # Oszacuj zużycie pamięci
            cache_size = stats.get('cache_entries', 0)
            if hasattr(cache_instance, 'cache'):
                cache_size = len(cache_instance.cache)
            elif hasattr(cache_instance, 'file_map_cache'):
                cache_size = len(cache_instance.file_map_cache.cache)
                
            # Przybliżone zużycie pamięci (średnio 1KB na wpis)
            memory_usage_mb = cache_size * 1024 / 1024 / 1024  # Convert to MB
            
            metrics = CacheMetrics(
                timestamp=current_time,
                cache_hits=cache_hits,
                cache_misses=cache_misses,
                total_requests=total_requests,
                hit_ratio=hit_ratio,
                cache_size=cache_size,
                memory_usage_mb=memory_usage_mb
            )
            
            self.metrics_history.append(metrics)
            self._check_performance_issues(metrics)
            self._periodic_report()
            
            return metrics
            
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania metryk cache: {e}")
            return CacheMetrics(
                timestamp=time.time(),
                cache_hits=0,
                cache_misses=0,
                total_requests=0,
                hit_ratio=0.0,
                cache_size=0,
                memory_usage_mb=0.0
            )
    
    def _check_performance_issues(self, metrics: CacheMetrics):
        """Sprawdza problemy wydajnościowe i ostrzega."""
        issues = []
        
        # Sprawdź hit ratio
        if metrics.hit_ratio < self.hit_ratio_threshold and metrics.total_requests > 10:
            issues.append(f"Niski hit ratio: {metrics.hit_ratio:.1f}% (próg: {self.hit_ratio_threshold}%)")
        
        # Sprawdź zużycie pamięci
        if metrics.memory_usage_mb > self.memory_threshold_mb:
            issues.append(f"Wysokie zużycie pamięci: {metrics.memory_usage_mb:.1f}MB (próg: {self.memory_threshold_mb}MB)")
        
        # Sprawdź trendy (jeśli mamy historię)
        if len(self.metrics_history) >= 5:
            recent_metrics = list(self.metrics_history)[-5:]
            hit_ratios = [m.hit_ratio for m in recent_metrics if m.total_requests > 0]
            
            if len(hit_ratios) >= 3:
                # Sprawdź czy hit ratio spada
                if hit_ratios[-1] < hit_ratios[0] - 10:  # Spadek o więcej niż 10%
                    issues.append(f"Spadający hit ratio: {hit_ratios[0]:.1f}% → {hit_ratios[-1]:.1f}%")
        
        # Loguj problemy
        if issues:
            logger.warning(f"Problemy wydajności cache: {'; '.join(issues)}")
    
    def _periodic_report(self):
        """Generuje okresowy raport wydajności."""
        current_time = time.time()
        
        if current_time - self.last_report_time >= self.report_interval:
            self.last_report_time = current_time
            
            if self.metrics_history:
                latest = self.metrics_history[-1]
                logger.info(
                    f"Cache performance report: "
                    f"Hit ratio: {latest.hit_ratio:.1f}%, "
                    f"Size: {latest.cache_size} entries, "
                    f"Memory: {latest.memory_usage_mb:.1f}MB, "
                    f"Requests: {latest.total_requests}"
                )
    
    def get_performance_summary(self) -> Dict:
        """
        Zwraca podsumowanie wydajności cache.
        
        Returns:
            Dict: Podsumowanie metryk
        """
        if not self.metrics_history:
            return {"status": "no_data"}
        
        recent_metrics = list(self.metrics_history)
        latest = recent_metrics[-1]
        
        # Oblicz średnie z ostatnich 10 próbek
        recent_sample = recent_metrics[-10:] if len(recent_metrics) >= 10 else recent_metrics
        
        avg_hit_ratio = sum(m.hit_ratio for m in recent_sample) / len(recent_sample)
        avg_memory = sum(m.memory_usage_mb for m in recent_sample) / len(recent_sample)
        
        return {
            "status": "ok",
            "latest_metrics": {
                "hit_ratio": latest.hit_ratio,
                "cache_size": latest.cache_size,
                "memory_usage_mb": latest.memory_usage_mb,
                "total_requests": latest.total_requests
            },
            "averages": {
                "hit_ratio": avg_hit_ratio,
                "memory_usage_mb": avg_memory
            },
            "thresholds": {
                "hit_ratio_threshold": self.hit_ratio_threshold,
                "memory_threshold_mb": self.memory_threshold_mb
            },
            "alerts": self._get_current_alerts(latest)
        }
    
    def _get_current_alerts(self, metrics: CacheMetrics) -> List[str]:
        """Zwraca listę aktualnych alertów."""
        alerts = []
        
        if metrics.hit_ratio < self.hit_ratio_threshold and metrics.total_requests > 10:
            alerts.append("low_hit_ratio")
        
        if metrics.memory_usage_mb > self.memory_threshold_mb:
            alerts.append("high_memory_usage")
        
        return alerts
    
    def reset_metrics(self):
        """Resetuje historię metryk."""
        self.metrics_history.clear()
        self.last_report_time = time.time()
        logger.info("Cache metrics history reset")


# Globalna instancja monitora
cache_monitor = CachePerformanceMonitor()


def monitor_cache_performance(cache_instance) -> CacheMetrics:
    """
    Funkcja pomocnicza do monitorowania wydajności cache.
    
    Args:
        cache_instance: Instancja cache do monitorowania
        
    Returns:
        CacheMetrics: Aktualne metryki
    """
    return cache_monitor.record_metrics(cache_instance)


def get_cache_performance_report() -> Dict:
    """
    Zwraca raport wydajności cache.
    
    Returns:
        Dict: Raport wydajności
    """
    return cache_monitor.get_performance_summary()