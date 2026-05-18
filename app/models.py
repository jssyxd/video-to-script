from pydantic import BaseModel, HttpUrl
from typing import Optional
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Platform(str, Enum):
    YOUTUBE = "youtube"
    BILIBILI = "bilibili"
    UNKNOWN = "unknown"

class CreateJobRequest(BaseModel):
    video_url: str

class CreateJobResponse(BaseModel):
    job_id: str
    status: JobStatus

class TranscriptResult(BaseModel):
    chinese: str
    english: str
    is_translated: bool

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    video_url: Optional[str] = None
    platform: Optional[Platform] = None
    progress: Optional[int] = None
    error_message: Optional[str] = None
    transcript: Optional[TranscriptResult] = None