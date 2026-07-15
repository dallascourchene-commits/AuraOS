from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from aura_st3gg_compatibility import compress_report_with_v2_facade
from aura_st3gg_contracts import ST3GGRestorationMode

REPORT_TEXT = (
    "Emergent Properties and Future Potential\n"
    "Verified High-Leverage Clusters\n"
    "Evidence Status Score source_hash source_span required_tests verifier_notes\n"
    "NO_PATCHES NO_CODE_WRITES NO_UNIFIED_DIFF REPORT_ONLY\n"
) * 80


def _verified_evidence(tmp_path: Path):
    result = compress_report_with_v2_facade(
        REPORT_TEXT,
        persist_exact=True,
        ledger_path=tmp_path / "constructor_hardening.jsonl",
        minimum_savings_ratio=0.08,
    )
    assert result.v2_decision.restoration_mode is ST3GGRestorationMode.EXACT_RECALL
    assert result.recall_evidence is not None
    assert result.recall_evidence.verified is True
    return result.recall_evidence


def test_verified_evidence_rejects_missing_alias_proof(tmp_path: Path) -> None:
    evidence = _verified_evidence(tmp_path)

    with pytest.raises(ValueError, match="verified_alias_evidence_incomplete"):
        replace(evidence, alias_record_digests=())


def test_verified_evidence_rejects_json_digest_disagreement(tmp_path: Path) -> None:
    evidence = _verified_evidence(tmp_path)

    with pytest.raises(ValueError, match="verified_json_evidence_disagreement"):
        replace(evidence, json_index_record_digest="0" * 64)
