#!/usr/bin/env python3
"""Test sprawdzający czy scanner znajduje archiwa bez pary."""

import os
import sys

# Dodaj ścieżkę do modułów
sys.path.insert(0, ".")

from src.logic.scanner_core import scan_folder_for_pairs


def test_unpaired_files():
    """Testuje czy scanner znajduje archiwa bez pary."""
    # Test na przykładowym folderze
    test_folders = [
        "C:/Users/micz/Desktop/ARCHITECTURE",
        "C:/Users/micz/Desktop",
        "C:/_cloud/___TEST_FOLDER",
        "C:/_cloud",
    ]

    for test_folder in test_folders:
        if os.path.exists(test_folder):
            print(f"Testowanie folderu: {test_folder}")
            try:
                pairs, unpaired_archives, unpaired_previews, special_folders = (
                    scan_folder_for_pairs(test_folder, max_depth=0)
                )
                print(f"Wyniki skanowania:")
                print(f"  - {len(pairs)} par plików")
                print(f"  - {len(unpaired_archives)} archiwów bez pary")
                print(f"  - {len(unpaired_previews)} podglądów bez pary")
                print(f"  - {len(special_folders)} folderów specjalnych")

                if unpaired_archives:
                    print(f"Pierwsze 3 archiwa bez pary:")
                    for i, archive in enumerate(unpaired_archives[:3]):
                        print(f"    {i+1}. {os.path.basename(archive)}")
                else:
                    print("Brak archiwów bez pary w tym folderze")

                return True

            except Exception as e:
                print(f"Błąd podczas skanowania: {e}")
                continue
        else:
            print(f"Folder {test_folder} nie istnieje")

    print("Nie znaleziono żadnego dostępnego folderu do testowania")
    return False


if __name__ == "__main__":
    test_unpaired_files()
