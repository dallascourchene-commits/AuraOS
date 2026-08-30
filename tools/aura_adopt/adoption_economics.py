"""AURA-ADOPT-001 ZF-10A: consequence-complete adoption economics.

Pure deterministic economics membrane. UNKNOWN never becomes zero. Monetary
ratios use exact normalized integer fractions, never binary floating point. This
module performs no provider call, credential/payment effect, telemetry
collection, installation, deployment, or execution authorization.
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
ALLOWED_COHORT_KEYS = frozenset({
    "device_class", "storage_class", "connectivity_class", "skill_class",
    "trust_preference", "compute_preference", "storage_preference",
    "accessibility_class",
})
FORBIDDEN_KEY_TOKENS = frozenset({
    "api_key", "apikey", "secret", "token", "credential", "credentials",
    "password", "prompt", "content", "email", "phone", "user_id", "userid",
    "ip_address", "name", "address",
})
ADMITTED_LIFECYCLE_EVIDENCE = frozenset({
    MoneyEvidenceClass.BILLED,
    MoneyEvidenceClass.MEASURED,
    MoneyEvidenceClass.ESTIMATED_WITH_POLICY,
})
VALIDATED_REUSE_MONEY_EVIDENCE = frozenset({
    MoneyEvidenceClass.BILLED,
    MoneyEvidenceClass.MEASURED,
})


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
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


def _reject_private(value: Any, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).strip().casefold() in FORBIDDEN_KEY_TOKENS:
                raise EconomicsError("PRIVATE_FIELD_FORBIDDEN", f"{path}.{key}")
            _reject_private(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for idx, child in enumerate(value):
            _reject_private(child, f"{path}[{idx}]")


def _normalize_cohort(value: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        raise EconomicsError("COHORT_REQUIRED")
    keys = {str(k) for k in value}
    extra = sorted(keys - ALLOWED_COHORT_KEYS)
    if extra:
        raise EconomicsError("COHORT_FIELD_NOT_PRIVACY_MINIMAL", ",".join(extra))
    out = {str(k): _text(v, "COHORT_VALUE_REQUIRED") for k, v in value.items()}
    _reject_private(out, "cohort")
    return out


@dataclass(frozen=True)
class ExactMicrounitRatio:
    """Exact normalized money-per-accepted-value ratio."""

    numerator_microunits: int
    denominator_accepted_values: int

    def __post_init__(self) -> None:
        numerator = _nn_int(self.numerator_microunits, "RATIO_NUMERATOR_INVALID")
        denominator = _nn_int(
            self.denominator_accepted_values, "RATIO_DENOMINATOR_INVALID"
        )
        if denominator == 0:
            raise EconomicsError("RATIO_DENOMINATOR_ZERO")
        divisor = gcd(numerator, denominator)
        object.__setattr__(self, "numerator_microunits", numerator // divisor)
        object.__setattr__(
            self, "denominator_accepted_values", denominator // divisor
        )

    def logical(self) -> dict[str, int]:
        return {
            "numerator_microunits": self.numerator_microunits,
            "denominator_accepted_values": self.denominator_accepted_values,
        }

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
    """Exact signed delta used only for route comparison."""

    numerator_microunits: int
    denominator_accepted_values: int

    def __post_init__(self) -> None:
        numerator = self.numerator_microunits
        denominator = self.denominator_accepted_values
        if isinstance(numerator, bool) or not isinstance(numerator, int):
            raise EconomicsError("SIGNED_RATIO_NUMERATOR_INVALID")
        if isinstance(denominator, bool) or not isinstance(denominator, int) or denominator <= 0:
            raise EconomicsError("SIGNED_RATIO_DENOMINATOR_INVALID")
        divisor = gcd(abs(numerator), denominator)
        object.__setattr__(self, "numerator_microunits", numerator // divisor)
        object.__setattr__(
            self, "denominator_accepted_values", denominator // divisor
        )

    def logical(self) -> dict[str, int]:
        return {
            "numerator_microunits": self.numerator_microunits,
            "denominator_accepted_values": self.denominator_accepted_values,
        }


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
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CostKind):
            raise EconomicsError("COST_KIND_REQUIRED")
        if not isinstance(self.status, ObservationStatus):
            raise EconomicsError("COST_STATUS_REQUIRED", self.kind.value)
        if not isinstance(self.evidence_class, MoneyEvidenceClass):
            raise EconomicsError("COST_EVIDENCE_CLASS_REQUIRED", self.kind.value)
        _text(self.currency, "COST_CURRENCY_REQUIRED")
        _text(self.source_ref, "COST_SOURCE_REF_REQUIRED")
        _text(self.source_generation, "COST_SOURCE_GENERATION_REQUIRED")
        _text(self.currentness_ref, "COST_CURRENTNESS_REQUIRED")
        if self.status is ObservationStatus.KNOWN:
            _nn_int(self.value_microunits, "KNOWN_COST_VALUE_REQUIRED")
            if self.evidence_class is MoneyEvidenceClass.UNKNOWN:
                raise EconomicsError(
                    "KNOWN_COST_CANNOT_HAVE_UNKNOWN_EVIDENCE", self.kind.value
                )
        else:
            if self.value_microunits is not None:
                raise EconomicsError(
                    "NONKNOWN_COST_MUST_NOT_HAVE_VALUE", self.kind.value
                )
            if not isinstance(self.reason, str) or not self.reason.strip():
                raise EconomicsError("NONKNOWN_COST_REASON_REQUIRED", self.kind.value)
            if (
                self.status is ObservationStatus.UNKNOWN
                and self.evidence_class is not MoneyEvidenceClass.UNKNOWN
            ):
                raise EconomicsError(
                    "UNKNOWN_COST_EVIDENCE_MUST_BE_UNKNOWN", self.kind.value
                )
        if (
            self.evidence_class is MoneyEvidenceClass.ESTIMATED_WITH_POLICY
            and "policy" not in self.source_ref.casefold()
        ):
            raise EconomicsError(
                "ESTIMATED_COST_POLICY_REF_REQUIRED", self.kind.value
            )

    def logical(self) -> dict[str, Any]:
        out = asdict(self)
        out["kind"] = self.kind.value
        out["status"] = self.status.value
        out["evidence_class"] = self.evidence_class.value
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
        accepted = _nn_int(
            self.accepted_count, "ACCEPTED_VALUE_COUNT_INVALID", allow_none=True
        )
        attempts = _nn_int(
            self.attempt_count, "ATTEMPT_COUNT_INVALID", allow_none=True
        )
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
        return self.evidence_class in {
            AcceptedValueEvidenceClass.USER_EXPLICIT,
            AcceptedValueEvidenceClass.CONSENTED_STUDY,
        }

    def logical(self) -> dict[str, Any]:
        out = asdict(self)
        out["evidence_class"] = self.evidence_class.value
        return out


@dataclass(frozen=True)
class ReuseEvidence:
    kind: ReuseKind
    status: ObservationStatus
    source_ref: str
    source_generation: str
    currentness_ref: str
    evidence_class: MoneyEvidenceClass
    principal_scope: str
    source_current: bool | None
    source_current_evidence_ref: str | None
    privacy_isolated: bool | None
    privacy_isolation_evidence_ref: str | None
    avoided_provider_microunits: int | None = None
    avoided_recompute_units: int | None = None
    avoided_latency_ms: int | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ReuseKind):
            raise EconomicsError("REUSE_KIND_REQUIRED")
        if not isinstance(self.status, ObservationStatus):
            raise EconomicsError("REUSE_STATUS_REQUIRED")
        if not isinstance(self.evidence_class, MoneyEvidenceClass):
            raise EconomicsError("REUSE_EVIDENCE_CLASS_REQUIRED")
        _text(self.source_ref, "REUSE_SOURCE_REF_REQUIRED")
        _text(self.source_generation, "REUSE_SOURCE_GENERATION_REQUIRED")
        _text(self.currentness_ref, "REUSE_CURRENTNESS_REQUIRED")
        _text(self.principal_scope, "REUSE_PRINCIPAL_SCOPE_REQUIRED")
        for name in ("source_current", "privacy_isolated"):
            value = getattr(self, name)
            if value is not None and type(value) is not bool:
                raise EconomicsError("REUSE_BOOLEAN_INVALID", name)
        if self.source_current is True:
            _text(
                self.source_current_evidence_ref,
                "SOURCE_CURRENT_EVIDENCE_REF_REQUIRED",
            )
        elif self.source_current_evidence_ref is not None:
            _text(
                self.source_current_evidence_ref,
                "SOURCE_CURRENT_EVIDENCE_REF_INVALID",
            )
        if self.privacy_isolated is True:
            _text(
                self.privacy_isolation_evidence_ref,
                "PRIVACY_ISOLATION_EVIDENCE_REF_REQUIRED",
            )
        elif self.privacy_isolation_evidence_ref is not None:
            _text(
                self.privacy_isolation_evidence_ref,
                "PRIVACY_ISOLATION_EVIDENCE_REF_INVALID",
            )
        for name in (
            "avoided_provider_microunits",
            "avoided_recompute_units",
            "avoided_latency_ms",
        ):
            _nn_int(getattr(self, name), f"{name.upper()}_INVALID", allow_none=True)
        if self.status is not ObservationStatus.KNOWN:
            if any(
                getattr(self, name) is not None
                for name in (
                    "avoided_provider_microunits",
                    "avoided_recompute_units",
                    "avoided_latency_ms",
                )
            ):
                raise EconomicsError(
                    "NONKNOWN_REUSE_MUST_NOT_HAVE_VALUES", self.kind.value
                )
            if not isinstance(self.reason, str) or not self.reason.strip():
                raise EconomicsError(
                    "NONKNOWN_REUSE_REASON_REQUIRED", self.kind.value
                )
        if (
            self.status is ObservationStatus.UNKNOWN
            and self.evidence_class is not MoneyEvidenceClass.UNKNOWN
        ):
            raise EconomicsError(
                "UNKNOWN_REUSE_EVIDENCE_MUST_BE_UNKNOWN", self.kind.value
            )

    def logical(self) -> dict[str, Any]:
        out = asdict(self)
        out["kind"] = self.kind.value
        out["status"] = self.status.value
        out["evidence_class"] = self.evidence_class.value
        return out


@dataclass(frozen=True)
class AdoptionEconomicsReceipt:
    schema: str
    route_id: str
    mission_ref: str
    measurement_window_ref: str
    currency: str
    cohort: Mapping[str, str]
    route_evidence: tuple[EvidenceBinding, ...]
    friction_receipt_ref: str
    accepted_value: AcceptedValueEvidence
    costs: tuple[CostObservation, ...]
    reuse_evidence: tuple[ReuseEvidence, ...]
    lifecycle_monetary_total_microunits: int | None
    cpav_ratio: ExactMicrounitRatio | None
    user_cpav_ratio: ExactMicrounitRatio | None
    validated_avoided_provider_microunits: int | None
    counterfactual_without_reuse_microunits: int | None
    counterfactual_cpav_ratio: ExactMicrounitRatio | None
    unknown_cost_kinds: tuple[str, ...]
    scenario_cost_kinds: tuple[str, ...]
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
            "measurement_window_ref": self.measurement_window_ref,
            "currency": self.currency,
            "cohort": dict(self.cohort),
            "route_evidence": [asdict(item) for item in self.route_evidence],
            "friction_receipt_ref": self.friction_receipt_ref,
            "accepted_value": self.accepted_value.logical(),
            "costs": [item.logical() for item in self.costs],
            "reuse_evidence": [item.logical() for item in self.reuse_evidence],
            "lifecycle_monetary_total_microunits":
                self.lifecycle_monetary_total_microunits,
            "cpav_ratio": self.cpav_ratio.logical() if self.cpav_ratio else None,
            "user_cpav_ratio":
                self.user_cpav_ratio.logical() if self.user_cpav_ratio else None,
            "validated_avoided_provider_microunits":
                self.validated_avoided_provider_microunits,
            "counterfactual_without_reuse_microunits":
                self.counterfactual_without_reuse_microunits,
            "counterfactual_cpav_ratio":
                self.counterfactual_cpav_ratio.logical()
                if self.counterfactual_cpav_ratio else None,
            "unknown_cost_kinds": list(self.unknown_cost_kinds),
            "scenario_cost_kinds": list(self.scenario_cost_kinds),
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
    observed_user_cpav_ratio: ExactMicrounitRatio | None
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


def _normalize_costs(
    costs: Sequence[CostObservation], currency: str
) -> tuple[CostObservation, ...]:
    if isinstance(costs, (str, bytes)) or not isinstance(costs, Sequence):
        raise EconomicsError("COSTS_SEQUENCE_REQUIRED")
    out = tuple(costs)
    kinds = [
        item.kind.value if isinstance(item, CostObservation) else None
        for item in out
    ]
    if (
        len(out) != len(COST_KINDS)
        or set(kinds) != set(COST_KINDS)
        or len(set(kinds)) != len(kinds)
    ):
        raise EconomicsError("COST_KIND_COVERAGE_INVALID")
    if any(item.currency != currency for item in out):
        raise EconomicsError("COST_CURRENCY_MISMATCH")
    return tuple(sorted(out, key=lambda item: item.kind.value))


def _normalize_reuse(
    reuse: Sequence[ReuseEvidence],
) -> tuple[ReuseEvidence, ...]:
    if isinstance(reuse, (str, bytes)) or not isinstance(reuse, Sequence):
        raise EconomicsError("REUSE_SEQUENCE_REQUIRED")
    if not all(isinstance(item, ReuseEvidence) for item in reuse):
        raise EconomicsError("REUSE_EVIDENCE_TYPE_REQUIRED")
    return tuple(
        sorted(
            tuple(reuse),
            key=lambda item: (
                item.kind.value,
                item.source_ref,
                item.source_generation,
            ),
        )
    )


def _lifecycle_total(
    costs: Sequence[CostObservation],
) -> tuple[int | None, tuple[str, ...], tuple[str, ...]]:
    total = 0
    unknown: list[str] = []
    scenario: list[str] = []
    for item in costs:
        if item.status is ObservationStatus.NOT_APPLICABLE:
            continue
        if item.status is ObservationStatus.UNKNOWN:
            unknown.append(item.kind.value)
            continue
        if item.evidence_class is MoneyEvidenceClass.SCENARIO:
            scenario.append(item.kind.value)
            continue
        if item.evidence_class not in ADMITTED_LIFECYCLE_EVIDENCE:
            unknown.append(item.kind.value)
            continue
        assert item.value_microunits is not None
        total += item.value_microunits
    return (
        None if unknown or scenario else total,
        tuple(sorted(unknown)),
        tuple(sorted(scenario)),
    )


def _validated_reuse_money(
    reuse: Sequence[ReuseEvidence],
) -> tuple[int | None, tuple[str, ...]]:
    if not reuse:
        return 0, ()
    total = 0
    unresolved: list[str] = []
    for item in reuse:
        label = f"{item.kind.value}:{item.source_ref}"
        if item.status is ObservationStatus.NOT_APPLICABLE:
            continue
        if item.status is ObservationStatus.UNKNOWN:
            unresolved.append(label)
        elif item.source_current is not True:
            unresolved.append(f"{label}:SOURCE_CURRENTNESS")
        elif not item.source_current_evidence_ref:
            unresolved.append(f"{label}:SOURCE_CURRENTNESS_EVIDENCE")
        elif item.privacy_isolated is not True:
            unresolved.append(f"{label}:PRIVACY_ISOLATION")
        elif not item.privacy_isolation_evidence_ref:
            unresolved.append(f"{label}:PRIVACY_ISOLATION_EVIDENCE")
        elif item.evidence_class not in VALIDATED_REUSE_MONEY_EVIDENCE:
            unresolved.append(f"{label}:MONEY_EVIDENCE")
        elif item.avoided_provider_microunits is None:
            unresolved.append(f"{label}:AVOIDED_PROVIDER_COST")
        else:
            total += item.avoided_provider_microunits
    return (None if unresolved else total, tuple(sorted(unresolved)))


def _ratio(
    total_microunits: int | None, accepted_count: int | None
) -> ExactMicrounitRatio | None:
    if total_microunits is None or accepted_count is None or accepted_count <= 0:
        return None
    return ExactMicrounitRatio(total_microunits, accepted_count)


def _provider_paid_evidence(
    receipt: AdoptionEconomicsReceipt,
) -> CostObservation | None:
    provider = next(
        (item for item in receipt.costs if item.kind is CostKind.PROVIDER),
        None,
    )
    if (
        provider is not None
        and provider.status is ObservationStatus.KNOWN
        and provider.value_microunits is not None
        and provider.value_microunits > 0
        and provider.evidence_class in ADMITTED_LIFECYCLE_EVIDENCE
    ):
        return provider
    return None


def build_economics_receipt(
    *,
    route_id: str,
    mission_ref: str,
    measurement_window_ref: str,
    currency: str,
    cohort: Mapping[str, str],
    route_evidence: Sequence[EvidenceBinding],
    friction_receipt_ref: str,
    accepted_value: AcceptedValueEvidence,
    costs: Sequence[CostObservation],
    reuse_evidence: Sequence[ReuseEvidence] = (),
) -> AdoptionEconomicsReceipt:
    route_id = _text(route_id, "ROUTE_ID_REQUIRED")
    mission_ref = _text(mission_ref, "MISSION_REF_REQUIRED")
    measurement_window_ref = _text(
        measurement_window_ref, "MEASUREMENT_WINDOW_REQUIRED"
    )
    currency = _text(currency, "CURRENCY_REQUIRED")
    friction_receipt_ref = _text(
        friction_receipt_ref, "FRICTION_RECEIPT_REF_REQUIRED"
    )
    cohort = _normalize_cohort(cohort)
    evidence = tuple(route_evidence)
    if not evidence or not all(
        isinstance(item, EvidenceBinding) for item in evidence
    ):
        raise EconomicsError("ROUTE_EVIDENCE_REQUIRED")
    evidence = tuple(
        sorted(
            evidence,
            key=lambda item: (
                item.artifact_ref,
                item.source_generation,
                item.artifact_digest,
            ),
        )
    )
    if not isinstance(accepted_value, AcceptedValueEvidence):
        raise EconomicsError("ACCEPTED_VALUE_EVIDENCE_REQUIRED")
    costs = _normalize_costs(costs, currency)
    reuse = _normalize_reuse(reuse_evidence)

    lifecycle, unknown_costs, scenario_costs = _lifecycle_total(costs)
    accepted = accepted_value.accepted_count
    if accepted is None:
        cpav = None
        disposition = "PARTIAL_ACCEPTED_VALUE_UNKNOWN"
    elif accepted == 0:
        cpav = None
        disposition = "NO_ACCEPTED_VALUE"
    elif lifecycle is None:
        cpav = None
        disposition = "PARTIAL_COST_UNKNOWN_OR_SCENARIO"
    else:
        cpav = _ratio(lifecycle, accepted)
        disposition = (
            "RESOLVED_USER"
            if accepted_value.is_user_evidence
            else "RESOLVED_TECHNICAL"
        )
    user_cpav = cpav if accepted_value.is_user_evidence else None

    avoided, unresolved_reuse = _validated_reuse_money(reuse)
    counterfactual = (
        lifecycle + avoided
        if lifecycle is not None and avoided is not None
        else None
    )
    counterfactual_cpav = _ratio(counterfactual, accepted)
    logical = {
        "schema": RECEIPT_SCHEMA,
        "route_id": route_id,
        "mission_ref": mission_ref,
        "measurement_window_ref": measurement_window_ref,
        "currency": currency,
        "cohort": cohort,
        "route_evidence": [asdict(item) for item in evidence],
        "friction_receipt_ref": friction_receipt_ref,
        "accepted_value": accepted_value.logical(),
        "costs": [item.logical() for item in costs],
        "reuse_evidence": [item.logical() for item in reuse],
        "lifecycle_monetary_total_microunits": lifecycle,
        "cpav_ratio": cpav.logical() if cpav else None,
        "user_cpav_ratio": user_cpav.logical() if user_cpav else None,
        "validated_avoided_provider_microunits": avoided,
        "counterfactual_without_reuse_microunits": counterfactual,
        "counterfactual_cpav_ratio":
            counterfactual_cpav.logical() if counterfactual_cpav else None,
        "unknown_cost_kinds": list(unknown_costs),
        "scenario_cost_kinds": list(scenario_costs),
        "unresolved_reuse": list(unresolved_reuse),
        "disposition": disposition,
        "payment_authorized": False,
        "provider_authorized": False,
        "execution_authorized": False,
    }
    logical_id = "aecon-" + _digest("AURA_ADOPTION_ECONOMICS_V1", logical)
    return AdoptionEconomicsReceipt(
        schema=RECEIPT_SCHEMA,
        route_id=route_id,
        mission_ref=mission_ref,
        measurement_window_ref=measurement_window_ref,
        currency=currency,
        cohort=cohort,
        route_evidence=evidence,
        friction_receipt_ref=friction_receipt_ref,
        accepted_value=accepted_value,
        costs=costs,
        reuse_evidence=reuse,
        lifecycle_monetary_total_microunits=lifecycle,
        cpav_ratio=cpav,
        user_cpav_ratio=user_cpav,
        validated_avoided_provider_microunits=avoided,
        counterfactual_without_reuse_microunits=counterfactual,
        counterfactual_cpav_ratio=counterfactual_cpav,
        unknown_cost_kinds=unknown_costs,
        scenario_cost_kinds=scenario_costs,
        unresolved_reuse=unresolved_reuse,
        disposition=disposition,
        logical_id=logical_id,
        payment_authorized=False,
        provider_authorized=False,
        execution_authorized=False,
    )


def compile_economics_admission(
    receipt: AdoptionEconomicsReceipt,
    *,
    max_user_cpav_microunits: int | None,
    allow_paid_candidate: bool = False,
) -> AdoptionEconomicsAdmission:
    if not isinstance(receipt, AdoptionEconomicsReceipt):
        raise EconomicsError("ECONOMICS_RECEIPT_REQUIRED")
    if max_user_cpav_microunits is not None:
        _nn_int(max_user_cpav_microunits, "MAX_USER_CPAV_INVALID")
    if type(allow_paid_candidate) is not bool:
        raise EconomicsError("ALLOW_PAID_CANDIDATE_BOOL_REQUIRED")

    user_cpav = receipt.user_cpav_ratio
    provider_paid = _provider_paid_evidence(receipt)
    if receipt.accepted_value.accepted_count == 0:
        disposition, within, candidate = "NO_ACCEPTED_VALUE", None, False
        reason = "No accepted value observed; CPAV is undefined."
    elif not receipt.accepted_value.is_user_evidence:
        disposition, within, candidate = (
            "NEEDS_USER_VALUE_EVIDENCE", None, False
        )
        reason = (
            "Technical/synthetic acceptance cannot justify a paid-route "
            "economics candidate."
        )
    elif user_cpav is None:
        disposition, within, candidate = "NEEDS_COST_EVIDENCE", None, False
        reason = "Lifecycle cost or accepted-value evidence remains unresolved."
    elif provider_paid is None:
        disposition, within, candidate = (
            "NO_PAID_PROVIDER_COST_EVIDENCE", None, False
        )
        reason = (
            "No positive current provider-cost observation supports labeling "
            "this route as a paid candidate."
        )
    elif max_user_cpav_microunits is None:
        disposition, within, candidate = (
            "OBSERVED_ONLY_NO_BUDGET_POLICY", None, False
        )
        reason = (
            "Observed user CPAV exists but no current ceiling was supplied."
        )
    else:
        relation = user_cpav.compare_to_integer_ceiling(
            max_user_cpav_microunits
        )
        within = relation <= 0
        if within and allow_paid_candidate:
            disposition, candidate = "WITHIN_CPAV_POLICY_CANDIDATE", True
            reason = (
                "Within supplied CPAV ceiling with positive provider-cost "
                "evidence; effect/provider authority remains false."
            )
        elif within:
            disposition, candidate = (
                "WITHIN_CPAV_POLICY_NO_PAID_ADMISSION", False
            )
            reason = "Within ceiling but paid candidacy is not allowed."
        else:
            disposition, candidate = "EXCEEDS_CPAV_POLICY", False
            reason = "Observed user CPAV exceeds the supplied ceiling."
    return AdoptionEconomicsAdmission(
        schema=ADMISSION_SCHEMA,
        receipt_logical_id=receipt.logical_id,
        disposition=disposition,
        max_user_cpav_microunits=max_user_cpav_microunits,
        observed_user_cpav_ratio=user_cpav,
        within_policy=within,
        paid_route_candidate=candidate,
        reason=reason,
        payment_authorized=False,
        provider_authorized=False,
        execution_authorized=False,
    )


def compare_economics(
    baseline: AdoptionEconomicsReceipt,
    candidate: AdoptionEconomicsReceipt,
) -> AdoptionEconomicsComparison:
    if not isinstance(
        baseline, AdoptionEconomicsReceipt
    ) or not isinstance(candidate, AdoptionEconomicsReceipt):
        raise EconomicsError("ECONOMICS_RECEIPTS_REQUIRED")
    incompatible: list[str] = []
    if baseline.currency != candidate.currency:
        incompatible.append("CURRENCY")
    if baseline.measurement_window_ref != candidate.measurement_window_ref:
        incompatible.append("MEASUREMENT_WINDOW")
    if _canonical(dict(baseline.cohort)) != _canonical(dict(candidate.cohort)):
        incompatible.append("COHORT")
    if (
        baseline.accepted_value.evidence_class
        is not candidate.accepted_value.evidence_class
    ):
        incompatible.append("ACCEPTED_VALUE_EVIDENCE_CLASS")
    if baseline.cpav_ratio is None or candidate.cpav_ratio is None:
        incompatible.append("CPAV_UNRESOLVED")
    comparable = not incompatible
    delta = None
    lower = None
    if comparable:
        assert baseline.cpav_ratio is not None
        assert candidate.cpav_ratio is not None
        relation = candidate.cpav_ratio.compare(baseline.cpav_ratio)
        delta = candidate.cpav_ratio.subtract(baseline.cpav_ratio)
        if relation < 0:
            lower = candidate.route_id
        elif relation > 0:
            lower = baseline.route_id
    return AdoptionEconomicsComparison(
        schema=COMPARISON_SCHEMA,
        baseline_logical_id=baseline.logical_id,
        candidate_logical_id=candidate.logical_id,
        comparable=comparable,
        incompatibilities=tuple(sorted(set(incompatible))),
        baseline_cpav_ratio=baseline.cpav_ratio,
        candidate_cpav_ratio=candidate.cpav_ratio,
        cpav_delta_ratio=delta,
        lower_cpav_route_id=lower,
        baseline_friction_receipt_ref=baseline.friction_receipt_ref,
        candidate_friction_receipt_ref=candidate.friction_receipt_ref,
        overall_route_preference_claimed=False,
    )
