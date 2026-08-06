from __future__ import annotations

import json
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label} anchor count: {count}")
    return text.replace(old, new, 1)


code_path = Path("aura_ephemeral_workspace_contracts.py")
code = code_path.read_text(encoding="utf-8")

code = replace_once(
    code,
    '''    if value is None or (type(value) is tuple and not value):
        return ()
''',
    '''    if value is None:
        raise ValueError(f"{name} must be an object")
    if type(value) is tuple and not value:
        return ()
''',
    "explicit null metadata",
)

code = replace_once(
    code,
    '''    required_verification_gates: tuple[str, ...]
    ttl_seconds: int = 300
''',
    '''    required_verification_gates: tuple[str, ...]
    issued_at_epoch_seconds: int
    expires_at_epoch_seconds: int
    ttl_seconds: int = 300
''',
    "recipe lifecycle fields",
)

code = replace_once(
    code,
    '''        adapters = _refs(self.adapter_refs, "adapter_refs", require_current=True)
        evidence = _refs(self.evidence_refs, "evidence_refs", require_current=True)
        if {item.reference_id for item in adapters} & {item.reference_id for item in evidence}:
            raise ValueError("duplicate recipe reference IDs across adapter and evidence roles")
''',
    '''        adapters = _refs(self.adapter_refs, "adapter_refs", require_current=True)
        evidence = _refs(self.evidence_refs, "evidence_refs", require_current=True)
        reference_ids = [
            self.base_manifest_ref.reference_id,
            *(item.reference_id for item in adapters),
            *(item.reference_id for item in evidence),
        ]
        if len(set(reference_ids)) != len(reference_ids):
            raise ValueError(
                "duplicate recipe reference IDs across manifest, adapter, and evidence roles"
            )
''',
    "recipe cross-role reference uniqueness",
)

code = replace_once(
    code,
    '''        object.__setattr__(self, "ttl_seconds", _int(self.ttl_seconds, "recipe.ttl", 1, MAX_TTL_SECONDS))
        if self.budgets.wall_time_ms > self.ttl_seconds * 1000:
''',
    '''        object.__setattr__(
            self,
            "issued_at_epoch_seconds",
            _int(
                self.issued_at_epoch_seconds,
                "recipe.issued_at_epoch_seconds",
                1,
                MAX_TIMESTAMP,
            ),
        )
        object.__setattr__(
            self,
            "expires_at_epoch_seconds",
            _int(
                self.expires_at_epoch_seconds,
                "recipe.expires_at_epoch_seconds",
                1,
                MAX_TIMESTAMP,
            ),
        )
        object.__setattr__(self, "ttl_seconds", _int(self.ttl_seconds, "recipe.ttl", 1, MAX_TTL_SECONDS))
        if self.expires_at_epoch_seconds - self.issued_at_epoch_seconds != self.ttl_seconds:
            raise ValueError("recipe absolute expiration must equal issue time plus TTL")
        if self.budgets.wall_time_ms > self.ttl_seconds * 1000:
''',
    "recipe lifecycle relation",
)

code = replace_once(
    code,
    '''                "required_verification_gates": list(self.required_verification_gates),
                "ttl_seconds": self.ttl_seconds,
''',
    '''                "required_verification_gates": list(self.required_verification_gates),
                "issued_at_epoch_seconds": self.issued_at_epoch_seconds,
                "expires_at_epoch_seconds": self.expires_at_epoch_seconds,
                "ttl_seconds": self.ttl_seconds,
''',
    "recipe lifecycle serialization",
)

code = replace_once(
    code,
    '''                    "device_requirements", "allowed_interaction_actions",
                    "required_verification_gates", "ttl_seconds", "lifecycle_policy",
''',
    '''                    "device_requirements", "allowed_interaction_actions",
                    "required_verification_gates", "issued_at_epoch_seconds",
                    "expires_at_epoch_seconds", "ttl_seconds", "lifecycle_policy",
''',
    "recipe lifecycle parse shape",
)

code = replace_once(
    code,
    '''        if self.to_dict() != expected.to_dict():
            raise ValueError("stale complete recipe identity")


@dataclass(frozen=True)
class SpatialReferentBinding:
''',
    '''        if self.to_dict() != expected.to_dict():
            raise ValueError("stale complete recipe identity")
        _require_unexpired_recipe(self)


def _require_unexpired_recipe(recipe: EphemeralWorkspaceRecipe) -> None:
    """Reject admission after the recipe's signed absolute expiration boundary."""
    now = _finite_number(time.time(), "current time")
    if now >= recipe.expires_at_epoch_seconds:
        raise ValueError("workspace recipe is expired")


@dataclass(frozen=True)
class SpatialReferentBinding:
''',
    "bound recipe admission expiry",
)

