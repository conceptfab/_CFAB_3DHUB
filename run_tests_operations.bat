@echo off

echo === Uruchamianie testów jednostkowych ===
python -m pytest tests/unit/test_file_pair_operations.py -v > test_results_operations.txt 2>&1
python -m pytest tests/unit/test_folder_operations.py -v >> test_results_operations.txt 2>&1

echo === Wyniki zapisano do pliku test_results_operations.txt ===

echo.
echo === Gotowe ===
