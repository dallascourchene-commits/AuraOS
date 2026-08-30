"""Source-owned producer registry for BugHound cash-candidate evidence.

The canonical production registry is intentionally empty. Candidate evidence can
be structurally valid and internally consistent without proving who produced it.
A consequence-bearing caller cannot create producer trust by supplying a secret,
an expected identity, or an alternate registry beside the evidence it also
supplies.

A future independently observed producer may be pinned here by repository-owned
source change. Until then, canonical admission remains a D0 trust hold.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

SCHEMA = "BugHoundCandidateEvidenceRegistryV1"
REGISTRY_GENERATION = "BUGHOUND_CANDIDATE_EVIDENCE_REGISTRY_HOLD_V1"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


class CandidateEvidenceRegistryError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class CandidateEvidenceProducerRecordV1:
    producer_ref: str
    producer_generation: str
    producer_currentness_ref: str
    evidence_bundle_digest: str
    target_ref: str
    target_generation: str
    scope_rules_digest: str
    source_currentness_ref: str
    independent_reproduction_digest: str
    duplicate_check_currentness_ref: str
    report_digest: str
    program_admissibility_ref: str
    independently_observed: bool = True
    current: bool = True
    revoked: bool = False
    authority: bool = False
    external_effect: bool = False
    schema: str = "CandidateEvidenceProducerRecordV1"

    @property
    def record_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CANDIDATE_EVIDENCE_PRODUCER_RECORD_V1", asdict(self))


# Repository-owned production trust root. Deliberately empty until a real,
# independently observed cash-candidate producer generation is pinned here.
_CANONICAL_RECORDS: tuple[CandidateEvidenceProducerRecordV1, ...] = ()


@dataclass(frozen=True)
class CandidateEvidenceRegistryReceiptV1:
    registry_generation: str
    record_digests: tuple[str, ...]
    active_producer_count: int
    authority: bool = False
    external_effect: bool = False
    schema: str = SCHEMA

    @property
    def registry_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CANDIDATE_EVIDENCE_REGISTRY_V1", asdict(self))


def candidate_evidence_registry_receipt() -> CandidateEvidenceRegistryReceiptV1:
    records = tuple(sorted(_CANONICAL_RECORDS, key=lambda record: record.record_digest))
    return CandidateEvidenceRegistryReceiptV1(
        registry_generation=REGISTRY_GENERATION,
        record_digests=tuple(record.record_digest for record in records),
        active_producer_count=sum(
            1
            for record in records
            if record.independently_observed and record.current and not record.revoked
        ),
    )


def _resolve_from_records(
    *,
    records: tuple[CandidateEvidenceProducerRecordV1, ...],
    producer_ref: str,
    producer_generation: str,
    producer_currentness_ref: str,
    evidence_bundle_digest: str,
    target_ref: str,
    target_generation: str,
    scope_rules_digest: str,
    source_currentness_ref: str,
    independent_reproduction_digest: str,
    duplicate_check_currentness_ref: str,
    report_digest: str,
    program_admissibility_ref: str,
) -> CandidateEvidenceProducerRecordV1:
    for record in records:
        if not record.independently_observed or not record.current or record.revoked:
            continue
        if record.authority or record.external_effect:
            continue
        if (
            record.producer_ref == producer_ref
            and record.producer_generation == producer_generation
            and record.producer_currentness_ref == producer_currentness_ref
            and record.evidence_bundle_digest == evidence_bundle_digest
            and record.target_ref == target_ref
            and record.target_generation == target_generation
            and record.scope_rules_digest == scope_rules_digest
            and record.source_currentness_ref == source_currentness_ref
            and record.independent_reproduction_digest == independent_reproduction_digest
            and record.duplicate_check_currentness_ref == duplicate_check_currentness_ref
            and record.report_digest == report_digest
            and record.program_admissibility_ref == program_admissibility_ref
        ):
            return record
    raise CandidateEvidenceRegistryError("CANDIDATE_EVIDENCE_PRODUCER_TRUST_UNPROVEN")


def resolve_candidate_evidence_producer(
    *,
    producer_ref: str,
    producer_generation: str,
    producer_currentness_ref: str,
    evidence_bundle_digest: str,
    target_ref: str,
    target_generation: str,
    scope_rules_digest: str,
    source_currentness_ref: str,
    independent_reproduction_digest: str,
    duplicate_check_currentness_ref: str,
    report_digest: str,
    program_admissibility_ref: str,
) -> CandidateEvidenceProducerRecordV1:
    """Resolve only against the repository-owned production registry."""
    return _resolve_from_records(
        records=_CANONICAL_RECORDS,
        producer_ref=producer_ref,
        producer_generation=producer_generation,
        producer_currentness_ref=producer_currentness_ref,
        evidence_bundle_digest=evidence_bundle_digest,
        target_ref=target_ref,
        target_generation=target_generation,
        scope_rules_digest=scope_rules_digest,
        source_currentness_ref=source_currentness_ref,
        independent_reproduction_digest=independent_reproduction_digest,
        duplicate_check_currentness_ref=duplicate_check_currentness_ref,
        report_digest=report_digest,
        program_admissibility_ref=program_admissibility_ref,
    )
