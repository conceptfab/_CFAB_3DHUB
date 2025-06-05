"""
Skrypt do uruchomienia testów operacji na plikach i folderach.
"""

import os
import sys

import pytest


def run_tests():
    print("=== Uruchamianie testów operacji na parach plików ===")
    file_pair_result = pytest.main(["tests/unit/test_file_pair_operations.py", "-v"])

    print("\n=== Uruchamianie testów operacji na folderach ===")
    folder_result = pytest.main(["tests/unit/test_folder_operations.py", "-v"])

    print("\n=== Uruchamianie testów obsługi nazw plików Unicode (np. Cyrylica) ===")
    unicode_result = pytest.main(["tests/unit/test_unicode_filenames.py", "-v"])

    print("\n=== Wyniki testów ===")
    print(
        f"Test file_pair_operations: {'Sukces' if file_pair_result == 0 else f'Błąd ({file_pair_result})'}"
    )
    print(
        f"Test folder_operations: {'Sukces' if folder_result == 0 else f'Błąd ({folder_result})'}"
    )
    print(
        f"Test nazw Unicode: {'Sukces' if unicode_result == 0 else f'Błąd ({unicode_result})'}"
    )

    return file_pair_result == 0 and folder_result == 0 and unicode_result == 0


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    success = run_tests()
    sys.exit(0 if success else 1)
