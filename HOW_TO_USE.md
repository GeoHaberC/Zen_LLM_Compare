# Zen LLM Compare — How to Use

> **For humans and LLMs alike.** This document is the primary knowledge source for Zena (the built-in AI assistant). It is also useful as a system prompt for any external LLM that needs to understand this app.

---

## What Is Zen LLM Compare?

Zen LLM Compare (codename **Swarm**) is a self-hosted, browser-based benchmarking tool that runs multiple local GGUF language models **side-by-side** on the same prompt, scores every response with a configurable **LLM judge**, and presents ranked results with detailed performance metrics.

Key properties:
- **Zero cloud dependency.** All inference runs locally via `llama-cpp-python`.
- **Single HTML file UI.** `model_comparator.html` — no build step, no framework.
- **Python backend.** `comparator_backend.py` (stdlib + `llama_cpp`) on port **8123**.
- **Supports 1–8 models per run** in parallel threads.
- **Judge model is also a local GGUF** — you choose which model grades the others.

---

## Architecture

```
Browser (model_comparator.html)
        │  HTTP  │
        ▼        ▼
comparator_backend.py  :8123
        │
        ├── /__system-info      (GET)  — scan models, RAM, GPU
        ├── /__comparison/mixed (POST) — run models + judge
        ├── /__download-model   (POST) — fetch GGUF from URL
        ├── /__install-llama    (POST) — pip install llama_cpp
        ├── /__install-status   (GET)  — install progress
        └── /__chat             (POST) — Zena chat assistant
```

---

## Quick Start

1. **Start the backend:**  double-click `Run_me.bat`  
   (or `python comparator_backend.py` in a terminal)

2. **Open the UI:** the bat file opens `model_comparator.html` automatically,  
   or open it manually in any modern browser.

3. **First run:** The app scans `C:\AI\Models` (and sub-directories) on load.  
   Each found `.gguf` file becomes a selectable chip.

4. **Select models** in the left panel, **type a prompt**, choose a **judge model**,  
   then click the big **RUN** button.

---

## Adding Models

| Method | Steps |
|--------|-------|
| **Local file** | Drop a `.gguf` into `C:\AI\Models`, then click **Scan** in the app |
| **Download tab** | Paste a HuggingFace direct-download URL and click Download |
| **Custom path** | Edit `MODEL_DIRS` in `comparator_backend.py` to add more directories |

Model scanning is automatic on page load and after each download completes.

---

## Running a Comparison

1. **Tick 1–8 model checkboxes** in the Models panel (left side).
2. **Type or paste a prompt** in the Prompt box.
3. **Choose a Judge template** from the dropdown (see Judge Templates below).
4. **Choose the Judge model** — a separate GGUF that will score all responses.
5. Click **RUN** (or press the hotkey shown on the button).
6. Results appear in the table as each model finishes; the judge scores appear once all models are done.

### Parallel execution
All selected models run simultaneously in background threads. Faster/smaller models finish first and appear incrementally.

---

## Judge Templates

Each template focuses on different scoring criteria. All output a unified JSON schema:

```json
{
  "overall": 0–10,
  "accuracy": 0–10,
  "reasoning": 0–10,
  "instruction": 0–10,
  "safety": 0–10,
  "explanation": "free-text rationale"
}
```

| Template | Best for |
|----------|----------|
| **Medical Triage** | Emergency / urgent care prompts |
| **Clinical Decision Support** | Differential diagnosis, treatment planning |
| **Research Analysis** | Literature review, evidence grading |
| **Code Review** | Programming, debugging, algorithm questions |
| **Creative Writing** | Open-ended, narrative, language quality |

---

## Question Bank

The Question Bank (📚 chip row below the prompt box) contains 100+ categorised test prompts:

| Category | Examples |
|----------|---------|
| **Emergency** | Chest pain triage, sepsis protocol, trauma assessment |
| **Ops** | Medication reconciliation, discharge planning |
| **Cardiology** | ACS workup, arrhythmia management |
| **Coding** | Python debugging, algorithm design, SQL optimisation |
| **Reasoning** | Logic puzzles, multi-step inference |
| **Multilingual** | Prompts in Hebrew, Arabic, Spanish, French, German |

Click any chip to instantly load that prompt into the text box.

---

## Results Table

After a run, the results table shows 12 columns:

| Column | Description |
|--------|-------------|
| **Rank** | Sorted by `overall` judge score (highest = 1) |
| **Model** | Short model name (`.gguf` removed) |
| **TTFT (s)** | Time to first token in seconds |
| **Tokens/s** | Generation throughput |
| **RAM ↑ (MB)** | RAM consumed during inference |
| **Quality ★** | Overall judge score rendered as stars (0–5) |
| **Accuracy** | Judge sub-score |
| **Reasoning** | Judge sub-score |
| **Instruction** | Judge sub-score |
| **Safety** | Judge sub-score |
| **Response** | Truncated preview (click ▶ to expand full text) |
| **Actions** | Copy / Expand buttons |

