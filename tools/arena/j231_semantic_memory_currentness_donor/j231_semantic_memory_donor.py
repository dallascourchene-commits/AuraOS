from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Any, Iterable, Mapping, Sequence


def stable(v: Any) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(v: Any) -> str:
    return sha256(stable(v)).hexdigest()


def source_sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9_]+", text.lower()))


def _features(text: str) -> tuple[str, ...]:
    t = _tokens(text)
    out = list(t)
    out.extend(f"{a}::{b}" for a, b in zip(t, t[1:]))
    return tuple(out)


def _hdc192(text: str) -> int:
    acc = [0] * 192
    feats = _features(text)
    if not feats:
        feats = ("<empty>",)
    for feat in feats:
        h = sha256(feat.encode()).digest()
        bits = int.from_bytes(h + sha256(b"2" + feat.encode()).digest() + sha256(b"3" + feat.encode()).digest(), "big")
        for i in range(192):
            acc[i] += 1 if (bits >> i) & 1 else -1
    return sum(1 << i for i, x in enumerate(acc) if x >= 0)


def _ham(a: int, b: int) -> int:
    return (a ^ b).bit_count()


@dataclass(frozen=True)
class WorkBudget:
    max_records: int = 4096
    max_semantic_bytes: int = 8 * 1024 * 1024
    max_record_bytes: int = 65536
    max_feature_bits: int = 192 * 1_000_000
    max_lexical_refs: int = 2_000_000
    max_query_bytes: int = 16384
    max_query_feature_bits: int = 192 * 8192
    max_candidate_postings: int = 65536

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive int")


@dataclass(frozen=True)
class LifecycleRecord:
    identity: str
    semantic_text: str
    exact_source: str
    generation: str
    revision_id: str
    lifecycle_epoch: int
    k27: tuple[int, int, int]
    current: bool = True

    def __post_init__(self) -> None:
        if not self.identity or not self.generation or not self.revision_id:
            raise ValueError("identity/generation/revision required")
        if type(self.lifecycle_epoch) is not int or self.lifecycle_epoch < 0:
            raise ValueError("nonnegative lifecycle_epoch required")
        if len(self.k27) != 3 or any(type(x) is not int or not 0 <= x <= 26 for x in self.k27):
            raise ValueError("K27 digits must be ints in [0,26]")
        if type(self.current) is not bool:
            raise ValueError("current must be bool")


@dataclass(frozen=True)
class LifecycleReceipt:
    identity: str
    source_sha256: str
    semantic_sha256: str
    generation: str
    revision_id: str
    lifecycle_epoch: int
    observed_s: int
    index_generation: str
    receipt_digest: str

    @classmethod
    def build(cls, record: LifecycleRecord, observed_s: int, index_generation: str) -> "LifecycleReceipt":
        if type(observed_s) is not int or observed_s < 0:
            raise ValueError("observed_s must be nonnegative int")
        body = [record.identity, source_sha(record.exact_source), source_sha(record.semantic_text),
                record.generation, record.revision_id, record.lifecycle_epoch, observed_s, index_generation]
        return cls(record.identity, body[1], body[2], record.generation, record.revision_id,
                   record.lifecycle_epoch, observed_s, index_generation, digest(body))

    def verify(self) -> bool:
        body = [self.identity, self.source_sha256, self.semantic_sha256, self.generation, self.revision_id,
                self.lifecycle_epoch, self.observed_s, self.index_generation]
        return self.receipt_digest == digest(body)


@dataclass(frozen=True)
class CandidatePlane:
    query_digest: str
    candidate_ids: tuple[str, ...]
    index_generation: str
    semantic_index_root: str
    receipt_root: str

    @classmethod
    def build(cls, query: str, ids: Sequence[str], index_generation: str, semantic_index_root: str) -> "CandidatePlane":
        qd = digest(query)
        ids_t = tuple(ids)
        root = digest([qd, list(ids_t), index_generation, semantic_index_root])
        return cls(qd, ids_t, index_generation, semantic_index_root, root)

    def verify(self, query: str) -> bool:
        return self.query_digest == digest(query) and self.receipt_root == digest(
            [self.query_digest, list(self.candidate_ids), self.index_generation, self.semantic_index_root]
        )


