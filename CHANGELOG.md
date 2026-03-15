# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Vulkan GPU backend support for AMD Radeon 890M (RDNA 3.5)
- ThreadingHTTPServer — inference no longer blocks UI polling requests
- Backend now serves `model_comparator.html` directly (single-server setup)
- Auto-judge selection: picks largest model when no judge is manually chosen
- Chat bar "Ask Zena" with `/__chat` endpoint and HOW_TO_USE.md system prompt
- `/__download-status` and `/__install` endpoints for model management
- BitNet / incompatible quantization formats (i2_s, i1, i2, i3) skipped at scan time

### Fixed
- Backend default port changed 8787 → 8123 (was silently refusing all UI requests)
- `_autoPickJudge()` used `size_mb` but backend returns `size_gb` — fixed unit math
- Judge option values were `local:N` indices; now use real file paths
- Judge scoring now fires with just `judge_model + local_models` (no longer requires
  `judge_system_prompt` to be non-empty — falls back to built-in scoring prompt)
- `__del__` traceback from llama_cpp on model unload suppressed

### Changed
- `Run_me.bat` simplified to single server on port 8123
- `requirements.txt` — dependencies pinned to exact installed versions
