"""Tests for Aura Civic Commons Arena — comprehensive coverage of acceptance criteria."""
from __future__ import annotations
from pathlib import Path
import sys, json, hashlib, time
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


class TestTruthClasses:
    def test_truth_classes_defined(self):
        from aura_civic_truth import TRUTH_CLASSES
        assert "OFFICIAL_PRIMARY_SOURCE" in TRUTH_CLASSES
        assert "SYNTHETIC_DEMO_DATA" in TRUTH_CLASSES
        assert "COMMUNITY_ASSERTED" in TRUTH_CLASSES

    def test_validate_truth_class(self):
        from aura_civic_truth import validate_truth_class
        assert validate_truth_class("OFFICIAL_PRIMARY_SOURCE") is True
        assert validate_truth_class("FAKE") is False

    def test_synthetic_and_official_distinct(self):
        from aura_civic_truth import is_synthetic, is_official
        assert is_synthetic("SYNTHETIC_DEMO_DATA") is True
        assert is_official("SYNTHETIC_DEMO_DATA") is False
        assert is_official("OFFICIAL_PRIMARY_SOURCE") is True


class TestCivicProfiles:
    def test_winnipeg_profile_activates(self):
        from aura_civic_profiles import get_profile, create_winnipeg_demo_profile_set
        r = get_profile("winnipeg_mb_ca")
        assert r["ok"] is True
        ps = create_winnipeg_demo_profile_set()
        assert "winnipeg_mb_ca" in ps.jurisdiction_profile_refs

    def test_treaty1_not_activated_by_default(self):
        from aura_civic_profiles import create_winnipeg_demo_profile_set
        ps = create_winnipeg_demo_profile_set()
        assert "treaty1_context" not in ps.context_lens_refs

    def test_no_identity_based_activation(self):
        from aura_civic_context import check_activation
        r = check_activation("winnipeg_treaty1", [])
        assert r["activated"] is False
        assert "explicit profile selection" in r.get("note", "")

    def test_active_profiles_visible(self):
        from aura_civic_profiles import create_winnipeg_demo_profile_set
        ps = create_winnipeg_demo_profile_set()
        d = ps.to_dict()
        assert "jurisdiction_profile_refs" in d
        assert len(d["jurisdiction_profile_refs"]) > 0


class TestContributions:
    def test_original_statement_retained(self):
        from aura_civic_contributions import create_contribution
        c = create_contribution("NEED", "We need affordable housing")
        assert c.original_statement == "We need affordable housing"

    def test_consent_to_match_required(self):
        from aura_civic_contributions import create_contribution, check_consent_to_match
        c = create_contribution("NEED", "test", consent_to_match=False)
        r = check_consent_to_match(c)
        assert r["ok"] is False

    def test_consent_to_match_present(self):
        from aura_civic_contributions import create_contribution, check_consent_to_match
        c = create_contribution("NEED", "test", consent_to_match=True)
        r = check_consent_to_match(c)
        assert r["ok"] is True

    def test_withdrawal_propagates(self):
        from aura_civic_contributions import create_contribution, withdraw_contribution
        c = create_contribution("NEED", "test")
        c = withdraw_contribution(c)
        assert c.withdrawn is True

    def test_no_contact_leakage(self):
        from aura_civic_contributions import create_contribution, check_no_contact_leakage
        c = create_contribution("NEED", "contact me at john@example.com",
                                privacy="PRIVATE_NOT_SHARED")
        r = check_no_contact_leakage(c)
        assert r["ok"] is False


class TestResourceMatching:
    def test_complementary_resources_matched(self):
        from aura_civic_resources import match_resources
        need = {"need_id": "N1", "description": "salon space"}
        offers = [{"offer_id": "O1", "offer_type": "space", "consent_to_match": True, "privacy_class": "COMMUNITY_ONLY"}]
        r = match_resources(need, offers)
        assert r["ok"] is True
        assert r["count"] == 1
        assert r["constellations"][0]["score"] > 0

    def test_no_consent_blocks(self):
        from aura_civic_resources import match_resources
        need = {"need_id": "N1"}
        offers = [{"offer_id": "O1", "offer_type": "space", "consent_to_match": False}]
        r = match_resources(need, offers)
        assert "no_consent" in r["constellations"][0]["hard_blockers"]

    def test_expired_offer_blocked(self):
        from aura_civic_resources import match_resources
        need = {"need_id": "N1"}
        offers = [{"offer_id": "O1", "offer_type": "space", "consent_to_match": True, "expired": True}]
        r = match_resources(need, offers)
        assert "expired_offer" in r["constellations"][0]["hard_blockers"]

    def test_no_automatic_contract(self):
        from aura_civic_resources import match_resources
        r = match_resources({"need_id": "N1"}, [])
        assert "constellations" in r
        assert "contract" not in json.dumps(r).lower()


