from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


FOUR_TAB_LABELS = (
    "Civic Arena",
    "Human Agent Coding Arena",
    "Aura Observatory",
    "Learning Arena / Crucible",
)


def test_default_dockerfile_launches_unified_showcase() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "aura_showcase_server.py" in dockerfile
    assert "winnipeg_pathways" in dockerfile
    assert "${PORT:-10000}" in dockerfile
    assert "aura_coding_arena_server.py" not in dockerfile


def test_mini_coding_arena_remains_available_separately() -> None:
    dockerfile = (ROOT / "Dockerfile.coding-arena").read_text(encoding="utf-8")
    assert "aura_coding_arena_server.py" in dockerfile
    assert '"--demo"' in dockerfile


def test_unified_showcase_contains_all_four_tabs() -> None:
    index = (ROOT / "aura_showcase" / "index.html").read_text(encoding="utf-8")
    for label in FOUR_TAB_LABELS:
        assert label in index
    assert index.count('class="tab') >= 4


def test_render_blueprint_targets_default_unified_container() -> None:
    blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "runtime: docker" in blueprint
    assert "dockerfilePath: ./Dockerfile" in blueprint
    assert "healthCheckPath: /api/showcase/status" in blueprint
    assert "FIREWORKS_API_KEY" in blueprint
    assert "sync: false" in blueprint
