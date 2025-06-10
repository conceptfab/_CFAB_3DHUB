import json
import logging
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, mock_open, patch

from src.logic.metadata_manager import (
    METADATA_DIR_NAME,
    METADATA_FILE_NAME,
    _validate_metadata_structure,
    apply_metadata_to_file_pairs,
    get_absolute_path,
    get_metadata_for_relative_path,
    get_metadata_path,
    get_relative_path,
    load_metadata,
    remove_metadata_for_file,
    save_metadata,
)
from src.models.file_pair import FilePair
from src.utils.path_utils import normalize_path

# Wyłączenie logowania na czas testów, chyba że jest to potrzebne do debugowania
# logging.disable(logging.CRITICAL)


class TestMetadataManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.working_directory = normalize_path(os.path.join(self.test_dir, "work"))
        os.makedirs(self.working_directory, exist_ok=True)
        self.metadata_dir = normalize_path(
            os.path.join(self.working_directory, METADATA_DIR_NAME)
        )
        self.metadata_file_path = normalize_path(
            os.path.join(self.metadata_dir, METADATA_FILE_NAME)
        )

        # Upewnij się, że katalog metadanych istnieje przed każdym testem,
        # ponieważ niektóre testy mogą go usuwać lub oczekiwać jego istnienia.
        os.makedirs(self.metadata_dir, exist_ok=True)

        # Przykładowy obiekt FilePair
        # Używamy pełnych ścieżek absolutnych do inicjalizacji FilePair
        self.fp1_abs_archive_path = normalize_path(
            os.path.join(self.working_directory, "archive1.zip")
        )
        self.fp1_abs_preview_path = normalize_path(
            os.path.join(self.working_directory, "preview1.jpg")
        )
        self.fp1 = FilePair(
            self.fp1_abs_archive_path, self.fp1_abs_preview_path, self.working_directory
        )
        self.fp1.set_stars(3)
        self.fp1.set_color_tag("red")

        self.fp2_abs_archive_path = normalize_path(
            os.path.join(self.working_directory, "archive2.zip")
        )
        self.fp2_abs_preview_path = normalize_path(
            os.path.join(self.working_directory, "preview2.jpg")
        )
        self.fp2 = FilePair(
            self.fp2_abs_archive_path, self.fp2_abs_preview_path, self.working_directory
        )
        self.fp2.set_stars(5)
        self.fp2.set_color_tag("blue")

        # self.fp1.archive_path i self.fp2.archive_path będą teraz ścieżkami względnymi ("archive1.zip", "archive2.zip")
        # ponieważ base_path (self.working_directory) zostało podane do konstruktora FilePair.
        # To jest oczekiwane zachowanie dla kluczy w pliku metadanych.

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_get_metadata_path(self):
        expected_path = self.metadata_file_path
        self.assertEqual(get_metadata_path(self.working_directory), expected_path)

    def test_get_relative_path(self):
        base = normalize_path("C:/base/path")
        abs_p = normalize_path("C:/base/path/to/file.txt")
        self.assertEqual(get_relative_path(abs_p, base), normalize_path("to/file.txt"))

        abs_p_outside = normalize_path("C:/other/path/file.txt")
        # Na tym samym dysku, ale poza bazą - relpath powinien zadziałać
        self.assertEqual(
            get_relative_path(abs_p_outside, base),
            normalize_path("../../other/path/file.txt"),
        )

        if os.name == "nt":  # Testy specyficzne dla Windows
            abs_p_diff_drive = normalize_path("D:/another/file.txt")
            self.assertIsNone(get_relative_path(abs_p_diff_drive, base))

        # Test z normalizacją
        base_n = "C:\\base\\path\\"  # Poprawiony backslash
        abs_p_n = "C:\\base\\path\\to/file.txt"  # Poprawiony backslash
        self.assertEqual(get_relative_path(abs_p_n, base_n), "to/file.txt")

    def test_get_absolute_path(self):
        base = normalize_path("C:/base/path")
        rel_p = normalize_path("to/file.txt")
        expected = normalize_path(os.path.abspath("C:/base/path/to/file.txt"))
        self.assertEqual(get_absolute_path(rel_p, base), expected)

        # Test z normalizacją
        base_n = "C:\\base\\path\\"  # Poprawiony backslash
        rel_p_n = "to/file.txt"
        expected_n = normalize_path(os.path.abspath("C:/base/path/to/file.txt"))
        self.assertEqual(get_absolute_path(rel_p_n, base_n), expected_n)

    def test_validate_metadata_structure(self):
        valid_metadata = {
            "file_pairs": {"path/to/archive.zip": {"stars": 3, "color_tag": "red"}},
            "unpaired_archives": ["path/to/archive2.zip"],
            "unpaired_previews": ["path/to/preview.jpg"],
        }
        self.assertTrue(_validate_metadata_structure(valid_metadata))

        invalid_type_metadata = {"file_pairs": "not_a_dict"}
        self.assertFalse(_validate_metadata_structure(invalid_type_metadata))

        missing_key_metadata = {
            "file_pairs": {}
        }  # Brakuje unpaired_archives, unpaired_previews
        # _validate_metadata_structure uzupełnia brakujące klucze i zwraca True
        self.assertTrue(_validate_metadata_structure(missing_key_metadata))
        self.assertIn("unpaired_archives", missing_key_metadata)
        self.assertIn("unpaired_previews", missing_key_metadata)

        invalid_file_pair_data = {"file_pairs": {"path/to/archive.zip": "not_a_dict"}}
        self.assertFalse(_validate_metadata_structure(invalid_file_pair_data))

    @patch("src.logic.metadata_manager.os.path.exists")
    @patch("src.logic.metadata_manager.open", new_callable=mock_open)
    def test_load_metadata_file_not_exists(self, mock_file_open, mock_exists):
        mock_exists.return_value = False
        metadata = load_metadata(self.working_directory)
        self.assertEqual(
            metadata,
            {"file_pairs": {}, "unpaired_archives": [], "unpaired_previews": []},
        )
        mock_file_open.assert_not_called()

    @patch("src.logic.metadata_manager.os.path.exists")
    @patch("src.logic.metadata_manager.open", new_callable=mock_open)
    def test_load_metadata_json_decode_error(self, mock_file_open, mock_exists):
        mock_exists.return_value = True
        mock_file_open.side_effect = json.JSONDecodeError("Error", "doc", 0)
        metadata = load_metadata(self.working_directory)
        self.assertEqual(
            metadata,
            {"file_pairs": {}, "unpaired_archives": [], "unpaired_previews": []},
        )

    @patch("src.logic.metadata_manager.os.path.exists")
    @patch("src.logic.metadata_manager._validate_metadata_structure")
    @patch("src.logic.metadata_manager.open")
    def test_load_metadata_invalid_structure(
        self, mock_file_open, mock_validate, mock_exists
    ):
        mock_exists.return_value = True
        mock_validate.return_value = False  # Symulacja nieprawidłowej struktury

        # Symulacja wczytania poprawnych danych JSON, ale o złej strukturze wg _validate_metadata_structure
        m_open = mock_open(read_data='{"file_pairs": "bad_structure"}')
        mock_file_open.configure_mock(side_effect=m_open)

        metadata = load_metadata(self.working_directory)
        self.assertEqual(
            metadata,
            {"file_pairs": {}, "unpaired_archives": [], "unpaired_previews": []},
        )
        mock_validate.assert_called_once()

    def test_save_and_load_metadata_e2e(self):
        # Test end-to-end dla save_metadata i load_metadata
        file_pairs_list = [self.fp1, self.fp2]
        unpaired_archives = [
            normalize_path(os.path.join(self.working_directory, "ua1.zip"))
        ]
        unpaired_previews = [
            normalize_path(os.path.join(self.working_directory, "up1.jpg"))
        ]

        # Zapis
        result = save_metadata(
            self.working_directory,
            file_pairs_list,
            unpaired_archives,
            unpaired_previews,
        )
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.metadata_file_path))

        # Odczyt
        loaded_data = load_metadata(self.working_directory)

        fp1_rel_path = get_relative_path(
            self.fp1_abs_archive_path, self.working_directory
        )
        fp2_rel_path = get_relative_path(
            self.fp2_abs_archive_path, self.working_directory
        )

        self.assertIn(fp1_rel_path, loaded_data["file_pairs"])
        self.assertEqual(loaded_data["file_pairs"][fp1_rel_path]["stars"], 3)
        self.assertEqual(loaded_data["file_pairs"][fp1_rel_path]["color_tag"], "red")

        self.assertIn(fp2_rel_path, loaded_data["file_pairs"])
        self.assertEqual(loaded_data["file_pairs"][fp2_rel_path]["stars"], 5)
        self.assertEqual(loaded_data["file_pairs"][fp2_rel_path]["color_tag"], "blue")

        self.assertEqual(len(loaded_data["unpaired_archives"]), 1)
        self.assertEqual(
            loaded_data["unpaired_archives"][0], "ua1.zip"
        )  # Powinny być względne

        self.assertEqual(len(loaded_data["unpaired_previews"]), 1)
        self.assertEqual(loaded_data["unpaired_previews"][0], "up1.jpg")

    def test_apply_metadata_to_file_pairs(self):
        # Przygotowanie pliku metadanych
        fp1_rel_archive_path = get_relative_path(
            self.fp1_abs_archive_path, self.working_directory
        )
        metadata_content = {
            "file_pairs": {
                fp1_rel_archive_path: {  # Użyj jawnie ścieżki względnej
                    "stars": 4,
                    "color_tag": "green",
                },
                "non_existent_archive.zip": {"stars": 1, "color_tag": "yellow"},
            },
            "unpaired_archives": [],
            "unpaired_previews": [],
        }
        os.makedirs(self.metadata_dir, exist_ok=True)
        with open(self.metadata_file_path, "w", encoding="utf-8") as f:
            json.dump(metadata_content, f)

        # fp1 ma początkowo 3 gwiazdki, "red"
        # fp2 ma początkowo 5 gwiazdek, "blue" (brak w metadanych)
        fp1_to_update = FilePair(
            self.fp1_abs_archive_path, self.fp1_abs_preview_path, self.working_directory
        )
        fp1_to_update.set_stars(3)  # Reset do stanu początkowego testu
        fp1_to_update.set_color_tag("red")

        fp2_no_meta = FilePair(
            self.fp2_abs_archive_path, self.fp2_abs_preview_path, self.working_directory
        )
        fp2_no_meta.set_stars(5)
        fp2_no_meta.set_color_tag("blue")

        file_pairs_to_update = [fp1_to_update, fp2_no_meta]

        result = apply_metadata_to_file_pairs(
            self.working_directory, file_pairs_to_update
        )
        self.assertTrue(result)

        # Sprawdź fp1_to_update
        self.assertEqual(fp1_to_update.get_stars(), 4)
        self.assertEqual(fp1_to_update.get_color_tag(), "green")

        # Sprawdź fp2_no_meta (nie powinno się zmienić)
        self.assertEqual(fp2_no_meta.get_stars(), 5)
        self.assertEqual(fp2_no_meta.get_color_tag(), "blue")

    def test_remove_metadata_for_file(self):
        # Przygotowanie pliku metadanych
        fp1_rel_path = get_relative_path(
            self.fp1_abs_archive_path, self.working_directory
        )  # Użyj jawnie ścieżki względnej
        fp2_rel_path = get_relative_path(
            self.fp2_abs_archive_path, self.working_directory
        )  # Użyj jawnie ścieżki względnej

        metadata_content = {
            "file_pairs": {
                fp1_rel_path: {"stars": 3, "color_tag": "red"},
                fp2_rel_path: {"stars": 5, "color_tag": "blue"},
            },
            "unpaired_archives": [],
            "unpaired_previews": [],
        }
        os.makedirs(self.metadata_dir, exist_ok=True)
        with open(self.metadata_file_path, "w", encoding="utf-8") as f:
            json.dump(metadata_content, f)

        # Usuń metadane dla fp1
        result = remove_metadata_for_file(self.working_directory, fp1_rel_path)
        self.assertTrue(result)

        # Sprawdź, czy metadane fp1 zostały usunięte
        loaded_data = load_metadata(self.working_directory)
        self.assertNotIn(fp1_rel_path, loaded_data["file_pairs"])
        self.assertIn(fp2_rel_path, loaded_data["file_pairs"])  # fp2 powinno pozostać

        # Próba usunięcia nieistniejącego wpisu
        result_non_existent = remove_metadata_for_file(
            self.working_directory, "non_existent.zip"
        )
        self.assertTrue(
            result_non_existent
        )  # Powinno zwrócić True, bo nic nie trzeba było robić

    def test_get_metadata_for_relative_path(self):
        fp1_rel_path = get_relative_path(
            self.fp1_abs_archive_path, self.working_directory
        )  # Użyj jawnie ścieżki względnej
        metadata_content = {
            "file_pairs": {
                fp1_rel_path: {"stars": 3, "color_tag": "red"},
            },
            "unpaired_archives": [],
            "unpaired_previews": [],
        }
        os.makedirs(self.metadata_dir, exist_ok=True)
        with open(self.metadata_file_path, "w", encoding="utf-8") as f:
            json.dump(metadata_content, f)

        # Pobierz metadane dla fp1
        meta = get_metadata_for_relative_path(self.working_directory, fp1_rel_path)
        self.assertIsNotNone(meta)
        self.assertEqual(meta["stars"], 3)
        self.assertEqual(meta["color_tag"], "red")

        # Pobierz metadane dla nieistniejącego pliku
        meta_non_existent = get_metadata_for_relative_path(
            self.working_directory, "non_existent.zip"
        )
        self.assertIsNone(meta_non_existent)

    @patch("src.logic.metadata_manager.save_metadata")
    def test_save_metadata_handles_missing_attributes_gracefully(
        self, mock_save_metadata
    ):
        # Ten test sprawdza, czy save_metadata nie rzuca wyjątku,
        # jeśli obiekt FilePair nie ma wszystkich atrybutów.
        # Właściwa funkcja save_metadata ma logować warning i kontynuować.

        # Tworzymy mock FilePair, który nie ma metody get_base_name()
        # (lub innej oczekiwanej przez zaktualizowaną funkcję save_metadata)
        mock_fp_broken = MagicMock(spec=FilePair)
        # Symulujemy, że archive_path istnieje, ale inne metody mogą brakować
        mock_fp_broken.archive_path = normalize_path(
            os.path.join(self.working_directory, "broken.zip")
        )
        # mock_fp_broken.archive_path powinien być ścieżką absolutną dla konstruktora FilePair
        # ale dla celów tego testu (mockowanie i sprawdzanie logiki save_metadata),
        # ścieżka względna jest ok, ponieważ get_relative_path będzie mockowane lub
        # save_metadata powinno sobie z tym poradzić (co jest częścią testu).
        # Jednakże, aby uniknąć problemów z `get_relative_path` wewnątrz `save_metadata`,
        # lepiej jest, aby `mock_fp_broken.archive_path` była ścieżką absolutną,
        # a `get_relative_path` działało poprawnie.

        mock_fp_broken_abs_path = normalize_path(
            os.path.join(self.working_directory, "broken.zip")
        )
        # mock_fp_broken.archive_path = mock_fp_broken_abs_path # Ta linia jest zbędna, bo mock_fp_broken.archive_path jest ustawiane niżej
        # Symulujemy brak metody get_base_name
        # del mock_fp_broken.get_base_name # Usunięto, ponieważ get_base_name jest teraz wymagane
        # Zamiast usuwać, upewnijmy się, że jest, ale może być inny problem z atrybutem
        mock_fp_broken.get_base_name.return_value = "broken"
        mock_fp_broken.archive_path = (
            mock_fp_broken_abs_path  # Ustawienie archive_path dla mocka
        )

        # Symulujemy, że inne metody istnieją, aby przejść przez pierwszą część walidacji atrybutów
        mock_fp_broken.get_stars.return_value = 1
        mock_fp_broken.get_color_tag.return_value = "green"

        # Wywołujemy save_metadata z tym "uszkodzonym" obiektem
        # W tym teście nie sprawdzamy faktycznego zapisu, tylko czy funkcja nie wywala się
        # na braku atrybutu i czy mock_save_metadata (czyli nasza funkcja) jest wywoływana.
        # To jest bardziej test jednostkowy logiki wewnątrz save_metadata,
        # więc mockujemy samą funkcję save_metadata, aby uniknąć zapisu do pliku.
        # Lepszym podejściem byłoby przetestowanie oryginalnej funkcji save_metadata
        # i sprawdzenie logów lub tego, że plik został zapisany bez tego wpisu.

        # Zmieniamy podejście: testujemy prawdziwą funkcję save_metadata
        # i sprawdzamy, czy nie rzuca wyjątku oraz czy loguje ostrzeżenie.

        # Przygotowujemy poprawny FilePair
        fp_good_abs_path = normalize_path(
            os.path.join(self.working_directory, "good.zip")
        )
        fp_good_abs_preview_path = normalize_path(
            os.path.join(self.working_directory, "good.jpg")
        )
        fp_good = FilePair(
            fp_good_abs_path, fp_good_abs_preview_path, self.working_directory
        )
        fp_good.set_stars(5)
        fp_good.set_color_tag("blue")

        # Modyfikujemy mock_fp_broken, aby miał wszystkie wymagane atrybuty, ale jeden z nich będzie "zły"
        # np. get_stars zwraca string zamiast int, co powinno być obsłużone przez logikę w save_metadata
        # lub _validate_metadata_structure, ale save_metadata powinno pominąć taki obiekt.
        # W tym konkretnym teście skupiamy się na braku atrybutu, więc przywracamy usunięcie get_base_name.
        # Aby test był bardziej precyzyjny co do braku atrybutu, upewnijmy się, że archive_path jest ustawione
        # a następnie usuwamy inny wymagany atrybut.
        mock_fp_broken.archive_path = (
            mock_fp_broken_abs_path  # Ustawienie archive_path dla mocka
        )
        if hasattr(mock_fp_broken, "get_base_name"):
            del mock_fp_broken.get_base_name

        file_pairs_list = [mock_fp_broken, fp_good]

        with self.assertLogs(
            logger="src.logic.metadata_manager", level="WARNING"
        ) as log_watcher:
            save_metadata(self.working_directory, file_pairs_list, [], [])

        # Sprawdzamy, czy pojawiło się ostrzeżenie o pominięciu obiektu
        self.assertTrue(
            any(
                "Pominięto obiekt w file_pairs_list - brak wymaganych atrybutów" in msg
                for msg in log_watcher.output
            )
        )

        # Sprawdzamy, czy metadane dla poprawnego obiektu zostały zapisane
        loaded_data = load_metadata(self.working_directory)

        fp_good_rel_path = get_relative_path(
            fp_good_abs_path, self.working_directory
        )  # Użyj jawnie ścieżki względnej

        self.assertIn(fp_good_rel_path, loaded_data["file_pairs"])
        # mock_fp_broken.archive_path (po normalizacji i join) to ścieżka absolutna.
        # Potrzebujemy ścieżki względnej, jeśli chcemy sprawdzić jej brak.
        # Jednak test sprawdza, czy ostrzeżenie zostało zalogowane, co jest głównym celem.
        # Sprawdzenie, czy 'broken.zip' (względna) nie ma w metadanych jest bardziej bezpośrednie.
        relative_broken_path = get_relative_path(
            mock_fp_broken_abs_path, self.working_directory
        )
        if relative_broken_path:  # Tylko jeśli udało się uzyskać ścieżkę względną
            self.assertNotIn(relative_broken_path, loaded_data["file_pairs"])

    def test_save_metadata_empty_input(self):
        result = save_metadata(self.working_directory, [], [], [])
        self.assertTrue(result)
        loaded_data = load_metadata(self.working_directory)
        self.assertEqual(loaded_data["file_pairs"], {})
        self.assertEqual(loaded_data["unpaired_archives"], [])
        self.assertEqual(loaded_data["unpaired_previews"], [])

    def test_apply_metadata_to_file_pairs_empty_metadata_file(self):
        # Usuwamy plik metadanych, jeśli istnieje
        if os.path.exists(self.metadata_file_path):
            os.remove(self.metadata_file_path)

        fp_list = [self.fp1]  # fp1 ma 3 gwiazdki, "red"
        original_stars = self.fp1.get_stars()
        original_color = self.fp1.get_color_tag()

        result = apply_metadata_to_file_pairs(self.working_directory, fp_list)
        self.assertTrue(
            result
        )  # Powinno być True, bo nie ma metadanych do zastosowania

        # Wartości nie powinny się zmienić
        self.assertEqual(self.fp1.get_stars(), original_stars)
        self.assertEqual(self.fp1.get_color_tag(), original_color)

    def test_remove_metadata_for_file_when_metadata_file_not_exists(self):
        if os.path.exists(self.metadata_file_path):
            os.remove(self.metadata_file_path)

        result = remove_metadata_for_file(self.working_directory, "any_path.zip")
        self.assertTrue(result)  # Powinno być True, bo plik metadanych nie istnieje

    def test_remove_metadata_for_file_corrupted_json(self):
        os.makedirs(self.metadata_dir, exist_ok=True)
        with open(self.metadata_file_path, "w", encoding="utf-8") as f:
            f.write("this is not valid json")

        with self.assertLogs(
            logger="src.logic.metadata_manager", level="ERROR"
        ) as log_watcher:
            result = remove_metadata_for_file(self.working_directory, "any_path.zip")

        self.assertFalse(result)
        self.assertTrue(
            any("Błąd dekodowania JSON" in msg for msg in log_watcher.output)
        )


if __name__ == "__main__":
    unittest.main()
