"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8fa-[Q-SYS:AURA_FUSION]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / User-Owned Deliberation)
DEPENDENCIES: argparse, concurrent.futures, dataclasses, hashlib, json, os, re, time, uuid, aura_api_rotator, aura_codebase_navigator, aura_llm_egress, aura_model_probe_ledger, aura_single_seed_lift, aura_skillweaver, aura_substrate
FUNCTIONS: AuraFusionAgent, AuraPanelOutput, AuraFusionResult, load_fusion_config, build_task_capsule, parse_json_object, AuraFusionCoordinator, main
SYNOPSIS: Aura-native multi-model deliberation: compact task capsule, cached single-seed context lift, SkillWeaver gate, parallel Thinker/Worker/Verifier panel, structured judge synthesis, and phase-hashable run metrics using user-owned provider keys.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any

from aura_api_rotator import load_secrets
from aura_codebase_navigator import refresh_codemap_for_paths
from aura_llm_egress import generate_openai_compatible_payload
from aura_model_probe_ledger import AuraModelProbeLedger
from aura_single_seed_lift import compact_lift_capsule, compile_text_single_seed_lift
from aura_skillweaver import AuraSkillWeaver, gate_fusion_task
from aura_spectral_topology import build_fusion_topology_snapshot
from aura_substrate import REPO_ROOT, estimate_tokens

FUSION_CAPSULE_VERSION = "AURA_FUSION_CAPSULE_V1"
FUSION_LOG_PATH = os.path.join(REPO_ROOT, "Aura_Memory", "aura_fusion_runs.jsonl")
ALLOWED_ROLES = {"THINKER", "WORKER", "VERIFIER", "RESEARCHER", "JUDGE"}
DEFAULT_CONSTRAINTS = ["NO_NEW_DEPS", "NO_FAKE_FILES", "PRESERVE_SIGNATURES", "ASCII_ONLY"]
PLACEHOLDER_MARKERS = ("your_", "paste_", "changeme", "_here", "xxxx")
FUSION_TARGET_EXTENSIONS = ("py", "rs", "js", "ts", "tsx", "jsx", "md", "json", "toml", "yaml", "yml")
DOC_TARGET_EXTENSIONS = {".md", ".txt", ".pdf", ".tex"}


PANEL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "role": {"type": "string"},
        "answer": {"type": "string"},
        "claims": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "missing_info": {"type": "array", "items": {"type": "string"}},
        "recommended_action": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["role", "answer", "claims", "risks", "missing_info", "recommended_action", "confidence"],
}


JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "consensus": {"type": "array", "items": {"type": "string"}},
        "contradictions": {"type": "array", "items": {"type": "string"}},
        "coverage_gaps": {"type": "array", "items": {"type": "string"}},
        "unique_insights": {"type": "array", "items": {"type": "string"}},
        "blind_spots": {"type": "array", "items": {"type": "string"}},
        "winning_approach": {"type": "string"},
        "final_answer": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "should_escalate_to_human": {"type": "boolean"},
    },
    "required": [
        "consensus",
        "contradictions",
        "coverage_gaps",
        "unique_insights",
        "blind_spots",
        "winning_approach",
        "final_answer",
        "confidence",
        "should_escalate_to_human",
    ],
}


@dataclass
class AuraFusionAgent:
    name: str
    role: str
    provider: str
    base_url: str
    api_key_name: str
    model: str
    max_tokens: int = 900
    temperature: float = 0.0
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuraFusionAgent:
        allowed = {field for field in cls.__dataclass_fields__}
        payload = {key: value for key, value in data.items() if key in allowed}
        agent = cls(**payload)
        agent.role = agent.role.upper()
        if agent.role not in ALLOWED_ROLES:
            raise ValueError(f"invalid AuraFusion role '{agent.role}' for {agent.name}")
        return agent


@dataclass
class AuraPanelOutput:
    agent: str
    role: str
    provider: str
    model: str
    ok: bool
    latency_sec: float
    input_tokens_est: int
    output_tokens_est: int
    content: str
    error: str | None = None


@dataclass
class AuraFusionResult:
    ok: bool
    task: str
    mode: str
    phase_hash: str
    panel_outputs: list[dict]
    judge_output: dict
    final_answer: str
    metrics: dict

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _valid_secret(value: Any) -> bool:
    if not value or not str(value).strip():
        return False
    low = str(value).lower()
    return not any(marker in low for marker in PLACEHOLDER_MARKERS)


