from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json
import re
from typing import Any, Sequence

SCHEMA = "AURA-CROSS-PARENT-GENERATION-REPROOF-CERTIFICATE-v1"
RECEIPT_SCHEMA = SCHEMA + "-RECEIPT"
PARENT_1_DRIVE = "1SMo6rGGZHlhVSxCnogcAoli1_g3ABhDl9XU8dlO4NE8"
PARENT_2_DRIVE = "14_ZpoejN3fecIHoAk3Oxk6e9gIiHuCHa-dT3M61MzY4"
O4_PARENT_A_OLD = "b6aca91ce25589cf581c46e4582194529ed90dda"
O4_PARENT_A_NEW = "f018e0c6709d65caaa99fcdf0cb80b62b0019090"
O4_PARENT_B_OLD = "1833f12c31e89c498235f3a6b5806b8e08036224"
O4_PARENT_B_NEW = "d5632afa107c7d9b8e95fd4a9eab73cf4ff05044"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
NEUTRAL_FIELDS = frozenset({"generation", "receipt_root", "producer_metadata", "review_metadata"})
CONSEQUENCE_BINDINGS = ("source_identity", "benchmark_generation", "envelope_id")


class ReproofError(ValueError):
    pass


class TransitionClass(str, Enum):
    EXACT_UNCHANGED = "EXACT_UNCHANGED"
    PROOF_NEUTRAL_REBIND = "PROOF_NEUTRAL_REBIND"
    CONSEQUENCE_CHANGED = "CONSEQUENCE_CHANGED"
    UNKNOWN = "UNKNOWN"


class Decision(str, Enum):
    REUSE_EXACT = "REUSE_EXACT"
    REBIND_AND_READJUDICATE = "REBIND_AND_READJUDICATE"
    REPROVE_MINIMUM_CONE = "REPROVE_MINIMUM_CONE"
    HOLD_UNKNOWN = "HOLD_UNKNOWN"


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ReproofError("NON_CANONICAL_VALUE") from exc


def digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _root(value: Any) -> bool:
    return isinstance(value, str) and bool(_HEX64.fullmatch(value))


@dataclass(frozen=True)
class ParentSnapshot:
    role: str
    producer: str
    schema: str
    generation: str
    receipt_root: str
    consequence_root: str
    source_identity: str
    benchmark_generation: str
    envelope_id: str
    verified: bool
    current: bool
    d0: bool

    def validate(self) -> None:
        for value in (
            self.role,
            self.producer,
            self.schema,
            self.generation,
            self.source_identity,
            self.benchmark_generation,
            self.envelope_id,
        ):
            if not _nonempty(value):
                raise ReproofError("INVALID_PARENT_STRING")
        for value in (self.receipt_root, self.consequence_root):
            if not _root(value):
                raise ReproofError("INVALID_PARENT_ROOT")
        for value in (self.verified, self.current, self.d0):
            if type(value) is not bool:
                raise ReproofError("INVALID_PARENT_FLAG")

    @property
    def snapshot_root(self) -> str:
        self.validate()
        return digest(asdict(self))


@dataclass(frozen=True)
class TransitionAttestation:
    role: str
    old_snapshot_root: str
    new_snapshot: ParentSnapshot
    transition_class: TransitionClass
    changed_fields: tuple[str, ...]
    owner_transition_root: str
    expected_owner_transition_root: str
    owner_verified: bool

    def validate(self) -> None:
        if not _nonempty(self.role) or not _root(self.old_snapshot_root):
            raise ReproofError("INVALID_TRANSITION_BINDING")
        self.new_snapshot.validate()
        if self.new_snapshot.role != self.role:
            raise ReproofError("TRANSITION_ROLE_MISMATCH")
        if not isinstance(self.transition_class, TransitionClass):
            raise ReproofError("INVALID_TRANSITION_CLASS")
        if not isinstance(self.changed_fields, tuple) or any(not _nonempty(x) for x in self.changed_fields):
            raise ReproofError("INVALID_CHANGED_FIELDS")
        if len(set(self.changed_fields)) != len(self.changed_fields):
            raise ReproofError("DUPLICATE_CHANGED_FIELD")
        if not _root(self.owner_transition_root) or not _root(self.expected_owner_transition_root):
            raise ReproofError("INVALID_OWNER_TRANSITION_ROOT")
        if type(self.owner_verified) is not bool:
            raise ReproofError("INVALID_OWNER_VERIFIED_FLAG")

    @property
    def attestation_root(self) -> str:
        self.validate()
        payload = asdict(self)
        payload["transition_class"] = self.transition_class.value
        return digest(payload)


