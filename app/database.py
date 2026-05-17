import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "/app/data/video_to_script.db")
DB_DIR = os.path.dirname(DATABASE_URL)

def init_db():
    """Initialize database and create tables"""
    os.makedirs(DB_DIR, exist_ok=True)

    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Job table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            video_url TEXT NOT NULL,
            platform TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            result_path TEXT,
            error_message TEXT
        )
    """)

    # Transcript table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            english_text TEXT NOT NULL,
            chinese_text TEXT NOT NULL,
            segment_index INTEGER NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)

    conn.commit()
    conn.close()

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db_on_import():
    """Initialize database on module import"""
    init_db()