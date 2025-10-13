@echo off
echo ========================================
echo Setting up CognitoAI Engine Environment
echo ========================================
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Virtual environment activated!
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install requirements
echo Installing backend requirements...
cd apps\backend
pip install -r requirements.txt --quiet
cd ..\..

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Virtual environment is ready.
echo To start the application, run: venv\Scripts\python.exe start_app.py
echo.