code = replace_once(
    code,
    '''    _id(lease.get("lease_id"), "base manifest arena_lease.lease_id")
    if lease.get("domain") != "ephemeral":
''',
    '''    lease_id = _id(lease.get("lease_id"), "base manifest arena_lease.lease_id")
    lease_identity_body = dict(lease)
    lease_identity_body.pop("phase_hash")
    lease_identity_body.pop("lease_id")
    expected_lease_id = "LEASE-" + hashlib.blake2b(
        json.dumps(
            lease_identity_body,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8"),
        digest_size=16,
    ).hexdigest()[:12]
    if lease_id != expected_lease_id:
        raise ValueError("base manifest arena_lease lease_id does not match content")
    if lease.get("domain") != "ephemeral":
''',
    "derived arena lease id",
)

code = replace_once(
    code,
    '''    remaining_ttl = math.floor(remaining_seconds)
    effective_ttl = min(requested_ttl, manifest_ttl, remaining_ttl)

    manifest_limits = _manifest_resource_limits(body)
''',
    '''    remaining_ttl = math.floor(remaining_seconds)
    effective_ttl = min(requested_ttl, manifest_ttl, remaining_ttl)
    issued_at_epoch_seconds = _int(
        math.floor(now), "recipe issued_at_epoch_seconds", 1, MAX_TIMESTAMP
    )
    expires_at_epoch_seconds = issued_at_epoch_seconds + effective_ttl
    if expires_at_epoch_seconds > math.floor(expires_at):
        raise ValueError("recipe absolute expiration exceeds base manifest expiry")

    manifest_limits = _manifest_resource_limits(body)
''',
    "compiled absolute lifecycle",
)

code = replace_once(
    code,
    '''        "required_verification_gates": list(definition["required_verification_gates"]),
        "ttl_seconds": effective_ttl,
''',
    '''        "required_verification_gates": list(definition["required_verification_gates"]),
        "issued_at_epoch_seconds": issued_at_epoch_seconds,
        "expires_at_epoch_seconds": expires_at_epoch_seconds,
        "ttl_seconds": effective_ttl,
''',
    "compiled recipe identity lifecycle",
)

code = replace_once(
    code,
    '''        required_verification_gates=tuple(definition["required_verification_gates"]),
        ttl_seconds=effective_ttl,
''',
    '''        required_verification_gates=tuple(definition["required_verification_gates"]),
        issued_at_epoch_seconds=issued_at_epoch_seconds,
        expires_at_epoch_seconds=expires_at_epoch_seconds,
        ttl_seconds=effective_ttl,
''',
    "compiled recipe constructor lifecycle",
)

code = replace_once(
    code,
    '''    if record.to_dict() != expected.to_dict():
        raise ValueError("stale complete recipe identity")
    return record


def validate_project_semantics(
''',
    '''    if record.to_dict() != expected.to_dict():
        raise ValueError("stale complete recipe identity")
    _require_unexpired_recipe(record)
    return record


def validate_project_semantics(
''',
    "semantic recipe expiry admission",
)

code_path.write_text(code, encoding="utf-8")


test_path = Path("tests/test_aura_ephemeral_workspace_contracts.py")
tests = test_path.read_text(encoding="utf-8")

lease_old = '''    lease_body = {
        "lease_version": "AURA_ARENA_LEASE_V1",
        "lease_id": "lease-EORG-leased",
        "domain": "ephemeral",
        "capsule_id": leased.organ_id,
        "holder": leased.organ_id,
        "regions": [{"organ_id": leased.organ_id, "scope": "read_only"}],
        "allowed_actions": sorted(leased.granted_capabilities),
        "forbidden_actions": sorted({
            "network", "install", "shell", "production_mutation",
            "secret_access", "commit", "push", "automatic_crystallization",
        }),
        "mode": "read_only",
        "conflict_policy": "judge_then_reground",
        "status": "active",
        "metadata": {},
    }
    lease_body["phase_hash"] = workspace_contracts.hashlib.blake2b(
'''
lease_new = '''    lease_body = {
        "lease_version": "AURA_ARENA_LEASE_V1",
        "domain": "ephemeral",
        "capsule_id": leased.organ_id,
        "holder": leased.organ_id,
        "regions": [{"organ_id": leased.organ_id, "scope": "read_only"}],
        "allowed_actions": sorted(leased.granted_capabilities),
        "forbidden_actions": sorted({
            "network", "install", "shell", "production_mutation",
            "secret_access", "commit", "push", "automatic_crystallization",
        }),
        "mode": "read_only",
        "conflict_policy": "judge_then_reground",
        "status": "active",
        "metadata": {},
    }
    lease_body["lease_id"] = "LEASE-" + workspace_contracts.hashlib.blake2b(
        json.dumps(
            lease_body,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8"),
        digest_size=16,
    ).hexdigest()[:12]
    lease_body["phase_hash"] = workspace_contracts.hashlib.blake2b(
'''
tests = replace_once(tests, lease_old, lease_new, "canonical lease fixture")

