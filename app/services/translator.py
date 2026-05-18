import openai
import os
import re
from typing import List

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = "llama-3.3-70b-versatile"

def detect_language(text: str) -> str:
    """Simple language detection based on Chinese character ratio"""
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(re.findall(r'[\w]', text))
    if total_chars == 0:
        return "en"
    chinese_ratio = chinese_chars / total_chars
    return "zh" if chinese_ratio > 0.3 else "en"


def translate_segments(segments: List[dict]) -> dict:
    """
    Translate segments to Chinese
    Input: [{"text": "Hello world", "start": 0.0, "end": 1.5}, ...]
    Returns: {"chinese": "...", "english": "...", "is_translated": bool}
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")

    client = openai.OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )

    # Join all English text
    full_english = " ".join(seg["text"] for seg in segments if seg.get("text"))

    # Detect source language
    source_lang = detect_language(full_english)

    # If Chinese, skip translation
    if source_lang == "zh":
        return {
            "chinese": full_english,
            "english": full_english,
            "is_translated": False
        }

    # Translate to Chinese in batches
    batch_size = 50
    chinese_parts = []

    segment_texts = [seg["text"] for seg in segments if seg.get("text")]
    for i in range(0, len(segment_texts), batch_size):
        batch = segment_texts[i:i + batch_size]
        batch_text = " ".join(batch)

        messages = [
            {
                "role": "system",
                "content": "You are a professional translator. Translate the following English text to Chinese. Keep the same tone and style. Output only the translation, nothing else."
            },
            {
                "role": "user",
                "content": batch_text
            }
        ]

        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                response = client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=messages,
                    temperature=0.3
                )
                chinese_parts.append(response.choices[0].message.content.strip())
                break
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    chinese_parts.append(f"[Translation failed: {str(e)}]")
                import time
                time.sleep(2 * retry_count)

    return {
        "chinese": " ".join(chinese_parts),
        "english": full_english,
        "is_translated": True
    }