@dataclass(frozen=True)
class AtUseCapsule:
    identity: str
    exact_source: str
    source_sha256: str
    semantic_sha256: str
    generation: str
    revision_id: str
    lifecycle_epoch: int
    candidate_plane_root: str
    semantic_receipt_root: str
    authority: Mapping[str, bool]


class GovernedSemanticMemory:
    """D0 semantic candidate/reopen plane. Never owns Frontier/native routing or effects."""

    AUTHORITY = {"truth": False, "currentness": False, "effect": False,
                 "router_authority": False, "candidate_hint_only": True}

    def __init__(self, *, index_generation: str, budget: WorkBudget | None = None, prefix_bits: int = 12):
        if not index_generation:
            raise ValueError("index_generation required")
        if not 1 <= prefix_bits <= 24:
            raise ValueError("prefix_bits must be in [1,24]")
        self.index_generation = index_generation
        self.budget = budget or WorkBudget()
        self.prefix_bits = prefix_bits
        self.records: dict[str, LifecycleRecord] = {}
        self.receipts: dict[str, LifecycleReceipt] = {}
        self.signatures: dict[str, int] = {}
        self.prefix: dict[int, list[str]] = defaultdict(list)
        self.lex: dict[str, set[str]] = defaultdict(set)
        self.total_semantic_bytes = 0
        self.total_feature_bits = 0
        self.total_lexical_refs = 0

    def _prefix(self, sig: int) -> int:
        return sig >> (192 - self.prefix_bits)

    def add(self, record: LifecycleRecord, observed_s: int) -> LifecycleReceipt:
        if record.identity in self.records:
            raise ValueError("immutable index generation rejects duplicate identity")
        nbytes = len(record.semantic_text.encode("utf-8"))
        feats = _features(record.semantic_text)
        feat_bits = max(1, len(feats)) * 192
        lex_refs = len(set(_tokens(record.semantic_text)))
        b = self.budget
        if len(self.records) + 1 > b.max_records: raise ValueError("WORK_BUDGET_RECORDS")
        if nbytes > b.max_record_bytes: raise ValueError("WORK_BUDGET_RECORD_BYTES")
        if self.total_semantic_bytes + nbytes > b.max_semantic_bytes: raise ValueError("WORK_BUDGET_SEMANTIC_BYTES")
        if self.total_feature_bits + feat_bits > b.max_feature_bits: raise ValueError("WORK_BUDGET_FEATURE_BITS")
        if self.total_lexical_refs + lex_refs > b.max_lexical_refs: raise ValueError("WORK_BUDGET_LEXICAL_REFS")

        sig = _hdc192(record.semantic_text)
        receipt = LifecycleReceipt.build(record, observed_s, self.index_generation)
        self.records[record.identity] = record
        self.receipts[record.identity] = receipt
        self.signatures[record.identity] = sig
        self.prefix[self._prefix(sig)].append(record.identity)
        for term in set(_tokens(record.semantic_text)):
            self.lex[term].add(record.identity)
        self.total_semantic_bytes += nbytes
        self.total_feature_bits += feat_bits
        self.total_lexical_refs += lex_refs
        return receipt

    @property
    def semantic_index_root(self) -> str:
        rows = [[i, self.signatures[i], self.records[i].k27] for i in sorted(self.records)]
        return digest([self.index_generation, self.prefix_bits, rows])

    def candidate_plane(self, query: str, *, k: int = 32, max_hamming: int = 72) -> CandidatePlane:
        if type(k) is not int or not 1 <= k <= self.budget.max_candidate_postings:
            raise ValueError("WORK_BUDGET_K")
        qbytes = len(query.encode("utf-8"))
        qfeats = _features(query)
        if qbytes > self.budget.max_query_bytes: raise ValueError("WORK_BUDGET_QUERY_BYTES")
        if max(1, len(qfeats)) * 192 > self.budget.max_query_feature_bits: raise ValueError("WORK_BUDGET_QUERY_FEATURE_BITS")
        qsig = _hdc192(query)
        qterms = set(_tokens(query))
        semantic = list(self.prefix.get(self._prefix(qsig), ()))
        lexical: set[str] = set()
        for t in qterms:
            lexical.update(self.lex.get(t, ()))
        if len(semantic) + len(lexical) > self.budget.max_candidate_postings:
            raise ValueError("WORK_BUDGET_CANDIDATE_POSTINGS")
        pool = set(semantic) | lexical
        ranked = []
        for identity in pool:
            d = _ham(qsig, self.signatures[identity])
            overlap = len(qterms & set(_tokens(self.records[identity].semantic_text)))
            if overlap or d <= max_hamming:
                ranked.append((0 if overlap else 1, d, identity))
        ids = tuple(x[2] for x in sorted(ranked)[:k])
        return CandidatePlane.build(query, ids, self.index_generation, self.semantic_index_root)

    @staticmethod
    def stable_union(frontier_candidates: Sequence[str], semantic_candidates: Sequence[str]) -> tuple[str, ...]:
        """Frontier/native order is immutable; semantic IDs append only if unseen."""
        return tuple(dict.fromkeys([*frontier_candidates, *semantic_candidates]))

    def reopen_current(self, identity: str, current: LifecycleRecord, *, now_s: int, max_age_s: int) -> bool:
        old = self.records.get(identity)
        receipt = self.receipts.get(identity)
        if old is None or receipt is None or current.identity != identity or type(now_s) is not int or type(max_age_s) is not int:
            return False
        if not receipt.verify() or receipt.index_generation != self.index_generation or not current.current:
            return False
        age = now_s - receipt.observed_s
        if age < 0 or age > max_age_s:
            return False
        return (
            receipt.source_sha256 == source_sha(current.exact_source)
            and receipt.semantic_sha256 == source_sha(current.semantic_text)
            and receipt.generation == current.generation
            and receipt.revision_id == current.revision_id
            and receipt.lifecycle_epoch == current.lifecycle_epoch
        )

    def capture_at_use(self, query: str, plane: CandidatePlane, identity: str, current: LifecycleRecord,
                       *, now_s: int, max_age_s: int) -> AtUseCapsule | None:
        if not plane.verify(query) or plane.index_generation != self.index_generation:
            return None
        if plane.semantic_index_root != self.semantic_index_root or identity not in plane.candidate_ids:
            return None
        if not self.reopen_current(identity, current, now_s=now_s, max_age_s=max_age_s):
            return None
        receipt = self.receipts[identity]
        exact = str(current.exact_source)
        return AtUseCapsule(identity, exact, source_sha(exact), source_sha(current.semantic_text), current.generation, current.revision_id,
                            current.lifecycle_epoch, plane.receipt_root, receipt.receipt_digest, dict(self.AUTHORITY))


