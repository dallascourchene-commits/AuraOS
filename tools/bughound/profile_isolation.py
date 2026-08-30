"""BugHound vNext profile-isolation conformance contract.

This module is intentionally target-agnostic and lives in AuraOS only as a
noncanonical conformance substrate until BugHound has its own repository owner.
It models the vNext separation between the BOUNTY and AURAOS_INTERNAL profiles.

D0 only. It grants no network, credential, disclosure, payout, repository,
submission, or external-effect authority by itself.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Iterable

SCHEMA = "ProfileIsolationContractV1"
PROFILE_BOUNTY = "BOUNTY"
PROFILE_AURAOS = "AURAOS_INTERNAL"
NETWORK_OFF = "OFF"
NETWORK_ALLOWLIST = "ALLOWLIST"

# These classes are profile-exclusive consequence namespaces. Shared local
# analysis/reproduction capabilities are intentionally not included here.
_BOUNTY_ONLY_EFFECTS = frozenset(
    {
        "BOUNTY_LIVE_NETWORK_TEST",
        "BOUNTY_SUBMISSION",
        "BOUNTY_PAYOUT_CLAIM",
    }
)
_AURAOS_ONLY_EFFECTS = frozenset(
    {
        "AURAOS_REPO_MUTATION",
        "AURAOS_ISSUE_OR_PR_HANDOFF",
        "AURAOS_REVIEW_REQUEST",
    }
)
_SHARED_EFFECTS = frozenset({"LOCAL_ANALYSIS", "LOCAL_REPRODUCTION"})
_ALLOWED_PROFILES = frozenset({PROFILE_BOUNTY, PROFILE_AURAOS})


class ProfileIsolationError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProfileIsolationError("NONCANONICAL_PROFILE_STATE") from exc


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _nonempty(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProfileIsolationError(code)
    return value.strip()


def _string_set(values: Iterable[str], code: str) -> frozenset[str]:
    try:
        out = frozenset(values)
    except TypeError as exc:
        raise ProfileIsolationError(code) from exc
    if any(not isinstance(v, str) or not v for v in out):
        raise ProfileIsolationError(code)
    return out


@dataclass(frozen=True)
class BugHoundProfileEnvelopeV1:
    profile_id: str
    target_owner: str
    target_ref: str
    target_generation: str
    source_currentness_ref: str
    scope_policy_ref: str
    allowed_effect_classes: tuple[str, ...]
    forbidden_effect_classes: tuple[str, ...]
    network_policy: str
    network_allowlist: tuple[str, ...]
    credential_aliases: tuple[str, ...]
    disclosure_policy_ref: str
    money_policy_ref: str | None
    result_sink_ref: str
    reusable_memory_policy_ref: str
    invalidators: tuple[str, ...] = ()
    authority: bool = False
    schema: str = "BugHoundProfileEnvelopeV1"

    @property
    def envelope_digest(self) -> str:
        return _digest("AURA_BUGHOUND_PROFILE_ENVELOPE_V1", asdict(self))


@dataclass(frozen=True)
class CompiledProfilePolicyV1:
    profile_id: str
    target_owner: str
    target_ref: str
    target_generation: str
    source_currentness_ref: str
    scope_policy_ref: str
    allowed_effect_classes: tuple[str, ...]
    forbidden_effect_classes: tuple[str, ...]
    network_policy: str
    network_allowlist: tuple[str, ...]
    credential_aliases: tuple[str, ...]
    disclosure_policy_ref: str
    money_policy_ref: str | None
    result_sink_ref: str
    reusable_memory_policy_ref: str
    source_envelope_digest: str
    cross_profile_casts_forbidden: bool = True
    authority: bool = False
    external_effect: bool = False
    schema: str = SCHEMA

    @property
    def policy_digest(self) -> str:
        return _digest("AURA_BUGHOUND_COMPILED_PROFILE_POLICY_V1", asdict(self))


@dataclass(frozen=True)
class BugHypothesisProfileBindingV1:
    profile_id: str
    target_ref: str
    target_generation: str
    hypothesis_id: str
    effect_ceiling: tuple[str, ...]
    schema: str = "BugHypothesisProfileBindingV1"


@dataclass(frozen=True)
class BugHoundToolAdapterPolicyV1:
    adapter_id: str
    supported_profiles: tuple[str, ...]
    required_effect_classes: tuple[str, ...] = ()
    network_required: bool = False
    credential_aliases_required: tuple[str, ...] = ()
    authority: bool = False
    schema: str = "BugHoundToolAdapterPolicyV1"


@dataclass(frozen=True)
class BountyLiveEffectGrantV1:
    profile_id: str
    target_ref: str
    target_generation: str
    scope_policy_ref: str
    program_policy_currentness_ref: str
    effect_class: str
    network_origin: str
    credential_aliases: tuple[str, ...] = ()
    human_authorization_ref: str | None = None
    authority: bool = True
    schema: str = "BountyLiveEffectGrantV1"

    @property
    def grant_digest(self) -> str:
        return _digest("AURA_BUGHOUND_BOUNTY_LIVE_EFFECT_GRANT_V1", asdict(self))


@dataclass(frozen=True)
class SanitizedPatternReceiptV1:
    source_profile_id: str
    reusable_memory_policy_ref: str
    sanitizer_generation: str
    reviewer_ref: str
    removed_classes: tuple[str, ...]
    retained_pattern_ref: str
    target_specific_material_present: bool
    credentials_or_tokens_present: bool
    private_endpoint_present: bool
    undisclosed_exploit_material_present: bool
    pii_or_third_party_data_present: bool
    private_report_identifier_present: bool
    authority: bool = False
    schema: str = "SanitizedPatternReceiptV1"

    @property
    def receipt_digest(self) -> str:
        return _digest("AURA_BUGHOUND_SANITIZED_PATTERN_V1", asdict(self))


def compile_profile(envelope: BugHoundProfileEnvelopeV1) -> CompiledProfilePolicyV1:
    if not isinstance(envelope, BugHoundProfileEnvelopeV1):
        raise ProfileIsolationError("PROFILE_ENVELOPE_REQUIRED")
    if envelope.schema != "BugHoundProfileEnvelopeV1":
        raise ProfileIsolationError("PROFILE_ENVELOPE_SCHEMA_MISMATCH")
    profile = _nonempty(envelope.profile_id, "PROFILE_ID_REQUIRED")
    if profile not in _ALLOWED_PROFILES:
        raise ProfileIsolationError("PROFILE_ID_UNSUPPORTED", profile)
    if envelope.authority:
        raise ProfileIsolationError("PROFILE_ENVELOPE_CANNOT_SELF_GRANT_AUTHORITY")

    target_owner = _nonempty(envelope.target_owner, "TARGET_OWNER_REQUIRED")
    target_ref = _nonempty(envelope.target_ref, "TARGET_REF_REQUIRED")
    target_generation = _nonempty(envelope.target_generation, "TARGET_GENERATION_REQUIRED")
    currentness = _nonempty(envelope.source_currentness_ref, "SOURCE_CURRENTNESS_REF_REQUIRED")
    scope = _nonempty(envelope.scope_policy_ref, "SCOPE_POLICY_REF_REQUIRED")
    disclosure = _nonempty(envelope.disclosure_policy_ref, "DISCLOSURE_POLICY_REF_REQUIRED")
    result_sink = _nonempty(envelope.result_sink_ref, "RESULT_SINK_REF_REQUIRED")
    memory_policy = _nonempty(envelope.reusable_memory_policy_ref, "MEMORY_POLICY_REF_REQUIRED")

    allowed = _string_set(envelope.allowed_effect_classes, "ALLOWED_EFFECT_CLASSES_INVALID")
    forbidden = _string_set(envelope.forbidden_effect_classes, "FORBIDDEN_EFFECT_CLASSES_INVALID")
    if allowed & forbidden:
        raise ProfileIsolationError("EFFECT_CLASS_BOTH_ALLOWED_AND_FORBIDDEN")

    if profile == PROFILE_BOUNTY:
        if not envelope.money_policy_ref:
            raise ProfileIsolationError("BOUNTY_MONEY_POLICY_REQUIRED")
        _nonempty(envelope.money_policy_ref, "BOUNTY_MONEY_POLICY_REQUIRED")
        illegal = allowed & _AURAOS_ONLY_EFFECTS
        if illegal:
            raise ProfileIsolationError("BOUNTY_CANNOT_IMPORT_AURAOS_AUTHORITY", ",".join(sorted(illegal)))
    else:
        if envelope.money_policy_ref is not None:
            raise ProfileIsolationError("AURAOS_CANNOT_IMPORT_BOUNTY_MONEY_POLICY")
        illegal = allowed & _BOUNTY_ONLY_EFFECTS
        if illegal:
            raise ProfileIsolationError("AURAOS_CANNOT_IMPORT_BOUNTY_AUTHORITY", ",".join(sorted(illegal)))

    if envelope.network_policy not in {NETWORK_OFF, NETWORK_ALLOWLIST}:
        raise ProfileIsolationError("NETWORK_POLICY_INVALID")
    network_allowlist = _string_set(envelope.network_allowlist, "NETWORK_ALLOWLIST_INVALID")
    if envelope.network_policy == NETWORK_OFF and network_allowlist:
        raise ProfileIsolationError("NETWORK_OFF_REQUIRES_EMPTY_ALLOWLIST")
    if envelope.network_policy == NETWORK_ALLOWLIST:
        if profile != PROFILE_BOUNTY:
            raise ProfileIsolationError("AURAOS_EXTERNAL_NETWORK_PROFILE_FORBIDDEN")
        if not network_allowlist:
            raise ProfileIsolationError("NETWORK_ALLOWLIST_REQUIRED")
        if "BOUNTY_LIVE_NETWORK_TEST" not in allowed:
            raise ProfileIsolationError("NETWORK_ALLOWLIST_REQUIRES_LIVE_EFFECT_CLASS")

    credential_aliases = _string_set(envelope.credential_aliases, "CREDENTIAL_ALIASES_INVALID")
    if profile == PROFILE_AURAOS and credential_aliases:
        raise ProfileIsolationError("AURAOS_CANNOT_IMPORT_BOUNTY_CREDENTIAL_STATE")

    return CompiledProfilePolicyV1(
        profile_id=profile,
        target_owner=target_owner,
        target_ref=target_ref,
        target_generation=target_generation,
        source_currentness_ref=currentness,
        scope_policy_ref=scope,
        allowed_effect_classes=tuple(sorted(allowed)),
        forbidden_effect_classes=tuple(sorted(forbidden)),
        network_policy=envelope.network_policy,
        network_allowlist=tuple(sorted(network_allowlist)),
        credential_aliases=tuple(sorted(credential_aliases)),
        disclosure_policy_ref=disclosure,
        money_policy_ref=envelope.money_policy_ref,
        result_sink_ref=result_sink,
        reusable_memory_policy_ref=memory_policy,
        source_envelope_digest=envelope.envelope_digest,
    )


def admit_hypothesis(
    policy: CompiledProfilePolicyV1,
    hypothesis: BugHypothesisProfileBindingV1,
) -> str:
    if hypothesis.profile_id != policy.profile_id:
        raise ProfileIsolationError("HYPOTHESIS_PROFILE_CAST_FORBIDDEN")
    if hypothesis.target_ref != policy.target_ref or hypothesis.target_generation != policy.target_generation:
        raise ProfileIsolationError("HYPOTHESIS_TARGET_BINDING_MISMATCH")
    ceiling = _string_set(hypothesis.effect_ceiling, "HYPOTHESIS_EFFECT_CEILING_INVALID")
    if not ceiling <= set(policy.allowed_effect_classes):
        raise ProfileIsolationError("HYPOTHESIS_EFFECT_CEILING_WIDENS_PROFILE")
    if ceiling & set(policy.forbidden_effect_classes):
        raise ProfileIsolationError("HYPOTHESIS_EFFECT_CEILING_FORBIDDEN")
    return _digest(
        "AURA_BUGHOUND_PROFILE_BOUND_HYPOTHESIS_V1",
        {"policy": policy.policy_digest, "hypothesis": asdict(hypothesis)},
    )


def admit_tool(policy: CompiledProfilePolicyV1, tool: BugHoundToolAdapterPolicyV1) -> str:
    supported = _string_set(tool.supported_profiles, "TOOL_SUPPORTED_PROFILES_INVALID")
    if policy.profile_id not in supported:
        raise ProfileIsolationError("TOOL_PROFILE_UNSUPPORTED")
    if tool.authority:
        raise ProfileIsolationError("TOOL_CAPABILITY_CANNOT_SELF_GRANT_AUTHORITY")
    required_effects = _string_set(tool.required_effect_classes, "TOOL_EFFECT_CLASSES_INVALID")
    if not required_effects <= set(policy.allowed_effect_classes):
        raise ProfileIsolationError("TOOL_EFFECT_REQUIREMENT_EXCEEDS_PROFILE")
    if tool.network_required and policy.network_policy != NETWORK_ALLOWLIST:
        raise ProfileIsolationError("TOOL_NETWORK_NOT_ADMITTED")
    required_credentials = _string_set(tool.credential_aliases_required, "TOOL_CREDENTIAL_ALIASES_INVALID")
    if not required_credentials <= set(policy.credential_aliases):
        raise ProfileIsolationError("TOOL_CREDENTIALS_NOT_ADMITTED")
    return _digest(
        "AURA_BUGHOUND_PROFILE_BOUND_TOOL_V1",
        {"policy": policy.policy_digest, "tool": asdict(tool)},
    )


def admit_bounty_live_effect(
    policy: CompiledProfilePolicyV1,
    grant: BountyLiveEffectGrantV1,
) -> str:
    if policy.profile_id != PROFILE_BOUNTY or grant.profile_id != PROFILE_BOUNTY:
        raise ProfileIsolationError("BOUNTY_LIVE_EFFECT_PROFILE_REQUIRED")
    if not grant.authority:
        raise ProfileIsolationError("BOUNTY_LIVE_EFFECT_GRANT_NOT_AUTHORITATIVE")
    if grant.target_ref != policy.target_ref or grant.target_generation != policy.target_generation:
        raise ProfileIsolationError("BOUNTY_LIVE_EFFECT_TARGET_MISMATCH")
    if grant.scope_policy_ref != policy.scope_policy_ref:
        raise ProfileIsolationError("BOUNTY_LIVE_EFFECT_SCOPE_MISMATCH")
    _nonempty(grant.program_policy_currentness_ref, "BOUNTY_POLICY_CURRENTNESS_REQUIRED")
    if grant.effect_class not in set(policy.allowed_effect_classes):
        raise ProfileIsolationError("BOUNTY_LIVE_EFFECT_CLASS_NOT_ALLOWED")
    if grant.effect_class in set(policy.forbidden_effect_classes):
        raise ProfileIsolationError("BOUNTY_LIVE_EFFECT_CLASS_FORBIDDEN")
    if policy.network_policy != NETWORK_ALLOWLIST:
        raise ProfileIsolationError("BOUNTY_LIVE_NETWORK_NOT_COMPILED")
    if grant.network_origin not in set(policy.network_allowlist):
        raise ProfileIsolationError("BOUNTY_LIVE_NETWORK_ORIGIN_NOT_ALLOWED")
    grant_credentials = _string_set(grant.credential_aliases, "BOUNTY_GRANT_CREDENTIALS_INVALID")
    if not grant_credentials <= set(policy.credential_aliases):
        raise ProfileIsolationError("BOUNTY_GRANT_CREDENTIALS_NOT_ALLOWED")
    return _digest(
        "AURA_BUGHOUND_PROFILE_BOUND_LIVE_EFFECT_V1",
        {"policy": policy.policy_digest, "grant": asdict(grant)},
    )


def admit_sanitized_pattern(
    policy: CompiledProfilePolicyV1,
    receipt: SanitizedPatternReceiptV1,
    *,
    destination_profile_id: str,
) -> str:
    if receipt.source_profile_id != policy.profile_id:
        raise ProfileIsolationError("SANITIZED_PATTERN_SOURCE_PROFILE_MISMATCH")
    if destination_profile_id not in _ALLOWED_PROFILES:
        raise ProfileIsolationError("SANITIZED_PATTERN_DESTINATION_PROFILE_INVALID")
    if receipt.reusable_memory_policy_ref != policy.reusable_memory_policy_ref:
        raise ProfileIsolationError("SANITIZED_PATTERN_MEMORY_POLICY_MISMATCH")
    if receipt.authority:
        raise ProfileIsolationError("SANITIZED_PATTERN_CANNOT_CARRY_AUTHORITY")
    _nonempty(receipt.sanitizer_generation, "SANITIZER_GENERATION_REQUIRED")
    _nonempty(receipt.reviewer_ref, "SANITIZER_REVIEWER_REQUIRED")
    _nonempty(receipt.retained_pattern_ref, "SANITIZED_PATTERN_REF_REQUIRED")
    sensitive = {
        "target_specific_material": receipt.target_specific_material_present,
        "credentials_or_tokens": receipt.credentials_or_tokens_present,
        "private_endpoint": receipt.private_endpoint_present,
        "undisclosed_exploit_material": receipt.undisclosed_exploit_material_present,
        "pii_or_third_party_data": receipt.pii_or_third_party_data_present,
        "private_report_identifier": receipt.private_report_identifier_present,
    }
    leaking = sorted(key for key, present in sensitive.items() if present)
    if leaking:
        raise ProfileIsolationError("SANITIZED_PATTERN_STILL_CONTAINS_PRIVATE_STATE", ",".join(leaking))
    removed = _string_set(receipt.removed_classes, "SANITIZED_PATTERN_REMOVED_CLASSES_INVALID")
    required_removed = frozenset(sensitive)
    if not required_removed <= removed:
        raise ProfileIsolationError("SANITIZED_PATTERN_REMOVAL_COVERAGE_INCOMPLETE")
    # Cross-profile reuse is allowed only for this authority-free, fully
    # sanitized abstraction. The source profile remains bound in the receipt.
    return _digest(
        "AURA_BUGHOUND_PROFILE_SAFE_MEMORY_EXPORT_V1",
        {
            "policy": policy.policy_digest,
            "receipt": asdict(receipt),
            "destination_profile_id": destination_profile_id,
        },
    )
