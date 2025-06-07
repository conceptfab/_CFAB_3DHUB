#!/usr/bin/env python3
"""
Prosty test zapisywania metadanych
"""
import logging
import os
import sys

# Dodaj projekt do ścieżki
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Ustawienie logowania
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

from src.logic import metadata_manager
from src.models.file_pair import FilePair


def test_metadata_save():
    """Test zapisywania metadanych"""
    print("🧪 Test zapisywania metadanych")

    # Stwórz testowy katalog
    test_dir = r"c:\_cloud\_CFAB_3DHUB\test_data"
    os.makedirs(test_dir, exist_ok=True)

    # Stwórz testowy plik archiwum
    test_archive = os.path.join(test_dir, "test.zip")
    with open(test_archive, "w") as f:
        f.write("test")

    # Stwórz FilePair
    file_pair = FilePair(test_archive, None, test_dir)

    # Ustaw metadane
    file_pair.is_favorite = True
    file_pair.set_stars(4)
    file_pair.set_color_tag("#E53935")

    print(
        f"📊 FilePair: favorite={file_pair.is_favorite}, stars={file_pair.get_stars()}, color={file_pair.get_color_tag()}"
    )

    # Zapisz metadane
    result = metadata_manager.save_metadata(test_dir, [file_pair], [], [])

    print(f"💾 Wynik zapisu: {result}")

    # Sprawdź czy plik metadanych został utworzony
    metadata_path = metadata_manager.get_metadata_path(test_dir)
    print(f"📁 Ścieżka metadanych: {metadata_path}")
    print(f"📄 Plik istnieje: {os.path.exists(metadata_path)}")

    if os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as f:
            content = f.read()
            print(f"📝 Zawartość pliku metadanych:")
            print(content)

    # Wczytaj z powrotem
    loaded_metadata = metadata_manager.load_metadata(test_dir)
    print(f"📖 Wczytane metadane: {loaded_metadata}")

    # Zastosuj metadane
    metadata_manager.apply_metadata_to_file_pairs(test_dir, [file_pair])
    print(
        f"🔄 Po zastosowaniu: favorite={file_pair.is_favorite}, stars={file_pair.get_stars()}, color={file_pair.get_color_tag()}"
    )


if __name__ == "__main__":
    test_metadata_save()
