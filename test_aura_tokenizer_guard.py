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


def test_tokenizer_guard_empty_string_is_safe():
    report = sanitize_tokenizer_channels("")

    assert report.sanitized_text == ""
    assert report.original_chars == 0
    assert report.sanitized_chars == 0
    assert report.removed_counts == ()
    assert report.normalized is False
    assert report.changed is False


def test_tokenizer_guard_clean_ascii_text_is_unchanged():
    text = "Hello, World! This is clean ASCII text.\nWith newlines\tand tabs."

    report = sanitize_tokenizer_channels(text)

    assert report.sanitized_text == text
    assert report.changed is False
    assert report.removed_counts == ()
    assert report.normalized is False
    assert report.warnings() == ()


def test_tokenizer_sanitization_report_to_jsonable_structure():
    report = sanitize_tokenizer_channels("A\u200bB")

    result = report.to_jsonable()

    assert result["changed"] is True
    assert result["original_chars"] == 3
    assert result["sanitized_chars"] == 2
    assert result["normalized"] is False
    assert result["removed_counts"]["format_control"] == 1


def test_tokenizer_guard_changed_true_when_only_normalized():
    report = sanitize_tokenizer_channels("\uff41")

    assert report.normalized is True
    assert report.changed is True
    assert report.removed_counts == ()


def test_tokenizer_guard_changed_false_for_clean_input():
    report = sanitize_tokenizer_channels("clean text")

    assert report.changed is False


def test_tokenizer_guard_preserves_allowed_format_controls():
    text = "line1\nline2\r\nline3\ttabbed"

    report = sanitize_tokenizer_channels(text)

    assert report.sanitized_text == text
    assert report.removed_counts == ()


def test_message_sanitizer_all_clean_messages_no_changes():
    batch = sanitize_message_payloads([
        {"role": "system", "content": "Clean system prompt"},
        {"role": "user", "content": "Clean user message"},
    ])

    summary = batch.to_jsonable()
    assert summary["changed_message_count"] == 0
    assert summary["removed_counts"] == {}
    assert summary["normalized_message_count"] == 0


def test_message_sanitizer_skips_non_string_content():
    batch = sanitize_message_payloads([
        {"role": "tool", "content": {"key": "value"}},
        {"role": "function", "content": [1, 2, 3]},
        {"role": "user"},
    ])

    assert batch.messages[0]["content"] == {"key": "value"}
    assert batch.messages[1]["content"] == [1, 2, 3]
    assert "content" not in batch.messages[2]
    assert batch.to_jsonable()["changed_message_count"] == 0


def test_message_sanitizer_batch_to_jsonable_aggregates_multiple_changes():
    batch = sanitize_message_payloads([
        {"role": "user", "content": "A\u200bB"},
        {"role": "assistant", "content": "C\ufe0fD"},
    ])

    summary = batch.to_jsonable()
    assert summary["changed_message_count"] == 2
    assert summary["removed_counts"]["format_control"] == 1
    assert summary["removed_counts"]["variation_selector"] == 1


def test_tokenizer_guard_multiple_tag_chars_counted():
    report = sanitize_tokenizer_channels("ab\U000e0041\U000e0042\U000e0043cd")

    assert dict(report.removed_counts)["tag_char"] == 3
    assert report.sanitized_text == "abcd"


def test_tokenizer_guard_private_use_area_f_plane():
    report = sanitize_tokenizer_channels("A\U000f0000B")

    assert dict(report.removed_counts)["private_use"] == 1
    assert report.sanitized_text == "AB"


def test_message_sanitizer_preserves_message_keys_not_content():
    batch = sanitize_message_payloads([
        {"role": "user", "content": "ok", "name": "Alice"},
    ])

    assert batch.messages[0]["role"] == "user"
    assert batch.messages[0]["name"] == "Alice"
