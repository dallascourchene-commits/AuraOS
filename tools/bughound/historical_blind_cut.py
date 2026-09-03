"""BugHound O10: bitemporal historical-blind benchmark cut.

This module only compiles local benchmark packets. It grants no network,
credential, target-testing, disclosure, submission, payment, or deployment authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Iterable

SCHEMA = "BugHoundHistoricalBlindCutV1"
MODE_HISTORICAL_BLIND = "HISTORICAL_BLIND"
MODE_POST_DISCLOSURE = "POST_DISCLOSURE"
MODE_HOLD = "HOLD_INSUFFICIENT_TEMPORAL_EVIDENCE"

FORBIDDEN_SOLVER_KEYS = frozenset({
    "advisory_id", "cve_ids", "ghsa_ids", "vuln_title", "vuln_category",
    "entry_point_gold", "critical_operation_gold", "trace_gold",
    "fix_commit", "patch", "poc", "oracle", "expected_finding",
})


class HistoricalBlindError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _dt(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise HistoricalBlindError("TIMESTAMP_REQUIRED")
    text = value.strip().replace("Z", "+00:00")
    try:
        out = datetime.fromisoformat(text)
    except ValueError as exc:
        raise HistoricalBlindError("TIMESTAMP_INVALID", value) from exc
    if out.tzinfo is None:
        raise HistoricalBlindError("TIMESTAMP_MUST_BE_OFFSET_AWARE", value)
    return out.astimezone(timezone.utc)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode() + b"\0" + _canonical(value)).hexdigest()


def _nonempty(v: object, code: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise HistoricalBlindError(code)
    return v.strip()


@dataclass(frozen=True)
class TimedEvidenceV1:
    evidence_class: str
    source_ref: str
    observed_at: str
    payload_digest: str
    provider_generation: str
    semantic_root: str
    evaluator_only: bool = False
    authority: bool = False

    @property
    def evidence_digest(self) -> str:
        return _digest("AURA_BUGHOUND_TIMED_EVIDENCE_V1", asdict(self))


@dataclass(frozen=True)
class HistoricalCaseV1:
    corpus_id: str
    case_id: str
    repo_url: str
    vulnerable_commit: str
    source_commit_at: str
    source_tree_digest: str
    source_generation: str
    advisory_published_at: str | None
    evaluator_generation: str
    evidence: tuple[TimedEvidenceV1, ...] = ()
    advisory_id: str | None = None
    cve_ids: tuple[str, ...] = ()
    vuln_title: str | None = None
    vuln_category: str | None = None
    entry_point_gold: str | None = None
    critical_operation_gold: str | None = None
    trace_gold: tuple[str, ...] = ()
    fix_commit: str | None = None
    patch_digest: str | None = None
    poc_digest: str | None = None
    oracle_digest: str | None = None
    authority: bool = False

    @property
    def case_digest(self) -> str:
        return _digest("AURA_BUGHOUND_HISTORICAL_CASE_V1", asdict(self))


@dataclass(frozen=True)
class HistoricalBlindPacketV1:
    target_id: str
    corpus_id: str
    repo_url: str
    vulnerable_commit: str
    source_tree_digest: str
    source_generation: str
    as_of: str
    visible_evidence: tuple[tuple[str, str, str], ...]
    mode: str
    group_key: str
    authority: bool = False
    external_effect: bool = False
    schema: str = SCHEMA

    @property
    def packet_digest(self) -> str:
        return _digest("AURA_BUGHOUND_HISTORICAL_BLIND_PACKET_V1", asdict(self))

    def to_solver_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class EvaluatorSealV1:
    target_id: str
    case_digest: str
    evaluator_generation: str
    advisory_published_at: str | None
    gold_digest: str
    sealed_classes: tuple[str, ...]
    as_of: str
    schema: str = "BugHoundHistoricalEvaluatorSealV1"

    @property
    def seal_digest(self) -> str:
        return _digest("AURA_BUGHOUND_HISTORICAL_EVALUATOR_SEAL_V1", asdict(self))


@dataclass(frozen=True)
class SplitMemberV1:
    target_id: str
    repo_url: str
    group_key: str
    partition: str


def _gold_payload(case: HistoricalCaseV1) -> dict[str, object]:
    return {
        "advisory_id": case.advisory_id,
        "cve_ids": case.cve_ids,
        "vuln_title": case.vuln_title,
        "vuln_category": case.vuln_category,
        "entry_point_gold": case.entry_point_gold,
        "critical_operation_gold": case.critical_operation_gold,
        "trace_gold": case.trace_gold,
        "fix_commit": case.fix_commit,
        "patch_digest": case.patch_digest,
        "poc_digest": case.poc_digest,
        "oracle_digest": case.oracle_digest,
    }


def compile_historical_cut(case: HistoricalCaseV1, *, as_of: str, evaluator_salt: str) -> tuple[HistoricalBlindPacketV1, EvaluatorSealV1]:
    if not isinstance(case, HistoricalCaseV1):
        raise HistoricalBlindError("HISTORICAL_CASE_REQUIRED")
    if case.authority:
        raise HistoricalBlindError("CASE_CANNOT_SELF_GRANT_AUTHORITY")
    corpus = _nonempty(case.corpus_id, "CORPUS_ID_REQUIRED")
    cid = _nonempty(case.case_id, "CASE_ID_REQUIRED")
    repo = _nonempty(case.repo_url, "REPO_URL_REQUIRED")
    commit = _nonempty(case.vulnerable_commit, "VULNERABLE_COMMIT_REQUIRED")
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise HistoricalBlindError("VULNERABLE_COMMIT_INVALID")
    source_digest = _nonempty(case.source_tree_digest, "SOURCE_TREE_DIGEST_REQUIRED")
    source_generation = _nonempty(case.source_generation, "SOURCE_GENERATION_REQUIRED")
    evaluator_generation = _nonempty(case.evaluator_generation, "EVALUATOR_GENERATION_REQUIRED")
    if not isinstance(evaluator_salt, str) or len(evaluator_salt) < 16:
        raise HistoricalBlindError("EVALUATOR_SALT_TOO_SHORT")

    cut = _dt(as_of)
    source_at = _dt(case.source_commit_at)
    if source_at > cut:
        raise HistoricalBlindError("SOURCE_NOT_YET_AVAILABLE_AT_CUT")

    advisory_at = _dt(case.advisory_published_at) if case.advisory_published_at else None
    if advisory_at is None:
        mode = MODE_HOLD
    elif cut < advisory_at:
        mode = MODE_HISTORICAL_BLIND
    else:
        mode = MODE_POST_DISCLOSURE

    visible: list[tuple[str, str, str]] = []
    for e in case.evidence:
        if not isinstance(e, TimedEvidenceV1):
            raise HistoricalBlindError("TIMED_EVIDENCE_REQUIRED")
        if e.authority:
            raise HistoricalBlindError("EVIDENCE_CANNOT_SELF_GRANT_AUTHORITY")
        _nonempty(e.evidence_class, "EVIDENCE_CLASS_REQUIRED")
        _nonempty(e.source_ref, "EVIDENCE_SOURCE_REQUIRED")
        _nonempty(e.payload_digest, "EVIDENCE_PAYLOAD_DIGEST_REQUIRED")
        _nonempty(e.provider_generation, "EVIDENCE_PROVIDER_GENERATION_REQUIRED")
        _nonempty(e.semantic_root, "EVIDENCE_SEMANTIC_ROOT_REQUIRED")
        if _dt(e.observed_at) <= cut and not e.evaluator_only:
            visible.append((e.evidence_class, e.source_ref, e.payload_digest))

    target_id = _digest("AURA_BUGHOUND_HISTORICAL_TARGET_V1", {
        "salt": evaluator_salt,
        "corpus": corpus,
        "case_id": cid,
        "repo": repo,
        "commit": commit,
        "source_tree": source_digest,
        "source_generation": source_generation,
        "as_of": cut.isoformat(),
    })[:32]
    group_key = _digest("AURA_BUGHOUND_REPO_GROUP_V1", repo.lower())[:20]

    packet = HistoricalBlindPacketV1(
        target_id=target_id,
        corpus_id=corpus,
        repo_url=repo,
        vulnerable_commit=commit,
        source_tree_digest=source_digest,
        source_generation=source_generation,
        as_of=cut.isoformat(),
        visible_evidence=tuple(sorted(visible)),
        mode=mode,
        group_key=group_key,
    )
    gold = _gold_payload(case)
    seal = EvaluatorSealV1(
        target_id=target_id,
        case_digest=case.case_digest,
        evaluator_generation=evaluator_generation,
        advisory_published_at=case.advisory_published_at,
        gold_digest=_digest("AURA_BUGHOUND_HISTORICAL_GOLD_V1", gold),
        sealed_classes=tuple(sorted(k for k, v in gold.items() if v not in (None, (), ""))),
        as_of=cut.isoformat(),
    )
    assert not packet.authority and not packet.external_effect
    return packet, seal


def validate_solver_packet(packet: HistoricalBlindPacketV1) -> None:
    if not isinstance(packet, HistoricalBlindPacketV1):
        raise HistoricalBlindError("SOLVER_PACKET_REQUIRED")
    if packet.authority or packet.external_effect:
        raise HistoricalBlindError("SOLVER_PACKET_EFFECT_FORBIDDEN")
    body = packet.to_solver_dict()
    overlap = FORBIDDEN_SOLVER_KEYS.intersection(body)
    if overlap:
        raise HistoricalBlindError("GOLD_FIELD_LEAK", ",".join(sorted(overlap)))
    serialized = json.dumps(body, sort_keys=True)
    for token in ("CVE-", "GHSA-", "entry_point_gold", "critical_operation_gold", "trace_gold", "poc", "oracle", "patch_digest"):
        if token in serialized:
            raise HistoricalBlindError("GOLD_TOKEN_LEAK", token)


def validate_group_disjoint_split(members: Iterable[SplitMemberV1]) -> None:
    groups: dict[str, set[str]] = {}
    targets: dict[str, str] = {}
    for m in members:
        if m.partition not in {"TRAIN", "VALID", "TEST"}:
            raise HistoricalBlindError("PARTITION_INVALID", m.partition)
        if m.target_id in targets and targets[m.target_id] != m.partition:
            raise HistoricalBlindError("TARGET_CROSS_PARTITION", m.target_id)
        targets[m.target_id] = m.partition
        groups.setdefault(m.group_key, set()).add(m.partition)
    for group, partitions in groups.items():
        if "TEST" in partitions and ("TRAIN" in partitions or "VALID" in partitions):
            raise HistoricalBlindError("REPO_GROUP_CROSS_PARTITION", group)


def historical_blind_eligible(packet: HistoricalBlindPacketV1) -> bool:
    validate_solver_packet(packet)
    return packet.mode == MODE_HISTORICAL_BLIND


def hyper1000() -> tuple[tuple[int, int, int], ...]:
    return tuple((a, b, c) for a in range(10) for b in range(10) for c in range(10))
