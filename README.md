# OmniGet Video Transcript CLI

视频转写工具，将视频文件转写为双语（中英文）Markdown 格式。

## 功能

- FFmpeg 音频提取
- Groq Whisper large-v3 语音转文字
- Groq Llama 3.3 翻译为中文
- 双语 Markdown 输出

## 安装

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 FFmpeg (macOS)
brew install ffmpeg

# 安装 FFmpeg (Ubuntu/Debian)
sudo apt install ffmpeg

# 安装 FFmpeg (Windows)
# 下载 https://ffmpeg.org/download.html
```

## 配置

编辑 `config.yaml` 修改 API 设置：

```yaml
groq:
  api_key: "your-api-key"
  base_url: "https://api.groq.com/openai/v1"
```

## 使用

```bash
python transcript.py /path/to/video.mp4
```

输出文件：`/path/to/video.transcript.md`

## 输出格式

**English:**
[英文原文]

**中文:**
[中文翻译]

---

## 依赖

- Python 3.8+
- FFmpeg
- Groq API Key