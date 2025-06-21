"""
ETAP 5: Performance management dla FileTileWidget.

Wydzielony z file_tile_widget.py dla lepszej organizacji kodu.
"""

import logging
from typing import Any, Optional


class SafePerformanceMetric:
    """
    Wrapper dla opcjonalnego PerformanceMetric z graceful degradation.

    ETAP 5: Wydzielony z głównego pliku file_tile_widget.py
    """

    def __init__(self):
        self._metric = None
        self._available = False
        self._initialize()

    def _initialize(self):
        """Inicjalizuje performance metric jeśli dostępny."""
        try:
            from .tile_performance_monitor import PerformanceMetric

            self._metric = PerformanceMetric
            self._available = True
        except (ImportError, AttributeError) as e:
            logger = logging.getLogger(__name__)
            logger.debug(f"Performance monitoring niedostępny: {e}")
            self._available = False

    def is_available(self) -> bool:
        """Sprawdza czy performance monitoring jest dostępny."""
        return self._available

    def create_metric(self, *args, **kwargs) -> Optional[Any]:
        """Tworzy metric jeśli dostępny."""
        if self._available and self._metric:
            try:
                return self._metric(*args, **kwargs)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"Błąd tworzenia performance metric: {e}")
        return None

    def safe_call(self, method_name: str, *args, **kwargs) -> Optional[Any]:
        """Bezpieczne wywołanie metody na metric jeśli dostępna."""
        try:
            if self._available and hasattr(self._metric, method_name):
                method = getattr(self._metric, method_name)
                return method(*args, **kwargs)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.debug(f"Performance metric call failed: {e}")
        return None


# Globalna instancja dla całej aplikacji
_performance_metric = SafePerformanceMetric()


def get_performance_metric() -> SafePerformanceMetric:
    """Getter dla globalnej instancji performance metric."""
    return _performance_metric
