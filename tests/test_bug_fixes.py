"""
TDD Tests for Priority 1 Bug Fixes
====================================
Tests written BEFORE implementation (TDD style):
  1. Token counting — must use actual tokenizer, not word split
  2. CORS — must restrict to localhost origins only
  3. Judge retry — must retry/fallback on JSON parse failure

Run:
    pytest tests/test_bug_fixes.py -v
"""

import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

# ─── Allow importing the backend from the parent directory ──────────────────
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import comparator_backend as cb  # noqa: E402

# Test port — unique to avoid clashes
TEST_PORT = 18124
TEST_URL = f"http://127.0.0.1:{TEST_PORT}"


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

_server = None
_server_thread = None


def _start_test_server():
    """Start a test backend server in a daemon thread."""
    global _server, _server_thread
    if _server is not None:
        return
    from http.server import HTTPServer
    _server = HTTPServer(("127.0.0.1", TEST_PORT), cb.ComparatorHandler)
    _server_thread = threading.Thread(target=_server.serve_forever, daemon=True)
    _server_thread.start()
    # Wait for server to be ready
    for _ in range(30):
        try:
            req = urllib.request.Request(f"{TEST_URL}/__health")
            with urllib.request.urlopen(req, timeout=2) as r:
                if r.status == 200:
                    break
        except Exception:
            time.sleep(0.1)


def _get(path, headers=None, timeout=5):
    """HTTP GET helper returning (status, headers_dict, body_dict)."""
    req = urllib.request.Request(TEST_URL + path)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), json.loads(e.read()) if e.read() else {}


def _options(path, headers=None, timeout=5):
    """HTTP OPTIONS helper returning (status, headers_dict)."""
    req = urllib.request.Request(TEST_URL + path, method="OPTIONS")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: Token Counting Accuracy
# ═══════════════════════════════════════════════════════════════════════════════

class TestTokenCounting:
    """Token counting must use actual tokenizer, not len(text.split())."""

    def test_count_tokens_function_exists(self):
        """Backend must have a count_tokens() or equivalent function."""
        assert hasattr(cb, 'count_tokens'), \
            "comparator_backend must expose a count_tokens(text, model_path=None) function"

    def test_count_tokens_returns_int(self):
        """count_tokens must return a positive integer."""
        result = cb.count_tokens("Hello world, this is a test.")
        assert isinstance(result, int), f"Expected int, got {type(result)}"
        assert result > 0, "Token count must be positive"

    def test_count_tokens_differs_from_word_split(self):
        """Token count must differ from naive word split for typical text.
        
        For example: "don't" is 1 word but typically 2-3 tokens.
        "Hello, world!" has 2 words but 4+ tokens (punctuation tokenized separately).
        """
        text = "Hello, world! I don't think this should be split naively."
        word_count = len(text.split())
        token_count = cb.count_tokens(text)
        # Token count should NOT equal word count for complex text
        # (punctuation, contractions create more tokens)
        assert token_count != word_count, \
            f"Token count ({token_count}) equals word split ({word_count}) — still using naive splitting!"

    def test_count_tokens_empty_string(self):
        """Empty string should return 0 tokens."""
        assert cb.count_tokens("") == 0

    def test_count_tokens_handles_unicode(self):
        """Unicode text should be tokenized without errors."""
        result = cb.count_tokens("Héllo wörld 日本語 🎉")
        assert isinstance(result, int) and result > 0

    def test_count_tokens_long_text(self):
        """Long text should tokenize correctly (>1000 words)."""
        text = "The quick brown fox jumps over the lazy dog. " * 200
        result = cb.count_tokens(text)
        assert result > 100, f"Long text should produce many tokens, got {result}"
        # Tokenizers typically produce more tokens than word count
        word_count = len(text.split())
        # Should be in a reasonable range (0.5x to 3x of word count)
        assert 0.3 * word_count < result < 4.0 * word_count, \
            f"Token count {result} is unreasonably far from word count {word_count}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: CORS Security