tests = replace_once(
    tests,
    '''    tampered_lease_hash = copy.deepcopy(leased)
    tampered_lease_hash.arena_lease["lease_id"] = "lease-EORG-leased-tampered"
    tampered_lease_hash.phase_hash = tampered_lease_hash.compute_digest()
    with pytest.raises(ValueError, match="arena_lease digest does not match content"):
''',
    '''    tampered_lease_hash = copy.deepcopy(leased)
    tampered_lease_hash.arena_lease["phase_hash"] = "0" * 32
    tampered_lease_hash.phase_hash = tampered_lease_hash.compute_digest()
    with pytest.raises(ValueError, match="arena_lease digest does not match content"):
''',
    "lease phase-hash regression",
)

lease_insert_anchor = '''    unsafe_lease = copy.deepcopy(leased)
    unsafe_lease.arena_lease["allowed_actions"] = ["shell"]
'''
lease_insert = '''    redirected_lease_id = copy.deepcopy(leased)
    redirected_lease_id.arena_lease["lease_id"] = "LEASE-000000000000"
    redirected_lease_id_body = dict(redirected_lease_id.arena_lease)
    redirected_lease_id_body.pop("phase_hash")
    redirected_lease_id.arena_lease["phase_hash"] = workspace_contracts.hashlib.blake2b(
        json.dumps(
            redirected_lease_id_body,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8"),
        digest_size=16,
    ).hexdigest()
    redirected_lease_id.phase_hash = redirected_lease_id.compute_digest()
    with pytest.raises(ValueError, match="arena_lease lease_id does not match content"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=redirected_lease_id,
            expected_manifest_timestamps=_trusted_manifest_timestamps(redirected_lease_id),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    unsafe_lease = copy.deepcopy(leased)
    unsafe_lease.arena_lease["allowed_actions"] = ["shell"]
'''
tests = replace_once(tests, lease_insert_anchor, lease_insert, "derived lease id regression")

new_test = '''

def test_lifecycle_anchor_cross_role_identity_and_explicit_null_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Final contract closure binds delayed admission and every recipe reference role."""
    with pytest.raises(ValueError, match="reference.metadata must be an object"):
        CanonicalReference(
            "artifact:null-metadata",
            "canonical.owner",
            "owner://artifact:null-metadata",
            D["1"],
            metadata=None,
        )
    assert CanonicalReference(
        "artifact:default-metadata",
        "canonical.owner",
        "owner://artifact:default-metadata",
        D["1"],
    ).to_dict()["metadata"] == {}

    current, _ = recipe()
    colliding_adapter = replace(
        current.adapter_refs[0],
        reference_id=current.base_manifest_ref.reference_id,
    )
    with pytest.raises(
        ValueError,
        match="duplicate recipe reference IDs across manifest, adapter, and evidence roles",
    ):
        replace(
            current,
            adapter_refs=(colliding_adapter, *current.adapter_refs[1:]),
            recipe_digest="",
        )

    manifest = create_manifest(
        "Anchor delayed workspace admission to an absolute expiration.",
        organ_id="EORG-absolute-recipe-expiry",
        ttl_seconds=10,
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    compile_now = manifest.created_at + 1.25
    monkeypatch.setattr(workspace_contracts.time, "time", lambda: compile_now)
    anchored = compile_coding_spatial_workspace_recipe(
        base_manifest=manifest,
        expected_manifest_timestamps=_trusted_manifest_timestamps(manifest),
        project_projection=project(),
        expected_project_projection=project(),
        canonical_intent_digest=D["1"],
        adapter_refs=(ref("adapter:compass", D["2"]),),
        evidence_refs=(ref("evidence:source", D["3"]),),
        ttl_seconds=3,
    )
    assert anchored.issued_at_epoch_seconds == int(compile_now // 1)
    assert anchored.expires_at_epoch_seconds == anchored.issued_at_epoch_seconds + 3
    assert anchored.expires_at_epoch_seconds <= int(manifest.expires_at // 1)
    assert EphemeralWorkspaceRecipe.from_dict(anchored.to_dict()).to_dict() == anchored.to_dict()

    monkeypatch.setattr(
        workspace_contracts.time,
        "time",
        lambda: float(anchored.expires_at_epoch_seconds),
    )
    with pytest.raises(ValueError, match="workspace recipe is expired"):
        validate_recipe_semantics(anchored.to_dict(), expected_recipe=anchored)
    with pytest.raises(ValueError, match="workspace recipe is expired"):
        anchored.validate_bindings(
            expected_intent_digest=anchored.canonical_intent_digest,
            expected_project_projection_id=anchored.project_projection_id,
            expected_project_projection_digest=anchored.project_projection_digest,
            expected_base_manifest_ref=anchored.base_manifest_ref,
            expected_adapter_refs={
                item.reference_id: item.to_dict() for item in anchored.adapter_refs
            },
            expected_evidence_refs={
                item.reference_id: item.to_dict() for item in anchored.evidence_refs
            },
            expected_recipe=anchored,
        )
'''
if "def test_lifecycle_anchor_cross_role_identity_and_explicit_null_fail_closed(" in tests:
    raise SystemExit("new lifecycle closure regression already exists")
