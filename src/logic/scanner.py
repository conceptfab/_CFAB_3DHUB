"""
Moduł odpowiedzialny za skanowanie folderów i parowanie plików.
"""

import logging
import os

from src.app_config import SUPPORTED_ARCHIVE_EXTENSIONS, SUPPORTED_PREVIEW_EXTENSIONS
from src.models.file_pair import FilePair


def scan_folder_for_pairs(directory_path: str) -> list[FilePair]:
    """
    Rekursywnie przeszukuje podany katalog i jego podfoldery w poszukiwaniu
    plików archiwów i odpowiadających im plików podglądów.

    Paruje pliki, jeśli mają identyczną nazwę (bez rozszerzenia).
    W przypadku wielu podglądów do jednego archiwum, wybiera pierwszy pasujący.

    Args:
        directory_path (str): Ścieżka do folderu do przeskanowania.

    Returns:
        list[FilePair]: Lista znalezionych i sparowanych obiektów FilePair.
    """
    logging.info(f"Skanowanie folderu: {directory_path}")
    found_pairs: list[FilePair] = []
    # Słownik do przechowywania plików: {base_name: {type: path}}
    potential_files = {}

    for root, _, files in os.walk(directory_path):
        for file_name in files:
            base_name, extension = os.path.splitext(file_name)
            extension = extension.lower()
            full_path = os.path.join(root, file_name)

            # Ignoruj pliki bez nazwy (np. ukryte pliki systemowe)
            if not base_name:
                continue

            file_type = None
            if extension in SUPPORTED_ARCHIVE_EXTENSIONS:
                file_type = "archive"
            elif extension in SUPPORTED_PREVIEW_EXTENSIONS:
                file_type = "preview"

            if file_type:
                if base_name not in potential_files:
                    potential_files[base_name] = {}

                # Jeśli już istnieje plik tego typu o tej samej nazwie bazowej,
                # nie nadpisujemy go (bierzemy pierwszy znaleziony)
                if file_type not in potential_files[base_name]:
                    potential_files[base_name][file_type] = full_path
                    logging.debug(f"Potencjalny plik: {full_path} ({file_type})")
                else:
                    log_msg = (
                        f"Ignorowanie '{file_type}' dla '{base_name}': {full_path}. "
                        f"Istnieje: {potential_files[base_name][file_type]}"
                    )
                    logging.debug(log_msg)

    # Parowanie plików
    for base_name, files_data in potential_files.items():
        if "archive" in files_data and "preview" in files_data:
            archive_path = files_data["archive"]
            preview_path = files_data["preview"]
            try:
                pair = FilePair(archive_path=archive_path, preview_path=preview_path)
                found_pairs.append(pair)
                logging.debug(
                    f"Sparowano: A={os.path.basename(archive_path)}, P={os.path.basename(preview_path)}"
                )
            except Exception as e:
                logging.error(f"Błąd FilePair dla {archive_path} i {preview_path}: {e}")
        elif "archive" in files_data:
            logging.debug(f"Niesparowane archiwum: {files_data['archive']}")
        elif "preview" in files_data:
            logging.debug(f"Niesparowany podgląd: {files_data['preview']}")

    logging.info(f"Skanowanie zakończone. Znaleziono {len(found_pairs)} par.")
    return found_pairs


if __name__ == "__main__":
    # Ten blok jest przeznaczony do prostych testów manualnych.
    # Aby go użyć, odkomentuj i dostosuj ścieżkę `test_dir`.
    # Pamiętaj o utworzeniu odpowiedniej struktury folderów i plików.
    pass
