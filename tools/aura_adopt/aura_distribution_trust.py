from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Mapping, Optional
from urllib.parse import urlparse


MANIFEST_SCHEMA = "TrustedDistributionManifestV1"
RECEIPT_SCHEMA = "DistributionAdmissionReceiptV1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


class DistributionRefusal(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


class ArtifactKind(str, Enum):
    WEB_APP = "WEB_APP"
    PWA_MANIFEST = "PWA_MANIFEST"
    SERVICE_WORKER = "SERVICE_WORKER"
    RECIPE = "RECIPE"
    CAPABILITY = "CAPABILITY"
    WASM_MODULE = "WASM_MODULE"
    APK = "APK"
    UPDATE_MANIFEST = "UPDATE_MANIFEST"
    MODEL_BUNDLE = "MODEL_BUNDLE"


class AuthorityClass(str, Enum):
    DATA_ONLY = "DATA_ONLY"
    USER_GESTURE_LOCAL = "USER_GESTURE_LOCAL"
    CODE_EXECUTION = "CODE_EXECUTION"
    INSTALLABLE_BINARY = "INSTALLABLE_BINARY"


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


class AdmissionDisposition(str, Enum):
    TRUST_READY = "TRUST_READY"
    CONSENT_REQUIRED = "CONSENT_REQUIRED"
    REBASE_REQUIRED = "REBASE_REQUIRED"
    EVIDENCE_REQUIRED = "EVIDENCE_REQUIRED"
    INTEGRITY_MISMATCH = "INTEGRITY_MISMATCH"
    SOURCE_NOT_IMMUTABLE = "SOURCE_NOT_IMMUTABLE"
    SIGNATURE_EVIDENCE_REQUIRED = "SIGNATURE_EVIDENCE_REQUIRED"
    POLICY_REFUSED = "POLICY_REFUSED"


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DistributionRefusal(f"INVALID_{name.upper()}")
    return value.strip()


def _sha256(name: str, value: object) -> str:
    value = _text(name, value).lower()
    if not _SHA256_RE.fullmatch(value):
        raise DistributionRefusal(f"INVALID_{name.upper()}")
    return value


def _strict_enum(name: str, value: object, enum_type: type[Enum]) -> Enum:
    if not isinstance(value, enum_type):
        raise DistributionRefusal(f"INVALID_{name.upper()}")
    return value


def _stable_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _version_key(version: str):
    match = _SEMVER_RE.fullmatch(version)
    if not match:
        raise DistributionRefusal("INVALID_VERSION")
    core = tuple(map(int, match.group(1, 2, 3)))
    prerelease = match.group(4)
    if prerelease is None:
        return core, (1,)
    parts = []
    for part in prerelease.split("."):
        parts.append((0, int(part)) if part.isdigit() else (1, part))
    return core, (0, tuple(parts))


@dataclass(frozen=True)
class DistributionArtifact:
    artifact_id: str
    kind: ArtifactKind
    authority_class: AuthorityClass
    source_ref: str
    source_generation: str
    source_currentness_ref: str
    content_sha256: str
    byte_size: int
    immutable_source: bool
    version: str
    origin_uri: str
    channel: DistributionChannel
    media_type: str = "application/octet-stream"
    capability_ids: tuple[str, ...] = ()
    required_permissions: tuple[Permission, ...] = ()
    optional_permissions: tuple[Permission, ...] = ()
    binary_signature_evidence_ref: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_id", _text("artifact_id", self.artifact_id))
        object.__setattr__(self, "kind", _strict_enum("kind", self.kind, ArtifactKind))
        object.__setattr__(self, "authority_class", _strict_enum("authority_class", self.authority_class, AuthorityClass))
        object.__setattr__(self, "source_ref", _text("source_ref", self.source_ref))
        object.__setattr__(self, "source_generation", _text("source_generation", self.source_generation))
        object.__setattr__(self, "source_currentness_ref", _text("source_currentness_ref", self.source_currentness_ref))
        object.__setattr__(self, "content_sha256", _sha256("content_sha256", self.content_sha256))
        if isinstance(self.byte_size, bool) or not isinstance(self.byte_size, int) or self.byte_size < 0:
            raise DistributionRefusal("INVALID_BYTE_SIZE")
        if not isinstance(self.immutable_source, bool):
            raise DistributionRefusal("INVALID_IMMUTABLE_SOURCE")
        _version_key(_text("version", self.version))
        object.__setattr__(self, "origin_uri", _text("origin_uri", self.origin_uri))
        object.__setattr__(self, "channel", _strict_enum("channel", self.channel, DistributionChannel))
        object.__setattr__(self, "media_type", _text("media_type", self.media_type))
        if not isinstance(self.capability_ids, tuple) or any(not isinstance(v, str) or not v.strip() for v in self.capability_ids):
            raise DistributionRefusal("INVALID_CAPABILITY_IDS")
        if len(self.capability_ids) != len(set(self.capability_ids)):
            raise DistributionRefusal("DUPLICATE_CAPABILITY_ID")
        for name, values in (("required_permissions", self.required_permissions), ("optional_permissions", self.optional_permissions)):
            if not isinstance(values, tuple) or any(not isinstance(v, Permission) for v in values):
                raise DistributionRefusal(f"INVALID_{name.upper()}")
            if len(values) != len(set(values)):
                raise DistributionRefusal(f"DUPLICATE_{name.upper()}")
        if set(self.required_permissions) & set(self.optional_permissions):
            raise DistributionRefusal("PERMISSION_CLASS_OVERLAP")
        if not isinstance(self.binary_signature_evidence_ref, str):
            raise DistributionRefusal("INVALID_BINARY_SIGNATURE_EVIDENCE_REF")
        object.__setattr__(self, "binary_signature_evidence_ref", self.binary_signature_evidence_ref.strip())


@dataclass(frozen=True)
class ManifestSignerRequirement:
    signer_id: str
    key_id: str
    key_generation: str
    algorithm: str = "ED25519"

    def __post_init__(self) -> None:
        object.__setattr__(self, "signer_id", _text("signer_id", self.signer_id))
        object.__setattr__(self, "key_id", _text("key_id", self.key_id))
        object.__setattr__(self, "key_generation", _text("key_generation", self.key_generation))
        object.__setattr__(self, "algorithm", _text("algorithm", self.algorithm))


@dataclass(frozen=True)
class TrustedDistributionManifest:
    route_id: str
    build_ref: str
    manifest_generation: str
    source_currentness_ref: str
    artifacts: tuple[DistributionArtifact, ...]
    signer: ManifestSignerRequirement
    supersedes_manifest_digest: str = ""
    rollback_of_manifest_digest: str = ""
    update_policy: str = "PINNED_ONLY"
    telemetry_default_enabled: bool = False
    content_upload_default_enabled: bool = False
    network_code_fetch_authorized: bool = False
    public_distribution_authorized: bool = False
    schema: str = MANIFEST_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "route_id", _text("route_id", self.route_id))
        object.__setattr__(self, "build_ref", _text("build_ref", self.build_ref))
        object.__setattr__(self, "manifest_generation", _text("manifest_generation", self.manifest_generation))
        object.__setattr__(self, "source_currentness_ref", _text("source_currentness_ref", self.source_currentness_ref))
        if not isinstance(self.artifacts, tuple) or not self.artifacts:
            raise DistributionRefusal("ARTIFACTS_REQUIRED")
        if any(not isinstance(a, DistributionArtifact) for a in self.artifacts):
            raise DistributionRefusal("INVALID_ARTIFACT")
        ids = [a.artifact_id for a in self.artifacts]
        if len(ids) != len(set(ids)):
            raise DistributionRefusal("DUPLICATE_ARTIFACT_ID")
        if not isinstance(self.signer, ManifestSignerRequirement):
            raise DistributionRefusal("INVALID_SIGNER_REQUIREMENT")
        for name in ("supersedes_manifest_digest", "rollback_of_manifest_digest"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise DistributionRefusal(f"INVALID_{name.upper()}")
            value = value.strip().lower()
            if value:
                _sha256(name, value)
            object.__setattr__(self, name, value)
        if self.update_policy != "PINNED_ONLY":
            raise DistributionRefusal("UNPINNED_UPDATE_POLICY")
        for name in ("telemetry_default_enabled", "content_upload_default_enabled", "network_code_fetch_authorized", "public_distribution_authorized"):
            if not isinstance(getattr(self, name), bool):
                raise DistributionRefusal(f"INVALID_{name.upper()}")
        if self.telemetry_default_enabled:
            raise DistributionRefusal("TELEMETRY_DEFAULT_MUST_BE_OFF")
        if self.content_upload_default_enabled:
            raise DistributionRefusal("CONTENT_UPLOAD_DEFAULT_MUST_BE_OFF")
        if self.network_code_fetch_authorized:
            raise DistributionRefusal("NETWORK_CODE_FETCH_AUTHORITY_REFUSED")
        if self.public_distribution_authorized:
            raise DistributionRefusal("PUBLIC_DISTRIBUTION_AUTHORITY_REFUSED")

    def logical_dict(self) -> dict:
        return {
            "schema": self.schema,
            "route_id": self.route_id,
            "build_ref": self.build_ref,
            "manifest_generation": self.manifest_generation,
            "source_currentness_ref": self.source_currentness_ref,
            "signer": asdict(self.signer),
            "supersedes_manifest_digest": self.supersedes_manifest_digest,
            "rollback_of_manifest_digest": self.rollback_of_manifest_digest,
            "update_policy": self.update_policy,
            "telemetry_default_enabled": False,
            "content_upload_default_enabled": False,
            "network_code_fetch_authorized": False,
            "public_distribution_authorized": False,
            "artifacts": [
                {
                    **asdict(a),
                    "kind": a.kind.value,
                    "authority_class": a.authority_class.value,
                    "channel": a.channel.value,
                    "required_permissions": [p.value for p in a.required_permissions],
                    "optional_permissions": [p.value for p in a.optional_permissions],
                }
                for a in sorted(self.artifacts, key=lambda item: item.artifact_id)
            ],
        }

    @property
    def manifest_digest(self) -> str:
        return _stable_digest(self.logical_dict())


@dataclass(frozen=True)
class TrustedManifestVerificationEvidence:
    manifest_digest: str
    signer_id: str
    key_id: str
    key_generation: str
    trust_store_generation: str
    verification_source_ref: str
    verification_currentness_ref: str
    signature_verified: bool
    verified_binary_artifact_ids: tuple[str, ...] = ()
    key_revoked: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "manifest_digest", _sha256("manifest_digest", self.manifest_digest))
        for name in ("signer_id", "key_id", "key_generation", "trust_store_generation", "verification_source_ref", "verification_currentness_ref"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        if not isinstance(self.signature_verified, bool) or not isinstance(self.key_revoked, bool):
            raise DistributionRefusal("INVALID_TRUST_BOOLEAN")
        if not isinstance(self.verified_binary_artifact_ids, tuple) or any(not isinstance(v, str) or not v.strip() for v in self.verified_binary_artifact_ids):
            raise DistributionRefusal("INVALID_VERIFIED_BINARY_ARTIFACT_IDS")


@dataclass(frozen=True)
class RollbackAuthorization:
    from_manifest_digest: str
    to_manifest_digest: str
    authority_ref: str
    authority_currentness_ref: str
    authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "from_manifest_digest", _sha256("from_manifest_digest", self.from_manifest_digest))
        object.__setattr__(self, "to_manifest_digest", _sha256("to_manifest_digest", self.to_manifest_digest))
        object.__setattr__(self, "authority_ref", _text("authority_ref", self.authority_ref))
        object.__setattr__(self, "authority_currentness_ref", _text("authority_currentness_ref", self.authority_currentness_ref))
        if not isinstance(self.authorized, bool):
            raise DistributionRefusal("INVALID_ROLLBACK_AUTHORIZED")


