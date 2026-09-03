from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Iterable

SCHEMA = "AuraClaimBoundEffectTimePermitV1"


def digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True)
class ClaimKey:
    project: str
    subject: str
    claim: str
    domain: str

    def validate(self) -> None:
        if not all((self.project, self.subject, self.claim, self.domain)):
            raise ValueError("CLAIM_KEY_BINDING_REQUIRED")

    @property
    def identity(self) -> str:
        self.validate()
        return digest(asdict(self))


@dataclass(frozen=True)
class ClaimEvidence:
    key: ClaimKey
    source_ref: str
    source_generation: str
    semantic_root: str
    producer: str
    authority_boundary: str
    current: bool = True

    def validate(self) -> None:
        self.key.validate()
        if not all((self.source_ref, self.source_generation, self.semantic_root, self.producer, self.authority_boundary)):
            raise ValueError("CLAIM_EVIDENCE_BINDING_REQUIRED")
        if not self.current:
            raise ValueError("CLAIM_EVIDENCE_STALE")

    @property
    def atom(self) -> dict:
        self.validate()
        return {
            "claim_key": asdict(self.key),
            "source_ref": self.source_ref,
            "source_generation": self.source_generation,
            "semantic_root": self.semantic_root,
            "producer": self.producer,
            "authority_boundary": self.authority_boundary,
        }

    @property
    def atom_root(self) -> str:
        return digest(self.atom)


@dataclass(frozen=True)
class EffectTarget:
    owner_ref: str
    command_head: str
    live_head: str
    target_generation: str
    owner_authorization: str
    target_current: bool = True

    def validate_owner_ref(self) -> None:
        if not self.owner_ref.startswith("github://") or "/pull/" not in self.owner_ref:
            raise ValueError("OWNER_REF_QUALIFIED_REQUIRED")
        if not all((self.command_head, self.live_head, self.target_generation)):
            raise ValueError("TARGET_BINDING_REQUIRED")


@dataclass(frozen=True)
class EffectTimeDisposition:
    state: str
    live_head: str
    effect_authority: bool
    reason: str


@dataclass(frozen=True)
class CompressedPermit:
    schema: str
    owner_ref: str
    exact_head: str
    target_generation: str
    required_claim_ids: tuple[str, ...]
    claim_atom_roots: tuple[str, ...]
    reopen_refs: tuple[str, ...]
    commitment_root: str
    effect_authority: bool = False
    gate10: bool = False


@dataclass(frozen=True)
class EquivalenceWitness:
    disposition: str
    commitment_root: str
    required_claim_count: int
    atom_count: int
    exact_head: str
    protected_semantics_preserved: bool
    effect_authority: bool = False


class EffectTimePermitCompiler:
    def assess_target(self, target: EffectTarget) -> EffectTimeDisposition:
        target.validate_owner_ref()
        if target.command_head != target.live_head:
            return EffectTimeDisposition(
                "INVALIDATE_STALE_COMMAND",
                target.live_head,
                False,
                "COMMAND_HEAD_DIFFERS_FROM_EFFECT_TIME_LIVE_HEAD",
            )
        if not target.target_current:
            return EffectTimeDisposition("HOLD_TARGET_STALE", target.live_head, False, "TARGET_NOT_CURRENT")
        if target.owner_authorization != "AUTHORIZED":
            return EffectTimeDisposition(
                "OWNER_REAUTHORIZATION_REQUIRED",
                target.live_head,
                False,
                "EFFECT_TIME_OWNER_AUTHORIZATION_ABSENT",
            )
        return EffectTimeDisposition("READY_FOR_CLAIM_EVIDENCE", target.live_head, False, "HEAD_AND_OWNER_AUTH_CURRENT")

    def compile(
        self,
        target: EffectTarget,
        required_claims: Iterable[ClaimKey],
        evidence: Iterable[ClaimEvidence],
        *,
        reopen_refs: Iterable[str],
    ) -> CompressedPermit:
        disposition = self.assess_target(target)
        if disposition.state != "READY_FOR_CLAIM_EVIDENCE":
            raise ValueError(disposition.state)
        required = tuple(sorted(required_claims, key=lambda k: k.identity))
        if not required:
            raise ValueError("REQUIRED_CLAIMS_EMPTY")
        required_ids = tuple(k.identity for k in required)
        if len(set(required_ids)) != len(required_ids):
            raise ValueError("DUPLICATE_REQUIRED_CLAIM")

        by_id: dict[str, ClaimEvidence] = {}
        for item in evidence:
            item.validate()
            key_id = item.key.identity
            if key_id in by_id:
                if by_id[key_id].atom_root != item.atom_root:
                    raise ValueError("CONFLICTING_CLAIM_EVIDENCE")
                continue
            by_id[key_id] = item

        extra = set(by_id) - set(required_ids)
        if extra:
            raise ValueError("UNREQUESTED_CLAIM_EVIDENCE")
        missing = set(required_ids) - set(by_id)
        if missing:
            raise ValueError("MISSING_REQUIRED_CLAIM_EVIDENCE")

        atom_roots = tuple(by_id[key_id].atom_root for key_id in required_ids)
        refs = tuple(sorted(set(reopen_refs)))
        if not refs or any(not ref for ref in refs):
            raise ValueError("REOPEN_REFS_REQUIRED")
        body = {
            "schema": SCHEMA,
            "owner_ref": target.owner_ref,
            "exact_head": target.live_head,
            "target_generation": target.target_generation,
            "required_claim_ids": required_ids,
            "claim_atom_roots": atom_roots,
            "reopen_refs": refs,
            "effect_authority": False,
            "gate10": False,
        }
        return CompressedPermit(
            SCHEMA,
            target.owner_ref,
            target.live_head,
            target.target_generation,
            required_ids,
            atom_roots,
            refs,
            digest(body),
        )

    def verify_equivalence(
        self,
        target: EffectTarget,
        required_claims: Iterable[ClaimKey],
        evidence: Iterable[ClaimEvidence],
        permit: CompressedPermit,
        *,
        reopen_refs: Iterable[str],
    ) -> EquivalenceWitness:
        expected = self.compile(target, required_claims, evidence, reopen_refs=reopen_refs)
        if expected != permit:
            raise ValueError("COMPRESSED_PERMIT_NOT_EQUIVALENT")
        return EquivalenceWitness(
            "EQUIVALENT_READY_TO_COMPILE_P0",
            permit.commitment_root,
            len(permit.required_claim_ids),
            len(permit.claim_atom_roots),
            permit.exact_head,
            True,
            False,
        )
