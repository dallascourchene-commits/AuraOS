"""GLM53-MTP resolver trust request / external-appraiser membrane.

D0 structural trust grammar only. This module can bind the exact MTP evidence,
resolver, owner-policy, issuer, appraiser, currentness, and revocation coordinates
needed by a future domain authority. It deliberately cannot authenticate its own
appraiser input and therefore can never clear GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED
or admit G2 by itself.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any

REQUEST_SCHEMA = "GLM53MTPResolverTrustRequestV1"
APPRAISER_SCHEMA = "ExternalAppraiserObservationV1"
DISPOSITION_REQUIRED = "EXTERNAL_APPRAISER_REQUIRED"
DISPOSITION_UNSATISFIED = "EXTERNAL_APPRAISER_UNSATISFIED"
DISPOSITION_MATCHED = "EXTERNAL_APPRAISER_MATCHED_NOT_AUTHENTICATED"
PROVENANCE_BLOCKER = "GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED"
EVIDENCE_DOMAIN = "GLM53_MTP_ROLE"
_ALLOWED_ROLE = "MTP_NON_DECODER"
_ALLOWED_STATES = {"ACTIVE", "REVOKED", "SUPERSEDED"}
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,511}$")


class MTPResolverTrustError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _token(value: Any, code: str) -> str:
    if not isinstance(value, str):
        raise MTPResolverTrustError(code)
    out = value.strip()
    if not out or not _TOKEN.fullmatch(out):
        raise MTPResolverTrustError(code)
    return out


def _sha40(value: Any, code: str) -> str:
    out = _token(value, code).lower()
    if not _SHA40.fullmatch(out):
        raise MTPResolverTrustError(code)
    return out


def _sha64(value: Any, code: str) -> str:
    out = _token(value, code).lower()
    if not _SHA64.fullmatch(out):
        raise MTPResolverTrustError(code)
    return out


def _bool(value: Any, code: str) -> bool:
    if type(value) is not bool:
        raise MTPResolverTrustError(code)
    return value


def _roles(value: Any, hidden: int) -> tuple[tuple[int, str], ...]:
    if not isinstance(value, tuple) or not value:
        raise MTPResolverTrustError("MTP_ROLE_SET_REQUIRED")
    seen: set[int] = set()
    normalized: list[tuple[int, str]] = []
    for item in value:
        if (
            not isinstance(item, tuple)
            or len(item) != 2
            or isinstance(item[0], bool)
            or not isinstance(item[0], int)
            or not isinstance(item[1], str)
        ):
            raise MTPResolverTrustError("MTP_ROLE_ENTRY_INVALID")
        index, role = item
        if index < hidden:
            raise MTPResolverTrustError("DECODER_LAYER_ROLE_FORBIDDEN", str(index))
        if role != _ALLOWED_ROLE:
            raise MTPResolverTrustError("MTP_ROLE_UNSUPPORTED", role)
        if index in seen:
            raise MTPResolverTrustError("MTP_ROLE_DUPLICATE", str(index))
        seen.add(index)
        normalized.append((index, role))
    return tuple(sorted(normalized))


@dataclass(frozen=True)
class GLM53MTPResolverTrustRequest:
    model_revision: str
    index_sha256: str
    num_hidden_layers: int
    roles: tuple[tuple[int, str], ...]
    evidence_ref: str
    evidence_digest: str
    evidence_generation: str
    resolver_ref: str
    resolver_generation: str
    resolution_receipt_ref: str
    policy_ref: str
    policy_generation: str
    policy_currentness_ref: str
    issuer_ref: str
    issuer_generation: str
    subject_ref: str
    evidence_domain: str = EVIDENCE_DOMAIN
    schema: str = REQUEST_SCHEMA

    def normalized(self) -> dict[str, Any]:
        if self.schema != REQUEST_SCHEMA:
            raise MTPResolverTrustError("REQUEST_SCHEMA_MISMATCH")
        if self.evidence_domain != EVIDENCE_DOMAIN:
            raise MTPResolverTrustError("EVIDENCE_DOMAIN_MISMATCH")
        if isinstance(self.num_hidden_layers, bool) or not isinstance(self.num_hidden_layers, int) or self.num_hidden_layers <= 0:
            raise MTPResolverTrustError("NUM_HIDDEN_LAYERS_INVALID")
        roles = _roles(self.roles, self.num_hidden_layers)
        return {
            "schema": REQUEST_SCHEMA,
            "evidence_domain": EVIDENCE_DOMAIN,
            "model_revision": _sha40(self.model_revision, "MODEL_REVISION_INVALID"),
            "index_sha256": _sha64(self.index_sha256, "INDEX_SHA256_INVALID"),
            "num_hidden_layers": self.num_hidden_layers,
            "roles": [{"index": i, "role": r, "decoder_pager_membership": False} for i, r in roles],
            "evidence_ref": _token(self.evidence_ref, "EVIDENCE_REF_INVALID"),
            "evidence_digest": _sha64(self.evidence_digest, "EVIDENCE_DIGEST_INVALID"),
            "evidence_generation": _token(self.evidence_generation, "EVIDENCE_GENERATION_INVALID"),
            "resolver_ref": _token(self.resolver_ref, "RESOLVER_REF_INVALID"),
            "resolver_generation": _token(self.resolver_generation, "RESOLVER_GENERATION_INVALID"),
            "resolution_receipt_ref": _token(self.resolution_receipt_ref, "RESOLUTION_RECEIPT_REF_INVALID"),
            "policy_ref": _token(self.policy_ref, "POLICY_REF_INVALID"),
            "policy_generation": _token(self.policy_generation, "POLICY_GENERATION_INVALID"),
            "policy_currentness_ref": _token(self.policy_currentness_ref, "POLICY_CURRENTNESS_REF_INVALID"),
            "issuer_ref": _token(self.issuer_ref, "ISSUER_REF_INVALID"),
            "issuer_generation": _token(self.issuer_generation, "ISSUER_GENERATION_INVALID"),
            "subject_ref": _token(self.subject_ref, "SUBJECT_REF_INVALID"),
        }

    @property
    def request_digest(self) -> str:
        return _digest({"domain_separator": "AURA/AWJ032/GLM53_MTP_ROLE/TRUST_REQUEST/V1", "request": self.normalized()})


@dataclass(frozen=True)
class ExternalAppraiserObservation:
    request_digest: str
    appraiser_ref: str
    appraiser_generation: str
    appraiser_currentness_ref: str
    verification_receipt_ref: str
    issuer_trusted: bool
    owner_policy_resolved: bool
    policy_current: bool
    attestation_current: bool
    state: str
    schema: str = APPRAISER_SCHEMA

    def normalized(self) -> dict[str, Any]:
        if self.schema != APPRAISER_SCHEMA:
            raise MTPResolverTrustError("APPRAISER_SCHEMA_MISMATCH")
        if self.state not in _ALLOWED_STATES:
            raise MTPResolverTrustError("APPRAISER_STATE_INVALID")
        return {
            "schema": APPRAISER_SCHEMA,
            "request_digest": _sha64(self.request_digest, "APPRAISER_REQUEST_DIGEST_INVALID"),
            "appraiser_ref": _token(self.appraiser_ref, "APPRAISER_REF_INVALID"),
            "appraiser_generation": _token(self.appraiser_generation, "APPRAISER_GENERATION_INVALID"),
            "appraiser_currentness_ref": _token(self.appraiser_currentness_ref, "APPRAISER_CURRENTNESS_REF_INVALID"),
            "verification_receipt_ref": _token(self.verification_receipt_ref, "VERIFICATION_RECEIPT_REF_INVALID"),
            "issuer_trusted": _bool(self.issuer_trusted, "ISSUER_TRUST_BOOL_REQUIRED"),
            "owner_policy_resolved": _bool(self.owner_policy_resolved, "OWNER_POLICY_RESOLVED_BOOL_REQUIRED"),
            "policy_current": _bool(self.policy_current, "POLICY_CURRENT_BOOL_REQUIRED"),
            "attestation_current": _bool(self.attestation_current, "ATTESTATION_CURRENT_BOOL_REQUIRED"),
            "state": self.state,
        }

    @property
    def observation_digest(self) -> str:
        return _digest(self.normalized())


@dataclass(frozen=True)
class ResolverTrustAdmission:
    request_digest: str
    disposition: str
    blocker: str
    appraiser_observation_digest: str | None
    resolver_provenance_proven_by_this_module: bool = False
    g2_admitted: bool = False
    authority: bool = False
    runtime_executed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def logical_id(self) -> str:
        return _digest(self.to_dict())


def admit_external_appraiser(
    request: GLM53MTPResolverTrustRequest,
    observation: ExternalAppraiserObservation | None,
) -> ResolverTrustAdmission:
    if not isinstance(request, GLM53MTPResolverTrustRequest):
        raise MTPResolverTrustError("TRUST_REQUEST_REQUIRED")
    request.normalized()
    if observation is None:
        return ResolverTrustAdmission(
            request_digest=request.request_digest,
            disposition=DISPOSITION_REQUIRED,
            blocker=PROVENANCE_BLOCKER,
            appraiser_observation_digest=None,
        )
    if not isinstance(observation, ExternalAppraiserObservation):
        raise MTPResolverTrustError("APPRAISER_OBSERVATION_REQUIRED")
    appraiser = observation.normalized()
    if appraiser["request_digest"] != request.request_digest:
        raise MTPResolverTrustError("APPRAISER_REQUEST_DIGEST_MISMATCH")

    satisfied = (
        appraiser["state"] == "ACTIVE"
        and appraiser["issuer_trusted"]
        and appraiser["owner_policy_resolved"]
        and appraiser["policy_current"]
        and appraiser["attestation_current"]
    )
    return ResolverTrustAdmission(
        request_digest=request.request_digest,
        disposition=DISPOSITION_MATCHED if satisfied else DISPOSITION_UNSATISFIED,
        blocker=PROVENANCE_BLOCKER,
        appraiser_observation_digest=observation.observation_digest,
    )
