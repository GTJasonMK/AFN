@echo off
chcp 65001 >nul
echo ========================================
echo Arboris Novel Backend - PyQt Edition
echo ========================================
echo.

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        echo Please ensure Python 3.10+ is installed
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
    echo.
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
    echo Dependencies installed successfully
    echo.
)

if not exist ".env" (
    echo Creating default .env file...
    copy .env.example .env >nul
    echo .env file created successfully
    echo.
    echo ========================================
    echo IMPORTANT: LLM Configuration
    echo ========================================
    echo.
    echo You can configure LLM settings in TWO ways:
    echo.
    echo Option 1 - Use the application interface
    echo   - Start the app and go to LLM Config page
    echo   - Add your API key and settings there
    echo.
    echo Option 2 - Edit .env file manually
    echo   - Open backend\.env in a text editor
    echo   - Set OPENAI_API_KEY and other settings
    echo.
    echo The application will start now.
    echo You can add LLM config later in the app.
    echo.
    pause
)

if not exist "storage" mkdir storage

echo.
echo ========================================
echo Starting Arboris Novel Backend...
echo ========================================
echo.
echo API: http://127.0.0.1:8123
echo Docs: http://127.0.0.1:8123/docs
echo Health: http://127.0.0.1:8123/health
echo.
echo Log: storage\debug.log
echo Database: storage\arboris.db
echo.
echo Press Ctrl+C to stop
echo.

uvicorn app.main:app --reload --host 127.0.0.1 --port 8123

if errorlevel 1 (
    echo.
    echo Server exited with an error
    pause
)
