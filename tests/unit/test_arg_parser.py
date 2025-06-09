"""
Testy jednostkowe dla modułu arg_parser.py
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from src.utils.arg_parser import get_app_version, parse_args, setup_logging_from_args


class TestArgParser(unittest.TestCase):
    """Testy dla parsera argumentów linii poleceń"""

    def test_parse_args_defaults(self):
        """Test domyślnych wartości argumentów"""
        # Zapisujemy oryginalne argumenty
        original_argv = sys.argv.copy()

        try:
            # Symulujemy uruchomienie bez argumentów
            sys.argv = ["run_app.py"]
            args = parse_args()

            # Sprawdzamy domyślne wartości
            self.assertFalse(args.debug)
            self.assertEqual(args.log_level, "INFO")
            self.assertFalse(args.no_file_log)
            self.assertEqual(args.log_dir, "logs")
            self.assertIsNone(args.style)
            self.assertFalse(args.no_style)
            self.assertFalse(args.version)
        finally:
            # Przywracamy oryginalne argumenty
            sys.argv = original_argv

    def test_parse_args_with_options(self):
        """Test parsowania z podanymi opcjami"""
        # Zapisujemy oryginalne argumenty
        original_argv = sys.argv.copy()

        try:
            # Symulujemy uruchomienie z argumentami
            sys.argv = [
                "run_app.py",
                "--debug",
                "--log-level",
                "WARNING",
                "--no-file-log",
                "--log-dir",
                "custom_logs",
                "--style",
                "custom.qss",
            ]
            args = parse_args()

            # Sprawdzamy wartości argumentów
            self.assertTrue(args.debug)
            self.assertEqual(args.log_level, "WARNING")
            self.assertTrue(args.no_file_log)
            self.assertEqual(args.log_dir, "custom_logs")
            self.assertEqual(args.style, "custom.qss")
            self.assertFalse(args.no_style)
            self.assertFalse(args.version)
        finally:
            # Przywracamy oryginalne argumenty
            sys.argv = original_argv

    @patch("src.utils.logging_config.setup_logging")
    def test_setup_logging_from_args(self, mock_setup_logging):
        """Test konfiguracji logowania na podstawie argumentów"""
        # Tworzenie argumentów typu mock
        args = MagicMock()
        args.log_level = "ERROR"
        args.no_file_log = True
        args.log_dir = "test_logs"
        args.debug = False

        # Wywołanie funkcji
        setup_logging_from_args(args)

        # Sprawdzenie wywołania setup_logging z poprawnymi argumentami
        mock_setup_logging.assert_called_once()
        call_args = mock_setup_logging.call_args[1]
        self.assertEqual(call_args["log_to_file"], False)
        self.assertEqual(call_args["log_dir"], "test_logs")

    @patch("src.utils.logging_config.setup_logging")
    @patch("logging.getLogger")
    def test_setup_logging_debug_mode(self, mock_get_logger, mock_setup_logging):
        """Test konfiguracji logowania w trybie debugowania"""
        # Przygotowanie mocków
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Tworzenie argumentów typu mock
        args = MagicMock()
        args.log_level = "INFO"
        args.no_file_log = False
        args.log_dir = "logs"
        args.debug = True

        # Wywołanie funkcji
        setup_logging_from_args(args)

        # Sprawdzenie konfiguracji poziomu logowania dla modułu skanowania
        mock_get_logger.assert_called_once_with("src.logic.scanner")

    def test_get_app_version_file_exists(self):
        """Test pobierania wersji aplikacji, gdy plik istnieje"""
        # Tworzenie tymczasowego pliku VERSION
        with open("VERSION", "w") as f:
            f.write("2.0.0\n")

        try:
            # Pobieranie wersji
            version = get_app_version()
            self.assertEqual(version, "2.0.0")
        finally:
            # Usunięcie pliku VERSION
            if os.path.exists("VERSION"):
                os.remove("VERSION")

    @patch("os.path.exists", return_value=False)
    def test_get_app_version_file_not_exists(self, mock_exists):
        """Test pobierania wersji aplikacji, gdy plik nie istnieje"""
        version = get_app_version()
        self.assertEqual(version, "1.0.0")  # Domyślna wersja


if __name__ == "__main__":
    unittest.main()