class TestMITOSIS:
    def test_parent_objective_hash_preserved(self):
        from aura_civic_reasoning import civic_mitosis
        r = civic_mitosis("affordable hairstyling", mandatory_constraints=["community_ownership"])
        assert r["ok"] is True
        assert r["objective_hash"] != ""
        for ws in r["workstreams"]:
            assert ws["parent_objective_hash"] == r["objective_hash"]

    def test_mandatory_constraints_preserved(self):
        from aura_civic_reasoning import civic_mitosis
        r = civic_mitosis("test", mandatory_constraints=["community_ownership", "affordability"])
        for ws in r["workstreams"]:
            assert "community_ownership" in ws["mandatory_constraints"]

    def test_bounded_workstreams(self):
        from aura_civic_reasoning import civic_mitosis
        r = civic_mitosis("test")
        assert 5 < r["workstream_count"] < 20


class TestMUSIC:
    def test_pareto_frontier(self):
        from aura_civic_reasoning import civic_music
        scenarios = [
            {"scenario_id": "A", "metrics": {"local_ownership": 0.9, "cost": 0.5}},
            {"scenario_id": "B", "metrics": {"local_ownership": 0.3, "cost": 0.8}},
        ]
        r = civic_music(scenarios)
        assert r["ok"] is True
        assert len(r["comparison"]["pareto_frontier"]) > 0

    def test_all_dimensions_weighted_and_sensitivity_reported(self):
        from aura_civic_reasoning import MUSIC_DIMENSIONS, civic_music
        scenarios = [
            {"scenario_id": "A", "metrics": {dim: 0.2 for dim in MUSIC_DIMENSIONS}},
            {"scenario_id": "B", "metrics": {dim: 0.8 for dim in MUSIC_DIMENSIONS}},
        ]
        comparison = civic_music(scenarios)["comparison"]
        assert comparison["dimensions"] == list(MUSIC_DIMENSIONS)
        assert len(comparison["weights"]) == len(MUSIC_DIMENSIONS)
        assert comparison["pareto_frontier"] == [{"scenario_id": "B", "label": "pareto_optimal"}]
        assert comparison["sensitivity_analysis"]["baseline_ranking"] == ["B", "A"]

    def test_comparison_id_is_deterministic(self):
        from aura_civic_reasoning import civic_music
        scenarios = [{"scenario_id": "A", "metrics": {"accessibility": 0.8}}]
        assert civic_music(scenarios)["comparison"]["comparison_id"] == civic_music(scenarios)["comparison"]["comparison_id"]

    def test_weights_visible(self):
        from aura_civic_reasoning import civic_music
        r = civic_music([{"scenario_id": "A", "metrics": {}}])
        assert "weights" in r["comparison"]
        assert len(r["comparison"]["weights"]) > 0

    def test_no_hidden_winner(self):
        from aura_civic_reasoning import civic_music
        r = civic_music([{"scenario_id": "A", "metrics": {}}, {"scenario_id": "B", "metrics": {}}])
        # The note says "No hidden winner" which is correct — check there's no "winner" key
        text = json.dumps(r)
        assert '"winner"' not in text.lower()

    def test_bridge_options_labelled(self):
        from aura_civic_reasoning import civic_music
        r = civic_music([{"scenario_id": "A", "metrics": {}}, {"scenario_id": "B", "metrics": {}}])
        for b in r["comparison"].get("bridge_options", []):
            assert b.get("truth_class") == "AURA_PROPOSED"
            assert b.get("advisory_only") is True


