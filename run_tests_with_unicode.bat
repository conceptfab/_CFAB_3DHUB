@echo off
REM Ustawienie kodowania konsoli na UTF-8 dla prawidłowego wyświetlania znaków Unicode
chcp 65001 > nul

REM Uruchomienie skryptu testowego
python run_operation_tests.py

REM Wstrzymanie konsoli, aby można było przeczytać wyniki
pause
