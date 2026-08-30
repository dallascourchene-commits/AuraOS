"""AURA-ADOPT-001 ZF-10A: consequence-complete adoption economics.

This is a pure deterministic evidence membrane. UNKNOWN never becomes zero;
scenario/estimated economics never become observed paid-route evidence; reuse
credits are exact-principal/currentness/currency bound; and no result grants
payment, provider, credential, network, or execution authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from math import gcd
from typing import Any, Mapping, Sequence

RECEIPT_SCHEMA = "AdoptionEconomicsReceiptV1"
ADMISSION_SCHEMA = "AdoptionEconomicsAdmissionV1"
COMPARISON_SCHEMA = "AdoptionEconomicsComparisonV1"
SEMANTIC_VALIDATOR = "tools.aura_adopt.adoption_economics.validate_economics_receipt_dict"


class EconomicsError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


class ObservationStatus(str, Enum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class MoneyEvidenceClass(str, Enum):
    BILLED = "BILLED"
    MEASURED = "MEASURED"
    ESTIMATED_WITH_POLICY = "ESTIMATED_WITH_POLICY"
    SCENARIO = "SCENARIO"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE_ASSERTION = "NOT_APPLICABLE_ASSERTION"


class AcceptedValueEvidenceClass(str, Enum):
    TECHNICAL_SYNTHETIC = "TECHNICAL_SYNTHETIC"
    TECHNICAL_EXECUTED = "TECHNICAL_EXECUTED"
    USER_EXPLICIT = "USER_EXPLICIT"
    CONSENTED_STUDY = "CONSENTED_STUDY"


class CostKind(str, Enum):
    ONE_TIME_SETUP = "ONE_TIME_SETUP"
    PROVIDER = "PROVIDER"
    NETWORK_DATA = "NETWORK_DATA"
    LOCAL_ENERGY = "LOCAL_ENERGY"
    HARDWARE_DEPRECIATION = "HARDWARE_DEPRECIATION"
    SUPPORT_LABOR = "SUPPORT_LABOR"
    CACHE_INVALIDATION = "CACHE_INVALIDATION"


class ReuseKind(str, Enum):
    KV_CACHE = "KV_CACHE"
    COORDINATE_MEMORY = "COORDINATE_MEMORY"
    RECIPE = "RECIPE"
    WORKCAPSULE = "WORKCAPSULE"
    OTHER = "OTHER"


COST_KINDS = tuple(kind.value for kind in CostKind)
OBSERVED_MONEY_EVIDENCE = frozenset({MoneyEvidenceClass.BILLED, MoneyEvidenceClass.MEASURED})
VALIDATED_REUSE_MONEY_EVIDENCE = OBSERVED_MONEY_EVIDENCE

COHORT_VOCAB: dict[str, frozenset[str]] = {
    "device_class": frozenset({
        "low_end_android", "mid_android", "high_android", "desktop_laptop",
        "browser_only_managed",
    }),
    "storage_class": frozenset({"severely_constrained", "moderate", "ample"}),
    "connectivity_class": frozenset({"intermittent", "metered", "normal", "offline_first"}),
    "skill_class": frozenset({
        "nontechnical_creator", "experienced_creator", "developer", "organizational_operator",
    }),
    "trust_preference": frozenset({"web_sandbox_first", "app_store_binary", "github_source_transparent"}),
    "compute_preference": frozenset({"deterministic_only", "local_model", "optional_remote_model"}),
    "storage_preference": frozenset({"device_local", "cloud_backed", "hybrid"}),
    "accessibility_class": frozenset({
        "touch_only", "keyboard_mouse", "assistive_technology", "low_bandwidth_ui",
    }),
}


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                          allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EconomicsError("NONCANONICAL_ECONOMICS_STATE") from exc


def _digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EconomicsError(code)
    return value.strip()


def _nn_int(value: Any, code: str, *, allow_none: bool = False) -> int | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise EconomicsError(code)
    return value


def _bool_or_none(value: Any, code: str) -> bool | None:
    if value is None:
        return None
    if type(value) is not bool:
        raise EconomicsError(code)
    return value


def _currency(value: Any) -> str:
    value = _text(value, "CURRENCY_REQUIRED").upper()
    if len(value) != 3 or not value.isalpha():
        raise EconomicsError("CURRENCY_CODE_INVALID")
    return value


def _principal(value: Any) -> str:
    value = _text(value, "PRINCIPAL_SCOPE_REQUIRED")
    if not value.startswith("principal:") or len(value) > 96:
        raise EconomicsError("PRINCIPAL_SCOPE_INVALID")
    suffix = value.split(":", 1)[1]
    if not suffix or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-" for ch in suffix):
        raise EconomicsError("PRINCIPAL_SCOPE_INVALID")
    return value


def _normalize_cohort(value: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        raise EconomicsError("COHORT_REQUIRED")
    out: dict[str, str] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key)
        if key not in COHORT_VOCAB:
            raise EconomicsError("COHORT_FIELD_NOT_PRIVACY_MINIMAL", key)
        val = _text(raw_value, "COHORT_VALUE_REQUIRED")
        if val not in COHORT_VOCAB[key]:
            raise EconomicsError("COHORT_VALUE_NOT_PRIVACY_MINIMAL", f"{key}:{val}")
        out[key] = val
    return dict(sorted(out.items()))


@dataclass(frozen=True)
class ExactMicrounitRatio:
    numerator_microunits: int
    denominator_accepted_values: int

    def __post_init__(self) -> None:
        numerator = _nn_int(self.numerator_microunits, "RATIO_NUMERATOR_INVALID")
        denominator = _nn_int(self.denominator_accepted_values, "RATIO_DENOMINATOR_INVALID")
        if denominator == 0:
            raise EconomicsError("RATIO_DENOMINATOR_ZERO")
        divisor = gcd(numerator, denominator)
        object.__setattr__(self, "numerator_microunits", numerator // divisor)
        object.__setattr__(self, "denominator_accepted_values", denominator // divisor)

    def logical(self) -> dict[str, int]:
        return asdict(self)

    def compare_to_integer_ceiling(self, ceiling_microunits: int) -> int:
        ceiling = _nn_int(ceiling_microunits, "CPAV_CEILING_INVALID")
        left = self.numerator_microunits
        right = ceiling * self.denominator_accepted_values
        return (left > right) - (left < right)

    def compare(self, other: "ExactMicrounitRatio") -> int:
        if not isinstance(other, ExactMicrounitRatio):
            raise EconomicsError("RATIO_REQUIRED")
        left = self.numerator_microunits * other.denominator_accepted_values
        right = other.numerator_microunits * self.denominator_accepted_values
        return (left > right) - (left < right)

    def subtract(self, other: "ExactMicrounitRatio") -> "SignedExactRatio":
        if not isinstance(other, ExactMicrounitRatio):
            raise EconomicsError("RATIO_REQUIRED")
        return SignedExactRatio(
            self.numerator_microunits * other.denominator_accepted_values
            - other.numerator_microunits * self.denominator_accepted_values,
            self.denominator_accepted_values * other.denominator_accepted_values,
        )


@dataclass(frozen=True)
class SignedExactRatio:
    numerator_microunits: int
    denominator_accepted_values: int

    def __post_init__(self) -> None:
        if isinstance(self.numerator_microunits, bool) or not isinstance(self.numerator_microunits, int):
            raise EconomicsError("SIGNED_RATIO_NUMERATOR_INVALID")
        if isinstance(self.denominator_accepted_values, bool) or not isinstance(self.denominator_accepted_values, int) or self.denominator_accepted_values <= 0:
            raise EconomicsError("SIGNED_RATIO_DENOMINATOR_INVALID")
        divisor = gcd(abs(self.numerator_microunits), self.denominator_accepted_values)
        object.__setattr__(self, "numerator_microunits", self.numerator_microunits // divisor)
        object.__setattr__(self, "denominator_accepted_values", self.denominator_accepted_values // divisor)

    def logical(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceBinding:
    artifact_ref: str
    artifact_digest: str
    source_generation: str
    currentness_ref: str
    evidence_class: str

    def __post_init__(self) -> None:
        for value, code in (
            (self.artifact_ref, "EVIDENCE_ARTIFACT_REF_REQUIRED"),
            (self.artifact_digest, "EVIDENCE_ARTIFACT_DIGEST_REQUIRED"),
            (self.source_generation, "EVIDENCE_SOURCE_GENERATION_REQUIRED"),
            (self.currentness_ref, "EVIDENCE_CURRENTNESS_REQUIRED"),
            (self.evidence_class, "EVIDENCE_CLASS_REQUIRED"),
        ):
            _text(value, code)

    def logical(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class CostObservation:
    kind: CostKind
    status: ObservationStatus
    value_microunits: int | None
    currency: str
    evidence_class: MoneyEvidenceClass
    source_ref: str
    source_generation: str
    currentness_ref: str
    source_current: bool | None
    source_current_evidence_ref: str | None
    policy_ref: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CostKind):
            raise EconomicsError("COST_KIND_REQUIRED")
        if not isinstance(self.status, ObservationStatus):
            raise EconomicsError("COST_STATUS_REQUIRED", self.kind.value)
        if not isinstance(self.evidence_class, MoneyEvidenceClass):
            raise EconomicsError("COST_EVIDENCE_CLASS_REQUIRED", self.kind.value)
        object.__setattr__(self, "currency", _currency(self.currency))
        _text(self.source_ref, "COST_SOURCE_REF_REQUIRED")
        _text(self.source_generation, "COST_SOURCE_GENERATION_REQUIRED")
        _text(self.currentness_ref, "COST_CURRENTNESS_REQUIRED")
        _bool_or_none(self.source_current, "COST_SOURCE_CURRENT_INVALID")
        if self.status is ObservationStatus.KNOWN:
            _nn_int(self.value_microunits, "KNOWN_COST_VALUE_REQUIRED")
            if self.evidence_class in {MoneyEvidenceClass.UNKNOWN, MoneyEvidenceClass.NOT_APPLICABLE_ASSERTION}:
                raise EconomicsError("KNOWN_COST_EVIDENCE_INVALID", self.kind.value)
            if self.source_current is not True:
                raise EconomicsError("KNOWN_COST_SOURCE_NOT_CURRENT", self.kind.value)
            _text(self.source_current_evidence_ref, "COST_CURRENTNESS_EVIDENCE_REQUIRED")
            if self.evidence_class is MoneyEvidenceClass.ESTIMATED_WITH_POLICY:
                _text(self.policy_ref, "ESTIMATED_COST_POLICY_REF_REQUIRED")
            elif self.policy_ref is not None:
                _text(self.policy_ref, "COST_POLICY_REF_INVALID")
        elif self.status is ObservationStatus.UNKNOWN:
            if self.value_microunits is not None:
                raise EconomicsError("UNKNOWN_COST_MUST_NOT_HAVE_VALUE", self.kind.value)
            if self.evidence_class is not MoneyEvidenceClass.UNKNOWN:
                raise EconomicsError("UNKNOWN_COST_EVIDENCE_MUST_BE_UNKNOWN", self.kind.value)
            _text(self.reason, "UNKNOWN_COST_REASON_REQUIRED")
        else:
            if self.value_microunits is not None:
                raise EconomicsError("NA_COST_MUST_NOT_HAVE_VALUE", self.kind.value)
            if self.evidence_class is not MoneyEvidenceClass.NOT_APPLICABLE_ASSERTION:
                raise EconomicsError("NA_COST_EVIDENCE_REQUIRED", self.kind.value)
            if self.source_current is not True:
                raise EconomicsError("NA_COST_SOURCE_NOT_CURRENT", self.kind.value)
            _text(self.source_current_evidence_ref, "NA_COST_CURRENTNESS_EVIDENCE_REQUIRED")
            _text(self.reason, "NA_COST_REASON_REQUIRED")

    def logical(self) -> dict[str, Any]:
        out = asdict(self)
        out.update(kind=self.kind.value, status=self.status.value, evidence_class=self.evidence_class.value)
        return out


@dataclass(frozen=True)
class AcceptedValueEvidence:
    accepted_count: int | None
    attempt_count: int | None
    evidence_class: AcceptedValueEvidenceClass
    verifier_ref: str
    receipt_ref: str
    consent_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_class, AcceptedValueEvidenceClass):
            raise EconomicsError("ACCEPTED_VALUE_EVIDENCE_CLASS_REQUIRED")
        _text(self.verifier_ref, "ACCEPTED_VALUE_VERIFIER_REQUIRED")
        _text(self.receipt_ref, "ACCEPTED_VALUE_RECEIPT_REQUIRED")
        accepted = _nn_int(self.accepted_count, "ACCEPTED_VALUE_COUNT_INVALID", allow_none=True)
        attempts = _nn_int(self.attempt_count, "ATTEMPT_COUNT_INVALID", allow_none=True)
        if (accepted is None) != (attempts is None):
            raise EconomicsError("ACCEPTED_VALUE_COUNTS_COMPLETENESS_MISMATCH")
        if accepted is not None and attempts is not None and accepted > attempts:
            raise EconomicsError("ACCEPTED_VALUE_EXCEEDS_ATTEMPTS")
        if self.evidence_class is AcceptedValueEvidenceClass.CONSENTED_STUDY:
            _text(self.consent_ref, "CONSENT_REF_REQUIRED")
        elif self.consent_ref is not None:
            _text(self.consent_ref, "CONSENT_REF_INVALID")

    @property
    def is_user_evidence(self) -> bool:
        return self.evidence_class in {AcceptedValueEvidenceClass.USER_EXPLICIT, AcceptedValueEvidenceClass.CONSENTED_STUDY}

    def logical(self) -> dict[str, Any]:
        out = asdict(self)
        out["evidence_class"] = self.evidence_class.value
        return out


@dataclass(frozen=True)
class ReuseEvidence:
    evidence_ref: str
    kind: ReuseKind
    status: ObservationStatus
    source_ref: str
    source_generation: str
    currentness_ref: str
    evidence_class: MoneyEvidenceClass
    principal_scope: str
    currency: str
    source_current: bool | None
    source_current_evidence_ref: str | None
    privacy_isolated: bool | None
    privacy_isolation_evidence_ref: str | None
    avoided_provider_microunits: int | None = None
    avoided_recompute_units: int | None = None
    avoided_latency_ms: int | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        _text(self.evidence_ref, "REUSE_EVIDENCE_REF_REQUIRED")
        if not isinstance(self.kind, ReuseKind):
            raise EconomicsError("REUSE_KIND_REQUIRED")
        if not isinstance(self.status, ObservationStatus):
            raise EconomicsError("REUSE_STATUS_REQUIRED")
        if not isinstance(self.evidence_class, MoneyEvidenceClass):
            raise EconomicsError("REUSE_EVIDENCE_CLASS_REQUIRED")
        _text(self.source_ref, "REUSE_SOURCE_REF_REQUIRED")
        _text(self.source_generation, "REUSE_SOURCE_GENERATION_REQUIRED")
        _text(self.currentness_ref, "REUSE_CURRENTNESS_REQUIRED")
        object.__setattr__(self, "principal_scope", _principal(self.principal_scope))
        object.__setattr__(self, "currency", _currency(self.currency))
        _bool_or_none(self.source_current, "REUSE_SOURCE_CURRENT_INVALID")
        _bool_or_none(self.privacy_isolated, "REUSE_PRIVACY_ISOLATED_INVALID")
        for field in ("avoided_provider_microunits", "avoided_recompute_units", "avoided_latency_ms"):
            _nn_int(getattr(self, field), f"{field.upper()}_INVALID", allow_none=True)
        if self.status is ObservationStatus.KNOWN:
            if self.evidence_class in {MoneyEvidenceClass.UNKNOWN, MoneyEvidenceClass.NOT_APPLICABLE_ASSERTION}:
                raise EconomicsError("KNOWN_REUSE_EVIDENCE_INVALID")
        else:
            if any(getattr(self, field) is not None for field in ("avoided_provider_microunits", "avoided_recompute_units", "avoided_latency_ms")):
                raise EconomicsError("NONKNOWN_REUSE_MUST_NOT_HAVE_VALUES")
            _text(self.reason, "NONKNOWN_REUSE_REASON_REQUIRED")
            if self.status is ObservationStatus.UNKNOWN and self.evidence_class is not MoneyEvidenceClass.UNKNOWN:
                raise EconomicsError("UNKNOWN_REUSE_EVIDENCE_MUST_BE_UNKNOWN")
            if self.status is ObservationStatus.NOT_APPLICABLE and self.evidence_class is not MoneyEvidenceClass.NOT_APPLICABLE_ASSERTION:
                raise EconomicsError("NA_REUSE_EVIDENCE_REQUIRED")
        if self.source_current is True:
            _text(self.source_current_evidence_ref, "SOURCE_CURRENT_EVIDENCE_REF_REQUIRED")
        if self.privacy_isolated is True:
            _text(self.privacy_isolation_evidence_ref, "PRIVACY_ISOLATION_EVIDENCE_REF_REQUIRED")

    def logical(self) -> dict[str, Any]:
        out = asdict(self)
        out.update(kind=self.kind.value, status=self.status.value, evidence_class=self.evidence_class.value)
        return out


@dataclass(frozen=True)
class AdoptionEconomicsReceipt:
    schema: str
    route_id: str
    mission_ref: str
    accepted_value_definition_ref: str
    measurement_window_ref: str
    principal_scope: str
    currency: str
    cohort: Mapping[str, str]
    route_evidence: tuple[EvidenceBinding, ...]
    friction_receipt_ref: str
    accepted_value: AcceptedValueEvidence
    costs: tuple[CostObservation, ...]
    reuse_evidence: tuple[ReuseEvidence, ...]
    lifecycle_monetary_total_microunits: int | None
    lifecycle_cost_provenance: str
    cpav_ratio: ExactMicrounitRatio | None
    user_cpav_ratio: ExactMicrounitRatio | None
    validated_avoided_provider_microunits: int | None
    counterfactual_without_reuse_microunits: int | None
    counterfactual_cpav_ratio: ExactMicrounitRatio | None
    unknown_cost_kinds: tuple[str, ...]
    scenario_cost_kinds: tuple[str, ...]
    estimated_cost_kinds: tuple[str, ...]
    unresolved_reuse: tuple[str, ...]
    disposition: str
    logical_id: str
    payment_authorized: bool = False
    provider_authorized: bool = False
    execution_authorized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "route_id": self.route_id,
            "mission_ref": self.mission_ref,
            "accepted_value_definition_ref": self.accepted_value_definition_ref,
            "measurement_window_ref": self.measurement_window_ref,
            "principal_scope": self.principal_scope,
            "currency": self.currency,
            "cohort": dict(self.cohort),
            "route_evidence": [item.logical() for item in self.route_evidence],
            "friction_receipt_ref": self.friction_receipt_ref,
            "accepted_value": self.accepted_value.logical(),
            "costs": [item.logical() for item in self.costs],
            "reuse_evidence": [item.logical() for item in self.reuse_evidence],
            "lifecycle_monetary_total_microunits": self.lifecycle_monetary_total_microunits,
            "lifecycle_cost_provenance": self.lifecycle_cost_provenance,
            "cpav_ratio": self.cpav_ratio.logical() if self.cpav_ratio else None,
            "user_cpav_ratio": self.user_cpav_ratio.logical() if self.user_cpav_ratio else None,
            "validated_avoided_provider_microunits": self.validated_avoided_provider_microunits,
            "counterfactual_without_reuse_microunits": self.counterfactual_without_reuse_microunits,
            "counterfactual_cpav_ratio": self.counterfactual_cpav_ratio.logical() if self.counterfactual_cpav_ratio else None,
            "unknown_cost_kinds": list(self.unknown_cost_kinds),
            "scenario_cost_kinds": list(self.scenario_cost_kinds),
            "estimated_cost_kinds": list(self.estimated_cost_kinds),
            "unresolved_reuse": list(self.unresolved_reuse),
            "disposition": self.disposition,
            "logical_id": self.logical_id,
            "payment_authorized": False,
            "provider_authorized": False,
            "execution_authorized": False,
        }


@dataclass(frozen=True)
class AdoptionEconomicsAdmission:
    schema: str
    receipt_logical_id: str
    disposition: str
    max_user_cpav_microunits: int | None
    user_cpav_ratio: ExactMicrounitRatio | None
    within_policy: bool | None
    paid_route_candidate: bool
    reason: str
    payment_authorized: bool = False
    provider_authorized: bool = False
    execution_authorized: bool = False


@dataclass(frozen=True)
class AdoptionEconomicsComparison:
    schema: str
    baseline_logical_id: str
    candidate_logical_id: str
    comparable: bool
    incompatibilities: tuple[str, ...]
    baseline_cpav_ratio: ExactMicrounitRatio | None
    candidate_cpav_ratio: ExactMicrounitRatio | None
    cpav_delta_ratio: SignedExactRatio | None
    lower_cpav_route_id: str | None
    baseline_friction_receipt_ref: str
    candidate_friction_receipt_ref: str
    overall_route_preference_claimed: bool = False


def _normalize_evidence(items: Sequence[EvidenceBinding]) -> tuple[EvidenceBinding, ...]:
    if isinstance(items, (str, bytes)) or not isinstance(items, Sequence) or not items:
        raise EconomicsError("ROUTE_EVIDENCE_REQUIRED")
    if not all(isinstance(item, EvidenceBinding) for item in items):
        raise EconomicsError("ROUTE_EVIDENCE_TYPE_REQUIRED")
    out = tuple(sorted(items, key=lambda item: (
        item.artifact_ref, item.artifact_digest, item.source_generation,
        item.currentness_ref, item.evidence_class,
    )))
    logical = [_canonical(item.logical()) for item in out]
    if len(logical) != len(set(logical)):
        raise EconomicsError("DUPLICATE_ROUTE_EVIDENCE")
    return out


def _normalize_costs(costs: Sequence[CostObservation], currency: str) -> tuple[CostObservation, ...]:
    if isinstance(costs, (str, bytes)) or not isinstance(costs, Sequence):
        raise EconomicsError("COSTS_SEQUENCE_REQUIRED")
    if not all(isinstance(item, CostObservation) for item in costs):
        raise EconomicsError("COST_OBSERVATION_TYPE_REQUIRED")
    out = tuple(costs)
    kinds = [item.kind.value for item in out]
    if len(out) != len(COST_KINDS) or set(kinds) != set(COST_KINDS) or len(set(kinds)) != len(kinds):
        raise EconomicsError("COST_KIND_COVERAGE_INVALID")
    if any(item.currency != currency for item in out):
        raise EconomicsError("COST_CURRENCY_MISMATCH")
    return tuple(sorted(out, key=lambda item: item.kind.value))


def _normalize_reuse(items: Sequence[ReuseEvidence]) -> tuple[ReuseEvidence, ...]:
    if isinstance(items, (str, bytes)) or not isinstance(items, Sequence):
        raise EconomicsError("REUSE_SEQUENCE_REQUIRED")
    if not all(isinstance(item, ReuseEvidence) for item in items):
        raise EconomicsError("REUSE_EVIDENCE_TYPE_REQUIRED")
    out = tuple(sorted(items, key=lambda item: (
        item.evidence_ref, item.kind.value, item.source_ref, item.source_generation,
        item.currentness_ref, item.evidence_class.value, item.principal_scope,
        item.currency, str(item.source_current), str(item.privacy_isolated),
        str(item.avoided_provider_microunits), str(item.avoided_recompute_units),
        str(item.avoided_latency_ms), item.source_current_evidence_ref or "",
        item.privacy_isolation_evidence_ref or "", item.reason or "",
    )))
    evidence_refs = [item.evidence_ref for item in out]
    logical_ids = [_digest("AURA_REUSE_EVIDENCE_V1", item.logical()) for item in out]
    if len(evidence_refs) != len(set(evidence_refs)) or len(logical_ids) != len(set(logical_ids)):
        raise EconomicsError("DUPLICATE_REUSE_EVIDENCE")
    return out


def _lifecycle_total(costs: Sequence[CostObservation]) -> tuple[int | None, str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    total = 0
    unknown: list[str] = []
    scenario: list[str] = []
    estimated: list[str] = []
    for item in costs:
        if item.status is ObservationStatus.UNKNOWN:
            unknown.append(item.kind.value)
            continue
        if item.status is ObservationStatus.NOT_APPLICABLE:
            continue
        if item.evidence_class is MoneyEvidenceClass.SCENARIO:
            scenario.append(item.kind.value)
            continue
        if item.evidence_class is MoneyEvidenceClass.ESTIMATED_WITH_POLICY:
            estimated.append(item.kind.value)
        elif item.evidence_class not in OBSERVED_MONEY_EVIDENCE:
            unknown.append(item.kind.value)
            continue
        assert item.value_microunits is not None
        total += item.value_microunits
    if unknown or scenario:
        return None, "UNRESOLVED", tuple(sorted(unknown)), tuple(sorted(scenario)), tuple(sorted(estimated))
    provenance = "ESTIMATED" if estimated else "OBSERVED"
    return total, provenance, (), (), tuple(sorted(estimated))


def _validated_reuse_money(reuse: Sequence[ReuseEvidence], *, principal_scope: str, currency: str) -> tuple[int | None, tuple[str, ...]]:
    if not reuse:
        return 0, ()
    total = 0
    unresolved: list[str] = []
    for item in reuse:
        label = f"{item.kind.value}:{item.evidence_ref}"
        if item.status is ObservationStatus.NOT_APPLICABLE:
            continue
        if item.status is ObservationStatus.UNKNOWN:
            unresolved.append(f"{label}:UNKNOWN")
        elif item.principal_scope != principal_scope:
            unresolved.append(f"{label}:PRINCIPAL_SCOPE")
        elif item.currency != currency:
            unresolved.append(f"{label}:CURRENCY")
        elif item.source_current is not True or not item.source_current_evidence_ref:
            unresolved.append(f"{label}:SOURCE_CURRENTNESS")
        elif item.privacy_isolated is not True or not item.privacy_isolation_evidence_ref:
            unresolved.append(f"{label}:PRIVACY_ISOLATION")
        elif item.evidence_class not in VALIDATED_REUSE_MONEY_EVIDENCE:
            unresolved.append(f"{label}:MONEY_EVIDENCE")
        elif item.avoided_provider_microunits is None:
            unresolved.append(f"{label}:AVOIDED_PROVIDER_COST")
        else:
            total += item.avoided_provider_microunits
    return (None if unresolved else total, tuple(sorted(unresolved)))


def _ratio(total: int | None, accepted: int | None) -> ExactMicrounitRatio | None:
    if total is None or accepted is None or accepted <= 0:
        return None
    return ExactMicrounitRatio(total, accepted)


def build_economics_receipt(*, route_id: str, mission_ref: str,
                            accepted_value_definition_ref: str,
                            measurement_window_ref: str, principal_scope: str,
                            currency: str, cohort: Mapping[str, str],
                            route_evidence: Sequence[EvidenceBinding],
                            friction_receipt_ref: str,
                            accepted_value: AcceptedValueEvidence,
                            costs: Sequence[CostObservation],
                            reuse_evidence: Sequence[ReuseEvidence] = ()) -> AdoptionEconomicsReceipt:
    route_id = _text(route_id, "ROUTE_ID_REQUIRED")
    mission_ref = _text(mission_ref, "MISSION_REF_REQUIRED")
    accepted_value_definition_ref = _text(accepted_value_definition_ref, "ACCEPTED_VALUE_DEFINITION_REQUIRED")
    measurement_window_ref = _text(measurement_window_ref, "MEASUREMENT_WINDOW_REQUIRED")
    principal_scope = _principal(principal_scope)
    currency = _currency(currency)
    friction_receipt_ref = _text(friction_receipt_ref, "FRICTION_RECEIPT_REF_REQUIRED")
    cohort = _normalize_cohort(cohort)
    evidence = _normalize_evidence(route_evidence)
    if not isinstance(accepted_value, AcceptedValueEvidence):
        raise EconomicsError("ACCEPTED_VALUE_EVIDENCE_REQUIRED")
    costs = _normalize_costs(costs, currency)
    reuse = _normalize_reuse(reuse_evidence)
    lifecycle, lifecycle_provenance, unknown_costs, scenario_costs, estimated_costs = _lifecycle_total(costs)
    accepted = accepted_value.accepted_count
    if accepted is None:
        cpav, disposition = None, "PARTIAL_ACCEPTED_VALUE_UNKNOWN"
    elif accepted == 0:
        cpav, disposition = None, "NO_ACCEPTED_VALUE"
    elif lifecycle is None:
        cpav, disposition = None, "PARTIAL_COST_UNKNOWN_OR_SCENARIO"
    else:
        cpav = _ratio(lifecycle, accepted)
        if lifecycle_provenance == "ESTIMATED":
            disposition = "RESOLVED_ESTIMATED_USER" if accepted_value.is_user_evidence else "RESOLVED_ESTIMATED_TECHNICAL"
        else:
            disposition = "RESOLVED_USER" if accepted_value.is_user_evidence else "RESOLVED_TECHNICAL"
    user_cpav = cpav if accepted_value.is_user_evidence else None
    avoided, unresolved_reuse = _validated_reuse_money(reuse, principal_scope=principal_scope, currency=currency)
    counterfactual = lifecycle + avoided if lifecycle is not None and avoided is not None else None
    counterfactual_cpav = _ratio(counterfactual, accepted)
    logical = {
        "schema": RECEIPT_SCHEMA, "route_id": route_id, "mission_ref": mission_ref,
        "accepted_value_definition_ref": accepted_value_definition_ref,
        "measurement_window_ref": measurement_window_ref, "principal_scope": principal_scope,
        "currency": currency, "cohort": cohort,
        "route_evidence": [item.logical() for item in evidence],
        "friction_receipt_ref": friction_receipt_ref, "accepted_value": accepted_value.logical(),
        "costs": [item.logical() for item in costs], "reuse_evidence": [item.logical() for item in reuse],
        "lifecycle_monetary_total_microunits": lifecycle,
        "lifecycle_cost_provenance": lifecycle_provenance,
        "cpav_ratio": cpav.logical() if cpav else None,
        "user_cpav_ratio": user_cpav.logical() if user_cpav else None,
        "validated_avoided_provider_microunits": avoided,
        "counterfactual_without_reuse_microunits": counterfactual,
        "counterfactual_cpav_ratio": counterfactual_cpav.logical() if counterfactual_cpav else None,
        "unknown_cost_kinds": list(unknown_costs), "scenario_cost_kinds": list(scenario_costs),
        "estimated_cost_kinds": list(estimated_costs), "unresolved_reuse": list(unresolved_reuse),
        "disposition": disposition, "payment_authorized": False,
        "provider_authorized": False, "execution_authorized": False,
    }
    logical_id = "aecon-" + _digest("AURA_ADOPTION_ECONOMICS_V1", logical)
    return AdoptionEconomicsReceipt(
        schema=RECEIPT_SCHEMA, route_id=route_id, mission_ref=mission_ref,
        accepted_value_definition_ref=accepted_value_definition_ref,
        measurement_window_ref=measurement_window_ref, principal_scope=principal_scope,
        currency=currency, cohort=cohort, route_evidence=evidence,
        friction_receipt_ref=friction_receipt_ref, accepted_value=accepted_value,
        costs=costs, reuse_evidence=reuse,
        lifecycle_monetary_total_microunits=lifecycle,
        lifecycle_cost_provenance=lifecycle_provenance, cpav_ratio=cpav,
        user_cpav_ratio=user_cpav, validated_avoided_provider_microunits=avoided,
        counterfactual_without_reuse_microunits=counterfactual,
        counterfactual_cpav_ratio=counterfactual_cpav, unknown_cost_kinds=unknown_costs,
        scenario_cost_kinds=scenario_costs, estimated_cost_kinds=estimated_costs,
        unresolved_reuse=unresolved_reuse, disposition=disposition, logical_id=logical_id,
        payment_authorized=False, provider_authorized=False, execution_authorized=False,
    )


def verify_economics_receipt(receipt: AdoptionEconomicsReceipt) -> AdoptionEconomicsReceipt:
    if not isinstance(receipt, AdoptionEconomicsReceipt):
        raise EconomicsError("ECONOMICS_RECEIPT_REQUIRED")
    rebuilt = build_economics_receipt(
        route_id=receipt.route_id, mission_ref=receipt.mission_ref,
        accepted_value_definition_ref=receipt.accepted_value_definition_ref,
        measurement_window_ref=receipt.measurement_window_ref,
        principal_scope=receipt.principal_scope, currency=receipt.currency,
        cohort=receipt.cohort, route_evidence=receipt.route_evidence,
        friction_receipt_ref=receipt.friction_receipt_ref,
        accepted_value=receipt.accepted_value, costs=receipt.costs,
        reuse_evidence=receipt.reuse_evidence,
    )
    if _canonical(receipt.to_dict()) != _canonical(rebuilt.to_dict()):
        raise EconomicsError("ECONOMICS_RECEIPT_DERIVATION_MISMATCH")
    return receipt


def _provider_paid_evidence(receipt: AdoptionEconomicsReceipt) -> CostObservation | None:
    provider = next((item for item in receipt.costs if item.kind is CostKind.PROVIDER), None)
    if (provider and provider.status is ObservationStatus.KNOWN
            and provider.value_microunits is not None and provider.value_microunits > 0
            and provider.evidence_class in OBSERVED_MONEY_EVIDENCE
            and provider.source_current is True and provider.source_current_evidence_ref):
        return provider
    return None


def compile_economics_admission(receipt: AdoptionEconomicsReceipt, *,
                                max_user_cpav_microunits: int | None,
                                allow_paid_candidate: bool = False) -> AdoptionEconomicsAdmission:
    verify_economics_receipt(receipt)
    if max_user_cpav_microunits is not None:
        _nn_int(max_user_cpav_microunits, "MAX_USER_CPAV_INVALID")
    if type(allow_paid_candidate) is not bool:
        raise EconomicsError("ALLOW_PAID_CANDIDATE_BOOL_REQUIRED")
    user_cpav = receipt.user_cpav_ratio
    provider_paid = _provider_paid_evidence(receipt)
    if receipt.accepted_value.accepted_count == 0:
        disposition, within, candidate, reason = "NO_ACCEPTED_VALUE", None, False, "No accepted value observed; CPAV is undefined."
    elif not receipt.accepted_value.is_user_evidence:
        disposition, within, candidate, reason = "NEEDS_USER_VALUE_EVIDENCE", None, False, "Technical acceptance cannot justify paid-route economics."
    elif receipt.lifecycle_cost_provenance != "OBSERVED":
        disposition, within, candidate, reason = "NEEDS_OBSERVED_COST_EVIDENCE", None, False, "Estimated/scenario/unresolved lifecycle cost cannot justify paid-route candidacy."
    elif user_cpav is None:
        disposition, within, candidate, reason = "NEEDS_COST_EVIDENCE", None, False, "Lifecycle cost or accepted-value evidence remains unresolved."
    elif provider_paid is None:
        disposition, within, candidate, reason = "NO_PAID_PROVIDER_COST_EVIDENCE", None, False, "No positive current observed provider-cost evidence supports a paid candidate."
    elif max_user_cpav_microunits is None:
        disposition, within, candidate, reason = "OBSERVED_ONLY_NO_BUDGET_POLICY", None, False, "Observed user CPAV exists but no current ceiling was supplied."
    else:
        within = user_cpav.compare_to_integer_ceiling(max_user_cpav_microunits) <= 0
        if within and allow_paid_candidate:
            disposition, candidate, reason = "WITHIN_CPAV_POLICY_CANDIDATE", True, "Within supplied CPAV ceiling with observed provider-cost evidence; effect authority remains false."
        elif within:
            disposition, candidate, reason = "WITHIN_CPAV_POLICY_NO_PAID_ADMISSION", False, "Within ceiling but paid candidacy is not allowed."
        else:
            disposition, candidate, reason = "EXCEEDS_CPAV_POLICY", False, "Observed user CPAV exceeds the supplied ceiling."
    return AdoptionEconomicsAdmission(
        schema=ADMISSION_SCHEMA, receipt_logical_id=receipt.logical_id,
        disposition=disposition, max_user_cpav_microunits=max_user_cpav_microunits,
        user_cpav_ratio=user_cpav, within_policy=within, paid_route_candidate=candidate,
        reason=reason, payment_authorized=False, provider_authorized=False,
        execution_authorized=False,
    )


def compare_economics(baseline: AdoptionEconomicsReceipt,
                      candidate: AdoptionEconomicsReceipt) -> AdoptionEconomicsComparison:
    verify_economics_receipt(baseline)
    verify_economics_receipt(candidate)
    incompatible: list[str] = []
    if baseline.mission_ref != candidate.mission_ref:
        incompatible.append("MISSION")
    if baseline.accepted_value_definition_ref != candidate.accepted_value_definition_ref:
        incompatible.append("ACCEPTED_VALUE_DEFINITION")
    if baseline.currency != candidate.currency:
        incompatible.append("CURRENCY")
    if baseline.measurement_window_ref != candidate.measurement_window_ref:
        incompatible.append("MEASUREMENT_WINDOW")
    if _canonical(dict(baseline.cohort)) != _canonical(dict(candidate.cohort)):
        incompatible.append("COHORT")
    if baseline.accepted_value.evidence_class is not candidate.accepted_value.evidence_class:
        incompatible.append("ACCEPTED_VALUE_EVIDENCE_CLASS")
    if baseline.lifecycle_cost_provenance != candidate.lifecycle_cost_provenance:
        incompatible.append("COST_PROVENANCE")
    if baseline.cpav_ratio is None or candidate.cpav_ratio is None:
        incompatible.append("CPAV_UNRESOLVED")
    comparable = not incompatible
    delta = None
    lower = None
    if comparable:
        assert baseline.cpav_ratio is not None and candidate.cpav_ratio is not None
        relation = candidate.cpav_ratio.compare(baseline.cpav_ratio)
        delta = candidate.cpav_ratio.subtract(baseline.cpav_ratio)
        if relation < 0:
            lower = candidate.route_id
        elif relation > 0:
            lower = baseline.route_id
    return AdoptionEconomicsComparison(
        schema=COMPARISON_SCHEMA, baseline_logical_id=baseline.logical_id,
        candidate_logical_id=candidate.logical_id, comparable=comparable,
        incompatibilities=tuple(sorted(set(incompatible))),
        baseline_cpav_ratio=baseline.cpav_ratio, candidate_cpav_ratio=candidate.cpav_ratio,
        cpav_delta_ratio=delta, lower_cpav_route_id=lower,
        baseline_friction_receipt_ref=baseline.friction_receipt_ref,
        candidate_friction_receipt_ref=candidate.friction_receipt_ref,
        overall_route_preference_claimed=False,
    )


def validate_economics_receipt_dict(value: Mapping[str, Any]) -> None:
    """Semantic validator required in addition to structural JSON Schema validation."""
    if not isinstance(value, Mapping):
        raise EconomicsError("RECEIPT_MAPPING_REQUIRED")
    accepted = value.get("accepted_value")
    if not isinstance(accepted, Mapping):
        raise EconomicsError("ACCEPTED_VALUE_MAPPING_REQUIRED")
    ac = accepted.get("accepted_count")
    at = accepted.get("attempt_count")
    if (ac is None) != (at is None):
        raise EconomicsError("ACCEPTED_VALUE_COUNTS_COMPLETENESS_MISMATCH")
    if ac is not None:
        _nn_int(ac, "ACCEPTED_VALUE_COUNT_INVALID")
        _nn_int(at, "ATTEMPT_COUNT_INVALID")
        if ac > at:
            raise EconomicsError("ACCEPTED_VALUE_EXCEEDS_ATTEMPTS")
    costs = value.get("costs")
    if not isinstance(costs, list):
        raise EconomicsError("COSTS_SEQUENCE_REQUIRED")
    kinds = [item.get("kind") for item in costs if isinstance(item, Mapping)]
    if len(costs) != len(COST_KINDS) or set(kinds) != set(COST_KINDS) or len(set(kinds)) != len(kinds):
        raise EconomicsError("COST_KIND_COVERAGE_INVALID")
    evidence_class = accepted.get("evidence_class")
    user_cpav = value.get("user_cpav_ratio")
    if evidence_class in {"TECHNICAL_SYNTHETIC", "TECHNICAL_EXECUTED"} and user_cpav is not None:
        raise EconomicsError("TECHNICAL_ACCEPTANCE_CANNOT_HAVE_USER_CPAV")
    if value.get("payment_authorized") is not False or value.get("provider_authorized") is not False or value.get("execution_authorized") is not False:
        raise EconomicsError("AUTHORITY_MUST_BE_FALSE")