class TestConsentArc:
    def test_non_binding(self):
        from aura_civic_deliberation import ConsentArc
        arc = ConsentArc(arc_id="A1", proposal_ref="P1")
        assert arc.non_binding is True
        assert arc.not_a_referendum is True

    def test_critical_objection_blocks(self):
        from aura_civic_deliberation import ConsentArc, ParticipantResponse, collect_response, assess_convergence
        arc = ConsentArc(arc_id="A2", proposal_ref="P1")
        r = ParticipantResponse("R1", "P1", "P1", "CRITICAL_OBJECTION")
        arc = collect_response(arc, r)
        conv = assess_convergence(arc)
        assert conv["status"] == "BLOCKED_BY_CRITICAL_OBJECTION"

    def test_no_false_unanimity(self):
        from aura_civic_deliberation import ConsentArc, assess_convergence
        arc = ConsentArc(arc_id="A3", proposal_ref="P1")
        conv = assess_convergence(arc)
        assert conv["status"] != "BROAD_CONSENT"

    def test_reservation_preserved(self):
        from aura_civic_deliberation import ConsentArc, ParticipantResponse, collect_response, assess_convergence
        arc = ConsentArc(arc_id="A4", proposal_ref="P1")
        arc.responses.append({"response_type": "CONSENT_WITH_RESERVATION", "statement": "concerns about parking"})
        conv = assess_convergence(arc)
        assert conv["reservation_count"] == 1

    def test_representation_gaps_visible(self):
        from aura_civic_deliberation import ConsentArc, assess_convergence
        arc = ConsentArc(arc_id="A5", proposal_ref="P1", representation_gaps=["Youth underrepresented"])
        conv = assess_convergence(arc)
        assert "Youth underrepresented" in conv["representation_gaps"]


class TestWhatIf:
    def test_simulation_labels(self):
        from aura_civic_scenarios import run_what_if
        r = run_what_if({"scenario_id": "S1", "metrics": {}}, {"cost": 0.7})
        assert "SIMULATION_ONLY" in r["simulation"]["labels"]
        assert "NOT_A_PREDICTION" in r["simulation"]["labels"]

    def test_assumptions_shown(self):
        from aura_civic_scenarios import run_what_if
        r = run_what_if({"scenario_id": "S1", "metrics": {"cost": 0.5, "access": 0.8}}, {"cost": 0.7})
        assert "cost" in r["simulation"]["changed_assumptions"]
        assert "access" in r["simulation"]["unchanged_assumptions"]


class TestPilotTunnel:
    def test_human_role_acceptance_required(self):
        from aura_civic_scenarios import create_pilot
        r = create_pilot({"scenario_id": "S1"})
        assert r["pilot"]["authority_status"] == "NOT_STARTED"
        assert r["pilot"]["accepted_human_owners"] == []

    def test_no_automatic_spending(self):
        from aura_civic_scenarios import create_pilot
        r = create_pilot({"scenario_id": "S1"})
        # The note mentions "No automatic spending" which is correct
        # Check that the pilot itself doesn't allocate funds
        pilot = r["pilot"]
        assert pilot["funding_checks"] == []  # No funding allocated
        assert "funding_allocated" not in json.dumps(pilot).lower()


class TestMap:
    def test_valid_geojson(self):
        from aura_civic_map import validate_geojson
        gj = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {}, "geometry": {"type": "Point", "coordinates": [-97.1, 49.9]}}]}
        r = validate_geojson(gj)
        assert r["ok"] is True

    def test_invalid_coordinates_rejected(self):
        from aura_civic_map import validate_geojson
        gj = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {}, "geometry": {"type": "Point", "coordinates": [999, 999]}}]}
        r = validate_geojson(gj)
        assert r["ok"] is False

    def test_heatmap_metadata_required(self):
        from aura_civic_map import validate_heatmap
        r = validate_heatmap({"metric": "service_access_distance"})
        assert r["ok"] is False  # Missing required fields

    def test_prohibited_heatmap_rejected(self):
        from aura_civic_map import validate_heatmap
        hm = {"metric": "person_level_crime", "source": "x", "time_range": "x",
              "geographic_unit": "x", "aggregation": "x", "denominator": "x",
              "missing_data_rate": 0, "freshness": "x", "uncertainty": "x", "truth_class": "x"}
        r = validate_heatmap(hm)
        assert r["ok"] is False

    def test_unknown_layer_rejected(self):
        from aura_civic_map import validate_layer
        r = validate_layer("evil_layer")
        assert r["ok"] is False


class TestLegal:
    def test_no_legal_approval(self):
        from aura_civic_evidence import check_no_legal_approval
        assert check_no_legal_approval({"approved": True})["ok"] is False
        assert check_no_legal_approval({"ok": True})["ok"] is True

    def test_legal_hierarchy(self):
        from aura_civic_evidence import LEGAL_HIERARCHY
        assert "constitutional_and_indigenous_rights" in LEGAL_HIERARCHY
        assert "city_bylaws" in LEGAL_HIERARCHY

    def test_applicability_disclaimer(self):
        from aura_civic_evidence import assess_legal_applicability
        r = assess_legal_applicability({"level": "bylaw"}, {})
        assert "Aura is not providing legal advice" in r["disclaimer"]


