from pathlib import Path
import re


def test_code_prefix_routes_to_live_architect_before_cognitive_lifecycle():
    source = Path("aura_node.py").read_text(encoding="utf-8")

    source = Path("aura_node.py").read_text(encoding="utf-8")

    helper = "async def dispatch_live_architect_command(raw_input: str) -> bool:"
    fast_path = re.compile(
        r"if\s+await\s+dispatch_live_architect_command\(u_in\):\s*\n\s+continue"
    )
    production_pattern = r"^\s*(architect|code)\b\s*:?\s*(.*)$"
    lifecycle = "# [LAYER 7 AUTOMATED COGNITIVE LIFECYCLE HOOK]"
    legacy_report = "STAGED MUTATION TOPOLOGY IMPACT REPORT (AURA_INCUBATOR)"

    assert helper in source
    assert production_pattern in source
    fast_path_match = fast_path.search(source)
    assert fast_path_match
    assert fast_path_match.start() < source.index(lifecycle)
    assert fast_path_match.start() < source.index(legacy_report)

    pattern = re.compile(production_pattern, re.IGNORECASE)
    match = pattern.match("code: Fix upgraded_arxiv_backtracker")

    assert match
    assert match.group(1) == "code"
    assert match.group(2) == "Fix upgraded_arxiv_backtracker"