@dataclass(frozen=True)
class PriorBridgeProof:
    bridge_id: str
    bridge_generation: str
    parent_a: ParentSnapshot
    parent_b: ParentSnapshot
    bridge_receipt_root: str
    d0: bool = True

    def validate(self) -> None:
        if not _nonempty(self.bridge_id) or not _nonempty(self.bridge_generation):
            raise ReproofError("INVALID_BRIDGE_ID")
        self.parent_a.validate()
        self.parent_b.validate()
        if self.parent_a.role == self.parent_b.role:
            raise ReproofError("DUPLICATE_PARENT_ROLE")
        if not _root(self.bridge_receipt_root):
            raise ReproofError("INVALID_BRIDGE_ROOT")
        if type(self.d0) is not bool or not self.d0:
            raise ReproofError("BRIDGE_NOT_D0")

    @property
    def proof_root(self) -> str:
        self.validate()
        return digest(
            {
                "bridge_id": self.bridge_id,
                "bridge_generation": self.bridge_generation,
                "parent_a_root": self.parent_a.snapshot_root,
                "parent_b_root": self.parent_b.snapshot_root,
                "bridge_receipt_root": self.bridge_receipt_root,
                "d0": self.d0,
            }
        )


@dataclass(frozen=True)
class ReproofReceipt:
    schema: str
    bridge_id: str
    prior_proof_root: str
    decision: Decision
    obligations: tuple[str, ...]
    transition_roots: tuple[str, ...]
    current_parent_roots: tuple[str, ...]
    eligible_to_readjudicate: bool
    auto_admitted: bool = False
    truth_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False

    @property
    def receipt_root(self) -> str:
        payload = asdict(self)
        payload["decision"] = self.decision.value
        return digest(payload)


def _transition_state(old: ParentSnapshot, t: TransitionAttestation) -> tuple[str, tuple[str, ...]]:
    t.validate()
    obligations: list[str] = []
    if t.old_snapshot_root != old.snapshot_root:
        return "UNKNOWN", (f"{old.role}:OLD_BINDING_MISMATCH",)
    if not t.owner_verified or t.owner_transition_root != t.expected_owner_transition_root:
        return "UNKNOWN", (f"{old.role}:VERIFY_OR_REPROVE_PARENT",)
    new = t.new_snapshot
    if not new.verified or not new.current or not new.d0:
        return "UNKNOWN", (f"{old.role}:VERIFY_OR_REPROVE_PARENT",)

    old_root = old.snapshot_root
    new_root = new.snapshot_root
    if t.transition_class is TransitionClass.EXACT_UNCHANGED:
        if old_root != new_root or t.changed_fields:
            return "UNKNOWN", (f"{old.role}:INVALID_EXACT_TRANSITION",)
        return "EXACT", ()

    if t.transition_class is TransitionClass.PROOF_NEUTRAL_REBIND:
        if old.consequence_root != new.consequence_root:
            return "REPROVE", (f"{old.role}:REPROVE_PARENT",)
        if not set(t.changed_fields).issubset(NEUTRAL_FIELDS):
            return "REPROVE", (f"{old.role}:REPROVE_PARENT",)
        if any(getattr(old, f) != getattr(new, f) for f in CONSEQUENCE_BINDINGS):
            return "REPROVE", (f"{old.role}:REPROVE_PARENT",)
        return "NEUTRAL", ()

    if t.transition_class is TransitionClass.CONSEQUENCE_CHANGED:
        return "REPROVE", (f"{old.role}:REPROVE_PARENT",)

    return "UNKNOWN", (f"{old.role}:VERIFY_OR_REPROVE_PARENT",)


