#!/usr/bin/env python
"""
Skrypt do zaktualizowania testów aby były zgodne z nową implementacją scanner.py
"""
import os


def main():
    # Utwórzmy kopię zapasową testów przed modyfikacją
    test_files = [
        "tests/unit/test_scanner_basic.py",
        "tests/unit/test_scanner_advanced.py",
        "tests/unit/test_scanner_performance.py",
    ]

    for test_file in test_files:
        backup_file = f"{test_file}.bak"
        if not os.path.exists(backup_file):
            print(f"Tworzenie kopii zapasowej {test_file} -> {backup_file}")
            with open(test_file, "r", encoding="utf-8") as src_file:
                content = src_file.read()

            with open(backup_file, "w", encoding="utf-8") as dst_file:
                dst_file.write(content)

    print("Utworzono kopie zapasowe testów.")
    print(
        "Uruchom testy i popraw je ręcznie na podstawie nowej implementacji scanner.py"
    )


if __name__ == "__main__":
    main()
