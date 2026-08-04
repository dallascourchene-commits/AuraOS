from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path('.')
SOURCE = ROOT / 'aura_ephemeral_workspace_contracts.py'
TESTS = ROOT / 'tests/test_aura_ephemeral_workspace_contracts.py'
DOC = ROOT / 'docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly one match, found {count}')
    return text.replace(old, new, 1)


def sub_once(text: str, pattern: str, replacement: str, label: str) -> str:
    result, count = re.subn(pattern, replacement, text, count=1, flags=re.S | re.M)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly one regex match, found {count}')
    return result


source = SOURCE.read_text()
source = replace_once(source, 'import re\nfrom types import MappingProxyType', 'import re\nimport time\nfrom types import MappingProxyType', 'time import')

source = replace_once(
    source,
    '_METADATA_FIELDS = _METADATA_TEXT_FIELDS | _METADATA_BOOL_FIELDS | _METADATA_INT_FIELDS | _METADATA_DIGEST_FIELDS\n',
    '''_METADATA_FIELDS = _METADATA_TEXT_FIELDS | _METADATA_BOOL_FIELDS | _METADATA_INT_FIELDS | _METADATA_DIGEST_FIELDS
_PROJECT_CANONICAL_OWNER = "aura_unified_memory_continuity"
_LEGACY_MANIFEST_FIELDS = frozenset({
    "manifest_version", "organ_id", "objective", "objective_hash", "creator",
    "created_at", "ttl_seconds", "expires_at", "intent_packet", "lexc_route",
    "machine_route", "capability_resolution_ref", "capability_resolution_digest",
    "requested_capabilities", "granted_capabilities", "denied_capabilities",
    "boundary_contracts", "arena_lease", "components", "resource_budget",
    "data_policy", "ui_manifest", "verifier_requirements", "human_approval_policy",
    "dissolution_policy", "crystallization_policy", "phase_hash",
    "signature_or_digest", "patch_authority", "vsa_patch_authority",
})
_LEGACY_ALLOWED_CAPABILITIES = frozenset({
    "resolve_capabilities", "search_code", "inspect_symbol", "read_slice",
    "rank_regions", "build_change_graph", "show_tests", "show_docs",
    "render_ui_schema", "write_temp_audit", "emit_telemetry", "dissolve",
})
_LEGACY_FORBIDDEN_CAPABILITIES = frozenset({
    "external_network", "package_install", "shell", "arbitrary_subprocess",
    "host_write_outside_temp", "production_mutation", "secret_access",
    "raw_private_memory", "commit", "push", "pr", "booking_payment",
    "permanent_plugin_install", "automatic_crystallization",
})
_LEGACY_RESOURCE_FIELDS = frozenset({
    "wall_time_ms", "memory_mb", "output_bytes", "tool_calls", "model_calls",
    "cost_usd", "network_calls",
})
''',
    'manifest constants',
)

source = sub_once(
    source,
    r'^def _canonical\(value: Any\) -> Any:\n.*?(?=^def canonical_json)',
    '''def _canonical(value: Any) -> Any:
    """Return a lossless canonical JSON value or reject ambiguous input."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        if hasattr(value, "to_dict") and callable(value.to_dict):
            return _canonical(value.to_dict())
        return _canonical(asdict(value))
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("JSON object keys must be strings")
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, (set, frozenset)):
        raise ValueError("sets are not JSON values")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite floats are prohibited")
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise ValueError(f"non-JSON value: {type(value).__name__}")


''',
    'canonical serializer',
)

source = sub_once(
    source,
    r'^def _text\(value: Any, name: str, \*, optional: bool = False, maximum: int = MAX_TEXT_BYTES\) -> str:\n.*?(?=^def _bool)',
    '''def _text(value: Any, name: str, *, optional: bool = False, maximum: int = MAX_TEXT_BYTES) -> str:
    """Validate canonical bounded text without coercion or whitespace folding."""
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")
    if not value and not optional:
        raise ValueError(f"{name} is required")
    if len(value.encode("utf-8")) > maximum or any(ord(char) < 32 for char in value):
        raise ValueError(f"{name} exceeds its bounded text contract")
    return value


def _id(value: Any, name: str) -> str:
    """Validate an Aura identifier."""
    result = _text(value, name, maximum=192)
    if not _ID.fullmatch(result):
        raise ValueError(f"{name} contains unsupported characters")
    return result


def _digest(value: Any, name: str, *, optional: bool = False) -> str:
    """Validate an exact lowercase BLAKE2b-256 digest."""
    result = _text(value, name, optional=optional, maximum=64)
    if result and not _DIGEST.fullmatch(result):
        raise ValueError(f"{name} must be 64 lowercase hex characters")
    return result


def _legacy_digest(value: Any, name: str) -> str:
    """Validate the retained lowercase 32-character V1 manifest digest."""
    result = _text(value, name, maximum=32)
    if not _LEGACY_DIGEST.fullmatch(result):
        raise ValueError(f"{name} must be a 32-character lowercase V1 digest")
    return result


def _commit_sha(value: Any, name: str) -> str:
    """Validate a complete lowercase Git SHA-1 or SHA-256 object identifier."""
    result = _text(value, name, maximum=64)
    if not _COMMIT_SHA.fullmatch(result):
        raise ValueError(f"{name} must be a complete lowercase 40- or 64-character Git object ID")
    return result


def _finite_number(value: Any, name: str, *, minimum: float = 0.0) -> float:
    """Validate a finite non-boolean numeric value at or above a minimum."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite JSON number")
    number = float(value)
    if not math.isfinite(number) or number < minimum:
        raise ValueError(f"{name} must be a finite number >= {minimum}")
    return number


''',
    'strict primitive block',
)

