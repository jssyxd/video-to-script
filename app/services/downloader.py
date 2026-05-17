import os
import yt_dlp
from typing import Optional

BILIBILI_COOKIE = os.getenv("BILIBILI_COOKIE", "")

def detect_platform(url: str) -> str:
    """Detect video platform from URL"""
    lower = url.lower()
    if "youtube.com" in lower or "youtu.be" in lower:
        return "youtube"
    if "bilibili.com" in lower or "b23.tv" in lower:
        return "bilibili"
    return "unknown"

def download_audio(url: str, output_path: str) -> tuple[bool, str]:
    """
    Download video audio
    Returns: (success_flag, error_message)
    """
    platform = detect_platform(url)

    if platform == "unknown":
        return False, f"Unsupported platform: {url}"

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
    }

    # Bilibili requires Cookie
    if platform == "bilibili" and BILIBILI_COOKIE:
        ydl_opts['cookiefile'] = None

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return True, ""
    except Exception as e:
        return False, str(e)

def get_video_info(url: str) -> dict:
    """Get video information"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            'title': info.get('title', 'unknown'),
            'duration': info.get('duration', 0),
            'platform': detect_platform(url)
        }