from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from tools.benchmarks.long_horizon_preregistration import SCHEMA_ID as PREREG_SCHEMA_ID
from tools.benchmarks.persistent_adapter_runner import RUNNER_SCHEMA_ID


PAIR_SCHEMA_ID = "AURA_BLINDED_PAIR_ADMISSION_V1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _verify_embedded_digest(payload: dict[str, Any], field: str) -> None:
    observed = payload.get(field)
    if not isinstance(observed, str) or not _SHA256_RE.fullmatch(observed):
        raise ValueError(f"INVALID_{field.upper()}")
    canonical = dict(payload)
    del canonical[field]
    if _canonical_digest(canonical) != observed:
        raise ValueError(f"{field.upper()}_MISMATCH")


def _telemetry_status(report: dict[str, Any]) -> str:
    if report.get("startup_disposition") != "PASS":
        return "NOT_COMPARABLE"
    turns = report.get("turns")
    if not isinstance(turns, list) or not turns:
        return "NOT_COMPARABLE"
    provenances: list[str] = []
    for turn in turns:
        if turn.get("disposition") not in {"PASS", "STATE_DRIFT"}:
            return "NOT_COMPARABLE"
        telemetry = turn.get("telemetry")
        if not isinstance(telemetry, dict):
            return "NOT_COMPARABLE"
        provenances.append(str(telemetry.get("provenance", "UNKNOWN")))
    if provenances and all(item == "OBSERVED" for item in provenances):
        return "OBSERVED_MATCHED_ELIGIBLE"
    return "NOT_COMPARABLE"


def admit_blinded_pair(
    preregistration: dict[str, Any],
    run_envelopes: list[dict[str, Any]],
) -> dict[str, Any]:
    if preregistration.get("schema_id") != PREREG_SCHEMA_ID:
        raise ValueError("INVALID_PREREGISTRATION_SCHEMA")
    _verify_embedded_digest(preregistration, "preregistration_digest")
    arms = preregistration.get("arms")
    if not isinstance(arms, list) or len(arms) != 2:
        raise ValueError("EXACTLY_TWO_PREREGISTERED_ARMS_REQUIRED")
    if not isinstance(run_envelopes, list) or len(run_envelopes) != 2:
        raise ValueError("EXACTLY_TWO_RUN_ENVELOPES_REQUIRED")

    prereg_by_label = {arm.get("blinded_label"): arm for arm in arms}
    if len(prereg_by_label) != 2 or None in prereg_by_label:
        raise ValueError("INVALID_PREREGISTERED_ARM_LABELS")

    seen: set[str] = set()
    admitted: list[dict[str, Any]] = []
    for envelope in run_envelopes:
        if not isinstance(envelope, dict):
            raise ValueError("RUN_ENVELOPE_MUST_BE_OBJECT")
        if "condition_name" in envelope or "treatment" in envelope:
            raise ValueError("UNBLINDED_CONDITION_FIELD_FORBIDDEN")
        label = envelope.get("blinded_label")
        if label not in prereg_by_label:
            raise ValueError("UNREGISTERED_BLINDED_LABEL")
        if label in seen:
            raise ValueError("DUPLICATE_RUN_BLINDED_LABEL")
        seen.add(label)
        arm = prereg_by_label[label]
        report = envelope.get("report")
        if not isinstance(report, dict) or report.get("schema_id") != RUNNER_SCHEMA_ID:
            raise ValueError("INVALID_RUNNER_REPORT")
        _verify_embedded_digest(report, "evidence_digest")
        if report.get("workload_digest") != preregistration.get("workload_digest"):
            raise ValueError("WORKLOAD_DIGEST_MISMATCH")
        if report.get("rounds") != preregistration.get("rounds"):
            raise ValueError("ROUND_COUNT_MISMATCH")
        if report.get("seed") != preregistration.get("seed"):
            raise ValueError("SEED_MISMATCH")
        if report.get("turn_timeout_seconds") != preregistration.get("timeout_seconds"):
            raise ValueError("TURN_TIMEOUT_MISMATCH")
        if report.get("adapter_command_digest") != arm.get("adapter_command_digest"):
            raise ValueError("ADAPTER_COMMAND_DIGEST_MISMATCH")

        startup = report.get("startup_disposition")
        observed_generation = report.get("adapter_generation")
        if startup == "PASS":
            if observed_generation != arm.get("adapter_generation"):
                raise ValueError("ADAPTER_GENERATION_MISMATCH")
            identity_status = "EXACT"
        else:
            if observed_generation is not None:
                raise ValueError("FAILED_STARTUP_CANNOT_ASSERT_GENERATION")
            identity_status = "COMMAND_MATCH_GENERATION_UNOBSERVED"

        admitted.append(
            {
                "blinded_label": label,
                "identity_status": identity_status,
                "campaign_disposition": report.get("campaign_disposition"),
                "startup_disposition": startup,
                "evidence_digest": report["evidence_digest"],
                "telemetry_status": _telemetry_status(report),
            }
        )

    if seen != set(prereg_by_label):
        raise ValueError("MISSING_PREREGISTERED_ARM")
    admitted.sort(key=lambda item: item["blinded_label"])
    all_exact = all(item["identity_status"] == "EXACT" for item in admitted)
    all_observed = all(item["telemetry_status"] == "OBSERVED_MATCHED_ELIGIBLE" for item in admitted)
    any_inconclusive = any(
        item["campaign_disposition"] in {"INCONCLUSIVE", "STATE_DRIFT_WITH_INCONCLUSIVE"}
        or item["startup_disposition"] != "PASS"
        for item in admitted
    )
    if not all_exact or any_inconclusive:
        pair_disposition = "PAIR_ADMITTED_INCONCLUSIVE"
    else:
        pair_disposition = "PAIR_ADMITTED"

    result = {
        "schema_id": PAIR_SCHEMA_ID,
        "preregistration_digest": preregistration["preregistration_digest"],
        "claim_ceiling": "BLINDED_PAIR_EVIDENCE_ONLY_NO_WINNER",
        "pair_disposition": pair_disposition,
        "state_outcomes_comparable": all_exact and not any_inconclusive,
        "telemetry_comparison_allowed": all_exact and all_observed and not any_inconclusive,
        "winner": None,
        "arms": admitted,
    }
    result["pair_evidence_digest"] = _canonical_digest(result)
    return result
