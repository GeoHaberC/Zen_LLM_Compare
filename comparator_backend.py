"""
LLM Model Comparator Backend
=============================
Serves system info, scans local models, and handles comparisons.

Usage:
    python comparator_backend.py       → runs on port 8123
    python comparator_backend.py 9000  → runs on custom port

Endpoints:
    GET  /__system-info                → {cpu_count, memory_gb, model_count, has_llama_cpp, models: [...]}
    POST /__comparison/mixed           → {local_models, online_models, prompt, ...} → results
"""

import ipaddress
import json
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Any
from urllib.parse import parse_qs, urlparse

# Enable Vulkan GPU backend for llama-cpp-python (AMD Radeon / any Vulkan GPU)
# Must be set before llama_cpp is imported. Has no effect if Vulkan is absent.
# Supports multi-GPU: set GGML_VK_VISIBLE_DEVICES=0,1 for two GPUs.
_vk_devices = os.environ.get('GGML_VK_VISIBLE_DEVICES', '0')
os.environ['GGML_VK_VISIBLE_DEVICES'] = _vk_devices


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle each request in a separate thread so inference doesn't block the UI."""

    daemon_threads = True


# ─ System info detection ────────────────────────────────────────────────────
try:
    import psutil

    HAS_PSUTIL = True
    proc = psutil.Process()  # current process — used for RAM delta tracking
except ImportError:
    HAS_PSUTIL = False
    psutil = None
    proc = None


def get_cpu_count() -> int:
    """Get physical CPU core count."""
    try:
        return os.cpu_count() or 1
    except Exception:
        return 1


def get_memory_gb() -> float:
    """Get total RAM in GB."""
    if HAS_PSUTIL:
        try:
            return psutil.virtual_memory().total / (1024**3)  # type: ignore[union-attr]
        except Exception:
            pass
    return 8.0  # fallback


def get_cpu_info() -> dict:
    """Detect CPU brand, full model name, and SIMD capabilities."""
    import platform

    info = {
        "brand": "Unknown",
        "name": "",
        "cores": get_cpu_count(),
        "avx2": False,
        "avx512": False,
    }
    try:
        proc = platform.processor()
        if proc:
            info["name"] = proc
            up = proc.upper()
            if "AMD" in up:
                info["brand"] = "AMD"
            elif "INTEL" in up:
                info["brand"] = "Intel"
    except Exception:
        pass

    # Try PROCESSOR_IDENTIFIER env var (Windows, non-blocking)
    pid = os.environ.get("PROCESSOR_IDENTIFIER", "")
    if pid and info["brand"] == "Unknown":
        if "AMD" in pid.upper():
            info["brand"] = "AMD"
        elif "INTEL" in pid.upper():
            info["brand"] = "Intel"
    if pid and not info["name"]:
        info["name"] = pid

    # CPUID via cpuinfo (optional, fast)
    try:
        import cpuinfo as _ci

        d = _ci.get_cpu_info()
        info["name"] = d.get("brand_raw", info["name"])
        flags = d.get("flags", [])
        info["avx2"] = "avx2" in flags
        info["avx512"] = any(f.startswith("avx512") for f in flags)
        brand = info["name"].upper()
        if "AMD" in brand:
            info["brand"] = "AMD"
        elif "INTEL" in brand:
            info["brand"] = "Intel"
    except Exception:
        pass

    # Fallback AVX2 detection via ctypes on Windows
    if not info["avx2"]:
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            # IsProcessorFeaturePresent(PF_AVX2_INSTRUCTIONS_AVAILABLE = 40)
            info["avx2"] = bool(kernel32.IsProcessorFeaturePresent(40))
        except Exception:
            pass

    return info


def get_gpu_info() -> list[dict]:
    """Detect GPUs and CUDA/ROCm/DirectML support."""
    gpus = []

    # ── NVIDIA via pynvml ────────────────────────────────────────────────────
    try:
        import pynvml  # type: ignore[import-untyped]

        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        for i in range(count):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(h)
            if isinstance(name, bytes):
                name = name.decode()
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)
            gpus.append(
                {
                    "name": name,
                    "vendor": "NVIDIA",
                    "vram_gb": round(mem.total / (1024**3), 1),
                    "backend": "CUDA",
                }
            )
        pynvml.nvmlShutdown()
    except Exception:
        pass

    # ── AMD via pyamdgpuinfo or WMI fallback ────────────────────────────────
    if not gpus:
        try:
            import pyamdgpuinfo  # type: ignore[import-untyped]

            count = pyamdgpuinfo.detect_gpus()
            for i in range(count):
                g = pyamdgpuinfo.get_gpu(i)
                vram = getattr(g, "memory_info", {}).get("vram_size", 0)
                gpus.append(
                    {
                        "name": g.name if hasattr(g, "name") else "AMD GPU",
                        "vendor": "AMD",
                        "vram_gb": round(vram / (1024**3), 1) if vram else 0,
                        "backend": "ROCm/Vulkan",
                    }
                )
        except Exception:
            pass

    # ── Windows PowerShell WMI fallback (wmic is deprecated on Win 11) ──────
    if not gpus:
        try:
            import json as _json
            import subprocess

            ps_cmd = (
                "Get-CimInstance Win32_VideoController "
                "| Select-Object Name,AdapterRAM "
                "| ConvertTo-Json -Compress"
            )
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                timeout=10,
                universal_newlines=True,
            )
            raw = _json.loads(out.strip())
            # ConvertTo-Json returns a dict for one GPU, list for multiple
            entries = raw if isinstance(raw, list) else [raw]
            for entry in entries:
                name = (entry.get("Name") or "").strip()
                if not name or name.lower() in ("", "microsoft basic display adapter"):
                    continue
                vram_bytes = int(entry.get("AdapterRAM") or 0)
                up = name.upper()
                vendor = (
                    "NVIDIA"
                    if "NVIDIA" in up
                    else (
                        "AMD"
                        if "AMD" in up or "RADEON" in up
                        else ("Intel" if "INTEL" in up else "Unknown")
                    )
                )
                backend = (
                    "CUDA"
                    if vendor == "NVIDIA"
                    else ("ROCm/Vulkan" if vendor == "AMD" else "DirectML")
                )
                gpus.append(
                    {
                        "name": name,
                        "vendor": vendor,
                        "vram_gb": round(vram_bytes / (1024**3), 1),
                        "backend": backend,
                    }
                )
        except Exception:
            pass

    return gpus


def get_llama_cpp_info() -> dict:
    """Return llama.cpp version and recommended build for this hardware."""
    installed = False
    version = None  # None (not a truthy string) so frontend can check falsiness
    try:
        import llama_cpp

        installed = True
        version = getattr(llama_cpp, "__version__", "installed") or "installed"
    except Exception:
        pass

    return {"installed": installed, "version": version}


