::
:: filepath: c:\_cloud\_CFAB_3DHUB\run_tests.bat
@echo off

echo === Uruchamianie testów jednostkowych ===
echo.
echo - Uruchomienie wszystkich testów jednostkowych (z pominieciem problematycznych)
python -m pytest tests/unit -v --ignore=.venv --ignore=venv --ignore=tests/unit/test_metadata_manager.py

echo.
echo - Uruchomienie uproszczonych testów dla metadata_manager.py
python tests/unit/simpler_test_metadata_manager.py

echo.
echo === Uruchamianie testów z generowaniem raportu pokrycia kodu ===
python -m pytest --cov=src tests/ --ignore=.venv --ignore=venv --ignore=tests/unit/test_metadata_manager.py

echo.
echo === Gotowe ===
pause
