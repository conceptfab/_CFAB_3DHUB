"""
Testy dla modułu file_operations.py
"""

import os
from unittest.mock import patch

import pytest

from src.logic import file_operations
from src.models.file_pair import FilePair


@pytest.fixture
def fake_fs_setup(fs):
    """Konfiguruje fałszywy system plików dla testów."""
    # Używamy os.path.join, aby tworzyć ścieżki neutralne dla systemu
    base_dir = os.path.join("/test_data")
    target_dir = os.path.join("/test_data_target")
    fs.create_dir(os.path.join(base_dir, "subfolder"))
    fs.create_file(os.path.join(base_dir, "archive1.zip"), contents="zip_data")
    fs.create_file(os.path.join(base_dir, "archive1.jpg"), contents="preview_data")
    fs.create_file(os.path.join(base_dir, "archive2.rar"), contents="rar_data")
    fs.create_file(os.path.join(base_dir, "existing_file.zip"), contents="existing")
    fs.create_dir(target_dir)
    return fs, base_dir, target_dir


class TestRenameFilePair:
    def test_rename_pair_success(self, fake_fs_setup):
        fs, base_dir, _ = fake_fs_setup
        old_archive = os.path.join(base_dir, "archive1.zip")
        old_preview = os.path.join(base_dir, "archive1.jpg")
        new_base_name = "new_name"

        result = file_operations.rename_file_pair(
            old_archive, old_preview, new_base_name
        )

        assert result is not None
        new_archive, new_preview = result

        expected_new_archive = os.path.join(base_dir, "new_name.zip")
        expected_new_preview = os.path.join(base_dir, "new_name.jpg")

        assert new_archive == expected_new_archive
        assert new_preview == expected_new_preview
        assert fs.exists(new_archive)
        assert fs.exists(new_preview)
        assert not fs.exists(old_archive)
        assert not fs.exists(old_preview)

    def test_rename_archive_only_success(self, fake_fs_setup):
        fs, base_dir, _ = fake_fs_setup
        old_archive = os.path.join(base_dir, "archive2.rar")

        result = file_operations.rename_file_pair(old_archive, None, "archive2_renamed")

        assert result is not None
        new_archive, new_preview = result

        expected_new_archive = os.path.join(base_dir, "archive2_renamed.rar")

        assert new_archive == expected_new_archive
        assert new_preview is None
        assert fs.exists(new_archive)
        assert not fs.exists(old_archive)

    def test_rename_fails_if_target_exists(self, fake_fs_setup):
        fs, base_dir, _ = fake_fs_setup
        old_archive = os.path.join(base_dir, "archive1.zip")
        result = file_operations.rename_file_pair(old_archive, None, "existing_file")
        assert result is None
        assert fs.exists(old_archive)  # Plik nie powinien być ruszony


class TestDeleteFilePair:
    def test_delete_pair_success(self, fake_fs_setup):
        fs, base_dir, _ = fake_fs_setup
        archive_to_delete = os.path.join(base_dir, "archive1.zip")
        preview_to_delete = os.path.join(base_dir, "archive1.jpg")

        result = file_operations.delete_file_pair(archive_to_delete, preview_to_delete)

        assert result is True
        assert not fs.exists(archive_to_delete)
        assert not fs.exists(preview_to_delete)

    def test_delete_nonexistent_pair(self, fake_fs_setup):
        # fs jest potrzebne, żeby pyfakefs działało, nawet jeśli nieużywane wprost
        fs, _, _ = fake_fs_setup
        result = file_operations.delete_file_pair(
            "/non/existent.zip", "/non/existent.jpg"
        )
        assert result is True


class TestMoveFilePair:
    def test_move_pair_success(self, fake_fs_setup):
        fs, base_dir, target_dir = fake_fs_setup
        old_archive = os.path.join(base_dir, "archive1.zip")
        old_preview = os.path.join(base_dir, "archive1.jpg")

        result = file_operations.move_file_pair(old_archive, old_preview, target_dir)

        assert result is not None
        new_archive, new_preview = result

        expected_new_archive = os.path.join(target_dir, "archive1.zip")
        expected_new_preview = os.path.join(target_dir, "archive1.jpg")

        assert new_archive == expected_new_archive
        assert new_preview == expected_new_preview
        assert fs.exists(new_archive)
        assert fs.exists(new_preview)
        assert not fs.exists(old_archive)
        assert not fs.exists(old_preview)

    def test_move_fails_if_target_dir_not_exists(self, fake_fs_setup):
        fs, base_dir, _ = fake_fs_setup
        old_archive = os.path.join(base_dir, "archive1.zip")
        result = file_operations.move_file_pair(old_archive, None, "/non_existent_dir")
        assert result is None
        assert fs.exists(old_archive)

    def test_move_fails_if_target_file_exists(self, fake_fs_setup):
        fs, base_dir, target_dir = fake_fs_setup
        # Stwórz plik w folderze docelowym, który będzie powodował konflikt
        fs.create_file(os.path.join(target_dir, "archive1.zip"))

        old_archive = os.path.join(base_dir, "archive1.zip")
        old_preview = os.path.join(base_dir, "archive1.jpg")

        result = file_operations.move_file_pair(old_archive, old_preview, target_dir)
        assert result is None
        assert fs.exists(old_archive)  # Pliki źródłowe nietknięte
        assert fs.exists(old_preview)
        assert fs.exists(os.path.join(target_dir, "archive1.zip"))


