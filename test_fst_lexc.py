from pathlib import Path

import pytest

from aura_fst_routing import FSTLexiconRoutingCore, SlotType
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