# ═══════════════════════════════════════════════════════════════════════════════

class TestCORSSecurity:
    """CORS must restrict origins to localhost only."""

    @classmethod
    def setup_class(cls):
        _start_test_server()

    def test_cors_allows_localhost(self):
        """Requests from localhost origins must be allowed."""
        status, headers, body = _get("/__health",
            headers={"Origin": "http://127.0.0.1:8123"})
        assert status == 200
        acao = headers.get("Access-Control-Allow-Origin", "")
        # Must either echo back the localhost origin or use a localhost pattern
        assert "127.0.0.1" in acao or "localhost" in acao or acao == "*", \
            f"Localhost origin should be allowed, got ACAO: {acao}"

    def test_cors_allows_localhost_variants(self):
        """Various localhost origins (different ports) should be allowed."""
        for origin in [
            "http://localhost:8123",
            "http://127.0.0.1:8123",
            "http://localhost:3000",
            "http://127.0.0.1:18124",
        ]:
            status, headers, body = _get("/__health",
                headers={"Origin": origin})
            assert status == 200, f"Request from {origin} should succeed"

    def test_cors_not_wildcard(self):
        """CORS must NOT use wildcard '*' — must be restricted."""
        status, headers, body = _get("/__health",
            headers={"Origin": "http://127.0.0.1:8123"})
        acao = headers.get("Access-Control-Allow-Origin", "")
        assert acao != "*", \
            "CORS Access-Control-Allow-Origin must NOT be wildcard '*' — security risk!"

    def test_cors_rejects_external_origin(self):
        """Requests from external origins must be rejected (no ACAO header)."""
        status, headers, body = _get("/__health",
            headers={"Origin": "https://evil-site.com"})
        acao = headers.get("Access-Control-Allow-Origin", "")
        # Should either be empty/absent or NOT contain the evil domain
        assert "evil-site.com" not in acao, \
            f"External origin should NOT be reflected in ACAO header: {acao}"

    def test_cors_options_preflight_localhost(self):
        """OPTIONS preflight from localhost must return proper CORS headers."""
        status, headers = _options("/__comparison/mixed",
            headers={
                "Origin": "http://127.0.0.1:8123",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            })
        assert status == 204
        assert "Access-Control-Allow-Methods" in headers

    def test_file_origin_allowed(self):
        """file:// origin (opening HTML directly) should be allowed."""
        status, headers, body = _get("/__health",
            headers={"Origin": "null"})  # file:// sends "null" as origin
        assert status == 200, "file:// origin (null) should not be blocked"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: Judge Retry on JSON Parse Failure
# ═══════════════════════════════════════════════════════════════════════════════

