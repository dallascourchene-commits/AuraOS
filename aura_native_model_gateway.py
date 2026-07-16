"""Native Aura model gateway backed by the Model Cognome adaptive router.

All native provider selection enters through ``AdaptiveModelRouter``. The gateway
does not choose a hard-coded vendor. It asks Aura's evidence store and policy
layer to select ZERO_MODEL, DIRECT, CASCADE, or PANEL, and execution telemetry is
returned for the Cognome to learn from verified outcomes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from aura_adaptive_model_router import AdaptiveModelRouter, SHADOW

NATIVE_MODEL_GATEWAY_VERSION = "AURA_NATIVE_MODEL_GATEWAY_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


class AuraNativeModelGateway:
    """Route native Aura tasks through evidence-based model selection."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        router_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.router_factory = router_factory or AdaptiveModelRouter

    def _new_router(self) -> Any:
        return self.router_factory(repo_root=self.repo_root)

    @staticmethod
    def _selection_trace(result: Mapping[str, Any]) -> dict[str, Any]:
        option = dict(result.get("selected_option") or {})
        assessments = list(dict(result.get("shadow_evaluation") or {}).get("candidate_assessments") or [])
        return {
            "policy_mode": option.get("policy_mode"),
            "selected_profile_ids": list(option.get("profile_ids") or []),
            "expected_verified_success": option.get("expected_success"),
            "expected_cost_usd": option.get("expected_cost_usd"),
            "expected_time_to_verified_ms": option.get("expected_time_to_verified_ms"),
            "candidate_count": len(assessments),
            "admitted_profile_ids": [
                str(item.get("candidate", {}).get("profile_id") or item.get("profile_id") or "")
                for item in assessments
                if bool(item.get("admitted"))
            ],
            "routing_basis": "MODEL_COGNOME_VERIFIED_OUTCOME_EVIDENCE",
            "fallback_semantics": (
                "CASCADE advances only after provider failure or verifier rejection; "
                "PANEL is reserved for policy-selected multi-model review."
            ),
        }

    def plan_best(
        self,
        objective: str,
        *,
        purpose_digest: str,
        target_files: list[str] | None = None,
        target_symbols: list[str] | None = None,
        task_fields: Mapping[str, Any] | None = None,
        token_budget: int = 2400,
        forced_model: str | None = None,
    ) -> dict[str, Any]:
        router = self._new_router()
        try:
            result = router.plan(
                objective,
                purpose_digest=purpose_digest,
                target_files=target_files,
                target_symbols=target_symbols,
                forced_model=forced_model,
                task_fields=task_fields,
                token_budget=token_budget,
            )
            result = dict(result)
            result["native_gateway"] = {
                "version": NATIVE_MODEL_GATEWAY_VERSION,
                "adaptive_selection": forced_model is None,
                "selection_trace": self._selection_trace(result),
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
            return result
        finally:
            if hasattr(router, "close"):
                router.close()

    def execute_best(
        self,
        objective: str,
        *,
        purpose_digest: str,
        execution_mode: str = SHADOW,
        authorization: Mapping[str, Any] | Any | None = None,
        target_files: list[str] | None = None,
        target_symbols: list[str] | None = None,
        task_fields: Mapping[str, Any] | None = None,
        token_budget: int = 2400,
        forced_model: str | None = None,
    ) -> dict[str, Any]:
        router = self._new_router()
        try:
            result = router.execute(
                objective,
                purpose_digest=purpose_digest,
                execution_mode=execution_mode,
                authorization=authorization,
                target_files=target_files,
                target_symbols=target_symbols,
                forced_model=forced_model,
                task_fields=task_fields,
                token_budget=token_budget,
            )
            result = dict(result)
            result["native_gateway"] = {
                "version": NATIVE_MODEL_GATEWAY_VERSION,
                "adaptive_selection": forced_model is None,
                "selection_trace": self._selection_trace(result),
                "telemetry_persistence_expected": execution_mode.upper() != SHADOW,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
            return result
        finally:
            if hasattr(router, "close"):
                router.close()


__all__ = ["AuraNativeModelGateway", "NATIVE_MODEL_GATEWAY_VERSION"]
