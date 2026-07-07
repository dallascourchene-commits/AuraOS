import json
from pathlib import Path
import urllib.request

from aura_coding_arena_grounding import ground_coding_arena_intent
from aura_emergent_potential_repl import (
    AUDIT_ROUTE,
    AbilityAtom,
    STATUS_FUTURE_PATCHABLE,
    STATUS_NEEDS_GROUNDING,
    audit_emergent_potential,
    build_connection_for_atoms,
    build_demo_fixture_anchor,
    handle_emergent_potential_command,
    is_emergent_potential_intent,
)


def test_emerge_returns_report_not_unified_diff():
    rendered = handle_emergent_potential_command("emerge --top 2", build_demo_fixture_anchor())

    assert rendered.startswith("# Emergent Properties and Future Potential")
    assert "diff --git" not in rendered
    assert "\n--- " not in rendered
    assert "REPORT_ONLY" in rendered


def test_emerge_json_returns_valid_json():
    raw = handle_emergent_potential_command("emerge --json --top 2", build_demo_fixture_anchor())

    payload = json.loads(raw)
    assert payload["route"] == AUDIT_ROUTE
    assert payload["safe_to_patch"] is False
    assert payload["connections"]


def test_demo_topology_produces_expected_unwired_candidates():
    report = audit_emergent_potential(build_demo_fixture_anchor(), top=8)
    abilities = {connection.emergent_ability for connection in report.connections}

    assert "Research Manifest -> Empirical Software Lab" in abilities
    assert "Coding Arena -> Capsule Compiler" in abilities


def test_missing_source_spans_mark_needs_grounding():
    proposed = AbilityAtom(
        ability_id="proposed",
        file="",
        symbol="voice command router",
        kind="function",
        evidence=[],
    )
    target = AbilityAtom(
        ability_id="target",
        file="aura_coding_arena_server.py",
        symbol="serve",
        kind="function",
        evidence=[{"file": "aura_coding_arena_server.py", "symbol": "serve"}],
    )

    connection = build_connection_for_atoms(proposed, target)

    assert connection.status == STATUS_NEEDS_GROUNDING


def test_source_spans_and_tests_can_be_future_patchable():
    left = AbilityAtom(
        ability_id="left",
        file="aura_research_manifest.py",
        symbol="load_research_manifest",
        kind="function",
        tests=["test_aura_research_manifest.py"],
        evidence=[{"file": "aura_research_manifest.py", "symbol": "load_research_manifest", "source_span": [1, 3], "source_hash": "abc", "roles": ["research_manifest"]}],
    )
    right = AbilityAtom(
        ability_id="right",
        file="aura_empirical_software_lab.py",
        symbol="define_empirical_task",
        kind="function",
        tests=["test_aura_empirical_software_lab.py"],
        evidence=[{"file": "aura_empirical_software_lab.py", "symbol": "define_empirical_task", "source_span": [4, 8], "source_hash": "def", "roles": ["empirical_lab"]}],
    )

    connection = build_connection_for_atoms(
        left,
        right,
        role_pair=("research_manifest", "empirical_lab"),
        confidence=0.8,
    )

    assert connection.status == STATUS_FUTURE_PATCHABLE
    assert connection.future_patch_capsule_hint is not None


def test_proposed_new_function_mode_returns_possible_combinations():
    raw = handle_emergent_potential_command(
        'emerge --new "voice command router" --with aura_coding_arena_3d.py --json --top 3',
        build_demo_fixture_anchor(),
    )
    payload = json.loads(raw)

    assert payload["future_query"]["new_function_description"] == "voice command router"
    assert payload["connections"]
    assert payload["connections"][0]["status"] == STATUS_NEEDS_GROUNDING
    assert payload["connections"][0]["source"]["symbol"] == "voice command router"


def test_no_external_api_calls_occur(monkeypatch):
    called = False

    def fail_urlopen(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("network call attempted")

    monkeypatch.setattr(urllib.request, "urlopen", fail_urlopen)

    handle_emergent_potential_command("emerge --top 2", build_demo_fixture_anchor())

    assert called is False


def test_default_mode_does_not_write_files(tmp_path: Path, monkeypatch):
    (tmp_path / "aura_research_manifest.py").write_text(
        "def load_research_manifest():\n    return 'research manifest acceptance_test'\n",
        encoding="utf-8",
    )
    (tmp_path / "aura_empirical_software_lab.py").write_text(
        "def score_empirical_task():\n    return 'empirical candidate_tree scorecard metric'\n",
        encoding="utf-8",
    )
    before = {path.name: path.read_text(encoding="utf-8") for path in tmp_path.glob("*.py")}

    def fail_write_text(self, *args, **kwargs):
        raise AssertionError(f"unexpected write to {self}")

    monkeypatch.setattr(Path, "write_text", fail_write_text)

    handle_emergent_potential_command("emerge --top 5", tmp_path)

    after = {path.name: path.read_text(encoding="utf-8") for path in tmp_path.glob("*.py")}
    assert after == before


def test_grounding_routes_broad_future_potential_away_from_patch_mode(tmp_path: Path):
    (tmp_path / "aura_research_manifest.py").write_text(
        "def load_research_manifest():\n    return 'research manifest acceptance_test'\n",
        encoding="utf-8",
    )

    packet = ground_coding_arena_intent("find emergent properties and future potential", tmp_path)

    assert packet["route"] == AUDIT_ROUTE
    assert packet["safe_to_patch"] is False
    assert packet["target_file"] is None
    assert packet["route_diagnostics"]["safe_to_patch"] is False


def test_explicit_patch_intent_is_not_emergent_report_route():
    assert is_emergent_potential_intent("patch candidate 2") is False
    assert is_emergent_potential_intent("implement candidate X") is False
    assert is_emergent_potential_intent("what is the future of this project?") is False
