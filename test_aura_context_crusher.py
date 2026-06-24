import json
from pathlib import Path
import textwrap

from aura_context_crusher import (
    apply_context_crush_to_messages,
    apply_context_crush_to_prompt,
    compute_cache_prefix_report,
    retrieve_context_crush,
)


def test_json_context_crush_is_reversible(tmp_path: Path):
    ledger = tmp_path / "context_crush.jsonl"
    payload = [
        {"path": f"file_{idx}.py", "line": idx, "severity": "ERROR", "message": "same schema"}
        for idx in range(80)
    ]
    raw = json.dumps(payload)

    result = apply_context_crush_to_prompt(raw, source_hint="json", ledger_path=ledger)

    assert result.was_compressed is True
    assert result.content_type == "json"
    assert result.token_savings_estimate > 0
    assert result.original_hash in result.compressed_payload
    restored = retrieve_context_crush(result.original_hash, ledger_path=ledger)
    assert restored == raw


def test_log_context_crush_preserves_error_lines(tmp_path: Path):
    ledger = tmp_path / "context_crush.jsonl"
    raw = "\n".join(
        [f"2026-06-24 10:00:{idx:02d} INFO heartbeat {idx}" for idx in range(70)]
        + ["2026-06-24 10:01:11 ERROR database lock timeout"]
        + [f"2026-06-24 10:02:{idx:02d} DEBUG followup {idx}" for idx in range(70)]
    )

    result = apply_context_crush_to_prompt(raw, source_hint="log", ledger_path=ledger)

    assert result.was_compressed is True
    assert "ERROR database lock timeout" in result.compressed_payload
    assert "[AURA_LOG_CRUSH" in result.compressed_payload


def test_cache_prefix_report_detects_volatile_system_prompt():
    messages = [
        {
            "role": "system",
            "content": "Cache seed 2026-06-24T12:00:00Z id 123e4567-e89b-12d3-a456-426614174000",
        },
        {"role": "user", "content": "hello"},
    ]

    report = compute_cache_prefix_report(messages)

    assert report.stable_prefix_hash
    assert report.alignment_score < 100
    labels = {finding.label for finding in report.findings}
    assert {"iso8601", "uuid"}.issubset(labels)


def test_message_crush_never_mutates_system_prompt(tmp_path: Path):
    ledger = tmp_path / "context_crush.jsonl"
    system = "Use strict JSON. Session 2026-06-24T12:00:00Z"
    user_payload = json.dumps([{"key": "value", "idx": idx} for idx in range(90)])
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_payload},
    ]

    batch = apply_context_crush_to_messages(messages, ledger_path=ledger)

    assert batch.messages[0]["content"] == system
    assert batch.messages[1]["content"] != user_payload
    assert batch.results[0].was_compressed is True
    assert batch.cache_prefix.stable_prefix_hash


def test_openai_compatible_helper_applies_context_crush(monkeypatch, tmp_path: Path):
    import aura_llm_egress

    captured = {}

    def fake_generate(url, api_key, payload, **kwargs):
        captured["payload"] = payload
        captured["kwargs"] = kwargs
        return "ok", None

    monkeypatch.setattr(aura_llm_egress, "openai_compatible_generate", fake_generate)
    user_payload = json.dumps([{"path": "a.py", "line": idx, "status": "same"} for idx in range(100)])

    text, err, _lat, _schema = aura_llm_egress.generate_openai_compatible_payload(
        provider="openrouter",
        base_url="https://openrouter.ai/api/v1/chat/completions",
        api_key="sk-test",
        model="model",
        messages=[
            {"role": "system", "content": "strict system prompt"},
            {"role": "user", "content": user_payload},
        ],
        context_crush_ledger=str(tmp_path / "context_crush.jsonl"),
    )

    assert err is None
    assert text == "ok"
    outbound = captured["payload"]["messages"]
    assert outbound[0]["content"] == "strict system prompt"
    assert "[AURA_CCR" in outbound[1]["content"]
    meta = captured["kwargs"]["savings_metadata"]["context_crush"]
    assert meta["compressed_message_count"] == 1


def test_context_crusher_uses_rust_wasm_bridge_when_candidate_wins(monkeypatch, tmp_path: Path):
    fake = tmp_path / "fake_accel.py"
    fake.write_text(
        textwrap.dedent(
            """
            import json
            import sys

            envelope = json.loads(sys.stdin.read())
            compressed = b"[RUST_ACCELERATED_LOG]"
            print(json.dumps({
                "status": "success",
                "accelerator": "rust:fake",
                "operation": envelope["operation"],
                "compressed_hex": compressed.hex(),
            }))
            """
        ).strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("AURA_CRUSH_ACCELERATOR_PATH", str(fake))
    raw = "\n".join(f"2026-06-24 10:00:{idx % 60:02d} ERROR noisy line {idx}" for idx in range(180))

    result = apply_context_crush_to_prompt(
        raw,
        source_hint="log",
        ledger_path=tmp_path / "context_crush.jsonl",
    )

    assert result.was_compressed is True
    assert result.accelerator == "rust:fake"
    assert "[RUST_ACCELERATED_LOG]" in result.compressed_payload
    assert result.to_jsonable()["accelerator"] == "rust:fake"
