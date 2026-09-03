from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping

SCHEMA = "AuraCrossCityBridgeABIV1"

PORTABLE_KINDS = frozenset({
    "IDENTITY_PROVENANCE",
    "SOUVENIR",
    "LEARNING_CANDIDATE",
    "QUALIFICATION_EVIDENCE",
    "WORK_SAMPLE",
    "SOURCE_POINTER",
    "CERTIFICATION_EVIDENCE",
})
NONPORTABLE_KINDS = frozenset({"MEMBERSHIP", "LEASE", "EFFECT_PERMIT", "LOCAL_VISA"})

EVIDENCE_DOMAINS = frozenset({
    "SOURCE_SECURITY",
    "RUNTIME_CAPABILITY",
    "PHYSICAL_OBSERVATION",
    "CORRECTNESS",
    "CAUSAL_BENEFIT",
    "PROVENANCE",
    "TIMING",
    "MEMORY",
    "ENERGY",
    "OWNER_AUTHORITY",
    "LEGAL_COMMUNITY_DISPOSITION",
    "HUMAN_GATE",
})
NONPORTABLE_GATE_DOMAINS = frozenset({
    "OWNER_AUTHORITY", "LEGAL_COMMUNITY_DISPOSITION", "HUMAN_GATE"
})


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


@dataclass(frozen=True)
class EvidenceLeaf:
    domain: str
    digest: str
    source_ref: str
    generation: str
    current: bool = True

    def validate(self) -> None:
        if self.domain not in EVIDENCE_DOMAINS:
            raise ValueError("UNKNOWN_EVIDENCE_DOMAIN")
        if not all((self.digest, self.source_ref, self.generation)):
            raise ValueError("EVIDENCE_BINDING_REQUIRED")
        if self.domain in NONPORTABLE_GATE_DOMAINS:
            raise ValueError("NONPORTABLE_EVIDENCE_DOMAIN")


@dataclass(frozen=True)
class WalletItem:
    kind: str
    digest: str
    source_ref: str
    generation: str
    current: bool = True
    privacy_clearance: bool = True

    def validate(self) -> None:
        if not all((self.kind, self.digest, self.source_ref, self.generation)):
            raise ValueError("WALLET_BINDING_REQUIRED")
        if self.kind not in PORTABLE_KINDS | NONPORTABLE_KINDS:
            raise ValueError("UNKNOWN_WALLET_KIND")
        if self.kind in NONPORTABLE_KINDS:
            raise ValueError("NONPORTABLE_WALLET_KIND")
        if not self.current:
            raise ValueError("STALE_WALLET_ITEM")
        if not self.privacy_clearance:
            raise ValueError("PRIVACY_CUSTOMS_HOLD")


@dataclass(frozen=True)
class BridgeContract:
    bridge_id: str
    schema_version: str
    exporting_jurisdiction: str
    exporting_owner: str
    importing_jurisdiction: str
    importing_owner: str
    semantic_type: str
    allowed_transformations: tuple[str, ...]
    forbidden_casts: tuple[str, ...]
    required_evidence_domains: tuple[str, ...]
    required_local_gates: tuple[str, ...]
    dependency_invalidators: tuple[str, ...]
    max_cost_units: int
    replay_semantics: str = "IDEMPOTENT_BY_ENVELOPE_DIGEST"
    authority_ceiling: str = "NO_AUTHORITY_PROMOTION"

    def validate(self) -> None:
        required = (
            self.bridge_id,
            self.schema_version,
            self.exporting_jurisdiction,
            self.exporting_owner,
            self.importing_jurisdiction,
            self.importing_owner,
            self.semantic_type,
            self.replay_semantics,
            self.authority_ceiling,
        )
        if not all(required):
            raise ValueError("BRIDGE_BINDING_REQUIRED")
        if self.exporting_jurisdiction == self.importing_jurisdiction:
            raise ValueError("CROSS_JURISDICTION_REQUIRED")
        if self.max_cost_units <= 0:
            raise ValueError("INVALID_COST_CAP")
        if set(self.allowed_transformations) & set(self.forbidden_casts):
            raise ValueError("TRANSFORM_POLICY_CONFLICT")
        if not self.allowed_transformations:
            raise ValueError("ALLOWED_TRANSFORM_REQUIRED")
        unknown = set(self.required_evidence_domains) - EVIDENCE_DOMAINS
        if unknown:
            raise ValueError("UNKNOWN_REQUIRED_EVIDENCE_DOMAIN")
        if set(self.required_evidence_domains) & NONPORTABLE_GATE_DOMAINS:
            raise ValueError("LOCAL_GATE_CANNOT_BE_PORTABLE_EVIDENCE")
        if set(self.required_local_gates) - NONPORTABLE_GATE_DOMAINS:
            raise ValueError("UNKNOWN_LOCAL_GATE")
        if self.authority_ceiling != "NO_AUTHORITY_PROMOTION":
            raise ValueError("AUTHORITY_WIDENING")
        if self.replay_semantics != "IDEMPOTENT_BY_ENVELOPE_DIGEST":
            raise ValueError("UNSUPPORTED_REPLAY_SEMANTICS")

    @property
    def contract_digest(self) -> str:
        self.validate()
        return digest(asdict(self))


