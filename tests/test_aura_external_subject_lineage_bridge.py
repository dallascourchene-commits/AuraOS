from __future__ import annotations

import hashlib
import json

import pytest

from tools.aura_external_subject_lineage_bridge import (
    CurrentSubjectDescriptorV1,
    CurrentnessStatus,
    ExternalSubjectLineageBridgeV1,
    LineageDisposition,
    SubjectLineageRequestV1,
    SubjectLineageValidationContextV1,
    current_subject_key,
    legacy_semantic_id,
)


CANONICAL_ID = "2606.26511"
CANONICAL_URI = "https://arxiv.org/abs/2606.26511"
LEGACY_KIND = "ARXIV"
CURRENT_PROVIDER = "ARXIV"
CURRENT_KIND = "PAPER"
STORE_REF = "memory://eki3-fixture"
STORE_GENERATION = "EKI3::STORE::fixture"
R1 = "f" * 64
R2 = "0" * 64


def _subject(*, uri: str = CANONICAL_URI, claimed: str | None = None, provider: str = CURRENT_PROVIDER, kind: str = CURRENT_KIND) -> CurrentSubjectDescriptorV1:
    key = current_subject_key(provider=provider, source_kind=kind, canonical_id=CANONICAL_ID)
    return CurrentSubjectDescriptorV1(
        provider=provider,
        source_kind=kind,
        canonical_id=CANONICAL_ID,
        canonical_uri=uri,
        claimed_subject_key=claimed or key,
    )


def _key(record_generation: str, *, canonical_id: str = CANONICAL_ID, legacy_kind: str = LEGACY_KIND) -> str:
    semantic = legacy_semantic_id(legacy_source_kind=legacy_kind, canonical_id=canonical_id)
    return f"external-cognition://{semantic}/record/{record_generation}"


def _row(
    record_generation: str,
    *,
    successor: str | None = None,
    uri: str = CANONICAL_URI,
    canonical_id: str = CANONICAL_ID,
    legacy_kind: str = LEGACY_KIND,
    cell_marker: int = 0,
) -> dict[str, object]:
    semantic = legacy_semantic_id(legacy_source_kind=legacy_kind, canonical_id=canonical_id)
    standing = {
        "semantic_id": semantic,
        "record_generation": record_generation,
        "source_kind": legacy_kind,
        "canonical_id": canonical_id,
        "canonical_uri": uri,
    }
    return {
        "K": _key(record_generation, canonical_id=canonical_id, legacy_kind=legacy_kind),
        "V": {
            "cell": {
                "placement_schema": "fixture",
                "marker": cell_marker,
                "semantic_identity": False,
                "authority": False,
            },
            "digest": hashlib.sha256(record_generation.encode("ascii")).hexdigest(),
            "standing": json.dumps(standing, sort_keys=True, separators=(",", ":")),
            "reopen": {"canonical_uri": uri},
            "successor": successor,
        },
    }


