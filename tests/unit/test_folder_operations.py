"""
Testy dla operacji na folderach w module file_operations.py
"""

import os
import shutil
import tempfile
from unittest.mock import patch

import pytest

from src.logic.file_operations import create_folder, delete_folder, rename_folder


@pytest.fixture
def temp_test_dir():
    """Tworzy tymczasowy katalog testowy."""
    test_dir = tempfile.mkdtemp()
    try:
        yield test_dir
    finally:
        # Posprzątaj po teście
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


@pytest.mark.unit
def test_create_folder_success(temp_test_dir):
    """Test utworzenia folderu."""
    folder_name = "testfolder"
    new_folder_path = create_folder(temp_test_dir, folder_name)

    # Sprawdzenie rezultatu
    assert new_folder_path is not None
    assert os.path.isdir(new_folder_path)
    assert os.path.basename(new_folder_path) == folder_name


@pytest.mark.unit
def test_create_folder_invalid_parent(temp_test_dir):
    """Test tworzenia folderu w nieistniejącym katalogu nadrzędnym."""
    invalid_parent = os.path.join(temp_test_dir, "nonexistent")
    folder_name = "testfolder"

    new_folder_path = create_folder(invalid_parent, folder_name)

    # Sprawdzenie rezultatu
    assert new_folder_path is None


@pytest.mark.unit
def test_create_folder_invalid_name(temp_test_dir):
    """Test tworzenia folderu z nieprawidłową nazwą."""
    invalid_names = ["folder?", "folder|", "folder:", 'folder"', "", " "]

    for name in invalid_names:
        new_folder_path = create_folder(temp_test_dir, name)

        # Sprawdzenie rezultatu
        assert new_folder_path is None
        assert not os.path.exists(os.path.join(temp_test_dir, name))


@pytest.mark.unit
def test_create_folder_exists(temp_test_dir):
    """Test tworzenia folderu, który już istnieje."""
    folder_name = "existing_folder"
    os.makedirs(os.path.join(temp_test_dir, folder_name))

    new_folder_path = create_folder(temp_test_dir, folder_name)

    # Funkcja powinna zwrócić ścieżkę do istniejącego folderu
    assert new_folder_path is not None
    assert os.path.isdir(new_folder_path)
    assert os.path.basename(new_folder_path) == folder_name


@pytest.mark.unit
def test_rename_folder_success(temp_test_dir):
    """Test pomyślnej zmiany nazwy folderu."""
    old_folder_name = "old_folder"
    new_folder_name = "new_folder"

    old_folder_path = os.path.join(temp_test_dir, old_folder_name)
    os.makedirs(old_folder_path)

    new_folder_path = rename_folder(old_folder_path, new_folder_name)

    # Sprawdzenie rezultatu
    assert new_folder_path is not None
    assert os.path.isdir(new_folder_path)
    assert os.path.basename(new_folder_path) == new_folder_name
    assert not os.path.exists(old_folder_path)


@pytest.mark.unit
def test_rename_folder_nonexistent(temp_test_dir):
    """Test zmiany nazwy nieistniejącego folderu."""
    old_folder_path = os.path.join(temp_test_dir, "nonexistent_folder")
    new_folder_name = "new_folder"

    new_folder_path = rename_folder(old_folder_path, new_folder_name)

    # Sprawdzenie rezultatu
    assert new_folder_path is None


@pytest.mark.unit
def test_rename_folder_invalid_name(temp_test_dir):
    """Test zmiany nazwy folderu na nieprawidłową nazwę."""
    old_folder_name = "old_folder"
    old_folder_path = os.path.join(temp_test_dir, old_folder_name)
    os.makedirs(old_folder_path)

    invalid_names = ["folder?", "folder|", "folder:", 'folder"', "", " "]

    for name in invalid_names:
        new_folder_path = rename_folder(old_folder_path, name)

        # Sprawdzenie rezultatu
        assert new_folder_path is None
        assert os.path.exists(
            old_folder_path
        )  # oryginalny folder powinien nadal istnieć


@pytest.mark.unit
def test_rename_folder_target_exists(temp_test_dir):
    """Test zmiany nazwy folderu, gdy docelowy folder już istnieje."""
    old_folder_name = "old_folder"
    new_folder_name = "existing_folder"

    old_folder_path = os.path.join(temp_test_dir, old_folder_name)
    os.makedirs(old_folder_path)

    # Utwórz folder o nazwie docelowej
    os.makedirs(os.path.join(temp_test_dir, new_folder_name))

    new_folder_path = rename_folder(old_folder_path, new_folder_name)

    # Sprawdzenie rezultatu
    assert new_folder_path is None
    assert os.path.exists(old_folder_path)  # oryginalny folder powinien nadal istnieć


@pytest.mark.unit
def test_delete_folder_empty(temp_test_dir):
    """Test usunięcia pustego folderu."""
    folder_name = "empty_folder"
    folder_path = os.path.join(temp_test_dir, folder_name)
    os.makedirs(folder_path)

    result = delete_folder(folder_path)

    # Sprawdzenie rezultatu
    assert result is True
    assert not os.path.exists(folder_path)


@pytest.mark.unit
def test_delete_folder_with_content(temp_test_dir):
    """Test usunięcia folderu z zawartością."""
    folder_name = "nonempty_folder"
    folder_path = os.path.join(temp_test_dir, folder_name)
    os.makedirs(folder_path)

    # Dodaj zawartość do folderu
    with open(os.path.join(folder_path, "testfile.txt"), "w") as f:
        f.write("test content")

    # Najpierw test bez delete_content
    result = delete_folder(folder_path)

    # Sprawdzenie rezultatu
    assert result is False
    assert os.path.exists(folder_path)

    # Teraz test z delete_content=True
    result = delete_folder(folder_path, delete_content=True)

    # Sprawdzenie rezultatu
    assert result is True
    assert not os.path.exists(folder_path)


@pytest.mark.unit
def test_delete_folder_nonexistent(temp_test_dir):
    """Test usunięcia nieistniejącego folderu."""
    folder_path = os.path.join(temp_test_dir, "nonexistent_folder")

    result = delete_folder(folder_path)

    # Sprawdzenie rezultatu - powinno zwrócić True, jeśli folder nie istnieje
    assert result is True
    assert not os.path.exists(folder_path)


@pytest.mark.unit
def test_delete_folder_permission_error(temp_test_dir):
    """Test usunięcia folderu, do którego nie mamy uprawnień."""
    folder_name = "protected_folder"
    folder_path = os.path.join(temp_test_dir, folder_name)
    os.makedirs(folder_path)

    # Mockujemy os.rmdir aby zasymulować brak uprawnień
    with patch("os.rmdir") as mock_rmdir:
        mock_rmdir.side_effect = PermissionError("Brak uprawnień")

        result = delete_folder(folder_path)

        # Sprawdzenie rezultatu
        assert result is False