def recommend_llama_build(cpu: dict, gpus: list[dict]) -> dict:
    """Return the best llama.cpp build name and download URL for this machine."""
    nvidia = next((g for g in gpus if g["vendor"] == "NVIDIA"), None)
    amd = next((g for g in gpus if g["vendor"] == "AMD"), None)

    if nvidia:
        vram = nvidia["vram_gb"]
        return {
            "build": "CUDA (NVIDIA GPU)",
            "flag": "cuda",
            "reason": f"{nvidia['name']} {vram} GB VRAM → GPU acceleration via CUDA",
            "pip": "pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124",
            "note": "Fastest option — runs models entirely on GPU",
        }
    if amd:
        return {
            "build": "ROCm / Vulkan (AMD GPU)",
            "flag": "rocm",
            "reason": f"{amd['name']} → GPU acceleration via ROCm or Vulkan",
            "pip": "pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/rocm",
            "note": "Use ROCm for Linux; Vulkan backend works on Windows",
        }
    if cpu.get("avx512"):
        return {
            "build": "AVX-512 (CPU optimised)",
            "flag": "avx512",
            "reason": f"{cpu['name']} supports AVX-512 → fastest CPU inference",
            "pip": 'CMAKE_ARGS="-DLLAMA_AVX512=on" pip install llama-cpp-python',
            "note": "Best CPU performance on modern Intel/AMD processors with AVX-512",
        }
    if cpu.get("avx2"):
        return {
            "build": "AVX2 (CPU, recommended)",
            "flag": "avx2",
            "reason": f"{cpu['brand']} {cpu['cores']}-core CPU with AVX2 support",
            "pip": "pip install llama-cpp-python",
            "note": "Default pre-built wheel already uses AVX2 on Windows",
        }
    return {
        "build": "CPU Basic (no AVX2)",
        "flag": "cpu",
        "reason": "No AVX2 detected — falling back to basic CPU build",
        "pip": 'CMAKE_ARGS="-DLLAMA_AVX=on" pip install llama-cpp-python',
        "note": "Performance will be limited; consider upgrading hardware",
    }


def scan_models(model_dirs: list[str]) -> list[dict]:
    """Scan model directories for GGUF files."""
    # Quantization types that require a special llama.cpp build and will fail to load
    _INCOMPATIBLE_QUANT_SUFFIXES = ("i2_s", "i1", "i2", "i3")

    models = []
    seen = set()
    for d in model_dirs:
        if not os.path.isdir(d):
            continue
        try:
            for fname in os.listdir(d):
                if not fname.lower().endswith(".gguf"):
                    continue

                # Skip BitNet / exotic quant formats that llama-cpp-python can't load
                stem = fname.lower().replace(".gguf", "")
                if any(
                    stem.endswith(f"-{q}") or f"_{q}." in fname.lower()
                    for q in _INCOMPATIBLE_QUANT_SUFFIXES
                ):
                    print(f"[scan] SKIP incompatible quant: {fname}")
                    continue

                full_path = os.path.join(d, fname)
                try:
                    size_bytes = os.path.getsize(full_path)
                except OSError:
                    continue

                # Skip tiny/partial files
                if size_bytes < 50 * 1024 * 1024:
                    continue

                key = fname.lower()
                if key in seen:
                    continue
                seen.add(key)

                models.append(
                    {
                        "name": fname,
                        "path": full_path,
                        "size_gb": round(size_bytes / (1024**3), 2),
                    }
                )
        except Exception:
            pass

    models.sort(key=lambda m: m["name"].lower())
    return models


def get_system_info(model_dirs: list[str]) -> dict:
    """Return comprehensive system info."""
    cpu = get_cpu_info()
    memory_gb = get_memory_gb()
    gpus = get_gpu_info()
    llama = get_llama_cpp_info()
    rec = recommend_llama_build(cpu, gpus)
    models = scan_models(model_dirs)

    return {
        # Legacy fields (keep for backward compat)
        "cpu_brand": cpu["brand"],
        "cpu_count": cpu["cores"],
        # Extended fields
        "cpu_name": cpu["name"],
        "cpu_avx2": cpu["avx2"],
        "cpu_avx512": cpu["avx512"],
        "memory_gb": round(memory_gb, 1),
        "gpus": gpus,
        "has_llama_cpp": llama["installed"],
        "llama_cpp_version": llama["version"],
        "recommended_build": rec,
        "model_count": len(models),
        "models": models,
        "timestamp": time.time(),
    }


# ─ Token counting (actual tokenizer) ─────────────────────────────────────────

# Shared lightweight tokenizer (loaded once, no model weights needed).
# Falls back to a reasonable heuristic when llama_cpp is unavailable.
_shared_tokenizer = None
_tokenizer_lock = threading.Lock()


def _get_tokenizer():
    """Return a tokenizer callable(text→list[int]).  Thread-safe, lazy-loaded."""
    global _shared_tokenizer
    if _shared_tokenizer is not None:
        return _shared_tokenizer

    with _tokenizer_lock:
        if _shared_tokenizer is not None:
            return _shared_tokenizer

        # Prefer tiktoken (fast, pure-Python, no model file needed)
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            _shared_tokenizer = enc.encode
            return _shared_tokenizer
        except Exception:
            pass

        # Fallback: regex-based approximation (≈1.3 tokens per word)
        _tok_re = re.compile(r"""'s|'t|'re|'ve|'m|'ll|'d| ?\w+| ?\d+| ?[^\s\w]+|\s+""")

        def _regex_tokenize(text: str) -> list:
            return _tok_re.findall(text)

        _shared_tokenizer = _regex_tokenize
        return _shared_tokenizer


def count_tokens(text: str, model_path: str | None = None) -> int:
    """Count tokens in *text* using the best available tokenizer.

    Uses tiktoken or a regex approximation — never loads a model file
    (too slow for inline use).
    """
    if not text:
        return 0
    tokenizer = _get_tokenizer()
    return len(tokenizer(text))


# ─ Judge score extraction (robust, multi-fallback) ────────────────────────────

