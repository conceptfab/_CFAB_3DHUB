import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image
from PyQt6.QtGui import QPixmap

from src.models.file_pair import FilePair


@pytest.mark.unit
def test_file_pair_basic():
    file_pair = FilePair("path/to/archive.zip", "path/to/preview.jpg")
    assert file_pair.get_base_name() == "archive"
    assert file_pair.get_archive_path() == "path/to/archive.zip"
    assert file_pair.get_preview_path() == "path/to/preview.jpg"


@pytest.mark.unit
def test_file_pair_with_real_files():
    # Utwórz tymczasowy katalog na pliki testowe
    test_dir = tempfile.mkdtemp()

    try:
        # Utwórz testowy plik archiwum
        archive_path = os.path.join(test_dir, "testarchive.zip")
        with open(archive_path, "wb") as f:
            f.write(b"testdata")  # 8 bajtów danych testowych

        # Utwórz testowy plik podglądu
        preview_path = os.path.join(test_dir, "testarchive.jpg")
        test_image = Image.new("RGB", (100, 100), color="blue")
        test_image.save(preview_path)

        # Utwórz instancję FilePair
        file_pair = FilePair(archive_path, preview_path)

        # Testuj metody dostępu do rozmiarów plików
        assert file_pair.get_archive_size() == 8
        assert file_pair.get_formatted_archive_size() == "8 B"        # Testuj generowanie miniatury - użyjemy patchowania aby uniknąć problemów z QPixmap
        with patch('src.utils.image_utils.pillow_image_to_qpixmap') as mock_to_qpixmap:
            # Utwórz mock QPixmap
            mock_pixmap = MagicMock()
            mock_pixmap.isNull.return_value = False
            mock_pixmap.width.return_value = 50
            mock_pixmap.height.return_value = 50
            mock_to_qpixmap.return_value = mock_pixmap
            
            # Teraz testuj
            thumbnail = file_pair.load_preview_thumbnail((50, 50))
            assert thumbnail is mock_pixmap
            assert not thumbnail.isNull()
            assert thumbnail.width() == 50
            assert thumbnail.height() == 50

    finally:
        # Posprzątaj po teście
        shutil.rmtree(test_dir)



