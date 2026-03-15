# Zen LLM Compare

[![GitHub Stars](https://img.shields.io/github/stars/GeoHaberC/Zen_LLM_Compare?style=social)](https://github.com/GeoHaberC/Zen_LLM_Compare/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/GeoHaberC/Zen_LLM_Compare?style=social)](https://github.com/GeoHaberC/Zen_LLM_Compare/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/GeoHaberC/Zen_LLM_Compare)](https://github.com/GeoHaberC/Zen_LLM_Compare/issues)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

> **Run the same prompt through multiple local LLMs simultaneously — speed, quality, and RAM, ranked side-by-side.**

Zen LLM Compare is a self-hosted, zero-cloud benchmarking tool for local GGUF language models.  
Send any prompt to 1–8 models at once, score every response with a configurable **LLM judge**, and get a ranked results table with per-model metrics in seconds.

---

## ✨ Features

- **Side-by-side inference** — up to 8 local GGUF models run in parallel threads
- **LLM-as-judge scoring** — a separate local model grades every response on accuracy, reasoning, instruction-following, and safety (0–10)
- **5 judge templates** — Medical Triage · Clinical Decision · Research · Code Review · Creative Writing
- **100+ question bank** — categorised test prompts (emergency, cardiology, coding, reasoning, multilingual)
- **Live performance metrics** — TTFT, tokens/s, RAM delta, total time
- **Monkey Mode 🐒** — randomised model + prompt + judge for unattended regression runs
- **Zena AI assistant** — built-in chat powered by any of your local models
- **No build step** — single HTML file + one Python file, pure stdlib backend
- **Dark mode** · **RTL languages** (Hebrew, Arabic) · **CSV export**

---

## 🚀 Quick Start

### Windows — one click
Double-click **`Run_me.bat`**. It starts the backend and opens the UI automatically.

### Manual

```bash
# Install Python dependencies (once)
pip install -r requirements.txt

# Start the backend (serves UI + API on port 8123)
python comparator_backend.py

# Open in browser
# http://127.0.0.1:8123
```

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `llama-cpp-python` | Local GGUF model inference |
| `psutil` | RAM / CPU monitoring |
| `huggingface_hub` | Model downloads |

```bash
pip install -r requirements.txt
```

`llama-cpp-python` can also be installed directly from the UI (Settings → Install llama.cpp).

---

## 🗂️ Model Storage

Drop `.gguf` files into **`C:\AI\Models`** — they are auto-detected on startup and after each download.  
Additional directories can be added by editing `MODEL_DIRS` in `comparator_backend.py`.

---

## 🏗️ Architecture

```
Browser  ─────────────────────────────────────────
  model_comparator.html  (single-file SPA)
         │  HTTP  │
         ▼        ▼
comparator_backend.py  :8123
         │
         ├── GET  /                    serve the HTML app
         ├── GET  /__system-info       hardware scan + model list
         ├── POST /__comparison/mixed  parallel inference + judge scoring
         ├── POST /__chat              Zena assistant chat
         ├── POST /__download-model    fetch GGUF from URL
         ├── POST /__install-llama     pip install llama_cpp
         └── GET  /__install-status   install progress
```

- **Frontend** — vanilla JS, Tailwind CSS (CDN), no framework, no build step
- **Backend** — Python `ThreadingHTTPServer` (stdlib only + `llama_cpp`)
- **Judge** — same backend, different model instance; fires after all comparisons complete

---

## 🖥️ Usage

1. **Start** — run `Run_me.bat` or `python comparator_backend.py`
2. **Select models** — tick checkboxes in the left panel (auto-scanned from `C:\AI\Models`)
3. **Enter a prompt** — or pick one from the 📚 Question Bank
4. **Choose a judge template** and a **judge model**
5. **Click RUN** — results appear as each model finishes; judge scores follow

### Results table (12 columns)
`Rank · Model · TTFT · Tokens/s · RAM ↑ · Quality ★ · Accuracy · Reasoning · Instruction · Safety · Response · Actions`

---

## 📊 Judge Templates

| Template | Best for |
|----------|----------|
| Medical Triage | Emergency / urgent care |
| Clinical Decision | Differential diagnosis, treatment planning |
| Research Analysis | Literature review, evidence grading |
| Code Review | Programming, debugging, algorithms |
| Creative Writing | Open-ended narrative and language quality |

All templates output a unified JSON schema: `overall · accuracy · reasoning · instruction · safety · explanation`

---

## 📁 File Structure

| File | Role |
|---|---|
| `model_comparator.html` | Complete single-file SPA — UI, CSS, JS |
| `comparator_backend.py` | Python HTTP API — hardware scan, inference, judge, downloads |
| `requirements.txt` | Python dependencies |
| `Run_me.bat` | One-click Windows launcher |
| `HOW_TO_USE.md` | Full user guide (also used as Zena's system prompt) |
| `zena_256x256.png` | Zena avatar |

---

## ⚙️ Configuration

| Setting | Where to change |
|---|---|
| Backend port (default `8123`) | Top of `comparator_backend.py` · `const BACKEND` in the HTML |
| Model scan directories | `MODEL_DIRS` list in `comparator_backend.py` |
| Judge system prompt | Judge Template dropdown in the UI |

---

## 🧪 Tests

```bash
pytest tests/
```

Open `tests/test_comparator.html` in a browser for the JS unit test suite.

---

## 📄 License

MIT — see [LICENSE](LICENSE)
