"""
Testy dla modułu metadata_manager.py
"""

import json
import os
import shutil
import tempfile

import pytest

from src.logic import metadata_manager
from src.models.file_pair import FilePair


class TestMetadataManager:

    @pytest.fixture
    def temp_dir(self):
        """Fixture zwracający tymczasowy katalog do testów."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_get_metadata_path(self):
        """Test generowania ścieżki do pliku metadanych."""
        working_dir = "/test/working/dir"
        expected_path = os.path.join(
            working_dir,
            metadata_manager.METADATA_DIR_NAME,
            metadata_manager.METADATA_FILE_NAME,
        )

        assert metadata_manager.get_metadata_path(working_dir) == expected_path

    def test_get_relative_path(self):
        """Test konwersji ścieżki absolutnej na względną."""
        base_path = os.path.normpath("/base/path")
        abs_path = os.path.normpath("/base/path/subdir/file.txt")

        rel_path = metadata_manager.get_relative_path(abs_path, base_path)
        expected = os.path.normpath("subdir/file.txt")
        assert rel_path == expected

    def test_get_absolute_path(self):
        """Test konwersji ścieżki względnej na absolutną."""
        base_path = os.path.normpath("/base/path")
        rel_path = os.path.normpath("subdir/file.txt")

        abs_path = metadata_manager.get_absolute_path(rel_path, base_path)
        expected = os.path.normpath("/base/path/subdir/file.txt")
        assert abs_path == expected

    def test_load_metadata_nonexistent(self, temp_dir):
        """Test wczytywania metadanych gdy plik nie istnieje."""
        metadata = metadata_manager.load_metadata(temp_dir)
        assert isinstance(metadata, dict)
        assert "file_pairs" in metadata
        assert metadata["file_pairs"] == {}
        assert "unpaired_archives" in metadata
        assert metadata["unpaired_archives"] == []
        assert "unpaired_previews" in metadata
        assert metadata["unpaired_previews"] == []

    def test_load_metadata_empty(self, temp_dir):
        """Test wczytywania pustego pliku metadanych."""
        metadata_dir = os.path.join(temp_dir, metadata_manager.METADATA_DIR_NAME)
        os.makedirs(metadata_dir, exist_ok=True)
        metadata_path = os.path.join(metadata_dir, metadata_manager.METADATA_FILE_NAME)
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump({}, f)  # Zapisujemy pusty, ale poprawny obiekt JSON

        metadata = metadata_manager.load_metadata(temp_dir)

        # Oczekujemy, że load_metadata uzupełni domyślne klucze
        expected_metadata = {
            "file_pairs": {},
            "unpaired_archives": [],
            "unpaired_previews": [],
        }
        assert metadata == expected_metadata

    def test_load_metadata_corrupted(self, temp_dir):
        """Test wczytywania uszkodzonego pliku metadanych."""
        metadata_dir = os.path.join(temp_dir, metadata_manager.METADATA_DIR_NAME)
        os.makedirs(metadata_dir, exist_ok=True)
        metadata_path = os.path.join(metadata_dir, metadata_manager.METADATA_FILE_NAME)
        with open(metadata_path, "w", encoding="utf-8") as f:
            f.write("{invalid json")
        metadata = metadata_manager.load_metadata(temp_dir)
        assert isinstance(metadata, dict)
        assert "file_pairs" in metadata
        assert metadata["file_pairs"] == {}
        assert "unpaired_archives" in metadata
        assert metadata["unpaired_archives"] == []
        assert "unpaired_previews" in metadata
        assert metadata["unpaired_previews"] == []

    def test_save_metadata(self, temp_dir):
        """Test zapisywania metadanych."""
        archive_path1 = os.path.join(temp_dir, "archive.zip")
        preview_path1 = os.path.join(temp_dir, "preview.jpg")
        archive_path2 = os.path.join(temp_dir, "archive2.rar")
        preview_path2 = os.path.join(temp_dir, "preview2.png")
        file_pair1 = FilePair(archive_path1, preview_path1, temp_dir)
        file_pair1.is_favorite = True
        file_pair2 = FilePair(archive_path2, preview_path2, temp_dir)

        unpaired_arc_path1 = os.path.join(temp_dir, "unpaired_A.7z")
        unpaired_arc_path2 = os.path.join(temp_dir, "subdir", "unpaired_B.zip")
        unpaired_prev_path1 = os.path.join(temp_dir, "unpaired_X.gif")
        unpaired_prev_path2 = os.path.join(
            temp_dir, "adir", "unp_Y.webp"
        )  # Skrócono nazwę pliku

        os.makedirs(os.path.join(temp_dir, "subdir"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "adir"), exist_ok=True)

        unpaired_archives_list = [unpaired_arc_path1, unpaired_arc_path2]
        unpaired_previews_list = [unpaired_prev_path1, unpaired_prev_path2]

        result = metadata_manager.save_metadata(
            temp_dir,
            [file_pair1, file_pair2],
            unpaired_archives_list,
            unpaired_previews_list,
        )
        assert result is True
        metadata_path = metadata_manager.get_metadata_path(temp_dir)
        assert os.path.exists(metadata_path)

        with open(metadata_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        assert "file_pairs" in saved_data
        assert "unpaired_archives" in saved_data
        assert "unpaired_previews" in saved_data

        rel_pair_path1 = metadata_manager.get_relative_path(archive_path1, temp_dir)
        rel_pair_path2 = metadata_manager.get_relative_path(archive_path2, temp_dir)
        assert rel_pair_path1 in saved_data["file_pairs"]
        assert rel_pair_path2 in saved_data["file_pairs"]
        fp1_data = saved_data["file_pairs"][rel_pair_path1]
        fp2_data = saved_data["file_pairs"][rel_pair_path2]
        assert fp1_data["is_favorite"] is True
        assert (
            fp2_data["is_favorite"] is False
        )  # Poprawiono z saved_data["file_pairs"][rel_pair_path2]

        exp_rel_arc1 = metadata_manager.get_relative_path(unpaired_arc_path1, temp_dir)
        exp_rel_arc2 = metadata_manager.get_relative_path(unpaired_arc_path2, temp_dir)
        assert sorted(saved_data["unpaired_archives"]) == sorted(
            [exp_rel_arc1, exp_rel_arc2]
        )

        exp_rel_prev1 = metadata_manager.get_relative_path(
            unpaired_prev_path1, temp_dir
        )
        exp_rel_prev2 = metadata_manager.get_relative_path(
            unpaired_prev_path2, temp_dir
        )
        assert sorted(saved_data["unpaired_previews"]) == sorted(
            [exp_rel_prev1, exp_rel_prev2]
        )

    def test_apply_metadata_to_file_pairs(self, temp_dir):
        """Test aplikowania metadanych do obiektów FilePair."""
        archive_path = os.path.join(temp_dir, "archive.zip")
        preview_path = os.path.join(temp_dir, "preview.jpg")
        file_pair1 = FilePair(archive_path, preview_path, temp_dir)
        file_pair2 = FilePair(archive_path + "2", preview_path + "2", temp_dir)

        metadata_dir = os.path.join(temp_dir, metadata_manager.METADATA_DIR_NAME)
        os.makedirs(metadata_dir, exist_ok=True)
        metadata_path = os.path.join(metadata_dir, metadata_manager.METADATA_FILE_NAME)

        rel_path1 = metadata_manager.get_relative_path(archive_path, temp_dir)
        test_metadata = {"file_pairs": {rel_path1: {"is_favorite": True}}}

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(test_metadata, f)

        # Przeniesiono argumenty do nowych linii dla czytelności
        result = metadata_manager.apply_metadata_to_file_pairs(
            temp_dir, [file_pair1, file_pair2]
        )
        assert result is True
        assert file_pair1.is_favorite is True
        assert file_pair2.is_favorite is False

    def test_save_load_cycle(self, temp_dir):
        """Test cyklu zapis -> odczyt metadanych, w tym niesparowanych plików."""
        archive_path_fp = os.path.join(temp_dir, "paired_archive.zip")
        preview_path_fp = os.path.join(temp_dir, "paired_preview.jpg")
        file_pair = FilePair(archive_path_fp, preview_path_fp, temp_dir)
        file_pair.is_favorite = True

        unpaired_arc_path1_abs = os.path.join(temp_dir, "unpaired_A.7z")
        unpaired_arc_path2_abs = os.path.join(temp_dir, "subdir", "unpaired_B.zip")
        unpaired_prev_path1_abs = os.path.join(temp_dir, "unpaired_X.gif")

        os.makedirs(os.path.join(temp_dir, "subdir"), exist_ok=True)

        unpaired_archives_to_save_abs = [unpaired_arc_path1_abs, unpaired_arc_path2_abs]
        unpaired_previews_to_save_abs = [unpaired_prev_path1_abs]

        save_result = metadata_manager.save_metadata(
            temp_dir,
            [file_pair],
            unpaired_archives_to_save_abs,
            unpaired_previews_to_save_abs,
        )
        assert save_result is True

        loaded_metadata_dict = metadata_manager.load_metadata(temp_dir)

        assert "file_pairs" in loaded_metadata_dict
        assert "unpaired_archives" in loaded_metadata_dict
        assert "unpaired_previews" in loaded_metadata_dict

        rel_fp_arc_path = metadata_manager.get_relative_path(archive_path_fp, temp_dir)
        assert rel_fp_arc_path in loaded_metadata_dict["file_pairs"]
        assert (
            loaded_metadata_dict["file_pairs"][rel_fp_arc_path]["is_favorite"] is True
        )

        # load_metadata zwraca ścieżki WZGLĘDNE dla niesparowanych plików
        # Musimy porównać z oczekiwanymi ścieżkami względnymi
        expected_rel_unpaired_archives = sorted(
            [
                os.path.normpath(metadata_manager.get_relative_path(p, temp_dir))
                for p in unpaired_archives_to_save_abs
            ]
        )
        loaded_rel_unpaired_archives = sorted(
            [os.path.normpath(p) for p in loaded_metadata_dict["unpaired_archives"]]
        )
        assert loaded_rel_unpaired_archives == expected_rel_unpaired_archives

        expected_rel_unpaired_previews = sorted(
            [
                os.path.normpath(metadata_manager.get_relative_path(p, temp_dir))
                for p in unpaired_previews_to_save_abs
            ]
        )
        loaded_rel_unpaired_previews = sorted(
            [os.path.normpath(p) for p in loaded_metadata_dict["unpaired_previews"]]
        )
        assert loaded_rel_unpaired_previews == expected_rel_unpaired_previews

        # Weryfikacja apply_metadata_to_file_pairs (istniejąca logika)
        new_file_pair = FilePair(archive_path_fp, preview_path_fp, temp_dir)
        assert new_file_pair.is_favorite is False
        apply_result = metadata_manager.apply_metadata_to_file_pairs(
            temp_dir, [new_file_pair]
        )
        assert apply_result is True
        assert new_file_pair.is_favorite is True

    def test_load_metadata_with_unpaired_files(self, temp_dir):
        """Testuje wczytywanie metadanych z listami niesparowanych plików."""
        metadata_dir = os.path.join(temp_dir, metadata_manager.METADATA_DIR_NAME)
        os.makedirs(metadata_dir, exist_ok=True)
        metadata_path = os.path.join(metadata_dir, metadata_manager.METADATA_FILE_NAME)

        rel_unpaired_arc1 = "data/unpaired1.zip"
        rel_unpaired_arc2 = "unpaired2.rar"
        rel_unpaired_prev1 = "img/unpaired_img.jpg"
        rel_paired_arc = "collections/my_collection.zip"
        rel_paired_prev = "collections/my_collection.png"

        data_to_save = {
            "file_pairs": {
                rel_paired_arc: {
                    "preview_path": rel_paired_prev,
                    "is_favorite": True,
                    "stars": 4,
                    "color_tag": "red",
                }
            },
            "unpaired_archives": [rel_unpaired_arc1, rel_unpaired_arc2],
            "unpaired_previews": [rel_unpaired_prev1],
        }
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f)

        loaded_data = metadata_manager.load_metadata(temp_dir)

        assert rel_paired_arc in loaded_data["file_pairs"]
        assert loaded_data["file_pairs"][rel_paired_arc]["is_favorite"] is True

        # load_metadata zwraca ścieżki WZGLĘDNE zapisane w pliku
        assert "unpaired_archives" in loaded_data
        assert isinstance(loaded_data["unpaired_archives"], list)
        loaded_rel_arc_paths = sorted(
            [os.path.normpath(p) for p in loaded_data["unpaired_archives"]]
        )
        expected_rel_arc_paths = sorted(
            [os.path.normpath(p) for p in [rel_unpaired_arc1, rel_unpaired_arc2]]
        )
        assert loaded_rel_arc_paths == expected_rel_arc_paths

        assert "unpaired_previews" in loaded_data
        assert isinstance(loaded_data["unpaired_previews"], list)
        loaded_rel_prev_paths = sorted(
            [os.path.normpath(p) for p in loaded_data["unpaired_previews"]]
        )
        expected_rel_prev_paths = sorted(
            [os.path.normpath(rel_unpaired_prev1)]
        )  # Lista jednoelementowa
        assert loaded_rel_prev_paths == expected_rel_prev_paths
