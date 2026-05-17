from pydantic import BaseModel, HttpUrl
from typing import Optional, List
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

class TranscriptSegment(BaseModel):
    english: str
    chinese: str

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    video_url: Optional[str] = None
    platform: Optional[Platform] = None
    progress: Optional[int] = None
    error_message: Optional[str] = None
    transcript: Optional[List[TranscriptSegment]] = None