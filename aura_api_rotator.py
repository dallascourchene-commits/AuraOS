"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: json, __future__, sys, urllib.request, typing, urllib.error, os, time, pathlib, ssl, aura_llm_call_logger
FUNCTIONS: _secrets_search_paths, _warn_secret_load, _parse_secret_json, _load_secret_file, load_secrets, _is_valid_key, gemini_key_pool, _is_retryable, _gemini_url, _post_json, _extract_gemini_text, _extract_openai_text, gemini_generate, openai_compatible_generate, get_gemini_rotator, _add, __init__, key_count, keys, _available_keys, record_success, record_failure, iter_keys
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

"""
Gemini-first API key rotation with retries and provider fallback.

Loads keys from ~/aura_secrets.json:
  GEMINI_API_KEY          — primary
  GEMINI_API_KEYS         — list of additional keys (rotated on 429/timeout)
  GEMINI_API_KEY_2 … _9   — optional numbered backups
"""

import json
import os
from pathlib import Path
import ssl
import sys
import time
from typing import Any
import urllib.error
import urllib.request

from aura_llm_call_logger import log_gemini_call, log_openai_compatible_call

_DEFAULT_SECRETS = Path.home() / "aura_secrets.json"


def _secrets_search_paths() -> list[Path]:
    paths = [Path.home() / "aura_secrets.json"]
    module_dir = Path(__file__).resolve().parent / "aura_secrets.json"
    if module_dir not in paths:
        paths.append(module_dir)
    cwd = Path.cwd() / "aura_secrets.json"
    if cwd not in paths:
        paths.append(cwd)
    return paths


def _warn_secret_load(path: Path, message: str) -> None:
    print(f"[!] Secret load warning (non-fatal): {path.name}: {message}", file=sys.stderr)


def _parse_secret_json(raw: str, secrets_path: Path) -> dict[str, Any]:
    text = raw.lstrip("\ufeff").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
        _warn_secret_load(secrets_path, "top-level JSON must be an object; ignoring file")
        return {}
    except json.JSONDecodeError as original_exc:
        decoder = json.JSONDecoder()
        idx = 0
        merged: dict[str, Any] = {}
        fragments = 0
        while idx < len(text):
            while idx < len(text) and text[idx].isspace():
                idx += 1
            if idx >= len(text):
                break
            try:
                item, idx = decoder.raw_decode(text, idx)
            except json.JSONDecodeError:
                _warn_secret_load(
                    secrets_path,
                    f"invalid JSON at line {original_exc.lineno}, column {original_exc.colno}; ignoring file",
                )
                return {}
            if not isinstance(item, dict):
                _warn_secret_load(secrets_path, "all top-level JSON fragments must be objects; ignoring file")
                return {}
            merged.update(item)
            fragments += 1
        if fragments > 1:
            _warn_secret_load(
                secrets_path,
                "merged multiple top-level objects; move all keys inside one outer JSON object",
            )
        return merged


def _load_secret_file(secrets_path: Path) -> dict[str, Any]:
    try:
        return _parse_secret_json(secrets_path.read_text(encoding="utf-8"), secrets_path)
    except OSError as exc:
        _warn_secret_load(secrets_path, f"cannot read file: {exc}")
        return {}
    except UnicodeDecodeError as exc:
        _warn_secret_load(secrets_path, f"file is not valid UTF-8: {exc}")
        return {}
    except UnicodeDecodeError as exc:
        _warn_secret_load(secrets_path, f"file is not valid UTF-8: {exc}")
        return {}


def load_secrets(path: Path | str | None = None) -> dict[str, Any]:
    if path is not None:
        secrets_path = Path(path)
        if not secrets_path.exists():
            return {}
        return _load_secret_file(secrets_path)
    for secrets_path in _secrets_search_paths():
        if secrets_path.exists():
            return _load_secret_file(secrets_path)
    return {}

_RETRYABLE_FRAGMENTS = (
    "timeout",
    "timed out",
    "429",
    "rate",
    "quota",
    "503",
    "502",
    "500",
    "connection reset",
    "connection refused",
    "temporarily unavailable",
    "resource exhausted",
    "deadline",
)

_GEMINI_MODEL = os.environ.get("AURA_GEMINI_MODEL", "gemini-1.5-flash")
_CLOUD_TIMEOUT = float(os.environ.get("AURA_CLOUD_TIMEOUT_SEC", "30"))
_CLOUD_RETRIES_PER_KEY = int(os.environ.get("AURA_CLOUD_RETRIES_PER_KEY", "2"))

_PLACEHOLDER_MARKERS = ("your_actual_", "your_new_key", "YOUR_", "paste_", "changeme", "your_primary_")


