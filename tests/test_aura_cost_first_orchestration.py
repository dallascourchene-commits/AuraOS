from core.aura_cost_first_orchestration import (
    AMORTIZATION_ARTIFACTS,
    CognitionRequest,
    choose_cognition_route,
)


def test_reuse_beats_every_provider():
    out = choose_cognition_route(
        CognitionRequest(
            "repeat-analysis",
            current_reuse_available=True,
            frontier_reasoning_earned=True,
            expensive_provider="kimi-k3",
            expensive_provider_authorized=True,
            expensive_cost_upper_bound_known=True,
        )
    )
    assert out["route"] == "REUSE_COORDINATE_MEMORY"


def test_auraos_deterministic_before_model():
    out = choose_cognition_route(CognitionRequest("digest", deterministic_sufficient=True))
    assert out["route"] == "AURAOS_NO_MODEL"


def test_interactive_chatgpt_control_plane_before_paid_api():
    out = choose_cognition_route(
        CognitionRequest(
            "top-level-plan",
            interactive_chatgpt_available=True,
            top_level_reasoning_needed=True,
        )
    )
    assert out["route"] == "CHATGPT_CONTROL_PLANE"


def test_local_model_before_paid_remote_when_sufficient():
    out = choose_cognition_route(
        CognitionRequest("bounded-local", local_model_available=True, local_model_sufficient=True)
    )
    assert out["route"] == "LOCAL_MODEL"


def test_deepseek_is_default_paid_remote_provider():
    out = choose_cognition_route(CognitionRequest("swarm-work"))
    assert out["route"] == "DEEPSEEK_SWARM"
    assert out["provider"] == "deepseek"
    assert out["requires_amortization"] == AMORTIZATION_ARTIFACTS


def test_no_implicit_paid_fallback_when_deepseek_unavailable():
    out = choose_cognition_route(
        CognitionRequest("swarm-work", deepseek_available=False)
    )
    assert out["route"] == "BLOCKED_DEEPSEEK_UNAVAILABLE"


def test_deepseek_unknown_cost_blocks_instead_of_assuming_free():
    out = choose_cognition_route(
        CognitionRequest("swarm-work", deepseek_cost_upper_bound_known=False)
    )
    assert out == {"route": "BLOCKED_ACCOUNTING_UNKNOWN", "provider": "deepseek"}


def test_expensive_frontier_requires_explicit_owner_authorization():
    out = choose_cognition_route(
        CognitionRequest(
            "deep-reasoning",
            frontier_reasoning_earned=True,
            expensive_provider="kimi-k3",
            expensive_cost_upper_bound_known=True,
        )
    )
    assert out["route"] == "BLOCKED_EXPENSIVE_PROVIDER_APPROVAL"


def test_expensive_frontier_requires_cost_bound():
    out = choose_cognition_route(
        CognitionRequest(
            "deep-reasoning",
            frontier_reasoning_earned=True,
            expensive_provider="kimi-k3",
            expensive_provider_authorized=True,
            expensive_cost_upper_bound_known=False,
        )
    )
    assert out == {"route": "BLOCKED_ACCOUNTING_UNKNOWN", "provider": "kimi-k3"}


def test_expensive_frontier_only_when_earned_and_authorized():
    out = choose_cognition_route(
        CognitionRequest(
            "deep-reasoning",
            frontier_reasoning_earned=True,
            expensive_provider="kimi-k3",
            expensive_provider_authorized=True,
            expensive_cost_upper_bound_known=True,
        )
    )
    assert out["route"] == "EXPENSIVE_FRONTIER_EXCEPTION"
    assert out["provider"] == "kimi-k3"
    assert out["requires_amortization"] == AMORTIZATION_ARTIFACTS


def test_d1_never_becomes_cost_optimization_problem():
    out = choose_cognition_route(CognitionRequest("consequential", consequence_class="D1"))
    assert out["route"] == "HUMAN_GATE"


def test_background_cannot_cross_gate10():
    out = choose_cognition_route(CognitionRequest("promotion", gate_target=11))
    assert out["route"] == "BLOCK"