def compile_reproof(prior: PriorBridgeProof, transitions: Sequence[TransitionAttestation]) -> ReproofReceipt:
    prior.validate()
    if not isinstance(transitions, Sequence) or isinstance(transitions, (str, bytes)) or len(transitions) != 2:
        raise ReproofError("EXACTLY_TWO_TRANSITIONS_REQUIRED")
    by_role: dict[str, TransitionAttestation] = {}
    for transition in transitions:
        transition.validate()
        if transition.role in by_role:
            raise ReproofError("DUPLICATE_TRANSITION_ROLE")
        by_role[transition.role] = transition
    expected = {prior.parent_a.role, prior.parent_b.role}
    if set(by_role) != expected:
        raise ReproofError("TRANSITION_ROLE_SET_MISMATCH")

    old_by_role = {prior.parent_a.role: prior.parent_a, prior.parent_b.role: prior.parent_b}
    states: dict[str, str] = {}
    obligations: list[str] = []
    current: list[ParentSnapshot] = []
    transition_roots: list[str] = []
    for role in sorted(expected):
        transition = by_role[role]
        state, obs = _transition_state(old_by_role[role], transition)
        states[role] = state
        obligations.extend(obs)
        current.append(transition.new_snapshot)
        transition_roots.append(transition.attestation_root)

    a, b = sorted(current, key=lambda s: s.role)
    cross_drift = [f for f in CONSEQUENCE_BINDINGS if getattr(a, f) != getattr(b, f)]
    if cross_drift:
        obligations.append("CROSS_BINDINGS:READJUDICATE:" + ",".join(cross_drift))

    if "UNKNOWN" in states.values():
        decision = Decision.HOLD_UNKNOWN
        if not any(x.startswith("CROSS_BINDINGS:") for x in obligations):
            obligations.append("CROSS_BINDINGS:READJUDICATE_AFTER_PARENT_PROOF")
        eligible = False
    elif "REPROVE" in states.values():
        decision = Decision.REPROVE_MINIMUM_CONE
        obligations.append("CROSS_BINDINGS:READJUDICATE_AFTER_PARENT_REPROOF")
        eligible = False
    elif cross_drift:
        decision = Decision.REPROVE_MINIMUM_CONE
        eligible = False
    elif "NEUTRAL" in states.values():
        decision = Decision.REBIND_AND_READJUDICATE
        obligations.append("CROSS_BINDINGS:READJUDICATE_CURRENT_GENERATIONS")
        eligible = True
    else:
        decision = Decision.REUSE_EXACT
        eligible = True

    obligations = tuple(dict.fromkeys(obligations))
    return ReproofReceipt(
        schema=RECEIPT_SCHEMA,
        bridge_id=prior.bridge_id,
        prior_proof_root=prior.proof_root,
        decision=decision,
        obligations=obligations,
        transition_roots=tuple(transition_roots),
        current_parent_roots=tuple(s.snapshot_root for s in sorted(current, key=lambda x: x.role)),
        eligible_to_readjudicate=eligible,
    )


def verify_receipt(prior: PriorBridgeProof, transitions: Sequence[TransitionAttestation], receipt: ReproofReceipt) -> bool:
    try:
        return receipt == compile_reproof(prior, transitions) and receipt.receipt_root == compile_reproof(prior, transitions).receipt_root
    except ReproofError:
        return False


def crystalline_admission(omega8: Sequence[int]) -> bool:
    if len(omega8) != 8 or any(type(v) is not int or v not in (0, 1, 2) for v in omega8):
        raise ReproofError("INVALID_OMEGA8")
    return tuple(omega8) == (2, 2, 2, 2, 2, 2, 2, 1)


def admission_13d(omega8: Sequence[int], tail5: Sequence[int]) -> bool:
    if len(tail5) != 5 or any(type(v) is not int or v not in (0, 1, 2) for v in tail5):
        raise ReproofError("INVALID_ROUTING5")
    return crystalline_admission(omega8)


def demo_prior() -> PriorBridgeProof:
    shared = dict(source_identity="shared-src", benchmark_generation="bench-g1", envelope_id="env-g1", verified=True, current=True, d0=True)
    a = ParentSnapshot("WORKLOAD", "AGENT_06", "WORKLOAD-CONTAMINATION-v1", O4_PARENT_A_OLD, digest({"a":"receipt-old"}), digest({"a":"consequence-old"}), **shared)
    b = ParentSnapshot("COST", "AGENT_05", "FUSED-COST-v1", O4_PARENT_B_OLD, digest({"b":"receipt-old"}), digest({"b":"consequence-old"}), **shared)
    return PriorBridgeProof("O4-CONTAMINATION-BOUND-FUSED-COST", "o4-g1", a, b, digest({"bridge":"o4"}))


def exact_transition(old: ParentSnapshot) -> TransitionAttestation:
    root = digest({"owner": old.producer, "transition": "exact"})
    return TransitionAttestation(old.role, old.snapshot_root, old, TransitionClass.EXACT_UNCHANGED, (), root, root, True)
