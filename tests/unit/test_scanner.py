"""
Testy jednostkowe dla modułu src.logic.scanner
"""

import os
from unittest.mock import ANY, MagicMock, patch

import pytest

from src.logic import scanner
from src.logic.scanner import ScanningInterrupted
from src.models.file_pair import FilePair


@pytest.fixture
def mock_cache():
    """Mock dla funkcji cache z modułu scanner_cache."""
    with patch("src.logic.scanner._cache") as mock:
        yield mock


@pytest.fixture
def sample_file_map():
    """Przykładowa mapa plików do testów."""
    return {
        "C:/test/file1": ["C:/test/file1.stl", "C:/test/file1.jpg"],
        "C:/test/file2": ["C:/test/file2.stl"],
        "C:/test/file3": ["C:/test/file3.jpg"],
    }


def test_collect_files_delegates_to_collect_files_streaming():
    """Test czy collect_files deleguje do collect_files_streaming."""
    with patch("src.logic.scanner.collect_files_streaming") as mock_streaming:
        mock_streaming.return_value = {"test": ["test"]}

        # Wywołanie testowanej funkcji
        result = scanner.collect_files(
            directory="test_dir",
            max_depth=3,
            interrupt_check=lambda: False,
            force_refresh=True,
            progress_callback=lambda p, m: None,
        )

        # Sprawdzenie czy funkcja streaming została wywołana z tymi samymi parametrami
        mock_streaming.assert_called_once_with(
            directory="test_dir",
            max_depth=3,
            interrupt_check=ANY,  # Używamy ANY zamiast lambdy
            force_refresh=True,
            progress_callback=ANY,  # Używamy ANY zamiast lambdy
        )

        # Sprawdzenie czy wynik został przekazany dalej
        assert result == {"test": ["test"]}


def test_collect_files_streaming_delegates_to_core():
    """Test czy collect_files_streaming deleguje do modułu core."""
    with patch("src.logic.scanner_core.collect_files_streaming") as mock_core:
        mock_core.return_value = {"test": ["test"]}

        # Wywołanie testowanej funkcji
        result = scanner.collect_files_streaming(
            directory="test_dir",
            max_depth=3,
            interrupt_check=lambda: False,
            force_refresh=True,
            progress_callback=lambda p, m: None,
        )

        # Sprawdzenie czy funkcja z modułu core została wywołana z tymi samymi parametrami
        mock_core.assert_called_once_with(
            directory="test_dir",
            max_depth=3,
            interrupt_check=ANY,  # Używamy ANY zamiast lambdy
            force_refresh=True,
            progress_callback=ANY,  # Używamy ANY zamiast lambdy
        )

        # Sprawdzenie czy wynik został przekazany dalej
        assert result == {"test": ["test"]}


def test_create_file_pairs_delegates_to_file_pairing():
    """Test czy create_file_pairs deleguje do modułu file_pairing."""
    with patch("src.logic.file_pairing.create_file_pairs") as mock_pairing:
        mock_pairs = [MagicMock(spec=FilePair)]
        mock_processed = {"file1", "file2"}
        mock_pairing.return_value = (mock_pairs, mock_processed)

        file_map = {"path": ["file1", "file2"]}
        base_directory = "base_dir"

        # Wywołanie testowanej funkcji
        pairs, processed = scanner.create_file_pairs(
            file_map=file_map, base_directory=base_directory, pair_strategy="best_match"
        )

        # Sprawdzenie czy funkcja pairing została wywołana z tymi samymi parametrami
        mock_pairing.assert_called_once_with(
            file_map=file_map, base_directory=base_directory, pair_strategy="best_match"
        )

        # Sprawdzenie czy wynik został przekazany dalej
        assert pairs == mock_pairs
        assert processed == mock_processed


def test_scan_folder_for_pairs_delegates_to_core():
    """Test czy scan_folder_for_pairs deleguje do modułu core."""
    with patch("src.logic.scanner_core.scan_folder_for_pairs") as mock_core:
        mock_pairs = [MagicMock(spec=FilePair)]
        mock_unpaired_archives = ["file1.stl"]
        mock_unpaired_previews = ["file2.jpg"]
        mock_core.return_value = (
            mock_pairs,
            mock_unpaired_archives,
            mock_unpaired_previews,
        )

        # Wywołanie testowanej funkcji
        pairs, unpaired_archives, unpaired_previews = scanner.scan_folder_for_pairs(
            directory="test_dir",
            max_depth=3,
            use_cache=True,
            pair_strategy="best_match",
            interrupt_check=lambda: False,
            force_refresh_cache=True,
            progress_callback=lambda p, m: None,
        )

        # Sprawdzenie czy funkcja core została wywołana z tymi samymi parametrami
        mock_core.assert_called_once_with(
            directory="test_dir",
            max_depth=3,
            use_cache=True,
            pair_strategy="best_match",
            interrupt_check=ANY,  # Używamy ANY zamiast lambdy
            force_refresh_cache=True,
            progress_callback=ANY,  # Używamy ANY zamiast lambdy
        )

        # Sprawdzenie czy wynik został przekazany dalej
        assert pairs == mock_pairs
        assert unpaired_archives == mock_unpaired_archives
        assert unpaired_previews == mock_unpaired_previews


def test_clear_cache_delegates_to_scanner_cache():
    """Test czy clear_cache deleguje do modułu scanner_cache."""
    with patch("src.logic.scanner_cache.clear_cache") as mock_clear:
        # Wywołanie testowanej funkcji
        scanner.clear_cache()

        # Sprawdzenie czy funkcja cache została wywołana
        mock_clear.assert_called_once()


def test_identify_unpaired_files_delegates_to_file_pairing():
    """Test czy identify_unpaired_files deleguje do modułu file_pairing."""
    with patch("src.logic.file_pairing.identify_unpaired_files") as mock_identify:
        mock_unpaired_archives = ["file1.stl"]
        mock_unpaired_previews = ["file2.jpg"]
        mock_identify.return_value = (mock_unpaired_archives, mock_unpaired_previews)

        file_map = {"path": ["file1", "file2"]}
        processed_files = {"file1", "file2"}

        # Wywołanie testowanej funkcji
        unpaired_archives, unpaired_previews = scanner.identify_unpaired_files(
            file_map=file_map, processed_files=processed_files
        )

        # Sprawdzenie czy funkcja identify została wywołana z tymi samymi parametrami
        mock_identify.assert_called_once_with(file_map, processed_files)

        # Sprawdzenie czy wynik został przekazany dalej
        assert unpaired_archives == mock_unpaired_archives
        assert unpaired_previews == mock_unpaired_previews


def test_get_scan_statistics_delegates_to_core():
    """Test czy get_scan_statistics deleguje do modułu core."""
    with patch("src.logic.scanner_core.get_scan_statistics") as mock_stats:
        mock_stats.return_value = {"cache_hits": 10, "cache_misses": 5}

        # Wywołanie testowanej funkcji
        stats = scanner.get_scan_statistics()

        # Sprawdzenie czy funkcja stats została wywołana
        mock_stats.assert_called_once()

        # Sprawdzenie czy wynik został przekazany dalej
        assert stats == {"cache_hits": 10, "cache_misses": 5}
