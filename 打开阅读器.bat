@echo off
chcp 65001 >nul
cd /d "%~dp0"
python "%~dp0archive.py" serve --open
echo.
pause
