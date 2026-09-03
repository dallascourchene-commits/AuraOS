from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Iterable


def digest(x: object) -> str:
    return hashlib.sha256(
        json.dumps(x, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


@dataclass(frozen=True)
class ResearchLead:
    source_ref: str
    source_generation: str
    provider_revision: str
    semantic_root: str
    producer: str
    typed_relation: str
    transfer_basis: str
    transfer_falsifier: str
    k27: tuple[int, int, int]
    source_current: bool = True
    source_access: str = "PUBLIC"

    def validate(self) -> None:
        if not all(
            (
                self.source_ref,
                self.source_generation,
                self.provider_revision,
                self.semantic_root,
                self.producer,
                self.typed_relation,
                self.transfer_basis,
                self.transfer_falsifier,
            )
        ):
            raise ValueError("RESEARCH_BINDING_REQUIRED")
        if not self.source_current:
            raise ValueError("SOURCE_STALE")
        if self.source_access == "DENIED":
            raise ValueError("SOURCE_ACCESS_DENIED")
        if len(self.k27) != 3 or any(
            (not isinstance(v, int) or v < 0 or v > 26) for v in self.k27
        ):
            raise ValueError("K27_INVALID")

    @property
    def lease_root(self) -> str:
        self.validate()
        return digest(
            {
                "source_ref": self.source_ref,
                "provider_revision": self.provider_revision,
                "semantic_root": self.semantic_root,
                "producer": self.producer,
            }
        )


@dataclass(frozen=True)
class OwnerTarget:
    provider: str
    repository: str
    object_kind: str
    ordinal: int
    exact_head: str
    target_generation: str
    authorization: str
    target_current: bool = True

    def validate(self) -> None:
        if self.provider != "github" or "/" not in self.repository:
            raise ValueError("OWNER_NOT_QUALIFIED")
        if self.object_kind not in {"pull", "issue"} or self.ordinal <= 0:
            raise ValueError("OWNER_NOT_QUALIFIED")
        if not self.exact_head or not self.target_generation:
            raise ValueError("TARGET_BINDING_REQUIRED")
        if self.authorization != "AUTHORIZED":
            raise ValueError("TARGET_NOT_AUTHORIZED")
        if not self.target_current:
            raise ValueError("TARGET_STALE")

    @property
    def owner_ref(self) -> str:
        self.validate()
        return f"github://{self.repository}/{self.object_kind}/{self.ordinal}"


@dataclass(frozen=True)
class P0Policy:
    allowed_effect: str = "D0"
    required_rung: str = "P0"
    forbidden_actions: tuple[str, ...] = (
        "MODEL_GENERATION",
        "P1_PROFILE",
        "P2_MATCHED_EPISODES",
        "GIT_MUTATION",
        "WORKFLOW_RERUN",
        "CREDENTIAL_ACTION",
        "PUBLIC_EFFECT",
        "GATE10",
    )


@dataclass(frozen=True)
class P0Command:
    command_id: str
    idempotency_key: str
    owner_ref: str
    exact_head: str
    research_lease_root: str
    source_ref: str
    source_generation: str
    target_generation: str
    transfer_basis: str
    transfer_falsifier: str
    requested_rung: str
    effect_ceiling: str
    negative_intent: tuple[str, ...]
    k27: tuple[int, int, int]
    command_root: str


@dataclass(frozen=True)
class CommandObservation:
    command_id: str
    state: str
    owner_ref: str
    exact_head: str
    result_lease_root: str | None = None
    result_semantic_root: str | None = None
    effect_authority: bool = False


@dataclass(frozen=True)
class AdmissionReceipt:
    disposition: str
    command_id: str
    command_root: str
    evidence_state: str
    effect_authority: bool
    reason: str


class ResearchOwnerP0Admission:
    def __init__(self, policy: P0Policy = P0Policy()):
        self.policy = policy

    def compile(
        self, lead: ResearchLead, target: OwnerTarget, *, command_id: str
    ) -> P0Command:
        lead.validate()
        target.validate()
        if not command_id:
            raise ValueError("COMMAND_ID_REQUIRED")
        if not lead.transfer_basis or not lead.transfer_falsifier:
            raise ValueError("TRANSFER_CONTRACT_REQUIRED")
        body = {
            "command_id": command_id,
            "owner_ref": target.owner_ref,
            "exact_head": target.exact_head,
            "research_lease_root": lead.lease_root,
            "source_ref": lead.source_ref,
            "source_generation": lead.source_generation,
            "target_generation": target.target_generation,
            "transfer_basis": lead.transfer_basis,
            "transfer_falsifier": lead.transfer_falsifier,
            "requested_rung": self.policy.required_rung,
            "effect_ceiling": self.policy.allowed_effect,
            "negative_intent": self.policy.forbidden_actions,
            "k27": lead.k27,
        }
        root = digest(body)
        return P0Command(
            command_id,
            command_id,
            target.owner_ref,
            target.exact_head,
            lead.lease_root,
            lead.source_ref,
            lead.source_generation,
            target.target_generation,
            lead.transfer_basis,
            lead.transfer_falsifier,
            self.policy.required_rung,
            self.policy.allowed_effect,
            self.policy.forbidden_actions,
            lead.k27,
            root,
        )

    def observe(
        self, command: P0Command, observations: Iterable[CommandObservation]
    ) -> AdmissionReceipt:
        same = [o for o in observations if o.command_id == command.command_id]
        if not same:
            return AdmissionReceipt(
                "WAIT_COMMAND_OBSERVATION",
                command.command_id,
                command.command_root,
                "NONE",
                False,
                "NO_COMMAND_BOUND_OBSERVATION",
            )
        for obs in same:
            if obs.effect_authority:
                raise ValueError("OBSERVATION_AUTHORITY_WIDENING")
            if obs.owner_ref != command.owner_ref or obs.exact_head != command.exact_head:
                raise ValueError("COMMAND_TARGET_DRIFT")
        states = {o.state for o in same}
        if "RESULT" in states:
            results = [o for o in same if o.state == "RESULT"]
            if any(
                not o.result_lease_root or not o.result_semantic_root for o in results
            ):
                return AdmissionReceipt(
                    "HOLD_RESULT_UNBOUND",
                    command.command_id,
                    command.command_root,
                    "RESULT",
                    False,
                    "RESULT_MISSING_LEASE_OR_SEMANTIC_ROOT",
                )
            return AdmissionReceipt(
                "P0_RESULT_ADMISSIBLE",
                command.command_id,
                command.command_root,
                "RESULT",
                False,
                "COMMAND_BOUND_RESULT_PRESENT",
            )
        if "ACKED" in states:
            return AdmissionReceipt(
                "ACKED_WAIT_RESULT",
                command.command_id,
                command.command_root,
                "ACKED",
                False,
                "ACK_PRESENT_RESULT_ABSENT",
            )
        if "MATERIALIZED" in states:
            return AdmissionReceipt(
                "MATERIALIZED_WAIT_ACK",
                command.command_id,
                command.command_root,
                "MATERIALIZED",
                False,
                "COMMAND_EXISTS_EXECUTION_UNPROVEN",
            )
        raise ValueError("UNKNOWN_COMMAND_STATE")
