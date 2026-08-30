"""ZF-04 canonical distribution trust -> ZF-05A ShareCapsule trust bridge.

D0 evidence composition only. This bridge prevents a caller-supplied textual
`TRUST_READY` on ShareCapsule.BindingEvidence from satisfying share launch by
itself. The distribution binding used by compile_share_launch() is overwritten
with a projection derived from the canonical ZF-04 manifest + admission receipt.

No fetching, signature verification, installation, publication, network action,
recipient tracking, payment, provider call, or adoption-success claim occurs here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Callable, Mapping

from tools.aura_adopt.share_capsule import (
    BindingEvidence,
    RouteEvidence,
    ShareCapsule,
    compile_share_launch,
)

MANIFEST_SCHEMA = "TrustedDistributionManifestV1"
RECEIPT_SCHEMA = "DistributionAdmissionReceiptV1"
BRIDGE_SCHEMA = "ShareDistributionTrustProjectionV1"


class ShareDistributionTrustError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ShareDistributionTrustError("NONCANONICAL_TRUST_STATE") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ShareDistributionTrustError(code)
    return value.strip()


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ShareDistributionTrustError(code)
    return value


def _strict_false(row: Mapping[str, Any], fields: tuple[str, ...], code: str) -> None:
    for field in fields:
        if row.get(field) is not False:
            raise ShareDistributionTrustError(code, field)


@dataclass(frozen=True)
class ShareDistributionTrustProjectionV1:
    manifest_digest: str
    artifact_id: str
    distribution_ref: str
    distribution_digest: str
    source_generation: str
    canonical_disposition: str
    canonical_blockers: tuple[str, ...]
    binding_evidence: BindingEvidence
    schema: str = BRIDGE_SCHEMA
    install_authorized: bool = False
    execution_authorized: bool = False
    publication_authorized: bool = False
    network_fetch_authorized: bool = False
    payment_authorized: bool = False
    telemetry_authorized: bool = False
    recipient_tracking_authorized: bool = False
    provider_call_authorized: bool = False
    adoption_success_proven: bool = False
    projection_digest: str = ""

    def __post_init__(self) -> None:
        if self.schema != BRIDGE_SCHEMA:
            raise ShareDistributionTrustError("PROJECTION_SCHEMA_MISMATCH")
        logical = asdict(self)
        logical.pop("projection_digest", None)
        expected = _digest(logical)
        supplied = str(self.projection_digest or "").strip()
        if supplied and supplied != expected:
            raise ShareDistributionTrustError("PROJECTION_DIGEST_MISMATCH")
        object.__setattr__(self, "projection_digest", expected)


def validate_manifest_view(manifest_view: Mapping[str, Any]) -> tuple[Mapping[str, Any], str]:
    view = _mapping(manifest_view, "DISTRIBUTION_MANIFEST_VIEW_REQUIRED")
    supplied = _text(view.get("manifest_digest"), "DISTRIBUTION_MANIFEST_DIGEST_REQUIRED")
    logical = dict(view)
    logical.pop("manifest_digest", None)
    if logical.get("schema") != MANIFEST_SCHEMA:
        raise ShareDistributionTrustError("DISTRIBUTION_MANIFEST_SCHEMA_MISMATCH")
    if _digest(logical) != supplied:
        raise ShareDistributionTrustError("DISTRIBUTION_MANIFEST_DIGEST_MISMATCH")
    _strict_false(
        logical,
        (
            "telemetry_default_enabled",
            "content_upload_default_enabled",
            "network_code_fetch_authorized",
            "public_distribution_authorized",
        ),
        "DISTRIBUTION_MANIFEST_AUTHORITY_WIDENING",
    )
    artifacts = logical.get("artifacts")
    if not isinstance(artifacts, (list, tuple)) or not artifacts:
        raise ShareDistributionTrustError("DISTRIBUTION_ARTIFACTS_REQUIRED")
    return logical, supplied


def _resolve_target_artifact(capsule: ShareCapsule, logical_manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    matches = []
    for raw in logical_manifest["artifacts"]:
        if not isinstance(raw, Mapping):
            raise ShareDistributionTrustError("DISTRIBUTION_ARTIFACT_INVALID")
        if raw.get("source_ref") == capsule.distribution.ref:
            matches.append(raw)
    if len(matches) != 1:
        raise ShareDistributionTrustError("SHARE_DISTRIBUTION_ARTIFACT_NOT_UNIQUE")
    artifact = matches[0]
    if artifact.get("content_sha256") != capsule.distribution.digest:
        raise ShareDistributionTrustError("SHARE_DISTRIBUTION_DIGEST_MISMATCH")
    if artifact.get("source_generation") != capsule.distribution.source_generation:
        raise ShareDistributionTrustError("SHARE_DISTRIBUTION_GENERATION_MISMATCH")
    if artifact.get("immutable_source") is not True:
        raise ShareDistributionTrustError("SHARE_DISTRIBUTION_SOURCE_NOT_IMMUTABLE")
    return artifact


def _canonical_receipt(
    *,
    resolver: Callable[[str], Mapping[str, Any]] | None,
    manifest_digest: str,
    route_id: str,
) -> Mapping[str, Any]:
    if resolver is None or not callable(resolver):
        raise ShareDistributionTrustError("CANONICAL_DISTRIBUTION_RECEIPT_RESOLVER_REQUIRED")
    receipt = _mapping(
        resolver(manifest_digest), "CANONICAL_DISTRIBUTION_RECEIPT_MAPPING_REQUIRED"
    )
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise ShareDistributionTrustError("CANONICAL_DISTRIBUTION_RECEIPT_SCHEMA_MISMATCH")
    if receipt.get("manifest_digest") != manifest_digest:
        raise ShareDistributionTrustError("CANONICAL_DISTRIBUTION_RECEIPT_MANIFEST_MISMATCH")
    if receipt.get("route_id") != route_id:
        raise ShareDistributionTrustError("CANONICAL_DISTRIBUTION_RECEIPT_ROUTE_MISMATCH")
    _strict_false(
        receipt,
        (
            "effect_authorized",
            "execution_authorized",
            "execution_proven",
            "install_performed",
            "update_performed",
            "network_fetch_performed",
            "public_distribution_performed",
        ),
        "CANONICAL_DISTRIBUTION_RECEIPT_AUTHORITY_WIDENING",
    )
    blockers = receipt.get("blockers")
    verified = receipt.get("verified_artifact_ids")
    if not isinstance(blockers, (list, tuple)) or any(not isinstance(x, str) for x in blockers):
        raise ShareDistributionTrustError("CANONICAL_DISTRIBUTION_BLOCKERS_INVALID")
    if not isinstance(verified, (list, tuple)) or any(not isinstance(x, str) for x in verified):
        raise ShareDistributionTrustError("CANONICAL_VERIFIED_ARTIFACTS_INVALID")
    for field in ("integrity_ready", "signature_ready", "currentness_ready"):
        if not isinstance(receipt.get(field), bool):
            raise ShareDistributionTrustError("CANONICAL_DISTRIBUTION_READINESS_INVALID", field)
    return receipt


def project_canonical_distribution_trust(
    *,
    capsule: ShareCapsule,
    distribution_manifest_view: Mapping[str, Any],
    canonical_distribution_receipt_resolver: Callable[[str], Mapping[str, Any]] | None,
) -> ShareDistributionTrustProjectionV1:
    if not isinstance(capsule, ShareCapsule):
        raise ShareDistributionTrustError("SHARE_CAPSULE_REQUIRED")
    logical, manifest_digest = validate_manifest_view(distribution_manifest_view)
    artifact = _resolve_target_artifact(capsule, logical)
    artifact_id = _text(artifact.get("artifact_id"), "DISTRIBUTION_ARTIFACT_ID_REQUIRED")
    route_id = _text(logical.get("route_id"), "DISTRIBUTION_ROUTE_ID_REQUIRED")
    receipt = _canonical_receipt(
        resolver=canonical_distribution_receipt_resolver,
        manifest_digest=manifest_digest,
        route_id=route_id,
    )

    disposition = _text(receipt.get("disposition"), "CANONICAL_DISTRIBUTION_DISPOSITION_REQUIRED")
    blockers = tuple(receipt.get("blockers", ()))
    verified = set(receipt.get("verified_artifact_ids", ()))
    currentness_ready = receipt.get("currentness_ready") is True

    if disposition == "TRUST_READY":
        if blockers:
            raise ShareDistributionTrustError("TRUST_READY_RECEIPT_HAS_BLOCKERS")
        if not (
            receipt.get("integrity_ready") is True
            and receipt.get("signature_ready") is True
            and currentness_ready
        ):
            raise ShareDistributionTrustError("TRUST_READY_RECEIPT_NOT_FULLY_READY")
        if artifact_id not in verified:
            raise ShareDistributionTrustError("TRUST_READY_ARTIFACT_NOT_VERIFIED")
        trust_state = "TRUST_READY"
        currentness = "CURRENT"
    elif disposition == "REBASE_REQUIRED":
        trust_state = "UNKNOWN"
        currentness = "STALE"
    elif disposition in {
        "EVIDENCE_REQUIRED",
        "SIGNATURE_EVIDENCE_REQUIRED",
    }:
        trust_state = "UNKNOWN"
        currentness = "CURRENT" if currentness_ready else "UNKNOWN"
    elif disposition in {
        "INTEGRITY_MISMATCH",
        "SOURCE_NOT_IMMUTABLE",
        "POLICY_REFUSED",
        "CONSENT_REQUIRED",
    }:
        trust_state = "TRUST_BLOCKED"
        currentness = "CURRENT" if currentness_ready else "UNKNOWN"
    else:
        raise ShareDistributionTrustError("CANONICAL_DISTRIBUTION_DISPOSITION_UNSUPPORTED", disposition)

    binding = BindingEvidence(
        capsule.distribution.ref,
        capsule.distribution.digest,
        capsule.distribution.source_generation,
        currentness,
        trust_state,
    )
    return ShareDistributionTrustProjectionV1(
        manifest_digest=manifest_digest,
        artifact_id=artifact_id,
        distribution_ref=capsule.distribution.ref,
        distribution_digest=capsule.distribution.digest,
        source_generation=capsule.distribution.source_generation,
        canonical_disposition=disposition,
        canonical_blockers=blockers,
        binding_evidence=binding,
    )


def compile_share_launch_with_canonical_distribution(
    *,
    capsule: ShareCapsule,
    current_bindings: Mapping[str, BindingEvidence],
    route_evidence: RouteEvidence,
    distribution_manifest_view: Mapping[str, Any],
    canonical_distribution_receipt_resolver: Callable[[str], Mapping[str, Any]] | None,
) -> dict[str, Any]:
    if not isinstance(current_bindings, Mapping):
        raise ShareDistributionTrustError("CURRENT_BINDINGS_REQUIRED")
    projection = project_canonical_distribution_trust(
        capsule=capsule,
        distribution_manifest_view=distribution_manifest_view,
        canonical_distribution_receipt_resolver=canonical_distribution_receipt_resolver,
    )
    bindings = dict(current_bindings)
    # Critical law: caller-supplied distribution trust is not authoritative here.
    bindings[capsule.distribution.ref] = projection.binding_evidence
    plan = compile_share_launch(
        capsule,
        current_bindings=bindings,
        route_evidence=route_evidence,
    )
    return {
        "schema": "ShareLaunchWithCanonicalDistributionV1",
        "share_launch_plan": plan,
        "canonical_distribution_projection_digest": projection.projection_digest,
        "canonical_distribution_disposition": projection.canonical_disposition,
        "canonical_distribution_trust_state": projection.binding_evidence.trust_state,
        "canonical_distribution_currentness": projection.binding_evidence.currentness,
        "install_authorized": False,
        "publication_authorized": False,
        "network_fetch_authorized": False,
        "payment_authorized": False,
        "telemetry_authorized": False,
        "recipient_tracking_authorized": False,
        "provider_call_authorized": False,
        "adoption_success_proven": False,
    }
