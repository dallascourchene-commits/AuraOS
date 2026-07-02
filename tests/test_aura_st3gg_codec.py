from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aura_builder_context import BuilderContextPacket, attach_st3gg_summary, render_context_packet_prompt  # noqa: E402
from aura_st3gg_codec import (  # noqa: E402
    ST3GGCodec,
    ST3GGProfile,
    choose_profile_for_phase,
    compare_raw_vs_encoded,
)

SAMPLE_SOURCE = """
import os
from pathlib import Path


def normalize_path(path: str, root: str = "") -> str:
    cleaned = path.strip()
    if root:
        cleaned = os.path.join(root, cleaned)
    result = str(Path(cleaned).resolve())
    if not result:
        raise ValueError("empty path")
    return result


def test_normalize_path() -> None:
    value = normalize_path("demo")
    assert value
""".strip()


def test_repeated_identifiers_are_interned_consistently() -> None:
    source = """
def total(items):
    total = 0
    for item in items:
        total += item.value
    return total
"""
    frame = ST3GGCodec().encode_source(source, profile=ST3GGProfile.SYMBOLIC)
    symbols = {item["name"]: item for item in frame.symbols}

    assert symbols["total"]["id"] in frame.encoded
    assert frame.encoded.count(symbols["total"]["id"]) >= 2
    assert ST3GGCodec().encode_source(source, profile=ST3GGProfile.SYMBOLIC).symbols == frame.symbols


def test_summary_is_smaller_than_raw_for_nontrivial_function() -> None:
    source = (
        """
def hydrate(records, default):
    hydrated = []
    for record in records:
        name = record.get("name", default)
        tags = record.get("tags", [])
        if name and tags:
            hydrated.append({"name": name, "tags": sorted(tags)})
        elif name:
            hydrated.append({"name": name, "tags": []})
    return hydrated
"""
        * 5
    )
    frame = ST3GGCodec().encode_source(source, profile=ST3GGProfile.SUMMARY)

    assert frame.metrics.encoded_token_estimate < frame.metrics.raw_token_estimate
    assert frame.metrics.compression_ratio < 1.0


def test_patch_preserves_exact_source_span_information() -> None:
    frame = ST3GGCodec().encode_source(
        SAMPLE_SOURCE,
        source_file="sample.py",
        target_symbol="normalize_path",
        profile=ST3GGProfile.PATCH,
    )

    assert frame.spans
    assert any(span["name"] == "normalize_path" and "def normalize_path" in span["text"] for span in frame.spans)
    assert not any("patch_frame_summary_only" in warning for warning in frame.warnings)


def test_patch_preserves_nested_method_target_span() -> None:
    source = """
class Worker:
    def build(self, value):
        if value < 0:
            raise ValueError("negative")
        return value + 1
"""
    frame = ST3GGCodec().encode_source(source, target_symbol="build", profile=ST3GGProfile.PATCH)

    assert any(span["kind"] == "function" and span["name"] == "build" for span in frame.spans)
    assert not any("target_symbol_not_found" in warning for warning in frame.warnings)


def test_large_string_literals_are_summarized() -> None:
    large = "A" * 500
    source = f'''
def payload():
    text = "{large}"
    return text
'''.strip()
    frame = ST3GGCodec().encode_source(source, profile=ST3GGProfile.SYMBOLIC)

    assert large not in frame.encoded
    assert "str(len=500" in frame.encoded


def test_syntax_errors_are_handled_with_warning_and_fallback_text() -> None:
    source = "def broken(:\n    return 1\n"
    frame = ST3GGCodec().encode_source(source, source_file="broken.py", profile=ST3GGProfile.SYMBOLIC)

    assert any("syntax_error_fallback" in warning for warning in frame.warnings)
    assert "FALLBACK_TEXT" in frame.encoded
    assert frame.source_hash


def test_token_estimate_comparison_is_deterministic() -> None:
    codec = ST3GGCodec()
    frame = codec.encode_source(SAMPLE_SOURCE, source_file="sample.py", profile=ST3GGProfile.SYMBOLIC)

    assert compare_raw_vs_encoded(SAMPLE_SOURCE, frame) == compare_raw_vs_encoded(SAMPLE_SOURCE, frame)
    assert codec.estimate_token_cost(SAMPLE_SOURCE) == ST3GGCodec().estimate_token_cost(SAMPLE_SOURCE)


def test_choose_profile_for_phase_returns_expected_profiles() -> None:
    assert choose_profile_for_phase("planner") == ST3GGProfile.SUMMARY
    assert choose_profile_for_phase("MUSIC council localizer") == ST3GGProfile.SYMBOLIC
    assert choose_profile_for_phase("builder patch") == ST3GGProfile.PATCH
    assert choose_profile_for_phase("test generation") == ST3GGProfile.TEST
    assert choose_profile_for_phase("verifier hotswap") == ST3GGProfile.VERIFIER


def test_fidelity_score_decreases_when_exact_spans_are_omitted() -> None:
    codec = ST3GGCodec()
    patch_frame = codec.encode_source(SAMPLE_SOURCE, target_symbol="normalize_path", profile=ST3GGProfile.PATCH)
    summary_frame = ST3GGCodec().encode_source(
        SAMPLE_SOURCE,
        target_symbol="normalize_path",
        profile=ST3GGProfile.SUMMARY,
    )

    assert patch_frame.metrics.fidelity_score > summary_frame.metrics.fidelity_score
    assert summary_frame.spans == ()


def test_no_new_dependencies_are_required() -> None:
    source = Path(REPO_ROOT / "aura_st3gg_codec.py").read_text(encoding="utf-8")
    forbidden = ("numpy", "zlib", "tree_sitter", "tiktoken")

    assert all(f"import {name}" not in source and f"from {name}" not in source for name in forbidden)


def test_builder_hook_attaches_st3gg_beside_exact_excerpt() -> None:
    packet = BuilderContextPacket(
        target_file="sample.py",
        target_symbol="normalize_path",
        source_excerpt="def normalize_path(path):\n    return path",
    )

    attach_st3gg_summary(packet, source=SAMPLE_SOURCE, profile=ST3GGProfile.PATCH)
    prompt = render_context_packet_prompt(packet)

    assert packet.source_excerpt == "def normalize_path(path):\n    return path"
    assert packet.st3gg_context["profile"] == "PATCH"
    assert "source_excerpt (exact lines from repository)" in prompt
    assert "st3gg_compact_context" in prompt
    assert prompt.index("source_excerpt") < prompt.index("st3gg_compact_context")


def test_benchmark_fixture_reports_two_real_aura_snippets() -> None:
    snippets: list[tuple[str, str]] = []
    for file_name in ("aura_builder_context.py", "aura_st3gg_recall.py"):
        text = (REPO_ROOT / file_name).read_text(encoding="utf-8", errors="replace")
        snippets.append((file_name, "\n".join(text.splitlines()[:120])))

    reports = []
    for file_name, snippet in snippets:
        frame = ST3GGCodec().encode_source(snippet, source_file=file_name, profile=ST3GGProfile.SUMMARY)
        report = compare_raw_vs_encoded(snippet, frame)
        reports.append(report)
        print(
            f"ST3GG_BENCH {file_name} raw={report['raw_token_estimate']} "
            f"encoded={report['encoded_token_estimate']} ratio={report['compression_ratio']} "
            f"fidelity={report['fidelity_score']}"
        )

    assert len(reports) == 2
    for report in reports:
        assert report["raw_token_estimate"] > 0
        assert report["encoded_token_estimate"] > 0
        assert "compression_ratio" in report
        assert "fidelity_score" in report
