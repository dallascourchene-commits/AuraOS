@echo off
REM Quick-start script for CODEMAP File System Watcher (Windows)
REM This script starts the watcher with sensible defaults

echo ==========================================
echo CODEMAP File System Watcher
echo ==========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    echo Please install Python 3.7 or later
    pause
    exit /b 1
)

REM Check if watchdog is installed
echo Checking dependencies...
python -c "import watchdog" >nul 2>&1
if errorlevel 1 (
    echo WARNING: watchdog library not installed
    echo.
    echo Installing watchdog...
    python -m pip install watchdog
    
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install watchdog
        echo Please install manually: pip install watchdog
        pause
        exit /b 1
    )
    echo [32m✓[0m watchdog installed successfully
)

echo [32m✓[0m Dependencies OK
echo.

REM Check if CODEMAP exists
if not exist ".aura\CODEMAP.json" (
    echo WARNING: CODEMAP not found at .aura\CODEMAP.json
    echo.
    echo Generating CODEMAP...
    python aura_codebase_navigator.py
    
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to generate CODEMAP
        echo Please run manually: python aura_codebase_navigator.py
        pause
        exit /b 1
    )
    echo [32m✓[0m CODEMAP generated successfully
)

echo.
echo Starting CODEMAP File System Watcher...
echo Monitoring workspace for code changes from ANY source
echo.
echo Press Ctrl+C to stop
echo ==========================================
echo.

REM Start the watcher
python aura_codemap_watcher.py

REM Cleanup on exit
echo.
echo [32m✓[0m CODEMAP watcher stopped
pause

@REM Made with Bob
