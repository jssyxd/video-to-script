import os
import sys
import uuid
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# ============== Database ==============
DATABASE_URL = os.getenv("DATABASE_URL", "/tmp/video_to_script.db")
DB_DIR = os.path.dirname(DATABASE_URL)

def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            english_text TEXT NOT NULL,
            chinese_text TEXT NOT NULL,
            segment_index INTEGER NOT NULL,
            is_translated INTEGER DEFAULT 1,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)
    conn.commit()
    conn.close()

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# ============== FastAPI ==============
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse

app = FastAPI()

# ============== Routes ==============

@app.get("/")
async def root():
    api_dir = os.path.dirname(os.path.abspath(__file__))
    home_html = os.path.join(api_dir, "home.html")
    if os.path.exists(home_html):
        return FileResponse(home_html)
    return {"message": "Video to Script API"}

@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, video_url, platform, status, error_message FROM jobs WHERE id = ?",
            (job_id,)
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Job not found")

        job = {
            "job_id": row[0],
            "video_url": row[1],
            "platform": row[2],
            "status": row[3],
            "error_message": row[4]
        }

        if row[3] == "completed":
            cursor.execute(
                "SELECT english_text, chinese_text, is_translated FROM transcripts WHERE job_id = ? ORDER BY segment_index LIMIT 1",
                (job_id,)
            )
            transcript_row = cursor.fetchone()
            if transcript_row:
                job["transcript"] = {
                    "chinese": transcript_row[1],
                    "english": transcript_row[0],
                    "is_translated": bool(transcript_row[2])
                }

        return job

@app.post("/api/jobs")
async def create_job(request: Request):
    try:
        body = await request.json()
    except:
        body = {}
    video_url = body.get("video_url", "")
    if not video_url:
        raise HTTPException(status_code=400, detail="video_url required")

    job_id = str(uuid.uuid4())
    platform = "unknown"
    if "youtube.com" in video_url.lower() or "youtu.be" in video_url.lower():
        platform = "youtube"
    elif "bilibili.com" in video_url.lower() or "b23.tv" in video_url.lower():
        platform = "bilibili"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO jobs (id, video_url, platform, status) VALUES (?, ?, ?, ?)",
            (job_id, video_url, platform, "pending")
        )
        conn.commit()

    return {"job_id": job_id, "status": "pending"}

@app.post("/api/audio")
async def upload_audio(file: UploadFile = File(...)):
    if not file.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="File must be an audio file")

    audio_id = str(uuid.uuid4())
    audio_dir = os.getenv("AUDIO_TEMP_DIR", "/tmp/audio_temp")
    os.makedirs(audio_dir, exist_ok=True)
    audio_path = os.path.join(audio_dir, f"{audio_id}.wav")

    with open(audio_path, "wb") as f:
        content = await file.read()
        f.write(content)

    job_id = str(uuid.uuid4())

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO jobs (id, video_url, platform, status) VALUES (?, ?, ?, ?)",
            (job_id, f"browser-upload:{audio_id}", "unknown", "pending")
        )
        conn.commit()

    return {"job_id": job_id, "status": "pending"}

# Initialize DB on startup
init_db()