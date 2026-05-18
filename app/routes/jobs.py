import uuid
import os
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.models import (
    CreateJobRequest, CreateJobResponse,
    JobResponse, JobStatus, Platform
)
from app.database import get_db
from app.services.downloader import detect_platform

router = APIRouter(prefix="/api", tags=["jobs"])

# Temp directory for uploaded audio files
AUDIO_TEMP_DIR = os.getenv("AUDIO_TEMP_DIR", "/app/data/audio_temp")
os.makedirs(AUDIO_TEMP_DIR, exist_ok=True)

@router.post("/audio", response_model=CreateJobResponse)
async def upload_audio(file: UploadFile = File(...)):
    """Handle audio file upload for browser-extracted audio transcription"""
    # Validate file type
    if not file.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="File must be an audio file")

    # Save the uploaded audio file
    audio_id = str(uuid.uuid4())
    audio_path = os.path.join(AUDIO_TEMP_DIR, f"{audio_id}.wav")

    with open(audio_path, "wb") as f:
        content = await file.read()
        f.write(content)

    video_url = f"browser-upload:{audio_id}"

    job_id = str(uuid.uuid4())

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO jobs (id, video_url, platform, status) VALUES (?, ?, ?, ?)",
            (job_id, video_url, platform, "pending")
        )
        conn.commit()

    return CreateJobResponse(job_id=job_id, status=JobStatus.PENDING)

@router.post("/jobs", response_model=CreateJobResponse)
async def create_job(request: CreateJobRequest):
    """Create a new transcription job"""
    video_url = request.video_url
    platform = detect_platform(video_url)

    if platform == "unknown":
        raise HTTPException(status_code=400, detail="Unsupported video platform")

    job_id = str(uuid.uuid4())

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO jobs (id, video_url, platform, status) VALUES (?, ?, ?, ?)",
            (job_id, video_url, platform, "pending")
        )
        conn.commit()

    return CreateJobResponse(job_id=job_id, status=JobStatus.PENDING)

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get job status and results"""
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

        # If completed, get transcription results
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

        return JobResponse(**job)