def _snapshot(rows: list[dict[str, object]]) -> bytes:
    return json.dumps(
        {
            "schema": {"name": "aura-coordinate-memory-kv-v1", "version": "1.0.0"},
            "rows": rows,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _resolve(
    rows: list[dict[str, object]],
    *,
    subject: CurrentSubjectDescriptorV1 | None = None,
    currentness: CurrentnessStatus | None = CurrentnessStatus.RESOLVED_CURRENT,
    legacy_kind: str = LEGACY_KIND,
    expected_sha: str | None = None,
    responsibility: str = "SOURCE_BOUND_COORDINATE_MEMORY",
):
    payload = _snapshot(rows)
    bridge = ExternalSubjectLineageBridgeV1(
        snapshot_bytes=payload,
        store_ref=STORE_REF,
        store_generation=STORE_GENERATION,
    )
    terminal = rows[-1]["K"] if rows else ""
    context = SubjectLineageValidationContextV1(
        record_currentness={} if currentness is None else {str(terminal): currentness},
        source_resolver_refs=("fixture-currentness-resolver",),
    )
    request = SubjectLineageRequestV1(
        store_ref=STORE_REF,
        expected_store_generation=STORE_GENERATION,
        expected_store_sha256=expected_sha or hashlib.sha256(payload).hexdigest(),
        legacy_source_kind=legacy_kind,
        subject=subject or _subject(),
        responsibility=responsibility,
    )
    return bridge.resolve(request, context)


def test_identity_domains_remain_distinct_but_exact_descriptor_bridges_them() -> None:
    legacy = legacy_semantic_id(legacy_source_kind=LEGACY_KIND, canonical_id=CANONICAL_ID)
    current = current_subject_key(provider=CURRENT_PROVIDER, source_kind=CURRENT_KIND, canonical_id=CANONICAL_ID)
    assert legacy != current

    r1_key = _key(R1)
    r2_key = _key(R2)
    receipt = _resolve([_row(R1, successor=r2_key), _row(R2)])
    assert receipt.disposition is LineageDisposition.RESOLVED_CURRENT_RECORD_CANDIDATE
    assert receipt.legacy_semantic_id == legacy
    assert receipt.current_subject_key == current
    assert receipt.ordered_record_keys == (r1_key, r2_key)
    assert receipt.historical_record_keys == (r1_key,)
    assert receipt.terminal_record_key == r2_key
    assert receipt.currentness_minted_from_store is False
    assert receipt.chronological_order_inferred is False
    assert receipt.write_authority is False
    assert receipt.effect_authority is False
    assert receipt.native_private_transformer_kv_accessed is False


def test_explicit_successor_beats_lexical_or_timestamp_like_order() -> None:
    # R1 is lexically greater than R2, yet the explicit R1 -> R2 edge owns order.
    r2_key = _key(R2)
    receipt = _resolve([_row(R1, successor=r2_key), _row(R2)])
    assert receipt.ordered_record_keys == (_key(R1), r2_key)
    assert receipt.terminal_record_key == r2_key


def test_unknown_currentness_requires_revalidation() -> None:
    receipt = _resolve([_row(R1)], currentness=None)
    assert receipt.disposition is LineageDisposition.CURRENTNESS_REVALIDATION_REQUIRED
    assert receipt.terminal_currentness == CurrentnessStatus.UNKNOWN.value


def test_stale_terminal_reopens_source_currentness() -> None:
    receipt = _resolve([_row(R1)], currentness=CurrentnessStatus.STALE)
    assert receipt.disposition is LineageDisposition.CURRENTNESS_REOPEN


def test_persisted_cell_or_k27_like_placement_cannot_change_lineage() -> None:
    r2_key = _key(R2)
    a = _resolve([_row(R1, successor=r2_key, cell_marker=1), _row(R2, cell_marker=2)])
    b = _resolve([_row(R1, successor=r2_key, cell_marker=26), _row(R2, cell_marker=0)])
    assert a.ordered_record_keys == b.ordered_record_keys
    assert a.terminal_record_key == b.terminal_record_key
    assert a.k27_semantic_authority is False


def test_current_subject_key_cannot_be_claimed_without_exact_digest() -> None:
    receipt = _resolve([_row(R1)], subject=_subject(claimed="1" * 64))
    assert receipt.disposition is LineageDisposition.IDENTITY_BRIDGE_HOLD
    assert "CURRENT_SUBJECT_KEY_DIGEST_MISMATCH" in (receipt.refusal_reason or "")


def test_provider_and_source_kind_bridge_is_typed_not_inferred() -> None:
    # A valid digest for the wrong current type still cannot bridge ARXIV legacy identity.
    wrong = _subject(provider="WEB", kind="WEB_PAGE")
    receipt = _resolve([_row(R1)], subject=wrong)
    assert receipt.disposition is LineageDisposition.IDENTITY_BRIDGE_HOLD
    assert "provider+source-kind mapping mismatch" in (receipt.refusal_reason or "")


def test_canonical_uri_drift_requires_explicit_alias_or_reopen_proof() -> None:
    receipt = _resolve([_row(R1, uri="https://arxiv.org/abs/2606.26511v1")])
    assert receipt.disposition is LineageDisposition.IDENTITY_BRIDGE_HOLD
    assert "canonical URI drift" in (receipt.refusal_reason or "")


def test_disconnected_same_subject_versions_do_not_infer_latest() -> None:
    receipt = _resolve([_row(R1), _row(R2)])
    assert receipt.disposition is LineageDisposition.LINEAGE_AMBIGUOUS
    assert receipt.terminal_record_key is None


def test_successor_must_remain_inside_exact_subject_lineage() -> None:
    foreign_key = _key("a" * 64, canonical_id="different-subject")
    receipt = _resolve([_row(R1, successor=foreign_key)])
    assert receipt.disposition is LineageDisposition.LINEAGE_BROKEN


def test_store_sha_is_exact_not_prefix_compatible_at_bridge() -> None:
    receipt = _resolve([_row(R1)], expected_sha="0" * 64)
    assert receipt.disposition is LineageDisposition.STORE_INTEGRITY_ERROR


def test_model_prefix_kv_routes_to_wrong_owner() -> None:
    receipt = _resolve([_row(R1)], responsibility="MODEL_PREFIX_KV")
    assert receipt.disposition is LineageDisposition.WRONG_RESPONSIBILITY_OWNER
    assert receipt.native_private_transformer_kv_accessed is False


def test_unsupported_legacy_kind_requires_explicit_bridge_owner() -> None:
    # The request cannot invent a mapping for a source kind outside the fixed table.
    receipt = _resolve([_row(R1)], legacy_kind="CROSSREF")
    assert receipt.disposition is LineageDisposition.IDENTITY_BRIDGE_HOLD
    assert "no unambiguous" in (receipt.refusal_reason or "")


def test_snapshot_schema_and_duplicates_fail_closed_at_construction() -> None:
    payload = json.dumps({"schema": {"name": "wrong", "version": "1"}, "rows": []}).encode()
    with pytest.raises(ValueError, match="STORE_SCHEMA_MISMATCH"):
        ExternalSubjectLineageBridgeV1(snapshot_bytes=payload, store_ref=STORE_REF, store_generation=STORE_GENERATION)

    row = _row(R1)
    duplicate = _snapshot([row, row])
    with pytest.raises(ValueError, match="STORE_DUPLICATE_KEY"):
        ExternalSubjectLineageBridgeV1(snapshot_bytes=duplicate, store_ref=STORE_REF, store_generation=STORE_GENERATION)
