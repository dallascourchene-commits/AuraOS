#!/usr/bin/env python3
"""EKI-2: provider-ingress -> versioned external cognition store writer.

D0 / HS1 / NONPROMOTING.

Consumes EKI-1 ExternalKnowledgeCard objects and emits the exact
`aura-coordinate-memory-kv-v1@1.0.0` row ABI consumed by the independently
owned WP03 ExternalCognitionResolveAdapterV1 (PR #728).

Identity/currentness/placement remain deliberately separate:
- source semantic identity + source generation live in the record payload;
- record generation changes when bounded standing/reopen evidence changes;
- placement generation changes when 13D/K27 locality changes;
- store generation changes when the materialized snapshot changes;
- currentness is still resolved by the reader's external validation context;
- no persisted field grants instruction/write/effect/tool-execution authority.

Generation-less discovery observations are persistable, but their record key is
content-addressed and they cannot be confused with source-generation-bound rows.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping, Sequence

from tools import aura_external_knowledge_ingress as eki1


STORE_SCHEMA_NAME = "aura-coordinate-memory-kv-v1"
STORE_SCHEMA_VERSION = "1.0.0"
WRITER_SCHEMA = "AURA-EKI-VERSIONED-EXTERNAL-COGNITION-WRITER-v1"
WRITER_IMPLEMENTATION = "ExternalKnowledgeStoreWriterV1/source-ready"
PR728_READER_HEAD = "9865c42f3ada2520141bd2fe30a439ce160ce2f8"
PR728_READER_RUN = 33416056653
PR728_READER_JOB = 99566849919
PR728_READER_BLOB = "53de9d551c81a0eb495eb180294c0aba5eb359d0"


class StoreWriterError(ValueError):
    pass


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=lambda obj: obj.value if isinstance(obj, Enum) else str(obj),
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _required(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StoreWriterError(f"{name}_REQUIRED")
    return value.strip()


def _record_generation_payload(card: eki1.ExternalKnowledgeCard) -> Mapping[str, Any]:
    """Everything consequence-relevant except physical/locality placement.

    The 13D/K27/toroidal projections are intentionally excluded. Relevance,
    sharding, scheduling or placement changes therefore do not manufacture a new
    semantic/evidence record generation. They create a new placement/store
    generation instead.
    """
    return {
        "schema": card.schema,
        "semantic_id": card.semantic_id,
        "source_kind": card.source_kind,
        "artifact_class": card.artifact_class,
        "canonical_id": card.canonical_id,
        "canonical_uri": card.canonical_uri,
        "title": card.title,
        "source_generation_id": card.generation_id,
        "source_currentness_label": card.currentness,
        "availability": card.availability,
        "admitted_hydration_level": card.admitted_hydration_level,
        "hydration": card.hydration,
        "rights": card.rights,
        "security": card.security,
        "advisory_only": card.advisory_only,
        "exact_reopen_uri": card.exact_reopen_uri,
        "content_sha256": card.content_sha256,
        "claim_ceiling": {
            "read_only_reference_authority": card.read_only_reference_authority,
            "execution_authorized": card.execution_authorized,
            "provider_effect_authorized": card.provider_effect_authorized,
            "semantic_k27_authority": card.semantic_k27_authority,
            "native_private_transformer_kv_accessed": card.native_private_transformer_kv_accessed,
            "gate10_promoted": card.gate10_promoted,
            "merge_deploy_spend_public_financial_human_effect_authorized": (
                card.merge_deploy_spend_public_financial_human_effect_authorized
            ),
        },
    }


def record_generation_id(card: eki1.ExternalKnowledgeCard) -> str:
    return _sha(
        {
            "domain": "AURA-EKI2-RECORD-GENERATION-v1",
            "payload": _record_generation_payload(card),
        }
    )


def placement_generation_id(card: eki1.ExternalKnowledgeCard) -> str:
    return _sha(
        {
            "domain": "AURA-EKI2-PLACEMENT-GENERATION-v1",
            "semantic_id": card.semantic_id,
            "source_generation_id": card.generation_id,
            "projection_13d": card.projection_13d,
            "k27_locality": card.k27_locality,
            "refresh_phase": card.refresh_phase,
        }
    )


def semantic_record_key(card: eki1.ExternalKnowledgeCard) -> str:
    """Versioned semantic key consumed by the PR728 reader.

    The record generation includes exact bounded standing/evidence state while
    excluding locality. This means source/evidence changes create a distinct key,
    but relocalization preserves the key and value digest.
    """
    return (
        "external-cognition://"
        + card.semantic_id
        + "/record/"
        + record_generation_id(card)
    )


def _standing_payload(card: eki1.ExternalKnowledgeCard) -> Mapping[str, Any]:
    # Standing is bounded reference material, never an instruction packet.
    return {
        "semantic_id": card.semantic_id,
        "record_generation": record_generation_id(card),
        "source_kind": card.source_kind,
        "artifact_class": card.artifact_class,
        "canonical_id": card.canonical_id,
        "canonical_uri": card.canonical_uri,
        "title": card.title,
        "source_generation_id": card.generation_id,
        "persisted_currentness_label": card.currentness,
        "availability": card.availability,
        "admitted_hydration_level": card.admitted_hydration_level,
        "hydration": card.hydration,
        "rights": card.rights,
        "security": card.security,
        "advisory_only": card.advisory_only,
        "instruction_authority": False,
        "write_authority": False,
        "effect_authority": False,
        "tool_execution_authority": False,
    }


def _reopen_payload(card: eki1.ExternalKnowledgeCard) -> Mapping[str, Any]:
    return {
        "canonical_uri": card.canonical_uri,
        "exact_reopen_uri": card.exact_reopen_uri,
        "source_generation_id": card.generation_id,
        "content_sha256": card.content_sha256,
        "required_currentness_axes": [
            "SOURCE_GENERATION_CURRENT",
            "SOURCE_BODY_CURRENT",
        ],
        "persisted_currentness_label_is_not_witness": True,
        "source_currentness_must_be_resolved_externally": True,
    }


def _semantic_value_digest(card: eki1.ExternalKnowledgeCard) -> str:
    # Placement intentionally excluded: a relocalization is not semantic drift.
    return _sha(
        {
            "domain": "AURA-EKI2-SEMANTIC-VALUE-v1",
            "standing": _standing_payload(card),
            "reopen": _reopen_payload(card),
        }
    )


@dataclass(frozen=True)
class ExternalCognitionStoreRow:
    key: str
    value: Mapping[str, Any]
    semantic_id: str
    record_generation: str
    placement_generation: str
    source_generation_id: str | None

    def validate(self) -> None:
        _required(self.key, "ROW_KEY")
        _required(self.semantic_id, "ROW_SEMANTIC_ID")
        _required(self.record_generation, "ROW_RECORD_GENERATION")
        _required(self.placement_generation, "ROW_PLACEMENT_GENERATION")
        if set(self.value) != {"cell", "digest", "standing", "reopen", "successor"}:
            raise StoreWriterError("ROW_V_EXACT_SCHEMA_REQUIRED")
        if not isinstance(self.value["digest"], str) or not self.value["digest"]:
            raise StoreWriterError("ROW_DIGEST_REQUIRED")
        if not isinstance(self.value["standing"], str):
            raise StoreWriterError("ROW_STANDING_MUST_BE_STRING")
        if not isinstance(self.value["cell"], Mapping):
            raise StoreWriterError("ROW_CELL_MUST_BE_MAPPING")
        if not isinstance(self.value["reopen"], Mapping):
            raise StoreWriterError("ROW_REOPEN_MUST_BE_MAPPING")
        cell = self.value["cell"]
        if cell.get("semantic_identity") is not False:
            raise StoreWriterError("PLACEMENT_CANNOT_BE_SEMANTIC_IDENTITY")
        if cell.get("authority") is not False:
            raise StoreWriterError("PLACEMENT_CANNOT_MINT_AUTHORITY")

    def to_wire(self) -> Mapping[str, Any]:
        self.validate()
        return {"K": self.key, "V": dict(self.value)}


def compile_row(
    card: eki1.ExternalKnowledgeCard,
    *,
    successor: str | None = None,
) -> ExternalCognitionStoreRow:
    key = semantic_record_key(card)
    record_generation = record_generation_id(card)
    placement_generation = placement_generation_id(card)
    standing = json.dumps(
        _standing_payload(card),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    cell = {
        "placement_schema": "AURA-EKI2-PLACEMENT-v1",
        "placement_generation": placement_generation,
        "operational_13d": card.projection_13d,
        "k27_locality": card.k27_locality,
        "refresh_phase": card.refresh_phase,
        "semantic_identity": False,
        "source_currentness_witness": False,
        "authority": False,
    }
    value = {
        "cell": cell,
        "digest": _semantic_value_digest(card),
        "standing": standing,
        "reopen": _reopen_payload(card),
        "successor": successor,
    }
    row = ExternalCognitionStoreRow(
        key=key,
        value=value,
        semantic_id=card.semantic_id,
        record_generation=record_generation,
        placement_generation=placement_generation,
        source_generation_id=card.generation_id,
    )
    row.validate()
    return row


def _parse_store(snapshot_bytes: bytes) -> dict[str, Mapping[str, Any]]:
    try:
        parsed = json.loads(snapshot_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StoreWriterError("EXISTING_STORE_MUST_BE_VALID_UTF8_JSON") from exc
    schema = parsed.get("schema")
    if not isinstance(schema, Mapping):
        raise StoreWriterError("EXISTING_STORE_SCHEMA_OBJECT_REQUIRED")
    if schema.get("name") != STORE_SCHEMA_NAME or schema.get("version") != STORE_SCHEMA_VERSION:
        raise StoreWriterError("EXISTING_STORE_SCHEMA_MISMATCH")
    rows = parsed.get("rows")
    if not isinstance(rows, list):
        raise StoreWriterError("EXISTING_STORE_ROWS_LIST_REQUIRED")
    index: dict[str, Mapping[str, Any]] = {}
    required = {"cell", "digest", "standing", "reopen", "successor"}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("K"), str):
            raise StoreWriterError("EXISTING_STORE_ROW_SHAPE_INVALID")
        value = row.get("V")
        if not isinstance(value, Mapping) or set(value) != required:
            raise StoreWriterError("EXISTING_STORE_ROW_V_SCHEMA_INVALID")
        key = row["K"]
        if key in index:
            raise StoreWriterError("EXISTING_STORE_DUPLICATE_KEY")
        index[key] = dict(value)
    return index


def _wire_snapshot(index: Mapping[str, Mapping[str, Any]]) -> bytes:
    body = {
        "schema": {"name": STORE_SCHEMA_NAME, "version": STORE_SCHEMA_VERSION},
        "rows": [{"K": key, "V": index[key]} for key in sorted(index)],
    }
    return _canonical_json(body)


@dataclass(frozen=True)
class StoreWriteReceipt:
    schema: str
    writer_implementation: str
    store_generation: str
    store_sha256: str
    row_count: int
    inserted_keys: tuple[str, ...]
    relocated_keys: tuple[str, ...]
    noop_keys: tuple[str, ...]
    supersession_edges: tuple[tuple[str, str], ...]
    pr728_reader_head: str = PR728_READER_HEAD
    pr728_reader_run: int = PR728_READER_RUN
    pr728_reader_job: int = PR728_READER_JOB
    candidate_only: bool = True
    persisted_currentness_is_witness: bool = False
    instruction_authority: bool = False
    write_authority_granted_to_reader: bool = False
    tool_execution_authority: bool = False
    provider_effect_authority: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect_authorized: bool = False

    @property
    def receipt_digest(self) -> str:
        return _sha({"domain": WRITER_SCHEMA, "receipt": asdict(self)})

    def to_dict(self) -> dict[str, Any]:
        body = asdict(self)
        body["receipt_digest"] = self.receipt_digest
        return body


@dataclass(frozen=True)
class CompiledStore:
    snapshot_bytes: bytes
    receipt: StoreWriteReceipt


def compile_store(
    rows: Sequence[ExternalCognitionStoreRow],
    *,
    existing_snapshot_bytes: bytes | None = None,
    supersession_edges: Sequence[tuple[str, str]] = (),
) -> CompiledStore:
    """Materialize one coherent exact snapshot.

    Same semantic key + same value digest + changed cell is lawful relocalization.
    Same semantic key + changed semantic digest fails closed: consequence/evidence
    drift must receive a new record generation/key.

    Supersession is explicit caller/source-owner input. No chronology is inferred
    from timestamps, lexical order, K27 locality, or a persisted CURRENT label.
    """
    index: dict[str, Mapping[str, Any]] = {}
    if existing_snapshot_bytes is not None:
        index.update(_parse_store(existing_snapshot_bytes))

    inserted: list[str] = []
    relocated: list[str] = []
    noops: list[str] = []

    for row in rows:
        row.validate()
        incoming = dict(row.value)
        current = index.get(row.key)
        if current is None:
            index[row.key] = incoming
            inserted.append(row.key)
            continue
        if current == incoming:
            noops.append(row.key)
            continue
        if (
            current.get("digest") == incoming.get("digest")
            and current.get("standing") == incoming.get("standing")
            and current.get("reopen") == incoming.get("reopen")
            and current.get("successor") == incoming.get("successor")
            and current.get("cell") != incoming.get("cell")
        ):
            index[row.key] = incoming
            relocated.append(row.key)
            continue
        raise StoreWriterError(
            "SAME_RECORD_KEY_SEMANTIC_DRIFT_REQUIRES_NEW_RECORD_GENERATION"
        )

    applied_edges: list[tuple[str, str]] = []
    for predecessor, successor in supersession_edges:
        predecessor = _required(predecessor, "SUPERSESSION_PREDECESSOR")
        successor = _required(successor, "SUPERSESSION_SUCCESSOR")
        if predecessor == successor:
            raise StoreWriterError("SUPERSESSION_SELF_EDGE_FORBIDDEN")
        if predecessor not in index or successor not in index:
            raise StoreWriterError("SUPERSESSION_EDGE_REQUIRES_BOTH_ROWS")
        current = dict(index[predecessor])
        existing_successor = current.get("successor")
        if existing_successor not in (None, "", successor):
            raise StoreWriterError("SUPERSESSION_PREDECESSOR_ALREADY_POINTS_ELSEWHERE")
        current["successor"] = successor
        index[predecessor] = current
        applied_edges.append((predecessor, successor))

    # Detect successor cycles in the materialized snapshot.
    for start in index:
        seen: set[str] = set()
        cursor = start
        while cursor in index:
            if cursor in seen:
                raise StoreWriterError("SUPERSESSION_CYCLE_FORBIDDEN")
            seen.add(cursor)
            nxt = index[cursor].get("successor")
            if not isinstance(nxt, str) or not nxt:
                break
            cursor = nxt

    snapshot = _wire_snapshot(index)
    store_sha = _sha_bytes(snapshot)
    store_generation = "EKI2::STORE::" + store_sha[:32]
    receipt = StoreWriteReceipt(
        schema=WRITER_SCHEMA,
        writer_implementation=WRITER_IMPLEMENTATION,
        store_generation=store_generation,
        store_sha256=store_sha,
        row_count=len(index),
        inserted_keys=tuple(sorted(inserted)),
        relocated_keys=tuple(sorted(relocated)),
        noop_keys=tuple(sorted(noops)),
        supersession_edges=tuple(sorted(applied_edges)),
    )
    return CompiledStore(snapshot_bytes=snapshot, receipt=receipt)


def compile_card_from_envelope(
    envelope: Mapping[str, Any],
    *,
    requested_level: eki1.HydrationLevel = eki1.HydrationLevel.L1,
) -> eki1.ExternalKnowledgeCard:
    observation = eki1.observation_from_provider_metadata(envelope)
    # Provider adapters are cheap metadata collectors. Heavy L2-L4 synthesis must
    # be supplied later as explicitly generation-bound HydrationMaterial objects.
    return eki1.admit_external_knowledge(
        observation=observation,
        requested_level=requested_level,
        materials=(),
    )


def atomic_write(path: Path, payload: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Aura EKI-2 external cognition store writer")
    parser.add_argument("--envelope", required=True, help="Provider-normalized EKI-1 envelope JSON")
    parser.add_argument("--store", required=True, help="Output aura-coordinate-memory-kv-v1 JSON")
    parser.add_argument("--receipt", help="Optional writer receipt JSON path")
    parser.add_argument(
        "--supersedes-key",
        help="Explicit prior record key superseded by the newly ingested row; never inferred",
    )
    args = parser.parse_args()

    envelope = _load_json(Path(args.envelope))
    if not isinstance(envelope, Mapping):
        raise StoreWriterError("ENVELOPE_MUST_BE_JSON_OBJECT")
    card = compile_card_from_envelope(envelope)
    row = compile_row(card)

    store_path = Path(args.store)
    existing = store_path.read_bytes() if store_path.exists() else None
    edges: tuple[tuple[str, str], ...] = ()
    if args.supersedes_key:
        edges = ((args.supersedes_key, row.key),)
    compiled = compile_store(
        (row,),
        existing_snapshot_bytes=existing,
        supersession_edges=edges,
    )
    atomic_write(store_path, compiled.snapshot_bytes)

    receipt_bytes = json.dumps(
        compiled.receipt.to_dict(),
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
    ).encode("utf-8") + b"\n"
    if args.receipt:
        atomic_write(Path(args.receipt), receipt_bytes)
    else:
        print(receipt_bytes.decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
