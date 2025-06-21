"""
Testy dla ETAP 6 file_operations.py - Thread-safe factory pattern, walidacja parametrów, batch operations.
"""

import os
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from src.logic.file_operations import (
    BatchFileOperations,
    FileOperationsFactory,
    create_batch_operations,
    create_folder,
    create_pair_from_files,
    delete_file_pair,
    delete_folder,
    manually_pair_files,
    move_file_pair,
    open_archive_externally,
    open_file,
    open_file_externally,
    open_folder,
    open_folder_externally,
    rename_file_pair,
    rename_folder,
)
from src.models.file_pair import FilePair


class TestFileOperationsFactory(unittest.TestCase):
    """Testy dla thread-safe factory pattern."""

    def setUp(self):
        """Przygotowanie testów."""
        self.factory = FileOperationsFactory()
        self.factory.clear_cache()

    def test_singleton_pattern(self):
        """Test czy factory używa singleton pattern."""
        factory1 = FileOperationsFactory()
        factory2 = FileOperationsFactory()
        self.assertIs(factory1, factory2)

    def test_thread_safe_component_access(self):
        """Test thread-safe dostępu do komponentów."""
        results = []
        errors = []

        def worker():
            try:
                opener = self.factory.get_file_opener()
                system_ops = self.factory.get_file_system_ops()
                pair_ops = self.factory.get_file_pair_ops()
                results.append((opener, system_ops, pair_ops))
            except Exception as e:
                errors.append(e)

        # Uruchom 10 wątków jednocześnie
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Czekaj na zakończenie wszystkich wątków
        for thread in threads:
            thread.join()

        # Sprawdź czy nie było błędów
        self.assertEqual(len(errors), 0, f"Błędy w wątkach: {errors}")
        self.assertEqual(len(results), 10, "Nie wszystkie wątki zwróciły wyniki")

        # Sprawdź czy wszystkie komponenty są tego samego typu
        for opener, system_ops, pair_ops in results:
            self.assertIsInstance(opener, type(results[0][0]))
            self.assertIsInstance(system_ops, type(results[0][1]))
            self.assertIsInstance(pair_ops, type(results[0][2]))

    def test_clear_cache(self):
        """Test czyszczenia cache."""
        # Pobierz komponenty
        opener1 = self.factory.get_file_opener()
        system_ops1 = self.factory.get_file_system_ops()
        pair_ops1 = self.factory.get_file_pair_ops()

        # Wyczyść cache
        self.factory.clear_cache()

        # Pobierz ponownie
        opener2 = self.factory.get_file_opener()
        system_ops2 = self.factory.get_file_system_ops()
        pair_ops2 = self.factory.get_file_pair_ops()

        # Sprawdź czy to nowe instancje
        self.assertIsNot(opener1, opener2)
        self.assertIsNot(system_ops1, system_ops2)
        self.assertIsNot(pair_ops1, pair_ops2)


