import re
from pathlib import Path


def test_code_prefix_routes_to_live_architect_before_cognitive_lifecycle():
    source = Path("aura_node.py").read_text(encoding="utf-8")

    helper = "async def dispatch_live_architect_command(raw_input: str) -> bool:"
    fast_path = "if await dispatch_live_architect_command(u_in):"
    lifecycle = "# [LAYER 7 AUTOMATED COGNITIVE LIFECYCLE HOOK]"
    legacy_report = "STAGED MUTATION TOPOLOGY IMPACT REPORT (AURA_INCUBATOR)"

    assert helper in source
    assert fast_path in source
    assert source.index(fast_path) < source.index(lifecycle)
    assert source.index(fast_path) < source.index(legacy_report)

    pattern = re.compile(r"^\s*(architect|code)\b\s*:?\s*(.*)$", re.IGNORECASE)
    match = pattern.match("code: Fix upgraded_arxiv_backtracker")

    assert match
    assert match.group(1) == "code"
    assert match.group(2) == "Fix upgraded_arxiv_backtracker"

