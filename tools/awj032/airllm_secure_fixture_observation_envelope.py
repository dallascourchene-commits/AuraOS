"""Secure tiny-fixture runtime -> physical-observation envelope for AWJ-032.

D0 / HS1 / NONPROMOTING.

This module is a relation-only bridge between two independently owned evidence
planes:

* PR #311: AirLLM HARD_FALSE source/runtime and tiny standard-architecture fixture.
* PR #408: physical-I/O accounting must be observer/backend-attested, workload
  scoped, provenance complete, and must keep latency overlap separate from byte
  avoidance.

The bridge deliberately does NOT reinterpret the AirLLM tiny Llama fixture as a
GLM-5.3 benchmark or reuse PR #408's GLM-specific reducer on the Llama fixture.
It only defines the common provenance envelope a later host observation must
satisfy before physical counters may be associated with the exact fixture run.

No model admission, GLM performance, G2/G3 promotion, transfer authority,
provider effect, K27 semantic authority, or private/native transformer KV access
is granted here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

SCHEMA = "AURA-AWJ032-SECURE-FIXTURE-OBSERVATION-ENVELOPE-v1"
AIRLLM_FIXTURE_SCHEMA = "AWJ032_AIRLLM_TINY_FIXTURE_RUNTIME_RECEIPT_V1"
PHYSICAL_OBSERVATION_SCHEMA = "AURA-HOST-PHYSICAL-IO-OBSERVATION-v1"

AIRLLM_SOURCE_HEAD = "d951404e0ba15a04682f47610f4643ce55d9ff7e"
W4_SOURCE_HEAD = "3a7c562f2e0f278bc3f350416ff243893d0eb0ff"

BOUND = "SECURE_FIXTURE_PHYSICAL_OBSERVATION_BOUND"
HOLD = "HOLD_PHYSICAL_OBSERVATION_REQUIRED"

HEX = frozenset("0123456789abcdef")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _required(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value.strip()


def _sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in HEX for ch in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")
    return value


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name}_MUST_BE_NONNEGATIVE_INT")
    return value


@dataclass(frozen=True)
class SecureTinyFixtureProjection:
    """Minimal projection of PR #311's bounded tiny-runtime receipt."""

    schema: str
    source_head: str
    status: str
    model_id: str
    model_revision: str
    workload_ref: str
    device: str
    fixture_manifest_digest: str
    split_manifest_digest: str
    runtime_guard_receipt_digest: str
    first_generated_token_count: int
    reopen_generated_token_count: int
    split_manifest_reopen_stable: bool
    remote_code_authorized: bool = False
    large_checkpoint_used: bool = False
    provider_used: bool = False
    glm53_performance_proven: bool = False
    model_admission_granted: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        if (self.schema, self.source_head) != (AIRLLM_FIXTURE_SCHEMA, AIRLLM_SOURCE_HEAD):
            raise ValueError("FIXTURE_EXACT_PR311_SOURCE_REQUIRED")
        if self.status != "PASS":
            raise ValueError("FIXTURE_PASS_REQUIRED")
        for value, name in (
            (self.model_id, "FIXTURE_MODEL_ID"),
            (self.model_revision, "FIXTURE_MODEL_REVISION"),
            (self.workload_ref, "FIXTURE_WORKLOAD_REF"),
            (self.device, "FIXTURE_DEVICE"),
        ):
            _required(value, name)
        for value, name in (
            (self.fixture_manifest_digest, "FIXTURE_MANIFEST_DIGEST"),
            (self.split_manifest_digest, "SPLIT_MANIFEST_DIGEST"),
            (self.runtime_guard_receipt_digest, "RUNTIME_GUARD_RECEIPT_DIGEST"),
        ):
            _sha256(value, name)
        if self.first_generated_token_count < 1 or self.reopen_generated_token_count < 1:
            raise ValueError("FIXTURE_GENERATION_ADVANCE_REQUIRED")
        if self.split_manifest_reopen_stable is not True:
            raise ValueError("FIXTURE_SPLIT_REOPEN_STABILITY_REQUIRED")
        if any(
            (
                self.remote_code_authorized,
                self.large_checkpoint_used,
                self.provider_used,
                self.glm53_performance_proven,
                self.model_admission_granted,
                self.semantic_k27_authority,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError("FIXTURE_CLAIM_CEILING_WIDENED")

    @property
    def fixture_identity_digest(self) -> str:
        self.validate()
        return _sha(
            {
                "domain": AIRLLM_FIXTURE_SCHEMA,
                "source_head": self.source_head,
                "model_id": self.model_id,
                "model_revision": self.model_revision,
                "workload_ref": self.workload_ref,
                "device": self.device,
                "fixture_manifest_digest": self.fixture_manifest_digest,
                "split_manifest_digest": self.split_manifest_digest,
                "runtime_guard_receipt_digest": self.runtime_guard_receipt_digest,
            }
        )


@dataclass(frozen=True)
class HostPhysicalObservationProjection:
    """Operation-bound physical counter observation; not a GLM W4 receipt."""

    schema: str
    observer_generation: str
    backend_owner_ref: str
    operation_id: str
    workload_ref: str
    source_generation: str
    fixture_identity_digest: str
    fixture_manifest_digest: str
    split_manifest_digest: str
    physical_io_attestation_ref: str
    logical_bytes_required: int
    physical_demand_bytes: int
    prefetch_useful_bytes: int
    prefetch_waste_bytes: int
    aura_cache_avoided_bytes: int
    os_cache_avoided_bytes: int
    other_proven_avoided_bytes: int
    physical_io_attested: bool = True
    observer_current: bool = True
    exact_operation_bound: bool = True
    avoided_bytes_provenance_complete: bool = True
    glm53_workload: bool = False
    execution_authority_granted: bool = False
    provider_effect_authority_granted: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        if self.schema != PHYSICAL_OBSERVATION_SCHEMA:
            raise ValueError("PHYSICAL_OBSERVATION_SCHEMA_MISMATCH")
        for value, name in (
            (self.observer_generation, "OBSERVER_GENERATION"),
            (self.backend_owner_ref, "BACKEND_OWNER_REF"),
            (self.operation_id, "OPERATION_ID"),
            (self.workload_ref, "OBSERVATION_WORKLOAD_REF"),
            (self.source_generation, "OBSERVATION_SOURCE_GENERATION"),
            (self.physical_io_attestation_ref, "PHYSICAL_IO_ATTESTATION_REF"),
        ):
            _required(value, name)
        for value, name in (
            (self.fixture_identity_digest, "OBSERVATION_FIXTURE_IDENTITY_DIGEST"),
            (self.fixture_manifest_digest, "OBSERVATION_FIXTURE_MANIFEST_DIGEST"),
            (self.split_manifest_digest, "OBSERVATION_SPLIT_MANIFEST_DIGEST"),
        ):
            _sha256(value, name)
        logical = _nonnegative_int(self.logical_bytes_required, "LOGICAL_BYTES_REQUIRED")
        demand = _nonnegative_int(self.physical_demand_bytes, "PHYSICAL_DEMAND_BYTES")
        useful = _nonnegative_int(self.prefetch_useful_bytes, "PREFETCH_USEFUL_BYTES")
        waste = _nonnegative_int(self.prefetch_waste_bytes, "PREFETCH_WASTE_BYTES")
        aura = _nonnegative_int(self.aura_cache_avoided_bytes, "AURA_CACHE_AVOIDED_BYTES")
        os_avoided = _nonnegative_int(self.os_cache_avoided_bytes, "OS_CACHE_AVOIDED_BYTES")
        other = _nonnegative_int(self.other_proven_avoided_bytes, "OTHER_PROVEN_AVOIDED_BYTES")
        consumed = demand + useful
        if logical <= 0:
            raise ValueError("LOGICAL_BYTES_REQUIRED_MUST_BE_POSITIVE")
        if consumed > logical:
            raise ValueError("PHYSICAL_CONSUMED_BYTES_EXCEED_LOGICAL_REQUIRED")
        if (aura + os_avoided + other) != (logical - consumed):
            raise ValueError("AVOIDED_BYTE_ACCOUNTING_MUST_CLOSE_EXACTLY")
        if self.physical_io_attested is not True:
            raise ValueError("PHYSICAL_IO_ATTESTATION_REQUIRED")
        if self.observer_current is not True:
            raise ValueError("PHYSICAL_IO_OBSERVER_CURRENTNESS_REQUIRED")
        if self.exact_operation_bound is not True:
            raise ValueError("EXACT_OPERATION_BOUND_PHYSICAL_RECEIPT_REQUIRED")
        if self.avoided_bytes_provenance_complete is not True:
            raise ValueError("AVOIDED_BYTES_PROVENANCE_COMPLETE_REQUIRED")
        if self.glm53_workload is not False:
            raise ValueError("TINY_FIXTURE_CANNOT_BE_CROSSCAST_AS_GLM53_WORKLOAD")
        if any(
            (
                self.execution_authority_granted,
                self.provider_effect_authority_granted,
                self.semantic_k27_authority,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError("PHYSICAL_OBSERVATION_CLAIM_CEILING_WIDENED")
        del waste  # waste is physical cost but does not enter avoided-byte closure.

    @property
    def observation_digest(self) -> str:
        self.validate()
        return _sha({"domain": PHYSICAL_OBSERVATION_SCHEMA, "observation": asdict(self)})


@dataclass(frozen=True)
class SecureFixtureObservationEnvelope:
    schema: str
    disposition: str
    reason_code: str
    relation_id: str | None
    fixture_identity_digest: str
    physical_observation_digest: str | None
    operation_id: str | None
    workload_ref: str
    physical_observation_bound: bool
    hard_false_runtime_preserved: bool = True
    collision_cognition_preserved: bool = True
    tiny_fixture_crosscast_to_glm53: bool = False
    glm53_performance_proven: bool = False
    model_admission_granted: bool = False
    execution_authority_granted: bool = False
    provider_effect_authority_granted: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False

    @property
    def receipt_digest(self) -> str:
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})


def bind_secure_fixture_observation(
    *,
    fixture: SecureTinyFixtureProjection,
    observation: HostPhysicalObservationProjection | None,
) -> SecureFixtureObservationEnvelope:
    fixture.validate()
    fixture_id = fixture.fixture_identity_digest

    common = dict(
        fixture_identity_digest=fixture_id,
        workload_ref=fixture.workload_ref,
    )

    if observation is None:
        return SecureFixtureObservationEnvelope(
            schema=SCHEMA,
            disposition=HOLD,
            reason_code="OPERATION_BOUND_BACKEND_PHYSICAL_OBSERVATION_NOT_PRESENT",
            relation_id=None,
            physical_observation_digest=None,
            operation_id=None,
            physical_observation_bound=False,
            **common,
        )

    observation.validate()
    exact = (
        observation.workload_ref == fixture.workload_ref
        and observation.source_generation == fixture.source_head
        and observation.fixture_identity_digest == fixture_id
        and observation.fixture_manifest_digest == fixture.fixture_manifest_digest
        and observation.split_manifest_digest == fixture.split_manifest_digest
    )
    if not exact:
        return SecureFixtureObservationEnvelope(
            schema=SCHEMA,
            disposition="HOLD_FIXTURE_OBSERVATION_IDENTITY_MISMATCH",
            reason_code="FIXTURE_RUNTIME_AND_PHYSICAL_OBSERVATION_DO_NOT_COMMUTE",
            relation_id=None,
            physical_observation_digest=observation.observation_digest,
            operation_id=observation.operation_id,
            physical_observation_bound=False,
            **common,
        )

    observation_digest = observation.observation_digest
    relation_id = _sha(
        {
            "domain": SCHEMA,
            "airllm_source_head": AIRLLM_SOURCE_HEAD,
            "w4_rule_source_head": W4_SOURCE_HEAD,
            "fixture_identity_digest": fixture_id,
            "physical_observation_digest": observation_digest,
            "operation_id": observation.operation_id,
            "observer_generation": observation.observer_generation,
            "backend_owner_ref": observation.backend_owner_ref,
            "physical_io_attestation_ref": observation.physical_io_attestation_ref,
            "authority_ceiling": "FIXTURE_OBSERVATION_RELATION_ONLY_NONPROMOTING",
        }
    )
    return SecureFixtureObservationEnvelope(
        schema=SCHEMA,
        disposition=BOUND,
        reason_code="HARD_FALSE_FIXTURE_BOUND_TO_EXACT_OPERATION_PHYSICAL_OBSERVATION",
        relation_id=relation_id,
        physical_observation_digest=observation_digest,
        operation_id=observation.operation_id,
        physical_observation_bound=True,
        **common,
    )
