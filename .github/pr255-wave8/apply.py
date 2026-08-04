from pathlib import Path

PATH = Path("tests/test_aura_ephemeral_workspace_contracts.py")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


text = PATH.read_text(encoding="utf-8")

text = replace_once(
    text,
    '''def test_recipe_lifetime_budget_resource_ceiling_and_identity_are_fully_bound() -> None:
    """Recipes cannot outlive manifests, exceed resources, or reuse content IDs."""
    short, _ = recipe(ttl_seconds=300, manifest_ttl=10)
    assert 1 <= short.ttl_seconds <= 10
    assert short.budgets.wall_time_ms <= 10_000
''',
    '''def test_recipe_lifetime_budget_resource_ceiling_and_identity_are_fully_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recipes cannot outlive manifests, exceed resources, or reuse content IDs."""
    manifest = create_manifest(
        "Bound workspace lifetime",
        organ_id="EORG-bound-lifetime",
        ttl_seconds=10,
    )
    monkeypatch.setattr(
        workspace_contracts.time,
        "time",
        lambda: manifest.expires_at - 2.5,
    )
    short, _ = recipe(ttl_seconds=300, manifest=manifest)
    assert short.ttl_seconds == 2
    assert short.budgets.wall_time_ms <= 2_000
''',
    "fixed-clock TTL regression",
)

text = replace_once(
    text,
    '''    compile_coding_spatial_workspace_recipe(
        base_manifest=leased,
        project_projection=project(),
        canonical_intent_digest=D["1"],
        adapter_refs=(ref("adapter:compass", D["2"]),),
        evidence_refs=(ref("evidence:source", D["3"]),),
    )
    unsafe_lease = copy.deepcopy(leased)
''',
    '''    compile_coding_spatial_workspace_recipe(
        base_manifest=leased,
        project_projection=project(),
        canonical_intent_digest=D["1"],
        adapter_refs=(ref("adapter:compass", D["2"]),),
        evidence_refs=(ref("evidence:source", D["3"]),),
    )

    tampered_lease_hash = copy.deepcopy(leased)
    tampered_lease_hash.arena_lease["lease_id"] = "lease-EORG-leased-tampered"
    tampered_lease_hash.phase_hash = tampered_lease_hash.compute_digest()
    with pytest.raises(ValueError, match="arena_lease digest does not match content"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=tampered_lease_hash,
            project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    unsafe_lease = copy.deepcopy(leased)
''',
    "nested lease digest regression",
)

text = replace_once(
    text,
    '''    p = project()
    oversized_expected = {
        f"artifact:{index}": ref(f"artifact:{index}", D["1"]).to_dict()
        for index in range(workspace_contracts.MAX_ITEMS + 1)
    }
    with pytest.raises(ValueError, match="size mismatch"):
        workspace_contracts._validate_reference_set(
            p.all_references(),
            oversized_expected,
            "project",
        )
''',
    '''    oversized_actual = tuple(
        ref(f"artifact:{index}", D["1"])
        for index in range(workspace_contracts.MAX_ITEMS + 1)
    )
    oversized_expected = {
        reference.reference_id: reference.to_dict()
        for reference in oversized_actual
    }
    with pytest.raises(ValueError, match="size mismatch"):
        workspace_contracts._validate_reference_set(
            oversized_actual,
            oversized_expected,
            "project",
        )
''',
    "reference-map ceiling regression",
)

PATH.write_text(text, encoding="utf-8")
print("strengthened TTL, arena-lease digest, and reference-map ceiling regressions")
