#!/usr/bin/env python3
"""EKI-1: External Knowledge Ingress Admission Fabric.

D0 / HS1 / NONPROMOTING.

The fabric normalizes external discoveries into source-generation-bound,
demand-paged read-only knowledge cards. Discovery and locality are intentionally
separate from source currentness, semantic truth, capability/execution authority,
and provider effects.

Provider adapters may cheaply populate L0/L1. L2/L3 require a CURRENT,
provider-generation-bound observation. L4 additionally requires an exact source
handle and content digest.

The 13-axis operational projection and 27-trit locality key are retrieval/routing
hints only. They never mint identity, currentness, truth, license/security review,
tool availability, execution authority, or effect permission.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse


SCHEMA = "AURA-EXTERNAL-KNOWLEDGE-INGRESS-v1"
PROJECTION_SCHEMA = "AURA-EKI-OPERATIONAL-13D-v1"
K27_SCHEMA = "AURA-EKI-27TRIT-LOCALITY-v1"
REFRESH_SCHEMA = "AURA-EKI-TOROIDAL-REFRESH-PHASE-v1"

HEX = frozenset("0123456789abcdef")


class SourceKind(str, Enum):
    ARXIV = "ARXIV"
    GITHUB = "GITHUB"
    HUGGINGFACE_MODEL = "HUGGINGFACE_MODEL"
    HUGGINGFACE_DATASET = "HUGGINGFACE_DATASET"
    HUGGINGFACE_SPACE = "HUGGINGFACE_SPACE"
    GOOGLE_SCHOLAR_DISCOVERY = "GOOGLE_SCHOLAR_DISCOVERY"
    REDDIT = "REDDIT"
    WEB = "WEB"


class ArtifactClass(str, Enum):
    KNOWLEDGE = "KNOWLEDGE"
    CODE = "CODE"
    MODEL = "MODEL"
    DATASET = "DATASET"
    TOOL = "TOOL"
    DISCUSSION = "DISCUSSION"


class Currentness(str, Enum):
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"
    CURRENT = "CURRENT"


class RightsState(str, Enum):
    UNKNOWN = "UNKNOWN"
    DECLARED = "DECLARED"
    REVIEWED = "REVIEWED"


class SecurityState(str, Enum):
    UNKNOWN = "UNKNOWN"
    METADATA_RECORDED = "METADATA_RECORDED"
    REVIEWED = "REVIEWED"


class Volatility(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RelevanceBand(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Availability(str, Enum):
    DISCOVERY_CACHEABLE = "DISCOVERY_CACHEABLE"
    STALE_REVERIFY_REQUIRED = "STALE_REVERIFY_REQUIRED"
    READ_ONLY_REFERENCE_READY = "READ_ONLY_REFERENCE_READY"
    TOOL_METADATA_REVIEW_REQUIRED = "TOOL_METADATA_REVIEW_REQUIRED"
    TOOL_INSPECTION_READY = "TOOL_INSPECTION_READY"


class HydrationLevel(int, Enum):
    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4


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


def _sha256_hex(value: str, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in HEX for c in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")
    return value


def _required(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value.strip()


def _http_uri(value: str, name: str) -> str:
    value = _required(value, name)
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{name}_MUST_BE_HTTP_URI")
    return value


def _bool_trit(value: bool | None) -> int:
    # Categorical routing code: false=0, unknown=1, true=2.
    if value is None:
        return 1
    return 2 if value else 0


@dataclass(frozen=True)
class SourceGeneration:
    generation_type: str
    generation_value: str
    checked_at: str
    exact_source_uri: str | None = None
    content_sha256: str | None = None
    etag: str | None = None
    last_modified: str | None = None

    def validate(self) -> None:
        _required(self.generation_type, "GENERATION_TYPE")
        _required(self.generation_value, "GENERATION_VALUE")
        _required(self.checked_at, "GENERATION_CHECKED_AT")
        if self.exact_source_uri is not None:
            _http_uri(self.exact_source_uri, "EXACT_SOURCE_URI")
        if self.content_sha256 is not None:
            _sha256_hex(self.content_sha256, "CONTENT_SHA256")
        if self.etag is not None:
            _required(self.etag, "ETAG")
        if self.last_modified is not None:
            _required(self.last_modified, "LAST_MODIFIED")

    @property
    def generation_id(self) -> str:
        self.validate()
        return _sha({"domain": "AURA-EKI-SOURCE-GENERATION-v1", **asdict(self)})


@dataclass(frozen=True)
class RightsMetadata:
    state: RightsState = RightsState.UNKNOWN
    license_expression: str | None = None
    terms_uri: str | None = None

    def validate(self) -> None:
        if self.license_expression is not None:
            _required(self.license_expression, "LICENSE_EXPRESSION")
        if self.terms_uri is not None:
            _http_uri(self.terms_uri, "TERMS_URI")
        if self.state is not RightsState.UNKNOWN and not (
            self.license_expression or self.terms_uri
        ):
            raise ValueError("RIGHTS_DECLARED_OR_REVIEWED_REQUIRES_EVIDENCE")


@dataclass(frozen=True)
class SecurityMetadata:
    state: SecurityState = SecurityState.UNKNOWN
    remote_code_requested: bool | None = None
    network_capability: bool | None = None
    write_capability: bool | None = None
    secret_capability: bool | None = None
    security_notes: tuple[str, ...] = ()

    def validate(self) -> None:
        if self.state is not SecurityState.UNKNOWN:
            # Metadata-recorded may legitimately record all capabilities as false.
            if all(
                v is None
                for v in (
                    self.remote_code_requested,
                    self.network_capability,
                    self.write_capability,
                    self.secret_capability,
                )
            ):
                raise ValueError("SECURITY_RECORDED_OR_REVIEWED_REQUIRES_CAPABILITY_FACTS")
        for note in self.security_notes:
            _required(note, "SECURITY_NOTE")


@dataclass(frozen=True)
class HydrationMaterial:
    level: HydrationLevel
    source_generation_id: str | None
    payload: Mapping[str, Any]
    payload_sha256: str | None = None

    def validate(self) -> None:
        if not isinstance(self.payload, Mapping):
            raise ValueError("HYDRATION_PAYLOAD_MUST_BE_MAPPING")
        if self.level.value >= HydrationLevel.L2.value:
            _required(self.source_generation_id or "", "HYDRATION_SOURCE_GENERATION_ID")
        if self.payload_sha256 is not None:
            _sha256_hex(self.payload_sha256, "HYDRATION_PAYLOAD_SHA256")

    @property
    def material_digest(self) -> str:
        self.validate()
        actual = _sha({"level": int(self.level), "payload": dict(self.payload)})
        if self.payload_sha256 is not None and self.payload_sha256 != actual:
            raise ValueError("HYDRATION_PAYLOAD_DIGEST_MISMATCH")
        return actual


@dataclass(frozen=True)
class ExternalDiscoveryObservation:
    source_kind: SourceKind
    artifact_class: ArtifactClass
    canonical_id: str
    canonical_uri: str
    title: str
    thesis: str
    currentness: Currentness = Currentness.UNKNOWN
    generation: SourceGeneration | None = None
    rights: RightsMetadata = field(default_factory=RightsMetadata)
    security: SecurityMetadata = field(default_factory=SecurityMetadata)
    authors_or_owner: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    volatility: Volatility = Volatility.MEDIUM
    relevance: RelevanceBand = RelevanceBand.MEDIUM
    advisory_only: bool = False

    def validate(self) -> None:
        _required(self.canonical_id, "CANONICAL_ID")
        _http_uri(self.canonical_uri, "CANONICAL_URI")
        _required(self.title, "TITLE")
        _required(self.thesis, "THESIS")
        self.rights.validate()
        self.security.validate()
        for value in self.authors_or_owner:
            _required(value, "AUTHOR_OR_OWNER")
        for value in self.tags:
            _required(value, "TAG")

        if self.currentness is Currentness.CURRENT and self.generation is None:
            raise ValueError("CURRENT_REQUIRES_SOURCE_GENERATION")
        if self.generation is not None:
            self.generation.validate()

        # Scholar search is a discovery mechanism, not a primary source generation owner.
        if (
            self.source_kind is SourceKind.GOOGLE_SCHOLAR_DISCOVERY
            and self.currentness is Currentness.CURRENT
        ):
            raise ValueError("SCHOLAR_DISCOVERY_CANNOT_SELF_MINT_PRIMARY_SOURCE_CURRENTNESS")

    @property
    def semantic_id(self) -> str:
        self.validate()
        return _sha(
            {
                "domain": "AURA-EKI-EXTERNAL-SEMANTIC-ID-v1",
                "source_kind": self.source_kind.value,
                "canonical_id": self.canonical_id,
            }
        )


AXIS_LABELS = (
    "generation_binding",
    "freshness_state",
    "provenance_strength",
    "hydration_band",
    "artifact_consequence",
    "rights_state",
    "security_state",
    "remote_code_risk",
    "network_capability",
    "write_capability",
    "secret_capability",
    "source_volatility",
    "objective_relevance",
)


@dataclass(frozen=True)
class OperationalProjection13D:
    trits: tuple[int, ...]
    labels: tuple[str, ...] = AXIS_LABELS
    schema: str = PROJECTION_SCHEMA
    semantic_authority: bool = False

    def validate(self) -> None:
        if len(self.trits) != 13 or len(self.labels) != 13:
            raise ValueError("OPERATIONAL_PROJECTION_MUST_HAVE_13_AXES")
        if tuple(self.labels) != AXIS_LABELS:
            raise ValueError("OPERATIONAL_PROJECTION_AXIS_SCHEMA_MISMATCH")
        if any(type(v) is not int or v not in (0, 1, 2) for v in self.trits):
            raise ValueError("OPERATIONAL_PROJECTION_AXES_MUST_BE_TRITS")
        if self.semantic_authority is not False:
            raise ValueError("OPERATIONAL_PROJECTION_CANNOT_MINT_SEMANTIC_AUTHORITY")

    @property
    def projection_digest(self) -> str:
        self.validate()
        return _sha({"schema": self.schema, "labels": self.labels, "trits": self.trits})


@dataclass(frozen=True)
class K27Locality:
    trits: tuple[int, ...]
    operational_prefix: tuple[int, ...]
    schema: str = K27_SCHEMA
    routing_only: bool = True
    semantic_identity: bool = False
    authority: bool = False

    def validate(self) -> None:
        if len(self.trits) != 27:
            raise ValueError("K27_LOCALITY_MUST_HAVE_27_TRITS")
        if any(type(v) is not int or v not in (0, 1, 2) for v in self.trits):
            raise ValueError("K27_LOCALITY_VALUES_MUST_BE_TRITS")
        if tuple(self.trits[:13]) != tuple(self.operational_prefix):
            raise ValueError("K27_LOCALITY_PREFIX_MUST_PRESERVE_13D_OPERATIONAL_PROJECTION")
        if self.routing_only is not True or self.semantic_identity or self.authority:
            raise ValueError("K27_LOCALITY_IS_ROUTING_ONLY")

    @property
    def key(self) -> str:
        self.validate()
        return "".join(str(v) for v in self.trits)


@dataclass(frozen=True)
class ToroidalRefreshPhase:
    slot: int
    slot_count: int
    recommended_interval_seconds: int
    schema: str = REFRESH_SCHEMA
    currentness_witness: bool = False

    def validate(self) -> None:
        if self.slot_count != 27:
            raise ValueError("REFRESH_PHASE_SLOT_COUNT_MUST_BE_27")
        if not (0 <= self.slot < self.slot_count):
            raise ValueError("REFRESH_PHASE_SLOT_OUT_OF_RANGE")
        if self.recommended_interval_seconds <= 0:
            raise ValueError("REFRESH_INTERVAL_MUST_BE_POSITIVE")
        if self.currentness_witness is not False:
            raise ValueError("REFRESH_PHASE_CANNOT_PROVE_CURRENTNESS")


@dataclass(frozen=True)
class ExternalKnowledgeCard:
    schema: str
    semantic_id: str
    generation_id: str | None
    source_kind: str
    artifact_class: str
    canonical_id: str
    canonical_uri: str
    title: str
    currentness: str
    availability: str
    admitted_hydration_level: int
    hydration: Mapping[str, Mapping[str, Any]]
    rights: Mapping[str, Any]
    security: Mapping[str, Any]
    projection_13d: Mapping[str, Any]
    k27_locality: Mapping[str, Any]
    refresh_phase: Mapping[str, Any]
    advisory_only: bool
    exact_reopen_uri: str | None
    content_sha256: str | None
    read_only_reference_authority: bool = True
    execution_authorized: bool = False
    provider_effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect_authorized: bool = False

    @property
    def receipt_digest(self) -> str:
        return _sha({"domain": SCHEMA, "card": asdict(self)})

    def to_dict(self) -> dict[str, Any]:
        body = asdict(self)
        body["receipt_digest"] = self.receipt_digest
        return body


def _artifact_consequence_trit(artifact_class: ArtifactClass) -> int:
    if artifact_class in {ArtifactClass.KNOWLEDGE, ArtifactClass.DISCUSSION}:
        return 0
    if artifact_class in {ArtifactClass.DATASET, ArtifactClass.MODEL}:
        return 1
    return 2


def _volatility_trit(value: Volatility) -> int:
    return {Volatility.LOW: 0, Volatility.MEDIUM: 1, Volatility.HIGH: 2}[value]


def _relevance_trit(value: RelevanceBand) -> int:
    return {RelevanceBand.LOW: 0, RelevanceBand.MEDIUM: 1, RelevanceBand.HIGH: 2}[value]


def _rights_trit(value: RightsState) -> int:
    return {RightsState.UNKNOWN: 0, RightsState.DECLARED: 1, RightsState.REVIEWED: 2}[value]


def _security_trit(value: SecurityState) -> int:
    return {
        SecurityState.UNKNOWN: 0,
        SecurityState.METADATA_RECORDED: 1,
        SecurityState.REVIEWED: 2,
    }[value]


def _freshness_trit(value: Currentness) -> int:
    return {Currentness.UNKNOWN: 0, Currentness.STALE: 1, Currentness.CURRENT: 2}[value]


def _to_base3_digits(value: int, width: int) -> tuple[int, ...]:
    digits = [0] * width
    for index in range(width - 1, -1, -1):
        digits[index] = value % 3
        value //= 3
    return tuple(digits)


def build_projection_13d(
    observation: ExternalDiscoveryObservation, admitted_level: HydrationLevel
) -> OperationalProjection13D:
    observation.validate()
    generation_binding = 2 if observation.generation is not None else 0
    provenance_strength = 0
    if observation.generation is not None:
        provenance_strength = 1
        if observation.generation.content_sha256 is not None:
            provenance_strength = 2
    hydration_band = 0 if admitted_level.value <= 1 else (1 if admitted_level.value <= 3 else 2)
    projection = OperationalProjection13D(
        trits=(
            generation_binding,
            _freshness_trit(observation.currentness),
            provenance_strength,
            hydration_band,
            _artifact_consequence_trit(observation.artifact_class),
            _rights_trit(observation.rights.state),
            _security_trit(observation.security.state),
            _bool_trit(observation.security.remote_code_requested),
            _bool_trit(observation.security.network_capability),
            _bool_trit(observation.security.write_capability),
            _bool_trit(observation.security.secret_capability),
            _volatility_trit(observation.volatility),
            _relevance_trit(observation.relevance),
        )
    )
    projection.validate()
    return projection


def build_k27_locality(
    observation: ExternalDiscoveryObservation, projection: OperationalProjection13D
) -> K27Locality:
    observation.validate()
    projection.validate()
    # Preserve the full 13D operational feature prefix for locality. The remaining
    # 13 trits spread sources inside that operational cell, and one trit checksums
    # the complete 26-trit prefix. Exact identity is always semantic_id+generation.
    spread_digest = hashlib.sha256(
        (
            "AURA-EKI-K27-SPREAD-v1|"
            + observation.source_kind.value
            + "|"
            + observation.canonical_id
        ).encode("utf-8")
    ).digest()
    spread_int = int.from_bytes(spread_digest, "big") % (3**13)
    spread = _to_base3_digits(spread_int, 13)
    first26 = tuple(projection.trits) + spread
    checksum = sum((i + 1) * trit for i, trit in enumerate(first26)) % 3
    locality = K27Locality(
        trits=first26 + (checksum,),
        operational_prefix=tuple(projection.trits),
    )
    locality.validate()
    return locality


def build_refresh_phase(observation: ExternalDiscoveryObservation) -> ToroidalRefreshPhase:
    observation.validate()
    slot = int.from_bytes(
        hashlib.sha256(
            ("AURA-EKI-REFRESH|" + observation.semantic_id).encode("ascii")
        ).digest()[:8],
        "big",
    ) % 27
    interval = {
        Volatility.HIGH: 3600,
        Volatility.MEDIUM: 21600,
        Volatility.LOW: 86400,
    }[observation.volatility]
    phase = ToroidalRefreshPhase(slot=slot, slot_count=27, recommended_interval_seconds=interval)
    phase.validate()
    return phase


def _tool_like(observation: ExternalDiscoveryObservation) -> bool:
    return observation.artifact_class in {ArtifactClass.CODE, ArtifactClass.TOOL} or (
        observation.source_kind is SourceKind.HUGGINGFACE_SPACE
    )


def _availability(observation: ExternalDiscoveryObservation) -> Availability:
    if observation.currentness is Currentness.STALE:
        return Availability.STALE_REVERIFY_REQUIRED
    if observation.currentness is not Currentness.CURRENT:
        return Availability.DISCOVERY_CACHEABLE

    if not _tool_like(observation):
        return Availability.READ_ONLY_REFERENCE_READY

    # A tool may be inspected after provider metadata is current, but execution
    # remains outside this fabric. Unknown rights/security stay explicit.
    if (
        observation.rights.state is RightsState.UNKNOWN
        or observation.security.state is SecurityState.UNKNOWN
    ):
        return Availability.TOOL_METADATA_REVIEW_REQUIRED
    return Availability.TOOL_INSPECTION_READY


def _max_level(observation: ExternalDiscoveryObservation, requested: HydrationLevel) -> HydrationLevel:
    if observation.currentness is not Currentness.CURRENT or observation.generation is None:
        return HydrationLevel(min(requested.value, HydrationLevel.L1.value))
    if requested is HydrationLevel.L4:
        if (
            observation.generation.exact_source_uri is None
            or observation.generation.content_sha256 is None
        ):
            return HydrationLevel.L3
    return requested


def admit_external_knowledge(
    *,
    observation: ExternalDiscoveryObservation,
    requested_level: HydrationLevel,
    materials: Sequence[HydrationMaterial] = (),
) -> ExternalKnowledgeCard:
    observation.validate()
    admitted_level = _max_level(observation, requested_level)

    by_level: dict[int, HydrationMaterial] = {}
    for material in materials:
        material.validate()
        if material.level.value in by_level:
            raise ValueError("DUPLICATE_HYDRATION_LEVEL")
        by_level[material.level.value] = material

    generation_id = observation.generation.generation_id if observation.generation else None

    # L0 is always normalized from provider discovery metadata.
    payloads: dict[str, Mapping[str, Any]] = {
        "L0": {
            "canonical_id": observation.canonical_id,
            "canonical_uri": observation.canonical_uri,
            "title": observation.title,
            "thesis": observation.thesis,
            "semantic_id": observation.semantic_id,
        }
    }

    if admitted_level.value >= HydrationLevel.L1.value:
        payloads["L1"] = {
            "authors_or_owner": list(observation.authors_or_owner),
            "tags": list(observation.tags),
            "rights_state": observation.rights.state.value,
            "license_expression": observation.rights.license_expression,
            "security_state": observation.security.state.value,
            # Preserve unknowns as null; never sanitize missing facts to false.
            "remote_code_requested": observation.security.remote_code_requested,
            "network_capability": observation.security.network_capability,
            "write_capability": observation.security.write_capability,
            "secret_capability": observation.security.secret_capability,
        }

    for level in (HydrationLevel.L2, HydrationLevel.L3, HydrationLevel.L4):
        if admitted_level.value < level.value:
            continue
        material = by_level.get(level.value)
        if material is None:
            # Do not hallucinate heavy synthesis. The level is not admitted merely
            # because a caller asked for it.
            admitted_level = HydrationLevel(level.value - 1)
            break
        if material.source_generation_id != generation_id:
            raise ValueError("HYDRATION_GENERATION_MISMATCH")
        payloads[level.name] = {
            "payload": dict(material.payload),
            "material_digest": material.material_digest,
            "source_generation_id": material.source_generation_id,
        }

    # Recompute in case a missing material shortened the admitted depth.
    projection = build_projection_13d(observation, admitted_level)
    locality = build_k27_locality(observation, projection)
    phase = build_refresh_phase(observation)
    availability = _availability(observation)

    exact_reopen_uri = None
    content_sha256 = None
    if admitted_level is HydrationLevel.L4 and observation.generation is not None:
        exact_reopen_uri = observation.generation.exact_source_uri
        content_sha256 = observation.generation.content_sha256

    card = ExternalKnowledgeCard(
        schema=SCHEMA,
        semantic_id=observation.semantic_id,
        generation_id=generation_id,
        source_kind=observation.source_kind.value,
        artifact_class=observation.artifact_class.value,
        canonical_id=observation.canonical_id,
        canonical_uri=observation.canonical_uri,
        title=observation.title,
        currentness=observation.currentness.value,
        availability=availability.value,
        admitted_hydration_level=admitted_level.value,
        hydration=payloads,
        rights=asdict(observation.rights),
        security=asdict(observation.security),
        projection_13d={
            "schema": projection.schema,
            "labels": list(projection.labels),
            "trits": list(projection.trits),
            "projection_digest": projection.projection_digest,
            "semantic_authority": False,
        },
        k27_locality={
            "schema": locality.schema,
            "trits": list(locality.trits),
            "key": locality.key,
            "routing_only": True,
            "semantic_identity": False,
            "authority": False,
        },
        refresh_phase=asdict(phase),
        advisory_only=observation.advisory_only,
        exact_reopen_uri=exact_reopen_uri,
        content_sha256=content_sha256,
    )
    return card


def observation_from_provider_metadata(payload: Mapping[str, Any]) -> ExternalDiscoveryObservation:
    """Normalize a provider-independent JSON envelope.

    Network collection stays outside this D0 core. PowerShell, GitHub, arXiv,
    Hugging Face, Scholar, Reddit, or browser adapters can cheaply produce this
    envelope, then the same admission law applies.
    """
    generation_payload = payload.get("generation")
    generation = None
    if generation_payload is not None:
        generation = SourceGeneration(**generation_payload)

    rights_payload = payload.get("rights") or {}
    rights = RightsMetadata(
        state=RightsState(rights_payload.get("state", RightsState.UNKNOWN.value)),
        license_expression=rights_payload.get("license_expression"),
        terms_uri=rights_payload.get("terms_uri"),
    )

    security_payload = payload.get("security") or {}
    security = SecurityMetadata(
        state=SecurityState(
            security_payload.get("state", SecurityState.UNKNOWN.value)
        ),
        remote_code_requested=security_payload.get("remote_code_requested"),
        network_capability=security_payload.get("network_capability"),
        write_capability=security_payload.get("write_capability"),
        secret_capability=security_payload.get("secret_capability"),
        security_notes=tuple(security_payload.get("security_notes") or ()),
    )

    observation = ExternalDiscoveryObservation(
        source_kind=SourceKind(payload["source_kind"]),
        artifact_class=ArtifactClass(payload["artifact_class"]),
        canonical_id=payload["canonical_id"],
        canonical_uri=payload["canonical_uri"],
        title=payload["title"],
        thesis=payload["thesis"],
        currentness=Currentness(payload.get("currentness", Currentness.UNKNOWN.value)),
        generation=generation,
        rights=rights,
        security=security,
        authors_or_owner=tuple(payload.get("authors_or_owner") or ()),
        tags=tuple(payload.get("tags") or ()),
        volatility=Volatility(payload.get("volatility", Volatility.MEDIUM.value)),
        relevance=RelevanceBand(payload.get("relevance", RelevanceBand.MEDIUM.value)),
        advisory_only=bool(payload.get("advisory_only", False)),
    )
    observation.validate()
    return observation


def main() -> None:
    # Fail-closed demonstration: discovery metadata is cacheable, but no provider
    # generation has been observed, so hydration stops at L1 and execution is false.
    observation = ExternalDiscoveryObservation(
        source_kind=SourceKind.ARXIV,
        artifact_class=ArtifactClass.KNOWLEDGE,
        canonical_id="arXiv:example",
        canonical_uri="https://arxiv.org/abs/example",
        title="Example external discovery",
        thesis="Demonstrate discovery-before-trust.",
        currentness=Currentness.UNKNOWN,
        advisory_only=True,
    )
    card = admit_external_knowledge(
        observation=observation,
        requested_level=HydrationLevel.L4,
    )
    print(json.dumps(card.to_dict(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