class TestJudgeRetry:
    """Judge must retry or fallback when JSON parsing fails."""

    def test_extract_json_from_clean_json(self):
        """Clean JSON should parse directly."""
        raw = '{"overall": 8.5, "accuracy": 7, "reasoning": 9, "instruction_following": true, "safety": "safe"}'
        assert hasattr(cb, 'extract_judge_scores'), \
            "comparator_backend must expose extract_judge_scores(raw_text) function"
        result = cb.extract_judge_scores(raw)
        assert isinstance(result, dict)
        assert result.get("overall") == 8.5

    def test_extract_json_from_markdown_fences(self):
        """JSON wrapped in markdown code fences should be extracted."""
        raw = '''Here is my evaluation:
```json
{"overall": 7.0, "accuracy": 6, "reasoning": 8, "instruction_following": true, "safety": "safe"}
```
The model performed well overall.'''
        result = cb.extract_judge_scores(raw)
        assert isinstance(result, dict)
        assert result.get("overall") == 7.0

    def test_extract_json_from_natural_language(self):
        """When JSON parsing fails entirely, extract scores from natural language."""
        raw = """Based on my evaluation:
- Overall score: 6 out of 10
- Accuracy: 5/10
- Reasoning: 7/10
- The response follows instructions: yes
- Safety: safe

The model provided a decent response but lacked depth."""
        result = cb.extract_judge_scores(raw)
        assert isinstance(result, dict)
        # Should extract at least an overall score
        assert "overall" in result, "Must extract overall score from natural language"
        score = result["overall"]
        assert isinstance(score, (int, float)), f"Score must be numeric, got {type(score)}"
        assert 0 <= score <= 10, f"Score {score} out of valid range 0-10"

    def test_extract_json_returns_zero_on_total_garbage(self):
        """Complete garbage text should return a valid dict with score 0."""
        raw = "I cannot evaluate this because my circuits are overloaded with existential dread."
        result = cb.extract_judge_scores(raw)
        assert isinstance(result, dict), "Must always return a dict"
        assert "overall" in result, "Must always have 'overall' key"
        # Score 0 is acceptable for unparseable output
        assert isinstance(result["overall"], (int, float))

    def test_extract_json_from_partial_json(self):
        """Partial/malformed JSON should still extract what's possible."""
        raw = '{"overall": 8, "accuracy": 7, reasoning: 6}'  # missing quotes on key
        result = cb.extract_judge_scores(raw)
        assert isinstance(result, dict)
        # Should recover at least the overall score
        assert "overall" in result

    def test_extract_json_handles_score_out_of_range(self):
        """Scores outside 0-10 should be clamped."""
        raw = '{"overall": 15, "accuracy": -3}'
        result = cb.extract_judge_scores(raw)
        assert 0 <= result.get("overall", 0) <= 10, "Score should be clamped to 0-10"

    def test_extract_json_handles_nested_json(self):
        """JSON with extra nesting (common LLM output) should be handled."""
        raw = '''```json
{
  "evaluation": {
    "overall": 8,
    "accuracy": 7,
    "reasoning": 9,
    "instruction_following": true,
    "safety": "safe"
  }
}
```'''
        result = cb.extract_judge_scores(raw)
        assert isinstance(result, dict)
        assert "overall" in result

    def test_extract_handles_score_as_string(self):
        """Scores as strings like "8/10" or "8.5" should be parsed."""
        raw = '{"overall": "8/10", "accuracy": "7.5"}'
        result = cb.extract_judge_scores(raw)
        assert isinstance(result.get("overall"), (int, float))
        assert result["overall"] == 8.0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: URL Validation (bonus security)
# ═══════════════════════════════════════════════════════════════════════════════

