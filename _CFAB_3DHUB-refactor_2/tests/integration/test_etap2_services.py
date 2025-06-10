"""
Testy integracyjne dla Etapu 2 - weryfikacja działania nowych serwisów.
Test separacji logiki biznesowej od UI.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from src.models.file_pair import FilePair
from src.services.file_operations_service import FileOperationsService
from src.services.scanning_service import ScanningService, ScanResult


class TestEtap2Services(unittest.TestCase):
    """Testy integracyjne dla serwisów wprowadzonych w Etapie 2."""

    def setUp(self):
        """Przygotowanie testów."""
        self.file_ops_service = FileOperationsService()
        self.scanning_service = ScanningService()

        # Utwórz tymczasowy katalog dla testów
        self.test_dir = tempfile.mkdtemp(prefix="etap2_test_")

    def tearDown(self):
        """Czyszczenie po testach."""
        # Usuń tymczasowy katalog
        import shutil

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_file_operations_service_initialization(self):
        """Test inicjalizacji FileOperationsService."""
        service = FileOperationsService()

        # Sprawdź czy serwis ma logger
        self.assertIsNotNone(service.logger)
        self.assertEqual(service.logger.name, "src.services.file_operations_service")

    def test_scanning_service_initialization(self):
        """Test inicjalizacji ScanningService."""
        service = ScanningService()

        # Sprawdź czy serwis ma logger i scanner
        self.assertIsNotNone(service.logger)
        self.assertIsNotNone(service.scanner)
        self.assertEqual(service.logger.name, "src.services.scanning_service")

    def test_validate_file_paths_empty_paths(self):
        """Test walidacji pustych ścieżek."""
        errors = self.file_ops_service.validate_file_paths("", None)

        self.assertGreater(len(errors), 0)
        self.assertIn("Pusta ścieżka", errors[0])

    def test_validate_file_paths_nonexistent(self):
        """Test walidacji nieistniejących ścieżek."""
        fake_path = "/nie/istniejaca/sciezka/plik.txt"
        errors = self.file_ops_service.validate_file_paths(fake_path)

        self.assertGreater(len(errors), 0)
        self.assertTrue(any("nie istnieje" in error for error in errors))

    def test_validate_directory_path_empty(self):
        """Test walidacji pustej ścieżki katalogu."""
        errors = self.scanning_service.validate_directory_path("")

        self.assertGreater(len(errors), 0)
        self.assertIn("Ścieżka jest pusta", errors)

    def test_validate_directory_path_nonexistent(self):
        """Test walidacji nieistniejącego katalogu."""
        errors = self.scanning_service.validate_directory_path(
            "/nie/istniejacy/katalog"
        )

        self.assertGreater(len(errors), 0)
        self.assertIn("Katalog nie istnieje", errors)

    def test_validate_directory_path_existing(self):
        """Test walidacji istniejącego katalogu."""
        errors = self.scanning_service.validate_directory_path(self.test_dir)

        # Nie powinno być błędów dla istniejącego katalogu
        self.assertEqual(len(errors), 0)

    def test_scan_nonexistent_directory(self):
        """Test skanowania nieistniejącego katalogu."""
        result = self.scanning_service.scan_directory("/nie/istniejacy/katalog")

        # Sprawdź czy zwrócono poprawny ScanResult z błędem
        self.assertIsInstance(result, ScanResult)
        self.assertEqual(len(result.file_pairs), 0)
        self.assertIsNotNone(result.error_message)
        self.assertIn("nie istnieje", result.error_message)

    def test_scan_existing_empty_directory(self):
        """Test skanowania istniejącego pustego katalogu."""
        result = self.scanning_service.scan_directory(self.test_dir)

        # Sprawdź czy zwrócono poprawny ScanResult
        self.assertIsInstance(result, ScanResult)
        self.assertEqual(len(result.file_pairs), 0)
        self.assertEqual(len(result.unpaired_archives), 0)
        self.assertEqual(len(result.unpaired_previews), 0)
        self.assertIsNone(result.error_message)

    def test_manual_pair_creation(self):
        """Test tworzenia ręcznej pary plików."""
        # Utwórz tymczasowe pliki
        archive_path = os.path.join(self.test_dir, "test.zip")
        preview_path = os.path.join(self.test_dir, "test.jpg")

        # Utwórz pliki
        with open(archive_path, "w") as f:
            f.write("test archive")
        with open(preview_path, "w") as f:
            f.write("test preview")

        # Test tworzenia pary
        pair = self.file_ops_service.manual_pair(archive_path, preview_path)

        self.assertIsNotNone(pair)
        self.assertIsInstance(pair, FilePair)
        self.assertEqual(pair.archive_path, archive_path)
        self.assertEqual(pair.preview_path, preview_path)

    def test_manual_pair_nonexistent_files(self):
        """Test tworzenia pary z nieistniejących plików."""
        pair = self.file_ops_service.manual_pair(
            "/nie/istniejacy/archiwum.zip", "/nie/istniejacy/podglad.jpg"
        )

        self.assertIsNone(pair)

    def test_bulk_delete_empty_list(self):
        """Test bulk delete z pustą listą."""
        deleted, errors = self.file_ops_service.bulk_delete([])

        self.assertEqual(len(deleted), 0)
        self.assertEqual(len(errors), 0)

    def test_bulk_move_invalid_destination(self):
        """Test bulk move z nieprawidłową destinacją."""
        # Utwórz fikcyjną parę
        pair = FilePair()
        pair.archive_path = "/fake/path.zip"
        pair.preview_path = "/fake/path.jpg"

        # Test z nieprawidłową destinacją (katalog w którym nie można utworzyć nowego)
        moved, errors = self.file_ops_service.bulk_move([pair], "/root/niedostepny")

        self.assertEqual(len(moved), 0)
        self.assertGreater(len(errors), 0)

    def test_cleanup_empty_directories(self):
        """Test czyszczenia pustych katalogów."""
        # Utwórz pusty podkatalog
        empty_dir = os.path.join(self.test_dir, "pusty_katalog")
        os.makedirs(empty_dir)

        # Sprawdź czy katalog istnieje
        self.assertTrue(os.path.exists(empty_dir))

        # Uruchom czyszczenie
        removed_count = self.file_ops_service.cleanup_empty_directories(self.test_dir)

        # Sprawdź czy katalog został usunięty
        self.assertGreater(removed_count, 0)
        self.assertFalse(os.path.exists(empty_dir))

    def test_get_scan_statistics(self):
        """Test pobierania statystyk skanowania."""
        stats = self.scanning_service.get_scan_statistics(self.test_dir)

        self.assertIsInstance(stats, dict)
        self.assertIn("path", stats)
        self.assertIn("cache_hit", stats)
        self.assertEqual(stats["path"], self.test_dir)

    def test_clear_all_caches(self):
        """Test czyszczenia cache."""
        result = self.scanning_service.clear_all_caches()

        self.assertTrue(result)

    @patch("src.services.scanning_service.Scanner")
    def test_scanning_service_error_handling(self, mock_scanner_class):
        """Test obsługi błędów w ScanningService."""
        # Skonfiguruj mock żeby rzucał błąd
        mock_scanner = MagicMock()
        mock_scanner.scan_directory.side_effect = Exception("Test error")
        mock_scanner_class.return_value = mock_scanner

        # Utwórz nowy serwis z mock'iem
        service = ScanningService()

        # Test skanowania z błędem
        result = service.scan_directory(self.test_dir)

        self.assertIsInstance(result, ScanResult)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Test error", result.error_message)


if __name__ == "__main__":
    unittest.main()
