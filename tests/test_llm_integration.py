"""
Headless LLM Integration Test
==============================
Tests the full backend pipeline WITHOUT a browser:
  1. Backend health + system info
  2. Model scanning
  3. Actual inference on up to 6 GGUF models
  4. Timing + response quality assertions

Run:
    python tests/test_llm_integration.py
    python tests/test_llm_integration.py --models-dir "D:\\Models" --max 3
    python tests/test_llm_integration.py --live   # start backend first
"""

import argparse
import io
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

# Force UTF-8 output on Windows (avoids cp1252 encode errors) — only in CLI mode
if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── Allow importing the backend from the parent directory ──────────────────
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import comparator_backend as cb  # noqa: E402

BACKEND_PORT = 18123  # separate port so we don't clash with any running instance
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _get(path: str, timeout: int = 10) -> dict:
    url = BACKEND_URL + path
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # nosec B310
        return json.loads(resp.read())


def _post(path: str, payload: dict, timeout: int = 300) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        BACKEND_URL + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
        return json.loads(resp.read())


def _wait_backend(retries: int = 20, delay: float = 0.3) -> bool:
    for _ in range(retries):
        try:
            _get("/__health", timeout=2)
            return True
        except Exception:
            time.sleep(delay)
    return False


def _start_backend_thread(model_dirs: list[str]) -> threading.Thread:
    """Spin up the HTTP server in a daemon thread for this test run."""
    from http.server import HTTPServer

    server = HTTPServer(("127.0.0.1", BACKEND_PORT), cb.ComparatorHandler)
    # Override model_dirs for this test run
    cb.ComparatorHandler.model_dirs = model_dirs

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"  → Backend started on {BACKEND_URL}")
    return t


# ═══════════════════════════════════════════════════════════════════════════════
# Result printer
# ═══════════════════════════════════════════════════════════════════════════════

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
WARN = "\033[93m[WARN]\033[0m"
INFO = "\033[94m[INFO]\033[0m"


def _check(condition: bool, label: str, detail: str = "") -> bool:
    status = PASS if condition else FAIL
    msg = f"  {status}  {label}"
    if detail:
        msg += f"\n         {detail}"
    print(msg)
    return condition


# ═══════════════════════════════════════════════════════════════════════════════
# Test suites
# ═══════════════════════════════════════════════════════════════════════════════


def test_unit_functions() -> int:
    """Unit-test pure Python functions in comparator_backend (no HTTP)."""
    failures = 0
    print("\n\033[1m── UNIT TESTS (pure functions) ──────────────────────────────\033[0m")

    # cpu_count returns a positive int
    c = cb.get_cpu_count()
    ok = isinstance(c, int) and c >= 1
    failures += 0 if _check(ok, f"get_cpu_count() → {c}") else 1

    # memory_gb returns positive float
    mem = cb.get_memory_gb()
    ok = isinstance(mem, float) and mem > 0
    failures += 0 if _check(ok, f"get_memory_gb() → {mem:.1f} GB") else 1

    # cpu_info has required keys
    cpu = cb.get_cpu_info()
    required = {"brand", "name", "cores", "avx2", "avx512"}
    ok = required.issubset(cpu.keys())
    failures += (
        0
        if _check(
            ok,
            f"get_cpu_info() keys OK  brand={cpu['brand']}  cores={cpu['cores']}  "
            f"avx2={cpu['avx2']}  avx512={cpu['avx512']}",
        )
        else 1
    )

    # gpu_info returns a list
    gpus = cb.get_gpu_info()
    ok = isinstance(gpus, list)
    failures += 0 if _check(ok, f"get_gpu_info() → {len(gpus)} GPU(s) found") else 1
    for g in gpus:
        print(
            f"         {g['vendor']} {g['name']}  VRAM={g.get('vram_gb', '?')} GB  backend={g.get('backend', '?')}"
        )

    # llama_cpp_info: installed field present
    llama = cb.get_llama_cpp_info()
    ok = "installed" in llama
    failures += (
        0
        if _check(
            ok,
            f"get_llama_cpp_info()  installed={llama['installed']}  version={llama['version']}",
        )
        else 1
    )

    # recommend_llama_build returns pip key
    rec = cb.recommend_llama_build(cpu, gpus)
    ok = "pip" in rec and "build" in rec
    failures += 0 if _check(ok, f"recommend_llama_build()  build={rec['build']}") else 1

    return failures


def test_http_endpoints(model_dirs: list[str]) -> int:
    """Integration tests against the live backend HTTP server."""
    failures = 0
    print("\n\033[1m── HTTP ENDPOINT TESTS ──────────────────────────────────────\033[0m")

    # Health check
    try:
        resp = _get("/__health")
        failures += 0 if _check(resp.get("ok") is True, "/__health → {ok:true}") else 1
    except Exception as e:
        _check(False, "/__health  UNREACHABLE", str(e))
        failures += 1
        return failures  # no point continuing if server is down

    # System info
    try:
        info = _get("/__system-info")
        required_keys = {
            "cpu_count",
            "memory_gb",
            "has_llama_cpp",
            "models",
            "recommended_build",
        }
        ok = required_keys.issubset(info.keys())
        failures += (
            0
            if _check(ok, f"/__system-info keys present  models={info.get('model_count', 0)}")
            else 1
        )
        if ok:
            print(f"         CPU: {info.get('cpu_name', '?')}  {info.get('cpu_count', '?')} cores")
            print(f"         RAM: {info.get('memory_gb', '?')} GB")
            print(f"         GPUs: {len(info.get('gpus', []))}")
            print(f"         llama.cpp: {info.get('llama_cpp_version') or 'not installed'}")
            print(f"         Models found: {info.get('model_count', 0)}")
    except Exception as e:
        _check(False, "/__system-info  FAILED", str(e))
        failures += 1

    return failures


