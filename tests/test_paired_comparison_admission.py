from __future__ import annotations

import copy
import hashlib
import json

import pytest

from tools.benchmarks.long_horizon_preregistration import build_preregistration
from tools.benchmarks.paired_comparison_admission import admit_blinded_pair
from tools.benchmarks.persistent_adapter_runner import RUNNER_SCHEMA_ID


def digest(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def prereg():
    arms = [
        {
            "blinded_label": "arm-01",
            "adapter_generation": "gen-a",
            "adapter_command_digest": "a" * 64,
            "condition_commitment": "c" * 64,
        },
        {
            "blinded_label": "arm-02",
            "adapter_generation": "gen-b",
            "adapter_command_digest": "b" * 64,
            "condition_commitment": "d" * 64,
        },
    ]
    return build_preregistration(
        campaign_id="pair-001",
        rounds=4,
        seed=17,
        timeout_seconds=120.0,
        arms=arms,
    )


def report(
    pre,
    *,
    label,
    generation,
    command_digest,
    provenance="UNKNOWN",
    metric_values=None,
    startup="PASS",
    campaign="PASS",
):
    turns = []
    if startup == "PASS":
        telemetry = {"provenance": provenance}
        if metric_values:
            telemetry.update(metric_values)
        turns = [
            {
                "turn": turn,
                "disposition": "PASS",
                "expected_state_digest": "e" * 64,
                "observed_state_digest": "e" * 64,
                "telemetry": dict(telemetry),
                "wall_time_ms": 1.0,
            }
            for turn in range(pre["rounds"])
        ]
    payload = {
        "schema_id": RUNNER_SCHEMA_ID,
        "campaign_disposition": campaign,
        "startup_disposition": startup,
        "handshake": None if startup != "PASS" else {"adapter_generation": generation},
        "adapter_generation": generation if startup == "PASS" else None,
        "adapter_command_digest": command_digest,
        "rounds": pre["rounds"],
        "seed": pre["seed"],
        "startup_timeout_seconds": 10.0,
        "turn_timeout_seconds": pre["timeout_seconds"],
        "workload_digest": pre["workload_digest"],
        "state_drift_detected": False,
        "inconclusive_turns": 0 if startup == "PASS" else pre["rounds"],
        "disposition_counts": {},
        "runner_wall_time_ms": 4.0,
        "turns": turns,
        "teardown": {"disposition": "CLEAN_EXIT", "returncode": 0},
        "stderr": [],
    }
    payload["evidence_digest"] = digest(payload)
    return {"blinded_label": label, "report": payload}


def matched_pair(pre, provenance="UNKNOWN", metric_values=None):
    return [
        report(
            pre,
            label="arm-01",
            generation="gen-a",
            command_digest="a" * 64,
            provenance=provenance,
            metric_values=metric_values,
        ),
        report(
            pre,
            label="arm-02",
            generation="gen-b",
            command_digest="b" * 64,
            provenance=provenance,
            metric_values=metric_values,
        ),
    ]


def test_exact_pair_is_admitted_but_remains_blinded_without_winner():
    pre = prereg()
    result = admit_blinded_pair(pre, matched_pair(pre))
    assert result["pair_disposition"] == "PAIR_ADMITTED"
    assert result["state_outcomes_comparable"] is True
    assert result["telemetry_comparison_allowed"] is False
    assert result["comparable_observed_metrics"] == []
    assert result["winner"] is None
    assert result["claim_ceiling"] == "BLINDED_PAIR_EVIDENCE_ONLY_NO_WINNER"
    assert [arm["blinded_label"] for arm in result["arms"]] == ["arm-01", "arm-02"]


def test_observed_label_without_values_does_not_mint_metric_comparability():
    pre = prereg()
    result = admit_blinded_pair(pre, matched_pair(pre, provenance="OBSERVED"))
    assert result["telemetry_comparison_allowed"] is False
    assert result["comparable_observed_metrics"] == []


def test_only_metrics_observed_on_every_turn_in_both_arms_are_comparable():
    pre = prereg()
    pair = matched_pair(
        pre,
        provenance="OBSERVED",
        metric_values={"input_tokens": 10, "output_tokens": 5, "cost_usd": 0.01},
    )
    result = admit_blinded_pair(pre, pair)
    assert result["telemetry_comparison_allowed"] is True
    assert result["comparable_observed_metrics"] == ["cost_usd", "input_tokens", "output_tokens"]

    mixed = matched_pair(
        pre,
        provenance="OBSERVED",
        metric_values={"input_tokens": 10, "output_tokens": 5, "cost_usd": 0.01},
    )
    for turn in mixed[1]["report"]["turns"]:
        turn["telemetry"].pop("cost_usd")
    mixed[1]["report"]["evidence_digest"] = digest(
        {k: v for k, v in mixed[1]["report"].items() if k != "evidence_digest"}
    )
    result = admit_blinded_pair(pre, mixed)
    assert result["telemetry_comparison_allowed"] is True
    assert result["comparable_observed_metrics"] == ["input_tokens", "output_tokens"]

    estimated = matched_pair(
        pre,
        provenance="OBSERVED",
        metric_values={"input_tokens": 10},
    )
    estimated[1] = report(
        pre,
        label="arm-02",
        generation="gen-b",
        command_digest="b" * 64,
        provenance="ESTIMATED",
        metric_values={"input_tokens": 10},
    )
    result = admit_blinded_pair(pre, estimated)
    assert result["telemetry_comparison_allowed"] is False
    assert result["comparable_observed_metrics"] == []


def test_pair_rejects_workload_command_and_generation_substitution():
    pre = prereg()
    bad = matched_pair(pre)
    bad[0]["report"]["workload_digest"] = "f" * 64
    bad[0]["report"]["evidence_digest"] = digest({k: v for k, v in bad[0]["report"].items() if k != "evidence_digest"})
    with pytest.raises(ValueError, match="WORKLOAD_DIGEST_MISMATCH"):
        admit_blinded_pair(pre, bad)

    bad = matched_pair(pre)
    bad[0]["report"]["adapter_command_digest"] = "f" * 64
    bad[0]["report"]["evidence_digest"] = digest({k: v for k, v in bad[0]["report"].items() if k != "evidence_digest"})
    with pytest.raises(ValueError, match="ADAPTER_COMMAND_DIGEST_MISMATCH"):
        admit_blinded_pair(pre, bad)

    bad = matched_pair(pre)
    bad[0]["report"]["adapter_generation"] = "stale-gen"
    bad[0]["report"]["evidence_digest"] = digest({k: v for k, v in bad[0]["report"].items() if k != "evidence_digest"})
    with pytest.raises(ValueError, match="ADAPTER_GENERATION_MISMATCH"):
        admit_blinded_pair(pre, bad)


def test_startup_failure_is_retained_as_matched_inconclusive_evidence():
    pre = prereg()
    pair = matched_pair(pre)
    pair[1] = report(
        pre,
        label="arm-02",
        generation="gen-b",
        command_digest="b" * 64,
        startup="TIMEOUT",
        campaign="INCONCLUSIVE",
    )
    result = admit_blinded_pair(pre, pair)
    assert result["pair_disposition"] == "PAIR_ADMITTED_INCONCLUSIVE"
    assert result["state_outcomes_comparable"] is False
    assert result["telemetry_comparison_allowed"] is False
    assert result["comparable_observed_metrics"] == []
    arm_02 = next(arm for arm in result["arms"] if arm["blinded_label"] == "arm-02")
    assert arm_02["identity_status"] == "COMMAND_MATCH_GENERATION_UNOBSERVED"


def test_unblinded_fields_and_duplicate_labels_fail_closed():
    pre = prereg()
    pair = matched_pair(pre)
    pair[0]["condition_name"] = "AURA"
    with pytest.raises(ValueError, match="UNBLINDED_CONDITION_FIELD_FORBIDDEN"):
        admit_blinded_pair(pre, pair)

    pair = matched_pair(pre)
    pair[1]["blinded_label"] = "arm-01"
    with pytest.raises(ValueError, match="DUPLICATE_RUN_BLINDED_LABEL"):
        admit_blinded_pair(pre, pair)


def test_tampered_evidence_digest_fails_closed():
    pre = prereg()
    pair = matched_pair(pre)
    pair[0]["report"] = copy.deepcopy(pair[0]["report"])
    pair[0]["report"]["runner_wall_time_ms"] = 999.0
    with pytest.raises(ValueError, match="EVIDENCE_DIGEST_MISMATCH"):
        admit_blinded_pair(pre, pair)