source = replace_once(
    source,
    '        if key in _METADATA_TEXT_FIELDS:\n            validated[key] = _text(item, field_name, maximum=4096)\n',
    '        if key == "manifest_version":\n            validated[key] = _id(item, field_name)\n        elif key in _METADATA_TEXT_FIELDS:\n            validated[key] = _text(item, field_name, maximum=4096)\n',
    'metadata manifest version',
)

source = replace_once(
    source,
    '        return cls(**dict(payload))\n\n\n@dataclass(frozen=True)\nclass RepositoryIdentity:',
    '''        return cls(**dict(payload))


def _reference_map(value: Any, name: str) -> dict[str, CanonicalReference]:
    """Parse a complete identifier-to-canonical-reference mapping."""
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} is required")
    result: dict[str, CanonicalReference] = {}
    for supplied_id, raw_reference in value.items():
        reference_id = _id(supplied_id, f"{name} key")
        reference = raw_reference if isinstance(raw_reference, CanonicalReference) else CanonicalReference.from_dict(raw_reference)
        if reference_id != reference.reference_id:
            raise ValueError(f"{name} key/reference mismatch: {reference_id}")
        if reference_id in result:
            raise ValueError(f"duplicate {name} reference: {reference_id}")
        result[reference_id] = reference
    return result


def _validate_reference_set(actual: Sequence[CanonicalReference], expected_value: Any,
                            name: str, *, require_current: bool = True) -> None:
    """Rebind a complete reference set, including owner and metadata identity."""
    expected = _reference_map(expected_value, f"expected_{name}_refs")
    current = {reference.reference_id: reference for reference in actual}
    if set(current) != set(expected):
        raise ValueError(f"{name} reference set mismatch")
    for reference_id in sorted(current):
        if current[reference_id].to_dict() != expected[reference_id].to_dict():
            raise ValueError(f"stale {name} canonical reference: {reference_id}")
        if require_current and current[reference_id].freshness_class not in _CURRENT_FRESHNESS:
            raise ValueError(f"stale {name} canonical reference: {reference_id}")


@dataclass(frozen=True)
class RepositoryIdentity:''',
    'reference identity helpers',
)

source = sub_once(
    source,
    r'^    def validate_bindings\(self, \*, expected_repository_identity_digest: str,\n.*?(?=^@dataclass\(frozen=True\)\nclass WorkspaceBudget)',
    '''    def validate_bindings(self, *, expected_repository_identity_digest: str,
                          expected_project_ref: str,
                          expected_canonical_owner: str,
                          expected_references: Mapping[str, CanonicalReference | Mapping[str, Any]],
                          reject_stale: bool = True) -> None:
        """Rebind the complete projection to current canonical identities."""
        if self.repository_identity.identity_digest != _digest(expected_repository_identity_digest, "expected repository digest"):
            raise ValueError("stale repository identity digest")
        if self.project_ref != _text(expected_project_ref, "expected project ref"):
            raise ValueError("stale project reference")
        if self.canonical_owner != _id(expected_canonical_owner, "expected project owner"):
            raise ValueError("stale project canonical owner")
        references = self.all_references()
        _validate_reference_set(references, expected_references, "project", require_current=reject_stale)
        if reject_stale and self.freshness_class not in _CURRENT_FRESHNESS:
            raise ValueError("stale or unknown project projection")


''',
    'project binding validator',
)

source = sub_once(
    source,
    r'^def _refs\(value: Any, name: str\) -> tuple\[CanonicalReference, \.\.\.\]:\n.*?(?=^def _owner_map)',
    '''def _refs(value: Any, name: str, *, require_current: bool = False) -> tuple[CanonicalReference, ...]:
    """Validate and canonicalize a non-empty reference set."""
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence) or not value or len(value) > MAX_ITEMS:
        raise ValueError(f"{name} must be a non-empty bounded sequence")
    result = tuple(item if isinstance(item, CanonicalReference) else CanonicalReference.from_dict(item) for item in value)
    if len({item.reference_id for item in result}) != len(result):
        raise ValueError(f"duplicate {name} IDs")
    if require_current and any(item.freshness_class not in _CURRENT_FRESHNESS for item in result):
        raise ValueError(f"{name} must contain only current or bounded references")
    return tuple(sorted(result, key=lambda item: (item.reference_id, item.owner, item.digest)))


''',
    'reference sequence validator',
)

source = replace_once(
    source,
    '        adapters = _refs(self.adapter_refs, "adapter_refs")\n        evidence = _refs(self.evidence_refs, "evidence_refs")\n',
    '        adapters = _refs(self.adapter_refs, "adapter_refs", require_current=True)\n        evidence = _refs(self.evidence_refs, "evidence_refs", require_current=True)\n',
    'recipe current references',
)

source = replace_once(
    source,
    '        self._validate_frozen_demonstration()\n        _set_record_digest(self, "recipe_digest")\n',
    '''        self._validate_frozen_demonstration()
        identity_body = self.to_dict()
        identity_body.pop("recipe_id")
        identity_body.pop("recipe_digest")
        if self.recipe_id != _compiled_recipe_id(identity_body):
            raise ValueError("recipe.recipe_id does not match behavior-defining content")
        _set_record_digest(self, "recipe_digest")
''',
    'recipe id validation',
)

