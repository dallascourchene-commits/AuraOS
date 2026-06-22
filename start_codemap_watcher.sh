#!/bin/bash
# Quick-start script for CODEMAP File System Watcher
# This script starts the watcher with sensible defaults

echo "=========================================="
echo "CODEMAP File System Watcher"
echo "=========================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "ERROR: Python not found"
    echo "Please install Python 3.7 or later"
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# Check if watchdog is installed
echo "Checking dependencies..."
if ! $PYTHON_CMD -c "import watchdog" 2>/dev/null; then
    echo "WARNING: watchdog library not installed"
    echo ""
    echo "Installing watchdog..."
    $PYTHON_CMD -m pip install watchdog
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "ERROR: Failed to install watchdog"
        echo "Please install manually: pip install watchdog"
        exit 1
    fi
    echo "✅ watchdog installed successfully"
fi

echo "✅ Dependencies OK"
echo ""

# Check if CODEMAP exists
if [ ! -f ".aura/CODEMAP.json" ]; then
    echo "WARNING: CODEMAP not found at .aura/CODEMAP.json"
    echo ""
    echo "Generating CODEMAP..."
    $PYTHON_CMD aura_codebase_navigator.py
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "ERROR: Failed to generate CODEMAP"
        echo "Please run manually: python aura_codebase_navigator.py"
        exit 1
    fi
    echo "✅ CODEMAP generated successfully"
fi

echo ""
echo "Starting CODEMAP File System Watcher..."
echo "Monitoring workspace for code changes from ANY source"
echo ""
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

# Start the watcher
$PYTHON_CMD aura_codemap_watcher.py

# Cleanup on exit
echo ""
echo "✅ CODEMAP watcher stopped"

# Made with Bob
