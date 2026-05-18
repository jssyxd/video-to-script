# video-to-script

A Flask web application that transcribes videos to text using Whisper, with job queue management and translation support.

## Architecture

- **Flask API server** (`app/main.py`) — serves web interface and job API
- **Worker process** (`app/worker.py`) — processes transcription jobs from a Redis queue
- **Services**:
  - `services/downloader.py` — downloads video from URL
  - `services/transcriber.py` — transcribes audio using Whisper
  - `services/translator.py` — translates transcript using LibreTranslate
- **Database** (`app/database.py`) — SQLite for job state management
- **Routes** (`app/routes/jobs.py`) — REST API for job submission and status

## Running locally

```bash
pip install -r requirements.txt
python app/main.py        # API server
python app/worker.py       # Background worker (separate terminal)
```

## Configuration

- `config.yaml` — API keys and service endpoints
- `render.yaml` — Deployment configuration (Render.com)

## Tech stack

Flask, Redis, SQLite, Whisper (OpenAI), LibreTranslate

## Agent skills

### Issue tracker

GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses defaults (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — one CONTEXT.md at repo root if needed. See `docs/agents/domain.md`.