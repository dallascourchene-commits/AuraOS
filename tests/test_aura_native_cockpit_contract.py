"""Tests for Aura Native Cockpit contract.

Tests cover:
- Cockpit contract generation
- Intent ingestion from .aura.md file
- LEXC route validation
- Capability connectome has 18 nodes
- Capability path for an objective
- Token economy has savings_sources
- Workflow gates has 18 states
- Agent handoff packet
- CLI commands return valid JSON
- patch_authority invariant in all packets
- vsa_patch_authority false in all packets
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_native_cockpit import AuraNativeCockpit, COCKPIT_VERSION, PATCH_AUTHORITY, VSA_PATCH_AUTHORITY
from aura_agent_arena_cli import main as cli_main

EXAMPLE_INTENT = REPO_ROOT / ".aura" / "intents" / "example.aura.md"


class TestCockpitContract:
    def test_contract_generation(self):
        cockpit = AuraNativeCockpit(repo_root=REPO_ROOT)
        result = cockpit.cockpit_contract("Refactor Fireworks egress")
        assert result["ok"] is True
        assert "contract" in result
        assert "intent_packet" in result
        assert "capability_path" in result
        assert "token_economy" in result
        assert "workflow_gates" in result
        assert result["patch_authority"] == PATCH_AUTHORITY
        assert result["vsa_patch_authority"] is VSA_PATCH_AUTHORITY

    def test_contract_contains_objective(self):
        cockpit = AuraNativeCockpit(repo_root=REPO_ROOT)
        result = cockpit.cockpit_contract("Refactor Fireworks egress")
        assert "Refactor Fireworks egress" in result["contract"]

    def test_contract_contains_routing(self):
        cockpit = AuraNativeCockpit(repo_root=REPO_ROOT)
        result = cockpit.cockpit_contract("Refactor Fireworks egress")
        assert "Route:" in result["contract"]


class TestIntentIngestion:
    def test_ingest_example_file(self):
        if not EXAMPLE_INTENT.exists():
            pytest.skip("example.aura.md not found")
        cockpit = AuraNativeCockpit(repo_root=REPO_ROOT)
        result = cockpit.ingest_intent(str(EXAMPLE_INTENT), skip_grounding=True)
        assert result["ok"] is True
        assert result["objective"] != ""
        assert "polysynthetic_packet" in result
        assert "route_decision" in result

    def test_ingest_has_invariants(self):
        cockpit = AuraNativeCockpit(repo_root=REPO_ROOT)
        result = cockpit.ingest_intent("Refactor Fireworks egress", skip_grounding=True)
        assert result["patch_authority"] == PATCH_AUTHORITY
        assert result["vsa_patch_authority"] is VSA_PATCH_AUTHORITY


class TestLexcValidation:
    def test_validate_example(self):
        if not EXAMPLE_INTENT.exists():
            pytest.skip("example.aura.md not found")
        cockpit = AuraNativeCockpit(repo_root=REPO_ROOT)
        result = cockpit.validate_lexc_route(str(EXAMPLE_INTENT))
        assert result["ok"] is True
        assert "valid" in result


class TestCapabilityConnectome:
    def test_has_18_nodes(self):
        cockpit = AuraNativeCockpit(repo_root=REPO_ROOT)
        result = cockpit.capability_connectome()
        assert result["ok"] is True
        assert result["node_count"] >= 18


class TestCapabilityPath:
    def test_returns_path(self):
        cockpit = AuraNativeCockpit(repo_root=REPO_ROOT)
        result = cockpit.capability_path("refactor coding arena")
        assert result["ok"] is True
        assert len(result.get("path", [])) > 0


class TestTokenEconomy:
    def test_has_savings_sources(self):
        cockpit = AuraNativeCockpit(repo_root=REPO_ROOT)
        result = cockpit.token_economy("Refactor Fireworks egress", ["aura_llm_egress.py"])
        assert result["ok"] is True
        assert "savings_sources" in result
        assert len(result["savings_sources"]) > 0


class TestWorkflowGates:
    def test_has_18_states(self):
        cockpit = AuraNativeCockpit(repo_root=REPO_ROOT)
        result = cockpit.workflow_gates()
        states = result.get("states", [])
        gates = result.get("gates", [])
        assert len(states) == 18 or len(gates) == 18


class TestAgentHandoff:
    def test_handoff_packet(self):
        cockpit = AuraNativeCockpit(repo_root=REPO_ROOT)
        packet = cockpit.ingest_intent("Refactor Fireworks egress", skip_grounding=True)
        result = cockpit.prepare_handoff(packet, agent="hermes")
        assert result["ok"] is True
        assert result["agent"] == "hermes"
        assert "compressed_context" in result
        assert result["patch_authority"] == PATCH_AUTHORITY


class TestCLICommands:
    def test_cli_ingest_intent(self, capsys):
        if not EXAMPLE_INTENT.exists():
            pytest.skip("example.aura.md not found")
        rc = cli_main(["ingest-intent", "--file", str(EXAMPLE_INTENT)])
        assert rc in (0, 1)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "ok" in data

    def test_cli_native_cockpit_contract(self, capsys):
        rc = cli_main(["native-cockpit-contract", "--objective", "Test", "--json"])
        assert rc in (0, 1)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "ok" in data

    def test_cli_capability_connectome(self, capsys):
        rc = cli_main(["capability-connectome"])
        assert rc == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["ok"] is True

    def test_cli_token_economy(self, capsys):
        rc = cli_main(["token-economy", "--objective", "Test", "--files", "aura_llm_egress.py"])
        assert rc == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["ok"] is True
        assert "savings_sources" in data

    def test_cli_workflow_gates(self, capsys):
        rc = cli_main(["workflow-gates"])
        assert rc == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "states" in data or "gates" in data

    def test_cli_capability_path(self, capsys):
        rc = cli_main(["capability-path", "--objective", "refactor coding arena"])
        assert rc == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["ok"] is True


class TestInvariants:
    def test_cockpit_version(self):
        assert COCKPIT_VERSION == "AURA_NATIVE_COCKPIT_V1"

    def test_patch_authority(self):
        assert PATCH_AUTHORITY == "exact_source_spans_and_hashes_only"

    def test_vsa_patch_authority(self):
        assert VSA_PATCH_AUTHORITY is False
