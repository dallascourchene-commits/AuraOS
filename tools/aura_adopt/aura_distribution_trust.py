from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Mapping


MANIFEST_SCHEMA = "TrustedDistributionManifestV1"
RECEIPT_SCHEMA = "DistributionAdmissionReceiptV1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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


class AuthorityClass(str, Enum):
    DATA_ONLY = "DATA_ONLY"
    USER_GESTURE_LOCAL = "USER_GESTURE_LOCAL"
    CODE_EXECUTION = "CODE_EXECUTION"
    INSTALLABLE_BINARY = "INSTALLABLE_BINARY"


class SignatureStatus(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"
    VERIFIED = "VERIFIED"


class AdmissionDisposition(str, Enum):
    TRUST_READY = "TRUST_READY"
    REBASE_REQUIRED = "REBASE_REQUIRED"
    EVIDENCE_REQUIRED = "EVIDENCE_REQUIRED"
    INTEGRITY_MISMATCH = "INTEGRITY_MISMATCH"
    SOURCE_NOT_IMMUTABLE = "SOURCE_NOT_IMMUTABLE"
    SIGNATURE_EVIDENCE_REQUIRED = "SIGNATURE_EVIDENCE_REQUIRED"


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
    media_type: str = "application/octet-stream"
    signature_status: SignatureStatus = SignatureStatus.NOT_APPLICABLE
    signature_evidence_ref: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_id", _text("artifact_id", self.artifact_id))
        object.__setattr__(self, "kind", _strict_enum("kind", self.kind, ArtifactKind))
        object.__setattr__(
            self, "authority_class", _strict_enum("authority_class", self.authority_class, AuthorityClass)
        )
        object.__setattr__(self, "source_ref", _text("source_ref", self.source_ref))
        object.__setattr__(self, "source_generation", _text("source_generation", self.source_generation))
        object.__setattr__(
            self, "source_currentness_ref", _text("source_currentness_ref", self.source_currentness_ref)
        )
        object.__setattr__(self, "content_sha256", _sha256("content_sha256", self.content_sha256))
        if isinstance(self.byte_size, bool) or not isinstance(self.byte_size, int) or self.byte_size < 0:
            raise DistributionRefusal("INVALID_BYTE_SIZE")
        if not isinstance(self.immutable_source, bool):
            raise DistributionRefusal("INVALID_IMMUTABLE_SOURCE")
        object.__setattr__(self, "media_type", _text("media_type", self.media_type))
        object.__setattr__(
            self, "signature_status", _strict_enum("signature_status", self.signature_status, SignatureStatus)
        )
        if not isinstance(self.signature_evidence_ref, str):
            raise DistributionRefusal("INVALID_SIGNATURE_EVIDENCE_REF")
        object.__setattr__(self, "signature_evidence_ref", self.signature_evidence_ref.strip())

        if self.authority_class is AuthorityClass.INSTALLABLE_BINARY:
            if self.signature_status is not SignatureStatus.VERIFIED or not self.signature_evidence_ref:
                raise DistributionRefusal("SIGNATURE_EVIDENCE_REQUIRED", self.artifact_id)
        elif self.signature_status is SignatureStatus.VERIFIED and not self.signature_evidence_ref:
            raise DistributionRefusal("SIGNATURE_EVIDENCE_REQUIRED", self.artifact_id)


@dataclass(frozen=True)
class TrustedDistributionManifest:
    route_id: str
    build_ref: str
    manifest_generation: str
    source_currentness_ref: str
    artifacts: tuple[DistributionArtifact, ...]
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
        object.__setattr__(
            self, "source_currentness_ref", _text("source_currentness_ref", self.source_currentness_ref)
        )
        if not isinstance(self.artifacts, tuple) or not self.artifacts:
            raise DistributionRefusal("ARTIFACTS_REQUIRED")
        if any(not isinstance(a, DistributionArtifact) for a in self.artifacts):
            raise DistributionRefusal("INVALID_ARTIFACT")
        ids = [a.artifact_id for a in self.artifacts]
        if len(ids) != len(set(ids)):
            raise DistributionRefusal("DUPLICATE_ARTIFACT_ID")
        if self.update_policy != "PINNED_ONLY":
            raise DistributionRefusal("UNPINNED_UPDATE_POLICY")
        for name in (
            "telemetry_default_enabled",
            "content_upload_default_enabled",
            "network_code_fetch_authorized",
            "public_distribution_authorized",
        ):
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
                    "signature_status": a.signature_status.value,
                }
                for a in sorted(self.artifacts, key=lambda item: item.artifact_id)
            ],
        }

    @property
    def manifest_digest(self) -> str:
        return _stable_digest(self.logical_dict())


