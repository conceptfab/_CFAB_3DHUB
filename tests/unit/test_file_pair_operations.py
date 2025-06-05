"""
Testy dla operacji na parach plików (rename, delete, move) w module file_pair.py
"""

import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from src.models.file_pair import FilePair


@pytest.fixture
def temp_test_dir():
    """Tworzy tymczasowy katalog testowy z plikami testowymi."""
    test_dir = tempfile.mkdtemp()
    try:
        # Utwórz testowy plik archiwum
        archive_path = os.path.join(test_dir, "testarchive.zip")
        with open(archive_path, "wb") as f:
            f.write(b"testdata")

        # Utwórz testowy plik podglądu
        preview_path = os.path.join(test_dir, "testarchive.jpg")
        test_image = Image.new("RGB", (100, 100), color="blue")
        test_image.save(preview_path)

        yield test_dir
    finally:
        # Posprzątaj po teście
        shutil.rmtree(test_dir)


@pytest.mark.unit
def test_rename_success(temp_test_dir):
    """Test pomyślnej zmiany nazwy pary plików."""
    archive_path = os.path.join(temp_test_dir, "testarchive.zip")
    preview_path = os.path.join(temp_test_dir, "testarchive.jpg")

    file_pair = FilePair(archive_path, preview_path, temp_test_dir)

    assert file_pair.rename("newname") is True

    # Sprawdzenie, czy pliki zostały rzeczywiście przemianowane
    assert not os.path.exists(archive_path)
    assert not os.path.exists(preview_path)

    new_archive_path = os.path.join(temp_test_dir, "newname.zip")
    new_preview_path = os.path.join(temp_test_dir, "newname.jpg")

    assert os.path.exists(new_archive_path)
    assert os.path.exists(new_preview_path)

    # Sprawdź, czy wewnętrzne ścieżki zostały zaktualizowane
    assert file_pair.get_base_name() == "newname"
    assert os.path.normpath(file_pair.get_archive_path()) == os.path.normpath(
        "newname.zip"
    )  # ścieżka względna
    assert os.path.normpath(file_pair.get_preview_path()) == os.path.normpath(
        "newname.jpg"
    )  # ścieżka względna


@pytest.mark.unit
def test_rename_empty_name(temp_test_dir):
    """Test zmiany nazwy z pustą nową nazwą."""
    archive_path = os.path.join(temp_test_dir, "testarchive.zip")
    preview_path = os.path.join(temp_test_dir, "testarchive.jpg")

    file_pair = FilePair(archive_path, preview_path, temp_test_dir)

    assert file_pair.rename("") is False

    # Sprawdzenie, czy pliki nie zostały przemianowane
    assert os.path.exists(archive_path)
    assert os.path.exists(preview_path)


@pytest.mark.unit
def test_rename_conflict(temp_test_dir):
    """Test zmiany nazwy, gdy docelowy plik już istnieje."""
    # Utwórz pierwszy zestaw plików
    archive_path1 = os.path.join(temp_test_dir, "testarchive1.zip")
    preview_path1 = os.path.join(temp_test_dir, "testarchive1.jpg")

    with open(archive_path1, "wb") as f:
        f.write(b"testdata1")
    test_image = Image.new("RGB", (100, 100), color="red")
    test_image.save(preview_path1)

    # Utwórz drugi zestaw plików
    archive_path2 = os.path.join(temp_test_dir, "testarchive2.zip")
    preview_path2 = os.path.join(temp_test_dir, "testarchive2.jpg")

    with open(archive_path2, "wb") as f:
        f.write(b"testdata2")
    test_image = Image.new("RGB", (100, 100), color="green")
    test_image.save(preview_path2)

    # Próba zmiany nazwy pierwszej pary na nazwę drugiej pary
    file_pair1 = FilePair(archive_path1, preview_path1, temp_test_dir)

    assert file_pair1.rename("testarchive2") is False

    # Sprawdzenie, czy pliki nie zostały przemianowane
    assert os.path.exists(archive_path1)
    assert os.path.exists(preview_path1)


@pytest.mark.unit
def test_delete_success(temp_test_dir):
    """Test pomyślnego usunięcia pary plików."""
    archive_path = os.path.join(temp_test_dir, "testarchive.zip")
    preview_path = os.path.join(temp_test_dir, "testarchive.jpg")

    file_pair = FilePair(archive_path, preview_path, temp_test_dir)

    assert file_pair.delete() is True

    # Sprawdzenie, czy pliki zostały rzeczywiście usunięte
    assert not os.path.exists(archive_path)
    assert not os.path.exists(preview_path)