tests = tests.rstrip() + new_test + "\n"
test_path.write_text(tests, encoding="utf-8")


schema_path = Path("schemas/aura_ephemeral_workspace_recipe.schema.json")
schema = json.loads(schema_path.read_text(encoding="utf-8"))
schema["properties"]["issued_at_epoch_seconds"] = {
    "maximum": 2**63 - 1,
    "minimum": 1,
    "type": "integer",
}
schema["properties"]["expires_at_epoch_seconds"] = {
    "maximum": 2**63 - 1,
    "minimum": 1,
    "type": "integer",
}
for field_name in ("issued_at_epoch_seconds", "expires_at_epoch_seconds"):
    if field_name not in schema["required"]:
        schema["required"].append(field_name)
delegations = schema["x-aura-semantic-delegations"]
delegations.pop("reference_id_uniqueness_across_adapter_and_evidence_refs", None)
delegations[
    "reference_id_uniqueness_across_manifest_adapter_and_evidence_refs"
] = "mandatory semantic validator"
delegations["absolute_recipe_expiration_admission"] = "mandatory semantic validator"
invariants = schema["x-aura-semantic-invariants"]
old_uniqueness = (
    "reference-ID uniqueness within and across adapter/evidence references delegated "
    "to mandatory semantic validation"
)
if old_uniqueness in invariants:
    invariants[invariants.index(old_uniqueness)] = (
        "reference-ID uniqueness across manifest, adapter, and evidence roles delegated "
        "to mandatory semantic validation"
    )
for invariant in (
    "issued-at plus TTL equals the signed absolute recipe expiration",
    "expired recipes are rejected during mandatory semantic admission",
):
    if invariant not in invariants:
        invariants.append(invariant)
schema_path.write_text(
    json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    encoding="utf-8",
)


doc_path = Path("docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md")
doc = doc_path.read_text(encoding="utf-8")
doc = replace_once(
    doc,
    '''The frozen `CODING_SPATIAL_WORKSPACE_V1` recipe binds the manifest projection, canonical intent, project projection, capability graph, adapters, evidence, handoff owners, budgets, interactions, verification gates, TTL, and dissolution policy.
''',
    '''The frozen `CODING_SPATIAL_WORKSPACE_V1` recipe binds the manifest projection, canonical intent, project projection, capability graph, adapters, evidence, handoff owners, budgets, interactions, verification gates, signed issue time, absolute expiration, TTL, and dissolution policy.

`issued_at_epoch_seconds + ttl_seconds == expires_at_epoch_seconds` is enforced before signing. Parsing remains available for historical verification, but both recipe admission paths consult the trusted local clock and reject the exact record once its signed absolute expiration is reached. The compiler also proves that this expiration cannot exceed the wrapped V1 manifest's absolute expiry.

Reference identifiers are unique across the base-manifest, adapter, and evidence roles. Explicit JSON `null` metadata is rejected; only an omitted/default empty mapping represents no metadata.
''',
    "recipe lifecycle documentation",
)
doc = replace_once(
    doc,
    '''The focused suite contains **45 tests** covering the original review waves plus the structural repair:
''',
    '''The focused suite contains **46 tests** covering the original review waves plus the structural repair:
''',
    "focused test count heading",
)
doc = replace_once(
    doc,
    '''- manifest/recipe TTL, complete resource-budget ceilings, and exact authority/nested-record admission;
''',
    '''- manifest/recipe TTL, signed issue/absolute-expiry lifecycle binding, complete resource-budget ceilings, and exact authority/nested-record admission;
''',
    "focused lifecycle coverage",
)
doc = replace_once(
    doc,
    '''- focused tests: **45 passed**;
''',
    '''- focused tests: **46 passed**;
''',
    "focused test result count",
)
doc_path.write_text(doc, encoding="utf-8")
