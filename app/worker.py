#!/usr/bin/env python3
"""Background Worker - Process transcription jobs"""

import os
import time
import subprocess
import tempfile

from app.database import get_db
from app.services.downloader import download_audio, detect_platform
from app.services.transcriber import transcribe_audio
from app.services.translator import translate_segments

DATABASE_URL = os.getenv("DATABASE_URL", "/app/data/video_to_script.db")
TEMP_DIR = "/app/data/temp"

def update_job_status(job_id: str, status: str, error_message: str = None):
    """Update job status in database"""
    with get_db() as conn:
        cursor = conn.cursor()
        if error_message:
            cursor.execute(
                "UPDATE jobs SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, error_message, job_id)
            )
        else:
            cursor.execute(
                "UPDATE jobs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, job_id)
            )
        conn.commit()

def save_transcripts(job_id: str, transcripts: list):
    """Save transcription results to database"""
    with get_db() as conn:
        cursor = conn.cursor()
        for idx, seg in enumerate(transcripts):
            cursor.execute(
                "INSERT INTO transcripts (job_id, english_text, chinese_text, segment_index) VALUES (?, ?, ?, ?)",
                (job_id, seg["english"], seg["chinese"], idx)
            )
        conn.commit()

def process_job(job_id: str):
    """Process a single transcription job"""
    # Get job info from database
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT video_url FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            return
        video_url = row[0]

    update_job_status(job_id, "processing")

    os.makedirs(TEMP_DIR, exist_ok=True)

    try:
        # Step 1: Detect platform
        platform = detect_platform(video_url)

        # Step 2: Download audio
        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False, dir=TEMP_DIR) as tmp:
            audio_path = tmp.name

        success, error = download_audio(video_url, audio_path)
        if not success:
            update_job_status(job_id, "failed", f"Download failed: {error}")
            return

        # Step 3: Convert audio format with FFmpeg
        wav_path = audio_path.replace(".m4a", ".wav")
        result = subprocess.run([
            "ffmpeg", "-y", "-i", audio_path,
            "-ar", "16000", "-ac", "1", wav_path
        ], capture_output=True, text=True)
        if result.returncode != 0:
            update_job_status(job_id, "failed", f"Audio conversion failed: {result.stderr}")
            return

        # Step 4: Whisper transcription
        segments = transcribe_audio(wav_path)

        # Step 5: Translate
        transcripts = translate_segments(segments)

        # Step 6: Save results
        save_transcripts(job_id, transcripts)

        # Cleanup temp files
        try:
            os.unlink(audio_path)
            os.unlink(wav_path)
        except:
            pass

        update_job_status(job_id, "completed")

    except Exception as e:
        update_job_status(job_id, "failed", str(e))

def poll_jobs():
    """Poll for pending jobs"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM jobs WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row[0]
    return None

def run_worker():
    """Worker main loop"""
    print("Worker started")
    while True:
        job_id = poll_jobs()
        if job_id:
            print(f"Processing job: {job_id}")
            process_job(job_id)
        else:
            time.sleep(5)

if __name__ == "__main__":
    run_worker()