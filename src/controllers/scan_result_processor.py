"""
ScanResultProcessor - wydzielony processor do obsługi wyników skanowania.
Rozdziela odpowiedzialności z MainWindowController.
"""

import logging
from typing import List

from src.models.file_pair import FilePair
from src.models.special_folder import SpecialFolder
from src.services.scanning_service import ScanResult


class ScanResultProcessor:
    """
    Processor odpowiedzialny za przetwarzanie wyników skanowania.
    Wydzielony z głównego kontrolera dla lepszej separacji odpowiedzialności.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def process_scan_result(self, scan_result: ScanResult) -> dict:
        """
        Przetwarza wynik skanowania i przygotowuje dane dla UI.

        Args:
            scan_result: Wynik skanowania z ScanningService

        Returns:
            Słownik z przetworzonymi danymi
        """
        try:
            processed_data = {
                "directory_path": scan_result.directory_path,
                "file_pairs": scan_result.file_pairs,
                "unpaired_archives": scan_result.unpaired_archives,
                "unpaired_previews": scan_result.unpaired_previews,
                "special_folders": scan_result.special_folders or [],
                "error_message": scan_result.error_message,
                "statistics": self._calculate_statistics(scan_result),
            }

            self.logger.info(
                f"Przetworzono wynik skanowania: {len(scan_result.file_pairs)} "
                f"par, {len(scan_result.unpaired_archives)} archiwów, "
                f"{len(scan_result.unpaired_previews)} podglądów"
            )

            return processed_data

        except Exception as e:
            self.logger.error(f"Błąd przetwarzania wyniku skanowania: {str(e)}")
            return {
                "directory_path": "",
                "file_pairs": [],
                "unpaired_archives": [],
                "unpaired_previews": [],
                "special_folders": [],
                "error_message": f"Błąd przetwarzania: {str(e)}",
                "statistics": {},
            }

    def _calculate_statistics(self, scan_result: ScanResult) -> dict:
        """
        Oblicza statystyki dla wyniku skanowania.

        Args:
            scan_result: Wynik skanowania

        Returns:
            Słownik ze statystykami
        """
        return {
            "total_pairs": len(scan_result.file_pairs),
            "unpaired_archives_count": len(scan_result.unpaired_archives),
            "unpaired_previews_count": len(scan_result.unpaired_previews),
            "special_folders_count": len(scan_result.special_folders or []),
            "total_files": (
                len(scan_result.file_pairs) * 2
                + len(scan_result.unpaired_archives)
                + len(scan_result.unpaired_previews)
            ),
        }

    def validate_scan_result(self, scan_result: ScanResult) -> List[str]:
        """
        Waliduje wynik skanowania i zwraca listę błędów.

        Args:
            scan_result: Wynik skanowania do walidacji

        Returns:
            Lista błędów walidacji (pusta jeśli wszystko OK)
        """
        errors = []

        if not scan_result:
            errors.append("Brak wyniku skanowania")
            return errors

        if scan_result.error_message:
            errors.append(f"Błąd skanowania: {scan_result.error_message}")

        if not scan_result.directory_path:
            errors.append("Brak ścieżki katalogu")

        # Sprawdź czy są jakiekolwiek wyniki
        total_items = (
            len(scan_result.file_pairs)
            + len(scan_result.unpaired_archives)
            + len(scan_result.unpaired_previews)
        )

        if total_items == 0 and not scan_result.error_message:
            self.logger.warning("Skanowanie nie znalazło żadnych plików")

        return errors

    def merge_scan_results(self, results: List[ScanResult]) -> ScanResult:
        """
        Łączy wiele wyników skanowania w jeden.

        Args:
            results: Lista wyników skanowania

        Returns:
            Połączony wynik skanowania
        """
        if not results:
            return ScanResult("", [], [], [], [])

        merged = ScanResult(
            directory_path=results[0].directory_path,
            file_pairs=[],
            unpaired_archives=[],
            unpaired_previews=[],
            special_folders=[],
        )

        for result in results:
            if result.file_pairs:
                merged.file_pairs.extend(result.file_pairs)
            if result.unpaired_archives:
                merged.unpaired_archives.extend(result.unpaired_archives)
            if result.unpaired_previews:
                merged.unpaired_previews.extend(result.unpaired_previews)
            if result.special_folders:
                merged.special_folders.extend(result.special_folders)

        # Usuń duplikaty
        merged.file_pairs = list(set(merged.file_pairs))
        merged.unpaired_archives = list(set(merged.unpaired_archives))
        merged.unpaired_previews = list(set(merged.unpaired_previews))

        self.logger.debug(f"Połączono {len(results)} wyników skanowania")
        return merged
