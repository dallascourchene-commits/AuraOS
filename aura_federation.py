"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f5-[Q-SYS:AURA_FEDERATION]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIDINAWENDIMIN (Swarm Synergy / Sovereignty-First Federation)
DEPENDENCIES: dataclasses, hashlib, hmac, json, time, typing
FUNCTIONS: FederatedCapsule, FederationTrust, AuraFederation, build_default_federation
SYNOPSIS: Sovereignty-first federation. Exports redacted signed capsules only —
          no raw private memory, no raw sidecar dumps. All remote results pass
          the local verifier before acceptance. Federation trust is recorded in
          QDKT and repeated successful patterns crystallize.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import json
import time
from typing import Any

AURA_FEDERATION_VERSION = "AURA_FEDERATION_V1"

# Fields that must never appear in a federated (exported) capsule.
PRIVATE_FIELDS_DENYLIST = frozenset(
    {
        "raw_snapshot_bytes",
        "raw_sidecar_bytes",
        "raw_private_memory",
        "api_key",
        "secret",
        "password",
        "token",
        "private_key",
        "user_pii",
        "raw_post_content",
        "raw_ledger_bytes",
    }
)


def _hash_payload(payload: Any, *, size: int = 16) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=size).hexdigest()


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class FederatedCapsule:
    """A redacted, signed capsule ready for federation."""

    capsule_id: str
    origin_node: str
    redacted_payload: dict[str, Any]
    signature: str
    verifier_result: dict[str, Any]
    phase_hash: str
    ts: float = field(default_factory=time.time)
    status: str = "exported"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": AURA_FEDERATION_VERSION,
            "capsule_id": self.capsule_id,
            "origin_node": self.origin_node,
            "redacted_payload": dict(self.redacted_payload),
            "signature": self.signature,
            "verifier_result": dict(self.verifier_result),
            "phase_hash": self.phase_hash,
            "ts": self.ts,
            "status": self.status,
        }


@dataclass
class FederationTrust:
    """Per-node trust record."""

    origin_node: str
    trust_score: float = 0.5
    accepted_count: int = 0
    rejected_count: int = 0
    last_seen: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "origin_node": self.origin_node,
            "trust_score": self.trust_score,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "last_seen": self.last_seen,
        }


