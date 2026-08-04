from pathlib import Path

SOURCE = Path("aura_ephemeral_workspace_contracts.py")
TESTS = Path("tests/test_aura_ephemeral_workspace_contracts.py")

source = SOURCE.read_text(encoding="utf-8")
old = '''def _validate_v1_arena_lease(
    lease_value: Any,
    *,
    organ_id: str,
    granted_capabilities: set[str],
) -> None:
    """Verify that a retained V1 arena lease grants only canonical read authority."""
    lease = _require_mapping(lease_value, "base manifest arena_lease")
    if not lease:
        return
    expected_fields = {
        "lease_version", "lease_id", "domain", "capsule_id", "holder",
        "regions", "allowed_actions", "forbidden_actions", "mode",
        "conflict_policy", "status", "metadata", "phase_hash",
    }
    _strict(lease, expected_fields, "base manifest arena_lease")
    if lease.get("lease_version") != "AURA_ARENA_LEASE_V1":
        raise ValueError("base manifest arena_lease version is unsafe")
    _id(lease.get("lease_id"), "base manifest arena_lease.lease_id")
    if lease.get("domain") != "ephemeral":
        raise ValueError("base manifest arena_lease domain is unsafe")
    if lease.get("capsule_id") != organ_id or lease.get("holder") != organ_id:
        raise ValueError("base manifest arena_lease holder identity is unsafe")
    regions = _require_sequence(lease.get("regions"), "base manifest arena_lease.regions")
    if not regions or len(regions) > 16:
        raise ValueError("base manifest arena_lease regions must be bounded")
    for index, raw_region in enumerate(regions):
        region = _require_mapping(raw_region, f"base manifest arena_lease.regions[{index}]")
        _strict(region, {"organ_id", "scope"}, f"base manifest arena_lease.regions[{index}]")
        if region.get("organ_id") != organ_id or region.get("scope") != "read_only":
            raise ValueError("base manifest arena_lease region is not read-only")
    allowed = set(_seq(
        lease.get("allowed_actions"),
        "base manifest arena_lease.allowed_actions",
        ids=True,
        sort=True,
    ))
    if allowed != granted_capabilities:
        raise ValueError("base manifest arena_lease allowed actions disagree with grants")
    forbidden = set(_seq(
        lease.get("forbidden_actions"),
        "base manifest arena_lease.forbidden_actions",
        ids=True,
        sort=True,
    ))
    required_forbidden = {
        "network", "install", "shell", "production_mutation", "secret_access",
        "commit", "push", "automatic_crystallization",
    }
    if not required_forbidden <= forbidden or forbidden & allowed:
        raise ValueError("base manifest arena_lease forbidden actions are incomplete")
    if lease.get("mode") != "read_only":
        raise ValueError("base manifest arena_lease mode is unsafe")
    if lease.get("conflict_policy") != "judge_then_reground":
        raise ValueError("base manifest arena_lease conflict policy is unsafe")
    if lease.get("status") != "active":
        raise ValueError("base manifest arena_lease status is unsafe")
    metadata = _require_mapping(lease.get("metadata"), "base manifest arena_lease.metadata")
    if metadata:
        raise ValueError("base manifest arena_lease metadata must be empty")
    supplied_hash = _legacy_digest(
        lease.get("phase_hash"),
        "base manifest arena_lease.phase_hash",
    )
    hashed_body = dict(lease)
    hashed_body.pop("phase_hash")
    expected_hash = hashlib.blake2b(
        json.dumps(
            hashed_body,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8"),
        digest_size=16,
    ).hexdigest()
    if supplied_hash != expected_hash:
        raise ValueError("base manifest arena_lease digest does not match content")
'''
new = '''def _validate_v1_arena_lease_regions(lease: Mapping[str, Any], organ_id: str) -> None:
    """Require a bounded set of read-only regions owned by the wrapped organ."""
    regions = _require_sequence(lease.get("regions"), "base manifest arena_lease.regions")
    if not regions or len(regions) > 16:
        raise ValueError("base manifest arena_lease regions must be bounded")
    for index, raw_region in enumerate(regions):
        region = _require_mapping(raw_region, f"base manifest arena_lease.regions[{index}]")
        _strict(region, {"organ_id", "scope"}, f"base manifest arena_lease.regions[{index}]")
        if region.get("organ_id") != organ_id or region.get("scope") != "read_only":
            raise ValueError("base manifest arena_lease region is not read-only")


def _validate_v1_arena_lease_actions(
    lease: Mapping[str, Any],
    granted_capabilities: set[str],
) -> None:
    """Reconcile lease actions with manifest grants and mandatory denials."""
    allowed = set(_seq(
        lease.get("allowed_actions"),
        "base manifest arena_lease.allowed_actions",
        ids=True,
        sort=True,
    ))
    if allowed != granted_capabilities:
        raise ValueError("base manifest arena_lease allowed actions disagree with grants")
    forbidden = set(_seq(
        lease.get("forbidden_actions"),
        "base manifest arena_lease.forbidden_actions",
        ids=True,
        sort=True,
    ))
    required_forbidden = {
        "network", "install", "shell", "production_mutation", "secret_access",
        "commit", "push", "automatic_crystallization",
    }
    if not required_forbidden <= forbidden or forbidden & allowed:
        raise ValueError("base manifest arena_lease forbidden actions are incomplete")


def _validate_v1_arena_lease_digest(lease: Mapping[str, Any]) -> None:
    """Recompute and verify the canonical V1 arena-lease phase hash."""
    supplied_hash = _legacy_digest(
        lease.get("phase_hash"),
        "base manifest arena_lease.phase_hash",
    )
    hashed_body = dict(lease)
    hashed_body.pop("phase_hash")
    expected_hash = hashlib.blake2b(
        json.dumps(
            hashed_body,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8"),
        digest_size=16,
    ).hexdigest()
    if supplied_hash != expected_hash:
        raise ValueError("base manifest arena_lease digest does not match content")


def _validate_v1_arena_lease(
    lease_value: Any,
    *,
    organ_id: str,
    granted_capabilities: set[str],
) -> None:
    """Verify that a retained V1 arena lease grants only canonical read authority."""
    lease = _require_mapping(lease_value, "base manifest arena_lease")
    if not lease:
        # An absent lease is a valid V1 state; manifest-level grants remain validated.
        return
    expected_fields = {
        "lease_version", "lease_id", "domain", "capsule_id", "holder",
        "regions", "allowed_actions", "forbidden_actions", "mode",
        "conflict_policy", "status", "metadata", "phase_hash",
    }
    _strict(lease, expected_fields, "base manifest arena_lease")
    if lease.get("lease_version") != "AURA_ARENA_LEASE_V1":
        raise ValueError("base manifest arena_lease version is unsafe")
    _id(lease.get("lease_id"), "base manifest arena_lease.lease_id")
    if lease.get("domain") != "ephemeral":
        raise ValueError("base manifest arena_lease domain is unsafe")
    if lease.get("capsule_id") != organ_id or lease.get("holder") != organ_id:
        raise ValueError("base manifest arena_lease holder identity is unsafe")
    _validate_v1_arena_lease_regions(lease, organ_id)
    _validate_v1_arena_lease_actions(lease, granted_capabilities)
    if lease.get("mode") != "read_only":
        raise ValueError("base manifest arena_lease mode is unsafe")
    if lease.get("conflict_policy") != "judge_then_reground":
        raise ValueError("base manifest arena_lease conflict policy is unsafe")
    if lease.get("status") != "active":
        raise ValueError("base manifest arena_lease status is unsafe")
    metadata = _require_mapping(lease.get("metadata"), "base manifest arena_lease.metadata")
    if metadata:
        raise ValueError("base manifest arena_lease metadata must be empty")
    _validate_v1_arena_lease_digest(lease)
'''
if source.count(old) != 1:
    raise SystemExit(f"source anchor count={source.count(old)}")
SOURCE.write_text(source.replace(old, new), encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
old_import = "from pathlib import Path\n"
new_import = "from pathlib import Path\nfrom typing import Any\n"
if tests.count(old_import) != 1:
    raise SystemExit(f"typing import anchor count={tests.count(old_import)}")
tests = tests.replace(old_import, new_import, 1)
old_fixture = '    malformed_keys = ref("artifact:keys", D["1"]).to_dict()\n'
new_fixture = '    malformed_keys: dict[Any, Any] = dict(ref("artifact:keys", D["1"]).to_dict())\n'
if tests.count(old_fixture) != 1:
    raise SystemExit(f"malformed fixture anchor count={tests.count(old_fixture)}")
TESTS.write_text(tests.replace(old_fixture, new_fixture, 1), encoding="utf-8")
print("wave5_patch_applied=true")
