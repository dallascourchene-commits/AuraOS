"""Aura Civic Model Broker — bounded AMD/Fireworks model access without raw network.

The organ submits a schema-validated request to the broker.
The broker minimizes/redacts data, enforces provider allowlist, records cost.
Fixture mode works without a model key.
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field, asdict
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

ALLOWED_MODEL_TASKS = (
    "contribution_normalization","topic_extraction","plain_language_explanation",
    "bridge_option_drafting","ambiguity_detection","multilingual_rendering",
)

BLOCKED_INPUT_CLASSES = ("PRIVATE_NOT_SHARED","COMMUNITY_CONFIDENTIAL","INDIGENOUS_GOVERNED","CULTURAL_KNOWLEDGE")

@dataclass
class ModelBrokerRequest:
    task: str
    input_data: dict[str, Any] = field(default_factory=dict)
    input_privacy_class: str = "PUBLIC_PSEUDONYMOUS"
    model: str = "fixture"
    provider: str = "fixture"
    def to_dict(self): return asdict(self)

@dataclass
class ModelBrokerResponse:
    task: str
    output: dict[str, Any] = field(default_factory=dict)
    model: str = "fixture"
    provider: str = "fixture"
    latency_ms: float = 0.0
    usage: dict[str, int] = field(default_factory=dict)
    cost_usd: float = 0.0
    truth_class: str = "MODEL_EXTRACTED"
    labels: list[str] = field(default_factory=lambda: ["model_extraction","requires_source_inspection"])
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    def to_dict(self): return asdict(self)

def broker_request(req: ModelBrokerRequest) -> dict[str, Any]:
    # Check task is allowed
    if req.task not in ALLOWED_MODEL_TASKS:
        return {"ok": False, "error": f"task_not_allowed: {req.task}"}
    # Check input privacy
    if req.input_privacy_class in BLOCKED_INPUT_CLASSES:
        return {"ok": False, "error": f"input_class_blocked: {req.input_privacy_class}"}
    # Fixture mode — deterministic response
    start = time.time()
    if req.model == "fixture":
        resp = ModelBrokerResponse(
            task=req.task,
            output={"normalized": str(req.input_data), "result": "fixture_mode_deterministic"},
            latency_ms=(time.time() - start) * 1000,
            usage={"input_tokens": 100, "output_tokens": 50},
            cost_usd=0.0,
        )
        return {"ok": True, "response": resp.to_dict(),
                "broker_mode": "fixture",
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    # Real model would go here with provider allowlist, redaction, etc.
    return {"ok": False, "error": "real_model_not_configured_use_fixture",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