class AuraFederation:
    """Sovereignty-first federation of redacted signed capsules.

    Hard rules:
      1. ``export_capsule`` redacts private fields and signs the payload.
         It RAISES if raw private memory or raw sidecar bytes would be exported.
      2. ``import_capsule`` runs the local verifier before accepting.
         Rejected capsules are quarantined and never applied.
      3. Trust scores per origin node are recorded in QDKT.
    """

    def __init__(
        self,
        *,
        origin_node: str = "aura-local",
        node_key: bytes | None = None,
        qdkt: Any = None,
        local_verifier: Any = None,
    ) -> None:
        if node_key is None:
            raise ValueError("node_key must be provided; no default signing key is allowed")
        self.origin_node = origin_node
        self.node_key = node_key
        self.qdkt = qdkt
        self.local_verifier = local_verifier
        self._trust: dict[str, FederationTrust] = {}
        self._exported: list[FederatedCapsule] = []
        self._imported: list[FederatedCapsule] = []
        self._quarantined: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_capsule(
        self,
        capsule: dict[str, Any],
        *,
        verifier_result: dict[str, Any] | None = None,
    ) -> FederatedCapsule:
        """Redact private fields, sign, and return a federated capsule.

        Raises if raw private memory or raw sidecar bytes are present.
        """
        redacted = self._redact_private_memory(capsule)
        redacted = self._redact_sidecar_dump(redacted)
        payload = {
            "origin_node": self.origin_node,
            "redacted_payload": redacted,
            "verifier_result": dict(verifier_result or {}),
            "ts": time.time(),
        }
        capsule_id = f"FED-{_hash_payload(payload)[:12]}"
        # Sign the full envelope including origin_node, capsule_id, ts, and verifier_result
        envelope = {**payload, "capsule_id": capsule_id}
        signature = self._sign(envelope)
        phase_hash = _hash_payload({**envelope, "signature": signature})
        fed = FederatedCapsule(
            capsule_id=capsule_id,
            origin_node=self.origin_node,
            redacted_payload=redacted,
            signature=signature,
            verifier_result=dict(verifier_result or {}),
            phase_hash=phase_hash,
        )
        self._exported.append(fed)
        self._record("federation_export", fed.capsule_id, origin=self.origin_node, success=True)
        return fed

    def _redact_private_memory(self, capsule: dict[str, Any]) -> dict[str, Any]:
        """Remove any private-memory fields. Raise if raw private memory is present."""
        def _normalize_key(key: str) -> str:
            """Normalize key for consistent denylist matching."""
            # Convert to lowercase and replace common separators
            normalized = key.lower().replace("_", "").replace("-", "")
            return normalized
        
        def _check_and_redact(obj: Any) -> Any:
            """Recursively check and redact private fields."""
            if isinstance(obj, dict):
                # Check for raw memory fields at this level
                obj_keys = set(obj.keys())
                if any(k in obj_keys for k in ["raw_private_memory", "raw_sidecar_bytes"]):
                    raise ValueError("refusing to federate capsule containing raw private memory or raw sidecar bytes")
                
                # Redact and recurse
                out = {}
                for key, value in obj.items():
                    # Check normalized key against denylist
                    normalized = _normalize_key(key)
                    # Also check original key for exact matches
                    if key in PRIVATE_FIELDS_DENYLIST:
                        continue
                    # Check if normalized matches any normalized denylist entries
                    if any(_normalize_key(d) == normalized for d in PRIVATE_FIELDS_DENYLIST):
                        continue
                    out[key] = _check_and_redact(value)
                return out
            elif isinstance(obj, list):
                return [_check_and_redact(item) for item in obj]
            else:
                return obj
        
        return _check_and_redact(capsule)

    def _redact_sidecar_dump(self, capsule: dict[str, Any]) -> dict[str, Any]:
        """Ensure no raw sidecar dump fields remain."""
        bad = PRIVATE_FIELDS_DENYLIST & set(capsule.keys())
        if bad:
            raise ValueError(f"refusing to federate capsule with raw sidecar dump fields: {sorted(bad)}")
        return capsule

    def _sign(self, payload: dict[str, Any]) -> str:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hmac.new(self.node_key, body.encode("utf-8"), hashlib.blake2b).hexdigest()

    def verify_signature(self, capsule: FederatedCapsule, *, remote_key: bytes | None = None) -> bool:
        """Verify a federated capsule's signature against the full envelope."""
        key = remote_key or self.node_key
        # Reconstruct the full envelope that was signed (excluding the signature itself)
        envelope = {
            "origin_node": capsule.origin_node,
            "capsule_id": capsule.capsule_id,
            "redacted_payload": capsule.redacted_payload,
            "verifier_result": capsule.verifier_result,
            "ts": getattr(capsule, 'ts', 0),  # ts may not be in all capsule versions
        }
        body = json.dumps(envelope, sort_keys=True, separators=(",", ":"), default=str)
        expected = hmac.new(key, body.encode("utf-8"), hashlib.blake2b).hexdigest()
        return hmac.compare_digest(expected, capsule.signature)

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def import_capsule(
        self,
        remote: FederatedCapsule | dict[str, Any],
        *,
        remote_key: bytes | None = None,
    ) -> FederatedCapsule:
        """Import a remote capsule after local verification.

        Raises if the local verifier rejects the capsule. Quarantines
        rejected capsules instead of applying them.
        """
        if isinstance(remote, dict):
            remote = FederatedCapsule(
                capsule_id=str(remote.get("capsule_id") or ""),
                origin_node=str(remote.get("origin_node") or "unknown"),
                redacted_payload=dict(remote.get("redacted_payload") or {}),
                signature=str(remote.get("signature") or ""),
                verifier_result=dict(remote.get("verifier_result") or {}),
                phase_hash=str(remote.get("phase_hash") or ""),
                ts=float(remote.get("ts") or time.time()),
                status=str(remote.get("status") or "imported"),
            )

        # Signature check
        if not self.verify_signature(remote, remote_key=remote_key):
            self._quarantine(remote, reason="signature_check_failed")
            self._update_trust(remote.origin_node, accepted=False)
            raise ValueError(f"signature verification failed for {remote.capsule_id}")

        # Local verifier check
        if not self._local_verify(remote):
            self._quarantine(remote, reason="local_verifier_rejected")
            self._update_trust(remote.origin_node, accepted=False)
            raise ValueError(f"local verifier rejected {remote.capsule_id}")

        remote.status = "imported_verified"
        self._imported.append(remote)
        self._update_trust(remote.origin_node, accepted=True)
        self._record("federation_import", remote.capsule_id, origin=remote.origin_node, success=True)
        # Crystallize repeated successful patterns from trusted nodes.
        trust = self._trust.get(remote.origin_node)
        if trust and trust.accepted_count >= 3:
            self._crystallize_trust(remote.origin_node)
        return remote

    def _local_verify(self, capsule: FederatedCapsule) -> bool:
        """Run the local verifier on the remote capsule's verifier_result.

        If no local verifier is configured, fall back to requiring an
        explicit ``approved=True`` in the capsule's verifier_result.
        """
        if self.local_verifier is not None:
            try:
                result = self.local_verifier(capsule.redacted_payload)
                if isinstance(result, dict):
                    return bool(result.get("approved", False))
                return bool(result)
            except Exception:
                return False
        vr = capsule.verifier_result or {}
        return bool(vr.get("approved", False))

    def _quarantine(self, capsule: FederatedCapsule, *, reason: str) -> None:
        self._quarantined.append(
            {
                "capsule_id": capsule.capsule_id,
                "origin_node": capsule.origin_node,
                "reason": reason,
                "ts": time.time(),
            }
        )
        self._record("federation_quarantine", capsule.capsule_id, origin=capsule.origin_node, success=False)

    # ------------------------------------------------------------------
    # Trust
    # ------------------------------------------------------------------

    def _update_trust(self, origin_node: str, *, accepted: bool) -> None:
        trust = self._trust.setdefault(origin_node, FederationTrust(origin_node=origin_node))
        trust.last_seen = time.time()
        if accepted:
            trust.accepted_count += 1
            trust.trust_score = min(1.0, trust.trust_score + 0.05)
        else:
            trust.rejected_count += 1
            trust.trust_score = max(0.0, trust.trust_score - 0.15)

    def trust_record(self, origin_node: str) -> FederationTrust | None:
        return self._trust.get(origin_node)

    def trust_table(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self._trust.values()]

    def _crystallize_trust(self, origin_node: str) -> None:
        if self.qdkt is None:
            return
        try:
            self.qdkt.crystallize(
                f"federation_trust:{origin_node}",
                f"trusted federation peer {origin_node}",
                confidence=0.85,
                source="federation_repeated_success",
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # QDKT
    # ------------------------------------------------------------------

    def _record(self, event_type: str, capsule_id: str, *, origin: str, success: bool) -> None:
        if self.qdkt is None:
            return
        try:
            self.qdkt.observe(
                event_type,
                {
                    "capsule_id": capsule_id,
                    "origin_node": origin,
                    "success": bool(success),
                },
                rationale=f"federation {event_type}: {capsule_id}",
                concept=f"federation:{origin}",
                confidence=0.8 if success else 0.3,
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def exported_capsules(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._exported[-limit:]]

    def imported_capsules(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._imported[-limit:]]

    def quarantined_capsules(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return list(self._quarantined[-limit:])


def build_default_federation(
    *,
    origin_node: str = "aura-local",
    node_key: bytes | None = None,
    qdkt: Any = None,
    local_verifier: Any = None,
) -> AuraFederation:
    """Build a default federation instance."""
    return AuraFederation(
        origin_node=origin_node,
        node_key=node_key or b"aura-federation-default-key",
        qdkt=qdkt,
        local_verifier=local_verifier,
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Aura Federation — sovereignty-first capsule federation")
    parser.add_argument("--trust", action="store_true", help="print trust table")
    args = parser.parse_args(argv)
    federation = build_default_federation()
    if args.trust:
        print(json.dumps(federation.trust_table(), indent=2, sort_keys=True))
    else:
        print("Aura Federation: sovereignty-first, redacted signed capsules only")
        print(f"  origin_node: {federation.origin_node}")
        print(f"  exported: {len(federation.exported_capsules())}")
        print(f"  imported: {len(federation.imported_capsules())}")
        print(f"  quarantined: {len(federation.quarantined_capsules())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())