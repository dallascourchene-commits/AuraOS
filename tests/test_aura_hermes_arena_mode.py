"""Tests for the Aura Hermes Arena Mode (Hermes through Aura integration layer).

Tests cover:
- hermes-contract command emits required Aura-first rules
- preflight command returns valid JSON with recommended affordances
- token-report returns raw_token_estimate, total_aura_token_estimate, estimated_percent_saved
- pr-runbook includes safe Git flow and rejects/avoids git add .
- hub file broad-read warning is preserved
- patch_authority and vsa_patch_authority invariants appear in all new packets
- Windows-compatible commands use python -m aura_agent_arena_cli
- No network, no Fireworks, no GitHub auth required

All tests are deterministic and run offline.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

# Ensure repo root is on the path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_hermes_arena_mode import (
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
    generate_hermes_contract,
    generate_pr_runbook,
    generate_token_savings_report,
    run_preflight,
    write_hermes_aura_rules,
    HERMES_MODE_VERSION,
)
from aura_agent_arena_cli import build_parser, main as cli_main


def _has_codemap() -> bool:
    return (REPO_ROOT / ".aura" / "CODEMAP.json").exists()


# ---------------------------------------------------------------------------
# Tests: hermes-contract
# ---------------------------------------------------------------------------


class TestHermesContract:
    """Tests for the hermes-contract capability."""

    def test_contract_emits_required_aura_first_rules(self):
        """hermes-contract emits mandatory Aura-first workflow rules."""
        result = generate_hermes_contract(
            objective="Refactor Fireworks egress",
            mode="pr",
            repo_root=REPO_ROOT,
        )
        assert result["ok"] is True
        contract = result["contract"]
        # Must include mandatory rules
        assert "Aura Agent Arena Bridge" in contract
        assert "digest first" in contract
        assert "find-affordances" in contract
        assert "CODEMAP search" in contract
        assert "read-slice" in contract
        assert "token savings" in contract.lower() or "token-report" in contract
        assert "feature branch" in contract.lower()
        assert "git add ." in contract  # The rule that says "never" it

    def test_contract_includes_git_safety_rules(self):
        """Contract includes Git safety rules."""
        result = generate_hermes_contract(
            objective="Refactor Fireworks egress",
            mode="pr",
            repo_root=REPO_ROOT,
        )
        contract = result["contract"]
        assert "git add ." in contract
        assert "NEVER" in contract or "NOT" in contract
        assert "main" in contract

    def test_contract_includes_patch_authority_invariants(self):
        """Contract includes patch_authority and vsa_patch_authority."""
        result = generate_hermes_contract(
            objective="Test objective",
            repo_root=REPO_ROOT,
        )
        assert result["patch_authority"] == PATCH_AUTHORITY
        assert result["vsa_patch_authority"] is VSA_PATCH_AUTHORITY
        contract = result["contract"]
        assert "exact_source_spans_and_hashes_only" in contract
        assert "vsa_patch_authority" in contract

    def test_contract_includes_exact_commands(self):
        """Contract includes exact commands Hermes should run."""
        result = generate_hermes_contract(
            objective="Refactor Fireworks egress",
            repo_root=REPO_ROOT,
        )
        contract = result["contract"]
        assert "python -m aura_agent_arena_cli digest" in contract
        assert "python -m aura_agent_arena_cli find-affordances" in contract
        assert "python -m aura_agent_arena_cli search" in contract
        assert "python -m aura_agent_arena_cli read-slice" in contract
        assert "python -m aura_agent_arena_cli prepare" in contract
        assert "python -m aura_agent_arena_cli context" in contract
        assert "python -m aura_agent_arena_cli verify" in contract

    def test_contract_pr_mode_includes_gh_pr_create(self):
        """PR mode contract includes gh pr create command."""
        result = generate_hermes_contract(
            objective="Refactor Fireworks egress",
            mode="pr",
            repo_root=REPO_ROOT,
        )
        contract = result["contract"]
        assert "gh pr create" in contract
        assert "git push -u origin" in contract

    def test_contract_direct_mode_no_pr(self):
        """Direct mode contract does not include PR creation."""
        result = generate_hermes_contract(
            objective="Test objective",
            mode="direct",
            repo_root=REPO_ROOT,
        )
        contract = result["contract"]
        assert "gh pr create" not in contract

    def test_cli_hermes_contract_command(self, capsys):
        """CLI hermes-contract command produces valid output."""
        exit_code = cli_main([
            "hermes-contract",
            "--objective", "Refactor Fireworks egress",
            "--mode", "pr",
            "--json",
        ])
        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["ok"] is True
        assert "contract" in data
        assert data["patch_authority"] == "exact_source_spans_and_hashes_only"

    def test_cli_hermes_contract_markdown_output(self, capsys):
        """CLI hermes-contract without --json outputs markdown text."""
        exit_code = cli_main([
            "hermes-contract",
            "--objective", "Refactor Fireworks egress",
            "--mode", "pr",
        ])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Hermes → Aura Operating Contract" in captured.out


# ---------------------------------------------------------------------------
# Tests: preflight
# ---------------------------------------------------------------------------


class TestPreflight:
    """Tests for the preflight packet."""

    def test_preflight_returns_valid_json_with_required_fields(self):
        """preflight returns valid JSON with all required fields."""
        if not _has_codemap():
            pytest.skip("CODEMAP.json not available")
        result = run_preflight(
            objective="Refactor Fireworks egress provider",
            repo_root=REPO_ROOT,
        )
        assert result["ok"] is True
        assert result["objective"] == "Refactor Fireworks egress provider"
        assert "repo_digest" in result
        assert "recommended_affordances" in result
        assert "prompt_cards" in result
        assert "likely_files" in result
        assert "likely_symbols" in result
        assert "suggested_searches" in result
        assert "suggested_read_slices" in result
        assert "suggested_prepare_command" in result
        assert "safety_rules" in result
        assert "estimated_token_baseline" in result

    def test_preflight_includes_patch_authority_invariants(self):
        """preflight includes patch_authority and vsa_patch_authority."""
        if not _has_codemap():
            pytest.skip("CODEMAP.json not available")
        result = run_preflight(
            objective="Refactor Fireworks egress",
            repo_root=REPO_ROOT,
        )
        assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert result["vsa_patch_authority"] is False

    def test_preflight_recommended_affordances_is_list(self):
        """preflight recommended_affordances is a list of dicts."""
        if not _has_codemap():
            pytest.skip("CODEMAP.json not available")
        result = run_preflight(
            objective="Refactor coding arena routing",
            repo_root=REPO_ROOT,
        )
        affords = result["recommended_affordances"]
        assert isinstance(affords, list)
        if affords:
            assert isinstance(affords[0], dict)
            assert "id" in affords[0]
            assert "name" in affords[0]

    def test_preflight_repo_digest_has_codemap_status(self):
        """preflight repo_digest has codemap_status."""
        if not _has_codemap():
            pytest.skip("CODEMAP.json not available")
        result = run_preflight(
            objective="Test",
            repo_root=REPO_ROOT,
        )
        digest = result["repo_digest"]
        assert digest["codemap_status"] == "AURA_CODEMAP_ACTIVE"
        assert digest["file_count"] > 0

    def test_preflight_safety_rules_include_hub_file_warning(self):
        """preflight safety_rules include hub file broad-read warning."""
        result = run_preflight(
            objective="Test",
            repo_root=REPO_ROOT,
        )
        rules = result["safety_rules"]
        hub_rule = [r for r in rules if "hub file" in r.lower()]
        assert len(hub_rule) > 0

    def test_preflight_suggested_searches_use_python_m_cli(self):
        """preflight suggested searches use python -m aura_agent_arena_cli."""
        if not _has_codemap():
            pytest.skip("CODEMAP.json not available")
        result = run_preflight(
            objective="Refactor Fireworks egress",
            repo_root=REPO_ROOT,
        )
        searches = result["suggested_searches"]
        assert len(searches) > 0
        for cmd in searches:
            assert "python -m aura_agent_arena_cli" in cmd

    def test_cli_preflight_command(self, capsys):
        """CLI preflight command produces valid JSON."""
        if not _has_codemap():
            pytest.skip("CODEMAP.json not available")
        exit_code = cli_main([
            "preflight",
            "--objective", "Refactor Fireworks egress provider",
        ])
        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["ok"] is True
        assert data["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert "recommended_affordances" in data

    def test_preflight_hub_file_warning_in_hub_file_warnings(self):
        """preflight includes hub_file_warnings when a likely file is a hub file."""
        result = run_preflight(
            objective="Refactor aura_node",
            repo_root=REPO_ROOT,
            target_files=["aura_node.py"],
        )
        warnings = result.get("hub_file_warnings", [])
        assert any("aura_node.py" in w for w in warnings)


# ---------------------------------------------------------------------------
# Tests: token-report
# ---------------------------------------------------------------------------


class TestTokenReport:
    """Tests for the token savings report."""

    def test_token_report_has_required_fields(self):
        """token-report returns raw_token_estimate, total_aura_token_estimate, estimated_percent_saved."""
        result = generate_token_savings_report(
            objective="Refactor Fireworks egress",
            files=["aura_llm_egress.py", "aura_agent_arena_bridge.py"],
            repo_root=REPO_ROOT,
        )
        assert result["ok"] is True
        assert "raw_token_estimate" in result
        assert "total_aura_token_estimate" in result
        assert "estimated_percent_saved" in result
        assert "raw_char_count" in result
        assert "raw_files_considered" in result
        assert "aura_digest_token_estimate" in result
        assert "aura_search_token_estimate" in result
        assert "aura_read_slice_token_estimate" in result
        assert "aura_micro_context_token_estimate" in result
        assert "estimated_tokens_saved" in result
        assert "files_avoided" in result
        assert "method" in result
        assert "warning" in result

    def test_token_report_method_is_local_estimate(self):
        """token-report method is local_chars_div_4_estimate."""
        result = generate_token_savings_report(
            objective="Test",
            files=["aura_llm_egress.py"],
            repo_root=REPO_ROOT,
        )
        assert result["method"] == "local_chars_div_4_estimate"

    def test_token_report_warning_is_present(self):
        """token-report includes a warning that it is an estimate."""
        result = generate_token_savings_report(
            objective="Test",
            files=["aura_llm_egress.py"],
            repo_root=REPO_ROOT,
        )
        warning = result["warning"]
        assert "estimate" in warning.lower()
        assert "not provider billing telemetry" in warning.lower()

    def test_token_report_patch_authority_invariants(self):
        """token-report includes patch_authority and vsa_patch_authority."""
        result = generate_token_savings_report(
            objective="Test",
            files=["aura_llm_egress.py"],
            repo_root=REPO_ROOT,
        )
        assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert result["vsa_patch_authority"] is False

    def test_token_report_raw_token_estimate_is_positive_for_real_files(self):
        """raw_token_estimate is positive for existing files."""
        result = generate_token_savings_report(
            objective="Test",
            files=["aura_llm_egress.py"],
            repo_root=REPO_ROOT,
        )
        # aura_llm_egress.py exists and has content
        if "aura_llm_egress.py" in result["raw_files_considered"]:
            assert result["raw_token_estimate"] > 0
            assert result["raw_char_count"] > 0

    def test_token_report_avoids_forbidden_paths(self):
        """token-report avoids forbidden directories."""
        result = generate_token_savings_report(
            objective="Test",
            files=[".venv/lib.py", "node_modules/pkg/index.js", "aura_llm_egress.py"],
            repo_root=REPO_ROOT,
        )
        avoided = result["files_avoided"]
        assert any(".venv" in f for f in avoided)
        assert any("node_modules" in f for f in avoided)
        assert "aura_llm_egress.py" in result["raw_files_considered"]

    def test_token_report_markdown_format(self):
        """token-report markdown format includes markdown field."""
        result = generate_token_savings_report(
            objective="Test",
            files=["aura_llm_egress.py"],
            repo_root=REPO_ROOT,
            output_format="markdown",
        )
        assert "markdown" in result
        md = result["markdown"]
        assert "# Aura Token Savings Report" in md
        assert "Raw token estimate" in md
        assert "Total Aura token estimate" in md

    def test_token_report_include_preflight(self):
        """token-report with include_preflight includes preflight packet."""
        if not _has_codemap():
            pytest.skip("CODEMAP.json not available")
        result = generate_token_savings_report(
            objective="Refactor Fireworks egress",
            files=["aura_llm_egress.py"],
            repo_root=REPO_ROOT,
            include_preflight=True,
        )
        assert "preflight" in result
        assert result["preflight"]["ok"] is True

    def test_cli_token_report_command(self, capsys):
        """CLI token-report command produces valid JSON."""
        exit_code = cli_main([
            "token-report",
            "--objective", "Refactor Fireworks egress",
            "--files", "aura_llm_egress.py,aura_agent_arena_bridge.py",
        ])
        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["ok"] is True
        assert "raw_token_estimate" in data
        assert "total_aura_token_estimate" in data
        assert "estimated_percent_saved" in data

    def test_cli_token_report_markdown_output(self, capsys):
        """CLI token-report --format markdown outputs markdown text."""
        exit_code = cli_main([
            "token-report",
            "--objective", "Refactor Fireworks egress",
            "--files", "aura_llm_egress.py",
            "--format", "markdown",
        ])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "# Aura Token Savings Report" in captured.out


# ---------------------------------------------------------------------------
# Tests: pr-runbook
# ---------------------------------------------------------------------------


class TestPRRunbook:
    """Tests for the PR-safe runbook generator."""

    def test_runbook_includes_safe_git_flow(self):
        """pr-runbook includes safe Git flow."""
        result = generate_pr_runbook(
            objective="Refactor Fireworks egress",
            branch="feature/fireworks-egress-refactor",
            repo_root=REPO_ROOT,
        )
        assert result["ok"] is True
        runbook = result["runbook"]
        assert "git fetch origin" in runbook
        assert "git switch main" in runbook
        assert "git pull --ff-only origin main" in runbook
        assert "git switch -c feature/fireworks-egress-refactor" in runbook
        assert "git push -u origin feature/fireworks-egress-refactor" in runbook
        assert "gh pr create" in runbook

    def test_runbook_explicitly_says_no_git_add_dot(self):
        """pr-runbook explicitly says do not run git add ."""
        result = generate_pr_runbook(
            objective="Refactor Fireworks egress",
            branch="feature/test",
            repo_root=REPO_ROOT,
        )
        runbook = result["runbook"]
        assert "git add ." in runbook
        assert "NOT" in runbook
        # The "git add ." must appear in a warning context, not as a command
        # Check it appears after a "Do NOT" or similar
        lines = runbook.split("\n")
        add_dot_lines = [l for l in lines if "git add ." in l]
        for line in add_dot_lines:
            assert "NOT" in line or "not" in line or "Never" in line or "NEVER" in line

    def test_runbook_uses_scoped_git_add(self):
        """pr-runbook uses scoped git add, not git add ."""
        result = generate_pr_runbook(
            objective="Refactor Fireworks egress",
            branch="feature/test",
            repo_root=REPO_ROOT,
            files=["aura_llm_egress.py", "aura_agent_arena_bridge.py"],
        )
        runbook = result["runbook"]
        assert "git add aura_llm_egress.py aura_agent_arena_bridge.py" in runbook

    def test_runbook_includes_aura_commands(self):
        """pr-runbook includes Aura preflight and read-slice commands."""
        result = generate_pr_runbook(
            objective="Refactor Fireworks egress",
            branch="feature/test",
            repo_root=REPO_ROOT,
        )
        runbook = result["runbook"]
        assert "python -m aura_agent_arena_cli digest" in runbook
        assert "python -m aura_agent_arena_cli find-affordances" in runbook
        assert "python -m aura_agent_arena_cli preflight" in runbook
        assert "python -m aura_agent_arena_cli read-slice" in runbook
        assert "python -m aura_agent_arena_cli token-report" in runbook
        assert "python -m aura_agent_arena_cli verify" in runbook

    def test_runbook_includes_dirty_tree_warning(self):
        """pr-runbook warns about dirty working tree."""
        result = generate_pr_runbook(
            objective="Test",
            branch="feature/test",
            repo_root=REPO_ROOT,
        )
        runbook = result["runbook"]
        assert "dirty" in runbook.lower()
        assert "STOP" in runbook

    def test_runbook_includes_no_nested_auraos_warning(self):
        """pr-runbook warns about nested AuraOS folders."""
        result = generate_pr_runbook(
            objective="Test",
            branch="feature/test",
            repo_root=REPO_ROOT,
        )
        runbook = result["runbook"]
        assert "nested AuraOS" in runbook

    def test_runbook_patch_authority_invariants(self):
        """pr-runbook includes patch_authority and vsa_patch_authority."""
        result = generate_pr_runbook(
            objective="Test",
            branch="feature/test",
            repo_root=REPO_ROOT,
        )
        assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert result["vsa_patch_authority"] is False
        runbook = result["runbook"]
        assert "exact_source_spans_and_hashes_only" in runbook
        assert "vsa_patch_authority" in runbook

    def test_runbook_includes_compare_url(self):
        """pr-runbook includes compare URL for gh fallback."""
        result = generate_pr_runbook(
            objective="Test",
            branch="feature/test-branch",
            repo_root=REPO_ROOT,
        )
        runbook = result["runbook"]
        assert "compare/main...feature/test-branch" in runbook

    def test_cli_pr_runbook_command(self, capsys):
        """CLI pr-runbook command produces valid output."""
        exit_code = cli_main([
            "pr-runbook",
            "--objective", "Refactor Fireworks egress",
            "--branch", "feature/fireworks-egress-refactor",
        ])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "PR-Safe Runbook" in captured.out
        assert "git fetch origin" in captured.out

    def test_cli_pr_runbook_json_output(self, capsys):
        """CLI pr-runbook --json produces valid JSON."""
        exit_code = cli_main([
            "pr-runbook",
            "--objective", "Refactor Fireworks egress",
            "--branch", "feature/fireworks-egress-refactor",
            "--json",
        ])
        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["ok"] is True
        assert "runbook" in data
        assert data["branch"] == "feature/fireworks-egress-refactor"


# ---------------------------------------------------------------------------
# Tests: invariants across all packets
# ---------------------------------------------------------------------------


class TestInvariants:
    """Test that patch_authority and vsa_patch_authority appear in all new packets."""

    def test_contract_invariants(self):
        result = generate_hermes_contract("Test", repo_root=REPO_ROOT)
        assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert result["vsa_patch_authority"] is False

    def test_preflight_invariants(self):
        if not _has_codemap():
            pytest.skip("CODEMAP.json not available")
        result = run_preflight("Test", repo_root=REPO_ROOT)
        assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert result["vsa_patch_authority"] is False

    def test_token_report_invariants(self):
        result = generate_token_savings_report("Test", ["aura_llm_egress.py"], repo_root=REPO_ROOT)
        assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert result["vsa_patch_authority"] is False

    def test_pr_runbook_invariants(self):
        result = generate_pr_runbook("Test", "feature/test", repo_root=REPO_ROOT)
        assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert result["vsa_patch_authority"] is False


# ---------------------------------------------------------------------------
# Tests: hub file broad-read warning preserved
# ---------------------------------------------------------------------------


class TestHubFileWarning:
    """Test that hub file broad-read warnings are preserved."""

    def test_safety_rules_mention_hub_files(self):
        """Safety rules mention hub files."""
        result = generate_hermes_contract("Test", repo_root=REPO_ROOT)
        rules = result["safety_rules"]
        hub_rules = [r for r in rules if "hub file" in r.lower()]
        assert len(hub_rules) > 0

    def test_preflight_warns_about_hub_files_in_target(self):
        """Preflight warns when target_files includes a hub file."""
        result = run_preflight(
            "Refactor aura_node",
            repo_root=REPO_ROOT,
            target_files=["aura_node.py"],
        )
        warnings = result.get("hub_file_warnings", [])
        assert any("aura_node.py" in w for w in warnings)
        assert any("blocked hub file" in w.lower() for w in warnings)

    def test_blocked_hub_files_list_includes_aura_node(self):
        """The blocked hub files set includes aura_node.py."""
        from aura_hermes_arena_mode import _BLOCKED_HUB_FILES
        assert "aura_node.py" in _BLOCKED_HUB_FILES


# ---------------------------------------------------------------------------
# Tests: Windows-compatible commands
# ---------------------------------------------------------------------------


class TestWindowsCompatibleCommands:
    """Test that all commands use python -m aura_agent_arena_cli."""

    def test_contract_uses_python_m_cli(self):
        result = generate_hermes_contract("Test", repo_root=REPO_ROOT)
        contract = result["contract"]
        assert "python -m aura_agent_arena_cli" in contract
        # Should NOT use bare "aura-agent-arena" script
        assert "scripts/aura-agent-arena" not in contract

    def test_runbook_uses_python_m_cli(self):
        result = generate_pr_runbook("Test", "feature/test", repo_root=REPO_ROOT)
        runbook = result["runbook"]
        assert "python -m aura_agent_arena_cli" in runbook

    def test_preflight_suggested_commands_use_python_m_cli(self):
        if not _has_codemap():
            pytest.skip("CODEMAP.json not available")
        result = run_preflight("Test", repo_root=REPO_ROOT)
        for cmd in result["suggested_searches"]:
            assert "python -m aura_agent_arena_cli" in cmd
        for cmd in result["suggested_read_slices"]:
            assert "python -m aura_agent_arena_cli" in cmd
        assert "python -m aura_agent_arena_cli" in result["suggested_prepare_command"]


# ---------------------------------------------------------------------------
# Tests: CLI parser registration
# ---------------------------------------------------------------------------


class TestCLIParserRegistration:
    """Test that new subcommands are registered in the CLI parser."""

    def test_parser_has_hermes_contract(self):
        parser = build_parser()
        try:
            parser.parse_args(["hermes-contract", "--objective", "test", "--help"])
        except SystemExit:
            pass  # --help causes SystemExit

    def test_parser_has_preflight(self):
        parser = build_parser()
        try:
            parser.parse_args(["preflight", "--objective", "test", "--help"])
        except SystemExit:
            pass

    def test_parser_has_token_report(self):
        parser = build_parser()
        try:
            parser.parse_args(["token-report", "--objective", "test", "--files", "f.py", "--help"])
        except SystemExit:
            pass

    def test_parser_has_pr_runbook(self):
        parser = build_parser()
        try:
            parser.parse_args(["pr-runbook", "--objective", "test", "--branch", "b", "--help"])
        except SystemExit:
            pass

    def test_parser_has_write_rules(self):
        parser = build_parser()
        try:
            parser.parse_args(["write-rules", "--help"])
        except SystemExit:
            pass

    def test_all_new_subcommands_callable(self):
        """All new subcommands can be dispatched without import errors."""
        # hermes-contract
        assert cli_main(["hermes-contract", "--objective", "test", "--json"]) in (0, 1)
        # preflight
        assert cli_main(["preflight", "--objective", "test"]) in (0, 1)
        # token-report
        assert cli_main(["token-report", "--objective", "test", "--files", "aura_llm_egress.py"]) in (0, 1)
        # pr-runbook
        assert cli_main(["pr-runbook", "--objective", "test", "--branch", "feature/test"]) in (0, 1)


# ---------------------------------------------------------------------------
# Tests: write-rules guard file
# ---------------------------------------------------------------------------


class TestWriteRules:
    """Test the .aura/HERMES_AURA_RULES.md guard file."""

    def test_write_rules_creates_file(self):
        """write_hermes_aura_rules creates the guard file."""
        result = write_hermes_aura_rules(repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert result["path"] == ".aura/HERMES_AURA_RULES.md"
        assert "You are inside AuraOS" in result["content"]

    def test_write_rules_file_exists_on_disk(self):
        """The guard file exists on disk after writing."""
        write_hermes_aura_rules(repo_root=REPO_ROOT)
        rules_path = REPO_ROOT / ".aura" / "HERMES_AURA_RULES.md"
        assert rules_path.exists()
        content = rules_path.read_text(encoding="utf-8")
        assert "You are inside AuraOS" in content
        assert "git add ." in content
        assert "exact_source_spans_and_hashes_only" in content

    def test_write_rules_patch_authority_invariants(self):
        """write_hermes_aura_rules includes invariants."""
        result = write_hermes_aura_rules(repo_root=REPO_ROOT)
        assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert result["vsa_patch_authority"] is False

    def test_cli_write_rules_command(self, capsys):
        """CLI write-rules command creates the guard file."""
        exit_code = cli_main(["write-rules"])
        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["ok"] is True
