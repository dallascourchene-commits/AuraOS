from __future__ import annotations

from pathlib import Path

from aura_ai_router import query_router


def _resolution(*_args, **_kwargs):
    return {
        "objective": "locate target",
        "confidence": 0.8,
        "exact_matches": [
            {
                "file": "alpha.py",
                "symbol": "target",
                "grounding_class": "EXACT",
            }
        ],
        "related_functions": [],
        "reuse_plan": [],
        "tests": ["test_alpha.py"],
        "capability_connectome_path": {
            "ok": True,
            "graph_digest": "graph",
            "path_digest": "path",
            "path": ["cap.code"],
            "required_capability_ids": ["cap.code"],
        },
        "capability_graph_digest": "graph",
        "capability_path_digest": "path",
        "required_capability_ids": ["cap.code"],
        "capability_path_details": [
            {
                "implemented_by": ["alpha.py"],
                "symbols": ["target"],
                "tests": ["test_alpha.py"],
            }
        ],
    }


def test_query_router_uses_exact_topology_and_bounds_context(tmp_path: Path) -> None:
    (tmp_path / "alpha.py").write_text(
        "from beta import helper\n\ndef target(value):\n    return helper(value)\n",
        encoding="utf-8",
    )
    (tmp_path / "beta.py").write_text(
        "def helper(value):\n    return value + 1\n",
        encoding="utf-8",
    )
    (tmp_path / "test_alpha.py").write_text(
        "from alpha import target\n\ndef test_target():\n    assert target(1) == 2\n",
        encoding="utf-8",
    )

    result = query_router(
        "change `target` in alpha.py",
        repo_root=tmp_path,
        target_files=["alpha.py"],
        target_symbols=["target"],
        token_budget=300,
        static_fallback=False,
        resolver=_resolution,
    )

    assert result["status"] == "found"
    assert result["routing_source"] == "dynamic_topology"
    assert result["primary_file"] == "alpha.py"
    assert result["exact_symbols"][0]["symbol"] == "target"
    assert result["exact_symbols"][0]["source_hash"]
    assert any(item["symbol"] == "helper" for item in result["callees"])
    assert "test_alpha.py" in result["tests"]
    assert result["topology_digest"]
    assert result["context_tokens"] <= 300
    assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
    assert result["vsa_patch_authority"] is False


def test_generated_markdown_is_cold_fallback_only(tmp_path: Path) -> None:
    (tmp_path / "AURA_AI_ROUTER.md").write_text(
        "## Static Fallback Task → File Mapping\n\n"
        "| Task / Intent | Primary File | Secondary Files | Key Functions |\n"
        "|---|---|---|---|\n"
        "| `route llm request` | `aura_router.py` | `aura_llm_egress.py` | AutoRouter |\n",
        encoding="utf-8",
    )

    def empty_resolution(*_args, **_kwargs):
        return {
            "objective": "route llm request",
            "confidence": 0.0,
            "exact_matches": [],
            "related_functions": [],
            "reuse_plan": [],
            "tests": [],
            "capability_connectome_path": {"ok": False},
        }

    result = query_router(
        "route llm request",
        repo_root=tmp_path,
        resolver=empty_resolution,
    )

    assert result["status"] == "found"
    assert result["routing_source"] == "static_fallback"
    assert result["primary_file"] == "aura_router.py"
    assert result["advisory_only"] is True
    assert result["dynamic_attempt"]["routing_source"] in {"none", "dynamic_error"}

def test_query_router_prefers_explicit_file_for_duplicate_symbol(tmp_path: Path) -> None:
    (tmp_path / "alpha.py").write_text("def target():\n    return 'alpha'\n", encoding="utf-8")
    (tmp_path / "beta.py").write_text("def target():\n    return 'beta'\n", encoding="utf-8")

    result = query_router(
        "change target in beta.py",
        repo_root=tmp_path,
        target_files=["beta.py"],
        target_symbols=["target"],
        static_fallback=False,
        resolver=_resolution,
    )

    assert result["primary_file"] == "beta.py"
    assert result["exact_symbols"][0]["file"] == "beta.py"
    assert "return 'beta'" in result["router_context"]
    assert "return 'alpha'" not in result["router_context"]
