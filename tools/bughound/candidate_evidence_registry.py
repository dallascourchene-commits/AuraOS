"""Source-owned producer registry for BugHound cash-candidate evidence.

A repository-owned record is not automatically a trustworthy record. Before any
record can participate in a consequence-bearing producer lookup, its own schema,
identity, observer separation, digest shapes, exact booleans, and zero-authority
ceiling are validated.

The canonical production registry remains intentionally empty. A future real
cash-candidate producer record must be independently observed and pinned by
source change; callers cannot inject or override this registry.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re

SCHEMA = "BugHoundCandidateEvidenceRegistryV1"
RECORD_SCHEMA = "CandidateEvidenceProducerRecordV1"
REGISTRY_GENERATION = "BUGHOUND_CANDIDATE_EVIDENCE_REGISTRY_HOLD_V1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


class CandidateEvidenceRegistryError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _require_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CandidateEvidenceRegistryError(f"{name}_REQUIRED")
    return value.strip()


def _require_sha256(name: str, value: object) -> str:
    text = _require_text(name, value)
    if not _SHA256_RE.fullmatch(text):
        raise CandidateEvidenceRegistryError(f"{name}_SHA256_REQUIRED")
    return text


def _require_exact_bool(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise CandidateEvidenceRegistryError(f"{name}_EXACT_BOOL_REQUIRED")
    return value


@dataclass(frozen=True)
class CandidateEvidenceProducerRecordV1:
    producer_ref: str
    producer_generation: str
    producer_currentness_ref: str
    observer_ref: str
    observer_generation: str
    observer_currentness_ref: str
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
    schema: str = RECORD_SCHEMA

    @property
    def record_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CANDIDATE_EVIDENCE_PRODUCER_RECORD_V1", asdict(self))


def validate_candidate_evidence_producer_record(record: CandidateEvidenceProducerRecordV1) -> CandidateEvidenceProducerRecordV1:
    """Fail closed unless one source-owned record is structurally trustworthy."""
    if not isinstance(record, CandidateEvidenceProducerRecordV1):
        raise CandidateEvidenceRegistryError("CANDIDATE_EVIDENCE_RECORD_TYPE_INVALID")
    if record.schema != RECORD_SCHEMA:
        raise CandidateEvidenceRegistryError("CANDIDATE_EVIDENCE_RECORD_SCHEMA_MISMATCH")

    for name, value in (
        ("PRODUCER_REF", record.producer_ref),
        ("PRODUCER_GENERATION", record.producer_generation),
        ("PRODUCER_CURRENTNESS_REF", record.producer_currentness_ref),
        ("OBSERVER_REF", record.observer_ref),
        ("OBSERVER_GENERATION", record.observer_generation),
        ("OBSERVER_CURRENTNESS_REF", record.observer_currentness_ref),
        ("TARGET_REF", record.target_ref),
        ("TARGET_GENERATION", record.target_generation),
        ("SCOPE_RULES_DIGEST", record.scope_rules_digest),
        ("SOURCE_CURRENTNESS_REF", record.source_currentness_ref),
        ("DUPLICATE_CHECK_CURRENTNESS_REF", record.duplicate_check_currentness_ref),
        ("REPORT_DIGEST", record.report_digest),
        ("PROGRAM_ADMISSIBILITY_REF", record.program_admissibility_ref),
    ):
        _require_text(name, value)

    _require_sha256("EVIDENCE_BUNDLE_DIGEST", record.evidence_bundle_digest)
    _require_sha256("INDEPENDENT_REPRODUCTION_DIGEST", record.independent_reproduction_digest)

    if record.observer_ref == record.producer_ref:
        raise CandidateEvidenceRegistryError("CANDIDATE_EVIDENCE_OBSERVER_MUST_DIFFER_FROM_PRODUCER")

    for name, value in (
        ("INDEPENDENTLY_OBSERVED", record.independently_observed),
        ("CURRENT", record.current),
        ("REVOKED", record.revoked),
        ("AUTHORITY", record.authority),
        ("EXTERNAL_EFFECT", record.external_effect),
    ):
        _require_exact_bool(name, value)

    if record.authority or record.external_effect:
        raise CandidateEvidenceRegistryError("CANDIDATE_EVIDENCE_RECORD_AUTHORITY_WIDENED")
    return record


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
    records = tuple(validate_candidate_evidence_producer_record(record) for record in sorted(_CANONICAL_RECORDS, key=lambda item: item.record_digest))
    return CandidateEvidenceRegistryReceiptV1(
        registry_generation=REGISTRY_GENERATION,
        record_digests=tuple(record.record_digest for record in records),
        active_producer_count=sum(1 for record in records if record.independently_observed and record.current and not record.revoked),
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
    # Validate the entire source-owned registry before trusting any one member.
    validated = tuple(validate_candidate_evidence_producer_record(record) for record in records)
    for record in validated:
        if not record.independently_observed or not record.current or record.revoked:
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