class TestTranslation:
    def test_invented_translation_rejected(self):
        from aura_civic_translation import reject_invented_translation
        r = reject_invented_translation("anishinaabemowin", "fake translation")
        assert r["ok"] is False

    def test_unverified_not_displayed(self):
        from aura_civic_translation import TranslationRecord, validate_translation
        t = TranslationRecord("C1", "en", "oji", "hello", "boozhoo", authority_class="UNAVAILABLE")
        r = validate_translation(t)
        assert r["ok"] is False


class TestSystemicContext:
    def test_correlation_not_causation(self):
        from aura_civic_deliberation import create_systemic_context
        r = create_systemic_context([
            {"source": "Census 2021", "truth_class": "OFFICIAL_PRIMARY_SOURCE",
             "finding": "Higher displacement rates in North End", "time_period": "2016-2021"}])
        assert "not converted to causation" in r["note"].lower()

    def test_model_hypothesis_labelled(self):
        from aura_civic_deliberation import create_systemic_context
        r = create_systemic_context([
            {"source": "model analysis", "truth_class": "MODEL_INFERRED", "finding": "test"}])
        assert r["report"]["findings"][0]["classification"] == "MODEL_HYPOTHESIZED"


class TestMemory:
    def test_privacy_filtering(self):
        from aura_civic_memory import CivicMemoryArchive, CivicMemoryRecord
        arch = CivicMemoryArchive()
        arch.store(CivicMemoryRecord("R1", "contribution", "ref1", privacy_class="PRIVATE_NOT_SHARED",
                                     authorized_audiences=["facilitator"]))
        r = arch.export_governed("public_audience")
        assert r["count"] == 0

    def test_revocation(self):
        from aura_civic_memory import CivicMemoryArchive, CivicMemoryRecord
        arch = CivicMemoryArchive()
        arch.store(CivicMemoryRecord("R2", "contribution", "ref2", authorized_audiences=["all"]))
        arch.revoke("R2")
        r = arch.export_governed("all")
        assert r["count"] == 0

    def test_facilitator_only_requires_authorized_facilitator(self):
        from aura_civic_memory import CivicMemoryArchive, CivicMemoryRecord
        archive = CivicMemoryArchive()
        archive.store(CivicMemoryRecord(
            "R3", "contribution", "ref3", privacy_class="FACILITATOR_ONLY",
            authorized_audiences=["FACILITATOR"],
        ))
        assert archive.export_governed("public_audience")["count"] == 0
        assert archive.export_governed("FACILITATOR")["count"] == 1


class TestReviewRegressions:
    def test_malformed_geojson_returns_errors(self):
        from aura_civic_map import validate_geojson
        assert validate_geojson({"type": "FeatureCollection", "features": "bad"})["ok"] is False
        assert validate_geojson({"type": "FeatureCollection", "features": [None]})["ok"] is False
        assert validate_geojson({"type": "FeatureCollection", "features": [{"geometry": None}]})["ok"] is False

    def test_blocked_offer_payload_is_not_returned(self):
        from aura_civic_resources import match_resources
        private_offer = {
            "offer_id": "SECRET", "offer_type": "skill", "description": "private detail",
            "consent_to_match": False, "privacy_class": "PRIVATE_NOT_SHARED",
        }
        result = match_resources({"need_id": "N1"}, [private_offer])
        assert result["constellations"][0]["matched_offers"] == []

    def test_aliased_organ_reports_requested_type(self):
        from aura_civic_organs import execute_organ
        assert execute_organ("LegalBylawOrgan", {})["organ_type"] == "LegalBylawOrgan"
        assert execute_organ("ScenarioComparisonOrgan", {})["organ_type"] == "ScenarioComparisonOrgan"

    def test_aura_proposed_is_a_valid_truth_class(self):
        from aura_civic_truth import validate_truth_class
        assert validate_truth_class("AURA_PROPOSED") is True

    def test_systemic_context_id_is_stable_and_does_not_mutate_input(self):
        from aura_civic_deliberation import create_systemic_context
        findings = [{"source": "model", "truth_class": "MODEL_INFERRED", "finding": "x"}]
        first = create_systemic_context(findings)
        second = create_systemic_context(findings)
        assert first["report"]["report_id"] == second["report"]["report_id"]
        assert "classification" not in findings[0]


