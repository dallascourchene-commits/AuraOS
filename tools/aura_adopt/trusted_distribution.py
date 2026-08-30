from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from hashlib import sha256
from typing import Optional, Tuple
import json
import re
from urllib.parse import urlparse


SCHEMA_VERSION = "TrustedDistributionManifestV1"


class ArtifactKind(str, Enum):
    WEB_BUNDLE = "WEB_BUNDLE"
    PWA_ASSET = "PWA_ASSET"
    ANDROID_APK = "ANDROID_APK"
    ARENA_RECIPE = "ARENA_RECIPE"
    TOOL_BUNDLE = "TOOL_BUNDLE"
    MODEL_BUNDLE = "MODEL_BUNDLE"


class DistributionChannel(str, Enum):
    STABLE = "STABLE"
    BETA = "BETA"
    DEV = "DEV"
    RECIPE = "RECIPE"


class Permission(str, Enum):
    LOCAL_FILE_READ = "LOCAL_FILE_READ"
    LOCAL_FILE_WRITE = "LOCAL_FILE_WRITE"
    NETWORK = "NETWORK"
    CLOUD_DRIVE = "CLOUD_DRIVE"
    CAMERA = "CAMERA"
    MICROPHONE = "MICROPHONE"
    NOTIFICATIONS = "NOTIFICATIONS"
    BACKGROUND_EXECUTION = "BACKGROUND_EXECUTION"
    CREDENTIAL_INPUT = "CREDENTIAL_INPUT"
    MODEL_DOWNLOAD = "MODEL_DOWNLOAD"


class AdmissionStatus(str, Enum):
    ADMISSIBLE = "ADMISSIBLE"
    CONSENT_REQUIRED = "CONSENT_REQUIRED"
    REBASE_REQUIRED = "REBASE_REQUIRED"
    REFUSED = "REFUSED"


@dataclass(frozen=True)
class SourceBindingV1:
    source_ref: str
    source_generation: str
    source_currentness_ref: str
    source_digest_sha256: str


@dataclass(frozen=True)
class SignerRequirementV1:
    signer_id: str
    key_id: str
    key_generation: str
    algorithm: str = "ED25519"


@dataclass(frozen=True)
class ArtifactDescriptorV1:
    artifact_id: str
    version: str
    kind: ArtifactKind
    sha256_hex: str
    size_bytes: int
    origin_uri: str
    channel: DistributionChannel
    capability_ids: Tuple[str, ...] = ()
    required_permissions: Tuple[Permission, ...] = ()
    optional_permissions: Tuple[Permission, ...] = ()


@dataclass(frozen=True)
class TrustedDistributionManifestV1:
    artifact: ArtifactDescriptorV1
    source: SourceBindingV1
    signer: SignerRequirementV1
    supersedes_manifest_id: Optional[str] = None
    rollback_of_manifest_id: Optional[str] = None
    notes: Tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION
    manifest_id: str = ""

    def with_computed_id(self) -> "TrustedDistributionManifestV1":
        object.__setattr__(self, "manifest_id", compute_manifest_id(self))
        return self


@dataclass(frozen=True)
class TrustedVerificationEvidenceV1:
    manifest_id: str
    manifest_digest_sha256: str
    artifact_sha256_hex: str
    signer_id: str
    key_id: str
    key_generation: str
    trust_store_generation: str
    verification_source_ref: str
    verification_currentness_ref: str
    signature_verified: bool
    key_revoked: bool = False


@dataclass(frozen=True)
class RollbackAuthorizationV1:
    from_manifest_id: str
    to_manifest_id: str
    authority_ref: str
    authority_currentness_ref: str
    authorized: bool


@dataclass(frozen=True)
class DistributionPolicyV1:
    current_source_currentness_ref: str
    current_trust_store_generation: str
    current_trust_currentness_ref: str
    allowed_channels: Tuple[DistributionChannel, ...]
    allowed_required_permissions: Tuple[Permission, ...]
    allowed_origin_schemes: Tuple[str, ...] = ("https",)
    allowed_origin_hosts: Tuple[str, ...] = ()
    trusted_verifier_refs: Tuple[str, ...] = ()
    allow_channel_change: bool = False
    require_consent_for_new_required_permissions: bool = True
    rollback_authorization: Optional[RollbackAuthorizationV1] = None


@dataclass(frozen=True)
class DistributionAdmissionReceiptV1:
    manifest_id: str
    artifact_id: str
    version: str
    status: AdmissionStatus
    reasons: Tuple[str, ...]
    added_required_permissions: Tuple[Permission, ...]
    removed_required_permissions: Tuple[Permission, ...]
    install_authorized: bool = False
    update_authorized: bool = False
    public_distribution_authorized: bool = False
    effect_authorized: bool = False
    execution_proven: bool = False


def _canonical_manifest_dict(manifest: TrustedDistributionManifestV1) -> dict:
    data = asdict(manifest)
    data["manifest_id"] = ""
    return data