source = sub_once(
    source,
    r'^    def validate_bindings\(self, \*, expected_intent_digest: str,\n.*?(?=^@dataclass\(frozen=True\)\nclass SpatialReferentBinding)',
    '''    def validate_bindings(self, *, expected_intent_digest: str,
                          expected_project_projection_id: str,
                          expected_project_projection_digest: str,
                          expected_base_manifest_ref: CanonicalReference | Mapping[str, Any],
                          expected_adapter_refs: Mapping[str, CanonicalReference | Mapping[str, Any]],
                          expected_evidence_refs: Mapping[str, CanonicalReference | Mapping[str, Any]]) -> None:
        """Rebind the complete recipe to current manifest, project, and dependencies."""
        if self.canonical_intent_digest != _digest(expected_intent_digest, "expected intent"):
            raise ValueError("stale canonical intent digest")
        if self.project_projection_id != _id(expected_project_projection_id, "expected project projection id"):
            raise ValueError("stale project projection id")
        if self.project_projection_digest != _digest(expected_project_projection_digest, "expected project projection"):
            raise ValueError("stale project projection digest")
        expected_manifest = expected_base_manifest_ref if isinstance(expected_base_manifest_ref, CanonicalReference) else CanonicalReference.from_dict(expected_base_manifest_ref)
        if self.base_manifest_ref.to_dict() != expected_manifest.to_dict():
            raise ValueError("stale base manifest canonical reference")
        if self.base_manifest_ref.freshness_class not in _CURRENT_FRESHNESS:
            raise ValueError("stale base manifest canonical reference")
        _validate_reference_set(self.adapter_refs, expected_adapter_refs, "adapter")
        _validate_reference_set(self.evidence_refs, expected_evidence_refs, "evidence")


''',
    'recipe binding validator',
)

source = sub_once(
    source,
    r'^    def validate_bindings\(self, \*, expected_scene_digest: str,\n.*?(?=^def _legacy_manifest_body)',
    '''    def validate_bindings(self, *, expected_scene_digest: str,
                          expected_session_digest: str,
                          expected_entity_digests: Mapping[str, str] | None = None,
                          expected_evidence_refs: Mapping[str, CanonicalReference | Mapping[str, Any]] | None = None) -> None:
        """Rebind all scene, session, entity, and complete evidence identities."""
        if self.scene_digest != _digest(expected_scene_digest, "expected scene"):
            raise ValueError("stale scene digest")
        if self.session_digest != _digest(expected_session_digest, "expected session"):
            raise ValueError("stale session digest")
        if not isinstance(expected_entity_digests, Mapping):
            raise ValueError("expected_entity_digests is required")
        entity_ids = {target.entity_id for target in self.target_candidates}
        if entity_ids != set(expected_entity_digests):
            raise ValueError("entity reference set mismatch")
        for target in self.target_candidates:
            if target.entity_digest != _digest(expected_entity_digests[target.entity_id], "expected entity"):
                raise ValueError(f"stale scene entity: {target.entity_id}")
        _validate_reference_set(
            tuple(target.evidence_ref for target in self.target_candidates),
            expected_evidence_refs,
            "referent evidence",
        )


''',
    'observation binding validator',
)