def _redact_error(error: str | None, secrets: dict[str, Any]) -> str | None:
    if not error:
        return error
    redacted = str(error)
    for value in secrets.values():
        if isinstance(value, str) and len(value) > 6:
            redacted = redacted.replace(value, "***")
    return redacted


def _schema_response_format(name: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "schema": schema,
            "strict": True,
        },
    }


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from raw model text, tolerating fenced JSON."""
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        data = json.loads(raw[start:end + 1])
        if isinstance(data, dict):
            return data
    raise ValueError("model output did not contain a JSON object")


def load_fusion_config(secrets: dict[str, Any] | None = None) -> tuple[list[AuraFusionAgent], AuraFusionAgent | None]:
    """Load AuraFusion panel and judge from aura_secrets-style configuration."""
    cfg = secrets if secrets is not None else load_secrets()
    panel_raw = cfg.get("AURA_FUSION_PANEL") or []
    if not isinstance(panel_raw, list):
        raise ValueError("AURA_FUSION_PANEL must be a list")
    panel = [AuraFusionAgent.from_dict(item) for item in panel_raw if item.get("enabled", True)]
    if len(panel) > 8:
        raise ValueError("AuraFusion supports at most 8 enabled panel agents")
    judge_raw = cfg.get("AURA_FUSION_JUDGE")
    judge = AuraFusionAgent.from_dict(judge_raw) if isinstance(judge_raw, dict) else None
    return panel, judge


def _normalize_repo_path(value: str | None) -> str | None:
    if not value:
        return None
    token = str(value).strip().strip("`\"'")
    token = token.rstrip(".,;:)]}")
    token = token.replace("\\", "/")
    while token.startswith("./"):
        token = token[2:]
    return token.lstrip("/") or None


def _load_codemap(repo_root: str = REPO_ROOT) -> dict[str, Any]:
    path = Path(repo_root) / ".aura" / "CODEMAP.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _iter_codemap_symbols(codemap: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key in ("symbols", "symbol_index", "function_index"):
        symbols = codemap.get(key, {})
        if isinstance(symbols, list):
            items.extend(item for item in symbols if isinstance(item, dict))
            continue
        if not isinstance(symbols, dict):
            continue
        for name, entries in symbols.items():
            if isinstance(entries, dict):
                entries = [entries]
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict):
                    payload = dict(entry)
                    payload.setdefault("name", name)
                    items.append(payload)
    return items


def _codemap_known_paths(codemap: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    coverage = codemap.get("coverage", {})
    if isinstance(coverage, dict):
        for item in coverage.get("all_included_paths_sorted", []) or []:
            normalized = _normalize_repo_path(str(item))
            if normalized:
                paths.add(normalized)
    for entry in codemap.get("files", []) or []:
        if isinstance(entry, dict):
            normalized = _normalize_repo_path(str(entry.get("path", "")))
            if normalized:
                paths.add(normalized)
    for entry in _iter_codemap_symbols(codemap):
        normalized = _normalize_repo_path(str(entry.get("file", "")))
        if normalized:
            paths.add(normalized)
    return paths


def _resolve_codemap_file(candidate: str, codemap: dict[str, Any], repo_root: str = REPO_ROOT) -> str | None:
    normalized = _normalize_repo_path(candidate)
    if not normalized:
        return None
    known_paths = _codemap_known_paths(codemap)
    if normalized in known_paths:
        return normalized
    lowered = normalized.lower()
    for path in known_paths:
        if path.lower() == lowered:
            return path
    basename_matches = [path for path in known_paths if Path(path).name.lower() == Path(normalized).name.lower()]
    if basename_matches:
        return sorted(basename_matches, key=lambda path: (path.count("/"), len(path), path))[0]
    if (Path(repo_root) / normalized).exists():
        return normalized
    return None


def _split_codemap_location(location: str) -> tuple[str | None, int | None]:
    token = str(location or "").strip().strip("`")
    match = re.match(r"^(.+?):(\d+)$", token)
    if match:
        return _normalize_repo_path(match.group(1)), int(match.group(2))
    return _normalize_repo_path(token), None


def _symbol_for_location(codemap: dict[str, Any], target_file: str, line: int | None) -> str | None:
    if line is None:
        return None
    normalized_file = _normalize_repo_path(target_file)
    candidates: list[tuple[int, int, str]] = []
    for entry in _iter_codemap_symbols(codemap):
        if _normalize_repo_path(str(entry.get("file", ""))) != normalized_file:
            continue
        try:
            start = int(entry.get("line", 0) or 0)
            end = int(entry.get("end_line", start) or start)
        except (TypeError, ValueError):
            continue
        if start <= line <= end:
            kind = str(entry.get("kind", ""))
            priority = 0 if "function" in kind else 1
            span = max(0, end - start)
            candidates.append((span, priority, str(entry.get("name", ""))))
    if not candidates:
        return None
    return sorted(candidates)[0][2] or None


def _command_locations(codemap: dict[str, Any], command: str) -> list[str]:
    index = codemap.get("command_index", {})
    if not isinstance(index, dict):
        return []
    locations = index.get(command) or index.get(command.lower()) or index.get(command.upper()) or []
    if isinstance(locations, str):
        return [locations]
    return [str(item) for item in locations if item]


def _resolve_command_target(command: str, codemap: dict[str, Any], repo_root: str = REPO_ROOT) -> dict[str, Any] | None:
    scored: list[tuple[int, int, str, int | None, str | None, str]] = []
    for idx, location in enumerate(_command_locations(codemap, command)):
        path, line = _split_codemap_location(location)
        target_file = _resolve_codemap_file(path or "", codemap, repo_root=repo_root)
        if not target_file:
            continue
        suffix = Path(target_file).suffix.lower()
        score = 0
        if suffix == ".py":
            score += 100
        elif suffix in {".rs", ".js", ".ts", ".tsx", ".jsx"}:
            score += 80
        elif suffix in DOC_TARGET_EXTENSIONS:
            score -= 100
        else:
            score += 20
        if Path(target_file).name == "aura_node.py":
            score -= 20
        elif suffix == ".py":
            score += 20
        symbol = _symbol_for_location(codemap, target_file, line)
        if symbol:
            score += 5
        scored.append((score, -idx, target_file, line, symbol, location))
    if not scored:
        return None
    score, _order, target_file, line, symbol, location = sorted(scored, reverse=True)[0]
    return {
        "source": "command_mention",
        "matched": command,
        "target_file": target_file,
        "target_symbol": symbol,
        "line": line,
        "location": location,
        "score": score,
    }


def infer_fusion_target(task: str, *, repo_root: str = REPO_ROOT, codemap: dict[str, Any] | None = None) -> dict[str, Any]:
    """Infer a CODEMAP-grounded Fusion target from file or REPL command mentions."""
    codemap_data = codemap if codemap is not None else _load_codemap(repo_root)
    if not codemap_data:
        return {"source": None, "target_file": None, "target_symbol": None}

    extensions = "|".join(re.escape(ext) for ext in FUSION_TARGET_EXTENSIONS)
    file_pattern = rf"(?<![\w./\\-])[\w./\\-]+\.({extensions})(?![\w./\\-])"
    for match in re.finditer(file_pattern, task or "", flags=re.IGNORECASE):
        token = match.group(0)
        target_file = _resolve_codemap_file(token, codemap_data, repo_root=repo_root)
        if target_file:
            return {
                "source": "file_mention",
                "matched": token,
                "target_file": target_file,
                "target_symbol": None,
            }

    for command in re.findall(r"(?<!\w)![A-Za-z_][\w-]*", task or ""):
        if command.lower() == "!fusion":
            continue
        resolved = _resolve_command_target(command, codemap_data, repo_root=repo_root)
        if resolved:
            return resolved

    return {"source": None, "target_file": None, "target_symbol": None}


def _refresh_codemap_targets(repo_root: str, target_files: list[str | None]) -> dict[str, Any] | None:
    paths = sorted({
        _normalize_repo_path(path) or ""
        for path in target_files
        if _normalize_repo_path(path)
    })
    if not paths:
        return None
    try:
        payload = refresh_codemap_for_paths(paths, root=Path(repo_root), include_topology=True)
    except Exception as exc:
        return {"ok": False, "paths": paths, "error": type(exc).__name__}
    return {"ok": payload is not None, "paths": paths}


def _codemap_epoch(repo_root: str = REPO_ROOT) -> str:
    path = os.path.join(repo_root, ".aura", "CODEMAP.json")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return "unix:{generated_at_unix}|files:{included_file_count}".format(
            generated_at_unix=data.get("generated_at_unix", "unknown"),
            included_file_count=data.get("coverage", {}).get("included_file_count", "unknown"),
        )
    except Exception:
        return "unknown"


def _hash_payload(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


def _build_single_seed_context_lift(capsule: dict[str, Any]) -> dict[str, Any]:
    topology_snapshot = capsule.get("topology_snapshot")
    blocks = [
        str(capsule.get("task", "")),
        str(capsule.get("target_file", "")),
        str(capsule.get("target_symbol", "")),
        str(capsule.get("output_mode", "")),
        " ".join(str(item) for item in capsule.get("constraints", ()) or ()),
    ]
    if topology_snapshot:
        blocks.append(json.dumps(topology_snapshot, sort_keys=True, default=str))
    lift = compile_text_single_seed_lift(
        f"fusion:{capsule.get('target_file') or 'repo'}:{capsule.get('target_symbol') or ''}",
        blocks,
        top_trace_count=4,
    )
    profile = lift.profile.to_jsonable()
    profile["slot_capsule"] = compact_lift_capsule(lift.profile, limit=260)
    return profile


def build_task_capsule(
    task: str,
    *,
    target_file: str | None = None,
    target_symbol: str | None = None,
    output_mode: str = "TEXT",
    constraints: list[str] | None = None,
    codemap_epoch: str | None = None,
    repo_root: str = REPO_ROOT,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    capsule = {
        "capsule_version": FUSION_CAPSULE_VERSION,
        "task": task,
        "target_file": target_file,
        "target_symbol": target_symbol,
        "output_mode": output_mode.upper(),
        "constraints": constraints or list(DEFAULT_CONSTRAINTS),
        "codemap_epoch": codemap_epoch or _codemap_epoch(),
    }
    topology_snapshot = build_fusion_topology_snapshot(
        repo_root=repo_root,
        target_file=target_file,
        target_symbol=target_symbol,
    )
    if topology_snapshot is not None:
        capsule["topology_snapshot"] = topology_snapshot
    if extra:
        capsule.update(extra)
    capsule["single_seed_context_lift"] = _build_single_seed_context_lift(capsule)
    capsule["phase_hash"] = _hash_payload(capsule)
    return capsule


class AuraFusionCoordinator:
    def __init__(
        self,
        *,
        repo_root: str = REPO_ROOT,
        secrets: dict[str, Any] | None = None,
        panel: list[AuraFusionAgent] | None = None,
        judge: AuraFusionAgent | None = None,
        mock: bool = False,
        log_path: str = FUSION_LOG_PATH,
        caller: Callable[..., tuple[str | None, str | None, float, bool]] | None = None,
        probe_ledger: AuraModelProbeLedger | None = None,
    ):
        self.repo_root = repo_root
        self.secrets = secrets if secrets is not None else load_secrets()
        loaded_panel, loaded_judge = load_fusion_config(self.secrets)
        self.panel = panel if panel is not None else loaded_panel
        self.judge = judge if judge is not None else loaded_judge
        self.mock = mock
        self.log_path = log_path
        self.caller = caller or generate_openai_compatible_payload
        self.probe_ledger = probe_ledger or AuraModelProbeLedger()

    def _api_key_for(self, agent: AuraFusionAgent) -> str:
        if self.mock:
            return "mock"
        value = self.secrets.get(agent.api_key_name)
        if not _valid_secret(value):
            raise RuntimeError(f"missing usable API key named {agent.api_key_name} for agent {agent.name}")
        return str(value)

    def _rank_panel(self, task: str) -> list[AuraFusionAgent]:
        return sorted(
            [agent for agent in self.panel if agent.enabled],
            key=lambda agent: self.probe_ledger.score_agent(agent.provider, agent.model, agent.role, task),
            reverse=True,
        )

    def _mock_panel(self, agent: AuraFusionAgent, capsule: dict[str, Any]) -> tuple[str, None, float, bool]:
        content = {
            "role": agent.role,
            "answer": f"{agent.role} assessment for: {capsule['task']}",
            "claims": ["Capsule is compact", "CODEMAP epoch is preserved"],
            "risks": ["Requires configured external API keys for live execution"],
            "missing_info": [] if capsule.get("target_file") else ["target_file absent for mutation tasks"],
            "recommended_action": "Use judge synthesis before applying any code mutation.",
            "confidence": 0.72,
        }
        return json.dumps(content, sort_keys=True), None, 0.001, True

    def _mock_judge(self, capsule: dict[str, Any], panel_outputs: list[dict]) -> tuple[str, None, float, bool]:
        content = {
            "consensus": ["Panel agrees on compact capsule routing and structured output."],
            "contradictions": [],
            "coverage_gaps": [p["agent"] for p in panel_outputs if not p.get("ok")],
            "unique_insights": ["Mock mode validates orchestration without provider calls."],
            "blind_spots": [],
            "winning_approach": "Proceed with human-gated JSON plan review.",
            "final_answer": f"AuraFusion mock synthesis complete for: {capsule['task']}",
            "confidence": 0.74,
            "should_escalate_to_human": bool(capsule.get("target_file")),
        }
        return json.dumps(content, sort_keys=True), None, 0.001, True

    def _call_agent(
        self,
        agent: AuraFusionAgent,
        capsule: dict[str, Any],
        *,
        schema_name: str,
        schema: dict[str, Any],
        panel_outputs: list[dict] | None = None,
    ) -> tuple[str | None, str | None, float, bool, int]:
        if self.mock and agent.role != "JUDGE":
            text, err, latency, used_schema = self._mock_panel(agent, capsule)
            return text, err, latency, used_schema, estimate_tokens(json.dumps(capsule))
        if self.mock and agent.role == "JUDGE":
            text, err, latency, used_schema = self._mock_judge(capsule, panel_outputs or [])
            return text, err, latency, used_schema, estimate_tokens(json.dumps(capsule))

        api_key = self._api_key_for(agent)
        role_hint = (
            f"You are AuraFusion {agent.role}. Return only strict JSON matching the provided schema. "
            "Do not emit markdown. Preserve Aura constraints and never fabricate file paths."
        )
        payload = {
            "capsule": capsule,
            "agent": {"name": agent.name, "role": agent.role, "provider": agent.provider, "model": agent.model},
        }
        if panel_outputs is not None:
            payload["panel_outputs"] = panel_outputs
        messages = [
            {"role": "system", "content": role_hint},
            {"role": "user", "content": json.dumps(payload, sort_keys=True, default=str)},
        ]
        input_est = estimate_tokens(messages[0]["content"] + messages[1]["content"])
        text, err, latency, used_schema = self.caller(
            provider=agent.provider,
            base_url=agent.base_url,
            api_key=api_key,
            model=agent.model,
            messages=messages,
            max_tokens=agent.max_tokens,
            temperature=agent.temperature,
            response_format=_schema_response_format(schema_name, schema),
        )
        return text, _redact_error(err, self.secrets), latency, used_schema, input_est

    def _run_panel_agent(self, agent: AuraFusionAgent, capsule: dict[str, Any]) -> dict[str, Any]:
        try:
            text, err, latency, used_schema, input_est = self._call_agent(
                agent, capsule, schema_name="aura_panel_output", schema=PANEL_SCHEMA
            )
        except Exception as exc:
            text, err, latency, used_schema, input_est = None, _redact_error(str(exc), self.secrets), 0.0, False, 0
        parsed: dict[str, Any] = {}
        parse_error = None
        if text:
            try:
                parsed = parse_json_object(text)
            except Exception as exc:
                parse_error = str(exc)
        ok = bool(text and not err and not parse_error and all(field in parsed for field in PANEL_SCHEMA["required"]))
        output = AuraPanelOutput(
            agent=agent.name,
            role=agent.role,
            provider=agent.provider,
            model=agent.model,
            ok=ok,
            latency_sec=round(latency, 3),
            input_tokens_est=input_est,
            output_tokens_est=estimate_tokens(text or ""),
            content=text or "",
            error=err or parse_error,
        )
        data = asdict(output)
        data["parsed"] = parsed
        data["used_response_schema"] = used_schema
        return data

    def _dispatch_panel(self, task: str, capsule: dict[str, Any]) -> list[dict[str, Any]]:
        panel = self._rank_panel(task)
        if not panel and not self.mock:
            raise RuntimeError("AURA_FUSION_PANEL is empty; configure aura_secrets.json or run with --mock")
        if not panel and self.mock:
            panel = [
                AuraFusionAgent("mock_thinker", "THINKER", "mock", "mock", "MOCK_API_KEY", "mock-thinker"),
                AuraFusionAgent("mock_worker", "WORKER", "mock", "mock", "MOCK_API_KEY", "mock-worker"),
                AuraFusionAgent("mock_verifier", "VERIFIER", "mock", "mock", "MOCK_API_KEY", "mock-verifier"),
            ]

        outputs: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=min(8, max(1, len(panel)))) as pool:
            futures = {pool.submit(self._run_panel_agent, agent, capsule): agent.name for agent in panel}
            for future in as_completed(futures):
                outputs.append(future.result())
        return sorted(outputs, key=lambda item: item["agent"])

    def _run_judge(self, capsule: dict[str, Any], panel_outputs: list[dict[str, Any]]) -> dict[str, Any]:
        judge = self.judge
        if judge is None and self.mock:
            judge = AuraFusionAgent("mock_judge", "JUDGE", "mock", "mock", "MOCK_API_KEY", "mock-judge")
        if judge is None:
            raise RuntimeError("AURA_FUSION_JUDGE is not configured")
        if judge.role != "JUDGE":
            judge = AuraFusionAgent(**{**asdict(judge), "role": "JUDGE"})
        text, err, latency, used_schema, input_est = self._call_agent(
            judge,
            capsule,
            schema_name="aura_judge_output",
            schema=JUDGE_SCHEMA,
            panel_outputs=panel_outputs,
        )
        parsed: dict[str, Any] = {}
        parse_error = None
        if text:
            try:
                parsed = parse_json_object(text)
            except Exception as exc:
                parse_error = str(exc)
        ok = bool(text and not err and not parse_error and all(field in parsed for field in JUDGE_SCHEMA["required"]))
        return {
            "agent": judge.name,
            "provider": judge.provider,
            "model": judge.model,
            "ok": ok,
            "latency_sec": round(latency, 3),
            "input_tokens_est": input_est,
            "output_tokens_est": estimate_tokens(text or ""),
            "content": text or "",
            "parsed": parsed,
            "error": err or parse_error,
            "used_response_schema": used_schema,
        }

    def _append_log(self, result: AuraFusionResult) -> None:
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(result.to_dict(), sort_keys=True, default=str) + "\n")

    def run(
        self,
        task: str,
        *,
        mode: str = "fusion",
        target_file: str | None = None,
        target_symbol: str | None = None,
        output_mode: str = "TEXT",
        constraints: list[str] | None = None,
        extra_capsule: dict[str, Any] | None = None,
    ) -> AuraFusionResult:
        target_inference: dict[str, Any] = {"source": None, "target_file": target_file, "target_symbol": target_symbol}
        codemap_refreshes: list[dict[str, Any]] = []
        if not target_file:
            commands = [
                command
                for command in re.findall(r"(?<!\w)![A-Za-z_][\w-]*", task or "")
                if command.lower() != "!fusion"
            ]
            if commands:
                preflight_targets = ["aura_node.py"]
                codemap = _load_codemap(self.repo_root)
                for command in commands:
                    for location in _command_locations(codemap, command):
                        path, _line = _split_codemap_location(location)
                        if path:
                            preflight_targets.append(path)
                refresh = _refresh_codemap_targets(self.repo_root, preflight_targets)
                if refresh:
                    refresh["phase"] = "command_index_preflight"
                    codemap_refreshes.append(refresh)
            target_inference = infer_fusion_target(task, repo_root=self.repo_root)
            target_file = target_inference.get("target_file") or None
            if not target_symbol:
                target_symbol = target_inference.get("target_symbol") or None
        refresh = _refresh_codemap_targets(self.repo_root, [target_file])
        if refresh:
            refresh["phase"] = "target_branch_preflight"
            codemap_refreshes.append(refresh)

        capsule_extra = dict(extra_capsule or {})
        if target_inference.get("source"):
            capsule_extra["target_inference"] = target_inference
        if codemap_refreshes:
            capsule_extra["codemap_refreshes"] = codemap_refreshes

        capsule = build_task_capsule(
            task,
            target_file=target_file,
            target_symbol=target_symbol,
            output_mode=output_mode,
            constraints=constraints,
            codemap_epoch=_codemap_epoch(self.repo_root),
            repo_root=self.repo_root,
            extra=capsule_extra,
        )
        gate = gate_fusion_task(task, capsule, AuraSkillWeaver(repo_root=self.repo_root).skills)
        if not gate["allowed"]:
            result = AuraFusionResult(
                ok=False,
                task=task,
                mode=mode,
                phase_hash=capsule["phase_hash"],
                panel_outputs=[],
                judge_output={},
                final_answer=gate["reason"],
                metrics={
                    "gate": gate,
                    "panel_count": 0,
                    "estimated_cost_usd": 0.0,
                    "target_file": target_file,
                    "target_symbol": target_symbol,
                    "target_inference": target_inference,
                    "codemap_refreshes": codemap_refreshes,
                    "log_path": self.log_path,
                },
            )
            self._append_log(result)
            return result

        t0 = time.time()
        try:
            panel_outputs = self._dispatch_panel(task, capsule)
            judge_output = self._run_judge(capsule, panel_outputs)
            judge_parsed = judge_output.get("parsed") or {}
            ok = bool(panel_outputs and judge_output.get("ok"))
            final_answer = judge_parsed.get("final_answer") or judge_output.get("content") or "AuraFusion judge produced no final answer."
            metrics = {
                "gate": gate,
                "panel_count": len(panel_outputs),
                "panel_ok_count": sum(1 for item in panel_outputs if item.get("ok")),
                "schema_success_count": sum(1 for item in panel_outputs if item.get("used_response_schema")),
                "input_tokens_est": sum(item.get("input_tokens_est", 0) for item in panel_outputs) + judge_output.get("input_tokens_est", 0),
                "output_tokens_est": sum(item.get("output_tokens_est", 0) for item in panel_outputs) + judge_output.get("output_tokens_est", 0),
                "latency_sec": round(time.time() - t0, 3),
                "estimated_cost_usd": 0.0,
                "target_file": target_file,
                "target_symbol": target_symbol,
                "target_inference": target_inference,
                "codemap_refreshes": codemap_refreshes,
                "log_path": self.log_path,
            }
        except Exception as exc:
            panel_outputs = []
            judge_output = {}
            ok = False
            final_answer = _redact_error(str(exc), self.secrets) or "AuraFusion failed"
            metrics = {
                "gate": gate,
                "panel_count": 0,
                "latency_sec": round(time.time() - t0, 3),
                "estimated_cost_usd": 0.0,
                "error": final_answer,
                "target_file": target_file,
                "target_symbol": target_symbol,
                "target_inference": target_inference,
                "codemap_refreshes": codemap_refreshes,
                "log_path": self.log_path,
            }

        result = AuraFusionResult(
            ok=ok,
            task=task,
            mode=mode,
            phase_hash=capsule["phase_hash"],
            panel_outputs=panel_outputs,
            judge_output=judge_output,
            final_answer=final_answer,
            metrics=metrics,
        )
        self._append_log(result)
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AuraFusion native panel-plus-judge deliberation")
    parser.add_argument("task", nargs="+", help="Task text. Quote multi-word tasks.")
    parser.add_argument("--target-file", default=None)
    parser.add_argument("--target-symbol", default=None)
    parser.add_argument("--output-mode", default="TEXT")
    parser.add_argument("--mock", action="store_true", help="Run offline mock panel/judge without provider calls")
    parser.add_argument("--json", action="store_true", help="Print full structured result")
    args = parser.parse_args(argv)

    task = " ".join(args.task).strip()
    coordinator = AuraFusionCoordinator(mock=args.mock)
    result = coordinator.run(
        task,
        target_file=args.target_file,
        target_symbol=args.target_symbol,
        output_mode=args.output_mode,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True, default=str))
    else:
        status = "[+]" if result.ok else "[-]"
        print(f"{status} AuraFusion phase={result.phase_hash} panel={result.metrics.get('panel_count', 0)}")
        if result.metrics.get("target_file"):
            symbol = result.metrics.get("target_symbol")
            suffix = f"::{symbol}" if symbol else ""
            print(f"[target] {result.metrics['target_file']}{suffix}")
        print(result.final_answer)
        print(f"[log] {result.metrics.get('log_path', FUSION_LOG_PATH)}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
