from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib, json

class PersistenceMode(str, Enum):
    WINDOWS_SCHEDULED_RECONCILE = 'WINDOWS_SCHEDULED_RECONCILE'
    WINDOWS_USER_SESSION_GUARDIAN = 'WINDOWS_USER_SESSION_GUARDIAN'
    NONE = 'NONE'

@dataclass(frozen=True)
class LivenessEvidence:
    persistence_mode: PersistenceMode
    guardian_alive: bool | None
    wsl_wake_observed: bool | None
    consumer_progress: bool | None
    outbound_return_observed: bool | None
    provider_request_count: int | None
    currentness_exact: bool | None
    authority_bounded_d0: bool | None

@dataclass(frozen=True)
class LivenessDecision:
    disposition: str
    owner_session_liveness: bool
    boot_level_liveness: bool
    wake_from_stopped_proven: bool
    physical_acceptance: bool
    reasons: tuple[str, ...]


def classify(ev: LivenessEvidence) -> LivenessDecision:
    reasons: list[str] = []
    if ev.persistence_mode == PersistenceMode.NONE:
        reasons.append('NO_WINDOWS_PERSISTENCE_OWNER')
    if ev.guardian_alive is not True:
        reasons.append('WINDOWS_GUARDIAN_NOT_OBSERVED_ALIVE')
    if ev.wsl_wake_observed is not True:
        reasons.append('WAKE_FROM_STOPPED_NOT_OBSERVED')
    if ev.consumer_progress is not True:
        reasons.append('CONSUMER_PROGRESS_NOT_OBSERVED')
    if ev.outbound_return_observed is not True:
        reasons.append('OUTBOUND_RETURN_NOT_OBSERVED')
    if ev.provider_request_count != 0:
        reasons.append('PROVIDER_REQUEST_COUNT_NOT_ZERO')
    if ev.currentness_exact is not True:
        reasons.append('CURRENTNESS_NOT_EXACT')
    if ev.authority_bounded_d0 is not True:
        reasons.append('AUTHORITY_NOT_BOUNDED_D0')

    owner_session = ev.persistence_mode in {
        PersistenceMode.WINDOWS_SCHEDULED_RECONCILE,
        PersistenceMode.WINDOWS_USER_SESSION_GUARDIAN,
    }
    boot_level = False
    wake_proven = ev.wsl_wake_observed is True and ev.guardian_alive is True
    physical = owner_session and wake_proven and not reasons
    return LivenessDecision(
        disposition='PHYSICAL_ACCEPTANCE' if physical else 'HOLD_PHYSICAL_ACCEPTANCE',
        owner_session_liveness=owner_session,
        boot_level_liveness=boot_level,
        wake_from_stopped_proven=wake_proven,
        physical_acceptance=physical,
        reasons=tuple(reasons),
    )


def canonical_root(obj: object) -> str:
    body=json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=lambda x: x.value if isinstance(x, Enum) else x.__dict__)
    return hashlib.sha256(body.encode()).hexdigest()
