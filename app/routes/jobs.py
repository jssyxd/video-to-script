import uuid
from fastapi import APIRouter, HTTPException
from app.models import (
    CreateJobRequest, CreateJobResponse,
    JobResponse, JobStatus, Platform
)
from app.database import get_db
from app.services.downloader import detect_platform

router = APIRouter(prefix="/api", tags=["jobs"])

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
                "SELECT english_text, chinese_text FROM transcripts WHERE job_id = ? ORDER BY segment_index",
                (job_id,)
            )
            transcripts = [
                {"english": r[0], "chinese": r[1]}
                for r in cursor.fetchall()
            ]
            job["transcript"] = transcripts

        return JobResponse(**job)