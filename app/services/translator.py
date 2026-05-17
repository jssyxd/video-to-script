import openai
import os
from typing import List

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = "llama-3.3-70b-versatile"

def translate_segments(segments: List[dict]) -> List[dict]:
    """
    Translate segments to Chinese
    Input: [{"text": "Hello world", "start": 0.0, "end": 1.5}, ...]
    Returns: [{"english": "Hello world", "chinese": "你好世界"}, ...]
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")

    client = openai.OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )

    results = []
    for seg in segments:
        english_text = seg["text"]
        if not english_text:
            continue

        messages = [
            {
                "role": "system",
                "content": "You are a professional translator. Translate the following English text to Chinese. Keep the same tone and style. Output only the translation, nothing else."
            },
            {
                "role": "user",
                "content": english_text
            }
        ]

        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=0.3
            )
            chinese_text = response.choices[0].message.content.strip()
        except Exception as e:
            chinese_text = f"[Translation failed: {str(e)}]"

        results.append({
            "english": english_text,
            "chinese": chinese_text
        })

    return results