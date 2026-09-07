from __future__ import annotations

"""D0 possibility-envelope-identity-bound horizon certificate.

This is an adversarial repair of a horizon handoff that binds observation epoch
and support identity but not the exact consequence-relevant possibility set.
Irrelevant hidden configuration is intentionally excluded from the envelope
identity; a newly possible consequence-relevant world is not.
"""

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable

from .demand_lease_handoff import DemandCellLease, canonical_lease_root

SCHEMA = "AURA-MEMORY-CITY-ENVELOPE-BOUND-HORIZON-v1"


def _root(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field} must be lowercase SHA-256 hex")
    return value


def _nni(value: int, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a non-negative exact int")
    return value


def _hash(payload: object) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class HorizonDisposition(str, Enum):
    READY_D0 = "READY_D0"
    REBIND_REQUIRED = "REBIND_REQUIRED"
    HOLD = "HOLD"


@dataclass(frozen=True)
class ConsequenceWorld:
    support_closure_root: str
    reproof_closure_root: str
    authority_projection_root: str
    support_identity_root: str
    transition_signature_root: str
    irrelevant_config_root: str

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            _root(value, name)

    def relevant_projection(self) -> tuple[str, ...]:
        return (
            self.support_closure_root,
            self.reproof_closure_root,
            self.authority_projection_root,
            self.support_identity_root,
            self.transition_signature_root,
        )


@dataclass(frozen=True)
class PossibilityEnvelope:
    worlds: tuple[ConsequenceWorld, ...]
    completeness_generation: int

    def __post_init__(self) -> None:
        if not isinstance(self.worlds, tuple) or not self.worlds or any(not isinstance(w, ConsequenceWorld) for w in self.worlds):
            raise ValueError("worlds must be a non-empty tuple of ConsequenceWorld")
        _nni(self.completeness_generation, "completeness_generation")

    def consequence_envelope_root(self) -> str:
        # Exact set of consequence-relevant possible-world projections.
        # Multiplicity and irrelevant configuration are intentionally quotiented.
        projections = sorted(set(w.relevant_projection() for w in self.worlds))
        return _hash({"schema": SCHEMA, "kind": "consequence_envelope", "projections": projections})

    def uniform_consequence_root(self, current_support_identity_root: str) -> str | None:
        _root(current_support_identity_root, "current_support_identity_root")
        projections = {w.relevant_projection() for w in self.worlds}
        if len(projections) != 1:
            return None
        projection = next(iter(projections))
        if projection[3] != current_support_identity_root:
            return None
        return _hash({"schema": SCHEMA, "kind": "uniform_consequence", "projection": projection})

    def full_hidden_root(self) -> str:
        # Deliberately stricter baseline used only for falsification.
        return _hash({"schema": SCHEMA, "kind": "full_hidden", "worlds": sorted(tuple(w.__dict__.values()) for w in self.worlds)})


@dataclass(frozen=True)
class EnvelopeCompletenessReceipt:
    consequence_envelope_root: str
    completeness_generation: int
    authority_source_root: str
    verifier_receipt_root: str

    def __post_init__(self) -> None:
        _root(self.consequence_envelope_root, "consequence_envelope_root")
        _nni(self.completeness_generation, "completeness_generation")
        _root(self.authority_source_root, "authority_source_root")
        _root(self.verifier_receipt_root, "verifier_receipt_root")

    def canonical_receipt_root(self) -> str:
        return _hash({
            "schema": SCHEMA, "kind": "envelope_completeness_receipt",
            "consequence_envelope_root": self.consequence_envelope_root,
            "completeness_generation": self.completeness_generation,
            "authority_source_root": self.authority_source_root,
            "verifier_receipt_root": self.verifier_receipt_root,
        })


@dataclass(frozen=True)
class EnvelopeVerificationContext:
    authority_source_root: str
    verifier_receipt_root: str

    def __post_init__(self) -> None:
        _root(self.authority_source_root, "authority_source_root")
        _root(self.verifier_receipt_root, "verifier_receipt_root")


def _completeness_current(envelope: PossibilityEnvelope, receipt: EnvelopeCompletenessReceipt, verification: EnvelopeVerificationContext) -> bool:
    return (
        isinstance(receipt, EnvelopeCompletenessReceipt)
        and isinstance(verification, EnvelopeVerificationContext)
        and receipt.consequence_envelope_root == envelope.consequence_envelope_root()
        and receipt.completeness_generation == envelope.completeness_generation
        and receipt.authority_source_root == verification.authority_source_root
        and receipt.verifier_receipt_root == verification.verifier_receipt_root
    )


@dataclass(frozen=True)
class HorizonCertificate:
    lease_root: str
    support_identity_root: str
    observation_epoch: int
    horizon: int
    completeness_generation: int
    consequence_envelope_root: str
    uniform_consequence_root: str
    completeness_receipt_root: str
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        for field in ("lease_root", "support_identity_root", "consequence_envelope_root", "uniform_consequence_root", "completeness_receipt_root"):
            _root(getattr(self, field), field)
        _nni(self.observation_epoch, "observation_epoch")
        _nni(self.horizon, "horizon")
        _nni(self.completeness_generation, "completeness_generation")
        if self.authority_minted or self.effect_authority or self.gate10:
            raise ValueError("D0 horizon certificate cannot mint authority")


@dataclass(frozen=True)
class HorizonDecision:
    disposition: HorizonDisposition
    reason: str
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, HorizonDisposition):
            raise ValueError("disposition must be HorizonDisposition")
        if not isinstance(self.reason, str) or not self.reason:
            raise ValueError("reason required")
        if self.authority_minted or self.effect_authority or self.gate10:
            raise ValueError("D0 horizon decision cannot mint authority")


