"""Registered isolation-backend admission for BugHound Arena R1.

R0 deliberately models only a logical local capsule. This module adds the
*admission* membrane for a stronger R1 isolation backend without implementing or
pretending to execute one. A backend attestation is useful only after an
independent, source-owned registry pins the exact attestation generation.

Production intentionally starts with an empty immutable registry. Therefore a
caller cannot manufacture ``os_network_isolation_proven`` (or any sibling
containment claim) by passing booleans, a registry, or a self-chosen trust root.
Even a registered backend proves backend-policy admission only; a later runtime
execution receipt must separately prove that a particular capsule actually ran
under that backend.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from types import MappingProxyType
from typing import Mapping

from tools.bughound.arena_runtime import (
    NETWORK_OFF,
    BugHoundArenaRuntimeR0SpecV1,
)
from tools.bughound.target_profile import bind_target_profile

ATTESTATION_SCHEMA = "BugHoundIsolationBackendAttestationV1"
REGISTRY_SCHEMA = "BugHoundIsolationBackendRegistryRecordV1"
ADMISSION_SCHEMA = "BugHoundRegisteredIsolationBackendV1"

CONFINED = "CONFINED_BY_BACKEND_POLICY"
NO_SECRETS = "NO_CREDENTIALS_AVAILABLE"
NO_HOST_WRITABLE_MOUNTS = "NO_HOST_WRITABLE_MOUNTS"
NO_HOST_PRIVILEGE = "NO_HOST_PRIVILEGE"
DENY_BY_DEFAULT = "DENY_BY_DEFAULT"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


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


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")


def _require_sha256(name: str, value: str) -> None:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{name}_SHA256_REQUIRED")


def _require_exact_bool(name: str, value: object, expected: bool) -> None:
    if type(value) is not bool or value is not expected:
        suffix = "REQUIRED" if expected else "FORBIDDEN"
        raise ValueError(f"{name}_{suffix}")


@dataclass(frozen=True)
class BugHoundIsolationBackendAttestationV1:
    backend_id: str
    backend_generation: str
    backend_kind: str
    implementation_digest: str
    policy_digest: str
    platform_ref: str
    filesystem_confinement: str
    network_confinement: str
    ipc_confinement: str
    syscall_confinement: str
    secrets_policy: str
    host_writable_mounts_policy: str
    privilege_policy: str
    egress_policy: str
    audit_log_digest: str
    source_currentness_ref: str
    attester_ref: str
    attester_generation: str
    current: bool
    backend_policy_observed: bool
    external_effect: bool = False
    schema: str = ATTESTATION_SCHEMA

    @property
    def attestation_digest(self) -> str:
        return _digest("AURA_BUGHOUND_R1_ISOLATION_ATTESTATION_V1", asdict(self))


@dataclass(frozen=True)
class BugHoundIsolationBackendRegistryRecordV1:
    backend_id: str
    backend_generation: str
    attestation_digest: str
    registry_receipt_ref: str
    observer_ref: str
    observer_generation: str
    current: bool
    independently_observed: bool
    revoked: bool
    external_effect: bool = False
    schema: str = REGISTRY_SCHEMA

    @property
    def record_digest(self) -> str:
        return _digest("AURA_BUGHOUND_R1_ISOLATION_REGISTRY_V1", asdict(self))


@dataclass(frozen=True)
class BugHoundRegisteredIsolationBackendV1:
    backend_id: str
    backend_generation: str
    backend_kind: str
    attestation_digest: str
    registry_record_digest: str
    profile_receipt_digest: str
    profile_id: str
    target_ref: str
    target_generation: str
    source_digest: str
    filesystem_confinement: str
    network_confinement: str
    ipc_confinement: str
    syscall_confinement: str
    secrets_policy: str
    host_writable_mounts_policy: str
    privilege_policy: str
    egress_policy: str
    registered_backend_policy_proven: bool
    capsule_execution_under_backend_proven: bool = False
    os_network_isolation_for_capsule_proven: bool = False
    live_target_testing_authorized: bool = False
    credential_use_authorized: bool = False
    submission_authorized: bool = False
    payout_authority: bool = False
    external_effect: bool = False
    schema: str = ADMISSION_SCHEMA

    @property
    def admission_digest(self) -> str:
        return _digest("AURA_BUGHOUND_REGISTERED_R1_ISOLATION_BACKEND_V1", asdict(self))


# Production trust root. It is deliberately code-owned, immutable, and empty
# until an independently observed backend attestation is intentionally pinned.
TRUSTED_ISOLATION_BACKEND_REGISTRY: Mapping[
    str,
    tuple[BugHoundIsolationBackendAttestationV1, BugHoundIsolationBackendRegistryRecordV1],
] = MappingProxyType({})


def _validate_r0_spec(spec: BugHoundArenaRuntimeR0SpecV1):
    if spec.network_policy != NETWORK_OFF:
        raise ValueError("BUGHOUND_R1_REQUIRES_R0_LOGICAL_NETWORK_OFF")
    if spec.credential_refs:
        raise ValueError("BUGHOUND_R1_R0_CREDENTIALS_FORBIDDEN")
    _require_text("R0_SOURCE_DIGEST", spec.source_digest)
    return bind_target_profile(spec.profile)


def _validate_attestation(att: BugHoundIsolationBackendAttestationV1) -> None:
    if not isinstance(att, BugHoundIsolationBackendAttestationV1) or att.schema != ATTESTATION_SCHEMA:
        raise ValueError("BUGHOUND_R1_ATTESTATION_SCHEMA_MISMATCH")
    for name, value in (
        ("BACKEND_ID", att.backend_id),
        ("BACKEND_GENERATION", att.backend_generation),
        ("BACKEND_KIND", att.backend_kind),
        ("PLATFORM_REF", att.platform_ref),
        ("SOURCE_CURRENTNESS_REF", att.source_currentness_ref),
        ("ATTESTER_REF", att.attester_ref),
        ("ATTESTER_GENERATION", att.attester_generation),
    ):
        _require_text(name, value)
    for name, value in (
        ("IMPLEMENTATION_DIGEST", att.implementation_digest),
        ("POLICY_DIGEST", att.policy_digest),
        ("AUDIT_LOG_DIGEST", att.audit_log_digest),
    ):
        _require_sha256(name, value)
    _require_exact_bool("BUGHOUND_R1_ATTESTATION_CURRENT", att.current, True)
    _require_exact_bool("BUGHOUND_R1_BACKEND_POLICY_OBSERVED", att.backend_policy_observed, True)
    _require_exact_bool("BUGHOUND_R1_ATTESTATION_EXTERNAL_EFFECT", att.external_effect, False)
    for name, value in (
        ("FILESYSTEM", att.filesystem_confinement),
        ("NETWORK", att.network_confinement),
        ("IPC", att.ipc_confinement),
        ("SYSCALL", att.syscall_confinement),
    ):
        if value != CONFINED:
            raise ValueError(f"BUGHOUND_R1_{name}_CONFINEMENT_REQUIRED")
    if att.secrets_policy != NO_SECRETS:
        raise ValueError("BUGHOUND_R1_NO_SECRETS_POLICY_REQUIRED")
    if att.host_writable_mounts_policy != NO_HOST_WRITABLE_MOUNTS:
        raise ValueError("BUGHOUND_R1_HOST_WRITABLE_MOUNTS_FORBIDDEN")
    if att.privilege_policy != NO_HOST_PRIVILEGE:
        raise ValueError("BUGHOUND_R1_NO_HOST_PRIVILEGE_REQUIRED")
    if att.egress_policy != DENY_BY_DEFAULT:
        raise ValueError("BUGHOUND_R1_DENY_BY_DEFAULT_EGRESS_REQUIRED")


def _validate_registry_record(
    att: BugHoundIsolationBackendAttestationV1,
    record: BugHoundIsolationBackendRegistryRecordV1,
) -> None:
    if not isinstance(record, BugHoundIsolationBackendRegistryRecordV1) or record.schema != REGISTRY_SCHEMA:
        raise ValueError("BUGHOUND_R1_REGISTRY_SCHEMA_MISMATCH")
    for name, value in (
        ("REGISTRY_RECEIPT_REF", record.registry_receipt_ref),
        ("REGISTRY_OBSERVER_REF", record.observer_ref),
        ("REGISTRY_OBSERVER_GENERATION", record.observer_generation),
    ):
        _require_text(name, value)
    _require_sha256("REGISTRY_ATTESTATION_DIGEST", record.attestation_digest)
    _require_exact_bool("BUGHOUND_R1_REGISTRY_CURRENT", record.current, True)
    _require_exact_bool(
        "BUGHOUND_R1_REGISTRY_INDEPENDENT_OBSERVATION",
        record.independently_observed,
        True,
    )
    _require_exact_bool("BUGHOUND_R1_BACKEND_REVOKED", record.revoked, False)
    _require_exact_bool("BUGHOUND_R1_REGISTRY_EXTERNAL_EFFECT", record.external_effect, False)
    if record.backend_id != att.backend_id:
        raise ValueError("BUGHOUND_R1_REGISTRY_BACKEND_ID_MISMATCH")
    if record.backend_generation != att.backend_generation:
        raise ValueError("BUGHOUND_R1_REGISTRY_BACKEND_GENERATION_MISMATCH")
    if record.attestation_digest != att.attestation_digest:
        raise ValueError("BUGHOUND_R1_REGISTRY_ATTESTATION_DIGEST_MISMATCH")
    if record.observer_ref == att.attester_ref:
        raise ValueError("BUGHOUND_R1_REGISTRY_OBSERVER_NOT_INDEPENDENT")


def _admit_registered_isolation_backend_with_registry(
    *,
    r0_spec: BugHoundArenaRuntimeR0SpecV1,
    backend_id: str,
    registry: Mapping[
        str,
        tuple[BugHoundIsolationBackendAttestationV1, BugHoundIsolationBackendRegistryRecordV1],
    ],
) -> BugHoundRegisteredIsolationBackendV1:
    """Private/test plumbing for evaluating an explicitly supplied registry."""
    _require_text("BACKEND_ID", backend_id)
    profile = _validate_r0_spec(r0_spec)
    entry = registry.get(backend_id)
    if entry is None:
        raise ValueError("BUGHOUND_R1_ISOLATION_BACKEND_REQUIRED")
    att, record = entry
    _validate_attestation(att)
    _validate_registry_record(att, record)
    if att.backend_id != backend_id:
        raise ValueError("BUGHOUND_R1_REQUESTED_BACKEND_ID_MISMATCH")

    return BugHoundRegisteredIsolationBackendV1(
        backend_id=att.backend_id,
        backend_generation=att.backend_generation,
        backend_kind=att.backend_kind,
        attestation_digest=att.attestation_digest,
        registry_record_digest=record.record_digest,
        profile_receipt_digest=profile.receipt_digest,
        profile_id=profile.profile_id,
        target_ref=profile.target_ref,
        target_generation=profile.target_generation,
        source_digest=r0_spec.source_digest,
        filesystem_confinement=att.filesystem_confinement,
        network_confinement=att.network_confinement,
        ipc_confinement=att.ipc_confinement,
        syscall_confinement=att.syscall_confinement,
        secrets_policy=att.secrets_policy,
        host_writable_mounts_policy=att.host_writable_mounts_policy,
        privilege_policy=att.privilege_policy,
        egress_policy=att.egress_policy,
        registered_backend_policy_proven=True,
    )


def admit_registered_isolation_backend_for_r0(
    *,
    r0_spec: BugHoundArenaRuntimeR0SpecV1,
    backend_id: str,
) -> BugHoundRegisteredIsolationBackendV1:
    """Resolve one R1 backend through the production source-owned registry.

    The public consequence-bearing API intentionally exposes no registry,
    attestation, isolation booleans, trust flag, verifier secret, or expected
    producer metadata. Production therefore fails closed until a canonical
    independently observed backend generation is pinned in source.
    """
    return _admit_registered_isolation_backend_with_registry(
        r0_spec=r0_spec,
        backend_id=backend_id,
        registry=TRUSTED_ISOLATION_BACKEND_REGISTRY,
    )