@dataclass(frozen=True)
class DistributionAdmissionReceipt:
    manifest_digest: str
    route_id: str
    disposition: AdmissionDisposition
    blockers: tuple[str, ...]
    verified_artifact_ids: tuple[str, ...]
    integrity_ready: bool
    signature_ready: bool
    currentness_ready: bool
    effect_authorized: bool = False
    execution_authorized: bool = False
    execution_proven: bool = False
    install_performed: bool = False
    network_fetch_performed: bool = False
    public_distribution_performed: bool = False
    schema: str = RECEIPT_SCHEMA


def admit_distribution(
    manifest: TrustedDistributionManifest,
    *,
    expected_currentness_ref: str,
    observed_digests: Mapping[str, str],
) -> DistributionAdmissionReceipt:
    if not isinstance(manifest, TrustedDistributionManifest):
        raise DistributionRefusal("INVALID_MANIFEST")
    expected = _text("expected_currentness_ref", expected_currentness_ref)
    if not isinstance(observed_digests, Mapping):
        raise DistributionRefusal("INVALID_OBSERVED_DIGESTS")

    if expected != manifest.source_currentness_ref:
        return DistributionAdmissionReceipt(
            manifest.manifest_digest,
            manifest.route_id,
            AdmissionDisposition.REBASE_REQUIRED,
            ("CURRENTNESS_MISMATCH",),
            (),
            False,
            False,
            False,
        )

    blockers: list[str] = []
    verified: list[str] = []
    integrity_mismatch = False
    evidence_missing = False
    source_mutable = False
    signature_missing = False

    for artifact in manifest.artifacts:
        if artifact.source_currentness_ref != manifest.source_currentness_ref:
            blockers.append(f"ARTIFACT_CURRENTNESS_MISMATCH:{artifact.artifact_id}")
            continue
        if not artifact.immutable_source:
            blockers.append(f"MUTABLE_SOURCE_REFUSED:{artifact.artifact_id}")
            source_mutable = True
            continue
        if artifact.authority_class is AuthorityClass.INSTALLABLE_BINARY and (
            artifact.signature_status is not SignatureStatus.VERIFIED
            or not artifact.signature_evidence_ref
        ):
            blockers.append(f"SIGNATURE_EVIDENCE_REQUIRED:{artifact.artifact_id}")
            signature_missing = True
            continue
        observed = observed_digests.get(artifact.artifact_id)
        if observed is None:
            blockers.append(f"DIGEST_EVIDENCE_REQUIRED:{artifact.artifact_id}")
            evidence_missing = True
            continue
        try:
            observed = _sha256("observed_digest", observed)
        except DistributionRefusal:
            blockers.append(f"INVALID_OBSERVED_DIGEST:{artifact.artifact_id}")
            integrity_mismatch = True
            continue
        if observed != artifact.content_sha256:
            blockers.append(f"ARTIFACT_INTEGRITY_MISMATCH:{artifact.artifact_id}")
            integrity_mismatch = True
            continue
        verified.append(artifact.artifact_id)

    if any(b.startswith("ARTIFACT_CURRENTNESS_MISMATCH:") for b in blockers):
        disposition = AdmissionDisposition.REBASE_REQUIRED
    elif source_mutable:
        disposition = AdmissionDisposition.SOURCE_NOT_IMMUTABLE
    elif signature_missing:
        disposition = AdmissionDisposition.SIGNATURE_EVIDENCE_REQUIRED
    elif integrity_mismatch:
        disposition = AdmissionDisposition.INTEGRITY_MISMATCH
    elif evidence_missing:
        disposition = AdmissionDisposition.EVIDENCE_REQUIRED
    else:
        disposition = AdmissionDisposition.TRUST_READY

    ready = disposition is AdmissionDisposition.TRUST_READY
    signature_ready = ready and all(
        a.authority_class is not AuthorityClass.INSTALLABLE_BINARY
        or (
            a.signature_status is SignatureStatus.VERIFIED
            and bool(a.signature_evidence_ref)
        )
        for a in manifest.artifacts
    )
    return DistributionAdmissionReceipt(
        manifest.manifest_digest,
        manifest.route_id,
        disposition,
        tuple(blockers),
        tuple(sorted(verified)),
        ready,
        signature_ready,
        ready,
    )