@dataclass(frozen=True)
class BridgeEnvelope:
    bridge_id: str
    source_ref: str
    provider_generation: str
    semantic_root: str
    semantic_type: str
    requested_transformation: str
    evidence: tuple[EvidenceLeaf, ...]
    wallet_items: tuple[WalletItem, ...]
    cost_units: int

    def validate(self) -> None:
        if not all((
            self.bridge_id,
            self.source_ref,
            self.provider_generation,
            self.semantic_root,
            self.semantic_type,
            self.requested_transformation,
        )):
            raise ValueError("ENVELOPE_BINDING_REQUIRED")
        if self.cost_units < 0:
            raise ValueError("INVALID_OPERATION_COST")
        for leaf in self.evidence:
            leaf.validate()
            if not leaf.current:
                raise ValueError("STALE_EVIDENCE")
        for item in self.wallet_items:
            item.validate()

    @property
    def envelope_digest(self) -> str:
        self.validate()
        return digest(asdict(self))


@dataclass(frozen=True)
class BridgeAdmissionReceipt:
    disposition: str
    bridge_id: str
    contract_digest: str
    envelope_digest: str
    exporting_owner: str
    importing_owner: str
    destination_local_gates: tuple[str, ...]
    admitted_evidence_domains: tuple[str, ...]
    authority_promoted: bool = False
    effect_authority: bool = False


class CrossCityBridgeCompiler:
    """Declarative cross-jurisdiction membrane with no authority promotion."""

    def admit(self, contract: BridgeContract, envelope: BridgeEnvelope) -> BridgeAdmissionReceipt:
        contract.validate()
        envelope.validate()
        if envelope.bridge_id != contract.bridge_id:
            raise ValueError("BRIDGE_ID_MISMATCH")
        if envelope.semantic_type != contract.semantic_type:
            raise ValueError("SEMANTIC_TYPE_MISMATCH")
        transform = envelope.requested_transformation
        if transform in contract.forbidden_casts:
            raise ValueError("FORBIDDEN_CAST")
        if transform not in contract.allowed_transformations:
            raise ValueError("TRANSFORM_NOT_ALLOWED")
        if envelope.cost_units > contract.max_cost_units:
            raise ValueError("COST_CAP_EXCEEDED")
        evidence_domains = {leaf.domain for leaf in envelope.evidence}
        missing = set(contract.required_evidence_domains) - evidence_domains
        if missing:
            raise ValueError("MISSING_REQUIRED_EVIDENCE")
        disposition = (
            "PORTABLE_EVIDENCE_ADMITTED_LOCAL_REVALIDATION_REQUIRED"
            if contract.required_local_gates
            else "PORTABLE_EVIDENCE_ADMITTED_NO_AUTHORITY_PROMOTION"
        )
        return BridgeAdmissionReceipt(
            disposition=disposition,
            bridge_id=contract.bridge_id,
            contract_digest=contract.contract_digest,
            envelope_digest=envelope.envelope_digest,
            exporting_owner=contract.exporting_owner,
            importing_owner=contract.importing_owner,
            destination_local_gates=tuple(sorted(contract.required_local_gates)),
            admitted_evidence_domains=tuple(sorted(evidence_domains)),
        )

    def compose(self, first: BridgeContract, second: BridgeContract) -> str:
        first.validate()
        second.validate()
        if first.importing_jurisdiction != second.exporting_jurisdiction:
            return "HOLD_JURISDICTION_CHAIN_MISMATCH"
        if first.semantic_type != second.semantic_type:
            return "HOLD_SEMANTIC_TYPE_MISMATCH"
        return "COMPOSABLE_REVALIDATE_AT_EACH_DESTINATION_NO_AUTHORITY_PROMOTION"


class BridgeDependencyIndex:
    def __init__(self, contracts: Iterable[BridgeContract]):
        self.contracts: dict[str, BridgeContract] = {}
        for contract in contracts:
            contract.validate()
            if contract.bridge_id in self.contracts:
                raise ValueError("DUPLICATE_BRIDGE_ID")
            self.contracts[contract.bridge_id] = contract

    def affected(self, changed_invalidators: Iterable[str]) -> tuple[str, ...]:
        changed = set(changed_invalidators)
        return tuple(sorted(
            bridge_id
            for bridge_id, contract in self.contracts.items()
            if changed & set(contract.dependency_invalidators)
        ))


def contract_from_mapping(data: Mapping[str, object]) -> BridgeContract:
    """Compile one declarative policy object into the typed ABI contract."""
    def tup(name: str) -> tuple[str, ...]:
        value = data.get(name, ())
        if isinstance(value, str):
            raise ValueError(f"{name.upper()}_MUST_BE_SEQUENCE")
        return tuple(str(x) for x in value)

    contract = BridgeContract(
        bridge_id=str(data.get("bridge_id", "")),
        schema_version=str(data.get("schema_version", "")),
        exporting_jurisdiction=str(data.get("exporting_jurisdiction", "")),
        exporting_owner=str(data.get("exporting_owner", "")),
        importing_jurisdiction=str(data.get("importing_jurisdiction", "")),
        importing_owner=str(data.get("importing_owner", "")),
        semantic_type=str(data.get("semantic_type", "")),
        allowed_transformations=tup("allowed_transformations"),
        forbidden_casts=tup("forbidden_casts"),
        required_evidence_domains=tup("required_evidence_domains"),
        required_local_gates=tup("required_local_gates"),
        dependency_invalidators=tup("dependency_invalidators"),
        max_cost_units=int(data.get("max_cost_units", 0)),
        replay_semantics=str(data.get("replay_semantics", "IDEMPOTENT_BY_ENVELOPE_DIGEST")),
        authority_ceiling=str(data.get("authority_ceiling", "NO_AUTHORITY_PROMOTION")),
    )
    contract.validate()
    return contract