### Metrics Summary Bar
Above the table shows the champions for the current run:
- ⚡ **Fastest TTFT** — model with lowest time to first token
- 🚀 **Best Tok/s** — highest throughput
- 💾 **Peak RAM** — highest RAM delta recorded
- ⭐ **Top Quality** — highest overall judge score

---

## Monkey Mode 🐒

Click **RANDOM** (the monkey button) to:
1. Pick a random subset of available models.
2. Select a random prompt from the Question Bank.
3. Pick a random judge template.
4. Run the comparison automatically.

Useful for unattended regression testing or discovering model performance across diverse prompts.

---

## Language Switcher

Click the **🇺🇸 EN ▾** flag button in the nav bar to switch language.

Supported languages: English · Hebrew (עברית) · Arabic (العربية) · Spanish · French · German.

RTL layout is applied automatically for Hebrew and Arabic.

---

## Dark Mode

Toggle via the **🌙 / ☀** button in the nav bar. Preference is saved to `localStorage`.

---

## Export CSV

After a run, click **Export CSV** to download all result columns as a CSV file.  
The filename includes the prompt (truncated) and a timestamp.

---

## Zena Chat Assistant

Zena is the built-in AI assistant (this app itself).

1. Click **Ask Zena** in the footer bar.
2. Select a local model from the dropdown (auto-selects the largest available).
3. Type a question and press **Enter** (Shift+Enter = newline).
4. Zena answers using the selected model through `/__chat`.

**Session history**: last 8 conversation turns are sent for context.  
**System prompt**: the full content of this HOW_TO_USE document, so Zena always knows the app.

---

## API Reference (for LLMs)

All endpoints accept/return JSON. CORS is open (`*`).

### `GET /__system-info`
Returns detected models, system RAM, GPU info.

```json
{
  "models": [{"name": "mistral-7b.gguf", "path": "C:\\AI\\Models\\mistral-7b.gguf", "size_mb": 4096}],
  "ram_total_mb": 32000,
  "ram_free_mb": 18000,
  "gpu": "NVIDIA RTX 3090"
}
```

### `POST /__comparison/mixed`
Runs a full benchmark comparison.

```json
{
  "models": ["C:\\AI\\Models\\model-a.gguf", "C:\\AI\\Models\\model-b.gguf"],
  "prompt": "Explain the Ottawa Ankle Rules.",
  "judge_model": "C:\\AI\\Models\\judge.gguf",
  "judge_template": "medical_triage",
  "max_tokens": 512,
  "temperature": 0.7
}
```

### `POST /__chat`
Single-turn or multi-turn chat with a local model.

```json
{
  "model_path": "C:\\AI\\Models\\mistral-7b.gguf",
  "system": "You are a helpful assistant.",
  "messages": [
    {"role": "user", "content": "How do I add a new model?"}
  ],
  "max_tokens": 512,
  "temperature": 0.4
}
```

Response:
```json
{ "response": "Drop a .gguf file into C:\\AI\\Models and click Scan..." }
```

### `POST /__download-model`
```json
{ "url": "https://huggingface.co/.../model.gguf", "dest_dir": "C:\\AI\\Models" }
```

### `POST /__install-llama`
Triggers `pip install llama-cpp-python` with GPU flags. Poll `/__install-status` for progress.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| No models found | Check `MODEL_DIRS` in `comparator_backend.py`; ensure `.gguf` files exist |
| Backend not responding | Make sure `Run_me.bat` is running; check port 8123 is not blocked |
| Judge returns `parse error` | Judge model too small or wrong template; try a larger judge |
| GPU not used | Install `llama-cpp-python` with CUDA: `pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121` |
| High RAM usage | Reduce `n_ctx` in `comparator_backend.py` or run fewer models in parallel |
| Zena chat slow | Use a smaller/quantised model (Q4_K_M recommended for chat) |

---

## Tips for LLMs Using This App

- To test the app: `POST /__comparison/mixed` with 2 models and a short prompt.
- Judge template names: `medical_triage`, `clinical_decision`, `research_analysis`, `code_review`, `creative_writing`.
- All file paths must use the **server's** filesystem path (e.g., `C:\AI\Models\...`).
- The `messages` array in `/__chat` follows the OpenAI chat format (`role`: `user`/`assistant`/`system`).
- Token counts and RAM figures are approximate; `llama_cpp` reports them per-run.