@pytest.mark.unit
def test_delete_without_preview(temp_test_dir):
    """Test usunięcia pary plików bez pliku podglądu."""
    archive_path = os.path.join(temp_test_dir, "testarchive_nopreview.zip")

    with open(archive_path, "wb") as f:
        f.write(b"testdata")

    file_pair = FilePair(archive_path, None, temp_test_dir)

    assert file_pair.delete() is True

    # Sprawdzenie, czy plik archiwum został usunięty
    assert not os.path.exists(archive_path)


@pytest.mark.unit
def test_delete_nonexistent_files(temp_test_dir):
    """Test usunięcia nieistniejących plików."""
    # Definiujemy ścieżki do plików, ale nie tworzymy ich fizycznie
    archive_path = os.path.join(temp_test_dir, "nonexistent.zip")
    preview_path = os.path.join(temp_test_dir, "nonexistent.jpg")

    file_pair = FilePair(archive_path, preview_path, temp_test_dir)

    # Powinno zwrócić True, nawet jeśli pliki nie istnieją
    assert file_pair.delete() is True


@pytest.mark.unit
def test_move_success(temp_test_dir):
    """Test pomyślnego przeniesienia pary plików."""
    # Utwórz źródłowe pliki
    archive_path = os.path.join(temp_test_dir, "testarchive.zip")
    preview_path = os.path.join(temp_test_dir, "testarchive.jpg")

    with open(archive_path, "wb") as f:
        f.write(b"testdata")
    test_image = Image.new("RGB", (100, 100), color="blue")
    test_image.save(preview_path)

    # Utwórz folder docelowy
    target_dir = os.path.join(temp_test_dir, "target_dir")
    os.makedirs(target_dir)

    file_pair = FilePair(archive_path, preview_path, temp_test_dir)

    assert file_pair.move(target_dir) is True

    # Sprawdzenie, czy pliki zostały przeniesione
    assert not os.path.exists(archive_path)
    assert not os.path.exists(preview_path)

    new_archive_path = os.path.join(target_dir, "testarchive.zip")
    new_preview_path = os.path.join(target_dir, "testarchive.jpg")

    assert os.path.exists(new_archive_path)
    assert os.path.exists(new_preview_path)

    # Sprawdź, czy wewnętrzne ścieżki zostały zaktualizowane
    assert file_pair.get_base_name() == "testarchive"
    assert os.path.normpath(file_pair.get_archive_path()) == os.path.normpath(
        os.path.relpath(new_archive_path, temp_test_dir)
    )
    assert os.path.normpath(file_pair.get_preview_path()) == os.path.normpath(
        os.path.relpath(new_preview_path, temp_test_dir)
    )


@pytest.mark.unit
def test_move_nonexistent_target(temp_test_dir):
    """Test przeniesienia plików do nieistniejącego folderu docelowego."""
    archive_path = os.path.join(temp_test_dir, "testarchive.zip")
    preview_path = os.path.join(temp_test_dir, "testarchive.jpg")

    with open(archive_path, "wb") as f:
        f.write(b"testdata")
    test_image = Image.new("RGB", (100, 100), color="blue")
    test_image.save(preview_path)

    # Nieistniejący folder docelowy
    target_dir = os.path.join(temp_test_dir, "nonexistent_dir")

    file_pair = FilePair(archive_path, preview_path, temp_test_dir)

    assert file_pair.move(target_dir) is False

    # Sprawdzenie, czy pliki pozostały w oryginalnej lokalizacji
    assert os.path.exists(archive_path)
    assert os.path.exists(preview_path)


@pytest.mark.unit
def test_move_conflict(temp_test_dir):
    """Test przeniesienia plików, gdy docelowe pliki już istnieją."""
    # Utwórz pliki źródłowe
    archive_path = os.path.join(temp_test_dir, "testarchive.zip")
    preview_path = os.path.join(temp_test_dir, "testarchive.jpg")

    with open(archive_path, "wb") as f:
        f.write(b"testdata")
    test_image = Image.new("RGB", (100, 100), color="blue")
    test_image.save(preview_path)

    # Utwórz folder docelowy z plikami o tej samej nazwie
    target_dir = os.path.join(temp_test_dir, "target_dir")
    os.makedirs(target_dir)

    with open(os.path.join(target_dir, "testarchive.zip"), "wb") as f:
        f.write(b"conflict data")
    test_image = Image.new("RGB", (100, 100), color="red")
    test_image.save(os.path.join(target_dir, "testarchive.jpg"))

    file_pair = FilePair(archive_path, preview_path, temp_test_dir)

    assert file_pair.move(target_dir) is False

    # Sprawdzenie, czy pliki pozostały w oryginalnej lokalizacji
    assert os.path.exists(archive_path)
    assert os.path.exists(preview_path)

    # Sprawdzenie, czy pliki docelowe nie zostały nadpisane
    with open(os.path.join(target_dir, "testarchive.zip"), "rb") as f:
        assert f.read() == b"conflict data"
