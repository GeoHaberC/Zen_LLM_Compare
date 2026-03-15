# LLM Model Comparator — Swarm Test

Send the same prompt to multiple local GGUF models side-by-side and compare speed, quality, and resource usage.

## Quick Start

Double-click **`Run_me.bat`** — it starts both servers and opens the browser automatically.

Or manually:

```bash
# Terminal 1 — Backend API (port 8123)
python comparator_backend.py 8123

# Terminal 2 — Frontend file server (port 8889)
python -m http.server 8889

# Then open:
# http://127.0.0.1:8889/model_comparator.html
```

## Dependencies

```bash
pip install -r requirements.txt
```

| Package | Purpose |
|---|---|
| `psutil` | RAM / CPU detection |
| `huggingface_hub` | Model downloads |
| `llama-cpp-python` | Local model inference |

## Model Storage

Put `.gguf` files in `C:\AI\Models` — they are auto-detected on startup.

## Ports

| Port | Service | Change in |
|---|---|---|
| `8123` | Backend API | `comparator_backend.py` line 1 · `model_comparator.html` `const BACKEND` |
| `8889` | Frontend | `Run_me.bat` |

## Files

| File | Role |
|---|---|
| `model_comparator.html` | Single-file SPA frontend |
| `comparator_backend.py` | Python HTTP API — hardware detection, model scan, comparison, downloads |
| `requirements.txt` | Python dependencies |
| `Run_me.bat` | One-click launcher |