class TestValidationHelpers(unittest.TestCase):
    """Testy dla funkcji walidacji parametrów."""

    def setUp(self):
        """Przygotowanie testów."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.temp_file, "w") as f:
            f.write("test")

    def tearDown(self):
        """Czyszczenie po testach."""
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_validate_path_success(self):
        """Test poprawnej walidacji ścieżki."""
        # Nie powinno rzucić wyjątku
        open_file_externally(self.temp_file)

    def test_validate_path_empty_string(self):
        """Test walidacji pustego stringa."""
        with self.assertRaises(ValueError):
            open_file_externally("")

    def test_validate_path_none(self):
        """Test walidacji None."""
        with self.assertRaises(ValueError):
            open_file_externally(None)

    def test_validate_path_not_exists(self):
        """Test walidacji nieistniejącej ścieżki."""
        with self.assertRaises(FileNotFoundError):
            open_file_externally("/nie/istniejaca/sciezka")

    def test_validate_filename_success(self):
        """Test poprawnej walidacji nazwy pliku."""
        # Nie powinno rzucić wyjątku
        create_folder(self.temp_dir, "valid_name")

    def test_validate_filename_invalid_chars(self):
        """Test walidacji nazwy z nieprawidłowymi znakami."""
        with self.assertRaises(ValueError):
            create_folder(self.temp_dir, "invalid<>name")

    def test_validate_file_pair_success(self):
        """Test poprawnej walidacji FilePair."""
        file_pair = FilePair(self.temp_file, self.temp_file, self.temp_dir)
        # Nie powinno rzucić wyjątku
        delete_file_pair(file_pair)

    def test_validate_file_pair_wrong_type(self):
        """Test walidacji nieprawidłowego typu."""
        with self.assertRaises(TypeError):
            delete_file_pair("not_a_file_pair")

    def test_validate_file_pair_invalid_paths(self):
        """Test walidacji FilePair z nieprawidłowymi ścieżkami."""
        # Użyj absolutnych ścieżek ale pustych stringów
        file_pair = FilePair(self.temp_file, "", self.temp_dir)
        with self.assertRaises(ValueError):
            delete_file_pair(file_pair)


class TestBatchOperations(unittest.TestCase):
    """Testy dla batch operations."""

    def setUp(self):
        """Przygotowanie testów."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.temp_file, "w") as f:
            f.write("test")

    def tearDown(self):
        """Czyszczenie po testach."""
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_create_batch_operations(self):
        """Test tworzenia batch operations."""
        batch = create_batch_operations()
        self.assertIsInstance(batch, BatchFileOperations)
        self.assertEqual(batch.count(), 0)

    def test_batch_operations_thread_safe(self):
        """Test thread-safety batch operations."""
        batch = create_batch_operations()
        results = []
        errors = []

        def worker():
            try:
                batch.add_create_folder(self.temp_dir, "test_folder")
                batch.add_rename_folder(self.temp_dir, "new_name")
                count = batch.count()
                results.append(count)
            except Exception as e:
                errors.append(e)

        # Uruchom 5 wątków jednocześnie
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Czekaj na zakończenie wszystkich wątków
        for thread in threads:
            thread.join()

        # Sprawdź czy nie było błędów
        self.assertEqual(len(errors), 0, f"Błędy w wątkach: {errors}")

    def test_batch_operations_fluent_interface(self):
        """Test fluent interface batch operations."""
        batch = (
            create_batch_operations()
            .add_create_folder(self.temp_dir, "folder1")
            .add_create_folder(self.temp_dir, "folder2")
            .add_rename_folder(self.temp_dir, "new_name")
        )

        self.assertEqual(batch.count(), 3)
        self.assertIsInstance(batch, BatchFileOperations)

    def test_batch_operations_clear(self):
        """Test czyszczenia batch operations."""
        batch = create_batch_operations()
        batch.add_create_folder(self.temp_dir, "test_folder")
        self.assertEqual(batch.count(), 1)

        batch.clear()
        self.assertEqual(batch.count(), 0)

    def test_batch_operations_execute(self):
        """Test wykonywania batch operations."""
        batch = create_batch_operations().add_create_folder(
            self.temp_dir, "test_folder"
        )

        results = batch.execute()
        self.assertEqual(len(results), 1)
        self.assertEqual(batch.count(), 0)  # Operacje są czyszczone po wykonaniu


class TestDeprecationWarnings(unittest.TestCase):
    """Testy dla deprecation warnings."""

    def setUp(self):
        """Przygotowanie testów."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Czyszczenie po testach."""
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    @patch("src.logic.file_operations.logger")
    def test_deprecation_warning_once(self, mock_logger):
        """Test czy deprecation warning jest logowany tylko raz."""
        # Pierwsze wywołanie - powinno zalogować warning
        create_folder(self.temp_dir, "test", worker_factory=Mock())
        mock_logger.warning.assert_called_once()

        # Drugie wywołanie - nie powinno zalogować warning
        create_folder(self.temp_dir, "test2", worker_factory=Mock())
        mock_logger.warning.assert_called_once()  # Nadal tylko raz

    @patch("src.logic.file_operations.logger")
    def test_backward_compatibility_aliases(self, mock_logger):
        """Test deprecation warnings dla backward compatibility aliases."""
        # Mock _validate_path żeby nie sprawdzać istnienia pliku
        with patch("src.logic.file_operations._validate_path"):
            # Test open_file alias
            open_file("test_path")
            mock_logger.warning.assert_called_with(
                "open_file() is deprecated - use open_file_externally() instead"
            )

            # Test open_folder alias
            open_folder("test_path")
            mock_logger.warning.assert_called_with(
                "open_folder() is deprecated - use open_folder_externally() instead"
            )


class TestErrorHandling(unittest.TestCase):
    """Testy dla proper error handling."""

    def setUp(self):
        """Przygotowanie testów."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Czyszczenie po testach."""
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    @patch("src.logic.file_operations.logger")
    def test_validation_error_logging(self, mock_logger):
        """Test logowania błędów walidacji."""
        with self.assertRaises(ValueError):
            create_folder("", "test")

        mock_logger.error.assert_called_with(
            "create_folder failed - validation error: parent_directory must be a non-empty string"
        )

    @patch("src.logic.file_operations.logger")
    def test_system_error_logging(self, mock_logger):
        """Test logowania błędów systemowych."""
        # Próba utworzenia folderu w nieistniejącym katalogu
        with self.assertRaises(FileNotFoundError):
            create_folder("/nie/istniejacy/katalog", "test")

        mock_logger.error.assert_called_with(
            "create_folder failed - validation error: parent_directory does not exist: /nie/istniejacy/katalog"
        )


if __name__ == "__main__":
    unittest.main()
