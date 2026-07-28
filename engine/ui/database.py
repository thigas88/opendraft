import sqlite3
import json
from pathlib import Path
from datetime import datetime

# Database is stored in the project root
DB_PATH = Path(__file__).parent.parent.parent / "opendraft_ui.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            topic TEXT,
            level TEXT,
            status TEXT,
            created_at TEXT,
            updated_at TEXT,
            error_message TEXT,
            current_phase TEXT,
            progress_percent INTEGER,
            progress_details TEXT,
            pdf_path TEXT,
            docx_path TEXT
        )
    ''')
    conn.commit()
    conn.close()

def create_job(job_id: str, topic: str, level: str):
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO jobs (id, topic, level, status, created_at, updated_at, progress_percent, progress_details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (job_id, topic, level, 'running', now, now, 0, '{}'))
    conn.commit()
    conn.close()

def get_job(job_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_all_jobs():
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM jobs ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_job(job_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM jobs WHERE id = ?', (job_id,))
    conn.commit()
    conn.close()

def reset_job_status(job_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE jobs 
        SET status = 'running', error_message = NULL, updated_at = ? 
        WHERE id = ?
    ''', (datetime.now().isoformat(), job_id))
    conn.commit()
    conn.close()
