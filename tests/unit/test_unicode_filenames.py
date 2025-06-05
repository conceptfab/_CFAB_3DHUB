"""
Testy sprawdzające obsługę nazw plików z znakami Unicode (np. Cyrylica).
"""

import os
import shutil
import tempfile

import pytest
from PIL import Image

from src.logic.file_operations import create_folder, delete_folder, rename_folder
from src.logic.scanner import scan_folder_for_pairs
from src.models.file_pair import FilePair


@pytest.fixture
def temp_test_dir():
    """Tworzy tymczasowy katalog testowy z plikami testowymi z nazwami Unicode."""
    test_dir = tempfile.mkdtemp()
    try:
        # Utwórz testowy plik archiwum z nazwą cyrylicą
        archive_path = os.path.join(test_dir, "тестовый_файл.zip")
        with open(archive_path, "wb") as f:
            f.write(b"testdata")

        # Utwórz testowy plik podglądu z nazwą cyrylicą
        preview_path = os.path.join(test_dir, "тестовый_файл.jpg")
        test_image = Image.new("RGB", (100, 100), color="blue")
        test_image.save(preview_path)

        yield test_dir
    finally:
        # Posprzątaj po teście
        shutil.rmtree(test_dir)


@pytest.mark.unit
def test_file_pair_unicode_filename(temp_test_dir):
    """Test operacji na parach plików z nazwami Unicode."""
    archive_path = os.path.join(temp_test_dir, "тестовый_файл.zip")
    preview_path = os.path.join(temp_test_dir, "тестовый_файл.jpg")

    # Tworzenie obiektu FilePair z nazwą w cyrylicy
    file_pair = FilePair(archive_path, preview_path, temp_test_dir)

    # Sprawdzenie, czy nazwy są poprawnie obsługiwane
    assert file_pair.get_base_name() == "тестовый_файл"
    assert os.path.exists(archive_path)
    assert os.path.exists(preview_path)

    # Test zmiany nazwy
    assert file_pair.rename("новое_имя") is True

    # Sprawdzenie, czy pliki zostały rzeczywiście przemianowane
    new_archive_path = os.path.join(temp_test_dir, "новое_имя.zip")
    new_preview_path = os.path.join(temp_test_dir, "новое_имя.jpg")

    assert os.path.exists(new_archive_path)
    assert os.path.exists(new_preview_path)
    assert not os.path.exists(archive_path)
    assert not os.path.exists(preview_path)

    # Sprawdzenie, czy wewnętrzne ścieżki zostały zaktualizowane
    assert file_pair.get_base_name() == "новое_имя"

    # Test usuwania plików
    assert file_pair.delete() is True
    assert not os.path.exists(new_archive_path)
    assert not os.path.exists(new_preview_path)


@pytest.mark.unit
def test_folder_operations_unicode(temp_test_dir):
    """Test operacji na folderach z nazwami Unicode."""
    # Tworzenie folderu z nazwą w cyrylicy
    folder_name = "папка_тест"
    new_folder_path = create_folder(temp_test_dir, folder_name)

    assert new_folder_path is not None
    assert os.path.exists(new_folder_path)
    assert os.path.basename(new_folder_path) == folder_name

    # Zmiana nazwy folderu
    new_folder_name = "новая_папка"
    renamed_folder_path = rename_folder(new_folder_path, new_folder_name)

    assert renamed_folder_path is not None
    assert os.path.exists(renamed_folder_path)
    assert not os.path.exists(new_folder_path)
    assert os.path.basename(renamed_folder_path) == new_folder_name

    # Usuwanie folderu
    assert delete_folder(renamed_folder_path) is True
    assert not os.path.exists(renamed_folder_path)


@pytest.mark.unit
def test_scanner_unicode_filenames(temp_test_dir):
    """Test skanowania folderów z plikami o nazwach Unicode."""
    # Utwórz kilka plików z nazwami w cyrylicy
    files_data = [
        {"base_name": "тест1", "extensions": [".zip", ".jpg"]},
        {"base_name": "тест2", "extensions": [".rar", ".png"]},
        {"base_name": "файл3", "extensions": [".7z", ".gif"]},
    ]

    for data in files_data:
        for ext in data["extensions"]:
            file_path = os.path.join(temp_test_dir, data["base_name"] + ext)
            if ext in [".jpg", ".png", ".gif"]:
                # Tworzenie obrazu testowego
                test_image = Image.new("RGB", (100, 100), color="blue")
                test_image.save(file_path)
            else:
                # Tworzenie pustego archiwum
                with open(file_path, "wb") as f:
                    f.write(b"testdata")

    # Wywołanie funkcji skanującej
    found_pairs = scan_folder_for_pairs(temp_test_dir)

    # Sprawdzenie, czy wszystkie pary zostały znalezione
    assert len(found_pairs) == 3

    # Sprawdzenie, czy nazwy są poprawnie odczytywane
    base_names = [pair.get_base_name() for pair in found_pairs]
    expected_names = ["тест1", "тест2", "файл3"]

    for name in expected_names:
        assert name in base_names