SEMANTIC_DAG: Mapping[str, tuple[str, ...]] = {
    "RAW_SOURCE_STATE": (),
    "SEMANTIC_FIELDS": (),
    "ENCODER_PROFILE": (),
    "COMPRESSION_PROFILE": (),
    "ROUTING_PROFILE": (),
    "WORK_POLICY": (),
    "SIGNATURE": ("SEMANTIC_FIELDS", "ENCODER_PROFILE", "COMPRESSION_PROFILE", "WORK_POLICY"),
    "LEXICAL_INDEX": ("SEMANTIC_FIELDS", "WORK_POLICY"),
    "PREFIX_INDEX": ("SIGNATURE", "ROUTING_PROFILE", "WORK_POLICY"),
    "K27_INDEX": ("SEMANTIC_FIELDS",),
    "CURRENTNESS_RECEIPT": ("RAW_SOURCE_STATE", "SEMANTIC_FIELDS", "ENCODER_PROFILE", "COMPRESSION_PROFILE"),
    "CANDIDATE_PLANE": ("LEXICAL_INDEX", "PREFIX_INDEX", "K27_INDEX", "ROUTING_PROFILE", "WORK_POLICY"),
    "AT_USE_CAPSULE": ("CURRENTNESS_RECEIPT", "CANDIDATE_PLANE"),
}


