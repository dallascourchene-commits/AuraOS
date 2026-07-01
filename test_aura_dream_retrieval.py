import json
import sqlite3

from aura_dream_retrieval import (
    DreamCandidate,
    DreamReranker,
    DreamRetrievalExample,
    rerank_for_arena,
)
import aura_qdkt
from aura_qdkt import UnifiedQDKT
from aura_st3gg_recall import ST3GGRecallRecord, rerank_st3gg_recall_candidates


def test_dream_reranks_by_downstream_usefulness_and_writes_ledger(tmp_path):
    ledger_path = tmp_path / "dream.jsonl"
    result = rerank_for_arena(
        "patch aura_fusion build_task_capsule and nearby tests",
        [
            DreamCandidate(
                candidate_id="file:aura_fusion.py",
                candidate_type="codemap_file",
                source="CODEMAP",
                content="aura_fusion.py build_task_capsule",
                semantic_score=0.62,
            ),
            DreamCandidate(
                candidate_id="file:unrelated.py",
                candidate_type="codemap_file",
                source="CODEMAP",
                content="unrelated weather parser",
                semantic_score=0.92,
            ),
        ],
        "code_context",
        arena_domain="code",
        ledger_path=ledger_path,
    )

    assert result["ranked_candidates"][0]["candidate_id"] == "file:aura_fusion.py"
    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["query"].startswith("patch aura_fusion")
    assert rows[0]["candidate_id"] == "file:aura_fusion.py"
    assert rows[0]["usefulness_score"] > rows[1]["usefulness_score"]


def test_dream_local_loss_mode_rewards_lower_loss():
    def local_loss(_example, candidate):
        return {"baseline_loss": 10.0, "candidate_loss": 2.0 if candidate.candidate_id == "helpful" else 9.5}

    example = DreamRetrievalExample(
        query="answer travel package verifier",
        target_type="travel_vsa_pointer",
        candidates=[
            DreamCandidate(candidate_id="weak", candidate_type="travel_vsa_pointer", source="travel_vsa"),
            DreamCandidate(candidate_id="helpful", candidate_type="travel_vsa_pointer", source="travel_vsa"),
        ],
        mode="local_loss",
    )

    ranked = DreamReranker(local_loss_fn=local_loss).rerank(example, record=False)

    assert ranked["ranked_candidates"][0]["candidate_id"] == "helpful"
    assert ranked["scores"][0]["mode"] == "local_loss"


def test_dream_penalizes_failed_truth_boundary():
    result = rerank_for_arena(
        "family resort fresh verified price",
        [
            DreamCandidate(
                candidate_id="fresh",
                candidate_type="travel_vsa_pointer",
                source="travel_vsa_pointer_index",
                content="family resort",
                semantic_score=0.5,
                exact_lookup_required=True,
                verifier_result={"approved": True},
            ),
            DreamCandidate(
                candidate_id="stale",
                candidate_type="travel_vsa_pointer",
                source="travel_vsa_pointer_index",
                content="family resort",
                semantic_score=0.9,
                exact_lookup_required=True,
                verifier_result={"approved": False, "blockers": ["price_observation_stale"]},
            ),
        ],
        "travel_vsa_pointer",
        arena_domain="travel",
        record=False,
    )

    assert result["ranked_candidates"][0]["candidate_id"] == "fresh"
    stale = next(row for row in result["scores"] if row["candidate_id"] == "stale")
    assert stale["failure_reason"] == "price_observation_stale"


def test_qdkt_records_retrieval_usefulness(tmp_path, monkeypatch):
    monkeypatch.setattr(aura_qdkt, "_MEMPALACE_DB", tmp_path / "mempalace.db")
    monkeypatch.setattr(aura_qdkt, "_WORKSPACE_DB", tmp_path / "workspace.db")
    monkeypatch.setattr(aura_qdkt, "_CRYSTAL_JSON", tmp_path / "crystals.json")
    qdkt = UnifiedQDKT()

    result = rerank_for_arena(
        "retrieve useful code context",
        [
            DreamCandidate(
                candidate_id="file:aura_qdkt.py",
                candidate_type="codemap_file",
                source="CODEMAP",
                content="aura_qdkt.py retrieval usefulness",
            )
        ],
        "code_context",
        qdkt=qdkt,
        ledger_path=tmp_path / "dream.jsonl",
    )

    with sqlite3.connect(tmp_path / "workspace.db") as conn:
        row = conn.execute("SELECT candidate_id, usefulness_score FROM qdkt_retrieval_usefulness").fetchone()
    assert row[0] == "file:aura_qdkt.py"
    assert row[1] == result["scores"][0]["usefulness_score"]


def test_st3gg_records_can_be_reranked_without_changing_recall_storage():
    record = ST3GGRecallRecord(
        pointer="ST3GG-L2::MEM:ABCD:1234",
        dash_key="1234",
        glyph="ABCD",
        holographic_header="header",
        original_hash="hash",
        content_type="memory",
        original="AuraFusion retrieval usefulness memory",
        source_hint="ST3GG",
    )

    result = rerank_st3gg_recall_candidates("AuraFusion retrieval usefulness", [record])

    assert result["ranked_candidates"][0]["candidate_id"] == record.pointer
    assert result["scores"][0]["candidate_type"] == "st3gg_memory"