def _is_valid_key(key: str | None) -> bool:
    if not key or not str(key).strip():
        return False
    lowered = str(key).lower()
    return not any(m in lowered for m in _PLACEHOLDER_MARKERS)


def gemini_key_pool(secrets: dict[str, Any] | None = None) -> list[str]:
    """Collect unique Gemini keys in priority order."""
    sec = secrets if secrets is not None else load_secrets()
    ordered: list[str] = []

    def _add(key: str | None) -> None:
        if _is_valid_key(key) and key not in ordered:
            ordered.append(str(key).strip())

    _add(sec.get("GEMINI_API_KEY"))
    _add(sec.get("GEMINI_KEY"))
    multi = sec.get("GEMINI_API_KEYS")
    if isinstance(multi, list):
        for item in multi:
            _add(item if isinstance(item, str) else None)
    elif isinstance(multi, str):
        for part in multi.replace(";", ",").split(","):
            _add(part.strip())

    for idx in range(2, 10):
        _add(sec.get(f"GEMINI_API_KEY_{idx}"))
        _add(sec.get(f"GEMINI_KEY_{idx}"))

    # Environment overrides / supplements
    for env_name in ("GEMINI_API_KEY", "GEMINI_KEY", "GOOGLE_API_KEY"):
        _add(os.environ.get(env_name))

    return ordered


class GeminiKeyRotator:
    """Round-robin Gemini keys with per-key cooldown after failures."""

    def __init__(self, secrets: dict[str, Any] | None = None):
        self._keys = gemini_key_pool(secrets)
        self._index = 0
        self._cooldown_until: dict[str, float] = {}
        self._fail_counts: dict[str, int] = {}

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def keys(self) -> list[str]:
        return list(self._keys)

    def _available_keys(self) -> list[str]:
        now = time.time()
        return [k for k in self._keys if now >= self._cooldown_until.get(k, 0.0)]

    def record_success(self, key: str) -> None:
        self._fail_counts[key] = 0
        self._cooldown_until[key] = 0.0

    def record_failure(self, key: str, error: str) -> None:
        count = self._fail_counts.get(key, 0) + 1
        self._fail_counts[key] = count
        err = error.lower()
        cooldown = 30.0
        if any(f in err for f in ("429", "rate", "quota", "resource exhausted")):
            cooldown = 90.0
        elif "timeout" in err or "timed out" in err:
            cooldown = 45.0
        self._cooldown_until[key] = time.time() + cooldown

    def iter_keys(self) -> list[str]:
        """Round-robin ordering starting at next available key."""
        available = self._available_keys()
        if not available:
            return []
        start = self._index % len(available)
        self._index = (self._index + 1) % max(len(available), 1)
        return available[start:] + available[:start]


def _is_retryable(error: BaseException) -> bool:
    text = str(error).lower()
    if isinstance(error, TimeoutError):
        return True
    if isinstance(error, urllib.error.HTTPError):
        return error.code in (429, 500, 502, 503, 504)
    return any(fragment in text for fragment in _RETRYABLE_FRAGMENTS)


def _gemini_url(key: str) -> str:
    return (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{_GEMINI_MODEL}:generateContent?key={key}"
    )


def _post_json(
    url: str,
    payload: dict[str, Any],
    *,
    timeout: float,
    bearer: str | None = None,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except ssl.SSLError:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))


def _extract_gemini_text(data: dict[str, Any]) -> str:
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _extract_openai_text(data: dict[str, Any]) -> str:
    return data["choices"][0]["message"]["content"]


