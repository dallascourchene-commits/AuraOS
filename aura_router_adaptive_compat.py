"""Compatibility helpers connecting ``aura_router.AutoRouter`` to Model Cognome.

The public legacy router remains the default.  Callers opt into SHADOW or
PAIRED_LIVE explicitly, or set ``AURA_ADAPTIVE_ROUTER_MODE``.  This module keeps
all new imports lazy so existing calibration, mock, savings, and CLI workflows
retain their historical dependency surface.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from aura_model_cognome import stable_digest

LEGACY = "LEGACY"
SHADOW = "SHADOW"
PAIRED_LIVE = "PAIRED_LIVE"
MODE_ENV = "AURA_ADAPTIVE_ROUTER_MODE"
_ALLOWED_MODES = frozenset({LEGACY, SHADOW, PAIRED_LIVE})


def resolve_mode(value: str | None = None) -> str:
    mode = str(value or os.environ.get(MODE_ENV) or LEGACY).strip().upper()
    if mode not in _ALLOWED_MODES:
        raise ValueError(f"unknown router mode: {mode}")
    return mode


def load_authorization(value: Any) -> Any:
    if value is None or hasattr(value, "validate_for"):
        return value
    from aura_model_cognome_execution_auth import ExecutionAuthorization

    if isinstance(value, Mapping):
        return ExecutionAuthorization.from_mapping(value)
    path = Path(str(value)).expanduser().resolve()
    return ExecutionAuthorization.from_mapping(json.loads(path.read_text(encoding="utf-8")))


def _task_objective(task: Any) -> str:
    return (
        f"{task.human_prompt}\n\n"
        f"Target file: {task.target_file}\n"
        f"Target symbol: {task.target_func}\n"
        f"Required output format: {task.output_format}\n"
        "Respect exact source hashes, preserve signatures, and add no undeclared dependencies."
    )


def _task_verifier(auto_router: Any, task: Any):
    from aura_proxy_benchmark import QualityScorer, _repo_py_files
    from aura_substrate import existing_import_roots, sanitize_code

    original = auto_router.selector.read(task.target_file)
    scorer = QualityScorer(
        _repo_py_files(),
        existing_import_roots(original),
        original,
        target_func=task.target_func,
    )

    def verify(text: str | None, error: str | None, **_kwargs: Any) -> dict[str, Any]:
        if error or not text:
            return {
                "passed": False,
                "format_valid": False,
                "tests_passed": None,
                "tests_failed": None,
                "failure_class": "MODEL_CALL_FAILED",
            }
        clean, _replacements = sanitize_code(text)
        quality = scorer.score(clean, task)
        passed = all(quality["checks"].get(name) for name in auto_router._SAFETY_CHECKS)
        return {
            "passed": passed,
            "format_valid": bool(quality["checks"].get("format_ok")),
            "tests_passed": None,
            "tests_failed": None,
            "failure_class": "" if passed else "QUALITY_SCORER_REJECTED",
            "quality_score": quality["score"],
            "checks": quality["checks"],
            "notes": quality["notes"],
        }

    return verify, original


def _router(
    auto_router: Any,
    *,
    verifier: Any,
    fusion_required: bool = False,
    mock: bool = False,
):
    from aura_adaptive_fusion import AdaptiveFusionPanelExecutor
    from aura_adaptive_model_executor import AdaptiveModelExecutor
    from aura_adaptive_model_router import AdaptiveModelRouter
    from aura_shadow_model_router import ShadowRoutingPolicy

    policy = None
    if fusion_required:
        policy = ShadowRoutingPolicy(
            high_risk_direct_min_success=1.0,
            panel_uncertainty_threshold=0.0,
            panel_size=3,
            allow_panel=True,
        )

    def executor_factory(router: AdaptiveModelRouter):
        panel_executor = AdaptiveFusionPanelExecutor(
            repo_root=auto_router.root,
            store=router.store,
            mock=mock,
        )
        return AdaptiveModelExecutor(
            router=router,
            verifier=verifier,
            panel_executor=panel_executor,
        )

    return AdaptiveModelRouter(
        repo_root=auto_router.root,
        policy=policy,
        executor_factory=executor_factory,
    )


def route_test_case(
    auto_router: Any,
    task: Any,
    *,
    routing_mode: str,
    purpose_digest: str,
    authorization: Any = None,
    forced_model: str | None = None,
    data_egress_allowed: bool = False,
    mock: bool = False,
) -> dict[str, Any]:
    mode = resolve_mode(routing_mode)
    if mode == LEGACY:
        raise ValueError("route_test_case is only for SHADOW or PAIRED_LIVE")
    if not str(purpose_digest or "").strip():
        raise ValueError("adaptive routing requires purpose_digest")
    if mode == PAIRED_LIVE and mock:
        raise ValueError("PAIRED_LIVE cannot use the legacy mock egress")
    verifier, original = _task_verifier(auto_router, task)
    router = _router(auto_router, verifier=verifier, mock=mock)
    try:
        result = router.execute(
            _task_objective(task),
            purpose_digest=purpose_digest,
            execution_mode=mode,
            authorization=load_authorization(authorization),
            target_files=[task.target_file, *list(task.extra_context_files or [])],
            target_symbols=[task.target_func],
            forced_model=forced_model,
            task_fields={
                "task_family": task.task_type,
                "domain": "code",
                "artifact": task.target_file,
                "action": "patch",
                "scope": task.target_func,
                "risk": "LOW",
                "exactness_required": "EXACT_SOURCE_HASHES",
                "required_tools": (),
                "verifier_id": "aura_quality_scorer_v1",
                "data_egress_allowed": bool(data_egress_allowed),
            },
        )
    finally:
        router.close()
    result["router_mode"] = mode
    result["legacy_default"] = False
    result["task_key"] = task.key
    result["ok"] = result.get("status") in {"PROPOSED", "EXECUTED"}
    if result.get("executed") and result.get("output"):
        result["model_output"] = result["output"]
        result["artifact"] = auto_router._expand(str(result["output"]), task, original)
        result["accepted"] = bool(result.get("verified"))
    return result


def route_fusion_text(
    auto_router: Any,
    task_text: str,
    *,
    routing_mode: str,
    purpose_digest: str,
    authorization: Any = None,
    target_file: str | None = None,
    target_symbol: str | None = None,
    data_egress_allowed: bool = False,
    mock: bool = False,
) -> dict[str, Any]:
    mode = resolve_mode(routing_mode)
    if mode == LEGACY:
        raise ValueError("route_fusion_text is only for SHADOW or PAIRED_LIVE")
    if not str(purpose_digest or "").strip():
        raise ValueError("adaptive Fusion requires purpose_digest")
    if mode == PAIRED_LIVE and mock:
        raise ValueError("PAIRED_LIVE cannot use mock Fusion")
    router = _router(
        auto_router,
        verifier=None,
        fusion_required=True,
        mock=mock,
    )
    try:
        result = router.execute(
            task_text,
            purpose_digest=purpose_digest,
            execution_mode=mode,
            authorization=load_authorization(authorization),
            target_files=[target_file] if target_file else None,
            target_symbols=[target_symbol] if target_symbol else None,
            task_fields={
                "task_family": "fusion",
                "domain": "code" if target_file else "analysis",
                "artifact": target_file or "",
                "action": "panel_deliberation",
                "scope": target_symbol or "",
                "risk": "HIGH",
                "exactness_required": "DIVERSE_PANEL_AND_JUDGE",
                "verifier_id": "aura_fusion_judge_schema_v1",
                "data_egress_allowed": bool(data_egress_allowed),
            },
        )
    finally:
        router.close()
    result["router_mode"] = mode
    result["legacy_default"] = False
    result["ok"] = result.get("status") in {"PROPOSED", "EXECUTED"}
    return result


def purpose_digest_for_text(text: str) -> str:
    """Explicit helper for callers that choose to bind purpose to supplied text."""
    return stable_digest({"purpose": str(text or "").strip()})
