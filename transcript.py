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
    """使用 FFmpeg 提取音频（压缩格式）"""
    sample_rate = config["audio"]["sample_rate"]
    channels = config["audio"]["channels"]
    codec = config["audio"].get("codec", "libopus")
    bitrate = config["audio"].get("bitrate", "32k")

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-codec:a", codec,
        "-b:a", bitrate,
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


def detect_language(text: str) -> str:
    """简单检测文本语言"""
    import re
    # 计算中文字符比例
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(re.findall(r'[\w]', text))
    if total_chars == 0:
        return "en"
    chinese_ratio = chinese_chars / total_chars
    return "zh" if chinese_ratio > 0.3 else "en"


def translate_segments(segments: list[dict], config: dict) -> dict:
    """翻译段落，返回完整译文和原文"""
    client = OpenAI(
        api_key=config["groq"]["api_key"],
        base_url=config["groq"]["base_url"]
    )

    # 合并所有英文段落
    full_english = " ".join(seg["text"] for seg in segments)

    # 检测源语言
    source_lang = detect_language(full_english)

    # 如果是中文，跳过翻译
    if source_lang == "zh":
        return {
            "chinese": full_english,
            "english": full_english,
            "is_translated": False
        }

    # 翻译成中文
    batch_size = 50
    chinese_parts = []

    for i in range(0, len(segments), batch_size):
        batch = segments[i:i + batch_size]
        batch_texts = [seg["text"] for seg in batch]

        messages = [
            {
                "role": "system",
                "content": "You are a professional translator. Translate the following English text to Chinese. Keep the same tone and style. Output only the translation, nothing else."
            },
            {
                "role": "user",
                "content": " ".join(batch_texts)
            }
        ]

        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                response = client.chat.completions.create(
                    model=config["llm"]["model"],
                    messages=messages,
                    temperature=0.3
                )
                chinese_parts.append(response.choices[0].message.content.strip())
                break
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise e
                import time
                time.sleep(2 * retry_count)

    return {
        "chinese": " ".join(chinese_parts),
        "english": full_english,
        "is_translated": True
    }


def write_markdown(video_path: str, translation: dict, output_path: str):
    """写入 Markdown 文件"""
    video_name = Path(video_path).stem

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# {video_name}\n\n")
        f.write("> 转写 / Transcript\n\n")

        if translation["is_translated"]:
            f.write("## 中文\n\n")
            f.write(f"{translation['chinese']}\n\n")
            f.write("---\n\n")
            f.write("## English\n\n")
            f.write(f"{translation['english']}\n\n")
        else:
            f.write("## 原文\n\n")
            f.write(f"{translation['chinese']}\n\n")


def main():
    parser = argparse.ArgumentParser(description="转写视频为双语 Markdown")
    parser.add_argument("video_path", help="视频文件路径")
    parser.add_argument("--keep-audio", action="store_true", help="保留提取的音频文件")
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
    print("步骤 1/3: 提取音频...")
    suffix = ".opus" if config["audio"].get("codec") == "libopus" else ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        audio_path = tmp.name

    try:
        extract_audio(video_path, audio_path, config)
        audio_size = os.path.getsize(audio_path) / (1024 * 1024)
        print(f"音频已提取: {audio_path} ({audio_size:.1f} MB)")

        # 2. Whisper 转写
        print("步骤 2/3: 转写音频...")
        segments = transcribe_audio(audio_path, config)
        print(f"转写完成: {len(segments)} 个段落")

        # 3. 翻译并输出
        print("步骤 3/3: 翻译并生成文档...")
        translation = translate_segments(segments, config)
        if translation["is_translated"]:
            print("翻译完成（英文 → 中文）")
        else:
            print("检测为中文内容，跳过翻译")

        output_path = str(Path(video_path).with_suffix(".transcript.md"))
        write_markdown(video_path, translation, output_path)
        print(f"输出文件: {output_path}")

        print("\n转写完成!")
        return 0

    finally:
        # 清理临时音频文件
        if not args.keep_audio and os.path.exists(audio_path):
            os.unlink(audio_path)
            print(f"已清理音频文件: {audio_path}")


if __name__ == "__main__":
    exit(main())