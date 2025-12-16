@echo off
echo ========================================================
echo 🚀 Creating Database Tables
echo ========================================================
echo.

REM Check if virtual environment is activated
if not defined VIRTUAL_ENV (
    echo ❌ Virtual environment not activated!
    echo Activate it with: .\gym\Scripts\activate
    pause
    exit /b 1
)

REM Run the Python script
python scripts/create_tables_simple.py

echo.
pause