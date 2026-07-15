"""Strict finite-JSON and sidecar readers for QDKT projection."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import math
import re
from typing import Any

from aura_event_contracts import (
    AppendOnlyEventStore,
    AuraEventEnvelope,
    PATCH_AUTHORITY,
    canonical_json,
    stable_digest,
    stable_id,
)
from aura_qdkt_observations import (
    QDKT_EVENT_TYPE,
    QDKT_POLICY_SCOPE,
    QDKT_SIDECAR_KIND,
    QDKTObservation,
)
from aura_qdkt_projection_types import (
    QDKTProjectionFinding,
    QDKTProjectionFindingCode,
)

_PAYLOAD_REF_RE = re.compile(r"^payload_[0-9a-f]{24}$")


class FindingCollector:
    def __init__(self) -> None:
        self.findings: list[QDKTProjectionFinding] = []
        self._keys: set[tuple[str, tuple[str, ...], str]] = set()

    def add(
        self,
        code: QDKTProjectionFindingCode,
        message: str,
        event_ids: Sequence[str] = (),
    ) -> None:
        ids = tuple(
            sorted({str(item).strip() for item in event_ids if str(item).strip()})
        )
        key = (code.value, ids, message)
        if key not in self._keys:
            self._keys.add(key)
            self.findings.append(QDKTProjectionFinding(code, message, ids))


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _finite_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def parse_finite_object(text: str) -> dict[str, Any]:
    value = json.loads(
        text,
        object_pairs_hook=_unique_object,
        parse_constant=_finite_constant,
    )
    if not isinstance(value, dict):
        raise ValueError("JSON record must be an object")
    return value


def read_event_rows(
    store: AppendOnlyEventStore,
    collector: FindingCollector,
) -> list[tuple[int, dict[str, Any]]]:
    if not store.events_path.exists():
        return []
    try:
        text = store.events_path.read_bytes().decode("utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        collector.add(
            QDKTProjectionFindingCode.EVENT_LOG_READ_FAILED,
            f"event log read failed: {type(exc).__name__}",
        )
        return []
    if not text:
        return []
    terminated = text.endswith("\n")
    if not terminated:
        collector.add(
            QDKTProjectionFindingCode.NONCANONICAL_EVENT_RECORD,
            "event log is missing the required terminal newline",
        )
    body = text[:-1] if terminated else text
    rows: list[tuple[int, dict[str, Any]]] = []
    for index, line in enumerate(body.split("\n"), start=1):
        if not line.strip():
            collector.add(
                QDKTProjectionFindingCode.NONCANONICAL_EVENT_RECORD,
                f"event row {index} is blank",
            )
            continue
        try:
            value = parse_finite_object(line)
            canonical = canonical_json(value)
        except (TypeError, ValueError):
            collector.add(
                QDKTProjectionFindingCode.INVALID_EVENT_RECORD,
                f"event row {index} is not canonical finite JSON",
            )
            continue
        if line != canonical:
            collector.add(
                QDKTProjectionFindingCode.NONCANONICAL_EVENT_RECORD,
                f"event row {index} is not canonical JSON",
                (str(value.get("event_id") or ""),),
            )
        rows.append((index, value))
    return rows


def rebuild_envelope(raw: Mapping[str, Any]) -> AuraEventEnvelope | None:
    parents = raw.get("parent_event_ids")
    evidence = raw.get("evidence_refs")
    created = raw.get("created_at")
    if not isinstance(parents, list) or not isinstance(evidence, list):
        return None
    if (
        isinstance(created, bool)
        or not isinstance(created, (int, float))
        or not math.isfinite(float(created))
    ):
        return None
    try:
        expected = AuraEventEnvelope.create(
            trace_id=raw.get("trace_id"),
            parent_event_ids=parents,
            event_type=raw.get("event_type"),
            actor_id=raw.get("actor_id"),
            actor_type=raw.get("actor_type"),
            arena_id=raw.get("arena_id"),
            board_id=raw.get("board_id"),
            node_id=raw.get("node_id"),
            objective_id=raw.get("objective_id"),
            purpose_digest=raw.get("purpose_digest"),
            dikwp_stage=raw.get("dikwp_stage"),
            payload_ref=raw.get("payload_ref"),
            payload_digest=raw.get("payload_digest"),
            evidence_refs=evidence,
            policy_scope=raw.get("policy_scope"),
            proposal_only=raw.get("proposal_only"),
            measurement_classes=raw.get("measurement_classes"),
            confidence=raw.get("confidence"),
            uncertainty=raw.get("uncertainty"),
            created_at=created,
        )
    except Exception:
        return None
    if raw.get("event_id") != expected.event_id or raw != expected.to_dict():
        return None
    return expected


def _invalid_refs(values: list[Any]) -> bool:
    return any(type(item) is not str or not item.strip() for item in values)


def validate_qdkt_envelope(
    raw: Mapping[str, Any],
    collector: FindingCollector,
) -> AuraEventEnvelope | None:
    event_id = str(raw.get("event_id") or "")
    parents = raw.get("parent_event_ids")
    evidence = raw.get("evidence_refs")
    if not isinstance(parents, list) or not isinstance(evidence, list):
        collector.add(
            QDKTProjectionFindingCode.INVALID_EVENT_RECORD,
            "parent and evidence references must be JSON arrays",
            (event_id,),
        )
        return None
    if _invalid_refs(parents) or _invalid_refs(evidence):
        collector.add(
            QDKTProjectionFindingCode.INVALID_EVENT_RECORD,
            "parent and evidence references must be non-empty strings",
            (event_id,),
        )
        return None
    if len(parents) != len(set(parents)):
        collector.add(
            QDKTProjectionFindingCode.DUPLICATE_PARENT_REF,
            "duplicate parent reference",
            (event_id,),
        )
        return None
    if len(evidence) != len(set(evidence)):
        collector.add(
            QDKTProjectionFindingCode.DUPLICATE_EVIDENCE_REF,
            "duplicate evidence reference",
            (event_id,),
        )
        return None
    envelope = rebuild_envelope(raw)
    if envelope is None:
        collector.add(
            QDKTProjectionFindingCode.ENVELOPE_MISMATCH,
            "QDKT event differs from its canonical envelope",
            (event_id,),
        )
        return None
    if envelope.event_id != event_id:
        collector.add(
            QDKTProjectionFindingCode.EVENT_ID_MISMATCH,
            "QDKT event ID is not canonical",
            (event_id,),
        )
        return None
    if raw.get("proposal_only") is not True:
        collector.add(
            QDKTProjectionFindingCode.NON_PROPOSAL_EVENT,
            "QDKT event is not proposal-only",
            (event_id,),
        )
        return None
    if (
        envelope.event_type != QDKT_EVENT_TYPE
        or envelope.dikwp_stage != "KNOWLEDGE"
        or envelope.policy_scope != QDKT_POLICY_SCOPE
        or envelope.measurement_classes != {"legacy_belief": "DERIVED"}
        or envelope.confidence is not None
        or envelope.uncertainty is not None
        or raw.get("patch_authority") != PATCH_AUTHORITY
        or raw.get("vsa_patch_authority") is not False
    ):
        collector.add(
            QDKTProjectionFindingCode.WRONG_EVENT_CONTRACT,
            "QDKT event metadata or authority boundary changed",
            (event_id,),
        )
        return None
    return envelope


def load_observation(
    store: AppendOnlyEventStore,
    envelope: AuraEventEnvelope,
    collector: FindingCollector,
) -> QDKTObservation | None:
    event_id = envelope.event_id
    ref = envelope.payload_ref
    if type(ref) is not str or not _PAYLOAD_REF_RE.fullmatch(ref):
        collector.add(
            QDKTProjectionFindingCode.UNSAFE_PAYLOAD_REF,
            "QDKT payload reference is invalid",
            (event_id,),
        )
        return None
    path = (store.sidecars_dir / f"{ref}.json").resolve()
    try:
        path.relative_to(store.sidecars_dir.resolve())
    except ValueError:
        collector.add(
            QDKTProjectionFindingCode.UNSAFE_PAYLOAD_REF,
            "QDKT sidecar path is outside the event store",
            (event_id,),
        )
        return None
    if not path.is_file():
        collector.add(
            QDKTProjectionFindingCode.MISSING_SIDECAR,
            "QDKT sidecar is missing",
            (event_id,),
        )
        return None
    try:
        text = path.read_bytes().decode("utf-8", errors="strict")
        payload = parse_finite_object(text)
        canonical = canonical_json(payload)
        payload_digest = stable_digest(payload)
    except (OSError, UnicodeError, TypeError, ValueError):
        collector.add(
            QDKTProjectionFindingCode.MALFORMED_SIDECAR,
            "QDKT sidecar is malformed or contains non-finite data",
            (event_id,),
        )
        return None
    if text != canonical:
        collector.add(
            QDKTProjectionFindingCode.NONCANONICAL_SIDECAR,
            "QDKT sidecar is not canonical JSON",
            (event_id,),
        )
        return None
    if payload_digest != envelope.payload_digest:
        collector.add(
            QDKTProjectionFindingCode.PAYLOAD_DIGEST_MISMATCH,
            "QDKT sidecar digest differs from the event",
            (event_id,),
        )
        return None
    expected_ref = stable_id(
        "payload", {"kind": QDKT_SIDECAR_KIND, "digest": payload_digest}
    )
    if ref != expected_ref:
        collector.add(
            QDKTProjectionFindingCode.PAYLOAD_REF_MISMATCH,
            "QDKT sidecar reference is not canonical",
            (event_id,),
        )
        return None
    try:
        observation = QDKTObservation.from_dict(payload)
    except Exception:
        collector.add(
            QDKTProjectionFindingCode.MALFORMED_SIDECAR,
            "QDKT observation contract is invalid",
            (event_id,),
        )
        return None
    if envelope.node_id != observation.observation_id:
        collector.add(
            QDKTProjectionFindingCode.OBSERVATION_EVENT_MISMATCH,
            "QDKT event does not identify its observation",
            (event_id,),
        )
        return None
    return observation