def test_llm_inference(model_dirs: list[str], max_models: int = 6) -> int:
    """Run actual inference through up to max_models GGUF models."""
    failures = 0
    print("\n\033[1m── LLM INFERENCE TESTS ─────────────────────────────────────\033[0m")

    # Discover models
    models = cb.scan_models(model_dirs)
    if not models:
        print(f"  {WARN}  No GGUF models found in: {model_dirs}")
        print("         Cannot run inference tests. Add models to the scan dirs.")
        return 0  # not a failure — just no data

    picks = models[:max_models]
    print(f"  {INFO}  Found {len(models)} model(s), testing {len(picks)}:")
    for m in picks:
        print(f"         {m['name']}  ({m['size_gb']:.1f} GB)")

    TEST_PROMPTS = [
        ("What is 2 + 2? Answer with only the number.", "You are a concise assistant."),
        (
            "Say exactly: HELLO",
            "You are a test assistant. Follow instructions exactly.",
        ),
    ]

    prompt_text, sys_text = TEST_PROMPTS[0]
    print(f'\n  Running prompt: "{prompt_text}"')

    model_paths = [m["path"] for m in picks]
    t_total = time.time()

    try:
        resp = _post(
            "/__comparison/mixed",
            {
                "prompt": prompt_text,
                "system_prompt": sys_text,
                "local_models": model_paths,
                "online_models": [],
                "max_tokens": 64,
                "temperature": 0.0,
                "n_ctx": 2048,
            },
            timeout=600,
        )
    except Exception as e:
        _check(False, "POST /__comparison/mixed  FAILED", str(e))
        return failures + 1

    wall_s = time.time() - t_total
    responses = resp.get("responses", [])

    _check(len(responses) == len(picks), f"Got {len(responses)}/{len(picks)} responses")
    failures += 0 if len(responses) == len(picks) else 1

    times = []
    tps_all = []

    print()
    for r in responses:
        name = r.get("model", "?")
        text = r.get("response", "")
        err = r.get("error", "")
        t_ms = r.get("time_ms", 0)
        tps = r.get("tokens_per_sec", 0)
        tok = r.get("tokens", 0)
        has_resp = bool(text) and not err

        _check(
            has_resp,
            f"{name}",
            f'{t_ms:.0f}ms  {tok}tok  {tps:.1f}t/s  preview: "{text[:60].strip()}"'
            if has_resp
            else f"ERROR: {err or 'empty response'}",
        )
        failures += 0 if has_resp else 1

        if has_resp and t_ms > 0:
            times.append(t_ms)
            tps_all.append(tps)

    # Summary stats
    if times:
        print(f"\n  Summary  ({len(picks)} models, wall={wall_s:.1f}s)")
        print(
            f"         Time  min={min(times):.0f}ms  avg={sum(times) / len(times):.0f}ms  max={max(times):.0f}ms"
        )
        if tps_all:
            nonzero = [t for t in tps_all if t > 0]
            if nonzero:
                print(
                    f"         Tok/s min={min(nonzero):.1f}  avg={sum(nonzero) / len(nonzero):.1f}  max={max(nonzero):.1f}"
                )

    return failures


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════


def main() -> int:
    ap = argparse.ArgumentParser(description="Headless LLM integration test for comparator_backend")
    ap.add_argument(
        "--models-dir",
        default=None,
        help="Extra directory to scan for GGUF models (can be repeated)",
        action="append",
        dest="extra_dirs",
    )
    ap.add_argument(
        "--max",
        type=int,
        default=6,
        help="Max number of models to run inference on (default 6)",
    )
    ap.add_argument(
        "--live",
        action="store_true",
        help="Use an already-running backend on port 8123 instead of starting one",
    )
    args = ap.parse_args()

    model_dirs = list(cb.ComparatorHandler.model_dirs)
    if args.extra_dirs:
        model_dirs = args.extra_dirs + model_dirs

    print("=" * 60)
    print("   ZEN LLM COMPARE -- Headless Integration Test")
    print("=" * 60)
    print(f"Model dirs: {model_dirs}")
    print(f"Max models: {args.max}")

    total_failures = 0

    # ── 1. Unit tests (no server needed) ────────────────────────────────────
    total_failures += test_unit_functions()

    # ── 2. Start or use live backend ────────────────────────────────────────
    global BACKEND_PORT, BACKEND_URL
    if args.live:
        BACKEND_PORT = 8123
        BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"
        print(f"\nUsing live backend at {BACKEND_URL}")
    else:
        print(f"\nStarting backend on port {BACKEND_PORT}…")
        _start_backend_thread(model_dirs)
        if not _wait_backend():
            print(f"{FAIL}  Backend did not start within timeout")
            sys.exit(1)

    # ── 3. HTTP endpoint tests ───────────────────────────────────────────────
    total_failures += test_http_endpoints(model_dirs)

    # ── 4. Actual LLM inference tests ───────────────────────────────────────
    total_failures += test_llm_inference(model_dirs, max_models=args.max)

    # ── Final verdict ────────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    if total_failures == 0:
        print("\033[92m\033[1m  ALL TESTS PASSED\033[0m")
    else:
        print(f"\033[91m\033[1m  {total_failures} TEST(S) FAILED\033[0m")
    print("─" * 60)
    return total_failures


if __name__ == "__main__":
    sys.exit(main())