source = sub_once(
    source,
    r'^def _legacy_manifest_body\(body: Mapping\[str, Any\]\) -> dict\[str, Any\]:\n.*?(?=^def _compiled_recipe_id)',
    '''def _legacy_manifest_body(body: Mapping[str, Any]) -> dict[str, Any]:
    """Return the fields covered by the existing V1 manifest digest."""
    result = dict(body)
    for key in ("created_at", "expires_at", "phase_hash", "signature_or_digest"):
        result.pop(key, None)
    return result


def _legacy_manifest_digest(body: Mapping[str, Any]) -> str:
    """Recompute the exact existing BLAKE2b-128 V1 manifest digest."""
    payload = json.dumps(_legacy_manifest_body(body), sort_keys=True, default=str)
    return hashlib.blake2b(payload.encode("utf-8"), digest_size=16).hexdigest()


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    """Require a mapping at a nested V1 manifest boundary."""
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _require_sequence(value: Any, name: str) -> Sequence[Any]:
    """Require a non-string sequence at a nested V1 manifest boundary."""
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a sequence")
    return value


def _manifest_resource_limits(body: Mapping[str, Any]) -> dict[str, int]:
    """Return wrapper-compatible ceilings from the canonical V1 resource budget."""
    raw = _require_mapping(body.get("resource_budget"), "base manifest resource_budget")
    _strict(raw, set(_LEGACY_RESOURCE_FIELDS), "base manifest resource_budget")
    integer_fields = ("wall_time_ms", "memory_mb", "output_bytes", "tool_calls", "model_calls", "network_calls")
    limits = {name: _int(raw.get(name), f"base manifest resource_budget.{name}", 0, MAX_INTEGER) for name in integer_fields}
    cost_usd = _finite_number(raw.get("cost_usd"), "base manifest resource_budget.cost_usd")
    limits["cost_microusd"] = int(math.floor(cost_usd * 1_000_000))
    return limits


def _validate_v1_manifest(body: Mapping[str, Any]) -> None:
    """Require the complete safe V1 manifest shape and authority profile."""
    _strict(body, set(_LEGACY_MANIFEST_FIELDS), "base manifest")
    if body.get("manifest_version") != LEGACY_EPHEMERAL_MANIFEST_VERSION:
        raise ValueError("unsupported base manifest version")
    _id(body.get("organ_id"), "base organ id")
    objective = _text(body.get("objective"), "base manifest objective")
    objective_hash = _text(body.get("objective_hash"), "base manifest objective_hash", maximum=24)
    expected_objective_hash = hashlib.blake2b(objective.encode("utf-8"), digest_size=12).hexdigest()
    if objective_hash != expected_objective_hash:
        raise ValueError("base manifest objective_hash does not match objective")
    _id(body.get("creator"), "base manifest creator")
    ttl_seconds = _int(body.get("ttl_seconds"), "base manifest ttl", 1, MAX_TTL_SECONDS)
    created_at = _finite_number(body.get("created_at"), "base manifest created_at")
    expires_at = _finite_number(body.get("expires_at"), "base manifest expires_at")
    if expires_at <= created_at or abs((created_at + ttl_seconds) - expires_at) > 1e-6:
        raise ValueError("base manifest expiry is inconsistent with creation time and TTL")

    for name in ("intent_packet", "machine_route", "arena_lease", "data_policy", "ui_manifest", "verifier_requirements"):
        _require_mapping(body.get(name), f"base manifest {name}")
    for name in ("lexc_route", "requested_capabilities", "granted_capabilities", "denied_capabilities", "boundary_contracts", "components"):
        _require_sequence(body.get(name), f"base manifest {name}")
    _text(body.get("capability_resolution_ref"), "base manifest capability_resolution_ref", optional=True)
    resolution_digest = body.get("capability_resolution_digest")
    if resolution_digest:
        _digest(resolution_digest, "base manifest capability_resolution_digest")
    elif resolution_digest != "":
        raise ValueError("base manifest capability_resolution_digest must be a string")
    _text(body.get("signature_or_digest"), "base manifest signature_or_digest", optional=True)

    granted = set(_seq(body.get("granted_capabilities"), "base manifest granted_capabilities", ids=True, sort=True))
    if granted & _LEGACY_FORBIDDEN_CAPABILITIES or not granted <= _LEGACY_ALLOWED_CAPABILITIES:
        raise ValueError("base manifest grants a forbidden or unknown capability")
    requested = _require_sequence(body.get("requested_capabilities"), "base manifest requested_capabilities")
    requested_grants: set[str] = set()
    for index, raw_request in enumerate(requested):
        request = _require_mapping(raw_request, f"base manifest requested_capabilities[{index}]")
        _strict(request, {"capability", "requested", "granted", "denied_reason"}, f"base manifest requested_capabilities[{index}]")
        capability = _id(request.get("capability"), f"base manifest requested_capabilities[{index}].capability")
        _bool(request.get("requested"), f"base manifest requested_capabilities[{index}].requested", True)
        if not isinstance(request.get("granted"), bool):
            raise ValueError(f"base manifest requested_capabilities[{index}].granted must be boolean")
        _text(request.get("denied_reason"), f"base manifest requested_capabilities[{index}].denied_reason", optional=True)
        if request["granted"]:
            if capability not in _LEGACY_ALLOWED_CAPABILITIES:
                raise ValueError("base manifest request grants a forbidden or unknown capability")
            requested_grants.add(capability)
    if requested_grants != granted:
        raise ValueError("base manifest granted_capabilities disagree with capability requests")

    for index, raw_denial in enumerate(_require_sequence(body.get("denied_capabilities"), "base manifest denied_capabilities")):
        denial = _require_mapping(raw_denial, f"base manifest denied_capabilities[{index}]")
        _strict(denial, {"capability", "reason"}, f"base manifest denied_capabilities[{index}]")
        _id(denial.get("capability"), f"base manifest denied_capabilities[{index}].capability")
        _id(denial.get("reason"), f"base manifest denied_capabilities[{index}].reason")

    if body.get("components"):
        raise ValueError("base manifest components must be empty for the non-operational PR1 wrapper")
    data_policy = _require_mapping(body.get("data_policy"), "base manifest data_policy")
    for name in ("private_memory_export", "raw_sidecar_dump", "secrets_access"):
        _bool(data_policy.get(name), f"base manifest data_policy.{name}", False)
    ui_manifest = _require_mapping(body.get("ui_manifest"), "base manifest ui_manifest")
    _strict(ui_manifest, {"component_types", "schema", "executable"}, "base manifest ui_manifest")
    _require_sequence(ui_manifest.get("component_types"), "base manifest ui_manifest.component_types")
    _require_mapping(ui_manifest.get("schema"), "base manifest ui_manifest.schema")
    _bool(ui_manifest.get("executable"), "base manifest ui_manifest.executable", False)
    limits = _manifest_resource_limits(body)
    if limits["network_calls"] != 0:
        raise ValueError("base manifest network access must remain disabled")
    verifier = _require_mapping(body.get("verifier_requirements"), "base manifest verifier_requirements")
    required_verifiers = {"no_production_mutation", "no_secret_access", "no_network_access"}
    must_pass = set(_seq(verifier.get("must_pass"), "base manifest verifier_requirements.must_pass", ids=True, sort=True))
    if not required_verifiers <= must_pass:
        raise ValueError("base manifest verifier requirements are incomplete")
    _id(verifier.get("quality_gate"), "base manifest verifier_requirements.quality_gate")
    if body.get("human_approval_policy") != "required_for_consequential":
        raise ValueError("base manifest human approval policy is unsafe")
    if body.get("dissolution_policy") != "mandatory":
        raise ValueError("base manifest dissolution policy is unsafe")
    if body.get("crystallization_policy") != "proposal_only":
        raise ValueError("base manifest crystallization policy is unsafe")
    if body.get("patch_authority") != "exact_source_spans_and_hashes_only":
        raise ValueError("base manifest patch authority is unsafe")
    _bool(body.get("vsa_patch_authority"), "base manifest vsa_patch_authority", False)


def _manifest_snapshot(manifest: Any) -> tuple[dict[str, Any], str, str]:
    """Verify and snapshot an exact safe V1 manifest into a wrapper identity."""
    raw = manifest.to_dict() if hasattr(manifest, "to_dict") else manifest
    body = _canonical(raw)
    if not isinstance(body, dict):
        raise ValueError("base manifest must be an object")
    _validate_v1_manifest(body)
    recomputed_legacy = _legacy_manifest_digest(body)
    supplied_legacy = _legacy_digest(body.get("phase_hash"), "base manifest phase_hash")
    if supplied_legacy != recomputed_legacy:
        raise ValueError("base manifest digest does not match serialized content")
    wrapper_digest = stable_digest({
        "manifest_version": body["manifest_version"],
        "organ_id": body["organ_id"],
        "legacy_manifest_digest": recomputed_legacy,
        "snapshot": body,
    })
    return body, recomputed_legacy, wrapper_digest


''',
    'manifest verification',
)

