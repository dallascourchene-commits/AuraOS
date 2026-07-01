from types import SimpleNamespace

from aura_liquid_planning_arena import (
    CivicArenaAdapter,
    CodeArenaAdapter,
    TravelArenaAdapter,
    build_world_state_delta,
)


def test_civic_and_travel_adapters_define_domain_neutral_action_capsules():
    civic = CivicArenaAdapter()
    civic_action = civic.action_capsule_from_intent(
        objective="Reduce commute friction around a transit corridor.",
        capsule_id="CIVIC-1",
        target={"neighborhood": "Ward 3", "service": "transit", "funding": "grant"},
    )
    travel = TravelArenaAdapter()
    travel_action = travel.action_capsule_from_intent(
        objective="Plan a low-stress family trip under a fixed budget.",
        capsule_id="TRAVEL-1",
        target={"destination": "Montreal", "budget": "2500", "time_window": "June"},
    )

    assert "legal_constraints" in civic.schema()["domain_objects"]
    assert "dream_evidence_scores" in civic.schema()["domain_objects"]
    assert "claim legal approval" in civic_action.forbidden_actions
    assert "rank evidence by downstream usefulness" in civic_action.allowed_actions
    assert civic_action.expected_output == "CIVIC_INTERVENTION_PLAN"
    assert "bookable_options" in travel.schema()["domain_objects"]
    assert "dream_usefulness_scores" in travel.schema()["domain_objects"]
    assert "book without approval" in travel_action.forbidden_actions
    assert "rank semantic pointers by downstream usefulness" in travel_action.allowed_actions
    assert travel_action.expected_output == "TRAVEL_PLAN_OPTIONS"


def test_code_adapter_skips_missing_target_file_in_scope_lists():
    adapter = CodeArenaAdapter()
    act = SimpleNamespace(
        task_id="A-1",
        role="cheap_builder",
        objective="Patch only the declared file.",
        target_file=None,
        target_symbol=None,
        related_files=[None, " demo.py ", "demo.py"],
        allowed_scope="demo.py",
        acceptance="demo test passes",
        expected_output="UNIFIED_DIFF",
        constraints=[],
        escalate_if=[],
    )

    contract = adapter.boundary_contract_for_act(act, None)
    action = adapter.action_capsule_from_act(act, None, contract)
    file_regions = [item["id"] for item in action.scope["regions"] if item["region_type"] == "file"]

    assert file_regions == ["demo.py"]
    assert contract.owned_scope == ["demo.py"]


def test_world_state_delta_tracks_added_removed_changed_and_stable_objects():
    delta = build_world_state_delta(
        domain="travel",
        before_objects=[
            {"id": "route:rail", "object_type": "route", "duration": 5},
            {"id": "hotel:a", "object_type": "bookable_option", "price": 100},
            {"id": "old-tour", "object_type": "bookable_option", "price": 50},
        ],
        after_objects=[
            {"id": "route:rail", "object_type": "route", "duration": 6},
            {"id": "hotel:a", "object_type": "bookable_option", "price": 100},
            {"id": "museum-pass", "object_type": "bookable_option", "price": 40},
        ],
    )

    assert delta.added == ["museum-pass"]
    assert delta.removed == ["old-tour"]
    assert delta.changed == ["route:rail"]
    assert delta.stable == ["hotel:a"]
    assert delta.object_type_counts["bookable_option"] == {"before": 2, "after": 2}
