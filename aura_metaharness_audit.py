"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: json, __future__, sys, re, argparse, typing, os, time, pathlib, dataclasses, hashlib
FUNCTIONS: _get_store_value, _hash_payload, _clamp01, audit_metaharness, main, to_dict, overall_score, __init__, audit, _score_verifier_coverage, _score_sidecar_truth_separation, _score_qdkt_coverage, _score_dream_usefulness_coverage, _score_stale_data_risk, _count_unresolved_boundary_contracts, _score_secret_exposure, _score_plugin_permission_risk, _record, _has_raw_fields
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any

AURA_METAHARNESS_AUDIT_VERSION = "AURA_METAHARNESS_AUDIT_V1"
AUDIT_LEDGER_PATH = Path("Aura_Memory") / "metaharness_audit.jsonl"

# Secret-like patterns we scan for in proposals/exports.
_SECRET_PATTERNS = [
    re.compile(r"(?i)api[_-]?key"),
    re.compile(r"(?i)secret"),
    re.compile(r"(?i)password"),
    re.compile(r"(?i)token"),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{12,}"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
]


def _get_store_value(store: Any, key: str, default: Any = None) -> Any:
    """Get a value from arena_store, handling both object attributes and dict keys."""
    if isinstance(store, dict):
        return store.get(key, default)
    return getattr(store, key, default)


def _hash_payload(payload: Any, *, size: int = 16) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=size).hexdigest()


def _clamp01(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, number))


@dataclass
class MetaHarnessAudit:
    """Scored audit report across the eight meta-harness dimensions."""

    audit_version: str
    audit_id: str
    ts: float
    verifier_coverage: float
    sidecar_truth_separation: float
    qdkt_coverage: float
    dream_usefulness_coverage: float
    stale_data_risk: float  # 1.0 = no stale risk, 0.0 = high stale risk
    unresolved_boundary_contracts: int
    secret_exposure: float  # 1.0 = no secrets found, 0.0 = secrets found
    plugin_permission_risk: float  # 1.0 = low risk, 0.0 = high risk
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    phase_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        boundary_contracts_score = 0.0 if self.unresolved_boundary_contracts > 0 else 1.0
        return {
            "audit_version": self.audit_version,
            "audit_id": self.audit_id,
            "ts": self.ts,
            "scores": {
                "verifier_coverage": self.verifier_coverage,
                "sidecar_truth_separation": self.sidecar_truth_separation,
                "qdkt_coverage": self.qdkt_coverage,
                "dream_usefulness_coverage": self.dream_usefulness_coverage,
                "stale_data_risk": self.stale_data_risk,
                "secret_exposure": self.secret_exposure,
                "plugin_permission_risk": self.plugin_permission_risk,
                "boundary_contracts": boundary_contracts_score,
            },
            "unresolved_boundary_contracts": self.unresolved_boundary_contracts,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "phase_hash": self.phase_hash,
        }

    @property
    def overall_score(self) -> float:
        boundary_contracts_score = 0.0 if self.unresolved_boundary_contracts > 0 else 1.0
        scores = [
            self.verifier_coverage,
            self.sidecar_truth_separation,
            self.qdkt_coverage,
            self.dream_usefulness_coverage,
            self.stale_data_risk,
            self.secret_exposure,
            self.plugin_permission_risk,
            boundary_contracts_score,
        ]
        return round(sum(scores) / len(scores), 4) if scores else 0.0


