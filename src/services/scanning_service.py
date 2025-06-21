"""
Service odpowiedzialny za skanowanie katalogów i parowanie plików.
Separacja logiki biznesowej od UI zgodnie z Etapem 2 corrections.md
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from src.logic import scanner
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


class ScanningService:
    """Serwis do skanowania katalogów - separacja logiki biznesowej od UI."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Scanner to funkcje, nie klasa!

    def scan_directory(
        self, path: str, max_depth: int = -1, strategy: str = "first_match"
    ) -> ScanResult:
        """
        Skanuje katalog w poszukiwaniu par plików.

        Args:
            path: Ścieżka do katalogu
            max_depth: Maksymalna głębokość skanowania (-1 = bez limitu, 0 = tylko główny folder)
            strategy: Strategia parowania ("first_match", "best_match", "size_priority")

        Returns:
            ScanResult: Wynik skanowania
        """
        try:
            # Walidacja ścieżki używając centralnego validatora
            if not PathValidator.validate_directory_path(path):
                return ScanResult(
                    file_pairs=[],
                    unpaired_archives=[],
                    unpaired_previews=[],
                    special_folders=[],
                    scan_time=0.0,
                    total_files=0,
                    error_message=f"Katalog nie istnieje lub nie jest dostępny: {path}",
                )

            # Wykonaj skanowanie
            self.logger.info(f"Rozpoczynam skanowanie: {path}")

            start_time = time.time()
            result = scanner.scan_folder_for_pairs(
                path, max_depth=max_depth, pair_strategy=strategy
            )
            scan_time = time.time() - start_time

            # Zwróć ustrukturyzowany wynik
            scan_result = ScanResult(
                file_pairs=result[0],
                unpaired_archives=result[1],
                unpaired_previews=result[2],
                special_folders=result[3],
                scan_time=scan_time,
                total_files=len(result[0]) * 2 + len(result[1]) + len(result[2]),
            )

            self.logger.info(
                f"Skanowanie zakończone: {len(scan_result.file_pairs)} par, "
                f"{len(scan_result.unpaired_archives)} niesparowanych archiwów, "
                f"{len(scan_result.unpaired_previews)} niesparowanych podglądów, "
                f"{len(scan_result.special_folders)} specjalnych folderów"
            )

            return scan_result

        except Exception as e:
            error_msg = f"Błąd skanowania katalogu {path}: {str(e)}"
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

    def refresh_directory(self, path: str) -> ScanResult:
        """
        Odświeża katalog bez pełnego ponownego skanowania (jeśli możliwe).

        Args:
            path: Ścieżka do katalogu

        Returns:
            ScanResult: Wynik odświeżania
        """
        try:
            # Wyczyść cache dla tego katalogu
            self.scanner.clear_cache_for_directory(path)

            # Wykonaj ponowne skanowanie z domyślnymi ustawieniami
            return self.scan_directory(path)

        except Exception as e:
            error_msg = f"Błąd odświeżania katalogu {path}: {str(e)}"
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

    def get_scan_statistics(self, path: str) -> dict:
        """
        Zwraca statystyki ostatniego skanowania dla katalogu.

        Args:
            path: Ścieżka do katalogu

        Returns:
            dict: Statystyki skanowania
        """
        try:
            stats = {
                "path": path,
                "cache_hit": self.scanner.is_cached(path),
                "last_scan_time": getattr(self.scanner, "last_scan_time", 0.0),
                "cache_size": len(getattr(self.scanner, "_scan_cache", {})),
                "supported_extensions": {
                    "archives": self.scanner.archive_extensions,
                    "previews": self.scanner.preview_extensions,
                },
            }

            return stats

        except Exception as e:
            self.logger.error(f"Błąd pobierania statystyk: {str(e)}")
            return {"error": str(e)}

    def clear_all_caches(self) -> bool:
        """
        Czyści wszystkie cache skanowania.

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            self.scanner.clear_cache()
            self.logger.info("Cache skanowania wyczyszczony")
            return True

        except Exception as e:
            self.logger.error(f"Błąd czyszczenia cache: {str(e)}")
            return False

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