def _normalize(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    return value


def canonical_manifest_json(manifest: TrustedDistributionManifestV1) -> str:
    return json.dumps(
        _normalize(_canonical_manifest_dict(manifest)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def manifest_digest_sha256(manifest: TrustedDistributionManifestV1) -> str:
    return sha256(canonical_manifest_json(manifest).encode("utf-8")).hexdigest()


def compute_manifest_id(manifest: TrustedDistributionManifestV1) -> str:
    return f"tdm1:{manifest_digest_sha256(manifest)}"


_SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def parse_semver(version: str) -> tuple[int, int, int, tuple]:
    match = _SEMVER.fullmatch(version)
    if not match:
        raise ValueError("INVALID_SEMVER")
    major, minor, patch = map(int, match.group(1, 2, 3))
    prerelease = match.group(4)
    if prerelease is None:
        pre_key = ((1, ""),)
    else:
        parts = []
        for part in prerelease.split("."):
            if part.isdigit():
                parts.append((0, int(part)))
            else:
                parts.append((0, part))
        pre_key = tuple(parts)
    return major, minor, patch, pre_key


def _version_cmp(a: str, b: str) -> int:
    def key(v: str):
        m = _SEMVER.fullmatch(v)
        if not m:
            raise ValueError("INVALID_SEMVER")
        core = tuple(map(int, m.group(1, 2, 3)))
        pre = m.group(4)
        if pre is None:
            return core, (1,)
        bits = []
        for part in pre.split("."):
            bits.append((0, int(part)) if part.isdigit() else (1, part))
        return core, (0, tuple(bits))

    ka, kb = key(a), key(b)
    return (ka > kb) - (ka < kb)


def _validate_hex_digest(value: str, code: str, reasons: list[str]) -> None:
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        reasons.append(code)


def _validate_manifest_shape(manifest: TrustedDistributionManifestV1, reasons: list[str]) -> None:
    if manifest.schema_version != SCHEMA_VERSION:
        reasons.append("SCHEMA_VERSION_UNSUPPORTED")
    if not manifest.artifact.artifact_id.strip():
        reasons.append("ARTIFACT_ID_REQUIRED")
    try:
        parse_semver(manifest.artifact.version)
    except ValueError:
        reasons.append("INVALID_SEMVER")
    _validate_hex_digest(manifest.artifact.sha256_hex, "ARTIFACT_DIGEST_INVALID", reasons)
    _validate_hex_digest(manifest.source.source_digest_sha256, "SOURCE_DIGEST_INVALID", reasons)
    if manifest.artifact.size_bytes < 0:
        reasons.append("ARTIFACT_SIZE_INVALID")
    if set(manifest.artifact.required_permissions) & set(manifest.artifact.optional_permissions):
        reasons.append("PERMISSION_CLASS_OVERLAP")
    if len(set(manifest.artifact.required_permissions)) != len(manifest.artifact.required_permissions):
        reasons.append("DUPLICATE_REQUIRED_PERMISSION")
    if len(set(manifest.artifact.optional_permissions)) != len(manifest.artifact.optional_permissions):
        reasons.append("DUPLICATE_OPTIONAL_PERMISSION")
    if len(set(manifest.artifact.capability_ids)) != len(manifest.artifact.capability_ids):
        reasons.append("DUPLICATE_CAPABILITY_ID")


def verify_distribution_manifest(
    manifest: TrustedDistributionManifestV1,
    *,
    observed_artifact_sha256_hex: str,
    observed_artifact_size_bytes: int,
    evidence: Optional[TrustedVerificationEvidenceV1],
    policy: DistributionPolicyV1,
    previous_manifest: Optional[TrustedDistributionManifestV1] = None,
) -> DistributionAdmissionReceiptV1:
    """Pure pre-effect trust/currentness admission.

    ADMISSIBLE only means the package/update may proceed to a separate effect
    authority gate. It never grants install, update, distribution, or execution
    authority.
    """
    refused: list[str] = []
    rebase: list[str] = []
    consent: list[str] = []
    _validate_manifest_shape(manifest, refused)

    expected_id = compute_manifest_id(manifest)
    expected_digest = manifest_digest_sha256(manifest)
    if manifest.manifest_id != expected_id:
        refused.append("MANIFEST_ID_MISMATCH")

    parsed = urlparse(manifest.artifact.origin_uri)
    if parsed.scheme not in set(policy.allowed_origin_schemes):
        refused.append("ORIGIN_SCHEME_NOT_ALLOWED")
    if policy.allowed_origin_hosts and (parsed.hostname or "") not in set(policy.allowed_origin_hosts):
        refused.append("ORIGIN_HOST_NOT_ALLOWED")

    if manifest.artifact.channel not in set(policy.allowed_channels):
        refused.append("CHANNEL_NOT_ALLOWED")

    disallowed_required = set(manifest.artifact.required_permissions) - set(
        policy.allowed_required_permissions
    )
    if disallowed_required:
        refused.append("REQUIRED_PERMISSION_EXCEEDS_POLICY")

    if manifest.source.source_currentness_ref != policy.current_source_currentness_ref:
        rebase.append("SOURCE_CURRENTNESS_STALE")

    if observed_artifact_sha256_hex != manifest.artifact.sha256_hex:
        refused.append("ARTIFACT_DIGEST_MISMATCH")
    if observed_artifact_size_bytes != manifest.artifact.size_bytes:
        refused.append("ARTIFACT_SIZE_MISMATCH")

    if evidence is None:
        refused.append("TRUST_EVIDENCE_REQUIRED")
    else:
        if policy.trusted_verifier_refs and evidence.verification_source_ref not in set(policy.trusted_verifier_refs):
            refused.append("UNTRUSTED_VERIFICATION_SOURCE")
        if not evidence.signature_verified:
            refused.append("SIGNATURE_NOT_VERIFIED")
        if evidence.key_revoked:
            refused.append("SIGNING_KEY_REVOKED")
        if evidence.manifest_id != manifest.manifest_id:
            refused.append("TRUST_MANIFEST_ID_MISMATCH")
        if evidence.manifest_digest_sha256 != expected_digest:
            refused.append("TRUST_MANIFEST_DIGEST_MISMATCH")
        if evidence.artifact_sha256_hex != manifest.artifact.sha256_hex:
            refused.append("TRUST_ARTIFACT_DIGEST_MISMATCH")
        if evidence.signer_id != manifest.signer.signer_id:
            refused.append("TRUST_SIGNER_MISMATCH")
        if evidence.key_id != manifest.signer.key_id:
            refused.append("TRUST_KEY_ID_MISMATCH")
        if evidence.key_generation != manifest.signer.key_generation:
            refused.append("TRUST_KEY_GENERATION_MISMATCH")
        if evidence.trust_store_generation != policy.current_trust_store_generation:
            rebase.append("TRUST_STORE_GENERATION_STALE")
        if evidence.verification_currentness_ref != policy.current_trust_currentness_ref:
            rebase.append("TRUST_CURRENTNESS_STALE")

    added: tuple[Permission, ...] = ()
    removed: tuple[Permission, ...] = ()

    if previous_manifest is not None:
        if previous_manifest.artifact.artifact_id != manifest.artifact.artifact_id:
            refused.append("ARTIFACT_ID_CHANGED")
        if previous_manifest.artifact.kind != manifest.artifact.kind:
            refused.append("ARTIFACT_KIND_CHANGED")
        if manifest.supersedes_manifest_id != previous_manifest.manifest_id:
            refused.append("SUPERSESSION_BINDING_REQUIRED")
        if previous_manifest.artifact.channel != manifest.artifact.channel and not policy.allow_channel_change:
            refused.append("CHANNEL_CHANGE_NOT_ALLOWED")

        prev_required = set(previous_manifest.artifact.required_permissions)
        new_required = set(manifest.artifact.required_permissions)
        added = tuple(sorted(new_required - prev_required, key=lambda p: p.value))
        removed = tuple(sorted(prev_required - new_required, key=lambda p: p.value))
        if added and policy.require_consent_for_new_required_permissions:
            consent.append("NEW_REQUIRED_PERMISSION_CONSENT_REQUIRED")

        try:
            cmp = _version_cmp(manifest.artifact.version, previous_manifest.artifact.version)
        except ValueError:
            cmp = 0
        if cmp < 0:
            auth = policy.rollback_authorization
            if manifest.rollback_of_manifest_id != previous_manifest.manifest_id:
                refused.append("ROLLBACK_BINDING_REQUIRED")
            if (
                auth is None
                or not auth.authorized
                or auth.from_manifest_id != previous_manifest.manifest_id
                or auth.to_manifest_id != manifest.manifest_id
                or auth.authority_currentness_ref != policy.current_trust_currentness_ref
            ):
                refused.append("ROLLBACK_AUTHORITY_REQUIRED")
        elif manifest.rollback_of_manifest_id is not None:
            refused.append("ROLLBACK_MARKER_ON_NONROLLBACK")
    else:
        if manifest.supersedes_manifest_id is not None:
            refused.append("UNRESOLVED_SUPERSESSION")
        if manifest.rollback_of_manifest_id is not None:
            refused.append("UNRESOLVED_ROLLBACK")

    if refused:
        status = AdmissionStatus.REFUSED
        reasons = tuple(sorted(set(refused + rebase + consent)))
    elif rebase:
        status = AdmissionStatus.REBASE_REQUIRED
        reasons = tuple(sorted(set(rebase + consent)))
    elif consent:
        status = AdmissionStatus.CONSENT_REQUIRED
        reasons = tuple(sorted(set(consent)))
    else:
        status = AdmissionStatus.ADMISSIBLE
        reasons = ()

    return DistributionAdmissionReceiptV1(
        manifest_id=manifest.manifest_id,
        artifact_id=manifest.artifact.artifact_id,
        version=manifest.artifact.version,
        status=status,
        reasons=reasons,
        added_required_permissions=added,
        removed_required_permissions=removed,
    )
