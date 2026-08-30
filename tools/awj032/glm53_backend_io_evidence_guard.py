"""AWJ032-GLM53-05A backend I/O evidence guard.

D0/nonpromoting. This module is not a pager or checkpoint owner. It validates the
optional physical-I/O attestation emitted by a packed/per-expert backend before
GLM53-05/W4 is allowed to consume that evidence for laptop-feasibility math.

A logical selected-expert API is not physical-I/O proof. Missing telemetry stays
UNKNOWN. An attestation that reports non-selected physical reads, any whole-bank
read, or whole-bank materialization is unsafe and fails closed instead of being
accepted as a successful feasibility sample.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping

BACKEND_IO_ATTESTATION_SCHEMA = "AuraExpertPagerBackendIOAttestationV1"
W4_EVIDENCE_SCHEMA = "AuraGLM53W4BackendEvidenceV1"


class BackendEvidenceError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _nonneg_int(raw: Any, code: str, *, optional: bool = False) -> int | None:
    if raw is None and optional:
        return None
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        raise BackendEvidenceError(code)
    return raw


def _optional_text(raw: Any, code: str) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise BackendEvidenceError(code)
    return raw.strip()


@dataclass(frozen=True)
class W4BackendEvidence:
    schema: str
    binding_digest: str
    attestation_id: str | None
    physical_io_attested: bool
    physical_selected_only: bool | None
    whole_bank_reads: int | None
    whole_bank_materialized: bool | None
    physical_expert_bytes_read: int | None
    physical_read_operations: int | None
    read_elapsed_ms: float | None
    page_cache_provenance: str | None
    w4_metrics_complete: bool
    w4_admissible: bool
    g2_admitted: bool = False
    claim_ceiling: str = "D0_BACKEND_IO_EVIDENCE_ONLY_NO_MODEL_RUNTIME_OR_G2_PROOF"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_backend_evidence(backend: Any, *, binding_digest: str) -> W4BackendEvidence:
    """Validate a backend's source-bound physical-I/O attestation.

    The existing pager ABI treats absent attestation as UNKNOWN. W4 additionally
    requires exact physical expert bytes, physical read-operation count, elapsed
    read time, and page-cache provenance before a sample can enter feasibility
    calculations. These metrics are additive fields on the existing V1 mapping so
    existing pager backends remain compatible but are not silently promoted.
    """
    if not isinstance(binding_digest, str) or not binding_digest.strip():
        raise BackendEvidenceError("BINDING_DIGEST_REQUIRED")
    binding_digest = binding_digest.strip()
    attestor = getattr(backend, "io_attestation", None)
    if not callable(attestor):
        return W4BackendEvidence(
            schema=W4_EVIDENCE_SCHEMA,
            binding_digest=binding_digest,
            attestation_id=None,
            physical_io_attested=False,
            physical_selected_only=None,
            whole_bank_reads=None,
            whole_bank_materialized=None,
            physical_expert_bytes_read=None,
            physical_read_operations=None,
            read_elapsed_ms=None,
            page_cache_provenance=None,
            w4_metrics_complete=False,
            w4_admissible=False,
        )

    raw = attestor(binding_digest)
    if not isinstance(raw, Mapping):
        raise BackendEvidenceError("BACKEND_IO_ATTESTATION_INVALID")
    if raw.get("schema") != BACKEND_IO_ATTESTATION_SCHEMA:
        raise BackendEvidenceError("BACKEND_IO_ATTESTATION_SCHEMA_MISMATCH")
    if raw.get("binding_digest") != binding_digest:
        raise BackendEvidenceError("BACKEND_IO_ATTESTATION_BINDING_MISMATCH")

    attestation_id = _optional_text(raw.get("attestation_id"), "BACKEND_IO_ATTESTATION_ID_INVALID")
    if attestation_id is None:
        raise BackendEvidenceError("BACKEND_IO_ATTESTATION_ID_REQUIRED")
    selected_only = raw.get("physical_selected_only")
    if not isinstance(selected_only, bool):
        raise BackendEvidenceError("BACKEND_PHYSICAL_SELECTED_ONLY_INVALID")
    whole_reads = _nonneg_int(raw.get("whole_bank_reads"), "BACKEND_WHOLE_BANK_READS_INVALID")
    whole_materialized = raw.get("whole_bank_materialized")
    if not isinstance(whole_materialized, bool):
        raise BackendEvidenceError("BACKEND_WHOLE_BANK_MATERIALIZED_INVALID")

    # 05A safety membrane: an unsafe physical observation is not a dirty PASS.
    if not selected_only:
        raise BackendEvidenceError("PHYSICAL_SELECTED_ONLY_VIOLATION")
    if whole_reads != 0:
        raise BackendEvidenceError("WHOLE_BANK_PHYSICAL_READ_FORBIDDEN", str(whole_reads))
    if whole_materialized:
        raise BackendEvidenceError("WHOLE_BANK_MATERIALIZATION_FORBIDDEN")

    physical_bytes = _nonneg_int(
        raw.get("physical_expert_bytes_read"), "PHYSICAL_EXPERT_BYTES_INVALID", optional=True
    )
    read_operations = _nonneg_int(
        raw.get("physical_read_operations"), "PHYSICAL_READ_OPERATIONS_INVALID", optional=True
    )
    elapsed_raw = raw.get("read_elapsed_ms")
    if elapsed_raw is None:
        elapsed_ms = None
    elif isinstance(elapsed_raw, bool) or not isinstance(elapsed_raw, (int, float)) or elapsed_raw < 0:
        raise BackendEvidenceError("READ_ELAPSED_MS_INVALID")
    else:
        elapsed_ms = float(elapsed_raw)
    page_cache = _optional_text(raw.get("page_cache_provenance"), "PAGE_CACHE_PROVENANCE_INVALID")

    complete = all(
        value is not None for value in (physical_bytes, read_operations, elapsed_ms, page_cache)
    )
    return W4BackendEvidence(
        schema=W4_EVIDENCE_SCHEMA,
        binding_digest=binding_digest,
        attestation_id=attestation_id,
        physical_io_attested=True,
        physical_selected_only=True,
        whole_bank_reads=0,
        whole_bank_materialized=False,
        physical_expert_bytes_read=physical_bytes,
        physical_read_operations=read_operations,
        read_elapsed_ms=elapsed_ms,
        page_cache_provenance=page_cache,
        w4_metrics_complete=complete,
        w4_admissible=complete,
    )
