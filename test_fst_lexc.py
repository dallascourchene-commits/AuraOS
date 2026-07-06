from pathlib import Path

import pytest

from aura_fst_routing import AuraCodingArenaRouter, FSTLexiconRoutingCore, RoutingFrame, SlotType
from aura_lexc import SLOT_ORDER, AuraLexc, LexcCompileError

ROOT = Path(__file__).resolve().parent


def test_repository_lexicon_compiles_to_complete_six_slot_routes() -> None:
    compiled = AuraLexc.from_path(ROOT / "aura.lexc")

    assert not compiled.errors
    assert compiled.stats()["transitions"] > 40
    routes = compiled.complete_routes()
    assert routes
    assert all(route.slots == SLOT_ORDER for route in routes)
    assert all(route.states[0] == "Root" and route.states[-1] == "#" for route in routes)


def test_exact_six_slot_packet_validates_and_wrong_order_fails() -> None:
    compiled = AuraLexc.from_path(ROOT / "aura.lexc")
    route = compiled.complete_routes()[0]

    assert compiled.validate_symbols(route.symbols) == route
    swapped = list(route.symbols)
    swapped[1], swapped[2] = swapped[2], swapped[1]
    assert compiled.validate_symbols(swapped) is None
    assert compiled.validate_symbols(route.symbols[:-1]) is None


def test_malformed_lexicon_is_rejected_with_line_diagnostics() -> None:
    source = """
LEXICON Root
Data Gate ;
LEXICON Gate
+ASP:0 MissingTarget ;
"""
    with pytest.raises(LexcCompileError) as raised:
        AuraLexc.from_text(source)

    codes = {item.code for item in raised.value.diagnostics}
    assert "UNDEFINED_TARGET" in codes


def test_weighted_router_uses_repository_lexicon_and_requires_all_slots() -> None:
    router = FSTLexiconRoutingCore.from_lexc(str(ROOT / "aura.lexc"))
    route = router.find_optimal_path("Root", "#", cpu_temp=42.0)

    assert route is not None
    assert route.slot_sequence == [
        SlotType.DIR,
        SlotType.ASP,
        SlotType.CLASS,
        SlotType.SUBJ,
        SlotType.VOICE,
        SlotType.STEM,
    ]
    stats = router.get_stats()
    assert stats["source"] == "aura.lexc"
    assert stats["complete_six_slot_routes"] > 0
    assert stats["lexc_errors"] == 0


def test_coding_arena_router_compiles_structural_layer_hard_rules() -> None:
    router = AuraCodingArenaRouter()

    fake_symbol = router.route(
        RoutingFrame(
            intent="code_refactor",
            artifact="python_module",
            action="modify",
            scope="symbol",
            risk="medium",
            grounding=("file_exists",),
            tests="none",
            target_symbol="MissingArchitect",
        )
    )
    missing_tests = router.route(
        RoutingFrame(
            intent="code_refactor",
            action="modify",
            scope="symbol",
            risk="medium",
            grounding=("file_exists", "symbol_exists", "codemap_grounded"),
            tests="none",
            target_symbol="build_task_capsule",
        )
    )
    research = router.route(
        RoutingFrame(intent="research_rank", artifact="research_item", action="rank", scope="capsule", cost="no_model")
    )
    broad = router.route(
        RoutingFrame(intent="code_refactor", action="modify", scope="subsystem", risk="high", grounding=("file_exists",))
    )
    grounded = router.route(
        RoutingFrame(
            intent="code_refactor",
            action="modify",
            scope="symbol",
            risk="medium",
            grounding=("file_exists", "symbol_exists", "codemap_grounded", "tests_exist"),
            tests="existing",
            target_symbol="build_task_capsule",
        )
    )
    live = router.route(RoutingFrame(intent="code_refactor", action="inspect", risk="live", grounding=("full",), tests="existing"))
    live_missing_tests = router.route(
        RoutingFrame(
            intent="code_refactor",
            action="modify",
            risk="live",
            grounding=("file_exists", "symbol_exists", "codemap_grounded"),
            tests="none",
            target_symbol="build_task_capsule",
        )
    )
    repair = router.route(RoutingFrame(intent="repair", artifact="patch", action="repair", grounding=("file_exists",)))
    benchmark = router.route(RoutingFrame(intent="benchmark", action="inspect"))
    hotswap = router.route(
        RoutingFrame(
            intent="hotswap",
            artifact="patch",
            action="promote",
            risk="live",
            grounding=("symbol_exists", "codemap_grounded"),
            tests="existing",
        )
    )

    assert fake_symbol.route == "LOCALIZE_FIRST"
    assert fake_symbol.symbol_output() == "O:LOC|M:0|K:SUM|E:SYM0|V:0"
    assert missing_tests.route == "TEST_GAP_FILL"
    assert research.route == "MUSIC_RANK_ONLY"
    assert research.classification == "RESEARCH_ANALOGY_ONLY"
    assert broad.route == "PLAN_ONLY"
    assert grounded.route == "BUILDER_PATCH"
    assert grounded.symbol_output() == "O:BUILD|M:L|K:PAT|E:OK|V:1"
    assert live.route == "VERIFY_ONLY"
    assert live_missing_tests.route == "TEST_GAP_FILL"
    assert live_missing_tests.verifier_required is True
    assert repair.route == "REPAIR_PATCH"
    assert benchmark.route == "PLAN_ONLY"
    assert hotswap.route == "BLOCKED_WITH_REASON"
