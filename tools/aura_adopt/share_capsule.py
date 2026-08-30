"""AURA-ADOPT-001 ZF-05A: portable, zero-authority share/referral capsule."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA = "ShareCapsuleV1"
LAUNCH_SCHEMA = "ShareLaunchPlanV1"
IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,191}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
CURRENTNESS = frozenset({"CURRENT", "STALE", "UNKNOWN"})
TRUST_STATES = frozenset({"TRUST_READY", "TRUST_BLOCKED", "UNKNOWN", "NOT_APPLICABLE"})
ROUTE_STATES = frozenset({"AVAILABLE", "UNAVAILABLE", "UNKNOWN"})
SURFACES = frozenset({"ZERO_INSTALL_WEB_PWA", "NATIVE_ANDROID_APK", "DEV_CLI_GITHUB"})
MAX_REFERRAL_HOPS = 16

FORBIDDEN_KEYS = frozenset({
    "api_key", "apikey", "credential", "credentials", "secret", "token",
    "access_token", "refresh_token", "password", "private_key",
    "provider_url", "provider_endpoint", "endpoint", "download_url", "install_url",
    "shell", "shell_command", "command", "exec", "executable", "script", "javascript",
    "email", "email_address", "phone", "phone_number", "device_id", "account_id",
    "session_id", "ip", "ip_address", "advertising_id", "gaid", "idfa",
    "payout", "payment", "commission", "revenue_share", "conversion", "adoption_success",
    "tracking_id", "analytics_id", "cookie_id",
})


class ShareCapsuleError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _require_ident(name: str, value: Any) -> str:
    if not isinstance(value, str) or not IDENT.fullmatch(value):
        raise ShareCapsuleError("INVALID_IDENTIFIER", name)
    if value.startswith(("http://", "https://")):
        raise ShareCapsuleError("MUTABLE_OR_REMOTE_URL_FORBIDDEN", name)
    return value


def _require_sha(name: str, value: Any) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise ShareCapsuleError("INVALID_SHA256", name)
    return value


def _scan_safe_data(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ShareCapsuleError("NONSTRING_KEY_FORBIDDEN", path)
            if key.casefold() in FORBIDDEN_KEYS:
                raise ShareCapsuleError("FORBIDDEN_SHARE_FIELD", f"{path}.{key}")
            _scan_safe_data(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for i, child in enumerate(value):
            _scan_safe_data(child, f"{path}[{i}]")
    elif value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and (
            value != value or value in (float("inf"), float("-inf"))
        ):
            raise ShareCapsuleError("NONFINITE_NUMBER_FORBIDDEN", path)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            raise ShareCapsuleError("REMOTE_URL_FORBIDDEN", path)
    else:
        raise ShareCapsuleError("UNSUPPORTED_SHARE_VALUE", path)


def _strict_keys(raw: Mapping[str, Any], allowed: set[str], name: str) -> None:
    extra = sorted(set(raw) - allowed)
    if extra:
        raise ShareCapsuleError("UNKNOWN_FIELDS", f"{name}:{','.join(extra)}")


@dataclass(frozen=True)
class EvidenceRef:
    ref: str
    digest: str
    source_generation: str
    currentness: str = "UNKNOWN"

    def __post_init__(self) -> None:
        _require_ident("ref", self.ref)
        _require_sha("digest", self.digest)
        _require_ident("source_generation", self.source_generation)
        if self.currentness not in CURRENTNESS:
            raise ShareCapsuleError("INVALID_CURRENTNESS", self.currentness)


@dataclass(frozen=True)
class Attribution:
    contributor_ref: str
    role: str

    def __post_init__(self) -> None:
        _require_ident("contributor_ref", self.contributor_ref)
        _require_ident("role", self.role)


@dataclass(frozen=True)
class ReferralHop:
    hop_index: int
    referrer_ref: str
    parent_capsule_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.hop_index, int) or self.hop_index < 1:
            raise ShareCapsuleError("INVALID_HOP_INDEX")
        _require_ident("referrer_ref", self.referrer_ref)
        _require_sha("parent_capsule_digest", self.parent_capsule_digest)


@dataclass(frozen=True)
class BindingEvidence:
    ref: str
    digest: str
    source_generation: str
    currentness: str
    trust_state: str = "NOT_APPLICABLE"

    def __post_init__(self) -> None:
        _require_ident("binding.ref", self.ref)
        _require_sha("binding.digest", self.digest)
        _require_ident("binding.source_generation", self.source_generation)
        if self.currentness not in CURRENTNESS:
            raise ShareCapsuleError("INVALID_CURRENTNESS", self.currentness)
        if self.trust_state not in TRUST_STATES:
            raise ShareCapsuleError("INVALID_TRUST_STATE", self.trust_state)


@dataclass(frozen=True)
class RouteEvidence:
    surface: str
    availability: str
    next_surface: str | None = None

    def __post_init__(self) -> None:
        if self.surface not in SURFACES:
            raise ShareCapsuleError("INVALID_ENTRY_SURFACE", self.surface)
        if self.availability not in ROUTE_STATES:
            raise ShareCapsuleError("INVALID_ROUTE_STATE", self.availability)
        if self.next_surface is not None and self.next_surface not in SURFACES:
            raise ShareCapsuleError("INVALID_NEXT_SURFACE", self.next_surface)


@dataclass(frozen=True)
class ShareCapsule:
    capsule_id: str
    version: str
    creator_ref: str
    purpose: str
    source: EvidenceRef
    recipe: EvidenceRef
    accepted_output: EvidenceRef
    distribution: EvidenceRef
    entry_surface_preference: str
    attribution: tuple[Attribution, ...]
    referrals: tuple[ReferralHop, ...] = ()
    parent_capsule_digests: tuple[str, ...] = ()
    constraints: Mapping[str, Any] | None = None
    reopen_conditions: tuple[str, ...] = ()
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise ShareCapsuleError("SCHEMA_MISMATCH")
        _require_ident("capsule_id", self.capsule_id)
        _require_ident("version", self.version)
        _require_ident("creator_ref", self.creator_ref)
        if not isinstance(self.purpose, str) or not self.purpose.strip():
            raise ShareCapsuleError("PURPOSE_REQUIRED")
        if self.entry_surface_preference not in SURFACES:
            raise ShareCapsuleError("INVALID_ENTRY_SURFACE", self.entry_surface_preference)
        if len(self.referrals) > MAX_REFERRAL_HOPS:
            raise ShareCapsuleError("REFERRAL_DEPTH_EXCEEDED")
        for i, hop in enumerate(self.referrals, start=1):
            if hop.hop_index != i:
                raise ShareCapsuleError("REFERRAL_SEQUENCE_INVALID")
        if len({hop.referrer_ref for hop in self.referrals}) != len(self.referrals):
            raise ShareCapsuleError("DUPLICATE_REFERRER_FORBIDDEN")
        if any(hop.referrer_ref == self.creator_ref for hop in self.referrals):
            raise ShareCapsuleError("SELF_REFERRAL_FORBIDDEN")
        for digest in self.parent_capsule_digests:
            _require_sha("parent_capsule_digest", digest)
        if len(set(self.parent_capsule_digests)) != len(self.parent_capsule_digests):
            raise ShareCapsuleError("DUPLICATE_PARENT_DIGEST")
        if not any(
            a.contributor_ref == self.creator_ref
            and a.role in {"ORIGINAL_CREATOR", "ORIGINAL_PUBLISHER"}
            for a in self.attribution
        ):
            raise ShareCapsuleError("ORIGINAL_CREATOR_ATTRIBUTION_REQUIRED")
        object.__setattr__(self, "constraints", dict(self.constraints or {}))
        _scan_safe_data(self.constraints, "$.constraints")
        for condition in self.reopen_conditions:
            if not isinstance(condition, str) or not condition.strip():
                raise ShareCapsuleError("INVALID_REOPEN_CONDITION")

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "capsule_id": self.capsule_id,
            "version": self.version,
            "creator_ref": self.creator_ref,
            "purpose": self.purpose.strip(),
            "source": asdict(self.source),
            "recipe": asdict(self.recipe),
            "accepted_output": asdict(self.accepted_output),
            "distribution": asdict(self.distribution),
            "entry_surface_preference": self.entry_surface_preference,
            "attribution": [
                asdict(a)
                for a in sorted(self.attribution, key=lambda x: (x.contributor_ref, x.role))
            ],
            "referrals": [asdict(h) for h in self.referrals],
            "parent_capsule_digests": list(self.parent_capsule_digests),
            "constraints": self.constraints,
            "reopen_conditions": sorted(set(self.reopen_conditions)),
        }

    @property
    def digest(self) -> str:
        return _digest(self.canonical_payload())

    def export_json(self) -> str:
        return _canonical(self.canonical_payload()).decode("utf-8")


def _evidence_ref(raw: Mapping[str, Any], name: str) -> EvidenceRef:
    _strict_keys(raw, {"ref", "digest", "source_generation", "currentness"}, name)
    return EvidenceRef(
        ref=raw.get("ref"),
        digest=raw.get("digest"),
        source_generation=raw.get("source_generation"),
        currentness=raw.get("currentness", "UNKNOWN"),
    )


def _attribution(raw: Mapping[str, Any]) -> Attribution:
    _strict_keys(raw, {"contributor_ref", "role"}, "attribution")
    return Attribution(raw.get("contributor_ref"), raw.get("role"))


def _referral(raw: Mapping[str, Any]) -> ReferralHop:
    _strict_keys(raw, {"hop_index", "referrer_ref", "parent_capsule_digest"}, "referral")
    return ReferralHop(
        hop_index=raw.get("hop_index"),
        referrer_ref=raw.get("referrer_ref"),
        parent_capsule_digest=raw.get("parent_capsule_digest"),
    )


def import_share_capsule_json(text: str) -> ShareCapsule:
    try:
        raw = json.loads(text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ShareCapsuleError("SHARE_JSON_INVALID") from exc
    if not isinstance(raw, Mapping):
        raise ShareCapsuleError("SHARE_OBJECT_REQUIRED")
    allowed = {
        "schema", "capsule_id", "version", "creator_ref", "purpose", "source",
        "recipe", "accepted_output", "distribution", "entry_surface_preference",
        "attribution", "referrals", "parent_capsule_digests", "constraints",
        "reopen_conditions",
    }
    _strict_keys(raw, allowed, "share_capsule")
    if raw.get("schema") != SCHEMA:
        raise ShareCapsuleError("SCHEMA_MISMATCH")
    for key in ("source", "recipe", "accepted_output", "distribution", "constraints"):
        if not isinstance(raw.get(key, {}), Mapping):
            raise ShareCapsuleError("INVALID_MAPPING", key)
    for key in ("attribution", "referrals", "parent_capsule_digests", "reopen_conditions"):
        value = raw.get(key, [])
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            raise ShareCapsuleError("INVALID_SEQUENCE", key)
    return ShareCapsule(
        capsule_id=raw.get("capsule_id"),
        version=raw.get("version"),
        creator_ref=raw.get("creator_ref"),
        purpose=raw.get("purpose"),
        source=_evidence_ref(raw["source"], "source"),
        recipe=_evidence_ref(raw["recipe"], "recipe"),
        accepted_output=_evidence_ref(raw["accepted_output"], "accepted_output"),
        distribution=_evidence_ref(raw["distribution"], "distribution"),
        entry_surface_preference=raw.get("entry_surface_preference"),
        attribution=tuple(_attribution(x) for x in raw.get("attribution", [])),
        referrals=tuple(_referral(x) for x in raw.get("referrals", [])),
        parent_capsule_digests=tuple(raw.get("parent_capsule_digests", [])),
        constraints=dict(raw.get("constraints", {})),
        reopen_conditions=tuple(raw.get("reopen_conditions", [])),
    )


def refer_capsule(
    parent: ShareCapsule,
    *,
    capsule_id: str,
    version: str,
    referrer_ref: str,
) -> ShareCapsule:
    _require_ident("referrer_ref", referrer_ref)
    if referrer_ref == parent.creator_ref:
        raise ShareCapsuleError("SELF_REFERRAL_FORBIDDEN")
    if any(h.referrer_ref == referrer_ref for h in parent.referrals):
        raise ShareCapsuleError("DUPLICATE_REFERRER_FORBIDDEN")
    if len(parent.referrals) >= MAX_REFERRAL_HOPS:
        raise ShareCapsuleError("REFERRAL_DEPTH_EXCEEDED")
    hop = ReferralHop(len(parent.referrals) + 1, referrer_ref, parent.digest)
    attribution = tuple(parent.attribution) + (Attribution(referrer_ref, "REFERRER"),)
    return ShareCapsule(
        capsule_id=capsule_id,
        version=version,
        creator_ref=parent.creator_ref,
        purpose=parent.purpose,
        source=parent.source,
        recipe=parent.recipe,
        accepted_output=parent.accepted_output,
        distribution=parent.distribution,
        entry_surface_preference=parent.entry_surface_preference,
        attribution=attribution,
        referrals=tuple(parent.referrals) + (hop,),
        parent_capsule_digests=tuple(parent.parent_capsule_digests) + (parent.digest,),
        constraints=parent.constraints,
        reopen_conditions=parent.reopen_conditions,
    )


def _binding_blockers(bound: EvidenceRef, observed: BindingEvidence | None) -> list[str]:
    if observed is None:
        return [f"MISSING_BINDING:{bound.ref}"]
    blockers: list[str] = []
    if observed.ref != bound.ref:
        blockers.append(f"BINDING_REF_MISMATCH:{bound.ref}")
    if observed.digest != bound.digest:
        blockers.append(f"BINDING_DIGEST_MISMATCH:{bound.ref}")
    if observed.source_generation != bound.source_generation:
        blockers.append(f"BINDING_GENERATION_MISMATCH:{bound.ref}")
    if observed.currentness != "CURRENT":
        blockers.append(f"BINDING_NOT_CURRENT:{bound.ref}:{observed.currentness}")
    return blockers


def compile_share_launch(
    capsule: ShareCapsule,
    *,
    current_bindings: Mapping[str, BindingEvidence],
    route_evidence: RouteEvidence,
) -> dict[str, Any]:
    if not isinstance(current_bindings, Mapping):
        raise ShareCapsuleError("CURRENT_BINDINGS_REQUIRED")
    blockers: list[str] = []
    all_refs = (capsule.source, capsule.recipe, capsule.accepted_output, capsule.distribution)
    for bound in all_refs:
        observed = current_bindings.get(bound.ref)
        blockers.extend(_binding_blockers(bound, observed))
    dist_evidence = current_bindings.get(capsule.distribution.ref)
    if dist_evidence is None:
        blockers.append("TRUST_EVIDENCE_MISSING")
    elif dist_evidence.trust_state != "TRUST_READY":
        blockers.append(f"DISTRIBUTION_TRUST_NOT_READY:{dist_evidence.trust_state}")

    if route_evidence.surface != capsule.entry_surface_preference:
        blockers.append("ROUTE_EVIDENCE_SURFACE_MISMATCH")
    elif route_evidence.availability == "UNAVAILABLE":
        blockers.append("PREFERRED_ROUTE_UNAVAILABLE")
    elif route_evidence.availability == "UNKNOWN":
        blockers.append("PREFERRED_ROUTE_AVAILABILITY_UNKNOWN")

    if not blockers:
        status = "READY_FOR_USER_ACTION"
    elif any(
        x.startswith("PREFERRED_ROUTE") or x == "ROUTE_EVIDENCE_SURFACE_MISMATCH"
        for x in blockers
    ):
        status = "ROUTE_OR_EVIDENCE_REQUIRED"
    else:
        status = "EVIDENCE_REQUIRED"

    payload = {
        "schema": LAUNCH_SCHEMA,
        "capsule_digest": capsule.digest,
        "capsule_id": capsule.capsule_id,
        "preferred_entry_surface": capsule.entry_surface_preference,
        "next_surface": route_evidence.next_surface,
        "creator_ref": capsule.creator_ref,
        "attribution_refs": sorted({a.contributor_ref for a in capsule.attribution}),
        "referral_depth": len(capsule.referrals),
        "required_user_actions": [
            "OPEN_ENTRY_SURFACE",
            "REVIEW_PROVENANCE_AND_ATTRIBUTION",
            "CONFIRM_REPRODUCTION_INTENT",
        ],
        "blockers": blockers,
        "status": status,
        "network_fetch_authorized": False,
        "install_authorized": False,
        "execution_authorized": False,
        "execution_proven": False,
        "publication_authorized": False,
        "payment_authorized": False,
        "telemetry_authorized": False,
        "recipient_tracking_authorized": False,
        "provider_call_authorized": False,
        "adoption_success_proven": False,
    }
    payload["plan_digest"] = _digest(payload)
    return payload