source = sub_once(
    source,
    r'^def compile_coding_spatial_workspace_recipe\(\*, base_manifest: Any,\n.*?(?=^def validate_recipe_semantics)',
    '''def compile_coding_spatial_workspace_recipe(*, base_manifest: Any,
                                             project_projection: ProjectContextProjection | Mapping[str, Any],
                                             canonical_intent_digest: str,
                                             adapter_refs: Sequence[CanonicalReference | Mapping[str, Any]],
                                             evidence_refs: Sequence[CanonicalReference | Mapping[str, Any]],
                                             budgets: WorkspaceBudget | Mapping[str, Any] | None = None,
                                             ttl_seconds: int = 300,
                                             now_epoch_seconds: float | None = None) -> EphemeralWorkspaceRecipe:
    """Compile the frozen recipe without invoking any canonical owner."""
    raw_before = base_manifest.to_dict() if hasattr(base_manifest, "to_dict") else base_manifest
    before = canonical_json(raw_before)
    body, legacy_digest, wrapper_digest = _manifest_snapshot(base_manifest)
    raw_after = base_manifest.to_dict() if hasattr(base_manifest, "to_dict") else base_manifest
    if before != canonical_json(raw_after):
        raise ValueError("base V1 manifest changed while wrapping")
    project = project_projection if isinstance(project_projection, ProjectContextProjection) else ProjectContextProjection.from_dict(project_projection)
    if project.canonical_owner != _PROJECT_CANONICAL_OWNER:
        raise ValueError("project projection is not owned by the canonical continuity owner")
    if project.freshness_class not in _CURRENT_FRESHNESS or any(reference.freshness_class not in _CURRENT_FRESHNESS for reference in project.all_references()):
        raise ValueError("project projection or references are stale or unknown")
    manifest_ref = CanonicalReference(f"organ-manifest:{body['organ_id']}",
                                      "aura_ephemeral_manifest",
                                      f"ephemeral-organ:{body['organ_id']}@{body['manifest_version']}",
                                      wrapper_digest,
                                      metadata={"manifest_version": body["manifest_version"],
                                                "legacy_manifest_digest": legacy_digest,
                                                "wrapped_not_replaced": True})
    intent = _digest(canonical_intent_digest, "canonical intent")
    requested_ttl = _int(ttl_seconds, "recipe.ttl", 1, MAX_TTL_SECONDS)
    manifest_ttl = _int(body.get("ttl_seconds"), "base manifest ttl", 1, MAX_TTL_SECONDS)
    created_at = _finite_number(body.get("created_at"), "base manifest created_at")
    expires_at = _finite_number(body.get("expires_at"), "base manifest expires_at")
    now = time.time() if now_epoch_seconds is None else _finite_number(now_epoch_seconds, "compile now_epoch_seconds")
    if now < created_at:
        raise ValueError("compile time precedes base manifest creation")
    remaining_ttl = math.floor(expires_at - now)
    if remaining_ttl < 1:
        raise ValueError("base manifest is expired")
    effective_ttl = min(requested_ttl, manifest_ttl, remaining_ttl)

    manifest_limits = _manifest_resource_limits(body)
    if budgets is None:
        default_budget = WorkspaceBudget()
        budget = replace(default_budget, **{
            name: min(getattr(default_budget, name), ceiling)
            for name, ceiling in manifest_limits.items()
        })
    elif isinstance(budgets, WorkspaceBudget):
        budget = budgets
    else:
        budget = WorkspaceBudget.from_dict(budgets)
    for name, ceiling in manifest_limits.items():
        if getattr(budget, name) > ceiling:
            raise ValueError(f"budget.{name} exceeds base manifest resource ceiling")
    if budget.wall_time_ms > effective_ttl * 1000:
        raise ValueError("budget.wall_time_ms cannot exceed effective workspace TTL")
    adapters = _refs(adapter_refs, "adapter_refs", require_current=True)
    evidence = _refs(evidence_refs, "evidence_refs", require_current=True)
    definition = _FROZEN_DEFINITION
    recipe_body = {"demonstration_id": CODING_SPATIAL_WORKSPACE_V1,
                   "base_manifest_ref": manifest_ref.to_dict(),
                   "canonical_intent_digest": intent,
                   "project_projection_id": project.projection_id,
                   "project_projection_digest": project.projection_digest,
                   "capability_ids": list(definition["capability_ids"]),
                   "dependency_edges": [{"source_capability_id": source, "target_capability_id": target} for source, target in definition["dependency_edges"]],
                   "adapter_refs": [reference.to_dict() for reference in adapters],
                   "evidence_refs": [reference.to_dict() for reference in evidence],
                   "domain_owner_handoff_map": dict(definition["domain_owner_handoff_map"]),
                   "budgets": budget.to_dict(),
                   "renderer_requirements": list(definition["renderer_requirements"]),
                   "device_requirements": list(definition["device_requirements"]),
                   "allowed_interaction_actions": list(definition["allowed_interaction_actions"]),
                   "required_verification_gates": list(definition["required_verification_gates"]),
                   "ttl_seconds": effective_ttl,
                   "lifecycle_policy": _LIFECYCLE_POLICY,
                   "dissolution_policy": _DISSOLUTION_POLICY,
                   "automatic_persistence": False, "automatic_resume": False,
                   "automatic_promotion": False, "authority": AuthorityEnvelope().to_dict(),
                   "version": EPHEMERAL_WORKSPACE_RECIPE_VERSION}
    recipe_id = _compiled_recipe_id(recipe_body)
    return EphemeralWorkspaceRecipe(recipe_id, CODING_SPATIAL_WORKSPACE_V1, manifest_ref,
                                    intent, project.projection_id, project.projection_digest,
                                    tuple(definition["capability_ids"]),
                                    tuple(DependencyEdge(source, target) for source, target in definition["dependency_edges"]),
                                    adapters, evidence, definition["domain_owner_handoff_map"],
                                    budget, tuple(definition["renderer_requirements"]),
                                    tuple(definition["device_requirements"]),
                                    tuple(definition["allowed_interaction_actions"]),
                                    tuple(definition["required_verification_gates"]), effective_ttl)


''',
    'compiler repair',
)

