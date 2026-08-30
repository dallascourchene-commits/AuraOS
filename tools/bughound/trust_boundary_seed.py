"""Local trust-boundary seed for BugHound identity/scope drift detection.

D0 / no external target effect. This seed is derived from a public-source
architecture pattern and models an invariant, not a claimed vulnerability.
It never imports or calls the source project.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
import re

SCHEMA = "BugHoundTrustBoundarySeedV1"
_MEMANTO_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class ScopeDisposition(str, Enum):
    SCOPE_MATCHED = "SCOPE_MATCHED"
    SIGNED_PERSISTED_AGENT_MISMATCH = "SIGNED_PERSISTED_AGENT_MISMATCH"
    PERSISTED_NAMESPACE_DRIFT = "PERSISTED_NAMESPACE_DRIFT"


def expected_agent_namespace(agent_id: str) -> str:
    if not isinstance(agent_id, str) or not agent_id:
        raise ValueError("agent_id required")
    return f"memanto_agent_{agent_id}"


@dataclass(frozen=True)
class IdentityScopeObservationV1:
    signed_agent_id: str
    persisted_agent_id: str
    persisted_namespace: str
    source_repository: str
    source_generation: str
    source_paths: tuple[str, ...]
    external_effect: bool = False
    vulnerability_proven: bool = False
    authority: bool = False
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        if not self.signed_agent_id or not self.persisted_agent_id:
            raise ValueError("agent identity required")
        if not self.persisted_namespace:
            raise ValueError("namespace required")
        if self.source_repository != "moorcheh-ai/memanto":
            raise ValueError("unexpected source repository")
        if not _MEMANTO_COMMIT_RE.fullmatch(self.source_generation):
            raise ValueError("immutable source generation required")
        if not self.source_paths:
            raise ValueError("source paths required")
        if self.external_effect or self.vulnerability_proven or self.authority:
            raise ValueError("effect/authority widening forbidden")

    @property
    def expected_namespace(self) -> str:
        return expected_agent_namespace(self.persisted_agent_id)

    @property
    def disposition(self) -> ScopeDisposition:
        if self.signed_agent_id != self.persisted_agent_id:
            return ScopeDisposition.SIGNED_PERSISTED_AGENT_MISMATCH
        if self.persisted_namespace != self.expected_namespace:
            return ScopeDisposition.PERSISTED_NAMESPACE_DRIFT
        return ScopeDisposition.SCOPE_MATCHED

    @property
    def receipt_digest(self) -> str:
        body = asdict(self)
        body["disposition"] = self.disposition.value
        body["expected_namespace"] = self.expected_namespace
        raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        return hashlib.sha256(b"AURA_BUGHOUND_TRUST_BOUNDARY_SEED_V1\0" + raw).hexdigest()


def modeled_current_validation_accepts(
    *,
    signed_agent_id: str,
    persisted_agent_id: str,
    persisted_session_id: str,
    signed_session_id: str,
    persisted_active: bool,
) -> bool:
    """Model only the public-source identity checks relevant to the seed.

    This intentionally does not claim byte-for-byte equivalence to the target.
    It isolates the observed predicate: signed/persisted agent identity, session
    identity, and active state are checked while namespace equality is a
    separate invariant.
    """
    return (
        signed_agent_id == persisted_agent_id
        and signed_session_id == persisted_session_id
        and persisted_active
    )


def memanto_namespace_drift_seed() -> IdentityScopeObservationV1:
    """Return the public-source-bound local falsification candidate."""
    return IdentityScopeObservationV1(
        signed_agent_id="research_agent",
        persisted_agent_id="research_agent",
        persisted_namespace="memanto_agent_other_scope",
        source_repository="moorcheh-ai/memanto",
        source_generation="3bfde8e4eacea1a78b028f7f672ac285afc57b59",
        source_paths=(
            "memanto/app/core.py",
            "memanto/app/models/session.py",
            "memanto/app/services/session_service.py",
            "memanto/app/routes/auth_deps.py",
            "memanto/app/routes/memory.py",
        ),
    )
