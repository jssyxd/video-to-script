import openai
import os
from typing import List

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
WHISPER_MODEL = "whisper-large-v3"

def transcribe_audio(audio_path: str) -> List[dict]:
    """
    Transcribe audio using Whisper
    Returns: [{"text": "...", "start": 0.0, "end": 1.5}, ...]
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")

    client = openai.OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )

    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["segment"]
        )

    segments = []
    if hasattr(transcript, 'segments') and transcript.segments:
        for seg in transcript.segments:
            segments.append({
                "text": seg.text.strip(),
                "start": seg.start,
                "end": seg.end
            })
    else:
        # Fallback: entire audio as one segment
        segments.append({
            "text": transcript.text.strip() if hasattr(transcript, 'text') else "",
            "start": 0.0,
            "end": 0.0
        })

    return segments