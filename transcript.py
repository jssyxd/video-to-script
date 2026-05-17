#!/usr/bin/env python3
"""OmniGet Video Transcript CLI - 转写视频为双语 Markdown"""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

import yaml
from openai import OpenAI


def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def check_ffmpeg():
    """检查 FFmpeg 是否可用"""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def extract_audio(video_path: str, output_path: str, config: dict):
    """使用 FFmpeg 提取音频"""
    sample_rate = config["audio"]["sample_rate"]
    channels = config["audio"]["channels"]

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-vn", output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg 提取音频失败: {result.stderr}")

    return output_path


def transcribe_audio(audio_path: str, config: dict) -> list[dict]:
    """使用 Groq Whisper API 转写音频"""
    client = OpenAI(
        api_key=config["groq"]["api_key"],
        base_url=config["groq"]["base_url"]
    )

    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model=config["whisper"]["model"],
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["segment"]
        )

    # 返回分段结果
    segments = []
    if hasattr(transcript, 'segments'):
        for seg in transcript.segments:
            segments.append({
                "text": seg.text.strip(),
                "start": seg.start,
                "end": seg.end
            })
    else:
        # fallback: 整个音频作为一个段落
        segments.append({
            "text": transcript.text.strip(),
            "start": 0.0,
            "end": 0.0
        })

    return segments


def translate_segments(segments: list[dict], config: dict) -> list[dict]:
    """使用 Groq LLM API 翻译段落"""
    client = OpenAI(
        api_key=config["groq"]["api_key"],
        base_url=config["groq"]["base_url"]
    )

    results = []
    for seg in segments:
        english_text = seg["text"]

        # 构建翻译 prompt
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

        response = client.chat.completions.create(
            model=config["llm"]["model"],
            messages=messages,
            temperature=0.3
        )

        chinese_text = response.choices[0].message.content.strip()

        results.append({
            "english": english_text,
            "chinese": chinese_text
        })

    return results


def write_markdown(video_path: str, translations: list[dict], output_path: str):
    """写入双语 Markdown 文件"""
    video_name = Path(video_path).stem

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# {video_name}\n\n")
        f.write("> 双语转写 / Bilingual Transcript\n\n")

        for item in translations:
            f.write("**English:**\n")
            f.write(f"{item['english']}\n\n")
            f.write("**中文:**\n")
            f.write(f"{item['chinese']}\n\n")
            f.write("---\n\n")


def main():
    parser = argparse.ArgumentParser(description="转写视频为双语 Markdown")
    parser.add_argument("video_path", help="视频文件路径")
    args = parser.parse_args()

    # 检查文件是否存在
    if not os.path.exists(args.video_path):
        print(f"错误: 文件不存在 - {args.video_path}")
        return 1

    # 检查 FFmpeg
    if not check_ffmpeg():
        print("错误: FFmpeg 不可用。请安装 FFmpeg。")
        return 1

    config = load_config()
    video_path = args.video_path

    print(f"开始转写: {video_path}")

    # 1. 提取音频
    print("步骤 1/4: 提取音频...")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_path = tmp.name

    try:
        extract_audio(video_path, audio_path, config)
        print(f"音频已提取: {audio_path}")

        # 2. Whisper 转写
        print("步骤 2/4: 转写音频...")
        segments = transcribe_audio(audio_path, config)
        print(f"转写完成: {len(segments)} 个段落")

        # 3. 翻译
        print("步骤 3/4: 翻译内容...")
        translations = translate_segments(segments, config)
        print("翻译完成")

        # 4. 输出 Markdown
        print("步骤 4/4: 生成 Markdown...")
        output_path = str(Path(video_path).with_suffix(".transcript.md"))
        write_markdown(video_path, translations, output_path)
        print(f"输出文件: {output_path}")

        print("\n转写完成!")
        return 0

    finally:
        # 清理临时音频文件
        if os.path.exists(audio_path):
            os.unlink(audio_path)


if __name__ == "__main__":
    exit(main())