class TestManuallyPairFiles:
    def test_manual_pair_with_rename(self, fake_fs_setup):
        fs, base_dir, _ = fake_fs_setup
        # Używamy nowej nazwy, aby uniknąć konfliktu z 'archive1.jpg' z fixtury
        archive_path_str = os.path.join(base_dir, "new_archive.zip")
        fs.create_file(archive_path_str)

        preview_path_str = os.path.join(base_dir, "different_name.jpg")
        fs.create_file(preview_path_str, contents="preview")

        result = file_operations.manually_pair_files(
            archive_path_str, preview_path_str, base_dir
        )

        assert isinstance(result, FilePair)
        assert result.get_base_name() == "new_archive"

        expected_preview_path = os.path.join(base_dir, "new_archive.jpg")
        assert fs.exists(expected_preview_path)
        assert not fs.exists(preview_path_str)
        assert result.get_preview_path() == expected_preview_path

    def test_manual_pair_no_rename_needed(self, fake_fs_setup):
        fs, base_dir, _ = fake_fs_setup
        archive_path = os.path.join(base_dir, "archive1.zip")
        preview_path = os.path.join(base_dir, "archive1.jpg")

        result = file_operations.manually_pair_files(
            archive_path, preview_path, base_dir
        )

        assert isinstance(result, FilePair)
        assert result.get_base_name() == "archive1"
        assert result.get_preview_path() == preview_path
        assert fs.exists(preview_path)  # Upewnij się, że plik nie został usunięty

    def test_manual_pair_fails_if_target_exists(self, fake_fs_setup):
        fs, base_dir, _ = fake_fs_setup
        # Już istnieje /test_data/archive1.jpg
        archive_path = os.path.join(base_dir, "archive1.zip")
        # fs.create_file zwraca obiekt pliku, my potrzebujemy ścieżki (string)
        preview_to_rename_path_str = os.path.join(base_dir, "another.jpg")
        fs.create_file(preview_to_rename_path_str)

        result = file_operations.manually_pair_files(
            archive_path, preview_to_rename_path_str, base_dir
        )

        assert result is None
        assert fs.exists(
            preview_to_rename_path_str
        )  # Plik nie powinien być przemianowany
        assert fs.exists(
            os.path.join(base_dir, "archive1.jpg")
        )  # Istniejący plik nietknięty


class TestFileOperations:

    def test_open_archive_externally_nonexistent_file(self):
        """Test otwierania nieistniejącego pliku."""
        non_existent_path = "/path/to/non_existent_file.zip"
        result = file_operations.open_archive_externally(non_existent_path)
        assert result is False

    @patch("os.path.exists")
    @patch("platform.system")
    @patch("os.startfile")
    def test_open_archive_externally_windows(
        self, mock_startfile, mock_system, mock_exists
    ):
        """Test otwierania pliku na Windowsie."""
        # Konfiguracja mocków
        mock_exists.return_value = True
        mock_system.return_value = "Windows"

        # Wywołanie testowanej funkcji
        result = file_operations.open_archive_externally("test_file.zip")

        # Sprawdzenie wyników
        assert result is True
        mock_startfile.assert_called_once_with("test_file.zip")

    @patch("os.path.exists")
    @patch("platform.system")
    @patch("PyQt6.QtGui.QDesktopServices.openUrl")
    def test_open_archive_externally_other_os(
        self, mock_openurl, mock_system, mock_exists
    ):
        """Test otwierania pliku na innych systemach operacyjnych."""
        # Konfiguracja mocków
        mock_exists.return_value = True
        mock_system.return_value = "Linux"
        mock_openurl.return_value = True

        # Wywołanie testowanej funkcji
        result = file_operations.open_archive_externally("test_file.zip")

        # Sprawdzenie wyników
        assert result is True
        mock_openurl.assert_called_once()

    @patch("os.path.exists")
    @patch("platform.system")
    @patch("PyQt6.QtGui.QDesktopServices.openUrl")
    def test_open_archive_externally_qt_failure(
        self, mock_openurl, mock_system, mock_exists
    ):
        """Test gdy otwarcie pliku przez Qt się nie powiedzie."""
        # Konfiguracja mocków
        mock_exists.return_value = True
        mock_system.return_value = "Linux"
        mock_openurl.return_value = False

        # Wywołanie testowanej funkcji
        result = file_operations.open_archive_externally("test_file.zip")

        # Sprawdzenie wyników
        assert result is False
        mock_openurl.assert_called_once()

    @patch("os.path.exists")
    @patch("platform.system")
    @patch("os.startfile")
    def test_open_archive_externally_exception(
        self, mock_startfile, mock_system, mock_exists
    ):
        """Test obsługi wyjątku podczas otwierania pliku."""
        # Konfiguracja mocków
        mock_exists.return_value = True
        mock_system.return_value = "Windows"
        mock_startfile.side_effect = Exception("Test exception")

        # Wywołanie testowanej funkcji
        result = file_operations.open_archive_externally("test_file.zip")

        # Sprawdzenie wyników
        assert result is False
        mock_startfile.assert_called_once_with("test_file.zip")