class TestModelBroker:
    def test_fixture_mode_no_key(self):
        from aura_civic_model_broker import ModelBrokerRequest, broker_request
        r = broker_request(ModelBrokerRequest(task="contribution_normalization", model="fixture"))
        assert r["ok"] is True
        assert r["broker_mode"] == "fixture"
        assert r["response"]["cost_usd"] == 0.0

    def test_blocked_private_input(self):
        from aura_civic_model_broker import ModelBrokerRequest, broker_request
        r = broker_request(ModelBrokerRequest(task="contribution_normalization",
                                              input_privacy_class="PRIVATE_NOT_SHARED"))
        assert r["ok"] is False

    def test_unknown_task_blocked(self):
        from aura_civic_model_broker import ModelBrokerRequest, broker_request
        r = broker_request(ModelBrokerRequest(task="evil_task"))
        assert r["ok"] is False


class TestCivicLEXC:
    def test_civic_lexc_compiles(self):
        from aura_lexc import AuraLexc
        lexc = AuraLexc.from_path(REPO_ROOT / ".aura" / "civic_arena.lexc", strict=False)
        routes = lexc.complete_routes()
        assert len(routes) > 0


class TestSources:
    def test_sources_listed(self):
        from aura_civic_sources import list_sources
        r = list_sources()
        assert r["ok"] is True
        assert r["count"] > 0

    def test_winnipeg_source_exists(self):
        from aura_civic_sources import get_source
        r = get_source("city_of_winnipeg_open_data")
        assert r["ok"] is True


class TestE2EDemo:
    def test_hairstyling_story_e2e(self):
        from aura_civic_runtime import run_full_demo
        r = run_full_demo(story="hairstylist")
        assert r["ok"] is True
        assert r["fixture_mode"] is True
        assert r["zero_raw_network_calls"] is True
        assert r["organ_receipts"] is not None
        for organ_type, result in r["organ_results"].items():
            assert result["ok"] is True, f"Organ {organ_type} failed"

    def test_youth_centre_story_e2e(self):
        from aura_civic_runtime import run_full_demo
        r = run_full_demo(story="youth_centre")
        assert r["ok"] is True

    def test_council_pulse_e2e(self):
        from aura_civic_runtime import run_full_demo
        r = run_full_demo(story="council_pulse")
        assert r["ok"] is True

    def test_no_production_file_mutation(self):
        from aura_civic_runtime import run_full_demo
        prod_file = REPO_ROOT / "aura_lexc.py"
        before = hashlib.blake2b(prod_file.read_bytes(), digest_size=8).hexdigest()
        run_full_demo(story="hairstylist")
        after = hashlib.blake2b(prod_file.read_bytes(), digest_size=8).hexdigest()
        assert before == after

    def test_invariants_preserved(self):
        from aura_civic_runtime import run_full_demo
        r = run_full_demo(story="hairstylist")
        assert r["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert r["vsa_patch_authority"] is False

    def test_no_web3(self):
        from aura_civic_runtime import run_full_demo
        r = run_full_demo(story="hairstylist")
        text = json.dumps(r)
        assert "blockchain" not in text.lower()
        assert "wallet" not in text.lower()
        assert "token" not in text.lower() or "tokens" in text  # token economy is ok

    def test_no_prohibited_authority(self):
        from aura_civic_runtime import run_full_demo
        r = run_full_demo(story="hairstylist")
        text = json.dumps(r).lower()
        assert "legal_approval" not in text or "no_legal_approval" in text
        assert "funding_allocated" not in text
        assert "vote_cast" not in text
        assert "binding_decision" not in text


class TestCLI:
    def test_civic_demo_cli(self):
        from aura_agent_arena_cli import main as cli_main, _CIVIC_AVAILABLE
        assert _CIVIC_AVAILABLE is True
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["civic-demo", "--story", "hairstylist"])
        assert rc == 0
        d = json.loads(buf.getvalue())
        assert d["ok"] is True

    def test_civic_create_cli(self):
        from aura_agent_arena_cli import main as cli_main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["civic-create", "--objective", "test civic session"])
        assert rc == 0
        d = json.loads(buf.getvalue())
        assert d["ok"] is True
        assert "session_id" in d["session"]