def extract_judge_scores(raw_text: str) -> dict:
    """Extract evaluation scores from judge LLM output.

    Handles:
      1. Clean JSON
      2. JSON in markdown fences
      3. Nested JSON ({"evaluation": {...}})
      4. Partial / malformed JSON
      5. Natural-language scores ("overall: 8/10")
      6. Total garbage → {"overall": 0}

    Returns a dict always containing at least the key ``overall`` (0-10).
    """
    if not raw_text or not raw_text.strip():
        return {"overall": 0}

    raw = raw_text.strip()

    # ── Step 1: try markdown fences first ────────────────────────────────────
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    json_str = fence_match.group(1) if fence_match else raw

    # ── Step 2: try strict JSON parse ────────────────────────────────────────
    parsed = _try_json(json_str)

    # ── Step 3: find first { ... } in the raw text ──────────────────────────
    if parsed is None:
        brace_match = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
        if brace_match:
            parsed = _try_json(brace_match.group(0))

    # ── Step 4: handle nested JSON ───────────────────────────────────────────
    if parsed is not None:
        if "overall" not in parsed:
            # Check for nesting: {"evaluation": {"overall": 8, ...}}
            for v in parsed.values():
                if isinstance(v, dict) and "overall" in v:
                    parsed = v
                    break

    # ── Step 5: regex fallback from natural language ─────────────────────────
    if parsed is None:
        parsed = _extract_scores_regex(raw)

    # ── Step 6: normalise and clamp ──────────────────────────────────────────
    result = _normalise_scores(parsed or {})
    return result


def _try_json(text: str) -> dict | None:
    """Try to json.loads *text*, return dict or None."""
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass
    # Try fixing common issues: unquoted keys
    try:
        fixed = re.sub(r'(?<={|,)\s*(\w+)\s*:', r' "\1":', text)
        obj = json.loads(fixed)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return None


def _extract_scores_regex(text: str) -> dict:
    """Extract scores from natural-language judge output."""
    result: dict = {}
    lower = text.lower()

    # Match patterns: "overall score: 8", "overall: 8/10", "overall 8 out of 10"
    patterns = [
        (r"overall[\s:]+(\d+(?:\.\d+)?)\s*(?:/\s*10|out\s+of\s+10)?", "overall"),
        (r"accuracy[\s:]+(\d+(?:\.\d+)?)\s*(?:/\s*10)?", "accuracy"),
        (r"reasoning[\s:]+(\d+(?:\.\d+)?)\s*(?:/\s*10)?", "reasoning"),
    ]
    for pattern, key in patterns:
        m = re.search(pattern, lower)
        if m:
            result[key] = float(m.group(1))

    # If no overall but we found other scores, average them
    if "overall" not in result and result:
        nums = [v for v in result.values() if isinstance(v, (int, float))]
        if nums:
            result["overall"] = round(sum(nums) / len(nums), 1)

    # Absolute fallback: any standalone number 0-10 near "score"
    if "overall" not in result:
        m = re.search(r"score[:\s]*(\d+(?:\.\d+)?)", lower)
        if m:
            result["overall"] = float(m.group(1))

    if "overall" not in result:
        result["overall"] = 0

    return result


def _normalise_scores(d: dict) -> dict:
    """Ensure 'overall' exists, parse string scores, clamp to 0-10."""
    result: dict = {}
    for k, v in d.items():
        if isinstance(v, str):
            # Handle "8/10" format
            m = re.match(r"(\d+(?:\.\d+)?)\s*/\s*\d+", v)
            if m:
                v = float(m.group(1))
            else:
                try:
                    v = float(v)
                except (ValueError, TypeError):
                    result[k] = v
                    continue
        if isinstance(v, (int, float)):
            v = max(0.0, min(10.0, float(v)))
        result[k] = v

    if "overall" not in result:
        # Try to compute from other numeric scores
        nums = [v for v in result.values() if isinstance(v, (int, float))]
        result["overall"] = round(sum(nums) / len(nums), 1) if nums else 0

    return result


# ─ URL validation (SSRF prevention) ──────────────────────────────────────────

# Allowed HTTPS hosts for model downloads
_ALLOWED_DOWNLOAD_HOSTS = {
    "huggingface.co",
    "cdn-lfs.huggingface.co",
    "cdn-lfs-us-1.huggingface.co",
    "github.com",
    "objects.githubusercontent.com",
    "releases.githubusercontent.com",
    "gitlab.com",
    "ollama.com",
}


