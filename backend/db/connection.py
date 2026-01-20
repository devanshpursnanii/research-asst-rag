"""
Database Connection Layer
Pure SQLite connection management with no business logic.
"""

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).parent.parent.parent / "logs.db"


def get_connection() -> sqlite3.Connection:
    """
    Get a SQLite database connection with proper configuration.
    
    Returns:
        Configured sqlite3.Connection
    """
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Enable dict-like row access
    conn.row_factory = sqlite3.Row
    
    return conn