def reproof_cone(changed: Iterable[str]) -> tuple[str, ...]:
    changed_set = set(changed)
    if not changed_set or any(x not in SEMANTIC_DAG for x in changed_set):
        raise ValueError("known changed roots required")
    rev: dict[str, set[str]] = defaultdict(set)
    for node, deps in SEMANTIC_DAG.items():
        for dep in deps:
            rev[dep].add(node)
    out = set(changed_set)
    todo = list(changed_set)
    while todo:
        n = todo.pop()
        for child in rev[n]:
            if child not in out:
                out.add(child); todo.append(child)
    return tuple(sorted(out))


@dataclass(frozen=True)
class ReleaseEvidence:
    expected_semantic_head: str
    observed_semantic_head: str
    observed_carrier_head: str
    movement_kind: str
    metadata_only_verified: bool
    donor_source_sha256: str
    expected_source_sha256: str
    donor_test_sha256: str
    expected_test_sha256: str
    campaign_sha256: str
    expected_campaign_sha256: str
    local_proof_root: str
    expected_local_proof_root: str
    hosted_pass: bool = False
    independent_review_pass: bool = False
    gate10_pass: bool = False
    effect_authority: bool = False


@dataclass(frozen=True)
class ReleaseDecision:
    state: str
    reasons: tuple[str, ...]
    authority_minted: bool = False
    gate10: bool = False
    effect_authority: bool = False


def release_gate(e: ReleaseEvidence) -> ReleaseDecision:
    reasons: list[str] = []
    if e.observed_semantic_head != e.expected_semantic_head:
        reasons.append("SEMANTIC_HEAD_DRIFT")
    if e.movement_kind not in {"EXACT", "METADATA_ONLY", "SEMANTIC_OR_UNKNOWN"}:
        reasons.append("MOVEMENT_KIND_INVALID")
    if e.movement_kind == "SEMANTIC_OR_UNKNOWN":
        reasons.append("CARRIER_MOVEMENT_NOT_QUOTIENTABLE")
    if e.movement_kind == "EXACT" and e.observed_carrier_head != e.expected_semantic_head:
        reasons.append("CARRIER_HEAD_NOT_EXACT")
    if e.movement_kind == "METADATA_ONLY" and not e.metadata_only_verified:
        reasons.append("METADATA_ONLY_UNVERIFIED")
    if e.donor_source_sha256 != e.expected_source_sha256: reasons.append("SOURCE_BYTES_DRIFT")
    if e.donor_test_sha256 != e.expected_test_sha256: reasons.append("TEST_BYTES_DRIFT")
    if e.campaign_sha256 != e.expected_campaign_sha256: reasons.append("CAMPAIGN_BYTES_DRIFT")
    if e.local_proof_root != e.expected_local_proof_root: reasons.append("LOCAL_PROOF_ROOT_DRIFT")
    for name in ("metadata_only_verified", "hosted_pass", "independent_review_pass", "gate10_pass", "effect_authority"):
        if type(getattr(e, name)) is not bool:
            reasons.append(f"{name.upper()}_TYPE_INVALID")
    if reasons:
        return ReleaseDecision("HOLD", tuple(sorted(set(reasons))))
    if not e.hosted_pass:
        return ReleaseDecision("LOCAL_D0_GREEN_HOSTED_PENDING", ())
    return ReleaseDecision("READY_FOR_INDEPENDENT_REVIEW", ())
