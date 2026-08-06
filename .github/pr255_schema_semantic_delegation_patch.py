from __future__ import annotations

import json
from pathlib import Path

MANDATORY = "mandatory semantic validator"
EXACT_INTEGER_KEY = "exact_builtin_integer_representation"
SIGNED_EXPIRATION_KEY = "signed_recipe_expiration_arithmetic"
EXACT_INTEGER_INVARIANT = (
    "exact built-in integer representation delegated to mandatory semantic validation"
)
SIGNED_EXPIRATION_INVARIANT = (
    "signed issued-at plus TTL equals absolute expiration delegated to mandatory semantic validation"
)


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one replacement anchor, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_schema(path: str, *, signed_expiration: bool = False) -> None:
    target = Path(path)
    schema = json.loads(target.read_text(encoding="utf-8"))
    delegations = schema["x-aura-semantic-delegations"]
    delegations[EXACT_INTEGER_KEY] = MANDATORY
    if signed_expiration:
        delegations[SIGNED_EXPIRATION_KEY] = MANDATORY
    schema["x-aura-semantic-delegations"] = dict(sorted(delegations.items()))

    invariants = schema["x-aura-semantic-invariants"]
    if EXACT_INTEGER_INVARIANT not in invariants:
        invariants.append(EXACT_INTEGER_INVARIANT)
    if signed_expiration and SIGNED_EXPIRATION_INVARIANT not in invariants:
        invariants.append(SIGNED_EXPIRATION_INVARIANT)

    target.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


update_schema("schemas/aura_project_context_projection.schema.json")
update_schema(
    "schemas/aura_ephemeral_workspace_recipe.schema.json",
    signed_expiration=True,
)
update_schema("schemas/aura_multimodal_spatial_observation.schema.json")

replace_once(
    "docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md",
    "Cross-record identity, graph, digest equality, timestamp arithmetic, transcript equality, freshness admission, reference-ID uniqueness, manifest digest-prefix identity, target identity uniqueness, canonical serialized array ordering, Unicode scalar validity, and complete admission require executable semantic validation. All three schemas declare `x-aura-semantic-requires-independent-binding: true`. Each non-structural rejection is named in `x-aura-semantic-delegations`; UTF-8 byte ceilings, Unicode scalar validity, source-span ordering (`line_start <= line_end`), cross-record uniqueness/equality, freshness, digest-prefix identity, and canonical ordering are enforced by the named mandatory semantic validator rather than falsely claimed as Draft 2020-12 structure.",
    "Cross-record identity, graph, digest equality, signed issue/TTL/expiration arithmetic, exact built-in integer representation, transcript equality, freshness admission, reference-ID uniqueness, manifest digest-prefix identity, target identity uniqueness, canonical serialized array ordering, Unicode scalar validity, and complete admission require executable semantic validation. All three schemas declare `x-aura-semantic-requires-independent-binding: true`. Each non-structural rejection is named in `x-aura-semantic-delegations`; UTF-8 byte ceilings, Unicode scalar validity, exact built-in integer representation, signed lifecycle arithmetic, source-span ordering (`line_start <= line_end`), cross-record uniqueness/equality, freshness, digest-prefix identity, and canonical ordering are enforced by the named mandatory semantic validator rather than falsely claimed as Draft 2020-12 structure.",
)
replace_once(
    "docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md",
    "- schema parity, canonical path-policy equivalence, and explicit semantic delegation;",
    "- schema parity, canonical path-policy equivalence, exact integer representation, signed lifecycle arithmetic, and explicit semantic delegation;",
)

replace_once(
    "tests/test_aura_ephemeral_workspace_contracts.py",
    '            "project_projection_digest_equality",\n',
    '            "project_projection_digest_equality",\n'
    '            "exact_builtin_integer_representation",\n',
)
replace_once(
    "tests/test_aura_ephemeral_workspace_contracts.py",
    '            "behavior_derived_recipe_id",\n',
    '            "behavior_derived_recipe_id",\n'
    '            "exact_builtin_integer_representation",\n'
    '            "signed_recipe_expiration_arithmetic",\n',
)
replace_once(
    "tests/test_aura_ephemeral_workspace_contracts.py",
    '            "observation_digest_equality",\n',
    '            "observation_digest_equality",\n'
    '            "exact_builtin_integer_representation",\n',
)
replace_once(
    "tests/test_aura_ephemeral_workspace_contracts.py",
    '        assert "Unicode scalar validation delegated" in invariants\n',
    '        assert "Unicode scalar validation delegated" in invariants\n'
    '        assert "exact built-in integer representation delegated" in invariants\n'
    '        if filename == "aura_ephemeral_workspace_recipe.schema.json":\n'
    '            assert (\n'
    '                "signed issued-at plus TTL equals absolute expiration delegated"\n'
    '                in invariants\n'
    '            )\n',
)

# Control-plane trigger revision V3; this file is copied to the runner and never enters the PR delta.