def gemini_generate(
    prompt_text: str,
    *,
    secrets: dict[str, Any] | None = None,
    rotator: GeminiKeyRotator | None = None,
    timeout: float | None = None,
    retries_per_key: int | None = None,
    log_savings: bool = True,
    call_type: str = "generate",
    savings_metadata: dict[str, Any] | None = None,
    task: str | None = None,
    aspect: str | None = None,
    baseline_prompt_tokens: int | None = None,
    baseline_output_tokens: int | None = None,
    baseline_cost_usd: float | None = None,
    savings_db_path: str | None = None,
) -> tuple[str | None, str | None]:
    """
    Try every Gemini key with retries. Returns (text, None) or (None, error_summary).
    """
    rot = rotator or GeminiKeyRotator(secrets)
    keys = rot.iter_keys()
    if not keys:
        return None, "NO_GEMINI_KEYS: add GEMINI_API_KEY or GEMINI_API_KEYS to ~/aura_secrets.json"

    timeout_sec = timeout if timeout is not None else _CLOUD_TIMEOUT
    per_key_retries = retries_per_key if retries_per_key is not None else _CLOUD_RETRIES_PER_KEY
    errors: list[str] = []
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    t0 = time.time()
    attempts = 0

    for key in keys:
        url = _gemini_url(key)
        masked = f"...{key[-6:]}" if len(key) > 6 else "***"
        for attempt in range(per_key_retries):
            attempts += 1
            try:
                data = _post_json(url, payload, timeout=timeout_sec)
                text = _extract_gemini_text(data).strip()
                rot.record_success(key)
                if log_savings:
                    log_gemini_call(
                        prompt_text=prompt_text,
                        output_text=text,
                        error=None,
                        latency_sec=time.time() - t0,
                        model=_GEMINI_MODEL,
                        call_type=call_type,
                        task=task,
                        aspect=aspect,
                        baseline_prompt_tokens=baseline_prompt_tokens,
                        baseline_output_tokens=baseline_output_tokens,
                        baseline_cost_usd=baseline_cost_usd,
                        metadata={"attempts": attempts, **(savings_metadata or {})},
                        db_path=savings_db_path,
                    )
                return text, None
            except Exception as exc:
                err = f"GEMINI[{masked}] attempt {attempt + 1}: {exc}"
                errors.append(err)
                rot.record_failure(key, str(exc))
                if attempt + 1 < per_key_retries and _is_retryable(exc):
                    time.sleep(1.0 * (attempt + 1))
                    continue
                break

    error = "GEMINI_ROTATION_EXHAUSTED:\n" + "\n".join(errors[-6:])
    if log_savings:
        log_gemini_call(
            prompt_text=prompt_text,
            output_text=None,
            error=error,
            latency_sec=time.time() - t0,
            model=_GEMINI_MODEL,
            call_type=call_type,
            task=task,
            aspect=aspect,
            baseline_prompt_tokens=baseline_prompt_tokens,
            baseline_output_tokens=baseline_output_tokens,
            baseline_cost_usd=baseline_cost_usd,
            metadata={"attempts": attempts, **(savings_metadata or {})},
            db_path=savings_db_path,
        )
    return None, error


def openai_compatible_generate(
    url: str,
    api_key: str,
    payload: dict[str, Any],
    *,
    timeout: float | None = None,
    retries: int = 2,
    log_savings: bool = True,
    call_type: str = "generate",
    savings_metadata: dict[str, Any] | None = None,
    task: str | None = None,
    aspect: str | None = None,
    baseline_prompt_tokens: int | None = None,
    baseline_output_tokens: int | None = None,
    baseline_cost_usd: float | None = None,
    savings_db_path: str | None = None,
) -> tuple[str | None, str | None]:
    timeout_sec = timeout if timeout is not None else _CLOUD_TIMEOUT
    errors: list[str] = []
    t0 = time.time()
    for attempt in range(retries):
        try:
            data = _post_json(url, payload, timeout=timeout_sec, bearer=api_key)
            text = _extract_openai_text(data).strip()
            if log_savings:
                log_openai_compatible_call(
                    url=url,
                    payload=payload,
                    output_text=text,
                    error=None,
                    latency_sec=time.time() - t0,
                    call_type=call_type,
                    task=task,
                    aspect=aspect,
                    baseline_prompt_tokens=baseline_prompt_tokens,
                    baseline_output_tokens=baseline_output_tokens,
                    baseline_cost_usd=baseline_cost_usd,
                    metadata={"attempts": attempt + 1, **(savings_metadata or {})},
                    db_path=savings_db_path,
                )
            return text, None
        except Exception as exc:
            errors.append(str(exc))
            if attempt + 1 < retries and _is_retryable(exc):
                time.sleep(1.0 * (attempt + 1))
                continue
            break
    error = "; ".join(errors)
    if log_savings:
        log_openai_compatible_call(
            url=url,
            payload=payload,
            output_text=None,
            error=error,
            latency_sec=time.time() - t0,
            call_type=call_type,
            task=task,
            aspect=aspect,
            baseline_prompt_tokens=baseline_prompt_tokens,
            baseline_output_tokens=baseline_output_tokens,
            baseline_cost_usd=baseline_cost_usd,
            metadata={"attempts": len(errors), **(savings_metadata or {})},
            db_path=savings_db_path,
        )
    return None, error


# Process-wide rotator (persists cooldown state across calls in one session)
_GLOBAL_GEMINI_ROTATOR: GeminiKeyRotator | None = None


def get_gemini_rotator(secrets: dict[str, Any] | None = None) -> GeminiKeyRotator:
    global _GLOBAL_GEMINI_ROTATOR
    if _GLOBAL_GEMINI_ROTATOR is None:
        _GLOBAL_GEMINI_ROTATOR = GeminiKeyRotator(secrets)
    elif secrets is not None:
        fresh = gemini_key_pool(secrets)
        if fresh and fresh != _GLOBAL_GEMINI_ROTATOR._keys:
            _GLOBAL_GEMINI_ROTATOR = GeminiKeyRotator(secrets)
    return _GLOBAL_GEMINI_ROTATOR
