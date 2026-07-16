"""Insert the verified Architect benchmark section into README.md.

This script is idempotent and modifies documentation only. It is used by a
branch-scoped workflow after the benchmark evidence document is committed.
"""
from __future__ import annotations

from pathlib import Path

START = "<!-- AURA_ARCHITECT_BENCHMARK:START -->"
END = "<!-- AURA_ARCHITECT_BENCHMARK:END -->"


def _replace_or_insert(text: str, block: str) -> str:
    if START in text and END in text:
        before, rest = text.split(START, 1)
        _old, after = rest.split(END, 1)
        return before + block + after
    anchor = "## The Core Loop"
    if anchor not in text:
        raise RuntimeError(f"README anchor missing: {anchor}")
    return text.replace(anchor, block + "\n\n" + anchor, 1)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    readme_path = root / "README.md"
    evidence_path = root / "docs" / "AURA_ARCHITECT_CONSOLIDATION_BENCHMARK.md"
    readme = readme_path.read_text(encoding="utf-8")
    evidence = evidence_path.read_text(encoding="utf-8").strip()
    section = evidence.replace("# Aura Architect Consolidation Benchmark", "## First Architect Consolidation Benchmark", 1)
    block = f"{START}\n{section}\n{END}"
    updated = _replace_or_insert(readme, block)

    contents_line = "- [First Architect Consolidation Benchmark](#first-architect-consolidation-benchmark)"
    contents_anchor = "- [The Core Loop](#the-core-loop)"
    if contents_line not in updated:
        if contents_anchor not in updated:
            raise RuntimeError("README contents anchor missing")
        updated = updated.replace(contents_anchor, contents_line + "\n" + contents_anchor, 1)

    session_bullets = (
        "- leased external-LLM session open/next/submit/status/export;\n"
        "- bounded source and test slices instead of repository download;\n"
        "- provider-neutral Live Architect callback instrumentation;\n"
    )
    bridge_anchor = "- explicit human review boundaries."
    if "leased external-LLM session open/next/submit/status/export" not in updated:
        if bridge_anchor not in updated:
            raise RuntimeError("Agent Arena Bridge capability anchor missing")
        updated = updated.replace(bridge_anchor, session_bullets + bridge_anchor, 1)

    key_anchor = "- `aura_agent_arena_mcp.py`"
    extra_keys = (
        "- `aura_agent_arena_mcp.py`\n"
        "- `aura_agent_arena_mcp_external_llm.py`\n"
        "- `aura_external_llm_session.py`"
    )
    if "- `aura_agent_arena_mcp_external_llm.py`" not in updated:
        if key_anchor not in updated:
            raise RuntimeError("Agent Arena Bridge key-file anchor missing")
        updated = updated.replace(key_anchor, extra_keys, 1)

    readme_path.write_text(updated, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
