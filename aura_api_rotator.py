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
Provider-neutral API key rotation with retries and provider fallback.

Every provider may declare a primary key, plural key list, and numbered backups
in ~/aura_secrets.json. Gemini keeps its historical aliases for compatibility.
"""

import json
import os
from pathlib import Path
import ssl
import sys
import threading
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


def _with_runtime_defaults(secrets: dict[str, Any]) -> dict[str, Any]:
    """Attach non-secret provider defaults without overriding explicit config."""
    cfg = dict(secrets)
    if cfg.get("AURA_FUSION_PANEL") and cfg.get("AURA_FUSION_JUDGE"):
        return cfg
    try:
        from aura_provider_registry import ProviderRegistry

        registry = ProviderRegistry()

        def agent(role: str, model_role: str, *, skip: tuple[str, ...] = ()) -> dict[str, Any] | None:
            for provider in registry.provider_order(model_role):
                if provider in skip:
                    continue
                provider_cfg = registry.get_provider_config(provider) or {}
                if str(provider_cfg.get("api") or "openai") != "openai":
                    continue
                names = [provider_cfg.get("api_key_env"), *provider_cfg.get("api_key_aliases", [])]
                if not provider_key_pool(provider, cfg, key_names=[str(name) for name in names if name]):
                    continue
                return {
                    "name": f"auto_{role.lower()}_{provider}",
                    "role": role,
                    "provider": provider,
                    "base_url": str(provider_cfg["base_url"]),
                    "api_key_name": str(provider_cfg["api_key_env"]),
                    "model": registry.resolve_model(provider, model_role),
                    "max_tokens": 1200 if role == "JUDGE" else 900,
                    "temperature": 0.0,
                    "enabled": True,
                }
            return None

        if not cfg.get("AURA_FUSION_PANEL"):
            thinker = agent("THINKER", "premium")
            worker = agent("WORKER", "cheap_builder")
            verifier = agent(
                "VERIFIER",
                "shadow",
                skip=(str(worker.get("provider")),) if worker else (),
            )
            cfg["AURA_FUSION_PANEL"] = [item for item in (thinker, worker, verifier) if item]
        if not cfg.get("AURA_FUSION_JUDGE"):
            cfg["AURA_FUSION_JUDGE"] = agent("JUDGE", "premium")
    except (ImportError, KeyError, TypeError, ValueError):
        # Secrets loading must remain non-fatal; explicit Fusion configuration still works.
        pass
    return cfg


def load_secrets(path: Path | str | None = None) -> dict[str, Any]:
    if path is not None:
        secrets_path = Path(path)
        if not secrets_path.exists():
            return {}
        return _with_runtime_defaults(_load_secret_file(secrets_path))
    for secrets_path in _secrets_search_paths():
        if secrets_path.exists():
            return _with_runtime_defaults(_load_secret_file(secrets_path))
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

_PLACEHOLDER_MARKERS = (
    "your_actual_", "your_new_key", "your_", "paste_", "changeme",
    "your_primary_", "replace_me", "_here", "xxxx", "example",
)


def _is_valid_key(key: str | None) -> bool:
    if not key or not str(key).strip():
        return False
    lowered = str(key).lower()
    return not any(m in lowered for m in _PLACEHOLDER_MARKERS)


def _append_key_value(ordered: list[str], value: Any) -> None:
    if isinstance(value, (list, tuple)):
        for item in value:
            _append_key_value(ordered, item)
        return
    if isinstance(value, str) and ("," in value or ";" in value):
        for item in value.replace(";", ",").split(","):
            _append_key_value(ordered, item.strip())
        return
    key = str(value or "").strip()
    if _is_valid_key(key) and key not in ordered:
        ordered.append(key)


def _provider_key_names(provider_id: str, key_names: list[str] | tuple[str, ...] | None = None) -> list[str]:
    provider = str(provider_id or "").strip().lower()
    ordered = [str(name).strip() for name in (key_names or ()) if str(name).strip()]
    defaults = {
        "gemini": ["GEMINI_API_KEY", "GEMINI_KEY", "GOOGLE_API_KEY"],
        "xai": ["XAI_API_KEY", "GROK_API_KEY"],
        "openrouter": ["OPEN_ROUTER_API_KEY", "OPENROUTER_API_KEY"],
        "github": ["GITHUB_TOKEN", "GITHUB_MODELS_API_KEY"],
    }.get(provider, [f"{provider.upper()}_API_KEY"] if provider else [])
    for name in defaults:
        if name not in ordered:
            ordered.append(name)
    return ordered


def provider_key_pool(
    provider_id: str,
    secrets: dict[str, Any] | None = None,
    *,
    key_names: list[str] | tuple[str, ...] | None = None,
) -> list[str]:
    """Collect every valid key for one provider in deterministic priority order.

    Accepted shapes include ``FOO_API_KEY``, ``FOO_API_KEYS`` (list or
    comma-separated string), and numbered backups such as
    ``FOO_API_KEY_2``. Environment values supplement the secrets file.
    """
    sec = secrets if secrets is not None else load_secrets()
    ordered: list[str] = []
    roots = _provider_key_names(provider_id, key_names)

    for root in roots:
        variants = [root]
        if root.endswith("_API_KEY"):
            variants.append(root + "S")
        elif root.endswith("_KEY"):
            variants.append(root + "S")
        for name in variants:
            _append_key_value(ordered, sec.get(name))
            _append_key_value(ordered, os.environ.get(name))

        numbered: list[tuple[int, str]] = []
        prefix = root + "_"
        for name in set(sec) | set(os.environ):
            if not str(name).startswith(prefix):
                continue
            suffix = str(name)[len(prefix):]
            if suffix.isdigit():
                numbered.append((int(suffix), str(name)))
        for _index, name in sorted(numbered):
            _append_key_value(ordered, sec.get(name))
            _append_key_value(ordered, os.environ.get(name))

    return ordered


def gemini_key_pool(secrets: dict[str, Any] | None = None) -> list[str]:
    """Collect unique Gemini keys in priority order (legacy helper)."""
    return provider_key_pool("gemini", secrets)


class ProviderKeyRotator:
    """Round-robin provider keys with per-key cooldown after failures."""

    def __init__(
        self,
        provider_id: str,
        secrets: dict[str, Any] | None = None,
        *,
        key_names: list[str] | tuple[str, ...] | None = None,
        keys: list[str] | tuple[str, ...] | None = None,
    ):
        self.provider_id = str(provider_id or "unknown").lower()
        if keys is None:
            self._keys = provider_key_pool(self.provider_id, secrets, key_names=key_names)
        else:
            self._keys = []
            _append_key_value(self._keys, list(keys))
        self._index = 0
        self._cooldown_until: dict[str, float] = {}
        self._fail_counts: dict[str, int] = {}
        self._lock = threading.Lock()

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def keys(self) -> list[str]:
        return list(self._keys)

    def _available_keys(self) -> list[str]:
        now = time.time()
        return [key for key in self._keys if now >= self._cooldown_until.get(key, 0.0)]

    def record_success(self, key: str) -> None:
        with self._lock:
            self._fail_counts[key] = 0
            self._cooldown_until[key] = 0.0

    def record_failure(self, key: str, error: str) -> None:
        with self._lock:
            count = self._fail_counts.get(key, 0) + 1
            self._fail_counts[key] = count
            err = str(error or "").lower()
            cooldown = 30.0
            if any(fragment in err for fragment in ("429", "rate", "quota", "resource exhausted")):
                cooldown = 90.0
            elif "timeout" in err or "timed out" in err:
                cooldown = 45.0
            self._cooldown_until[key] = time.time() + cooldown

    def iter_keys(self) -> list[str]:
        """Return round-robin ordering starting at the next available key."""
        with self._lock:
            available = self._available_keys()
            if not available:
                return []
            start = self._index % len(available)
            self._index = (self._index + 1) % max(len(available), 1)
            return available[start:] + available[:start]


class GeminiKeyRotator(ProviderKeyRotator):
    """Compatibility wrapper around the generic provider rotator."""

    def __init__(self, secrets: dict[str, Any] | None = None):
        super().__init__("gemini", secrets)


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


# Process-wide rotators preserve cooldown state across calls in one session.
_GLOBAL_PROVIDER_ROTATORS: dict[str, ProviderKeyRotator] = {}


def get_provider_rotator(
    provider_id: str,
    secrets: dict[str, Any] | None = None,
    *,
    key_names: list[str] | tuple[str, ...] | None = None,
    keys: list[str] | tuple[str, ...] | None = None,
) -> ProviderKeyRotator:
    provider = str(provider_id or "unknown").lower()
    if keys is None:
        fresh = provider_key_pool(provider, secrets, key_names=key_names)
    else:
        fresh = []
        _append_key_value(fresh, list(keys))
    current = _GLOBAL_PROVIDER_ROTATORS.get(provider)
    if current is None or fresh != current._keys:
        current = ProviderKeyRotator(provider, keys=fresh)
        _GLOBAL_PROVIDER_ROTATORS[provider] = current
    return current


def get_gemini_rotator(secrets: dict[str, Any] | None = None) -> ProviderKeyRotator:
    return get_provider_rotator("gemini", secrets)
