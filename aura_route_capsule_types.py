"""Typed, non-executable contracts for Aura Executable Route Capsules.

C1 capsules contain only repository-relative references and authority metadata.
They cannot embed prompts, Python callables, shell commands, secrets, or live code.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import re
from typing import Any

ROUTE_CAPSULE_TYPES_VERSION = "AURA_ROUTE_CAPSULE_TYPES_V1"
ROUTE_CAPSULE_MANIFEST_VERSION = "AURA_EXECUTABLE_ROUTE_CAPSULE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
_ID_RE = re.compile(r"^[A-Za-z0-9_.:\-]+$")

REFERENCE_FIELDS = (
    "morphology_profile_ref",
    "vsa_profile_ref",
    "data_aperture_ref",
    "memory_aperture_ref",
    "tool_bundle_ref",
    "model_policy_ref",
    "execution_budget_ref",
    "verifier_contract_ref",
    "output_schema_ref",
)
FORBIDDEN_KEYS = frozenset({
    "python", "callable", "code", "source", "shell", "command", "prompt",
    "secret", "token", "api_key", "private_key", "automatic_commit",
    "automatic_push", "automatic_merge", "automatic_promotion",
})


@dataclass(frozen=True)
class ExecutableRouteCapsule:
    capsule_id: str
    capsule_version: str
    transition_id: str
    morphology_profile_ref: str
    vsa_profile_ref: str
    data_aperture_ref: str
    memory_aperture_ref: str
    tool_bundle_ref: str
    model_policy_ref: str
    execution_budget_ref: str
    verifier_contract_ref: str
    output_schema_ref: str
    morphology_signature: dict[str, str]
    routing_adjuncts: dict[str, str] = field(default_factory=dict)
    requested_capabilities: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ExecutableRouteCapsule":
        if not isinstance(value, dict):
            raise TypeError("route capsule manifest must be an object")
        if str(value.get("schema_version") or "") != ROUTE_CAPSULE_MANIFEST_VERSION:
            raise ValueError(f"expected schema_version {ROUTE_CAPSULE_MANIFEST_VERSION}")
        _reject_forbidden_content(value)
        allowed = {"schema_version", "capsule_id", "capsule_version", "transition_id", *REFERENCE_FIELDS, "morphology_signature", "routing_adjuncts", "requested_capabilities", "metadata"}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(f"unknown route capsule fields: {', '.join(unknown)}")
        capsule_id = _required_id(value, "capsule_id")
        capsule_version = _required_id(value, "capsule_version")
        transition_id = _required_id(value, "transition_id")
        refs = {field_name: _required_text(value, field_name) for field_name in REFERENCE_FIELDS}
        morphology_signature = value.get("morphology_signature") or {}
        if not isinstance(morphology_signature, dict):
            raise TypeError("morphology_signature must be an object")
        routing_adjuncts = value.get("routing_adjuncts") or {}
        if not isinstance(routing_adjuncts, dict):
            raise TypeError("routing_adjuncts must be an object")
        capabilities_raw = value.get("requested_capabilities") or []
        if not isinstance(capabilities_raw, list):
            raise TypeError("requested_capabilities must be a list")
        capabilities: list[str] = []
        for item in capabilities_raw:
            capability = str(item or "").strip()
            if not capability or not re.fullmatch(r"[A-Za-z0-9_.:\-]+", capability):
                raise ValueError(f"invalid capability id: {capability!r}")
            if capability not in capabilities:
                capabilities.append(capability)
        metadata = value.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise TypeError("metadata must be an object")
        _reject_forbidden_content(metadata)
        return cls(
            capsule_id=capsule_id,
            capsule_version=capsule_version,
            transition_id=transition_id,
            morphology_signature={str(k): str(v) for k, v in morphology_signature.items()},
            routing_adjuncts={str(k): str(v) for k, v in routing_adjuncts.items()},
            requested_capabilities=tuple(capabilities),
            metadata=dict(metadata),
            **refs,
        )

    def canonical_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema_version"] = ROUTE_CAPSULE_MANIFEST_VERSION
        data["morphology_signature"] = dict(sorted(self.morphology_signature.items()))
        data["routing_adjuncts"] = dict(sorted(self.routing_adjuncts.items()))
        data["requested_capabilities"] = list(self.requested_capabilities)
        data["metadata"] = dict(sorted(self.metadata.items()))
        return {"schema_version": data.pop("schema_version"), **data}

    def digest(self) -> str:
        body = json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
        return hashlib.blake2b(body.encode("utf-8"), digest_size=20).hexdigest()


@dataclass(frozen=True)
class CompiledRouteCapsule:
    capsule: ExecutableRouteCapsule
    capsule_manifest_digest: str
    component_digests: dict[str, str]
    component_ids: dict[str, str]
    capability_bindings: tuple[dict[str, Any], ...]
    morphology_vector_digest: str
    route_signature_digest: str
    vsa_profile_digest: str
    source_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "AURA_COMPILED_ROUTE_CAPSULE_V1",
            "capsule": self.capsule.canonical_dict(),
            "capsule_digest": self.capsule.digest(),
            "capsule_manifest_digest": self.capsule_manifest_digest,
            "component_digests": dict(sorted(self.component_digests.items())),
            "component_ids": dict(sorted(self.component_ids.items())),
            "capability_bindings": [dict(item) for item in self.capability_bindings],
            "morphology_vector_digest": self.morphology_vector_digest,
            "route_signature_digest": self.route_signature_digest,
            "vsa_profile_digest": self.vsa_profile_digest,
            "source_path": self.source_path,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "routing_authority": "advisory_after_hard_guards",
            "automatic_activation": False,
            "automatic_grammar_promotion": False,
            "automatic_code_installation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
        }


def _required_text(value: dict[str, Any], key: str) -> str:
    text = str(value.get(key) or "").strip()
    if not text:
        raise ValueError(f"{key} is required")
    return text


def _required_id(value: dict[str, Any], key: str) -> str:
    text = _required_text(value, key)
    if not _ID_RE.fullmatch(text):
        raise ValueError(f"{key} contains unsupported characters")
    return text


def _reject_forbidden_content(value: Any, *, path: str = "manifest") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().casefold()
            if normalized in FORBIDDEN_KEYS:
                raise ValueError(f"forbidden executable or authority field at {path}.{key}")
            _reject_forbidden_content(item, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_forbidden_content(item, path=f"{path}[{index}]")
