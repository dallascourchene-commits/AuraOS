from __future__ import annotations

"""Thin D0 adapter over an upstream ECF evidence owner.

This module does not authenticate signatures, register producers, mint evidence
or effect authority, or create a PKI. It consumes evidence-leaf witness roots
that the rightful upstream ECF owner has already admitted, then enforces exact
use-time cross-binding for Memory City decision surfaces.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _digest(value) -> str:
    return sha256(_canonical(value).encode()).hexdigest()


def _nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be nonempty")
    return value


def _hex64(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field} must be lowercase sha256 hex")
    return value


@dataclass(frozen=True)
class ECFCurrentCut:
    jurisdiction_id: str
    jurisdiction_generation: int
    producer_registry_root: str
    producer_id: str
    producer_incarnation: str
    evidence_scope: str
    coherent_cut_root: str

    def validate(self) -> None:
        for field in ("jurisdiction_id", "producer_id", "producer_incarnation", "evidence_scope"):
            _nonempty(getattr(self, field), field)
        if type(self.jurisdiction_generation) is not int or self.jurisdiction_generation < 0:
            raise ValueError("jurisdiction_generation must be nonnegative exact int")
        _hex64(self.producer_registry_root, "producer_registry_root")
        _hex64(self.coherent_cut_root, "coherent_cut_root")


@dataclass(frozen=True)
class ECFLeafAdmissionWitness:
    witness_id: str
    evidence_digest: str
    jurisdiction_id: str
    jurisdiction_generation: int
    producer_registry_root: str
    producer_id: str
    producer_incarnation: str
    evidence_scope: str
    coherent_cut_root: str
    authentication_witness_root: str
    evidence_authority_grant_root: str
    disposition: str = "ADMITTED_EVIDENCE_D0"
    effect_authority: bool = False
    gate10: bool = False

    def validate(self) -> None:
        for field in (
            "witness_id", "jurisdiction_id", "producer_id",
            "producer_incarnation", "evidence_scope", "disposition",
        ):
            _nonempty(getattr(self, field), field)
        if self.disposition != "ADMITTED_EVIDENCE_D0":
            raise ValueError("witness disposition must be ADMITTED_EVIDENCE_D0")
        if type(self.jurisdiction_generation) is not int or self.jurisdiction_generation < 0:
            raise ValueError("jurisdiction_generation must be nonnegative exact int")
        for field in (
            "evidence_digest", "producer_registry_root", "coherent_cut_root",
            "authentication_witness_root", "evidence_authority_grant_root",
        ):
            _hex64(getattr(self, field), field)
        if type(self.effect_authority) is not bool or type(self.gate10) is not bool:
            raise ValueError("authority flags must be exact bool")
        if self.effect_authority or self.gate10:
            raise ValueError("Memory City ECF adapter cannot consume effect/Gate10 witness")

    @property
    def witness_root(self) -> str:
        self.validate()
        return _digest({
            "schema": "AURA-ECF-LEAF-ADMISSION-WITNESS-ADAPTER-v1",
            "witness_id": self.witness_id,
            "evidence_digest": self.evidence_digest,
            "jurisdiction_id": self.jurisdiction_id,
            "jurisdiction_generation": self.jurisdiction_generation,
            "producer_registry_root": self.producer_registry_root,
            "producer_id": self.producer_id,
            "producer_incarnation": self.producer_incarnation,
            "evidence_scope": self.evidence_scope,
            "coherent_cut_root": self.coherent_cut_root,
            "authentication_witness_root": self.authentication_witness_root,
            "evidence_authority_grant_root": self.evidence_authority_grant_root,
            "disposition": self.disposition,
            "effect_authority": False,
            "gate10": False,
        })


@dataclass(frozen=True)
class ECFAdmission:
    status: str
    evidence_digest: str
    witness_root: str
    reason: str
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False


class ECFAdmissionIndex:
    """Validate exact use-site bindings for upstream-admitted ECF leaf witnesses.

    `admitted_witness_roots` is the explicit trust input from the rightful ECF
    owner. This adapter cannot populate or authenticate that set itself.
    """

    def __init__(
        self,
        current_cut: ECFCurrentCut,
        witnesses: Iterable[ECFLeafAdmissionWitness],
        *,
        admitted_witness_roots: Iterable[str],
    ):
        if not isinstance(current_cut, ECFCurrentCut):
            raise ValueError("current_cut must be ECFCurrentCut")
        current_cut.validate()
        self.current_cut = current_cut
        self._witnesses = {}
        self._witness_ids = set()
        for witness in witnesses:
            if not isinstance(witness, ECFLeafAdmissionWitness):
                raise ValueError("witnesses must be ECFLeafAdmissionWitness")
            root = witness.witness_root
            key = (witness.evidence_digest, witness.evidence_scope)
            if key in self._witnesses or witness.witness_id in self._witness_ids:
                raise ValueError("duplicate ECF witness identity")
            self._witnesses[key] = (root, witness)
            self._witness_ids.add(witness.witness_id)
        self._admitted = set(admitted_witness_roots)
        for root in self._admitted:
            _hex64(root, "admitted_witness_root")

    def resolve(self, evidence_digest: str, *, scope: str) -> ECFAdmission:
        _hex64(evidence_digest, "evidence_digest")
        _nonempty(scope, "scope")
        pair = self._witnesses.get((evidence_digest, scope))
        if pair is None:
            return ECFAdmission("HOLD_ECF_WITNESS_NOT_FOUND", evidence_digest, "", "no exact ECF witness for evidence digest/scope")
        root, witness = pair
        if root not in self._admitted:
            return ECFAdmission("HOLD_ECF_WITNESS_NOT_ADMITTED", evidence_digest, root, "upstream ECF owner has not admitted this witness root")
        cut = self.current_cut
        if witness.jurisdiction_id != cut.jurisdiction_id or witness.jurisdiction_generation != cut.jurisdiction_generation:
            return ECFAdmission("HOLD_ECF_JURISDICTION_CURRENTNESS", evidence_digest, root, "jurisdiction cut moved")
        if witness.producer_registry_root != cut.producer_registry_root:
            return ECFAdmission("HOLD_ECF_PRODUCER_REGISTRY_CURRENTNESS", evidence_digest, root, "producer registry root moved")
        if witness.producer_id != cut.producer_id or witness.producer_incarnation != cut.producer_incarnation:
            return ECFAdmission("HOLD_ECF_PRODUCER_CURRENTNESS", evidence_digest, root, "producer identity/incarnation moved")
        if witness.evidence_scope != cut.evidence_scope or scope != cut.evidence_scope:
            return ECFAdmission("HOLD_ECF_SCOPE_MISMATCH", evidence_digest, root, "evidence scope moved")
        if witness.coherent_cut_root != cut.coherent_cut_root:
            return ECFAdmission("HOLD_ECF_COHERENT_CUT_MISMATCH", evidence_digest, root, "evidence/use-time coherent cut moved")
        return ECFAdmission("ADMITTED_EVIDENCE_D0", evidence_digest, root, "exact current ECF leaf witness admitted")
