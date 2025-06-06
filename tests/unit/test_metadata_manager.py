import json
import os

# Dodajemy ścieżkę do src, aby móc importować moduły aplikacji
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from filelock import Timeout
from pyfakefs.fake_filesystem_unittest import TestCase

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
)

from logic import metadata_manager
from utils.path_utils import normalize_path


# Prosta klasa mockująca FilePair na potrzeby testów
class MockFilePair:
    def __init__(
        self,
        archive_path,
        is_favorite=False,
        stars=0,
        color_tag=None,
        base_name="test_file",
    ):
        self.archive_path = archive_path
        self.is_favorite = is_favorite
        self._stars = stars
        self._color_tag = color_tag
        self._base_name = base_name

    def get_stars(self):
        return self._stars

    def set_stars(self, stars_count):
        self._stars = stars_count

    def get_color_tag(self):
        return self._color_tag

    def set_color_tag(self, tag):
        self._color_tag = tag

    def get_base_name(self):  # Dodana metoda, której brakowało
        return self._base_name


class TestMetadataManagerPathFunctions(TestCase):
    def setUp(self):
        self.setUpPyfakefs()

        # Ustaw katalog testowy
        self.test_dir = normalize_path("/test_working_dir")
        self.fs.create_dir(self.test_dir)

        # Aby uniknąć problemów z plikami systemowymi, ustawmy tryb ograniczony
        # który będzie ignorował ścieżki spoza naszych testów
        self.fs.is_case_sensitive = False  # Windows jest case-insensitive

    def test_get_metadata_path(self):
        expected_path = normalize_path(
            os.path.join(
                self.test_dir,
                metadata_manager.METADATA_DIR_NAME,
                metadata_manager.METADATA_FILE_NAME,
            )
        )
        self.assertEqual(
            metadata_manager.get_metadata_path(self.test_dir), expected_path
        )

    def test_get_lock_path(self):
        expected_path = normalize_path(
            os.path.join(
                self.test_dir,
                metadata_manager.METADATA_DIR_NAME,
                metadata_manager.LOCK_FILE_NAME,
            )
        )
        self.assertEqual(metadata_manager.get_lock_path(self.test_dir), expected_path)

    def test_get_relative_path(self):
        base_path = normalize_path("C:/base/path")
        absolute_path = normalize_path("C:/base/path/to/file.txt")
        expected_relative_path = normalize_path("to/file.txt")
        self.assertEqual(
            metadata_manager.get_relative_path(absolute_path, base_path),
            expected_relative_path,
        )

        absolute_path_outside = normalize_path("C:/other/path/to/file.txt")
        # Na Windows, jeśli ścieżki są na tym samym dysku, relpath zadziała
        # Oczekujemy, że nasza funkcja zwróci znormalizowaną ścieżkę względną
        # lub None, jeśli konwersja nie jest jednoznaczna (np. różne dyski - obsłużone w kodzie)
        if os.name == "nt":
            # Symulacja tego samego dysku
            self.assertIsNotNone(
                metadata_manager.get_relative_path(absolute_path_outside, base_path)
            )

            # Symulacja różnych dysków - powinno zwrócić None
            with patch(
                "os.path.splitdrive",
                side_effect=lambda p: ("D:", p[2:]) if "other" in p else ("C:", p[2:]),
            ) as mock_splitdrive:
                self.assertIsNone(
                    metadata_manager.get_relative_path(absolute_path_outside, base_path)
                )
        else:  # Na systemach innych niż Windows, relpath zazwyczaj działa inaczej
            self.assertEqual(
                metadata_manager.get_relative_path(absolute_path_outside, base_path),
                normalize_path("../../other/path/to/file.txt"),
            )

    def test_get_relative_path_different_drives_windows(self):
        if os.name == "nt":
            base_path = normalize_path("C:/base/path")
            absolute_path_diff_drive = normalize_path("D:/another/path/file.txt")
            self.assertIsNone(
                metadata_manager.get_relative_path(absolute_path_diff_drive, base_path)
            )

    def test_get_absolute_path(self):
        base_path = normalize_path("C:/base/path")
        relative_path = normalize_path("from/here/file.txt")
        expected_absolute_path = normalize_path("C:/base/path/from/here/file.txt")
        self.assertEqual(
            metadata_manager.get_absolute_path(relative_path, base_path),
            expected_absolute_path,
        )

        base_path_trailing_slash = normalize_path("C:/base/path/")
        self.assertEqual(
            metadata_manager.get_absolute_path(relative_path, base_path_trailing_slash),
            expected_absolute_path,
        )


