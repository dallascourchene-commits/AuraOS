from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from aura_refactor_skeleton import (
    IntegrationDisposition,
    RefactorSkeleton,
    RefactorSkeletonNode,
    RefactorSkeletonStore,
    SourceSpan,
    sha256_file,
)


def integrations():
    return (
        IntegrationDisposition.create(
            "Human Agent Arena", "INTEGRATED", "Visible plan owner."
        ),
        IntegrationDisposition.create(
            "Crucible", "DEFERRED", "Verified experience only."
        ),
    )


def write_source(tmp_path: Path, name: str = "module.py", body: str = "a = 1\nb = 2\n"):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def node_for(
    tmp_path: Path,
    *,
    status: str = "PLANNED",
    file_name: str = "module.py",
    hash_override: str | None = None,
    spans: tuple[SourceSpan, ...] | None = None,
):
    source = write_source(tmp_path, file_name)
    hashes = {}
    exact_spans = ()
    if status == "READY_FOR_ACT":
        hashes[file_name] = hash_override or sha256_file(source)
        exact_spans = spans or (SourceSpan.create(file_name, 1, 2),)
    return RefactorSkeletonNode.create(
        node_id="E1",
        objective="Ground capability reuse.",
        canonical_owner="owner.py",
        reuse_decision="REUSE",
        target_files=(file_name,),
        exact_source_hashes=hashes,
        exact_source_spans=exact_spans,
        acceptance_criteria=("owner is exact",),
        required_tests=("tests/test_owner.py",),
        integration_dispositions=integrations(),
        status=status,
    )


def skeleton_for(node, *, revision=1, prior=""):
    return RefactorSkeleton.create(
        objective="Build through existing Aura owners.",
        domain="sco_construction_refactor",
        baseline_commit="a" * 40,
        source_plan_digest="b" * 64,
        addendum_digest="c" * 64,
        nodes=(node,),
        status="PLANNED",
        revision=revision,
        prior_revision_digest=prior,
    )


def test_identity_stable_and_storage_time_excluded(tmp_path):
    first = skeleton_for(node_for(tmp_path))
    second = skeleton_for(node_for(tmp_path))
    assert first.skeleton_id == second.skeleton_id
    assert first.skeleton_digest == second.skeleton_digest
    store = RefactorSkeletonStore(tmp_path)
    one = store.store(first)
    two = store.store(second)
    assert one["created"] is True
    assert two["created"] is False


def test_digest_covered_mappings_are_deeply_immutable(tmp_path):
    node = RefactorSkeletonNode.create(
        node_id="E1",
        objective="test",
        canonical_owner="owner",
        reuse_decision="REUSE",
        metadata={"nested": {"x": [1, 2]}},
        repair_history=({"gate": {"name": "scope"}},),
        integration_dispositions=integrations(),
    )
    with pytest.raises(TypeError):
        node.metadata["new"] = True
    with pytest.raises(TypeError):
        node.metadata["nested"]["x"] = ()
    with pytest.raises(TypeError):
        node.repair_history[0]["gate"] = "changed"


def test_exact_source_hashes_are_immutable(tmp_path):
    node = node_for(tmp_path, status="READY_FOR_ACT")
    with pytest.raises(TypeError):
        node.exact_source_hashes["module.py"] = "0" * 64


def test_ready_requires_sha256_for_every_target_and_span(tmp_path):
    write_source(tmp_path, "first.py")
    write_source(tmp_path, "second.py")
    with pytest.raises(ValueError, match="exactly one source hash"):
        RefactorSkeletonNode.create(
            node_id="E1",
            objective="test",
            canonical_owner="owner",
            reuse_decision="REUSE",
            target_files=("first.py", "second.py"),
            exact_source_hashes={"first.py": sha256_file(tmp_path / "first.py")},
            exact_source_spans=(SourceSpan.create("first.py", 1, 1),),
            required_tests=("tests/test.py",),
            status="READY_FOR_ACT",
        )
    with pytest.raises(ValueError, match="invalid SHA-256"):
        RefactorSkeletonNode.create(
            node_id="E1",
            objective="test",
            canonical_owner="owner",
            reuse_decision="REUSE",
            target_files=("first.py",),
            exact_source_hashes={"first.py": "abc123"},
            exact_source_spans=(SourceSpan.create("first.py", 1, 1),),
            required_tests=("tests/test.py",),
            status="READY_FOR_ACT",
        )
    with pytest.raises(ValueError, match="exact source spans"):
        RefactorSkeletonNode.create(
            node_id="E1",
            objective="test",
            canonical_owner="owner",
            reuse_decision="REUSE",
            target_files=("first.py",),
            exact_source_hashes={"first.py": sha256_file(tmp_path / "first.py")},
            required_tests=("tests/test.py",),
            status="READY_FOR_ACT",
        )


def test_ready_source_hash_is_verified_against_file_bytes(tmp_path):
    node = node_for(tmp_path, status="READY_FOR_ACT", hash_override="0" * 64)
    result = skeleton_for(node).validate(repo_root=tmp_path, verify_sources=True)
    assert result["ok"] is False
    assert "source hash mismatch" in str(result["errors"])