def validate_download_url(url: str) -> bool:
    """Validate a download URL for safety (prevent SSRF).

    Returns True only if the URL:
      - Uses HTTPS scheme
      - Targets an allowed host
      - Does not resolve to a private/loopback IP
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    # Only HTTPS allowed
    if parsed.scheme not in ("https",):
        return False

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False

    # Block loopback and private IPs
    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_reserved:
            return False
    except ValueError:
        # Not an IP literal — that's fine, check hostname
        pass

    # Block localhost names
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]"):
        return False

    # Check against allowed hosts
    if hostname not in _ALLOWED_DOWNLOAD_HOSTS:
        return False

    return True


# ─ HF Model Discovery cache ──────────────────────────────────────────────────
_discovery_cache: dict[str, dict] = {}  # cache_key → {ts, data}
_discovery_lock = threading.Lock()
_DISCOVERY_TTL = 900  # 15 minutes

_TRUSTED_QUANTIZERS = {
    "bartowski", "mradermacher", "unsloth", "TheBloke",
    "QuantFactory", "MaziyarPanahi", "lmstudio-community",
}


def _discover_hf_models(query: str = "", sort: str = "trending",
                        limit: int = 30) -> list[dict]:
    """Search HuggingFace for GGUF models. Uses huggingface_hub API."""
    cache_key = f"{query}|{sort}|{limit}"
    with _discovery_lock:
        cached = _discovery_cache.get(cache_key)
        if cached and time.time() - cached["ts"] < _DISCOVERY_TTL:
            return cached["data"]

    try:
        from huggingface_hub import HfApi
        api = HfApi()

        kwargs: dict[str, Any] = {
            "limit": min(limit, 60),
            "filter": "gguf",
        }
        if sort == "trending":
            kwargs["sort"] = "trending"
        elif sort == "downloads":
            kwargs["sort"] = "downloads"
        elif sort == "newest":
            kwargs["sort"] = "lastModified"
            kwargs["direction"] = -1
        elif sort == "likes":
            kwargs["sort"] = "likes"

        if query.strip():
            kwargs["search"] = query.strip()

        raw = list(api.list_models(**kwargs))
        results = []
        for m in raw:
            author = (m.id or "").split("/")[0] if "/" in (m.id or "") else ""
            results.append({
                "id": m.id,
                "author": author,
                "trusted": author in _TRUSTED_QUANTIZERS,
                "downloads": getattr(m, "downloads", 0) or 0,
                "likes": getattr(m, "likes", 0) or 0,
                "lastModified": str(getattr(m, "last_modified", "") or ""),
                "tags": list(getattr(m, "tags", []) or []),
                "pipeline": getattr(m, "pipeline_tag", "") or "",
            })

        with _discovery_lock:
            _discovery_cache[cache_key] = {"ts": time.time(), "data": results}
        return results
    except Exception as exc:
        return [{"error": str(exc)}]


# ─ Download job tracking ─────────────────────────────────────────────────────
_download_jobs: dict[str, dict] = {}  # job_id → {state, progress, path, error}
_download_lock = threading.Lock()
# ─ Install job tracking ─────────────────────────────────────────────
_install_jobs: dict[str, dict] = {}  # job_id → {state, log, error, status_text}
_install_lock = threading.Lock()


# ─ Input limits & defaults ────────────────────────────────────────────────────
MAX_PROMPT_TOKENS = 8192  # reject comparison prompts larger than this
DEFAULT_INFERENCE_TIMEOUT = 300  # seconds; overridable per-request
MAX_INFERENCE_TIMEOUT = 1800     # hard ceiling (30 min for reasoning models)


# ─ Rate limiting ──────────────────────────────────────────────────────────────

class _RateLimiter:
    """Simple per-IP sliding-window rate limiter.  Thread-safe."""

    def __init__(self, max_requests: int = 30, window_sec: float = 60.0):
        self._max = max_requests
        self._window = window_sec
        self._lock = threading.Lock()
        self._hits: dict[str, list[float]] = {}  # ip → [timestamps]

    def allow(self, ip: str) -> bool:
        now = time.time()
        cutoff = now - self._window
        with self._lock:
            stamps = self._hits.get(ip, [])
            stamps = [t for t in stamps if t > cutoff]
            if len(stamps) >= self._max:
                self._hits[ip] = stamps
                return False
            stamps.append(now)
            self._hits[ip] = stamps
            return True

    def remaining(self, ip: str) -> int:
        now = time.time()
        cutoff = now - self._window
        with self._lock:
            stamps = [t for t in self._hits.get(ip, []) if t > cutoff]
            return max(0, self._max - len(stamps))


# Global rate limiter: 30 requests/min for heavy endpoints
_rate_limiter = _RateLimiter(max_requests=30, window_sec=60.0)


def _is_safe_model_path(path: str, model_dirs: list[str]) -> bool:
    """Check that *path* is a .gguf file inside one of *model_dirs*.

    Prevents path-traversal attacks (e.g. loading /etc/passwd via the API).
    """
    if not path or not path.lower().endswith(".gguf"):
        return False
    try:
        real = os.path.realpath(path)
    except (OSError, ValueError):
        return False
    for d in model_dirs:
        try:
            if real.startswith(os.path.realpath(d) + os.sep):
                return True
        except (OSError, ValueError):
            continue
    return False


# ─ Model Comparator Handler ─────────────────────────────────────────────────
class ComparatorHandler(BaseHTTPRequestHandler):
    """HTTP request handler for model comparator endpoints."""

    model_dirs = ["C:\\AI\\Models", "C:\\Users\\Public\\AI\\Models"]

    # ── CORS preflight ────────────────────────────────────────────────────────
    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/__system-info":
            self._handle_system_info()
        elif self.path == "/__health":
            self._send_json(200, {"ok": True, "ts": time.time()})
        elif self.path == "/__config":
            self._send_json(200, {
                "vk_devices": os.environ.get("GGML_VK_VISIBLE_DEVICES", "0"),
                "default_inference_timeout": DEFAULT_INFERENCE_TIMEOUT,
                "max_inference_timeout": MAX_INFERENCE_TIMEOUT,
                "max_prompt_tokens": MAX_PROMPT_TOKENS,
                "rate_limit": {"max_requests": _rate_limiter._max, "window_sec": _rate_limiter._window},
            })
        elif self.path.startswith("/__discover-models"):
            self._handle_discover_models()
        elif self.path.startswith("/__download-status"):
            self._handle_download_status()
        elif self.path.startswith("/__install-status"):
            self._handle_install_status()
        elif self.path in ("/", "/model_comparator.html", "/index.html"):
            # Serve the main HTML app directly from the backend
            html_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "model_comparator.html"
            )
            try:
                with open(html_path, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self._cors_headers()
                self.end_headers()
                self.wfile.write(body)
            except FileNotFoundError:
                self._send_json(404, {"error": "model_comparator.html not found"})
        else:
            # Serve static assets (images, icons) from the same directory
            _STATIC_TYPES = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".ico": "image/x-icon",
                ".svg": "image/svg+xml",
                ".webp": "image/webp",
            }
            _ext = os.path.splitext(self.path.split("?")[0])[1].lower()
            if _ext in _STATIC_TYPES:
                _static_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    os.path.basename(self.path.split("?")[0]),
                )
                try:
                    with open(_static_path, "rb") as f:
                        body = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", _STATIC_TYPES[_ext])
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self._cors_headers()
                    self.end_headers()
                    self.wfile.write(body)
                except FileNotFoundError:
                    self._send_json(404, {"error": "Static asset not found"})
            else:
                self._send_json(404, {"error": "Not found"})

    def _client_ip(self) -> str:
        return self.client_address[0] if self.client_address else "unknown"

    def do_POST(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body) if body else {}
        except Exception:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        # Rate-limit heavy POST endpoints
        if self.path in ("/__comparison/mixed", "/__comparison/stream", "/__chat"):
            if not _rate_limiter.allow(self._client_ip()):
                remaining = _rate_limiter.remaining(self._client_ip())
                self._send_json(429, {
                    "error": "Too many requests. Please wait a moment.",
                    "retry_after": 60,
                    "remaining": remaining,
                })
                return

        if self.path == "/__comparison/mixed":
            self._handle_comparison(data)
        elif self.path == "/__comparison/stream":
            self._handle_stream_comparison(data)
        elif self.path == "/__download-model":
            self._handle_download(data)
        elif self.path == "/__install-llama":
            self._handle_install_llama(data)
        elif self.path == "/__chat":
            self._handle_chat(data)
        else:
            self._send_json(404, {"error": "Not found"})

    # ── Handlers ─────────────────────────────────────────────────────────────
    def _handle_system_info(self) -> None:
        try:
            info = get_system_info(self.model_dirs)
            self._send_json(200, info)
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _handle_install_status(self) -> None:
        """GET /__install-status?job=<id>"""
        from urllib.parse import parse_qs, urlparse

        qs = parse_qs(urlparse(self.path).query)
        job_id = qs.get("job", [""])[0]
        with _install_lock:
            job = dict(_install_jobs.get(job_id) or {"state": "unknown"})
        self._send_json(200, job)

    def _handle_install_llama(self, data: dict) -> None:
        """POST /__install-llama — run pip install in background, stream log."""
        import uuid

        pip_cmd = data.get("pip", "pip install llama-cpp-python").strip()
        # Security: only allow llama-cpp-python installation
        if not pip_cmd.startswith("pip install llama-cpp-python"):
            self._send_json(
                400,
                {"ok": False, "error": "Only llama-cpp-python installation allowed"},
            )
            return
        job_id = str(uuid.uuid4())[:8]
        with _install_lock:
            _install_jobs[job_id] = {
                "state": "starting",
                "log": "",
                "error": "",
                "status_text": "Starting…",
            }
        t = threading.Thread(target=_run_install, args=(job_id, pip_cmd), daemon=True)
        t.start()
        self._send_json(200, {"ok": True, "job_id": job_id})

    def _handle_download_status(self) -> None:
        """GET /__download-status?job=<id>"""
        from urllib.parse import parse_qs, urlparse

        qs = parse_qs(urlparse(self.path).query)
        job_id = qs.get("job", [""])[0]
        with _download_lock:
            job = _download_jobs.get(job_id) or {"state": "unknown"}
        self._send_json(200, job)

    def _handle_download(self, data: dict) -> None:
        """POST /__download-model — fire a background download, return job_id immediately."""
        import uuid

        model = data.get("model", "").strip()
        dest = data.get("dest", "C:\\AI\\Models")

        if not model:
            self._send_json(400, {"ok": False, "error": "model is required"})
            return

        job_id = str(uuid.uuid4())[:8]
        with _download_lock:
            _download_jobs[job_id] = {
                "state": "starting",
                "progress": 0,
                "path": "",
                "error": "",
            }

        # Start the real work in a background thread so this request returns instantly
        t = threading.Thread(target=_run_download, args=(job_id, model, dest), daemon=True)
        t.start()

        self._send_json(200, {"ok": True, "job_id": job_id})

    def _handle_comparison(self, data: dict) -> None:
        try:
            prompt = data.get("prompt", "")
            local_models = data.get("local_models", [])
            online_models = data.get("online_models", [])
            judge_model = data.get("judge_model")
            judge_system_prompt = data.get("judge_system_prompt", "")
            system_prompt = data.get("system_prompt", "You are a helpful assistant.")

            # ── Input validation ──────────────────────────────────────────
            # Reject oversized prompts (DoS prevention)
            if count_tokens(prompt) > MAX_PROMPT_TOKENS:
                self._send_json(400, {
                    "error": f"Prompt too large (>{MAX_PROMPT_TOKENS} tokens). Please shorten it."
                })
                return

            # Validate all model paths are inside configured model_dirs
            safe_models = [
                p for p in local_models
                if _is_safe_model_path(p, self.model_dirs)
            ]
            if len(safe_models) != len(local_models):
                rejected = len(local_models) - len(safe_models)
                print(f"[compare] WARN rejected {rejected} model path(s) outside model_dirs")

            # Clamp inference timeout to safe range
            req_timeout = min(
                max(10, int(data.get("inference_timeout", DEFAULT_INFERENCE_TIMEOUT))),
                MAX_INFERENCE_TIMEOUT,
            )
            params = {
                "n_ctx": int(data.get("n_ctx", 4096)),
                "max_tokens": int(data.get("max_tokens", 512)),
                "temperature": float(data.get("temperature", 0.7)),
                "top_p": float(data.get("top_p", 0.95)),
                "repeat_penalty": float(data.get("repeat_penalty", 1.1)),
                "inference_timeout": req_timeout,
            }
            responses = self._run_local_comparisons(prompt, system_prompt, safe_models, params)

            # ── Apply judge scoring if a judge model was selected ──────────
            if judge_model and local_models:
                judge_path = self._resolve_judge_path(judge_model, local_models)
                if judge_path:
                    # Fall back to a minimal scoring prompt if none provided
                    if not judge_system_prompt:
                        judge_system_prompt = (
                            "You are an expert evaluator. Score the model response and output "
                            "ONLY valid JSON with keys: overall (0-10), accuracy (0-10), "
                            'reasoning (0-10), instruction_following (true/false), safety ("safe"/"unsafe").'
                        )
                    responses = self._run_judge(
                        responses, prompt, judge_path, judge_system_prompt, params
                    )

            results = {
                "prompt": prompt,
                "models_tested": len(local_models) + len(online_models),
                "responses": responses,
                "judge_model": judge_model,
                "timestamp": time.time(),
            }
            self._send_json(200, results)
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _handle_stream_comparison(self, data: dict) -> None:
        """SSE endpoint: streams per-model tokens and results as they generate."""
        try:
            prompt = data.get("prompt", "")
            local_models = data.get("local_models", [])
            judge_model = data.get("judge_model")
            judge_system_prompt = data.get("judge_system_prompt", "")
            system_prompt = data.get("system_prompt", "You are a helpful assistant.")

            if count_tokens(prompt) > MAX_PROMPT_TOKENS:
                self._send_json(400, {
                    "error": f"Prompt too large (>{MAX_PROMPT_TOKENS} tokens)."
                })
                return

            safe_models = [
                p for p in local_models
                if _is_safe_model_path(p, self.model_dirs)
            ]

            req_timeout = min(
                max(10, int(data.get("inference_timeout", DEFAULT_INFERENCE_TIMEOUT))),
                MAX_INFERENCE_TIMEOUT,
            )
            params = {
                "n_ctx": int(data.get("n_ctx", 4096)),
                "max_tokens": int(data.get("max_tokens", 512)),
                "temperature": float(data.get("temperature", 0.7)),
                "top_p": float(data.get("top_p", 0.95)),
                "repeat_penalty": float(data.get("repeat_penalty", 1.1)),
                "inference_timeout": req_timeout,
            }

            # Send SSE headers
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self._cors_headers()
            self.end_headers()

            def _sse(event: str, payload: dict) -> None:
                line = f"event: {event}\ndata: {json.dumps(payload)}\n\n"
                self.wfile.write(line.encode("utf-8"))
                self.wfile.flush()

            # Stream model inference one-by-one
            try:
                import llama_cpp
            except ImportError:
                _sse("error", {"error": "llama-cpp-python not installed"})
                _sse("done", {})
                return

            import gc

            responses: list[dict] = []
            n_ctx = params["n_ctx"]
            max_tokens = params["max_tokens"]
            temperature = params["temperature"]
            top_p = params["top_p"]
            repeat_penalty = params["repeat_penalty"]
            inference_timeout = params["inference_timeout"]

            for model_idx, path in enumerate(safe_models):
                model_name = os.path.basename(path).replace(".gguf", "")
                _sse("model_start", {
                    "model": model_name,
                    "model_index": model_idx,
                    "total_models": len(safe_models),
                })

                t0 = time.time()
                llm = None
                ram_before = (
                    (proc.memory_info().rss // (1024 * 1024))
                    if (HAS_PSUTIL and proc is not None)
                    else 0
                )
                try:
                    llm = llama_cpp.Llama(
                        model_path=path,
                        n_ctx=n_ctx,
                        n_threads=os.cpu_count() or 4,
                        n_gpu_layers=-1,
                        verbose=False,
                    )
                    ttft_ms = 0.0
                    chunks: list[str] = []
                    token_count = 0
                    for chunk in llm.create_chat_completion(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=max_tokens,
                        temperature=temperature,
                        top_p=top_p,
                        repeat_penalty=repeat_penalty,
                        stream=True,
                    ):
                        delta = chunk["choices"][0].get("delta", {}).get("content", "")
                        if delta:
                            if not ttft_ms:
                                ttft_ms = (time.time() - t0) * 1000
                            chunks.append(delta)
                            token_count += 1
                            # Stream every token to client
                            _sse("token", {
                                "model": model_name,
                                "model_index": model_idx,
                                "token": delta,
                                "token_count": token_count,
                                "elapsed_ms": round((time.time() - t0) * 1000),
                            })
                        if (time.time() - t0) > inference_timeout:
                            chunks.append("\n\n[⏱ Inference timed out]")
                            break

                    elapsed_ms = (time.time() - t0) * 1000
                    response_text = "".join(chunks)
                    completion_tokens = max(1, count_tokens(response_text))
                    tps = completion_tokens / (elapsed_ms / 1000) if elapsed_ms > 0 else 0
                    ram_after = (
                        (proc.memory_info().rss // (1024 * 1024))
                        if (HAS_PSUTIL and proc is not None)
                        else 0
                    )
                    ram_delta = max(0, ram_after - ram_before)

                    result = {
                        "model": model_name,
                        "model_path": path,
                        "path": path,
                        "response": response_text,
                        "time_ms": round(elapsed_ms, 1),
                        "tokens": completion_tokens,
                        "tokens_per_sec": round(tps, 1),
                        "quality_score": 0,
                        "ttft_ms": round(ttft_ms, 1),
                        "ram_delta_mb": ram_delta,
                    }
                    responses.append(result)
                    _sse("model_done", result)
                except Exception as exc:
                    elapsed_ms = (time.time() - t0) * 1000
                    result = {
                        "model": model_name,
                        "model_path": path,
                        "path": path,
                        "response": f"❌ Error: {exc}",
                        "error": str(exc),
                        "time_ms": round(elapsed_ms, 1),
                        "tokens": 0,
                        "tokens_per_sec": 0,
                        "quality_score": 0,
                        "ttft_ms": 0,
                        "ram_delta_mb": 0,
                    }
                    responses.append(result)
                    _sse("model_done", result)
                finally:
                    try:
                        del llm
                    except Exception:
                        pass
                    gc.collect()

            # Judge scoring
            if judge_model and local_models:
                _sse("judge_start", {"judge_model": judge_model})
                judge_path = self._resolve_judge_path(judge_model, local_models)
                if judge_path:
                    if not judge_system_prompt:
                        judge_system_prompt = (
                            "You are an expert evaluator. Score the model response and output "
                            "ONLY valid JSON with keys: overall (0-10), accuracy (0-10), "
                            'reasoning (0-10), instruction_following (true/false), safety ("safe"/"unsafe").'
                        )
                    responses = self._run_judge(
                        responses, prompt, judge_path, judge_system_prompt, params
                    )
                _sse("judge_done", {"responses": responses})

            # Final done event
            _sse("done", {
                "prompt": prompt,
                "models_tested": len(safe_models),
                "responses": responses,
                "judge_model": judge_model,
                "timestamp": time.time(),
            })
        except Exception as e:
            try:
                line = f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                self.wfile.write(line.encode("utf-8"))
                self.wfile.flush()
            except Exception:
                pass

    def _run_local_comparisons(
        self,
        prompt: str,
        system_prompt: str,
        model_paths: list[str],
        params: dict | None = None,
    ) -> list[dict]:
        """Run prompt through each local GGUF model via llama-cpp-python."""
        params = params or {}
        n_ctx = params.get("n_ctx", 4096)
        max_tokens = params.get("max_tokens", 512)
        temperature = params.get("temperature", 0.7)
        top_p = params.get("top_p", 0.95)
        repeat_penalty = params.get("repeat_penalty", 1.1)
        inference_timeout = params.get("inference_timeout", DEFAULT_INFERENCE_TIMEOUT)

        try:
            import llama_cpp
        except ImportError:
            return [
                {
                    "model": os.path.basename(p).replace(".gguf", ""),
                    "model_path": p,
                    "path": p,
                    "response": "⚠️ llama-cpp-python not installed. Click Install in the sidebar.",
                    "error": "llama_cpp not installed",
                    "time_ms": 0,
                    "tokens": 0,
                    "tokens_per_sec": 0,
                    "quality_score": 0,
                    "ttft_ms": 0,
                    "ram_delta_mb": 0,
                }
                for p in model_paths
            ]

        import gc

        results = []
        for path in model_paths:
            model_name = os.path.basename(path).replace(".gguf", "")
            print(
                f"[compare] ▶ {model_name}  ctx={n_ctx}  max_tokens={max_tokens}  temp={temperature}"
            )
            t0 = time.time()
            llm = None
            ram_before = (
                (proc.memory_info().rss // (1024 * 1024))
                if (HAS_PSUTIL and proc is not None)
                else 0  # type: ignore[union-attr]
            )
            try:
                llm = llama_cpp.Llama(
                    model_path=path,
                    n_ctx=n_ctx,
                    n_threads=os.cpu_count() or 4,
                    n_gpu_layers=-1,  # use GPU layers if available, else 0
                    verbose=False,
                )
                # ── Streaming to capture TTFT ─────────────────────────────
                ttft_ms = 0.0
                chunks: list[str] = []
                for chunk in llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    repeat_penalty=repeat_penalty,
                    stream=True,
                ):
                    delta = chunk["choices"][0].get("delta", {}).get("content", "")  # type: ignore[index]
                    if delta:
                        if not ttft_ms:
                            ttft_ms = (time.time() - t0) * 1000
                        chunks.append(delta)
                    # Enforce per-model inference timeout
                    if (time.time() - t0) > inference_timeout:
                        chunks.append("\n\n[⏱ Inference timed out]")
                        break

                elapsed_ms = (time.time() - t0) * 1000
                response_text = "".join(chunks)
                # Use actual tokenizer for accurate token count
                completion_tokens = max(1, count_tokens(response_text))
                tps = completion_tokens / (elapsed_ms / 1000) if elapsed_ms > 0 else 0

                ram_after = (
                    (proc.memory_info().rss // (1024 * 1024))
                    if (HAS_PSUTIL and proc is not None)
                    else 0  # type: ignore[union-attr]
                )
                ram_delta = max(0, ram_after - ram_before)

                print(
                    f"[compare] ✅ {model_name}  {elapsed_ms:.0f}ms  ttft={ttft_ms:.0f}ms  {completion_tokens}tok  {tps:.1f}t/s  ram+{ram_delta}MB"
                )
                results.append(
                    {
                        "model": model_name,
                        "model_path": path,
                        "path": path,
                        "response": response_text,
                        "time_ms": round(elapsed_ms, 1),
                        "tokens": completion_tokens,
                        "tokens_per_sec": round(tps, 1),
                        "quality_score": 0,
                        "ttft_ms": round(ttft_ms, 1),
                        "ram_delta_mb": ram_delta,
                    }
                )
            except Exception as exc:
                elapsed_ms = (time.time() - t0) * 1000
                print(f"[compare] ERROR {model_name}: {exc}")
                results.append(
                    {
                        "model": model_name,
                        "model_path": path,
                        "path": path,
                        "response": f"❌ Error loading/running model: {exc}",
                        "error": str(exc),
                        "time_ms": round(elapsed_ms, 1),
                        "tokens": 0,
                        "tokens_per_sec": 0,
                        "quality_score": 0,
                        "ttft_ms": 0,
                        "ram_delta_mb": 0,
                    }
                )
            finally:
                try:
                    del llm
                except Exception:
                    pass
                gc.collect()  # free model memory before loading next one
        return results

    def _resolve_judge_path(self, judge_model: str, local_models: list[str]) -> str | None:
        """Return the filesystem path to use as judge model."""
        if judge_model == "local:best":
            # Pick largest model file available (heuristic: bigger = smarter)
            best = max(
                local_models,
                key=lambda p: os.path.getsize(p) if os.path.exists(p) else 0,
                default=None,
            )
            return best
        if judge_model and not judge_model.startswith("online:"):
            # Could be an explicit path passed through
            if os.path.exists(judge_model):
                return judge_model
            # Try to match by basename against local_models
            for p in local_models:
                if os.path.basename(p).lower().startswith(judge_model.lower()):
                    return p
        return None

    def _run_judge(
        self,
        responses: list[dict],
        original_prompt: str,
        judge_path: str,
        judge_system_prompt: str,
        params: dict,
    ) -> list[dict]:
        """Score each response using the judge model; adds judge_score + judge_detail.

        Position-bias mitigation: evaluates each response twice — once in
        original order, once with a randomised prompt preamble — then averages
        the two scores.  This counters the well-documented position bias where
        LLM judges favour the first response they see (Zheng et al., NeurIPS 2023).
        """
        try:
            import llama_cpp
        except ImportError:
            return responses

        import gc
        import random

        judge_name = os.path.basename(judge_path).replace(".gguf", "")
        print(f"[judge] Loading {judge_name}…")
        llm = None
        try:
            llm = llama_cpp.Llama(
                model_path=judge_path,
                n_ctx=min(params.get("n_ctx", 4096), 8192),
                n_threads=os.cpu_count() or 4,
                n_gpu_layers=-1,
                verbose=False,
            )

            # Build randomised context preambles per response to mitigate
            # position bias.  Each response gets two evaluations: one with a
            # neutral preamble, one with a shuffled-order summary of *other*
            # responses so the judge sees different ordinal positions.
            other_previews: list[str] = []
            for r in responses:
                if not r.get("error"):
                    preview = (r.get("response") or "")[:200]
                    other_previews.append(preview)

            for idx, r in enumerate(responses):
                if r.get("error"):
                    continue

                scores_collected: list[float] = []
                details_collected: list[dict] = []

                # --- Pass 1: standard (original order) ---
                user_msg_standard = (
                    f"Original question: {original_prompt}\n\n"
                    f"Model response:\n{r.get('response', '')}"
                )
                # --- Pass 2: randomised preamble ---
                others = [p for j, p in enumerate(other_previews) if j != idx]
                random.shuffle(others)
                context_block = ""
                if others:
                    snippets = "\n".join(
                        f"  [Other response {i+1}]: {s}…"
                        for i, s in enumerate(others[:3])
                    )
                    context_block = (
                        f"(For context, {len(others)} other model(s) also answered "
                        f"this question. Brief previews in random order:\n{snippets})\n\n"
                    )
                user_msg_shuffled = (
                    f"Original question: {original_prompt}\n\n"
                    f"{context_block}"
                    f"Model response to evaluate:\n{r.get('response', '')}"
                )

                for pass_idx, user_msg in enumerate(
                    [user_msg_standard, user_msg_shuffled]
                ):
                    for attempt in range(2):  # retry once on failure
                        try:
                            sys_prompt = (
                                judge_system_prompt
                                if attempt == 0
                                else (
                                    "Rate the response quality 0-10. Output ONLY a JSON "
                                    'object: {"overall": <number>}'
                                )
                            )
                            out = llm.create_chat_completion(
                                messages=[
                                    {"role": "system", "content": sys_prompt},
                                    {"role": "user", "content": user_msg},
                                ],
                                max_tokens=512,
                                temperature=0.1,
                                stream=False,
                            )
                            raw = out["choices"][0]["message"]["content"].strip()  # type: ignore[index]
                            jd = extract_judge_scores(raw)
                            score = float(jd.get("overall", 0))
                            scores_collected.append(score)
                            details_collected.append(jd)
                            break
                        except Exception as je:
                            print(
                                f"[judge] WARN pass {pass_idx+1} attempt {attempt+1} "
                                f"failed for {r['model']}: {je}"
                            )

                if scores_collected:
                    avg_score = sum(scores_collected) / len(scores_collected)
                    # Use the detail dict from the first successful pass,
                    # but override overall with the averaged score.
                    best_detail = details_collected[0].copy()
                    best_detail["overall"] = round(avg_score, 1)
                    best_detail["bias_passes"] = len(scores_collected)
                    best_detail["individual_scores"] = [
                        round(s, 1) for s in scores_collected
                    ]
                    r["judge_score"] = round(avg_score, 1)
                    r["quality_score"] = round(avg_score, 1)
                    r["judge_detail"] = best_detail
                    print(
                        f"[judge] OK {r['model']}  avg={avg_score:.1f} "
                        f"passes={scores_collected}"
                    )
                else:
                    r["judge_score"] = 0
                    r["quality_score"] = 0
                    r["judge_detail"] = {
                        "overall": 0,
                        "error": "Judge failed after retries",
                    }
        finally:
            del llm
            gc.collect()
        return responses

    def _handle_chat(self, data: dict) -> None:
        model_path = data.get("model_path", "").strip()
        if not model_path or not os.path.isfile(model_path):
            self._send_json(400, {"error": "Model file not found"})
            return
        # Validate path is inside configured model directories
        if not _is_safe_model_path(model_path, self.model_dirs):
            self._send_json(403, {"error": "Model path not allowed"})
            return
        system = data.get("system", "You are a helpful assistant.")
        messages = data.get("messages", [])
        max_tokens = min(int(data.get("max_tokens", 512)), 2048)
        temperature = float(data.get("temperature", 0.4))
        try:
            import gc

            import llama_cpp

            llm = llama_cpp.Llama(
                model_path=model_path,
                n_ctx=4096,
                n_threads=os.cpu_count() or 4,
                n_gpu_layers=-1,
                verbose=False,
            )
            full_messages = [{"role": "system", "content": system}] + messages
            out = llm.create_chat_completion(
                full_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False,
            )
            reply = out["choices"][0]["message"]["content"]  # type: ignore[index]
            del llm
            gc.collect()
            self._send_json(200, {"response": reply})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _handle_discover_models(self) -> None:
        """GET /__discover-models?q=&sort=trending&limit=30"""
        qs = parse_qs(urlparse(self.path).query)
        query = qs.get("q", [""])[0][:200]  # cap query length
        sort = qs.get("sort", ["trending"])[0]
        if sort not in ("trending", "downloads", "newest", "likes"):
            sort = "trending"
        try:
            limit = min(int(qs.get("limit", ["30"])[0]), 60)
        except (ValueError, TypeError):
            limit = 30
        results = _discover_hf_models(query, sort, limit)
        self._send_json(200, {"models": results, "cached": bool(_discovery_cache)})

    def _cors_headers(self) -> None:
        origin = self.headers.get("Origin", "")
        # Allow localhost origins (any port), file:// (null), and empty (same-origin)
        if origin in ("", "null") or re.match(
            r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$", origin
        ):
            allowed = origin if origin and origin != "null" else "http://127.0.0.1:8123"
            self.send_header("Access-Control-Allow-Origin", allowed)
            self.send_header("Vary", "Origin")
        # External origins: omit ACAO header → browser blocks the request
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status: int, data: Any) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")


def _run_download(job_id: str, model: str, dest: str) -> None:
    """Background download worker — updates _download_jobs[job_id]."""

    def _upd(**kw):
        with _download_lock:
            _download_jobs[job_id].update(kw)

    _upd(state="downloading", progress=5, message="Starting…")
    try:
        os.makedirs(dest, exist_ok=True)
        from huggingface_hub import hf_hub_download, snapshot_download

        # Determine repo_id and filename
        if model.lower().startswith("http"):  # nosec B310 — URL validated below
            # Validate URL for SSRF prevention
            if not validate_download_url(model):
                _upd(state="error", progress=0,
                     message="Download URL not allowed (must be HTTPS from trusted hosts)",
                     error="URL validation failed")
                return
            # Direct URL — stream download with progress
            import urllib.request as _ur

            filename = model.rstrip("/").split("/")[-1]
            out_path = os.path.join(dest, filename)
            _upd(state="downloading", progress=10, message=f"Connecting to {filename}…")

            def _reporthook(block_num, block_size, total_size):
                if total_size > 0:
                    pct = min(99, int(block_num * block_size * 100 / total_size))
                    _upd(progress=pct, message=f"Downloading {filename}… {pct}%")

            _ur.urlretrieve(model, out_path, reporthook=_reporthook)  # nosec B310

        elif model.count("/") >= 2:
            # "owner/repo/file.gguf"
            parts = model.split("/", 2)
            repo_id = "/".join(parts[:2])
            filename = parts[2]
            _upd(
                state="downloading",
                progress=15,
                message=f"Fetching {filename} from {repo_id}…",
            )
            out_path = hf_hub_download(  # nosec B615
                repo_id=repo_id, filename=filename, local_dir=dest
            )

        elif model.count("/") == 1:
            # "owner/repo" — snapshot (all files in repo)
            _upd(
                state="downloading",
                progress=15,
                message=f"Fetching repo metadata for {model}…",
            )
            out_path = snapshot_download(  # nosec B615
                repo_id=model,
                local_dir=os.path.join(dest, model.split("/")[-1]),
                ignore_patterns=["*.bin", "*.pt", "*.safetensors"],  # GGUF repos only
            )
        else:
            _upd(
                state="error",
                progress=0,
                message="Use format: owner/repo/file.gguf or a direct URL",
                error="Invalid format",
            )
            return

        _upd(state="done", progress=100, message="Download complete", path=str(out_path))
        print(f"[download] {job_id} DONE → {out_path}")
    except Exception as exc:
        _upd(state="error", progress=0, message=str(exc), error=str(exc))
        print(f"[download] {job_id} ERROR: {exc}")


def _run_install(job_id: str, pip_cmd: str) -> None:
    """Background install worker — updates _install_jobs[job_id] with live log."""
    import shlex
    import subprocess
    import sys as _sys

    def _upd(**kw):
        with _install_lock:
            _install_jobs[job_id].update(kw)

    _upd(state="running", log="", error="", status_text="Starting pip…")
    try:
        parts = shlex.split(pip_cmd)
        # Always use the same Python executable as the running backend
        if parts[0] in ("pip", "pip3"):
            parts = [_sys.executable, "-m", "pip"] + parts[1:]
        process = subprocess.Popen(
            parts,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        accumulated = ""
        for line in iter(process.stdout.readline, ""):  # type: ignore[union-attr]
            accumulated += line
            short = line.strip()[:100] if line.strip() else "Installing…"
            _upd(log=accumulated, status_text=short)
        process.wait()
        if process.returncode == 0:
            _upd(
                state="done",
                status_text="Installation complete!",
                log=accumulated + "\n✅ Done! Restart the backend to activate.",
            )
            print(f"[install] {job_id} DONE")
        else:
            _upd(
                state="error",
                error=f"pip exited with code {process.returncode}",
                log=accumulated,
            )
            print(f"[install] {job_id} FAILED (code {process.returncode})")
    except Exception as exc:
        _upd(state="error", error=str(exc), log=f"ERROR: {exc}")
        print(f"[install] {job_id} EXCEPTION: {exc}")


def run_server(port: int = 8123) -> None:
    """Start the HTTP server."""
    # Ensure emoji/unicode in log lines don't crash on Windows cp1252 consoles
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]
        except Exception:
            pass
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        try:
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]
        except Exception:
            pass
    server = ThreadingHTTPServer(("127.0.0.1", port), ComparatorHandler)
    print(f"[OK] Comparator backend listening on http://127.0.0.1:{port}")
    print("   System info: /__system-info")
    print("   Comparison:  /__comparison/mixed")
    server.serve_forever()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8123
    run_server(port)