class TestMetadataManagerLoadSave(TestCase):
    def setUp(self):
        self.setUpPyfakefs()

        # Ustaw katalog roboczy
        self.working_dir = normalize_path("/my_projects/project_alpha")
        self.fs.create_dir(self.working_dir)
        self.metadata_dir_path = os.path.join(
            self.working_dir, metadata_manager.METADATA_DIR_NAME
        )
        self.metadata_file_path = os.path.join(
            self.metadata_dir_path, metadata_manager.METADATA_FILE_NAME
        )
        self.lock_file_path = os.path.join(
            self.metadata_dir_path, metadata_manager.LOCK_FILE_NAME
        )

        # Aby uniknąć problemów z plikami systemowymi, ustawmy tryb ograniczony
        self.fs.is_case_sensitive = False  # Windows jest case-insensitive

    def test_load_metadata_no_file(self):
        """Testuje wczytywanie, gdy plik metadanych nie istnieje."""
        metadata = metadata_manager.load_metadata(self.working_dir)
        self.assertEqual(metadata, metadata_manager.DEFAULT_METADATA)
        self.assertTrue(
            os.path.exists(self.metadata_dir_path)
        )  # Katalog powinien zostać utworzony

    def test_load_metadata_empty_file(self):
        """Testuje wczytywanie, gdy plik metadanych jest pusty (niepoprawny JSON)."""
        self.fs.create_file(self.metadata_file_path, contents="")
        metadata = metadata_manager.load_metadata(self.working_dir)
        self.assertEqual(metadata, metadata_manager.DEFAULT_METADATA)

    def test_load_metadata_invalid_json(self):
        """Testuje wczytywanie, gdy plik metadanych zawiera niepoprawny JSON."""
        self.fs.create_file(self.metadata_file_path, contents="{not_json:")
        metadata = metadata_manager.load_metadata(self.working_dir)
        self.assertEqual(metadata, metadata_manager.DEFAULT_METADATA)

    def test_load_metadata_valid_file(self):
        """Testuje wczytywanie poprawnego pliku metadanych."""
        valid_data = {
            "file_pairs": {"archive1.zip": {"is_favorite": True, "stars": 5}},
            "unpaired_archives": ["archive2.zip"],
            "unpaired_previews": ["preview1.jpg"],
        }
        self.fs.create_file(self.metadata_file_path, contents=json.dumps(valid_data))
        metadata = metadata_manager.load_metadata(self.working_dir)
        self.assertEqual(metadata, valid_data)

    def test_load_metadata_incomplete_structure(self):
        """Testuje wczytywanie pliku z niekompletną, ale naprawialną strukturą."""
        partial_data = {
            "file_pairs": {"archive1.zip": {"is_favorite": True}}
            # Brakuje unpaired_archives i unpaired_previews
        }
        self.fs.create_file(self.metadata_file_path, contents=json.dumps(partial_data))
        metadata = metadata_manager.load_metadata(self.working_dir)
        self.assertTrue("unpaired_archives" in metadata)
        self.assertEqual(metadata["unpaired_archives"], [])
        self.assertTrue("unpaired_previews" in metadata)
        self.assertEqual(metadata["unpaired_previews"], [])
        self.assertEqual(metadata["file_pairs"], partial_data["file_pairs"])

    def test_save_metadata_creates_file_and_dir(self):
        """Testuje, czy save_metadata tworzy katalog i plik, jeśli nie istnieją."""
        fp1_path = normalize_path(os.path.join(self.working_dir, "archiveA.zip"))
        fp1 = MockFilePair(fp1_path, is_favorite=True, stars=3)
        file_pairs = [fp1]
        unpaired_archives = [
            normalize_path(os.path.join(self.working_dir, "lonely.rar"))
        ]
        unpaired_previews = []

        result = metadata_manager.save_metadata(
            self.working_dir, file_pairs, unpaired_archives, unpaired_previews
        )
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.metadata_dir_path))
        self.assertTrue(os.path.exists(self.metadata_file_path))

        # Sprawdzenie zawartości
        with open(self.metadata_file_path, "r") as f:
            saved_data = json.load(f)

        self.assertIn(
            metadata_manager.get_relative_path(fp1_path, self.working_dir),
            saved_data["file_pairs"],
        )
        self.assertEqual(
            saved_data["file_pairs"][
                metadata_manager.get_relative_path(fp1_path, self.working_dir)
            ]["is_favorite"],
            True,
        )
        self.assertEqual(
            saved_data["file_pairs"][
                metadata_manager.get_relative_path(fp1_path, self.working_dir)
            ]["stars"],
            3,
        )
        self.assertEqual(
            saved_data["unpaired_archives"],
            [
                metadata_manager.get_relative_path(
                    unpaired_archives[0], self.working_dir
                )
            ],
        )

    def test_save_and_load_cycle(self):
        """Testuje cykl zapisz -> wczytaj."""
        fp1_path = normalize_path(os.path.join(self.working_dir, "data/archive1.zip"))
        fp2_path = normalize_path(os.path.join(self.working_dir, "data/archive2.zip"))
        self.fs.create_dir(normalize_path(os.path.join(self.working_dir, "data")))

        file_pairs_to_save = [
            MockFilePair(fp1_path, is_favorite=True, stars=5, color_tag="red"),
            MockFilePair(fp2_path, is_favorite=False, stars=1, color_tag="blue"),
        ]
        unpaired_arc = [
            normalize_path(os.path.join(self.working_dir, "other/unpaired.zip"))
        ]
        unpaired_prev = [
            normalize_path(os.path.join(self.working_dir, "img/thumb.jpg"))
        ]
        self.fs.create_dir(normalize_path(os.path.join(self.working_dir, "other")))
        self.fs.create_dir(normalize_path(os.path.join(self.working_dir, "img")))

        save_result = metadata_manager.save_metadata(
            self.working_dir, file_pairs_to_save, unpaired_arc, unpaired_prev
        )
        self.assertTrue(save_result)

        loaded_metadata = metadata_manager.load_metadata(self.working_dir)

        rel_fp1_path = metadata_manager.get_relative_path(fp1_path, self.working_dir)
        rel_fp2_path = metadata_manager.get_relative_path(fp2_path, self.working_dir)

        self.assertIn(rel_fp1_path, loaded_metadata["file_pairs"])
        self.assertEqual(
            loaded_metadata["file_pairs"][rel_fp1_path]["is_favorite"], True
        )
        self.assertEqual(loaded_metadata["file_pairs"][rel_fp1_path]["stars"], 5)
        self.assertEqual(
            loaded_metadata["file_pairs"][rel_fp1_path]["color_tag"], "red"
        )

        self.assertIn(rel_fp2_path, loaded_metadata["file_pairs"])
        self.assertEqual(
            loaded_metadata["file_pairs"][rel_fp2_path]["is_favorite"], False
        )
        self.assertEqual(loaded_metadata["file_pairs"][rel_fp2_path]["stars"], 1)
        self.assertEqual(
            loaded_metadata["file_pairs"][rel_fp2_path]["color_tag"], "blue"
        )

        self.assertEqual(
            loaded_metadata["unpaired_archives"],
            [metadata_manager.get_relative_path(unpaired_arc[0], self.working_dir)],
        )
        self.assertEqual(
            loaded_metadata["unpaired_previews"],
            [metadata_manager.get_relative_path(unpaired_prev[0], self.working_dir)],
        )

    @patch("src.logic.metadata_manager.FileLock")
    def test_load_metadata_lock_timeout(self, MockFileLock):
        """Testuje timeout blokady podczas wczytywania."""
        mock_lock_instance = MockFileLock.return_value
        mock_lock_instance.acquire.side_effect = Timeout(self.lock_file_path)

        # Upewniamy się, że plik istnieje, aby testować logikę po próbie blokady
        self.fs.create_file(
            self.metadata_file_path, contents=json.dumps({"file_pairs": {}})
        )

        metadata = metadata_manager.load_metadata(self.working_dir)
        self.assertEqual(metadata, metadata_manager.DEFAULT_METADATA)
        MockFileLock.assert_called_with(
            self.lock_file_path, timeout=metadata_manager.LOCK_TIMEOUT
        )
        mock_lock_instance.__enter__.assert_called_once()  # Sprawdzenie, czy próbowano wejść do kontekstu

    @patch("src.logic.metadata_manager.FileLock")
    def test_save_metadata_lock_timeout(self, MockFileLock):
        """Testuje timeout blokady podczas zapisywania."""
        mock_lock_instance = MockFileLock.return_value
        mock_lock_instance.acquire.side_effect = Timeout(self.lock_file_path)

        result = metadata_manager.save_metadata(self.working_dir, [], [], [])
        self.assertFalse(result)
        MockFileLock.assert_called_with(
            self.lock_file_path, timeout=metadata_manager.LOCK_TIMEOUT
        )
        mock_lock_instance.__enter__.assert_called_once()