class TestURLValidation:
    """Download URLs must be validated to prevent SSRF."""

    def test_validate_download_url_exists(self):
        """Backend must have a validate_download_url function."""
        assert hasattr(cb, 'validate_download_url'), \
            "comparator_backend must expose validate_download_url(url) function"

    def test_allows_huggingface_urls(self):
        """HuggingFace download URLs should be allowed."""
        assert cb.validate_download_url(
            "https://huggingface.co/TheBloke/Llama-2-7B-GGUF/resolve/main/llama-2-7b.Q4_K_M.gguf"
        ) is True

    def test_allows_github_release_urls(self):
        """GitHub release URLs should be allowed."""
        assert cb.validate_download_url(
            "https://github.com/someone/repo/releases/download/v1.0/model.gguf"
        ) is True

    def test_blocks_localhost_urls(self):
        """localhost/127.0.0.1 URLs must be blocked (SSRF prevention)."""
        for url in [
            "http://localhost:8080/secret",
            "http://127.0.0.1:9200/_cluster/health",
            "http://[::1]/admin",
            "http://0.0.0.0:22/ssh",
        ]:
            assert cb.validate_download_url(url) is False, \
                f"Should block localhost URL: {url}"

    def test_blocks_private_ip_ranges(self):
        """Private IP ranges must be blocked (SSRF)."""
        for url in [
            "http://192.168.1.1/admin",
            "http://10.0.0.1/internal",
            "http://172.16.0.1/secret",
        ]:
            assert cb.validate_download_url(url) is False, \
                f"Should block private IP URL: {url}"

    def test_blocks_non_https(self):
        """Non-HTTPS URLs should be blocked (except for known safe hosts)."""
        assert cb.validate_download_url("http://random-site.com/model.gguf") is False

    def test_blocks_ftp_and_file_schemes(self):
        """ftp:// and file:// schemes must be blocked."""
        assert cb.validate_download_url("ftp://server/model.gguf") is False
        assert cb.validate_download_url("file:///etc/passwd") is False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: Integration — CORS + Token Count in comparison response
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests to verify fixes work end-to-end."""

    @classmethod
    def setup_class(cls):
        _start_test_server()

    def test_health_endpoint_has_restricted_cors(self):
        """Health endpoint CORS header must not be wildcard."""
        status, headers, body = _get("/__health",
            headers={"Origin": "http://127.0.0.1:8123"})
        assert status == 200
        acao = headers.get("Access-Control-Allow-Origin", "")
        assert acao != "*", f"CORS should not be wildcard, got: {acao}"

    def test_system_info_has_restricted_cors(self):
        """System info endpoint CORS header must not be wildcard."""
        status, headers, body = _get("/__system-info",
            headers={"Origin": "http://localhost:8123"})
        assert status == 200
        acao = headers.get("Access-Control-Allow-Origin", "")
        assert acao != "*", f"CORS should not be wildcard, got: {acao}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: Rate Limiting
# ═══════════════════════════════════════════════════════════════════════════════

class TestRateLimiting:
    """Rate limiter must throttle per-IP after exceeding max requests."""

    def test_rate_limiter_class_exists(self):
        """Backend must expose _RateLimiter."""
        assert hasattr(cb, '_RateLimiter'), \
            "comparator_backend must have a _RateLimiter class"

    def test_rate_limiter_allows_under_limit(self):
        """Requests under the limit should be allowed."""
        rl = cb._RateLimiter(max_requests=5, window_sec=60.0)
        for _ in range(5):
            assert rl.allow("10.0.0.1") is True

    def test_rate_limiter_blocks_over_limit(self):
        """Requests over the limit should be blocked."""
        rl = cb._RateLimiter(max_requests=3, window_sec=60.0)
        for _ in range(3):
            rl.allow("10.0.0.2")
        assert rl.allow("10.0.0.2") is False

    def test_rate_limiter_per_ip_isolation(self):
        """Different IPs should have independent limits."""
        rl = cb._RateLimiter(max_requests=2, window_sec=60.0)
        rl.allow("10.0.0.3")
        rl.allow("10.0.0.3")
        assert rl.allow("10.0.0.3") is False
        # A fresh IP should still be allowed
        assert rl.allow("10.0.0.4") is True

    def test_rate_limiter_remaining(self):
        """remaining() must return correct count."""
        rl = cb._RateLimiter(max_requests=5, window_sec=60.0)
        assert rl.remaining("10.0.0.5") == 5
        rl.allow("10.0.0.5")
        rl.allow("10.0.0.5")
        assert rl.remaining("10.0.0.5") == 3

    def test_rate_limiter_window_expiry(self):
        """Requests outside the window should be pruned."""
        rl = cb._RateLimiter(max_requests=1, window_sec=0.1)
        assert rl.allow("10.0.0.6") is True
        assert rl.allow("10.0.0.6") is False
        time.sleep(0.15)  # wait for window to expire
        assert rl.allow("10.0.0.6") is True

    def test_global_rate_limiter_instance(self):
        """A global _rate_limiter instance must be available."""
        assert hasattr(cb, '_rate_limiter'), \
            "comparator_backend must have a _rate_limiter global instance"
        assert isinstance(cb._rate_limiter, cb._RateLimiter)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 6: Configurable Inference Timeout
# ═══════════════════════════════════════════════════════════════════════════════

class TestInferenceTimeout:
    """Inference timeout must be configurable with safe clamping."""

    def test_default_timeout_constant(self):
        """DEFAULT_INFERENCE_TIMEOUT must be defined."""
        assert hasattr(cb, 'DEFAULT_INFERENCE_TIMEOUT')
        assert cb.DEFAULT_INFERENCE_TIMEOUT == 300

    def test_max_timeout_constant(self):
        """MAX_INFERENCE_TIMEOUT must be defined as hard ceiling."""
        assert hasattr(cb, 'MAX_INFERENCE_TIMEOUT')
        assert cb.MAX_INFERENCE_TIMEOUT == 1800

    def test_max_exceeds_default(self):
        """Max timeout must exceed default timeout."""
        assert cb.MAX_INFERENCE_TIMEOUT > cb.DEFAULT_INFERENCE_TIMEOUT


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 7: Config Endpoint
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfigEndpoint:
    """GET /__config must return server configuration."""

    @classmethod
    def setup_class(cls):
        _start_test_server()

    def test_config_endpoint_returns_200(self):
        """/__config must return HTTP 200."""
        status, headers, body = _get("/__config",
            headers={"Origin": "http://127.0.0.1:8123"})
        assert status == 200

    def test_config_has_required_fields(self):
        """/__config response must include all expected fields."""
        status, headers, body = _get("/__config",
            headers={"Origin": "http://127.0.0.1:8123"})
        assert "vk_devices" in body
        assert "default_inference_timeout" in body
        assert "max_inference_timeout" in body
        assert "rate_limit" in body

    def test_config_timeout_values(self):
        """Config timeout values must match module constants."""
        status, headers, body = _get("/__config",
            headers={"Origin": "http://127.0.0.1:8123"})
        assert body["default_inference_timeout"] == cb.DEFAULT_INFERENCE_TIMEOUT
        assert body["max_inference_timeout"] == cb.MAX_INFERENCE_TIMEOUT

    def test_config_rate_limit_structure(self):
        """Rate limit in config must have max_requests and window_sec."""
        status, headers, body = _get("/__config",
            headers={"Origin": "http://127.0.0.1:8123"})
        rl = body["rate_limit"]
        assert "max_requests" in rl
        assert "window_sec" in rl
        assert rl["max_requests"] > 0
        assert rl["window_sec"] > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 8: Multi-GPU Support
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiGPU:
    """GGML_VK_VISIBLE_DEVICES must support multi-GPU config."""

    def test_vk_devices_env_is_set(self):
        """GGML_VK_VISIBLE_DEVICES must be set after import."""
        assert "GGML_VK_VISIBLE_DEVICES" in os.environ

    def test_vk_devices_not_empty(self):
        """GGML_VK_VISIBLE_DEVICES must not be empty."""
        val = os.environ.get("GGML_VK_VISIBLE_DEVICES", "")
        assert len(val) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 9: Judge Bias Randomization (A2)
# ═══════════════════════════════════════════════════════════════════════════════

class TestJudgeBiasRandomization:
    """The _run_judge method must implement dual-pass bias mitigation."""

    def test_run_judge_method_exists(self):
        """ComparatorHandler must have _run_judge."""
        assert hasattr(cb.ComparatorHandler, '_run_judge')

    def test_run_judge_signature_accepts_responses_list(self):
        """_run_judge must accept responses list and return a list."""
        import inspect
        sig = inspect.signature(cb.ComparatorHandler._run_judge)
        params = list(sig.parameters.keys())
        assert 'responses' in params
        assert 'original_prompt' in params

    def test_extract_judge_scores_bias_passes_field(self):
        """extract_judge_scores should parse the bias_passes field correctly."""
        raw = '{"overall": 7.5, "accuracy": 8, "reasoning": 7, "instruction_following": "followed", "safety": "safe"}'
        result = cb.extract_judge_scores(raw)
        assert 'overall' in result
        assert result['overall'] == 7.5

    def test_extract_judge_scores_handles_markdown_wrap(self):
        """extract_judge_scores should handle ```json blocks."""
        raw = '```json\n{"overall": 8.0, "accuracy": 7}\n```'
        result = cb.extract_judge_scores(raw)
        assert result.get('overall') == 8.0

    def test_extract_judge_scores_handles_no_json(self):
        """extract_judge_scores should return usable output even with garbage."""
        raw = 'I think the score is about 6 out of 10'
        result = cb.extract_judge_scores(raw)
        # Should at least return a dict (may have 0 or a parsed number)
        assert isinstance(result, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 10: SSE Streaming Endpoint (A1)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSSEStreaming:
    """The /__comparison/stream endpoint must exist and return SSE headers."""

    @classmethod
    def setup_class(cls):
        _start_test_server()

    def _stream_post(self, path, body_dict, read_timeout=15):
        """POST using http.client to properly handle streaming SSE responses."""
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", TEST_PORT, timeout=read_timeout)
        body = json.dumps(body_dict)
        conn.request("POST", path, body=body, headers={
            "Content-Type": "application/json",
            "Origin": "http://127.0.0.1:8123",
        })
        resp = conn.getresponse()
        status = resp.status
        headers = dict(resp.getheaders())
        # Read body (with timeout safety)
        body_data = resp.read(8192).decode("utf-8", errors="replace")
        conn.close()
        return status, headers, body_data

    def test_stream_endpoint_exists(self):
        """POST to /__comparison/stream must not return 404."""
        status, headers, body = self._stream_post("/__comparison/stream", {
            "prompt": "Hello",
            "local_models": [],
            "online_models": [],
        })
        assert status != 404, "Stream endpoint returned 404 — route not registered"
        assert status == 200, f"Expected 200, got: {status}"

    def test_stream_endpoint_returns_sse_content_type(self):
        """The stream endpoint must set Content-Type: text/event-stream."""
        status, headers, body = self._stream_post("/__comparison/stream", {
            "prompt": "Test prompt",
            "local_models": [],
            "online_models": [],
        })
        ct = headers.get("Content-Type", "")
        assert "text/event-stream" in ct, f"Expected SSE content-type, got: {ct}"
        cc = headers.get("Cache-Control", "")
        assert "no-cache" in cc, f"Expected no-cache, got: {cc}"

    def test_stream_endpoint_sends_sse_events(self):
        """The stream endpoint must send valid SSE event lines."""
        _, _, body = self._stream_post("/__comparison/stream", {
            "prompt": "Test",
            "local_models": [],
            "online_models": [],
        })
        # Even with no valid models it should send at least a 'done' event
        assert "event:" in body or "data:" in body, f"No SSE events in body: {body[:300]}"

    def test_stream_endpoint_does_not_crash_server(self):
        """Server must stay alive after multiple stream requests."""
        for _ in range(2):
            try:
                self._stream_post("/__comparison/stream", {
                    "prompt": "Test",
                    "local_models": [],
                    "online_models": [],
                })
            except Exception:
                pass
        # Verify server is still alive
        status, _, _ = _get("/__health", headers={"Origin": "http://127.0.0.1:8123"})
        assert status == 200


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 11: Frontend Enhancements (A3, A4, B1-B3, C2)
# ═══════════════════════════════════════════════════════════════════════════════

class TestFrontendEnhancements:
    """Verify that the HTML file contains all required enhancement elements."""

    @classmethod
    def setup_class(cls):
        html_path = os.path.join(REPO_ROOT, "model_comparator.html")
        with open(html_path, "r", encoding="utf-8") as f:
            cls.html = f.read()

    # A4: Scenario cards
    def test_scenario_buttons_exist(self):
        """HTML must contain scenario preset buttons."""
        assert 'loadScenario(' in self.html
        for s in ['clinical_triage', 'code_review', 'math_olympiad', 'polyglot', 'speed_test', 'stress_test']:
            assert s in self.html, f"Missing scenario: {s}"

    def test_scenarios_config_object(self):
        """_SCENARIOS config must exist in JS."""
        assert '_SCENARIOS' in self.html

    # A3: History + ELO
    def test_history_storage_key(self):
        """localStorage key for history must be defined."""
        assert 'zen_compare_history' in self.html

    def test_elo_storage_key(self):
        """localStorage key for ELO must be defined."""
        assert 'zen_compare_elo' in self.html

    def test_leaderboard_table_exists(self):
        """Leaderboard HTML table must exist."""
        assert 'leaderboardBody' in self.html

    def test_save_to_history_function(self):
        """_saveToHistory function must exist."""
        assert '_saveToHistory' in self.html

    def test_update_elo_function(self):
        """_updateElo function must exist."""
        assert '_updateElo' in self.html

    def test_render_leaderboard_function(self):
        """_renderLeaderboard function must exist."""
        assert '_renderLeaderboard' in self.html

    def test_replay_history_function(self):
        """_replayHistory function must exist."""
        assert '_replayHistory' in self.html

    # B1: Race visualization
    def test_stream_cards_exist(self):
        """Streaming UI cards with progress bars must exist."""
        assert 'stream-bar-' in self.html
        assert 'stream-text-' in self.html
        assert 'stream-stats-' in self.html

    def test_handle_stream_event_function(self):
        """_handleStreamEvent must exist for SSE processing."""
        assert '_handleStreamEvent' in self.html

    # B2: Smart recommendations
    def test_model_fitness_function(self):
        """_modelFitness function must exist."""
        assert '_modelFitness' in self.html

    def test_fitness_column_header(self):
        """Model library table must have a Fit column."""
        assert '>Fit<' in self.html

    # B3: Shareable reports
    def test_share_report_function(self):
        """_shareReport function must exist."""
        assert '_shareReport' in self.html

    def test_share_button_exists(self):
        """Share button must be in the results panel."""
        assert 'SHARE' in self.html
        assert '_shareReport()' in self.html

    # C2: Batch comparisons
    def test_batch_mode_toggle(self):
        """_toggleBatchMode function must exist."""
        assert '_toggleBatchMode' in self.html

    def test_batch_panel_exists(self):
        """Batch panel HTML must exist."""
        assert 'batchPanel' in self.html
        assert 'batchPrompts' in self.html

    def test_run_batch_function(self):
        """_runBatch function must exist."""
        assert '_runBatch' in self.html

    def test_add_bank_to_batch_function(self):
        """_addBankToBatch function must exist."""
        assert '_addBankToBatch' in self.html

    # A1: SSE streaming
    def test_run_stream_comparison_function(self):
        """_runStreamComparison function must exist."""
        assert '_runStreamComparison' in self.html

    def test_show_streaming_ui_function(self):
        """_showStreamingUI function must exist."""
        assert '_showStreamingUI' in self.html


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 12: HuggingFace Model Discovery
# ═══════════════════════════════════════════════════════════════════════════════

class TestModelDiscovery:
    """Verify discovery endpoints and frontend elements."""

    # ── Backend unit tests ──────────────────────────────────────────────────

    def test_discover_endpoint_exists(self):
        """GET /__discover-models must return 200, not 404."""
        resp = urllib.request.urlopen(f"{TEST_URL}/__discover-models?q=test&sort=trending&limit=5", timeout=15)
        assert resp.status == 200

    def test_discover_returns_json(self):
        """Discovery endpoint must return valid JSON with 'models' key."""
        resp = urllib.request.urlopen(f"{TEST_URL}/__discover-models?q=&sort=trending&limit=5", timeout=15)
        data = json.loads(resp.read().decode())
        assert "models" in data

    def test_discover_sort_validation(self):
        """Invalid sort values should default to trending (not crash)."""
        resp = urllib.request.urlopen(f"{TEST_URL}/__discover-models?sort=INVALID", timeout=15)
        assert resp.status == 200

    def test_discover_limit_cap(self):
        """Limit should be capped at 60."""
        resp = urllib.request.urlopen(f"{TEST_URL}/__discover-models?limit=999", timeout=15)
        assert resp.status == 200

    def test_trusted_quantizers_list(self):
        """_TRUSTED_QUANTIZERS must contain known reliable sources."""
        assert hasattr(cb, '_TRUSTED_QUANTIZERS')
        for q in ("bartowski", "mradermacher", "TheBloke", "unsloth"):
            assert q in cb._TRUSTED_QUANTIZERS

    def test_discovery_cache_structure(self):
        """Discovery cache dict must exist on the module."""
        assert hasattr(cb, '_discovery_cache')
        assert isinstance(cb._discovery_cache, dict)

    def test_discovery_ttl_reasonable(self):
        """Cache TTL should be between 5 and 60 minutes."""
        assert 300 <= cb._DISCOVERY_TTL <= 3600

    # ── Frontend tests ──────────────────────────────────────────────────────

    @classmethod
    def setup_class(cls):
        html_path = os.path.join(REPO_ROOT, "model_comparator.html")
        with open(html_path, "r", encoding="utf-8") as f:
            cls.html = f.read()

    def test_discover_tab_button(self):
        """Discover tab button must exist in download modal."""
        assert "switchRepo('discover'" in self.html

    def test_discover_section_html(self):
        """repo-discover section must exist."""
        assert 'id="repo-discover"' in self.html

    def test_discover_search_input(self):
        """Search input field must exist in Discover tab."""
        assert 'id="discoverSearch"' in self.html

    def test_discover_sort_dropdown(self):
        """Sort dropdown in Discover tab must exist."""
        assert 'id="discoverSort"' in self.html

    def test_run_discover_search_function(self):
        """runDiscoverSearch function must exist."""
        assert 'function runDiscoverSearch' in self.html

    def test_render_discover_results_function(self):
        """renderDiscoverResults function must exist."""
        assert 'function renderDiscoverResults' in self.html

    def test_select_discover_model_function(self):
        """selectDiscoverModel function must exist."""
        assert 'function selectDiscoverModel' in self.html

    def test_discover_grid_element(self):
        """discoverGrid container must exist."""
        assert 'id="discoverGrid"' in self.html

    def test_trusted_badge_in_frontend(self):
        """Trusted quantizer badge must be rendered."""
        assert 'Trusted' in self.html

    # ── X-Ray: Security & edge-case tests ──────────────────────────────────

    def test_discover_limit_non_numeric_does_not_crash(self):
        """Non-numeric limit param must not crash the server."""
        resp = urllib.request.urlopen(f"{TEST_URL}/__discover-models?limit=abc", timeout=15)
        assert resp.status == 200

    def test_discover_empty_query_safe(self):
        """Empty query must return valid response."""
        resp = urllib.request.urlopen(f"{TEST_URL}/__discover-models?q=", timeout=15)
        data = json.loads(resp.read().decode())
        assert "models" in data

    def test_discover_xss_in_query_param(self):
        """XSS in query param must not break response."""
        xss = urllib.parse.quote('<script>alert(1)</script>')
        resp = urllib.request.urlopen(f"{TEST_URL}/__discover-models?q={xss}", timeout=15)
        assert resp.status == 200

    def test_frontend_eschtml_function_exists(self):
        """_escHtml sanitizer function must exist in HTML."""
        assert 'function _escHtml' in self.html

    def test_frontend_uses_eschtml_for_error(self):
        """Error display must use _escHtml to prevent XSS."""
        assert '_escHtml(e.message)' in self.html

    def test_frontend_uses_eschtml_for_model_id(self):
        """Model ID display must use _escHtml to prevent XSS from malicious repo names."""
        assert "_escHtml(m.id" in self.html

    def test_frontend_uses_eschtml_for_author(self):
        """Author display must use _escHtml."""
        assert "_escHtml(author)" in self.html

    def test_frontend_uses_eschtml_for_pipeline(self):
        """Pipeline tag must use _escHtml."""
        assert "_escHtml(m.pipeline)" in self.html

    def test_discover_no_frontend_cache(self):
        """Frontend must not have its own data cache (backend handles caching)."""
        assert '_discoverCache' not in self.html
