"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: MIIGWECH (Extension-Based Storage)
DEPENDENCIES: sqlite3, datetime, os, sys, logging
FUNCTIONS: setup_sqlite_logging, log_report, log_error, close_connection, __init__, emit
SYNOPSIS: The `AuraOSLogging` module provides SQLite-backed logging with strict dependency enforcement, utilizing `sqlite3` for storage, `datetime` for timestamps, `os`/`sys` for system interactions, and `logging` for structured output, while exposing `setup_sqlite_logging`, `log_report`, `log_error`, `close_connection`, `__init__`, and `emit` for audit-grade logging operations.
[/AURA_MASTER_KEY]
"""
# [AURA OPTIMIZED] - Bloat removed.

import sqlite3
from datetime import datetime
import logging
import sys
import os

# Global connection instance mapped to the module level
_conn = None

# Enforce topological hygiene: route logs to the protected memory manifold
MEMORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Aura_Memory")
os.makedirs(MEMORY_DIR, exist_ok=True)
DB_PATH = os.path.join(MEMORY_DIR, 'system_logs.db')

def setup_sqlite_logging():
    global _conn
    # 1. Initialize SQLite database with busy-wait timeout and strict pathing
    _conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn = _conn  # Keep local reference mapping safely to the handlers
    
    # Enable non-blocking, high-speed WAL mode for concurrent write thread-safety
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    
    cursor = conn.cursor()
    
    # 2. Define the Thread-Safe Handler
    class SQLiteHandler(logging.Handler):
        def __init__(self, connection):
            super().__init__()
            self.connection = connection
            
        def emit(self, record):
            try:
                # Use a local cursor for isolated thread safety
                local_cursor = self.connection.cursor()
                local_cursor.execute('''
                    INSERT INTO logs (timestamp, level, message, module, function)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    record.levelname,
                    record.getMessage(),
                    record.module,
                    record.funcName
                ))
                self.connection.commit()
            except Exception as e:
                sys.stderr.write(f"[-] SQLite Logging Handler Error: {e}\n")
                self.handleError(record)
                
    # 3. Create the Database Architecture
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            module TEXT,
            function TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            report_type TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            error_type TEXT NOT NULL,
            message TEXT NOT NULL,
            traceback TEXT,
            severity INTEGER DEFAULT 1
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dkt_holographic_log (
            thought_id TEXT PRIMARY KEY,
            binary_state_vector BLOB NOT NULL,
            execution_status TEXT NOT NULL,
            compute_time_ms REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    
    # 4. CREATE THE LOGGER FIRST
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 5. ATTACH THE HANDLERS SECOND
    sqlite_handler = SQLiteHandler(conn)
    logger.addHandler(sqlite_handler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # 6. Return the completed toolset
    return {
        'logger': logger,
        'log_report': log_report,
        'log_error': log_error,
        'close_connection': close_connection
    }

# 7. Global Helper functions mapping safely to the connection
def log_report(report_type, content, metadata=None):
    if not _conn:
        return
    try:
        _conn.execute('''
            INSERT INTO reports (timestamp, report_type, content, metadata)
            VALUES (?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            report_type,
            content,
            str(metadata) if metadata else None
        ))
        _conn.commit()
    except Exception as ex:
        sys.stderr.write(f"[-] Logging Kit: Failed to write report: {ex}\n")
        
def log_error(error_type, message, traceback=None, severity=1):
    if not _conn:
        return
    try:
        _conn.execute('''
            INSERT INTO errors (timestamp, error_type, message, traceback, severity)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            error_type,
            message,
            traceback,
            severity
        ))
        _conn.commit()
    except Exception as ex:
        sys.stderr.write(f"[-] Logging Kit: Failed to write error: {ex}\n")
        
def close_connection():
    global _conn
    if _conn:
        _conn.close()
        _conn = None