class TestMetadataManagerApplyAndManage(TestCase):
    def setUp(self):
        self.setUpPyfakefs()

        # Ustaw katalog roboczy
        self.working_dir = normalize_path("/data_repo")

        # Aby uniknąć problemów z plikami systemowymi, ustawmy tryb ograniczony
        self.fs.is_case_sensitive = False  # Windows jest case-insensitive
        self.fs.create_dir(self.working_dir)
        self.metadata_file_path = metadata_manager.get_metadata_path(self.working_dir)
        self.fs.create_dir(
            os.path.dirname(self.metadata_file_path)
        )  # Utwórz katalog .app_metadata

        self.fp1_abs_path = normalize_path(
            os.path.join(self.working_dir, "archive_one.zip")
        )
        self.fp2_abs_path = normalize_path(
            os.path.join(self.working_dir, "sub/archive_two.zip")
        )
        self.fs.create_dir(normalize_path(os.path.join(self.working_dir, "sub")))

        self.file_pair1 = MockFilePair(self.fp1_abs_path, base_name="archive_one")
        self.file_pair2 = MockFilePair(self.fp2_abs_path, base_name="archive_two")
        self.all_file_pairs = [self.file_pair1, self.file_pair2]

    def test_apply_metadata_to_file_pairs(self):
        """Testuje stosowanie metadanych do listy obiektów FilePair."""
        rel_fp1_path = metadata_manager.get_relative_path(
            self.fp1_abs_path, self.working_dir
        )
        rel_fp2_path = metadata_manager.get_relative_path(
            self.fp2_abs_path, self.working_dir
        )

        metadata_content = {
            "file_pairs": {
                rel_fp1_path: {"is_favorite": True, "stars": 4, "color_tag": "green"},
                rel_fp2_path: {"is_favorite": False, "stars": 2, "color_tag": None},
            },
            "unpaired_archives": [],
            "unpaired_previews": [],
        }
        self.fs.create_file(
            self.metadata_file_path, contents=json.dumps(metadata_content)
        )

        result = metadata_manager.apply_metadata_to_file_pairs(
            self.working_dir, self.all_file_pairs
        )
        self.assertTrue(result)

        self.assertTrue(self.file_pair1.is_favorite)
        self.assertEqual(self.file_pair1.get_stars(), 4)
        self.assertEqual(self.file_pair1.get_color_tag(), "green")

        self.assertFalse(self.file_pair2.is_favorite)
        self.assertEqual(self.file_pair2.get_stars(), 2)
        self.assertIsNone(self.file_pair2.get_color_tag())

    def test_apply_metadata_no_matching_pair(self):
        """Testuje stosowanie metadanych, gdy para nie ma wpisu w metadanych."""
        rel_fp_other_path = "non_existent_archive.zip"
        metadata_content = {
            "file_pairs": {rel_fp_other_path: {"is_favorite": True, "stars": 5}},
            "unpaired_archives": [],
            "unpaired_previews": [],
        }
        self.fs.create_file(
            self.metadata_file_path, contents=json.dumps(metadata_content)
        )

        # Zapisujemy początkowe wartości
        initial_fp1_favorite = self.file_pair1.is_favorite
        initial_fp1_stars = self.file_pair1.get_stars()

        result = metadata_manager.apply_metadata_to_file_pairs(
            self.working_dir, [self.file_pair1]
        )
        self.assertTrue(result)

        # Wartości nie powinny się zmienić
        self.assertEqual(self.file_pair1.is_favorite, initial_fp1_favorite)
        self.assertEqual(self.file_pair1.get_stars(), initial_fp1_stars)

    def test_remove_metadata_for_file(self):
        """Testuje usuwanie metadanych dla konkretnego pliku."""
        rel_fp1_path = metadata_manager.get_relative_path(
            self.fp1_abs_path, self.working_dir
        )
        metadata_content = {
            "file_pairs": {rel_fp1_path: {"is_favorite": True, "stars": 5}},
            "unpaired_archives": ["ua1"],
            "unpaired_previews": ["up1"],
        }
        self.fs.create_file(
            self.metadata_file_path, contents=json.dumps(metadata_content)
        )

        remove_result = metadata_manager.remove_metadata_for_file(
            self.working_dir, rel_fp1_path
        )
        self.assertTrue(remove_result)

        loaded_metadata = metadata_manager.load_metadata(self.working_dir)
        self.assertNotIn(rel_fp1_path, loaded_metadata["file_pairs"])
        # Sprawdź, czy inne dane nie zostały usunięte
        self.assertEqual(loaded_metadata["unpaired_archives"], ["ua1"])

    def test_remove_metadata_file_not_in_metadata(self):
        """Testuje usuwanie metadanych dla pliku, którego nie ma w metadanych."""
        rel_fp_non_existent = "no_such_file.zip"
        metadata_content = {
            "file_pairs": {"some_other_file.zip": {"is_favorite": False}},
            "unpaired_archives": [],
            "unpaired_previews": [],
        }
        self.fs.create_file(
            self.metadata_file_path, contents=json.dumps(metadata_content)
        )

        remove_result = metadata_manager.remove_metadata_for_file(
            self.working_dir, rel_fp_non_existent
        )
        self.assertTrue(
            remove_result
        )  # Powinno zwrócić True, bo operacja "się powiodła" (nic nie trzeba było robić)

        loaded_metadata = metadata_manager.load_metadata(self.working_dir)
        self.assertEqual(
            loaded_metadata["file_pairs"],
            {"some_other_file.zip": {"is_favorite": False}},
        )

    def test_get_all_favorite_relative_paths(self):
        """Testuje pobieranie wszystkich ulubionych ścieżek względnych."""
        rel_fp1 = metadata_manager.get_relative_path(
            self.fp1_abs_path, self.working_dir
        )
        rel_fp2 = metadata_manager.get_relative_path(
            self.fp2_abs_path, self.working_dir
        )
        rel_fp3 = "another/fav.rar"

        metadata_content = {
            "file_pairs": {
                rel_fp1: {"is_favorite": True, "stars": 5},
                rel_fp2: {"is_favorite": False, "stars": 1},
                rel_fp3: {"is_favorite": True, "stars": 3},
            },
            "unpaired_archives": [],
            "unpaired_previews": [],
        }
        self.fs.create_file(
            self.metadata_file_path, contents=json.dumps(metadata_content)
        )

        favorite_paths = metadata_manager.get_all_favorite_relative_paths(
            self.working_dir
        )
        self.assertIn(rel_fp1, favorite_paths)
        self.assertIn(rel_fp3, favorite_paths)
        self.assertNotIn(rel_fp2, favorite_paths)
        self.assertEqual(len(favorite_paths), 2)

    def test_get_metadata_for_relative_path(self):
        """Testuje pobieranie metadanych dla konkretnej ścieżki względnej."""
        rel_fp1 = metadata_manager.get_relative_path(
            self.fp1_abs_path, self.working_dir
        )
        fp1_data = {"is_favorite": True, "stars": 5, "color_tag": "orange"}

        metadata_content = {
            "file_pairs": {rel_fp1: fp1_data, "other.zip": {"is_favorite": False}},
            "unpaired_archives": [],
            "unpaired_previews": [],
        }
        self.fs.create_file(
            self.metadata_file_path, contents=json.dumps(metadata_content)
        )

        retrieved_data = metadata_manager.get_metadata_for_relative_path(
            self.working_dir, rel_fp1
        )
        self.assertEqual(retrieved_data, fp1_data)

        non_existent_data = metadata_manager.get_metadata_for_relative_path(
            self.working_dir, "non_existent.zip"
        )
        self.assertIsNone(non_existent_data)

    def test_validate_metadata_structure(self):
        """Testuje funkcję _validate_metadata_structure."""
        # Poprawna struktura
        valid_metadata = {
            "file_pairs": {
                "path/to/file.zip": {
                    "is_favorite": True,
                    "stars": 3,
                    "color_tag": "red",
                }
            },
            "unpaired_archives": ["path/to/archive.rar"],
            "unpaired_previews": ["path/to/preview.jpg"],
        }
        self.assertTrue(metadata_manager._validate_metadata_structure(valid_metadata))

        # Brakujący klucz - powinien zostać uzupełniony i zwrócić True
        missing_key_metadata = {"file_pairs": {}}
        self.assertTrue(
            metadata_manager._validate_metadata_structure(missing_key_metadata)
        )
        self.assertIn("unpaired_archives", missing_key_metadata)
        self.assertIn("unpaired_previews", missing_key_metadata)

        # Nieprawidłowy typ dla klucza głównego
        invalid_type_metadata = {
            "file_pairs": "not_a_dict",
            "unpaired_archives": [],
            "unpaired_previews": [],
        }
        self.assertFalse(
            metadata_manager._validate_metadata_structure(invalid_type_metadata)
        )

        # Nieprawidłowy typ wewnątrz file_pairs
        invalid_type_in_pairs_metadata = {
            "file_pairs": {"path/to/file.zip": "not_a_dict"},
            "unpaired_archives": [],
            "unpaired_previews": [],
        }
        self.assertFalse(
            metadata_manager._validate_metadata_structure(
                invalid_type_in_pairs_metadata
            )
        )

        # Nieprawidłowy typ dla is_favorite - powinien dać warning, ale zwrócić True
        invalid_type_favorite_metadata = {
            "file_pairs": {
                "path/to/file.zip": {"is_favorite": "true_string"}
            },  # Powinno być bool
            "unpaired_archives": [],
            "unpaired_previews": [],
        }
        with self.assertLogs(level="WARNING") as log:
            self.assertTrue(
                metadata_manager._validate_metadata_structure(
                    invalid_type_favorite_metadata
                )
            )
            self.assertIn("Nieprawidłowy typ dla 'is_favorite'", log.output[0])


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
