from aura_tokenizer_guard import sanitize_message_payloads, sanitize_tokenizer_channels


def test_tokenizer_guard_strips_survival_carriers():
    raw = "A\u200bB\U000e0001C\ue000D\u202eE\ufe0f"

    report = sanitize_tokenizer_channels(raw)

    assert report.sanitized_text == "ABCDE"
    removed = dict(report.removed_counts)
    assert removed["format_control"] == 1
    assert removed["tag_char"] == 1
    assert removed["private_use"] == 1
    assert removed["bidi_control"] == 1
    assert removed["variation_selector"] == 1
    assert "tokenizer_guard_removed_format_control:1" in report.warnings()


def test_tokenizer_guard_nfkc_normalizes_visible_text():
    report = sanitize_tokenizer_channels("Ａura")

    assert report.sanitized_text == "Aura"
    assert report.normalized is True
    assert "tokenizer_guard_nfkc_normalized" in report.warnings()


def test_message_sanitizer_preserves_shape_and_reports_changes():
    batch = sanitize_message_payloads([
        {"role": "system", "content": "Keep cache stable"},
        {"role": "user", "content": "hi\u200bthere"},
        {"role": "tool", "content": {"already": "structured"}},
    ])

    assert batch.messages[0]["content"] == "Keep cache stable"
    assert batch.messages[1]["content"] == "hithere"
    assert batch.messages[2]["content"] == {"already": "structured"}
    summary = batch.to_jsonable()
    assert summary["changed_message_count"] == 1
    assert summary["removed_counts"]["format_control"] == 1