def test_exact_span_must_fit_observed_file(tmp_path):
    node = node_for(
        tmp_path,
        status="READY_FOR_ACT",
        spans=(SourceSpan.create("module.py", 1, 99),),
    )
    result = skeleton_for(node).validate(repo_root=tmp_path, verify_sources=True)
    assert result["ok"] is False
    assert "exceeds file length" in str(result["errors"])


def test_source_path_cannot_escape_repo_root(tmp_path):
    outside = tmp_path.parent / "outside.py"
    outside.write_text("x=1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="normalized and relative"):
        SourceSpan.create("../outside.py", 1, 1)


def test_direct_replace_cannot_bypass_digest(tmp_path):
    node = node_for(tmp_path)
    with pytest.raises(ValueError, match="node_digest"):
        replace(node, node_digest="0" * 64)


def test_validate_recomputes_node_and_skeleton_digests(tmp_path):
    node = node_for(tmp_path)
    skeleton = skeleton_for(node)
    object.__setattr__(node, "objective", "tampered")
    result = skeleton.validate()
    assert result["ok"] is False
    assert "node digest" in str(result["errors"])
    assert "skeleton digest" in str(result["errors"])


def test_duplicate_integrations_fail_closed():
    with pytest.raises(ValueError, match="duplicate integration"):
        RefactorSkeletonNode.create(
            node_id="E1",
            objective="test",
            canonical_owner="owner",
            reuse_decision="REUSE",
            integration_dispositions=(
                IntegrationDisposition.create("Human Agent Arena", "INTEGRATED", "a"),
                IntegrationDisposition.create("Human Agent Arena", "DEFERRED", "b"),
            ),
        )


def test_unknown_dependencies_fail_closed():
    node = RefactorSkeletonNode.create(
        node_id="E2",
        objective="test",
        canonical_owner="owner",
        reuse_decision="REUSE",
        dependencies=("MISSING",),
    )
    with pytest.raises(ValueError, match="unknown node dependencies"):
        skeleton_for(node)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("proposal_only", False),
        ("patch_authority", "anything"),
        ("vsa_patch_authority", True),
        ("skeleton_version", "tampered"),
    ],
)
def test_persisted_authority_tampering_is_rejected(tmp_path, field, value):
    skeleton = skeleton_for(node_for(tmp_path))
    store = RefactorSkeletonStore(tmp_path)
    stored = store.store(skeleton)
    path = Path(stored["path"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["skeleton"][field] = value
    # Recompute envelope to prove skeleton authority validation is independent.
    payload["envelope_digest"] = store._envelope_digest(payload["skeleton"])
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="authority fields"):
        store.load_latest(skeleton.skeleton_id)


def test_envelope_tampering_is_rejected(tmp_path):
    skeleton = skeleton_for(node_for(tmp_path))
    store = RefactorSkeletonStore(tmp_path)
    stored = store.store(skeleton)
    path = Path(stored["path"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["truth_class"] = "OTHER"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="truth class"):
        store.load_latest(skeleton.skeleton_id)


def test_revision_chain_is_preserved(tmp_path):
    first = skeleton_for(node_for(tmp_path))
    second = first.revise_node(
        "E1",
        status="REPAIR_REQUIRED",
        repair_entry={"reason": "scope"},
    )
    store = RefactorSkeletonStore(tmp_path)
    store.store(first)
    store.store(second)
    loaded = store.load_latest(first.skeleton_id)
    assert loaded.revision == 2
    assert loaded.prior_revision_digest == first.skeleton_digest


def test_revision_gap_is_rejected(tmp_path):
    first = skeleton_for(node_for(tmp_path))
    third = RefactorSkeleton.create(
        objective=first.objective,
        domain=first.domain,
        baseline_commit=first.baseline_commit,
        source_plan_digest=first.source_plan_digest,
        addendum_digest=first.addendum_digest,
        nodes=first.nodes,
        revision=3,
        prior_revision_digest=first.skeleton_digest,
    )
    store = RefactorSkeletonStore(tmp_path)
    store.store(first)
    with pytest.raises(ValueError, match="extend the latest"):
        store.store(third)


def test_same_revision_fork_is_rejected(tmp_path):
    first = skeleton_for(node_for(tmp_path))
    fork_node = RefactorSkeletonNode.create(
        node_id="E1",
        objective="different",
        canonical_owner="owner.py",
        reuse_decision="REUSE",
        required_tests=("tests/test_owner.py",),
        integration_dispositions=integrations(),
    )
    fork = skeleton_for(fork_node)
    store = RefactorSkeletonStore(tmp_path)
    store.store(first)
    with pytest.raises(ValueError, match="fork"):
        store.store(fork)


def test_broken_prior_digest_chain_is_rejected_on_load(tmp_path):
    first = skeleton_for(node_for(tmp_path))
    second = first.revise_node("E1", status="REPAIR_REQUIRED")
    store = RefactorSkeletonStore(tmp_path)
    one = Path(store.store(first)["path"])
    two = Path(store.store(second)["path"])
    payload = json.loads(two.read_text(encoding="utf-8"))
    payload["skeleton"]["prior_revision_digest"] = "0" * 64
    payload["skeleton"]["skeleton_digest"] = "0" * 64
    payload["envelope_digest"] = store._envelope_digest(payload["skeleton"])
    two.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        store.load_latest(first.skeleton_id)