class AuraMetaHarnessAuditor:
    """Audits the meta-harness layer across eight dimensions.

    Each scorer is deterministic and operates on the gateway, registry,
    workers, federation, and QDKT instances passed in. The auditor never
    mutates production; it only reads and scores.
    """

    def __init__(self, *, qdkt: Any = None, ledger_path: str | Path = AUDIT_LEDGER_PATH) -> None:
        self.qdkt = qdkt
        self.ledger_path = Path(ledger_path)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def audit(
        self,
        *,
        gateway: Any = None,
        registry: Any = None,
        supervisor: Any = None,
        federation: Any = None,
        arena_store: Any = None,
        sidecar: Any = None,
        proposals: list[dict[str, Any]] | None = None,
        exports: list[dict[str, Any]] | None = None,
    ) -> MetaHarnessAudit:
        ts = time.time()
        arena_store = arena_store or {}
        proposals = proposals or []
        exports = exports or []

        verifier_coverage = self._score_verifier_coverage(arena_store, gateway)
        sidecar_separation = self._score_sidecar_truth_separation(arena_store, sidecar, exports)
        qdkt_coverage = self._score_qdkt_coverage(gateway, registry, supervisor, federation)
        dream_coverage = self._score_dream_usefulness_coverage(supervisor, arena_store)
        stale_risk = self._score_stale_data_risk(sidecar, arena_store)
        unresolved_bc = self._count_unresolved_boundary_contracts(arena_store)
        secret_exposure = self._score_secret_exposure(proposals, exports)
        plugin_risk = self._score_plugin_permission_risk(registry)

        blockers: list[str] = []
        warnings: list[str] = []
        if verifier_coverage < 0.5:
            blockers.append(f"low_verifier_coverage={verifier_coverage:.2f}")
        if sidecar_separation < 0.5:
            blockers.append(f"weak_sidecar_truth_separation={sidecar_separation:.2f}")
        if secret_exposure < 1.0:
            blockers.append(f"secret_exposure_detected={secret_exposure:.2f}")
        if plugin_risk < 0.5:
            warnings.append(f"elevated_plugin_permission_risk={plugin_risk:.2f}")
        if stale_risk < 0.5:
            warnings.append(f"stale_data_risk={stale_risk:.2f}")
        if unresolved_bc > 0:
            warnings.append(f"unresolved_boundary_contracts={unresolved_bc}")

        payload = {
            "ts": ts,
            "verifier_coverage": verifier_coverage,
            "sidecar_truth_separation": sidecar_separation,
            "qdkt_coverage": qdkt_coverage,
            "dream_usefulness_coverage": dream_coverage,
            "stale_data_risk": stale_risk,
            "unresolved_boundary_contracts": unresolved_bc,
            "secret_exposure": secret_exposure,
            "plugin_permission_risk": plugin_risk,
        }
        audit_id = f"AUDIT-{_hash_payload(payload)[:12]}"
        phase_hash = _hash_payload({**payload, "audit_id": audit_id})
        audit = MetaHarnessAudit(
            audit_version=AURA_METAHARNESS_AUDIT_VERSION,
            audit_id=audit_id,
            ts=ts,
            verifier_coverage=verifier_coverage,
            sidecar_truth_separation=sidecar_separation,
            qdkt_coverage=qdkt_coverage,
            dream_usefulness_coverage=dream_coverage,
            stale_data_risk=stale_risk,
            unresolved_boundary_contracts=unresolved_bc,
            secret_exposure=secret_exposure,
            plugin_permission_risk=plugin_risk,
            blockers=blockers,
            warnings=warnings,
            phase_hash=phase_hash,
        )
        self._record(audit)
        return audit

    # ------------------------------------------------------------------
    # Dimension scorers
    # ------------------------------------------------------------------

    def _score_verifier_coverage(self, arena_store: Any, gateway: Any) -> float:
        """Fraction of staged capsules with verifier gates."""
        capsules = _get_store_value(arena_store, "action_capsules", []) or []
        ledger = _get_store_value(arena_store, "verification_ledger", []) or []
        if not capsules:
            return 1.0  # no capsules => vacuously covered
        covered = {
            entry.get("capsule_id")
            for entry in ledger
            if isinstance(entry, dict) and entry.get("capsule_id")
        }
        with_gate = 0
        total = 0
        for capsule in capsules:
            if not isinstance(capsule, dict):
                continue
            total += 1
            cid = capsule.get("capsule_id")
            if cid in covered or capsule.get("acceptance_checks"):
                with_gate += 1
        return _clamp01(with_gate / total) if total else 1.0

    def _score_sidecar_truth_separation(self, arena_store: Any, sidecar: Any, exports: list[dict[str, Any]]) -> float:
        """Fraction of displayed values backed by sidecar records (no raw dumps)."""
        # Penalize any export that looks like a raw sidecar dump.
        raw_dump_penalty = 0.0
        
        def _has_raw_fields(obj: Any) -> bool:
            """Recursively check if an object contains raw dump fields."""
            if isinstance(obj, dict):
                keys = set(obj.keys())
                if "raw_snapshot_bytes" in keys or "raw_sidecar_bytes" in keys:
                    return True
                # Recurse into nested dicts and lists
                for value in obj.values():
                    if _has_raw_fields(value):
                        return True
            elif isinstance(obj, list):
                for item in obj:
                    if _has_raw_fields(item):
                        return True
            return False
        
        for export in exports:
            if isinstance(export, dict):
                if _has_raw_fields(export):
                    raw_dump_penalty += 0.5
        
        # If a sidecar is present, reward having VSA pointers that resolve.
        resolution_rate = 1.0
        if sidecar is not None:
            try:
                total = sidecar.conn.execute("SELECT COUNT(*) FROM vsa_entity_pointers").fetchone()[0]
                if total:
                    resolved = sidecar.conn.execute(
                        "SELECT COUNT(*) FROM vsa_entity_pointers WHERE exact_lookup_required=1"
                    ).fetchone()[0]
                    resolution_rate = resolved / total
            except Exception:
                resolution_rate = 0.5
        return _clamp01(resolution_rate - raw_dump_penalty)

    def _score_qdkt_coverage(self, gateway: Any, registry: Any, supervisor: Any, federation: Any) -> float:
        """Fraction of meta-harness components that have a QDKT instance attached."""
        components = [gateway, registry, supervisor, federation]
        present = [c for c in components if c is not None and getattr(c, "qdkt", None) is not None]
        return _clamp01(len(present) / len(components)) if components else 0.0

    def _score_dream_usefulness_coverage(self, supervisor: Any, arena_store: Any) -> float:
        """Fraction of retrieval events that have been scored."""
        dream_scores = _get_store_value(arena_store, "dream_scores", []) or []
        if not dream_scores:
            return 0.5  # neutral when no retrieval events recorded
        scored = sum(1 for s in dream_scores if isinstance(s, dict) and s.get("usefulness_score") is not None)
        return _clamp01(scored / len(dream_scores)) if dream_scores else 0.5

    def _score_stale_data_risk(self, sidecar: Any, arena_store: Any) -> float:
        """1.0 = no stale risk; 0.0 = high stale risk."""
        if sidecar is None:
            return 0.5
        try:
            total = sidecar.conn.execute("SELECT COUNT(*) FROM price_observations").fetchone()[0]
            if not total:
                return 1.0
            stale = sidecar.conn.execute(
                "SELECT COUNT(*) FROM price_observations WHERE freshness_status IN ('stale','expired','unverified')"
            ).fetchone()[0]
            return _clamp01(1.0 - (stale / total))
        except Exception:
            return 0.5

    def _count_unresolved_boundary_contracts(self, arena_store: Any) -> int:
        contracts = _get_store_value(arena_store, "boundary_contracts", []) or []
        return sum(
            1
            for c in contracts
            if isinstance(c, dict) and c.get("status") == "placeholder"
        )

    def _score_secret_exposure(self, proposals: list[dict[str, Any]], exports: list[dict[str, Any]]) -> float:
        """1.0 = no secrets found; 0.0 = secrets found in proposals/exports."""
        blobs: list[str] = []
        for item in list(proposals) + list(exports):
            try:
                blobs.append(json.dumps(item, sort_keys=True, default=str))
            except Exception:
                continue
        for blob in blobs:
            for pattern in _SECRET_PATTERNS:
                if pattern.search(blob):
                    return 0.0
        return 1.0

    def _score_plugin_permission_risk(self, registry: Any) -> float:
        """1.0 = low risk; 0.0 = high risk (inverted from registry risk)."""
        if registry is None:
            return 0.5
        try:
            audit = registry.permission_audit()
            max_risk = float(audit.get("max_permission_risk", 0.5))
            return _clamp01(1.0 - max_risk)
        except Exception:
            return 0.5

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def _record(self, audit: MetaHarnessAudit) -> None:
        row = audit.to_dict()
        try:
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
            with self.ledger_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        except OSError as e:
            # Log and propagate ledger persistence errors
            import sys
            print(f"ERROR: Failed to write audit ledger to {self.ledger_path}: {e}", file=sys.stderr)
            raise
        if self.qdkt is not None:
            try:
                self.qdkt.observe(
                    "metaharness_audit",
                    {
                        "audit_id": audit.audit_id,
                        "overall_score": audit.overall_score,
                        "blockers": audit.blockers,
                        "warnings": audit.warnings,
                    },
                    rationale=f"meta-harness audit {audit.audit_id}",
                    concept=f"metaharness_audit:{audit.audit_id}",
                    confidence=audit.overall_score,
                )
            except Exception:
                pass


def audit_metaharness(
    *,
    gateway: Any = None,
    registry: Any = None,
    supervisor: Any = None,
    federation: Any = None,
    arena_store: Any = None,
    sidecar: Any = None,
    proposals: list[dict[str, Any]] | None = None,
    exports: list[dict[str, Any]] | None = None,
    qdkt: Any = None,
) -> MetaHarnessAudit:
    """Convenience function to run a meta-harness audit."""
    auditor = AuraMetaHarnessAuditor(qdkt=qdkt)
    return auditor.audit(
        gateway=gateway,
        registry=registry,
        supervisor=supervisor,
        federation=federation,
        arena_store=arena_store,
        sidecar=sidecar,
        proposals=proposals,
        exports=exports,
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Aura MetaHarness Audit — run a dry audit")
    parser.add_argument("--dry", action="store_true", help="run a dry audit with empty stores")
    args = parser.parse_args(argv)
    if args.dry:
        audit = audit_metaharness()
        print(json.dumps(audit.to_dict(), indent=2, sort_keys=True))
    else:
        print("Aura MetaHarness Auditor: use --dry for a dry audit run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())