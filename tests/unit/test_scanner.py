from pathlib import Path

import pytest

from src.logic.scanner import scan_folder_for_pairs

# Zakładamy, że obsługiwane rozszerzenia są dostępne np. przez src.app_config.
# Dla uproszczenia testów używamy typowych rozszerzeń.


@pytest.fixture
def temp_test_dir(tmp_path: Path) -> Path:
    """Tworzy tymczasowy katalog testowy."""
    test_dir = tmp_path / "test_scan_dir"
    test_dir.mkdir()
    return test_dir


def create_files(base_path: Path, file_specs: list[tuple[str, str | None]]):
    """
    Tworzy pliki i katalogi na podstawie specyfikacji.
    file_specs: lista krotek (rel_path, content_or_None_for_dir)
    Np.: [("a.zip", "txt"), ("s/img.jpg", "dat"), ("e_sub", None)]
    """
    for rel_path, content in file_specs:
        full_path = base_path / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if content is not None:
            full_path.write_text(
                content if isinstance(content, str) else "dummy_content"
            )
        elif not full_path.exists():  # Jeśli content jest None, to katalog
            full_path.mkdir(parents=True, exist_ok=True)


def test_scan_empty_directory(temp_test_dir: Path):
    """Testuje skanowanie pustego katalogu."""
    pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
        str(temp_test_dir)
    )
    assert not pairs
    assert not unpaired_archives
    assert not unpaired_previews


def test_scan_no_supported_files(temp_test_dir: Path):
    """Testuje skanowanie katalogu bez obsługiwanych plików."""
    create_files(temp_test_dir, [("notes.txt", "text"), ("doc.docx", "doc")])
    pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
        str(temp_test_dir)
    )
    assert not pairs
    assert not unpaired_archives
    assert not unpaired_previews


def test_scan_basic_pairing(temp_test_dir: Path):
    """Testuje podstawowe parowanie plików."""
    create_files(
        temp_test_dir,
        [
            ("archive1.zip", "zip_data"),
            ("archive1.jpg", "jpg_data"),
            ("archive2.rar", "rar_data"),
            ("archive2.png", "png_data"),
        ],
    )
    pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
        str(temp_test_dir)
    )

    assert len(pairs) == 2
    assert not unpaired_archives
    assert not unpaired_previews

    pair_bases = {pair.get_base_name() for pair in pairs}
    assert "archive1" in pair_bases
    assert "archive2" in pair_bases

    for pair_obj in pairs:
        assert pair_obj.working_directory == str(temp_test_dir)
        if pair_obj.get_base_name() == "archive1":
            assert pair_obj.archive_path.endswith("archive1.zip")
            assert pair_obj.preview_path.endswith("archive1.jpg")
        elif pair_obj.get_base_name() == "archive2":
            assert pair_obj.archive_path.endswith("archive2.rar")
            assert pair_obj.preview_path.endswith("archive2.png")


def test_scan_case_insensitive_pairing(temp_test_dir: Path):
    """Testuje parowanie z ignorowaniem wielkości liter w nazwie bazowej."""
    create_files(
        temp_test_dir,
        [
            ("MyArchive.zip", "zip_data"),
            ("myarchive.jpg", "jpg_data"),
            ("AnotherArchive.RAR", "rar_data"),
            ("anotherarchive.PNG", "png_data"),
        ],
    )
    pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
        str(temp_test_dir)
    )
    assert len(pairs) == 2
    assert not unpaired_archives
    assert not unpaired_previews
    pair_bases = {p.get_base_name().lower() for p in pairs}
    assert "myarchive" in pair_bases
    assert "anotherarchive" in pair_bases


def test_scan_unpaired_archives(temp_test_dir: Path):
    """Testuje identyfikację niesparowanych archiwów."""
    create_files(
        temp_test_dir,
        [
            ("archive1.zip", "zip_data"),
            ("archive2.7z", "7z_data"),
            ("paired_arc.rar", "rar_data"),
            ("paired_arc.png", "png_data"),
        ],
    )
    pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
        str(temp_test_dir)
    )
    assert len(pairs) == 1
    assert len(unpaired_archives) == 2
    assert not unpaired_previews
    assert pairs[0].get_base_name() == "paired_arc"
    unpaired_archive_files = {Path(p).name for p in unpaired_archives}
    assert "archive1.zip" in unpaired_archive_files
    assert "archive2.7z" in unpaired_archive_files


def test_scan_unpaired_previews(temp_test_dir: Path):
    """Testuje identyfikację niesparowanych podglądów."""
    create_files(
        temp_test_dir,
        [
            ("preview1.jpg", "jpg_data"),
            ("preview2.gif", "gif_data"),
            ("paired_arc.rar", "rar_data"),
            ("paired_arc.png", "png_data"),
        ],
    )
    pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
        str(temp_test_dir)
    )
    assert len(pairs) == 1
    assert not unpaired_archives
    assert len(unpaired_previews) == 2
    assert pairs[0].get_base_name() == "paired_arc"
    unpaired_preview_files = {Path(p).name for p in unpaired_previews}
    assert "preview1.jpg" in unpaired_preview_files
    assert "preview2.gif" in unpaired_preview_files