@dataclass(frozen=True)
class DistributionPolicy:
    current_trust_store_generation: str
    current_trust_currentness_ref: str
    trusted_verifier_refs: tuple[str, ...]
    allowed_origin_schemes: tuple[str, ...] = ("https",)
    allowed_origin_hosts: tuple[str, ...] = ()
    allowed_channels: tuple[DistributionChannel, ...] = (DistributionChannel.STABLE,)
    allowed_required_permissions: tuple[Permission, ...] = ()
    require_consent_for_new_required_permissions: bool = True
    allow_channel_change: bool = False
    rollback_authorization: Optional[RollbackAuthorization] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "current_trust_store_generation", _text("current_trust_store_generation", self.current_trust_store_generation))
        object.__setattr__(self, "current_trust_currentness_ref", _text("current_trust_currentness_ref", self.current_trust_currentness_ref))
        if not self.trusted_verifier_refs or any(not isinstance(v, str) or not v.strip() for v in self.trusted_verifier_refs):
            raise DistributionRefusal("TRUSTED_VERIFIER_REFS_REQUIRED")
        if any(not isinstance(v, DistributionChannel) for v in self.allowed_channels):
            raise DistributionRefusal("INVALID_ALLOWED_CHANNELS")
        if any(not isinstance(v, Permission) for v in self.allowed_required_permissions):
            raise DistributionRefusal("INVALID_ALLOWED_REQUIRED_PERMISSIONS")


