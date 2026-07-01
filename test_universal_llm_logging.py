from pathlib import Path
import sqlite3

from aura_llm_call_logger import log_llm_call
from aura_savings_db import SavingsDB


def _rows(db_path: Path):
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM llm_calls ORDER BY id")]


def test_unknown_baseline_logs_call_with_zero_savings(tmp_path: Path):
    db_path = tmp_path / "savings.db"
    row_id = log_llm_call(
        provider="mistral",
        model="mistral-small-latest",
        call_type="generate",
        prompt_text="compact Aura packet",
        output_text="answer",
        latency_sec=0.01,
        db_path=str(db_path),
    )

    rows = _rows(db_path)
    assert row_id == 1
    assert len(rows) == 1
    assert rows[0]["tokens_saved"] == 0
    assert rows[0]["cost_saved_usd"] == 0.0
    assert rows[0]["baseline_prompt_tokens"] == rows[0]["prompt_tokens"]


def test_openai_compatible_generate_logs_direct_call(monkeypatch, tmp_path: Path):
    import aura_api_rotator

    db_path = tmp_path / "savings.db"

    def fake_post_json(url, payload, *, timeout, bearer=None):
        return {"choices": [{"message": {"content": "direct helper answer"}}]}

    monkeypatch.setattr(aura_api_rotator, "_post_json", fake_post_json)
    text, err = aura_api_rotator.openai_compatible_generate(
        "https://openrouter.ai/api/v1/chat/completions",
        "sk-test",
        {"model": "openai/gpt-4o-mini", "messages": [{"role": "user", "content": "hello"}]},
        retries=1,
        savings_db_path=str(db_path),
        savings_metadata={"unit_test": True},
    )

    assert err is None
    assert text == "direct helper answer"
    rows = _rows(db_path)
    assert len(rows) == 1
    assert rows[0]["provider"] == "openrouter"
    assert rows[0]["model"] == "openai/gpt-4o-mini"
    assert rows[0]["call_type"] == "generate"


def test_gemini_generate_logs_direct_call(monkeypatch, tmp_path: Path):
    import aura_api_rotator

    db_path = tmp_path / "savings.db"

    def fake_post_json(url, payload, *, timeout, bearer=None):
        return {"candidates": [{"content": {"parts": [{"text": "gemini answer"}]}}]}

    monkeypatch.setattr(aura_api_rotator, "_post_json", fake_post_json)
    text, err = aura_api_rotator.gemini_generate(
        "hello gemini",
        secrets={"GEMINI_API_KEY": "real-test-key"},
        retries_per_key=1,
        savings_db_path=str(db_path),
    )

    assert err is None
    assert text == "gemini answer"
    rows = _rows(db_path)
    assert len(rows) == 1
    assert rows[0]["provider"] == "gemini"
    assert rows[0]["call_type"] == "generate"


def test_external_llm_interpret_logs_once_as_interpret(monkeypatch, tmp_path: Path):
    from aura_llm_call_logger import log_openai_compatible_call
    import aura_llm_egress
    from aura_llm_egress import ExternalLLM

    db_path = tmp_path / "savings.db"

    def fake_generate(url, api_key, payload, **kwargs):
        text = "human-readable interpretation"
        log_openai_compatible_call(
            url=url,
            payload=payload,
            output_text=text,
            error=None,
            latency_sec=0.01,
            call_type=kwargs.get("call_type", "generate"),
            task=kwargs.get("task"),
            aspect=kwargs.get("aspect"),
            baseline_prompt_tokens=kwargs.get("baseline_prompt_tokens"),
            baseline_output_tokens=kwargs.get("baseline_output_tokens"),
            baseline_cost_usd=kwargs.get("baseline_cost_usd"),
            metadata=kwargs.get("savings_metadata"),
            db_path=str(db_path),
        )
        return text, None

    monkeypatch.setattr(aura_llm_egress, "openai_compatible_generate", fake_generate)
    egress = ExternalLLM(
        provider="openrouter",
        secrets={"OPEN_ROUTER_API_KEY": "sk-test"},
        task="interpret_test",
        aspect="conversation",
    )
    text, err, _lat = egress.interpret({"answer": 1}, "Explain briefly.", pre_egress=False)

    assert err is None
    assert text == "human-readable interpretation"
    rows = _rows(db_path)
    assert len(rows) == 1
    assert rows[0]["call_type"] == "interpret"
    assert rows[0]["task"] == "interpret_test"
    assert rows[0]["aspect"] == "conversation"


def test_recent_calls_exposes_baseline_fields(tmp_path: Path):
    db_path = tmp_path / "savings.db"
    db = SavingsDB(str(db_path))
    db.log_call(
        provider="mistral",
        model="m",
        call_type="generate",
        prompt_tokens=10,
        output_tokens=5,
        cost_usd=0.1,
        latency_sec=0.1,
        baseline_prompt_tokens=30,
        baseline_output_tokens=15,
        baseline_cost_usd=0.3,
    )
    recent = db.recent_calls(limit=1)
    assert recent[0]["baseline_prompt_tokens"] == 30
    assert recent[0]["baseline_output_tokens"] == 15
    assert recent[0]["tokens_saved"] == 30