SOURCE.write_text(source)

# Tests
tests = TESTS.read_text()
tests = replace_once(tests, 'from dataclasses import replace', 'from dataclasses import dataclass, replace', 'test dataclass import')
tests = replace_once(
    tests,
    '''def recipe(*, ttl_seconds: int = 300, manifest_ttl: int = 300,
           budgets: WorkspaceBudget | dict | None = None,
           adapters=None, evidence=None):
    """Build the frozen coding-workspace recipe and V1 manifest."""
    manifest = create_manifest(
''',
    '''def recipe(*, ttl_seconds: int = 300, manifest_ttl: int = 300,
           budgets: WorkspaceBudget | dict | None = None,
           adapters=None, evidence=None, manifest=None):
    """Build the frozen coding-workspace recipe and V1 manifest."""
    manifest = manifest or create_manifest(
''',
    'recipe helper manifest reuse',
)
tests = replace_once(
    tests,
    '        budgets=budgets,\n        ttl_seconds=ttl_seconds,\n    )\n',
    '        budgets=budgets,\n        ttl_seconds=ttl_seconds,\n        now_epoch_seconds=manifest.created_at,\n    )\n',
    'deterministic compile time',
)
tests = replace_once(
    tests,
    '''def expected_project_refs(value: ProjectContextProjection) -> dict[str, str]:
    """Return the complete project reference identity map."""
    return {item.reference_id: item.digest for item in value.all_references()}


def expected_observation_evidence(value: MultimodalSpatialObservation) -> dict[str, str]:
    """Return the complete referent-evidence identity map."""
    return {item.evidence_ref.reference_id: item.evidence_ref.digest for item in value.target_candidates}
''',
    '''def expected_project_refs(value: ProjectContextProjection) -> dict[str, dict]:
    """Return the complete project canonical-reference identity map."""
    return {item.reference_id: item.to_dict() for item in value.all_references()}


def expected_observation_evidence(value: MultimodalSpatialObservation) -> dict[str, dict]:
    """Return the complete referent-evidence canonical-reference identity map."""
    return {item.evidence_ref.reference_id: item.evidence_ref.to_dict() for item in value.target_candidates}
''',
    'full reference fixtures',
)

tests = replace_once(
    tests,
    '''    p.validate_bindings(
        expected_repository_identity_digest=p.repository_identity.identity_digest,
        expected_project_ref=p.project_ref,
        expected_reference_digests=expected_project_refs(p),
    )
    r.validate_bindings(
        expected_intent_digest=D["1"],
        expected_project_projection_digest=p.projection_digest,
        expected_base_manifest_digest=manifest.compute_digest(),
        expected_adapter_digests={item.reference_id: item.digest for item in r.adapter_refs},
        expected_evidence_digests={item.reference_id: item.digest for item in r.evidence_refs},
    )
''',
    '''    p.validate_bindings(
        expected_repository_identity_digest=p.repository_identity.identity_digest,
        expected_project_ref=p.project_ref,
        expected_canonical_owner=p.canonical_owner,
        expected_references=expected_project_refs(p),
    )
    r.validate_bindings(
        expected_intent_digest=D["1"],
        expected_project_projection_id=p.projection_id,
        expected_project_projection_digest=p.projection_digest,
        expected_base_manifest_ref=r.base_manifest_ref,
        expected_adapter_refs={item.reference_id: item.to_dict() for item in r.adapter_refs},
        expected_evidence_refs={item.reference_id: item.to_dict() for item in r.evidence_refs},
    )
''',
    'roundtrip complete bindings',
)
tests = tests.replace('expected_evidence_digests=expected_observation_evidence(o)', 'expected_evidence_refs=expected_observation_evidence(o)')

