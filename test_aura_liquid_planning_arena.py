from aura_liquid_planning_arena import (
    CivicArenaAdapter,
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
    assert "claim legal approval" in civic_action.forbidden_actions
    assert civic_action.expected_output == "CIVIC_INTERVENTION_PLAN"
    assert "bookable_options" in travel.schema()["domain_objects"]
    assert "book without approval" in travel_action.forbidden_actions
    assert travel_action.expected_output == "TRAVEL_PLAN_OPTIONS"


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
