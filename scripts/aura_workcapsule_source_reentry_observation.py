#!/usr/bin/env python3
"""Project ASTGE source-currentness results into WorkCapsule re-entry observations.

The source-currentness owner remains ``aura_astge_anchor_hydration``.  This
module reruns that owner from raw inputs and projects its result against a prior
admitted WorkCapsule binding.  The purpose is narrow: preserve the exact
source-dependency identity when currentness is rejected without pretending the
observed stale bytes constitute a valid new SourceGeneration.

CURRENT receipts use the owner's admitted locator.  STALE receipts retain the
owner witness's expected file/source-generation/body identity plus the observed
mismatch evidence; the observed stale bytes are explicitly not generation-
bound.  UNKNOWN receipts with no source-body witness remain identity-unresolved
and are not guessed from path/anchor projections.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.aura_astge_anchor_hydration import (
    CURRENT,
    STALE,
    UNKNOWN,
    WITNESS_VERSION,
    compile_hydration_admission,
)
from scripts.aura_workcapsule_context_binding import verify_workcapsule_context_binding

VERSION = "AURA_WORKCAPSULE_SOURCE_REENTRY_OBSERVATION_V1"
SOURCE_DOMAIN = "SOURCE"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _identity(payload_without_identity: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": "WORKCAPSULE_SOURCE_REENTRY_OBSERVATION_V1_FULL_PAYLOAD_EXCEPT_RECEIPT_IDENTITY",
        "value": hashlib.sha256(_canonical_bytes(payload_without_identity)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def _witness_index(witness_manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if witness_manifest.get("version") != WITNESS_VERSION:
        raise ValueError("unsupported ASTGE source-body witness version")
    rows = witness_manifest.get("witnesses")
    if not isinstance(rows, list):
        raise ValueError("witness manifest requires a witnesses list")
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each source-body witness must be an object")
        anchor_id = str(row.get("anchor_id") or "").strip()
        if not anchor_id:
            raise ValueError("anchor_id must be nonempty")
        if anchor_id in out:
            raise ValueError(f"duplicate source-body witness for anchor {anchor_id!r}")
        out[anchor_id] = row
    return out


def _source_coordinate(generation: int) -> dict[str, Any]:
    return {"domain": SOURCE_DOMAIN, "value": int(generation)}


def _prior_key(row: dict[str, Any]) -> tuple[int, str]:
    return int(row["file_id"]), str(row["relative_path"])


def _owner_witness_for_receipts(
    receipts: list[dict[str, Any]], witness_by_anchor: dict[str, dict[str, Any]]
) -> dict[str, Any] | None:
    found = [witness_by_anchor[r["anchor_id"]] for r in receipts if r["anchor_id"] in witness_by_anchor]
    if not found:
        return None
    first = found[0]
    key = (
        first.get("file_id"),
        first.get("source_generation"),
        first.get("expected_byte_len"),
        str(first.get("expected_body_sha256") or "").lower(),
    )
    for row in found[1:]:
        other = (
            row.get("file_id"),
            row.get("source_generation"),
            row.get("expected_byte_len"),
            str(row.get("expected_body_sha256") or "").lower(),
        )
        if other != key:
            raise ValueError("same source path has conflicting source-body witness identities")
    return first


def compile_source_reentry_observations(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
) -> dict[str, Any]:
    """Compile source observations suitable for O8 without laundering rejection.

    Returned ``o7_source_witnesses`` contains only prior WorkCapsule dependency
    members whose source identity is independently available from the PR488
    witness plane.  Missing witness => UNKNOWN identity and therefore no guessed
    O7 witness; O8 will see the prior dependency as unresolved/missing.
    """
    violations = verify_workcapsule_context_binding(previous_binding)
    if violations:
        raise ValueError("previous_binding is not coherent: " + ",".join(violations))
    if previous_binding.get("context_admitted") is not True:
        raise ValueError("previous_binding must be an admitted CURRENT baseline")

    hydration = compile_hydration_admission(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
    )
    witness_by_anchor = _witness_index(witness_manifest)

    receipts_by_path: dict[str, list[dict[str, Any]]] = {}
    for receipt in hydration["anchor_receipts"]:
        receipts_by_path.setdefault(str(receipt["path"]), []).append(receipt)
    locator_by_path = {str(row["relative_path"]): row for row in hydration["source_locators_v1"]}

    prior_rows = previous_binding["source_witnesses"]
    prior_paths = {str(row["relative_path"]) for row in prior_rows}
    observations: list[dict[str, Any]] = []
    o7_witnesses: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    for prior in sorted(prior_rows, key=lambda row: _prior_key(row)):
        path = str(prior["relative_path"])
        path_receipts = receipts_by_path.get(path, [])
        if not path_receipts:
            unresolved.append(
                {
                    "prior_file_id": int(prior["file_id"]),
                    "relative_path": path,
                    "prior_source_generation_coordinate": _source_coordinate(int(prior["source_generation"])),
                    "currentness": UNKNOWN,
                    "reason": "NO_ANCHOR_RECEIPT_FOR_PRIOR_SOURCE_PATH",
                    "identity_guessed": False,
                }
            )
            continue

        statuses = {str(row["body_currentness_status"]) for row in path_receipts}
        if CURRENT in statuses:
            locator = locator_by_path.get(path)
            if locator is None:
                raise ValueError(f"CURRENT source path lacks admitted locator: {path}")
            witness_ref = "+".join(
                sorted(str(row.get("witness_ref") or "") for row in path_receipts if row.get("witness_ref"))
            )
            projected = {
                "role": str(prior["role"]),
                "file_id": int(locator["file_id"]),
                "relative_path": path,
                "source_generation": int(locator["source_generation"]),
                "source_sha256": str(locator["sha256"]),
                "source_byte_len": int(locator["byte_len"]),
                "currentness": CURRENT,
                "witness_ref": witness_ref or f"ASTGE:CURRENT:{path}",
            }
            observations.append(
                {
                    "relative_path": path,
                    "currentness": CURRENT,
                    "source_generation_coordinate": _source_coordinate(projected["source_generation"]),
                    "dependency_identity_source": "ADMITTED_PR488_LOCATOR",
                    "observed_bytes_bound_to_source_generation": True,
                    "owner_receipts": path_receipts,
                }
            )
            o7_witnesses.append(projected)
            continue

        if STALE in statuses:
            stale_receipts = [row for row in path_receipts if row["body_currentness_status"] == STALE]
            owner_witness = _owner_witness_for_receipts(stale_receipts, witness_by_anchor)
            if owner_witness is None:
                unresolved.append(
                    {
                        "prior_file_id": int(prior["file_id"]),
                        "relative_path": path,
                        "prior_source_generation_coordinate": _source_coordinate(int(prior["source_generation"])),
                        "currentness": STALE,
                        "reason": "STALE_RECEIPT_WITHOUT_SOURCE_IDENTITY_WITNESS",
                        "identity_guessed": False,
                    }
                )
                continue
            projected = {
                "role": str(prior["role"]),
                "file_id": int(owner_witness["file_id"]),
                "relative_path": path,
                "source_generation": int(owner_witness["source_generation"]),
                "source_sha256": str(owner_witness["expected_body_sha256"]).lower(),
                "source_byte_len": int(owner_witness["expected_byte_len"]),
                "currentness": STALE,
                "witness_ref": str(owner_witness["witness_ref"]),
            }
            observations.append(
                {
                    "relative_path": path,
                    "currentness": STALE,
                    "source_generation_coordinate": _source_coordinate(projected["source_generation"]),
                    "dependency_identity_source": "EXPECTED_PR488_SOURCE_BODY_WITNESS",
                    "observed_bytes_bound_to_source_generation": False,
                    "expected_source_identity": {
                        "file_id": projected["file_id"],
                        "source_generation_coordinate": _source_coordinate(projected["source_generation"]),
                        "expected_byte_len": projected["source_byte_len"],
                        "expected_body_sha256": projected["source_sha256"],
                    },
                    "stale_owner_receipts": stale_receipts,
                }
            )
            o7_witnesses.append(projected)
            continue

        # UNKNOWN is intentionally not hydrated from prior identity or path.
        unresolved.append(
            {
                "prior_file_id": int(prior["file_id"]),
                "relative_path": path,
                "prior_source_generation_coordinate": _source_coordinate(int(prior["source_generation"])),
                "currentness": UNKNOWN,
                "reason": "PR488_MISSING_SOURCE_BODY_WITNESS",
                "identity_guessed": False,
                "owner_receipts": path_receipts,
            }
        )

    unbound_paths = sorted(set(receipts_by_path) - prior_paths)
    payload: dict[str, Any] = {
        "version": VERSION,
        "source_currentness_owner": "scripts/aura_astge_anchor_hydration.py",
        "source_generation_domain": SOURCE_DOMAIN,
        "previous_binding_identity": previous_binding["binding_identity"],
        "source_observations": observations,
        "o7_source_witnesses": sorted(
            o7_witnesses, key=lambda row: (int(row["file_id"]), str(row["relative_path"]))
        ),
        "unresolved_prior_sources": unresolved,
        "unbound_hydration_paths": unbound_paths,
        "stale_observed_bytes_bound_to_source_generation": False,
        "unknown_identity_guessed": False,
        "new_dependency_auto_promoted": False,
        "authority": {
            "source_currentness_minted": False,
            "semantic_truth_minted": False,
            "review_authorized": False,
            "mutation_authorized": False,
            "execution_authorized": False,
            "commit_authorized": False,
            "merge_authorized": False,
            "promotion_authorized": False,
            "provider_effect_authorized": False,
            "public_effect_authorized": False,
            "human_authority": False,
        },
    }
    payload["receipt_identity"] = _identity(payload)
    return payload


def verify_source_reentry_observations(receipt: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if receipt.get("version") != VERSION:
        violations.append("UNSUPPORTED_VERSION")
    if receipt.get("source_generation_domain") != SOURCE_DOMAIN:
        violations.append("SOURCE_GENERATION_DOMAIN_LOST")
    for observation in receipt.get("source_observations", []):
        coordinate = observation.get("source_generation_coordinate")
        if not isinstance(coordinate, dict) or coordinate.get("domain") != SOURCE_DOMAIN:
            violations.append("OBSERVATION_SOURCE_GENERATION_DOMAIN_LOST")
        if observation.get("currentness") == STALE and observation.get("observed_bytes_bound_to_source_generation") is not False:
            violations.append("STALE_OBSERVED_BYTES_LAUNDERED_AS_GENERATION_BOUND")
    for row in receipt.get("unresolved_prior_sources", []):
        if row.get("identity_guessed") is not False:
            violations.append("UNRESOLVED_SOURCE_IDENTITY_GUESSED")
    authority = receipt.get("authority")
    if not isinstance(authority, dict) or any(bool(value) for value in authority.values()):
        violations.append("AUTHORITY_MINTED_BY_SOURCE_REENTRY_PROJECTION")
    if receipt.get("new_dependency_auto_promoted") is not False:
        violations.append("UNBOUND_SOURCE_AUTO_PROMOTED")
    supplied = receipt.get("receipt_identity")
    without = dict(receipt)
    without.pop("receipt_identity", None)
    if supplied != _identity(without):
        violations.append("RECEIPT_IDENTITY_MISMATCH")
    return violations
