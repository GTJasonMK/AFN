@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Arboris Novel - One-Click Startup
echo ========================================
echo.

REM 保存当前目录
set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

REM ====================================
REM 第一步：检查和启动后端
REM ====================================
echo [1/5] Checking backend environment...
if not exist "backend\.venv" (
    echo ERROR: Backend virtual environment not found
    echo Please run backend\start.bat first to initialize
    pause
    exit /b 1
)

echo [2/5] Starting backend server...
echo.
start "Arboris Backend" cmd /k "cd /d "%ROOT_DIR%backend" && .venv\Scripts\activate.bat && echo Backend is starting... && uvicorn app.main:app --host 0.0.0.0 --port 8123"

REM 等待后端启动
echo Waiting for backend to start (this may take 10-15 seconds)...
timeout /t 3 /nobreak >nul

REM ====================================
REM 第二步：健康检查后端（可选）
REM ====================================
echo [3/5] Checking backend health...

REM 检查curl是否可用
curl --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo NOTE: curl command not found, skipping health check
    echo Please manually verify backend is running in the other window
    echo Look for: "Uvicorn running on http://0.0.0.0:8123"
    echo.
    echo Press any key to continue starting frontend...
    pause >nul
    goto :skip_health_check
)

set BACKEND_READY=0
set MAX_RETRIES=15

for /L %%i in (1,1,%MAX_RETRIES%) do (
    curl -s http://localhost:8123/health >nul 2>&1
    if !errorlevel! equ 0 (
        set BACKEND_READY=1
        goto :backend_ready
    )
    echo Attempt %%i/%MAX_RETRIES%: Backend not ready yet, waiting...
    timeout /t 2 /nobreak >nul
)

:backend_ready
if %BACKEND_READY% equ 1 (
    echo.
    echo ========================================
    echo Backend is ready!
    echo ========================================
    echo Backend URL: http://localhost:8123
    echo API Docs: http://localhost:8123/docs
    echo.
    goto :skip_health_check
)

if %BACKEND_READY% equ 0 (
    echo.
    echo ========================================
    echo WARNING: Health check failed
    echo ========================================
    echo.
    echo The backend may not be ready yet.
    echo Please check the "Arboris Backend" window:
    echo   - If you see "Uvicorn running" - Backend is OK, continue
    echo   - If you see errors - Press Ctrl+C to cancel and fix errors
    echo.
    echo Common issues:
    echo   1. Port 8123 already in use
    echo   2. Missing dependencies (run: pip install -r requirements.txt)
    echo   3. Database initialization error
    echo.
    echo Press any key to continue anyway, or Ctrl+C to cancel...
    pause >nul
)

:skip_health_check

REM ====================================
REM 第三步：检查前端环境
REM ====================================
echo [4/5] Checking frontend environment...

REM 检查Python是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Python not found in system PATH
    echo ========================================
    echo.
    echo Please install Python 3.10+ and add it to PATH
    echo.
    pause
    exit /b 1
)

REM 检查PyQt6是否安装
cd /d "%ROOT_DIR%frontend"
python -c "from PyQt6.QtWidgets import QApplication" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: PyQt6 not properly installed
    echo ========================================
    echo.
    echo Please install PyQt6:
    echo   pip install PyQt6
    echo.
    pause
    exit /b 1
)

REM ====================================
REM 第四步：启动前端
REM ====================================
echo [5/5] Launching frontend UI...
echo.

python main.py

REM ====================================
REM 前端关闭后的清理提示
REM ====================================
echo.
echo ========================================
echo Frontend closed
echo ========================================
echo.
echo The backend server is still running in the other window.
echo.
echo To stop the backend:
echo   - Go to the "Arboris Backend" window
echo   - Press Ctrl+C to stop the server
echo   - Or simply close the window
echo.
echo Press any key to exit...
pause >nul