tests = sub_once(
    tests,
    r'^def test_project_binding_requires_complete_reference_set_and_current_projection\(\) -> None:\n.*?(?=^def test_dependency_graph)',
    '''def test_project_binding_requires_complete_reference_set_owner_and_current_projection() -> None:
    """Partial identities, redirected owners, and stale projections must be rejected."""
    p = project()
    with pytest.raises(ValueError, match="expected_project_refs is required"):
        p.validate_bindings(
            expected_repository_identity_digest=p.repository_identity.identity_digest,
            expected_project_ref=p.project_ref,
            expected_canonical_owner=p.canonical_owner,
            expected_references=None,
        )
    partial = expected_project_refs(p)
    partial.pop(next(iter(partial)))
    with pytest.raises(ValueError, match="reference set mismatch"):
        p.validate_bindings(
            expected_repository_identity_digest=p.repository_identity.identity_digest,
            expected_project_ref=p.project_ref,
            expected_canonical_owner=p.canonical_owner,
            expected_references=partial,
        )
    stale = replace(p, freshness_class="STALE", projection_digest="")
    with pytest.raises(ValueError, match="stale or unknown project projection"):
        stale.validate_bindings(
            expected_repository_identity_digest=stale.repository_identity.identity_digest,
            expected_project_ref=stale.project_ref,
            expected_canonical_owner=stale.canonical_owner,
            expected_references=expected_project_refs(stale),
        )
    redirected = replace(p, canonical_owner="attacker.owner", projection_digest="")
    with pytest.raises(ValueError, match="canonical owner"):
        redirected.validate_bindings(
            expected_repository_identity_digest=redirected.repository_identity.identity_digest,
            expected_project_ref=redirected.project_ref,
            expected_canonical_owner=p.canonical_owner,
            expected_references=expected_project_refs(redirected),
        )
    altered_reference = replace(
        p,
        artifact_evidence_refs=(replace(p.artifact_evidence_refs[0], owner="attacker.owner"),),
        projection_digest="",
    )
    with pytest.raises(ValueError, match="canonical reference"):
        altered_reference.validate_bindings(
            expected_repository_identity_digest=altered_reference.repository_identity.identity_digest,
            expected_project_ref=altered_reference.project_ref,
            expected_canonical_owner=altered_reference.canonical_owner,
            expected_references=expected_project_refs(p),
        )
    with pytest.raises(ValueError, match="privacy_class"):
        replace(p, privacy_class="RAW_PRIVATE_MEMORY", projection_digest="")
    with pytest.raises(ValueError, match="egress_class"):
        replace(p, egress_class="NETWORK_ALLOWED", projection_digest="")


''',
    'project binding tests',
)

tests = replace_once(
    tests,
    '''    first, _ = recipe(adapters=adapters, evidence=evidence)
    second, _ = recipe(adapters=tuple(reversed(adapters)), evidence=tuple(reversed(evidence)))
''',
    '''    first, manifest = recipe(adapters=adapters, evidence=evidence)
    second, _ = recipe(manifest=manifest, adapters=tuple(reversed(adapters)), evidence=tuple(reversed(evidence)))
''',
    'order invariance manifest reuse',
)

tests = sub_once(
    tests,
    r'^def test_recipe_lifetime_budget_and_identity_are_fully_bound\(\) -> None:\n.*?(?=^def test_observation)',
    '''def test_recipe_lifetime_budget_resource_ceiling_and_identity_are_fully_bound() -> None:
    """Recipes cannot outlive manifests, exceed resources, or reuse content IDs."""
    short, _ = recipe(ttl_seconds=300, manifest_ttl=10)
    assert short.ttl_seconds == 10
    assert short.budgets.wall_time_ms <= 10_000
    assert short.budgets.memory_mb == 256
    assert short.budgets.output_bytes == 1_000_000
    assert short.budgets.tool_calls == 20
    assert short.budgets.model_calls == 0
    with pytest.raises(ValueError, match="budget keys mismatch"):
        recipe(budgets={})
    ttl_budget = WorkspaceBudget(
        wall_time_ms=10_001, memory_mb=256, output_bytes=1_000_000,
        tool_calls=20, model_calls=0, cost_microusd=0, network_calls=0,
    )
    with pytest.raises(ValueError, match="effective workspace TTL"):
        recipe(ttl_seconds=10, manifest_ttl=10, budgets=ttl_budget)
    oversized = WorkspaceBudget(
        wall_time_ms=30_000, memory_mb=257, output_bytes=1_000_000,
        tool_calls=20, model_calls=0, cost_microusd=0, network_calls=0,
    )
    with pytest.raises(ValueError, match="memory_mb exceeds base manifest resource ceiling"):
        recipe(budgets=oversized)
    with pytest.raises(ValueError, match="integer in 1"):
        recipe(ttl_seconds=0)
    with pytest.raises(ValueError, match="integer in 1"):
        recipe(ttl_seconds=MAX_TTL_SECONDS + 1)
    first, manifest = recipe()
    changed, _ = recipe(manifest=manifest, adapters=(ref("adapter:other", D["7"]),))
    assert first.recipe_id != changed.recipe_id
    assert first.recipe_digest != changed.recipe_digest

    forged = first.to_dict()
    forged["recipe_id"] = "workspace-recipe:forged-identity"
    digest_body = dict(forged)
    digest_body.pop("recipe_digest")
    forged["recipe_digest"] = stable_digest(digest_body)
    with pytest.raises(ValueError, match="recipe_id does not match"):
        EphemeralWorkspaceRecipe.from_dict(forged)


''',
    'lifetime resource identity tests',
)

tests = tests.replace('expected_evidence_digests=None', 'expected_evidence_refs=None')
tests = tests.replace('expected_evidence_digests=wrong_evidence', 'expected_evidence_refs=wrong_evidence')
tests = tests.replace('match="expected_evidence_digests is required"', 'match="expected_referent evidence_refs is required"')
tests = replace_once(
    tests,
    '    wrong_evidence["evidence:referent"] = D["9"]\n',
    '    wrong_evidence["evidence:referent"]["digest"] = D["9"]\n',
    'wrong full evidence identity',
)