@dataclass(frozen=True)
class DistributionAdmissionReceipt:
    manifest_digest: str
    route_id: str
    disposition: AdmissionDisposition
    blockers: tuple[str, ...]
    verified_artifact_ids: tuple[str, ...]
    added_required_permissions: tuple[str, ...]
    removed_required_permissions: tuple[str, ...]
    integrity_ready: bool
    signature_ready: bool
    currentness_ready: bool
    effect_authorized: bool = False
    execution_authorized: bool = False
    execution_proven: bool = False
    install_performed: bool = False
    update_performed: bool = False
    network_fetch_performed: bool = False
    public_distribution_performed: bool = False
    schema: str = RECEIPT_SCHEMA


def _artifact_map(manifest: TrustedDistributionManifest) -> dict[str, DistributionArtifact]:
    return {a.artifact_id: a for a in manifest.artifacts}


def admit_distribution(
    manifest: TrustedDistributionManifest,
    *,
    expected_currentness_ref: str,
    observed_digests: Mapping[str, str],
    trust_evidence: Optional[TrustedManifestVerificationEvidence],
    policy: DistributionPolicy,
    previous_manifest: Optional[TrustedDistributionManifest] = None,
) -> DistributionAdmissionReceipt:
    if not isinstance(manifest, TrustedDistributionManifest):
        raise DistributionRefusal("INVALID_MANIFEST")
    expected = _text("expected_currentness_ref", expected_currentness_ref)
    if not isinstance(observed_digests, Mapping):
        raise DistributionRefusal("INVALID_OBSERVED_DIGESTS")
    if not isinstance(policy, DistributionPolicy):
        raise DistributionRefusal("INVALID_DISTRIBUTION_POLICY")

    rebase: list[str] = []
    evidence_missing: list[str] = []
    integrity: list[str] = []
    mutable: list[str] = []
    signature: list[str] = []
    policy_blockers: list[str] = []
    consent: list[str] = []
    verified: list[str] = []
    added_permissions: set[str] = set()
    removed_permissions: set[str] = set()

    if expected != manifest.source_currentness_ref:
        rebase.append("CURRENTNESS_MISMATCH")

    if trust_evidence is None:
        signature.append("TRUST_EVIDENCE_REQUIRED")
    else:
        if trust_evidence.verification_source_ref not in set(policy.trusted_verifier_refs):
            signature.append("UNTRUSTED_VERIFICATION_SOURCE")
        if trust_evidence.manifest_digest != manifest.manifest_digest:
            integrity.append("TRUST_MANIFEST_DIGEST_MISMATCH")
        if not trust_evidence.signature_verified:
            signature.append("MANIFEST_SIGNATURE_NOT_VERIFIED")
        if trust_evidence.key_revoked:
            signature.append("SIGNING_KEY_REVOKED")
        if trust_evidence.signer_id != manifest.signer.signer_id:
            signature.append("TRUST_SIGNER_MISMATCH")
        if trust_evidence.key_id != manifest.signer.key_id:
            signature.append("TRUST_KEY_ID_MISMATCH")
        if trust_evidence.key_generation != manifest.signer.key_generation:
            signature.append("TRUST_KEY_GENERATION_MISMATCH")
        if trust_evidence.trust_store_generation != policy.current_trust_store_generation:
            rebase.append("TRUST_STORE_GENERATION_STALE")
        if trust_evidence.verification_currentness_ref != policy.current_trust_currentness_ref:
            rebase.append("TRUST_CURRENTNESS_STALE")

    previous = _artifact_map(previous_manifest) if previous_manifest else {}
    current = _artifact_map(manifest)

    if previous_manifest is None:
        if manifest.supersedes_manifest_digest:
            policy_blockers.append("UNRESOLVED_SUPERSESSION")
        if manifest.rollback_of_manifest_digest:
            policy_blockers.append("UNRESOLVED_ROLLBACK")
    elif manifest.supersedes_manifest_digest != previous_manifest.manifest_digest:
        policy_blockers.append("SUPERSESSION_BINDING_REQUIRED")

    for artifact in manifest.artifacts:
        if artifact.source_currentness_ref != manifest.source_currentness_ref:
            rebase.append(f"ARTIFACT_CURRENTNESS_MISMATCH:{artifact.artifact_id}")
            continue
        if not artifact.immutable_source:
            mutable.append(f"MUTABLE_SOURCE_REFUSED:{artifact.artifact_id}")
            continue

        parsed = urlparse(artifact.origin_uri)
        if parsed.scheme not in set(policy.allowed_origin_schemes):
            policy_blockers.append(f"ORIGIN_SCHEME_NOT_ALLOWED:{artifact.artifact_id}")
        if policy.allowed_origin_hosts and (parsed.hostname or "") not in set(policy.allowed_origin_hosts):
            policy_blockers.append(f"ORIGIN_HOST_NOT_ALLOWED:{artifact.artifact_id}")
        if artifact.channel not in set(policy.allowed_channels):
            policy_blockers.append(f"CHANNEL_NOT_ALLOWED:{artifact.artifact_id}")
        disallowed = set(artifact.required_permissions) - set(policy.allowed_required_permissions)
        if disallowed:
            policy_blockers.append(f"REQUIRED_PERMISSION_EXCEEDS_POLICY:{artifact.artifact_id}")

        observed = observed_digests.get(artifact.artifact_id)
        if observed is None:
            evidence_missing.append(f"DIGEST_EVIDENCE_REQUIRED:{artifact.artifact_id}")
        else:
            try:
                observed = _sha256("observed_digest", observed)
            except DistributionRefusal:
                integrity.append(f"INVALID_OBSERVED_DIGEST:{artifact.artifact_id}")
            else:
                if observed != artifact.content_sha256:
                    integrity.append(f"ARTIFACT_INTEGRITY_MISMATCH:{artifact.artifact_id}")
                else:
                    verified.append(artifact.artifact_id)

        if artifact.authority_class is AuthorityClass.INSTALLABLE_BINARY:
            if trust_evidence is None or artifact.artifact_id not in set(trust_evidence.verified_binary_artifact_ids) or not artifact.binary_signature_evidence_ref:
                signature.append(f"BINARY_SIGNATURE_EVIDENCE_REQUIRED:{artifact.artifact_id}")

        old = previous.get(artifact.artifact_id)
        if old is not None:
            if old.kind is not artifact.kind or old.authority_class is not artifact.authority_class:
                policy_blockers.append(f"ARTIFACT_TYPE_CHANGED:{artifact.artifact_id}")
            if old.channel is not artifact.channel and not policy.allow_channel_change:
                policy_blockers.append(f"CHANNEL_CHANGE_NOT_ALLOWED:{artifact.artifact_id}")
            old_required = set(old.required_permissions)
            new_required = set(artifact.required_permissions)
            for permission in new_required - old_required:
                added_permissions.add(f"{artifact.artifact_id}:{permission.value}")
            for permission in old_required - new_required:
                removed_permissions.add(f"{artifact.artifact_id}:{permission.value}")
            if new_required - old_required and policy.require_consent_for_new_required_permissions:
                consent.append(f"NEW_REQUIRED_PERMISSION_CONSENT_REQUIRED:{artifact.artifact_id}")

            old_key = _version_key(old.version)
            new_key = _version_key(artifact.version)
            if new_key < old_key:
                auth = policy.rollback_authorization
                if manifest.rollback_of_manifest_digest != previous_manifest.manifest_digest:
                    policy_blockers.append("ROLLBACK_BINDING_REQUIRED")
                if auth is None or not auth.authorized or auth.from_manifest_digest != previous_manifest.manifest_digest or auth.to_manifest_digest != manifest.manifest_digest or auth.authority_currentness_ref != policy.current_trust_currentness_ref:
                    policy_blockers.append("ROLLBACK_AUTHORITY_REQUIRED")
            elif manifest.rollback_of_manifest_digest:
                policy_blockers.append("ROLLBACK_MARKER_ON_NONROLLBACK")

    if previous_manifest is not None:
        for artifact_id in previous:
            if artifact_id not in current:
                policy_blockers.append(f"ARTIFACT_REMOVAL_REQUIRES_EXPLICIT_POLICY:{artifact_id}")

    blockers = tuple(sorted(set(rebase + evidence_missing + integrity + mutable + signature + policy_blockers + consent)))
    if rebase:
        disposition = AdmissionDisposition.REBASE_REQUIRED
    elif mutable:
        disposition = AdmissionDisposition.SOURCE_NOT_IMMUTABLE
    elif signature:
        disposition = AdmissionDisposition.SIGNATURE_EVIDENCE_REQUIRED
    elif integrity:
        disposition = AdmissionDisposition.INTEGRITY_MISMATCH
    elif evidence_missing:
        disposition = AdmissionDisposition.EVIDENCE_REQUIRED
    elif policy_blockers:
        disposition = AdmissionDisposition.POLICY_REFUSED
    elif consent:
        disposition = AdmissionDisposition.CONSENT_REQUIRED
    else:
        disposition = AdmissionDisposition.TRUST_READY

    ready = disposition is AdmissionDisposition.TRUST_READY
    return DistributionAdmissionReceipt(
        manifest.manifest_digest,
        manifest.route_id,
        disposition,
        blockers,
        tuple(sorted(verified)),
        tuple(sorted(added_permissions)),
        tuple(sorted(removed_permissions)),
        ready,
        ready,
        not rebase,
    )