def test_scan_mixed_paired_and_unpaired(temp_test_dir: Path):
    """Testuje mieszankę plików sparowanych i niesparowanych."""
    create_files(
        temp_test_dir,
        [
            ("archiveA.zip", "data"),
            ("archiveA.jpg", "data"),
            ("archiveB.rar", "data"),
            ("previewC.png", "data"),
            ("ArchiveD.7z", "data"),
            ("archived.gif", "data"),
        ],
    )
    pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
        str(temp_test_dir)
    )
    assert len(pairs) == 2
    assert len(unpaired_archives) == 1
    assert len(unpaired_previews) == 1
    paired_bases = {p.get_base_name().lower() for p in pairs}
    assert "archivea" in paired_bases
    assert "archived" in paired_bases
    assert Path(unpaired_archives[0]).name == "archiveB.rar"
    assert Path(unpaired_previews[0]).name == "previewC.png"


def test_scan_files_in_subdirectories(monkeypatch, temp_test_dir: Path):
    """Testuje skanowanie plików w podkatalogach (uproszczony)."""
    archive_exts = [".zip", ".rar", ".7z"]
    preview_exts = [".jpg", ".png", ".gif", ".webp"]
    monkeypatch.setattr("src.logic.scanner.SUPPORTED_ARCHIVE_EXTENSIONS", archive_exts)
    monkeypatch.setattr("src.logic.scanner.SUPPORTED_PREVIEW_EXTENSIONS", preview_exts)

    create_files(
        temp_test_dir,
        [
            ("root_A.zip", "data"),
            ("root_A.jpg", "data"),
            ("subdir1/nested_dir/deep_C.zip", "data"),
            ("subdir1/nested_dir/deep_C.webp", "data"),
        ],
    )
    pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
        str(temp_test_dir)
    )

    assert len(pairs) == 2
    assert not unpaired_archives
    assert not unpaired_previews

    paired_paths_check = {"root_A": False, "subdir1/nested_dir/deep_C": False}
    for pair_obj in pairs:
        rel_archive_path = (
            Path(pair_obj.archive_path).relative_to(temp_test_dir).as_posix()
        )
        base_name_from_path = (
            Path(rel_archive_path).parent / Path(rel_archive_path).stem
        )
        key_to_check = base_name_from_path.as_posix()

        if key_to_check == "root_A":
            assert pair_obj.archive_path.endswith("root_A.zip")
            assert pair_obj.preview_path.endswith("root_A.jpg")
            paired_paths_check["root_A"] = True
        elif key_to_check == "subdir1/nested_dir/deep_C":
            assert pair_obj.archive_path.endswith("deep_C.zip")
            assert pair_obj.preview_path.endswith("deep_C.webp")
            paired_paths_check["subdir1/nested_dir/deep_C"] = True

    assert all(paired_paths_check.values()), (
        f"Nie wszystkie oczekiwane pary (uproszczone): {paired_paths_check}. "
        f"Znaleziono: {[p.get_base_name() for p in pairs]}"
    )


def test_scan_multiple_previews_for_one_archive(temp_test_dir: Path):
    """
    Testuje sytuację z wieloma podglądami dla jednego archiwum.
    Skaner wybierze jeden podgląd, reszta będzie ignorowana.
    """
    create_files(
        temp_test_dir,
        [
            ("archiveX.zip", "data"),
            ("archiveX.jpg", "data_jpg"),
            ("archiveX.png", "data_png"),
            ("archiveY.rar", "data_rar"),
            ("previewZ.gif", "data_gif"),
        ],
    )
    pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
        str(temp_test_dir)
    )
    assert len(pairs) == 1
    assert len(unpaired_archives) == 1
    assert len(unpaired_previews) == 1
    assert pairs[0].get_base_name().lower() == "archivex"
    # Sprawdź, który podgląd wybrano (zależy od os.walk).
    # Zakładamy, że .jpg będzie pierwszy.
    assert Path(pairs[0].preview_path).name == "archiveX.jpg"
    assert Path(unpaired_archives[0]).name == "archiveY.rar"
    assert Path(unpaired_previews[0]).name == "previewZ.gif"
    unpaired_preview_names = {Path(p).name for p in unpaired_previews}
    assert "archiveX.png" not in unpaired_preview_names
    assert "archiveX.jpg" not in unpaired_preview_names


def test_scan_filename_without_base(temp_test_dir: Path):
    """Testuje pliki bez nazwy bazowej (np. '.log')."""
    create_files(
        temp_test_dir,
        [
            (".hiddenfile", "hidden"),
            ("archive.zip", "zip"),
            (".hiddenpreview.jpg", "preview_hidden"),
            ("archive.jpg", "jpg"),
        ],
    )
    pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
        str(temp_test_dir)
    )
    assert len(pairs) == 1
    assert pairs[0].get_base_name() == "archive"
    assert not unpaired_archives
    assert len(unpaired_previews) == 1
    assert Path(unpaired_previews[0]).name == ".hiddenpreview.jpg"
    # Sprawdźmy, czy plik ".hiddenfile" nie został zwrócony.
    # Plik ".hiddenpreview.jpg" jest zwracany jako niesparowany podgląd.
    all_returned_paths = (
        [p.archive_path for p in pairs]
        + [p.preview_path for p in pairs]
        + unpaired_archives
        + unpaired_previews
    )
    assert not any(Path(p).name == ".hiddenfile" for p in all_returned_paths)
