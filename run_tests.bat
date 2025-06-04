::
:: filepath: c:\_cloud\_CFAB_3DHUB\run_tests.bat
@echo off

echo === Uruchamianie testów jednostkowych ===
python -m pytest tests/unit -v

echo.
echo === Uruchamianie testów z generowaniem raportu pokrycia kodu ===
python -m pytest --cov=src tests/

echo.
echo === Gotowe ===
pause