new_tests = r'''

def test_contract_dataclass_canonicalization_whitespace_digest_and_metadata_are_exact() -> None:
    """Public serializers and exact spellings must define one canonical identity."""
    reference = ref("artifact:canonical", D["1"], metadata={"manifest_version": "AURA_EPHEMERAL_ORGAN_V1"})
    assert stable_digest(reference) == stable_digest(reference.to_dict())

    @dataclass
    class PlainDataclass:
        value: int

    assert canonical_json(PlainDataclass(1)) == '{"value":1}'
    with pytest.raises(ValueError, match="surrounding whitespace"):
        CanonicalReference("artifact:space", "owner", " owner://artifact ", D["1"])
    with pytest.raises(ValueError, match="lowercase"):
        CanonicalReference("artifact:upper", "owner", "owner://artifact", "A" * 64)
    with pytest.raises(ValueError, match="lowercase"):
        RepositoryIdentity("owner/repo", "main", "A" * 40, D["1"])
    with pytest.raises(ValueError, match="unsupported characters"):
        ref("artifact:bad-version", D["1"], metadata={"manifest_version": "bad version"})


def test_manifest_snapshot_requires_stored_hash_complete_shape_and_safe_policy() -> None:
    """Live and serialized V1 manifests must preserve their stored safe identity."""
    live = create_manifest("Verify stored phase hash", organ_id="EORG-stored-hash")
    live.objective = "mutated after phase hash"
    with pytest.raises(ValueError, match="digest does not match"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=live,
            project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
            now_epoch_seconds=live.created_at,
        )

    incomplete = {
        "manifest_version": "AURA_EPHEMERAL_ORGAN_V1",
        "organ_id": "EORG-incomplete",
        "ttl_seconds": 300,
        "phase_hash": "0" * 32,
    }
    with pytest.raises(ValueError, match="base manifest keys mismatch"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=incomplete,
            project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
            now_epoch_seconds=0.0,
        )

    unsafe = create_manifest("Reject unsafe policy", organ_id="EORG-unsafe")
    unsafe.granted_capabilities.append("shell")
    unsafe.requested_capabilities.append({
        "capability": "shell", "requested": True, "granted": True, "denied_reason": "",
    })
    unsafe.phase_hash = unsafe.compute_digest()
    with pytest.raises(ValueError, match="forbidden or unknown capability"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=unsafe,
            project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
            now_epoch_seconds=unsafe.created_at,
        )


def test_compiler_rejects_expired_stale_and_redirected_inputs() -> None:
    """Compilation must fail before emitting wrappers over expired or stale truth."""
    expired = create_manifest("Expired organ", organ_id="EORG-expired", ttl_seconds=10)
    with pytest.raises(ValueError, match="expired"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=expired,
            project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
            now_epoch_seconds=expired.expires_at,
        )

    manifest = create_manifest("Reject stale inputs", organ_id="EORG-stale-inputs")
    stale_project = replace(project(), freshness_class="STALE", projection_digest="")
    with pytest.raises(ValueError, match="stale or unknown"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=manifest,
            project_projection=stale_project,
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
            now_epoch_seconds=manifest.created_at,
        )
    redirected_project = replace(project(), canonical_owner="attacker.owner", projection_digest="")
    with pytest.raises(ValueError, match="canonical continuity owner"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=manifest,
            project_projection=redirected_project,
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
            now_epoch_seconds=manifest.created_at,
        )
    with pytest.raises(ValueError, match="current or bounded"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=manifest,
            project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:stale", D["2"], "STALE"),),
            evidence_refs=(ref("evidence:source", D["3"]),),
            now_epoch_seconds=manifest.created_at,
        )


def test_recipe_binding_revalidates_complete_manifest_and_dependency_identities() -> None:
    """Digest-only equality cannot redirect canonical owners or wrapper identity."""
    original, _ = recipe()
    altered_payload = original.to_dict()
    altered_payload["adapter_refs"][0]["owner"] = "attacker.owner"
    identity_body = {key: value for key, value in altered_payload.items() if key not in {"recipe_id", "recipe_digest"}}
    altered_payload["recipe_id"] = f"workspace-recipe:{stable_digest(identity_body)[:24]}"
    digest_body = dict(altered_payload)
    digest_body.pop("recipe_digest")
    altered_payload["recipe_digest"] = stable_digest(digest_body)
    altered = EphemeralWorkspaceRecipe.from_dict(altered_payload)
    with pytest.raises(ValueError, match="adapter canonical reference"):
        altered.validate_bindings(
            expected_intent_digest=original.canonical_intent_digest,
            expected_project_projection_id=original.project_projection_id,
            expected_project_projection_digest=original.project_projection_digest,
            expected_base_manifest_ref=original.base_manifest_ref,
            expected_adapter_refs={item.reference_id: item.to_dict() for item in original.adapter_refs},
            expected_evidence_refs={item.reference_id: item.to_dict() for item in original.evidence_refs},
        )
'''

tests = replace_once(
    tests,
    '\ndef test_schemas_enforce_structural_safety_and_semantic_validators_close_cross_field_gaps() -> None:\n',
    new_tests + '\n\ndef test_schemas_enforce_structural_safety_and_semantic_validators_close_cross_field_gaps() -> None:\n',
    'new review regressions',
)

tests = replace_once(
    tests,
    '{"__future__", "collections", "dataclasses", "enum", "hashlib", "json", "math", "re", "types", "typing"}',
    '{"__future__", "collections", "dataclasses", "enum", "hashlib", "json", "math", "re", "time", "types", "typing"}',
    'allowed time import',
)

for obsolete in (
    'expected_reference_digests', 'expected_base_manifest_digest',
    'expected_adapter_digests', 'expected_evidence_digests',
):
    if obsolete in tests or obsolete in source:
        raise RuntimeError(f'obsolete binding API remains: {obsolete}')

TESTS.write_text(tests)

test_tree = ast.parse(tests)
test_count = sum(
    1 for node in test_tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_')
)
doc = DOC.read_text()
doc, count_one = re.subn(r'The focused suite now contains \d+ tests covering:', f'The focused suite now contains {test_count} tests covering:', doc, count=1)
doc, count_two = re.subn(r'- focused tests: \*\*\d+ passed\*\*;', f'- focused tests: **{test_count} passed**;', doc, count=1)
if count_one != 1 or count_two != 1:
    raise RuntimeError(f'document test-count replacements failed: {count_one}, {count_two}')
DOC.write_text(doc)
print(f'patched_test_count={test_count}')
