"""
Service odpowiedzialny za skanowanie katalogów i parowanie plików.
Separacja logiki biznesowej od UI zgodnie z Etapem 2 corrections.md
"""

import logging
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from src.logic import scanner
from src.logic.scanner_cache import ThreadSafeCache
from src.models.file_pair import FilePair
from src.models.special_folder import SpecialFolder
from src.utils.path_validator import PathValidator


@dataclass
class ScanResult:
    """Wynik operacji skanowania."""

    file_pairs: List[FilePair]
    unpaired_archives: List[str]
    unpaired_previews: List[str]
    special_folders: List[SpecialFolder]
    scan_time: float
    total_files: int
    error_message: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Metryki wydajności skanowania."""

    scan_duration: float
    cache_hit_ratio: float
    memory_usage_mb: float
    files_per_second: float
    cache_entries: int


@dataclass
class BatchScanResult:
    """Wynik skanowania wielu katalogów."""

    results: Dict[str, ScanResult]
    total_scan_time: float
    total_files: int
    successful_scans: int
    failed_scans: int
    error_messages: List[str]


class ScanningServiceError(Exception):
    """Błąd serwisu skanowania."""

    pass


class ScanningService:
    """Serwis do skanowania katalogów - separacja logiki biznesowej od UI."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cache = ThreadSafeCache()
        self._performance_history: List[PerformanceMetrics] = []

    def scan_directory(
        self,
        path: str,
        max_depth: int = -1,
        strategy: str = "first_match",
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> ScanResult:
        """
        Skanuje katalog w poszukiwaniu par plików.

        Args:
            path: Ścieżka do katalogu
            max_depth: Maksymalna głębokość skanowania
                      (-1 = bez limitu, 0 = tylko główny folder)
            strategy: Strategia parowania ("first_match", "best_match",
                     "size_priority")
            progress_callback: Callback dla raportowania postępu

        Returns:
            ScanResult: Wynik skanowania

        Raises:
            ScanningServiceError: Gdy wystąpi błąd podczas skanowania
        """
        try:
            # Walidacja parametrów
            self._validate_scan_parameters(path, max_depth, strategy)

            # Walidacja ścieżki używając centralnego validatora
            validation_errors = self.validate_directory_path(path)
            if validation_errors:
                error_msg = (
                    f"Błąd walidacji ścieżki {path}: {'; '.join(validation_errors)}"
                )
                self.logger.error(error_msg)
                return ScanResult(
                    file_pairs=[],
                    unpaired_archives=[],
                    unpaired_previews=[],
                    special_folders=[],
                    scan_time=0.0,
                    total_files=0,
                    error_message=error_msg,
                )

            # Sprawdź cache przed skanowaniem
            cache_hit = self.cache.get_scan_result(path, strategy) is not None

            # Wykonaj skanowanie
            self.logger.info(f"Rozpoczynam skanowanie: {path} (strategy: {strategy})")

            start_time = time.time()
            result = scanner.scan_folder_for_pairs(
                path,
                max_depth=max_depth,
                pair_strategy=strategy,
                progress_callback=progress_callback,
            )
            scan_time = time.time() - start_time

            # Zwróć ustrukturyzowany wynik
            total_files = len(result[0]) * 2 + len(result[1]) + len(result[2])
            scan_result = ScanResult(
                file_pairs=result[0],
                unpaired_archives=result[1],
                unpaired_previews=result[2],
                special_folders=result[3],
                scan_time=scan_time,
                total_files=total_files,
            )

            # Zapisz w cache
            self.cache.set_scan_result(path, strategy, result)

            # Oblicz metryki wydajności
            self._record_performance_metrics(scan_result, cache_hit)

            self.logger.info(
                f"Skanowanie zakończone: {len(scan_result.file_pairs)} par, "
                f"{len(scan_result.unpaired_archives)} niesparowanych archiwów, "
                f"{len(scan_result.unpaired_previews)} niesparowanych podglądów, "
                f"{len(scan_result.special_folders)} specjalnych folderów"
            )

            return scan_result

        except Exception as e:
            error_msg = f"Błąd skanowania katalogu {path}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)

            # Rzuć wyjątek dla poważnych błędów
            if isinstance(e, (OSError, PermissionError, FileNotFoundError)):
                raise ScanningServiceError(error_msg) from e

            return ScanResult(
                file_pairs=[],
                unpaired_archives=[],
                unpaired_previews=[],
                special_folders=[],
                scan_time=0.0,
                total_files=0,
                error_message=error_msg,
            )

    def scan_multiple_directories(
        self,
        paths: List[str],
        max_depth: int = -1,
        strategy: str = "first_match",
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> BatchScanResult:
        """
        Skanuje wiele katalogów jednocześnie.

        Args:
            paths: Lista ścieżek do katalogów
            max_depth: Maksymalna głębokość skanowania
            strategy: Strategia parowania
            progress_callback: Callback dla raportowania postępu

        Returns:
            BatchScanResult: Wynik skanowania wszystkich katalogów
        """
        if not paths:
            self.logger.warning("Próba skanowania pustej listy katalogów")
            return BatchScanResult(
                results={},
                total_scan_time=0.0,
                total_files=0,
                successful_scans=0,
                failed_scans=0,
                error_messages=["Brak katalogów do skanowania"],
            )

        results = {}
        error_messages = []
        successful_scans = 0
        failed_scans = 0
        total_files = 0
        start_time = time.time()

        self.logger.info(f"Rozpoczynam skanowanie {len(paths)} katalogów")

        for i, path in enumerate(paths):
            try:
                # Wywołaj progress callback
                if progress_callback:
                    progress_callback(
                        int((i / len(paths)) * 100),
                        f"Skanowanie katalogu {i+1}/{len(paths)}: {path}",
                    )

                # Skanuj pojedynczy katalog
                result = self.scan_directory(path, max_depth, strategy)
                results[path] = result
                total_files += result.total_files

                if result.error_message:
                    failed_scans += 1
                    error_messages.append(f"{path}: {result.error_message}")
                else:
                    successful_scans += 1

            except Exception as e:
                failed_scans += 1
                error_msg = f"Błąd skanowania {path}: {str(e)}"
                error_messages.append(error_msg)
                self.logger.error(error_msg, exc_info=True)

                # Dodaj pusty wynik dla błędnego katalogu
                results[path] = ScanResult(
                    file_pairs=[],
                    unpaired_archives=[],
                    unpaired_previews=[],
                    special_folders=[],
                    scan_time=0.0,
                    total_files=0,
                    error_message=error_msg,
                )

        total_scan_time = time.time() - start_time

        # Final progress callback
        if progress_callback:
            progress_callback(100, "Skanowanie zakończone")

        self.logger.info(
            f"Skanowanie batch zakończone: {successful_scans} sukcesów, "
            f"{failed_scans} błędów, {total_files} plików w {total_scan_time:.2f}s"
        )

        return BatchScanResult(
            results=results,
            total_scan_time=total_scan_time,
            total_files=total_files,
            successful_scans=successful_scans,
            failed_scans=failed_scans,
            error_messages=error_messages,
        )

    def scan_directory_async(
        self,
        path: str,
        max_depth: int = -1,
        strategy: str = "first_match",
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> ScanResult:
        """
        Asynchroniczne skanowanie katalogu z progress callback.

        Args:
            path: Ścieżka do katalogu
            max_depth: Maksymalna głębokość skanowania
            strategy: Strategia parowania
            progress_callback: Callback dla raportowania postępu

        Returns:
            ScanResult: Wynik skanowania
        """
        # Dla teraz deleguje do synchronicznej wersji
        # W przyszłości można dodać prawdziwe async z asyncio
        return self.scan_directory(path, max_depth, strategy, progress_callback)

    def refresh_directory(self, path: str) -> ScanResult:
        """
        Odświeża katalog bez pełnego ponownego skanowania (jeśli możliwe).

        Args:
            path: Ścieżka do katalogu

        Returns:
            ScanResult: Wynik odświeżania
        """
        try:
            self.logger.info(f"Odświeżam katalog: {path}")

            # Wyczyść cache dla tego katalogu
            self.cache.remove_entry(path)

            # Wykonaj ponowne skanowanie z domyślnymi ustawieniami
            return self.scan_directory(path)

        except Exception as e:
            error_msg = f"Błąd odświeżania katalogu {path}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)

            return ScanResult(
                file_pairs=[],
                unpaired_archives=[],
                unpaired_previews=[],
                special_folders=[],
                scan_time=0.0,
                total_files=0,
                error_message=error_msg,
            )

    def get_scan_statistics(self, path: str) -> dict:
        """
        Zwraca statystyki ostatniego skanowania dla katalogu.

        Args:
            path: Ścieżka do katalogu

        Returns:
            dict: Statystyki skanowania
        """
        try:
            # Pobierz statystyki cache
            cache_stats = self.cache.get_statistics()

            # Sprawdź czy katalog jest w cache
            cache_hit = self.cache.get_file_map(path) is not None

            stats = {
                "path": path,
                "cache_hit": cache_hit,
                "cache_statistics": cache_stats,
                "performance_metrics": self._get_latest_performance_metrics(),
                "supported_extensions": {
                    "archives": scanner.ARCHIVE_EXTENSIONS,
                    "previews": scanner.PREVIEW_EXTENSIONS,
                },
            }

            self.logger.debug(f"Pobrano statystyki dla {path}: cache_hit={cache_hit}")
            return stats

        except Exception as e:
            error_msg = f"Błąd pobierania statystyk: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {"error": error_msg}

    def clear_all_caches(self) -> bool:
        """
        Czyści wszystkie cache skanowania.

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            scanner.clear_cache()
            self.logger.info("Cache skanowania wyczyszczony")
            return True

        except Exception as e:
            error_msg = f"Błąd czyszczenia cache: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False

    def get_performance_metrics(self) -> List[PerformanceMetrics]:
        """
        Zwraca historię metryk wydajności.

        Returns:
            List[PerformanceMetrics]: Lista metryk wydajności
        """
        return self._performance_history.copy()

    def clear_performance_history(self) -> None:
        """Czyści historię metryk wydajności."""
        self._performance_history.clear()
        self.logger.info("Historia metryk wydajności wyczyszczona")

    def validate_directory_path(self, path: str) -> List[str]:
        """
        Waliduje ścieżkę katalogu używając centralnego validatora.

        Args:
            path: Ścieżka do walidacji

        Returns:
            List[str]: Lista błędów walidacji (pusta jeśli OK)
        """
        errors = []

        if not path:
            errors.append("Ścieżka jest pusta")
            return errors

        if not PathValidator.validate_directory_path(path):
            errors.append("Katalog nie istnieje lub nie jest dostępny")
            return errors

        if not PathValidator.is_path_accessible(path):
            errors.append("Brak uprawnień do odczytu katalogu")

        return errors

    def _validate_scan_parameters(
        self, path: str, max_depth: int, strategy: str
    ) -> None:
        """Waliduje parametry skanowania."""
        if not path:
            raise ValueError("Ścieżka katalogu nie może być pusta")

        if not isinstance(max_depth, int) or max_depth < -1:
            raise ValueError("max_depth musi być liczbą całkowitą >= -1")

        valid_strategies = ["first_match", "best_match", "size_priority"]
        if strategy not in valid_strategies:
            raise ValueError(
                f"Nieprawidłowa strategia: {strategy}. Dozwolone: {valid_strategies}"
            )

    def _record_performance_metrics(
        self, scan_result: ScanResult, cache_hit: bool
    ) -> None:
        """Zapisuje metryki wydajności dla ostatniego skanowania."""
        try:
            # Pobierz statystyki cache
            cache_stats = self.cache.get_statistics()
            combined_stats = cache_stats.get("combined", {})
            memory_usage = combined_stats.get("memory_usage", {})

            # Oblicz metryki
            cache_hit_ratio = combined_stats.get("combined_hit_ratio", 0.0)
            memory_usage_mb = memory_usage.get("total_memory_mb", 0.0)
            cache_entries = combined_stats.get("total_entries", 0)

            # Oblicz pliki na sekundę
            files_per_second = 0.0
            if scan_result.scan_time > 0:
                files_per_second = scan_result.total_files / scan_result.scan_time

            # Utwórz metryki
            metrics = PerformanceMetrics(
                scan_duration=scan_result.scan_time,
                cache_hit_ratio=cache_hit_ratio,
                memory_usage_mb=memory_usage_mb,
                files_per_second=files_per_second,
                cache_entries=cache_entries,
            )

            # Dodaj do historii (zachowaj ostatnie 100 wpisów)
            self._performance_history.append(metrics)
            if len(self._performance_history) > 100:
                self._performance_history.pop(0)

            # Loguj metryki dla długotrwałych operacji
            if scan_result.scan_time > 5.0:
                self.logger.info(
                    f"Wydajność skanowania: {scan_result.scan_time:.2f}s, "
                    f"{files_per_second:.1f} plików/s, "
                    f"cache hit ratio: {cache_hit_ratio:.1f}%"
                )

        except Exception as e:
            self.logger.warning(f"Błąd zapisywania metryk wydajności: {e}")

    def _get_latest_performance_metrics(self) -> Optional[PerformanceMetrics]:
        """Zwraca najnowsze metryki wydajności."""
        if self._performance_history:
            return self._performance_history[-1]
        return None
