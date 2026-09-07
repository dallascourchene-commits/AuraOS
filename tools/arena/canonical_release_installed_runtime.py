from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import sqlite3
from typing import Callable

from tools.project006.installed_runtime_attestation import (
    HostMeasurement,
    MeasurementEvidence,
    RuntimeDisposition,
    RuntimeReleaseManifest,
    attest_runtime,
)

D0 = "D0_NONPROMOTING"
SCHEMA = "AURA-CANONICAL-RELEASE-INSTALLED-RUNTIME-v1"


def canon(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def root(value: object) -> str:
    return sha256(canon(value)).hexdigest()


def _require_root(value: str, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value.lower() != value
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{field} must be lowercase sha256 hex")
    return value


def _require_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} required")
    return value


@dataclass(frozen=True)
class CanonicalReleasePublication:
    commit_receipt_root: str
    canonical_state_root: str
    release_root: str
    publication_root: str
    canonical_commit: bool
    published: bool
    publication_current: bool
    authority: str = D0

    def __post_init__(self) -> None:
        for field in (
            "commit_receipt_root",
            "canonical_state_root",
            "release_root",
            "publication_root",
        ):
            _require_root(getattr(self, field), field)
        for field in ("canonical_commit", "published", "publication_current"):
            if type(getattr(self, field)) is not bool:
                raise ValueError(f"{field} must be bool")
        if self.authority != D0:
            raise ValueError("publication cannot widen authority")


@dataclass(frozen=True)
class InstallationIntent:
    host_id: str
    host_incarnation: str
    source_incarnation_root: str
    policy_root: str

    def __post_init__(self) -> None:
        _require_id(self.host_id, "host_id")
        _require_id(self.host_incarnation, "host_incarnation")
        _require_root(self.source_incarnation_root, "source_incarnation_root")
        _require_root(self.policy_root, "policy_root")


@dataclass(frozen=True)
class StableInstallation:
    release_root: str
    operation_root: str
    publication_root: str
    host_id: str
    host_incarnation: str
    source_incarnation_root: str


@dataclass(frozen=True)
class InstallAttempt:
    operation_root: str
    publication_root: str
    admission_root: str
    currentness_root: str
    actor_id: str
    installer_generation: int
    attempt_ordinal: int
    k27: tuple[int, int, int]

    def __post_init__(self) -> None:
        for field in (
            "operation_root",
            "publication_root",
            "admission_root",
            "currentness_root",
        ):
            _require_root(getattr(self, field), field)
        _require_id(self.actor_id, "actor_id")
        if self.installer_generation < 0 or self.attempt_ordinal < 0:
            raise ValueError("attempt counters must be nonnegative")
        if len(self.k27) != 3 or any(
            type(value) is not int or value < 0 or value > 26 for value in self.k27
        ):
            raise ValueError("k27 invalid")

    @property
    def claim_root(self) -> str:
        return root(
            {
                "schema": SCHEMA,
                "kind": "install_admission_claim",
                "operation_root": self.operation_root,
                "publication_root": self.publication_root,
                "admission_root": self.admission_root,
                "currentness_root": self.currentness_root,
                "actor_id": self.actor_id,
                "installer_generation": self.installer_generation,
                "attempt_ordinal": self.attempt_ordinal,
                "k27": list(self.k27),
            }
        )

    @property
    def attempt_root(self) -> str:
        return root(
            {
                "schema": SCHEMA,
                "kind": "install_attempt",
                "claim_root": self.claim_root,
                "authority": D0,
                "effect_authority": False,
                "gate10": False,
            }
        )


@dataclass(frozen=True)
class VerifiedInstallAdmission:
    claim_root: str
    operation_root: str
    publication_root: str
    currentness_root: str
    verifier_id: str
    subject_id: str
    authenticated: bool
    independent: bool
    issued_at_ms: int
    expires_at_ms: int
    authority: str = D0
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        for field in (
            "claim_root",
            "operation_root",
            "publication_root",
            "currentness_root",
        ):
            _require_root(getattr(self, field), field)
        _require_id(self.verifier_id, "verifier_id")
        _require_id(self.subject_id, "subject_id")
        if self.verifier_id == self.subject_id:
            raise ValueError("verifier must be independent by identity")
        if type(self.authenticated) is not bool or type(self.independent) is not bool:
            raise ValueError("admission booleans must be bool")
        if self.issued_at_ms < 0 or self.expires_at_ms < self.issued_at_ms:
            raise ValueError("admission validity window invalid")
        if self.authority != D0 or self.effect_authority or self.gate10:
            raise ValueError("verified admission cannot widen authority")

    @property
    def proof_root(self) -> str:
        return root(
            {
                "schema": SCHEMA,
                "kind": "verified_install_admission",
                "claim_root": self.claim_root,
                "operation_root": self.operation_root,
                "publication_root": self.publication_root,
                "currentness_root": self.currentness_root,
                "verifier_id": self.verifier_id,
                "subject_id": self.subject_id,
                "authenticated": self.authenticated,
                "independent": self.independent,
                "issued_at_ms": self.issued_at_ms,
                "expires_at_ms": self.expires_at_ms,
                "authority": self.authority,
            }
        )


InstallAdmissionResolver = Callable[[InstallAttempt], VerifiedInstallAdmission | None]


class InstallState(str, Enum):
    PREPARED = "PREPARED"
    ATTEMPT_DURABLE = "ATTEMPT_DURABLE"
    CONFIRMED_NOT_APPLIED = "CONFIRMED_NOT_APPLIED"
    APPLY_OBSERVED = "APPLY_OBSERVED"
    RECONCILE_REQUIRED = "RECONCILE_REQUIRED"
    ATTESTATION_PENDING = "ATTESTATION_PENDING"
    CURRENT_EXACT_HOST_OBSERVED = "CURRENT_EXACT_HOST_OBSERVED"


class RecoveryAction(str, Enum):
    START_FRESH_ATTEMPT = "START_FRESH_ATTEMPT"
    RECONCILE_BEFORE_RETRY = "RECONCILE_BEFORE_RETRY"
    MEASURE_ONLY_NEVER_REAPPLY = "MEASURE_ONLY_NEVER_REAPPLY"
    DONE = "DONE"


def compile_installation(
    manifest: RuntimeReleaseManifest,
    publication: CanonicalReleasePublication,
    intent: InstallationIntent,
) -> StableInstallation:
    manifest.validate()
    if not publication.canonical_commit:
        raise ValueError("CANONICAL_COMMIT_REQUIRED")
    if not publication.published or not publication.publication_current:
        raise ValueError("CURRENT_PUBLICATION_REQUIRED")
    if publication.release_root != manifest.release_root:
        raise ValueError("PUBLICATION_RELEASE_ROOT_DIVERGED")
    operation_root = root(
        {
            "schema": SCHEMA,
            "kind": "stable_installation",
            "commit_receipt_root": publication.commit_receipt_root,
            "canonical_state_root": publication.canonical_state_root,
            "release_root": manifest.release_root,
            "canonical_operation_root": manifest.canonical_operation_root,
            "host_id": intent.host_id,
            "host_incarnation": intent.host_incarnation,
            "source_incarnation_root": intent.source_incarnation_root,
            "policy_root": intent.policy_root,
        }
    )
    return StableInstallation(
        release_root=manifest.release_root,
        operation_root=operation_root,
        publication_root=publication.publication_root,
        host_id=intent.host_id,
        host_incarnation=intent.host_incarnation,
        source_incarnation_root=intent.source_incarnation_root,
    )


def _validate_admission(
    attempt: InstallAttempt,
    evidence: VerifiedInstallAdmission | None,
    now_ms: int,
) -> str | None:
    if evidence is None:
        return "HOLD_ADMISSION_UNVERIFIED"
    if evidence.claim_root != attempt.claim_root:
        return "HOLD_ADMISSION_CLAIM_DIVERGED"
    if evidence.operation_root != attempt.operation_root:
        return "HOLD_ADMISSION_OPERATION_DIVERGED"
    if evidence.publication_root != attempt.publication_root:
        return "HOLD_ADMISSION_PUBLICATION_DIVERGED"
    if evidence.currentness_root != attempt.currentness_root:
        return "HOLD_ADMISSION_CURRENTNESS_DIVERGED"
    if not evidence.authenticated or not evidence.independent:
        return "HOLD_ADMISSION_NOT_AUTHENTICATED_INDEPENDENT"
    if now_ms < evidence.issued_at_ms or now_ms > evidence.expires_at_ms:
        return "HOLD_ADMISSION_NOT_CURRENT_AT_USE"
    return None


class InstallationJournal:
    def __init__(self, path: str) -> None:
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS install_tx(
                operation_root TEXT PRIMARY KEY,
                release_root TEXT NOT NULL,
                host_id TEXT NOT NULL,
                host_incarnation TEXT NOT NULL,
                source_incarnation_root TEXT NOT NULL,
                publication_root TEXT NOT NULL,
                state TEXT NOT NULL,
                attempt_root TEXT,
                admission_proof_root TEXT,
                apply_receipt_root TEXT,
                attestation_root TEXT,
                reason TEXT
            )
            """
        )
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def prepare(self, installation: StableInstallation) -> tuple[str | None, ...]:
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO install_tx VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    installation.operation_root,
                    installation.release_root,
                    installation.host_id,
                    installation.host_incarnation,
                    installation.source_incarnation_root,
                    installation.publication_root,
                    InstallState.PREPARED.value,
                    None,
                    None,
                    None,
                    None,
                    None,
                ),
            )
            state, publication_root = self.db.execute(
                "SELECT state,publication_root FROM install_tx WHERE operation_root=?",
                (installation.operation_root,),
            ).fetchone()
            if (
                publication_root != installation.publication_root
                and InstallState(state)
                in (InstallState.PREPARED, InstallState.CONFIRMED_NOT_APPLIED)
            ):
                self.db.execute(
                    "UPDATE install_tx SET publication_root=?,reason=? WHERE operation_root=?",
                    (
                        installation.publication_root,
                        "PUBLICATION_REBOUND_BEFORE_ATTEMPT",
                        installation.operation_root,
                    ),
                )
        return self.status(installation.operation_root)

    def status(self, operation_root: str) -> tuple[str | None, ...]:
        row = self.db.execute(
            """
            SELECT state,attempt_root,admission_proof_root,
                   apply_receipt_root,attestation_root,reason
            FROM install_tx WHERE operation_root=?
            """,
            (operation_root,),
        ).fetchone()
        if row is None:
            raise KeyError(operation_root)
        return row

    def begin_attempt(
        self,
        installation: StableInstallation,
        attempt: InstallAttempt,
        resolve_admission: InstallAdmissionResolver,
        *,
        now_ms: int,
    ) -> str:
        if attempt.operation_root != installation.operation_root:
            return "HOLD_OPERATION_MOVED"
        if attempt.publication_root != installation.publication_root:
            return "HOLD_PUBLICATION_ADMISSION_MOVED"
        evidence = resolve_admission(attempt)
        admission_error = _validate_admission(attempt, evidence, now_ms)
        if admission_error is not None:
            return admission_error
        assert evidence is not None
        with self.db:
            row = self.db.execute(
                "SELECT state,publication_root FROM install_tx WHERE operation_root=?",
                (installation.operation_root,),
            ).fetchone()
            if row is None:
                raise KeyError(installation.operation_root)
            state = InstallState(row[0])
            if row[1] != attempt.publication_root:
                return "HOLD_PUBLICATION_JOURNAL_DIVERGED"
            if state in (
                InstallState.APPLY_OBSERVED,
                InstallState.RECONCILE_REQUIRED,
                InstallState.ATTESTATION_PENDING,
                InstallState.CURRENT_EXACT_HOST_OBSERVED,
            ):
                return "HOLD_NEVER_BLIND_REAPPLY"
            if state == InstallState.ATTEMPT_DURABLE:
                return "HOLD_RECONCILE_EXISTING_ATTEMPT"
            self.db.execute(
                """
                UPDATE install_tx
                SET state=?,attempt_root=?,admission_proof_root=?,reason=NULL
                WHERE operation_root=?
                """,
                (
                    InstallState.ATTEMPT_DURABLE.value,
                    attempt.attempt_root,
                    evidence.proof_root,
                    installation.operation_root,
                ),
            )
        return attempt.attempt_root

    def observe_apply(
        self,
        operation_root: str,
        attempt_root: str,
        outcome: str,
        apply_receipt_root: str | None = None,
    ) -> str:
        if outcome not in {"APPLIED", "NOT_APPLIED", "UNKNOWN"}:
            raise ValueError("invalid outcome")
        if apply_receipt_root is not None:
            _require_root(apply_receipt_root, "apply_receipt_root")
        with self.db:
            state, stored_attempt = self.db.execute(
                "SELECT state,attempt_root FROM install_tx WHERE operation_root=?",
                (operation_root,),
            ).fetchone()
            if (
                stored_attempt != attempt_root
                or InstallState(state) != InstallState.ATTEMPT_DURABLE
            ):
                return "HOLD_ATTEMPT_NOT_CURRENT"
            if outcome == "NOT_APPLIED":
                next_state = InstallState.CONFIRMED_NOT_APPLIED
                reason = "INDEPENDENTLY_CONFIRMED_NOT_APPLIED"
            elif outcome == "UNKNOWN":
                next_state = InstallState.RECONCILE_REQUIRED
                reason = "APPLY_OUTCOME_AMBIGUOUS"
            else:
                if apply_receipt_root is None:
                    return "HOLD_APPLY_RECEIPT_REQUIRED"
                next_state = InstallState.APPLY_OBSERVED
                reason = "LOCAL_APPLY_OBSERVED_NOT_CURRENTNESS"
            self.db.execute(
                """
                UPDATE install_tx
                SET state=?,apply_receipt_root=?,reason=?
                WHERE operation_root=?
                """,
                (next_state.value, apply_receipt_root, reason, operation_root),
            )
        return next_state.value

    def recovery_action(self, operation_root: str) -> RecoveryAction:
        state = InstallState(self.status(operation_root)[0])
        if state in (InstallState.PREPARED, InstallState.CONFIRMED_NOT_APPLIED):
            return RecoveryAction.START_FRESH_ATTEMPT
        if state in (InstallState.ATTEMPT_DURABLE, InstallState.RECONCILE_REQUIRED):
            return RecoveryAction.RECONCILE_BEFORE_RETRY
        if state in (InstallState.APPLY_OBSERVED, InstallState.ATTESTATION_PENDING):
            return RecoveryAction.MEASURE_ONLY_NEVER_REAPPLY
        return RecoveryAction.DONE

    def bind_attestation(
        self,
        installation: StableInstallation,
        manifest: RuntimeReleaseManifest,
        measurement: HostMeasurement | None,
        evidence: MeasurementEvidence | None,
        *,
        owner_reported_updated: bool | None,
        now_ms: int,
    ):
        state = InstallState(self.status(installation.operation_root)[0])
        if state not in (
            InstallState.APPLY_OBSERVED,
            InstallState.RECONCILE_REQUIRED,
            InstallState.ATTESTATION_PENDING,
        ):
            return "HOLD_INSTALL_NOT_ATTESTABLE"
        if manifest.release_root != installation.release_root:
            return "HOLD_RELEASE_MANIFEST_MOVED"
        if measurement is not None:
            if (
                measurement.host_id != installation.host_id
                or measurement.host_incarnation != installation.host_incarnation
            ):
                return "HOLD_TARGET_HOST_INCARNATION_DIVERGED"
            if measurement.source_incarnation_root != installation.source_incarnation_root:
                return "HOLD_SOURCE_INCARNATION_DIVERGED"
        attestation = attest_runtime(
            manifest,
            owner_reported_updated=owner_reported_updated,
            measurement=measurement,
            evidence=evidence,
            now_ms=now_ms,
        )
        attestation_root = root(attestation.to_dict())
        with self.db:
            if attestation.disposition == RuntimeDisposition.CURRENT_EXACT_HOST_OBSERVED:
                self.db.execute(
                    """
                    UPDATE install_tx
                    SET state=?,attestation_root=?,reason=NULL
                    WHERE operation_root=?
                    """,
                    (
                        InstallState.CURRENT_EXACT_HOST_OBSERVED.value,
                        attestation_root,
                        installation.operation_root,
                    ),
                )
            else:
                self.db.execute(
                    """
                    UPDATE install_tx
                    SET state=?,attestation_root=?,reason=?
                    WHERE operation_root=?
                    """,
                    (
                        InstallState.ATTESTATION_PENDING.value,
                        attestation_root,
                        attestation.disposition.value,
                        installation.operation_root,
                    ),
                )
        return attestation
