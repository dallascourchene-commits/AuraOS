from __future__ import annotations

from pathlib import Path

from scripts import aura_architecture_harness as harness


def test_digest_is_order_stable() -> None:
    assert harness._digest({"b": 2, "a": 1}) == harness._digest({"a": 1, "b": 2})


def test_default_venv_is_outside_repository() -> None:
    root = Path("/tmp/AuraOS")
    result = harness._default_venv(root)
    assert result.parent == root.parent
    assert result != root / ".venv"


def test_parser_defaults_to_bounded_minimal_atlas() -> None:
    args = harness._parser().parse_args(["--repo-root", ".", "run"])
    assert args.atlas_profile == "MINIMAL"
    assert args.allow_expansive_atlas is False
    assert args.pair_limit == 5_000_000
    assert args.resume is False


def test_required_surfaces_cover_requested_architecture() -> None:
    required = set(harness.REQUIRED_REPOSITORY_FILES)
    assert "aura_capability_connectome.py" in required
    assert "aura_relational_synthesis.py" in required
    assert "aura_relationship_atlas.py" in required
    assert "aura_emergent_potential_repl.py" in required
    assert "aura_architect_loop.py" in required


def test_harness_is_proposal_only() -> None:
    assert harness.PATCH_AUTHORITY == "exact_source_spans_and_hashes_only"
