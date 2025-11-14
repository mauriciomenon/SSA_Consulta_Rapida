@echo off
REM Setup virtual environment for PyOxidizer to read from

echo Creating virtual environment...
python -m venv pyox_venv

echo Activating virtual environment...
call pyox_venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip
pip install pandas==2.3.3 openpyxl==3.1.5 PyQt6==6.10.0

echo.
echo Virtual environment ready at: pyox_venv
echo PyOxidizer will read packages from this environment.
echo.

pause