def issue_horizon_certificate(
    lease: DemandCellLease,
    envelope: PossibilityEnvelope,
    completeness_receipt: EnvelopeCompletenessReceipt,
    verification: EnvelopeVerificationContext,
    *,
    current_support_identity_root: str,
    observation_epoch: int,
    horizon: int,
) -> tuple[HorizonDecision, HorizonCertificate | None]:
    if not isinstance(lease, DemandCellLease) or not isinstance(envelope, PossibilityEnvelope):
        raise ValueError("typed lease and envelope required")
    if not isinstance(completeness_receipt, EnvelopeCompletenessReceipt) or not isinstance(verification, EnvelopeVerificationContext):
        raise ValueError("typed completeness evidence required")
    _root(current_support_identity_root, "current_support_identity_root")
    _nni(observation_epoch, "observation_epoch")
    _nni(horizon, "horizon")
    if not _completeness_current(envelope, completeness_receipt, verification):
        return HorizonDecision(HorizonDisposition.HOLD, "POSSIBILITY_ENVELOPE_COMPLETENESS_UNPROVED"), None
    uniform = envelope.uniform_consequence_root(current_support_identity_root)
    if uniform is None:
        return HorizonDecision(HorizonDisposition.HOLD, "CONSEQUENCE_DIVERGENCE_OR_SUPPORT_IDENTITY_MISMATCH"), None
    cert = HorizonCertificate(
        lease_root=canonical_lease_root(lease),
        support_identity_root=current_support_identity_root,
        observation_epoch=observation_epoch,
        horizon=horizon,
        completeness_generation=envelope.completeness_generation,
        consequence_envelope_root=envelope.consequence_envelope_root(),
        uniform_consequence_root=uniform,
        completeness_receipt_root=completeness_receipt.canonical_receipt_root(),
    )
    return HorizonDecision(HorizonDisposition.READY_D0, "ENVELOPE_BOUND_HORIZON_CERTIFIED"), cert


def admit_horizon_certificate(
    certificate: HorizonCertificate,
    lease: DemandCellLease,
    envelope: PossibilityEnvelope,
    completeness_receipt: EnvelopeCompletenessReceipt,
    verification: EnvelopeVerificationContext,
    *,
    current_support_identity_root: str,
    observation_epoch: int,
    horizon: int,
) -> HorizonDecision:
    if not isinstance(certificate, HorizonCertificate) or not isinstance(lease, DemandCellLease) or not isinstance(envelope, PossibilityEnvelope):
        raise ValueError("typed certificate, lease and envelope required")
    if not isinstance(completeness_receipt, EnvelopeCompletenessReceipt) or not isinstance(verification, EnvelopeVerificationContext):
        raise ValueError("typed completeness evidence required")
    _root(current_support_identity_root, "current_support_identity_root")
    _nni(observation_epoch, "observation_epoch")
    _nni(horizon, "horizon")
    if not _completeness_current(envelope, completeness_receipt, verification):
        return HorizonDecision(HorizonDisposition.HOLD, "POSSIBILITY_ENVELOPE_COMPLETENESS_UNPROVED")
    if canonical_lease_root(lease) != certificate.lease_root:
        return HorizonDecision(HorizonDisposition.REBIND_REQUIRED, "LEASE_IDENTITY_MOVED")
    if current_support_identity_root != certificate.support_identity_root:
        return HorizonDecision(HorizonDisposition.REBIND_REQUIRED, "SUPPORT_IDENTITY_MOVED")
    if observation_epoch != certificate.observation_epoch:
        return HorizonDecision(HorizonDisposition.REBIND_REQUIRED, "OBSERVATION_EPOCH_MOVED")
    if horizon != certificate.horizon:
        return HorizonDecision(HorizonDisposition.REBIND_REQUIRED, "HORIZON_MOVED")
    if envelope.completeness_generation != certificate.completeness_generation:
        return HorizonDecision(HorizonDisposition.REBIND_REQUIRED, "ENVELOPE_COMPLETENESS_GENERATION_MOVED")
    if completeness_receipt.canonical_receipt_root() != certificate.completeness_receipt_root:
        return HorizonDecision(HorizonDisposition.REBIND_REQUIRED, "ENVELOPE_COMPLETENESS_RECEIPT_MOVED")
    if envelope.consequence_envelope_root() != certificate.consequence_envelope_root:
        return HorizonDecision(HorizonDisposition.REBIND_REQUIRED, "POSSIBILITY_ENVELOPE_IDENTITY_MOVED")
    uniform = envelope.uniform_consequence_root(current_support_identity_root)
    if uniform is None:
        return HorizonDecision(HorizonDisposition.HOLD, "CONSEQUENCE_DIVERGENCE_OR_SUPPORT_IDENTITY_MISMATCH")
    if uniform != certificate.uniform_consequence_root:
        return HorizonDecision(HorizonDisposition.REBIND_REQUIRED, "UNIFORM_CONSEQUENCE_MOVED")
    return HorizonDecision(HorizonDisposition.READY_D0, "EXACT_ENVELOPE_BOUND_HORIZON_REUSE")
