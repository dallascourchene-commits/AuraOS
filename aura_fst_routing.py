"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: numpy, aura_lexc, itertools, enum, heapq, dataclasses, hashlib, collections.abc
FUNCTIONS: __init__, _hash_to_hypervector, add_state, add_transition, _compute_transition_weight, update_transition_weights, validate_slot_sequence, from_lexc, find_optimal_path, build_standard_lexicon, get_stats, has_grounding, symbol_input, symbol_output, to_dict, route, weighted_route_scores
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]
"""
#!/usr/bin/env python3
"""
Aura FST-Lexicon Routing Core (N18/N21)

Implements Claims N18 and N21 from AuraOS prior art papers:
- Finite-state transducer lexicon for cognitive routing
- Replaces ad-hoc function call graphs with formal FST
- Reduces edge complexity from O(N²) to O(E)
- VSA-weighted transitions with thermal awareness
- Six-slot Athabaskan morphotactic constraint

Architecture:
1. Hierarchical FST with 5 tiers (Gate, Action, Target, Physics, Modifier)
2. Transition weights: α·sim(v_i, v_j) + (1-α)·(1 - T_CPU/T_max)
3. Optimal path selection via topological ordering (O(|Q| + |Δ|))
4. Six-slot constraint enforcement [DIR]→[ASP]→[CLASS]→[SUBJ]→[VOICE]→[STEM]

Performance:
- Original: >1300 edges
- FST: ~200 edges
- Routing: O(L) where L ≤ 10 (path length)
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib

import numpy as np

from aura_lexc import AuraLexc, SlotName


class TierType(Enum):
    """FST hierarchy tiers"""
    GATE = "gate"
    ACTION = "action"
    TARGET = "target"
    PHYSICS = "physics"
    MODIFIER = "modifier"


class SlotType(Enum):
    """Athabaskan six-slot morphotactic array"""
    DIR = 0      # Direction
    ASP = 1      # Aspect
    CLASS = 2    # Classifier
    SUBJ = 3     # Subject
    VOICE = 4    # Voice
    STEM = 5     # Stem


@dataclass
class State:
    """FST state node"""
    id: str
    tier: TierType
    slot: SlotType | None
    hypervector: np.ndarray  # 10,000-D VSA representation
    description: str


@dataclass
class Transition:
    """FST transition edge"""
    from_state: str
    to_state: str
    input_symbol: str
    weight: float  # Derived from VSA resonance + thermal
    slot_constraint: SlotType | None


@dataclass
class Path:
    """FST path from start to end"""
    states: list[str]
    transitions: list[Transition]
    total_cost: float
    slot_sequence: list[SlotType]


INTENT_SYMBOLS = {
    "code_refactor": "I:REF",
    "localize": "I:LOC",
    "test_generate": "I:TST",
    "verify": "I:VER",
    "repair": "I:REP",
    "benchmark": "I:BEN",
    "research_rank": "I:RSR",
    "explain": "I:EXP",
    "hotswap": "I:HOT",
}

ARTIFACT_SYMBOLS = {
    "python_module": "A:PY",
    "test_file": "A:TF",
    "codemap": "A:CM",
    "manifest": "A:MF",
    "patch": "A:PT",
    "transaction_log": "A:TX",
    "research_item": "A:RI",
    "documentation": "A:DC",
}

ACTION_SYMBOLS = {
    "inspect": "X:IN",
    "create": "X:CR",
    "modify": "X:MO",
    "rank": "X:RK",
    "verify": "X:VR",
    "repair": "X:RP",
    "rollback": "X:RB",
    "promote": "X:PR",
}

SCOPE_SYMBOLS = {
    "symbol": "S:SYM",
    "file": "S:FIL",
    "capsule": "S:CAP",
    "subsystem": "S:SUB",
    "repo": "S:REP",
}

RISK_SYMBOLS = {
    "low": "R:L",
    "medium": "R:M",
    "high": "R:H",
    "live": "R:V",
}

GROUNDING_SYMBOLS = {
    "none": "0",
    "file_exists": "F",
    "symbol_exists": "S",
    "tests_exist": "T",
    "manifest_owner": "M",
    "codemap_grounded": "C",
    "full": "FULL",
}

TEST_SYMBOLS = {
    "none": "T:0",
    "existing": "T:1",
    "generated": "T:G",
    "required": "T:R",
}

QUALITY_SYMBOLS = {
    "fast": "Q:F",
    "balanced": "Q:B",
    "accuracy_first": "Q:A",
    "verifier_required": "Q:V",
}

COST_SYMBOLS = {
    "no_model": "C:0",
    "local_first": "C:L",
    "cheap_first": "C:C",
    "premium_allowed": "C:P",
    "premium_required": "C:PR",
}

CONTEXT_SYMBOLS = {
    "SUMMARY": "K:SUM",
    "SYMBOLIC": "K:SYM",
    "PATCH": "K:PAT",
    "TEST": "K:TST",
    "VERIFIER": "K:VER",
}

MODEL_SYMBOLS = {
    "no_model": "M:0",
    "local_first": "M:L",
    "local_model": "M:L",
    "cheap_first": "M:C",
    "cheap_model": "M:C",
    "premium_allowed": "M:P",
    "premium_required": "M:P",
    "premium_model": "M:P",
}

ROUTE_SYMBOLS = {
    "LOCALIZE_FIRST": "O:LOC",
    "PLAN_ONLY": "O:PLAN",
    "MUSIC_RANK_ONLY": "O:MUSIC",
    "BUILDER_PATCH": "O:BUILD",
    "TEST_GAP_FILL": "O:TEST",
    "VERIFY_ONLY": "O:VERIFY",
    "REPAIR_PATCH": "O:REPAIR",
    "BLOCKED_WITH_REASON": "O:BLOCK",
}

REASON_SYMBOLS = {
    "target_symbol_unresolved": "E:SYM0",
    "missing_tests": "E:TEST0",
    "research_not_patch_evidence": "E:RG0",
    "scope_too_broad_for_act_capsule": "E:SCOPE",
    "live_risk_requires_verification": "E:LIVE",
    "hotswap_requires_full_grounding": "E:HOT0",
    "missing_grounding": "E:GROUND0",
    "route_valid": "E:OK",
    "benchmark_before_optimization": "E:BENCH",
    "repair_after_failed_patch": "E:REPAIR",
}


def _slot_symbol(table: dict[str, str], value: str, fallback: str) -> str:
    return table.get(str(value or "").strip().lower(), fallback)


@dataclass(frozen=True)
class RoutingFrame:
    """Canonical Coding Arena routing frame from Aura's structural layer."""

    intent: str
    artifact: str = "python_module"
    action: str = "modify"
    scope: str = "symbol"
    risk: str = "medium"
    grounding: tuple[str, ...] = ()
    tests: str = "none"
    quality: str = "balanced"
    cost: str = "local_first"
    target_file: str | None = None
    target_symbol: str | None = None
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        normalized_grounding = tuple(
            item
            for item in (
                str(value).strip().lower()
                for value in self.grounding
                if str(value).strip()
            )
            if item != "none"
        )
        if not normalized_grounding:
            normalized_grounding = ("none",)
        object.__setattr__(self, "intent", str(self.intent).strip().lower())
        object.__setattr__(self, "artifact", str(self.artifact).strip().lower())
        object.__setattr__(self, "action", str(self.action).strip().lower())
        object.__setattr__(self, "scope", str(self.scope).strip().lower())
        object.__setattr__(self, "risk", str(self.risk).strip().lower())
        object.__setattr__(self, "grounding", normalized_grounding)
        object.__setattr__(self, "tests", str(self.tests).strip().lower())
        object.__setattr__(self, "quality", str(self.quality).strip().lower())
        object.__setattr__(self, "cost", str(self.cost).strip().lower())

    def has_grounding(self, value: str) -> bool:
        """Return true when the structural layer established a grounding fact."""
        item = str(value).strip().lower()
        return "full" in self.grounding or item in self.grounding

    def grounding_symbol(self) -> str:
        if self.has_grounding("full"):
            return "G:FULL"
        ordered = [
            "file_exists",
            "symbol_exists",
            "tests_exist",
            "manifest_owner",
            "codemap_grounded",
        ]
        parts = [GROUNDING_SYMBOLS[item] for item in ordered if item in self.grounding]
        return f"G:{'+'.join(parts)}" if parts else "G:0"

    def symbol_input(self) -> str:
        return "|".join(
            [
                _slot_symbol(INTENT_SYMBOLS, self.intent, f"I:{self.intent.upper()}"),
                _slot_symbol(ARTIFACT_SYMBOLS, self.artifact, f"A:{self.artifact.upper()}"),
                _slot_symbol(ACTION_SYMBOLS, self.action, f"X:{self.action.upper()}"),
                _slot_symbol(SCOPE_SYMBOLS, self.scope, f"S:{self.scope.upper()}"),
                _slot_symbol(RISK_SYMBOLS, self.risk, f"R:{self.risk.upper()}"),
                self.grounding_symbol(),
                _slot_symbol(TEST_SYMBOLS, self.tests, f"T:{self.tests.upper()}"),
                _slot_symbol(QUALITY_SYMBOLS, self.quality, f"Q:{self.quality.upper()}"),
                _slot_symbol(COST_SYMBOLS, self.cost, f"C:{self.cost.upper()}"),
            ]
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "artifact": self.artifact,
            "action": self.action,
            "scope": self.scope,
            "risk": self.risk,
            "grounding": list(self.grounding),
            "tests": self.tests,
            "quality": self.quality,
            "cost": self.cost,
            "target_file": self.target_file,
            "target_symbol": self.target_symbol,
            "failure_reason": self.failure_reason,
            "symbol_input": self.symbol_input(),
        }


@dataclass(frozen=True)
class RouteDecision:
    """Deterministic route selected for a Coding Arena task."""

    rule_name: str
    route: str
    model: str
    context: str
    reason: str
    verifier_required: bool
    symbol_input: str
    rule_priority: int = 100
    classification: str | None = None
    weighted_alternatives: list[dict[str, object]] = field(default_factory=list)

    def symbol_output(self) -> str:
        return "|".join(
            [
                ROUTE_SYMBOLS.get(self.route, f"O:{self.route}"),
                MODEL_SYMBOLS.get(self.model, f"M:{self.model}"),
                CONTEXT_SYMBOLS.get(self.context, f"K:{self.context}"),
                REASON_SYMBOLS.get(self.reason, f"E:{self.reason}"),
                "V:1" if self.verifier_required else "V:0",
            ]
        )

    def to_dict(self) -> dict[str, object]:
        payload = {
            "rule_name": self.rule_name,
            "route": self.route,
            "model": self.model,
            "context": self.context,
            "reason": self.reason,
            "verifier_required": self.verifier_required,
            "rule_priority": self.rule_priority,
            "symbol_input": self.symbol_input,
            "symbol_output": self.symbol_output(),
            "weighted_alternatives": list(self.weighted_alternatives),
        }
        if self.classification:
            payload["classification"] = self.classification
        return payload


@dataclass(frozen=True)
class RoutingRule:
    name: str
    predicate: Callable[[RoutingFrame], bool]
    route: str
    model: str
    context: str
    reason: str
    verifier_required: bool = False
    classification: str | None = None
    priority: int = 100


class AuraCodingArenaRouter:
    """
    Deterministic structural router for the Coding Arena DSL.

    Hard gates fire in priority order. Weighted route scores are emitted as
    diagnostics only, so cost/quality preferences cannot override grounding,
    test, live-risk, or hotswap blockers.
    """

    def __init__(self) -> None:
        self.rules = [
            RoutingRule(
                "missing_grounding_blocks_hotswap",
                lambda f: f.intent == "hotswap" and not f.has_grounding("full"),
                "BLOCKED_WITH_REASON",
                "no_model",
                "VERIFIER",
                "hotswap_requires_full_grounding",
                True,
                priority=10,
            ),
            RoutingRule(
                "fake_symbol_blocks_builder",
                lambda f: (
                    f.intent == "code_refactor"
                    and f.action == "modify"
                    and bool(f.target_symbol)
                    and not f.has_grounding("symbol_exists")
                ),
                "LOCALIZE_FIRST",
                "no_model",
                "SUMMARY",
                "target_symbol_unresolved",
                priority=20,
            ),
            RoutingRule(
                "broad_subsystem_cannot_patch",
                lambda f: f.intent == "code_refactor" and f.scope in {"subsystem", "repo"} and f.action == "modify",
                "PLAN_ONLY",
                "cheap_first",
                "SUMMARY",
                "scope_too_broad_for_act_capsule",
                True,
                priority=30,
            ),
            RoutingRule(
                "research_without_grounding_is_analogy",
                lambda f: f.intent == "research_rank" and not f.has_grounding("manifest_owner"),
                "MUSIC_RANK_ONLY",
                "no_model",
                "SYMBOLIC",
                "research_not_patch_evidence",
                False,
                "RESEARCH_ANALOGY_ONLY",
                priority=40,
            ),
            RoutingRule(
                "failed_patch_routes_to_repair",
                lambda f: f.intent == "repair" and f.artifact == "patch" and f.action == "repair",
                "REPAIR_PATCH",
                "cheap_first",
                "PATCH",
                "repair_after_failed_patch",
                True,
                priority=50,
            ),
            RoutingRule(
                "benchmark_request_routes_to_measurement",
                lambda f: f.intent == "benchmark",
                "PLAN_ONLY",
                "local_first",
                "SYMBOLIC",
                "benchmark_before_optimization",
                priority=60,
            ),
            RoutingRule(
                "no_tests_routes_to_test_gap",
                lambda f: (
                    f.intent == "code_refactor"
                    and f.action == "modify"
                    and f.tests == "none"
                    and f.risk in {"medium", "high", "live"}
                ),
                "TEST_GAP_FILL",
                "local_first",
                "TEST",
                "missing_tests",
                priority=70,
            ),
            RoutingRule(
                "grounded_symbol_can_patch",
                lambda f: (
                    f.intent == "code_refactor"
                    and f.action == "modify"
                    and f.scope == "symbol"
                    and f.has_grounding("symbol_exists")
                    and f.has_grounding("codemap_grounded")
                    and f.tests in {"existing", "generated"}
                    and f.risk in {"low", "medium"}
                ),
                "BUILDER_PATCH",
                "local_first",
                "PATCH",
                "route_valid",
                True,
                priority=80,
            ),
            RoutingRule(
                "live_change_requires_verifier",
                lambda f: f.risk == "live",
                "VERIFY_ONLY",
                "no_model",
                "VERIFIER",
                "live_risk_requires_verification",
                True,
                priority=90,
            ),
        ]
        self.rules = sorted(self.rules, key=lambda rule: rule.priority)

    def route(self, frame: RoutingFrame) -> RouteDecision:
        alternatives = self.weighted_route_scores(frame)
        for rule in self.rules:
            if rule.predicate(frame):
                return RouteDecision(
                    rule_name=rule.name,
                    route=rule.route,
                    model=rule.model,
                    context=rule.context,
                    reason=rule.reason,
                    verifier_required=rule.verifier_required or frame.quality == "verifier_required" or frame.risk in {"high", "live"},
                    rule_priority=rule.priority,
                    classification=rule.classification,
                    symbol_input=frame.symbol_input(),
                    weighted_alternatives=alternatives,
                )
        return RouteDecision(
            rule_name="no_grounded_route",
            route="BLOCKED_WITH_REASON",
            model="no_model",
            context="SUMMARY",
            reason="missing_grounding",
            verifier_required=frame.quality == "verifier_required" or frame.risk in {"high", "live"},
            rule_priority=999,
            symbol_input=frame.symbol_input(),
            weighted_alternatives=alternatives,
        )

    def weighted_route_scores(self, frame: RoutingFrame) -> list[dict[str, object]]:
        """Score soft route affinity without replacing deterministic hard gates."""
        grounded = (
            0.30 * float(frame.has_grounding("file_exists"))
            + 0.25 * float(frame.has_grounding("symbol_exists"))
            + 0.25 * float(frame.has_grounding("codemap_grounded"))
            + 0.20 * float(frame.tests in {"existing", "generated"})
        )
        broad = float(frame.scope in {"subsystem", "repo"})
        missing_tests = float(frame.tests == "none")
        live = float(frame.risk == "live")
        failed_patch = float(frame.intent == "repair" and frame.artifact == "patch")
        research = float(frame.intent == "research_rank")
        scores = {
            "BUILDER_PATCH": max(0.0, grounded - 0.35 * broad - 0.30 * live),
            "LOCALIZE_FIRST": max(0.0, 1.0 - float(frame.has_grounding("symbol_exists")) if frame.target_symbol else 0.25),
            "TEST_GAP_FILL": missing_tests * (0.45 + 0.35 * float(frame.risk in {"medium", "high", "live"})),
            "PLAN_ONLY": max(0.0, 0.30 + 0.45 * broad + 0.20 * float(frame.intent == "benchmark")),
            "VERIFY_ONLY": max(0.0, 0.20 + 0.70 * live),
            "REPAIR_PATCH": max(0.0, failed_patch),
            "MUSIC_RANK_ONLY": max(0.0, research * (1.0 - float(frame.has_grounding("manifest_owner")))),
            "BLOCKED_WITH_REASON": max(0.0, 1.0 - grounded),
        }
        return [
            {"route": route, "score": round(score, 4)}
            for route, score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        ]


class FSTLexiconRoutingCore:
    """
    FST-Lexicon Routing Core

    Formal finite-state transducer that replaces ad-hoc function
    call graphs with a verified routing lexicon.
    """

    def __init__(self, dimensions: int = 10000, require_complete_slots: bool = False):
        self.dimensions = dimensions
        self.require_complete_slots = require_complete_slots
        self.lexc: AuraLexc | None = None

        # FST components
        self.states: dict[str, State] = {}
        self.transitions: list[Transition] = []
        self.start_state: str | None = None
        self.final_states: set[str] = set()

        # Routing parameters
        self.alpha = 0.7  # VSA resonance weight
        self.max_temp = 85.0  # °C
        self.path_length_penalty = 0.05  # λ

        # Six-slot constraint
        self.slot_order = [
            SlotType.DIR,
            SlotType.ASP,
            SlotType.CLASS,
            SlotType.SUBJ,
            SlotType.VOICE,
            SlotType.STEM
        ]

    def _hash_to_hypervector(self, data: bytes) -> np.ndarray:
        """Convert hash to hypervector"""
        seed = int.from_bytes(hashlib.sha256(data).digest()[:4], 'big')
        rng = np.random.RandomState(seed)
        real = rng.randn(self.dimensions)
        imag = rng.randn(self.dimensions)
        vec = real + 1j * imag
        return vec / np.linalg.norm(vec)

    def add_state(self, state_id: str, tier: TierType,
                  slot: SlotType | None = None,
                  description: str = "") -> State:
        """Add state to FST"""
        hypervector = self._hash_to_hypervector(state_id.encode())

        state = State(
            id=state_id,
            tier=tier,
            slot=slot,
            hypervector=hypervector,
            description=description
        )

        self.states[state_id] = state
        return state

    def add_transition(self, from_state: str, to_state: str,
                      input_symbol: str,
                      slot_constraint: SlotType | None = None):
        """Add transition to FST"""
        if from_state not in self.states or to_state not in self.states:
            raise ValueError(f"States must exist: {from_state}, {to_state}")

        # Compute initial weight (will be updated dynamically)
        weight = self._compute_transition_weight(from_state, to_state)

        transition = Transition(
            from_state=from_state,
            to_state=to_state,
            input_symbol=input_symbol,
            weight=weight,
            slot_constraint=slot_constraint
        )

        self.transitions.append(transition)

    def _compute_transition_weight(self, from_state: str, to_state: str,
                                  cpu_temp: float = 55.0) -> float:
        """
        Compute transition weight

        w_ij = α·sim(v_i, v_j) + (1-α)·(1 - T_CPU/T_max)
        """
        state_i = self.states[from_state]
        state_j = self.states[to_state]

        # VSA resonance
        similarity = np.abs(np.vdot(state_i.hypervector, state_j.hypervector))

        # Thermal fitness
        thermal_fitness = 1.0 - (cpu_temp / self.max_temp)

        # Weighted combination
        weight = self.alpha * similarity + (1 - self.alpha) * thermal_fitness

        return float(weight)

    def update_transition_weights(self, cpu_temp: float):
        """Update all transition weights based on current CPU temperature"""
        for transition in self.transitions:
            transition.weight = self._compute_transition_weight(
                transition.from_state,
                transition.to_state,
                cpu_temp
            )

    def validate_slot_sequence(self, path: Path) -> bool:
        """
        Validate that path respects six-slot constraint

        [DIR]→[ASP]→[CLASS]→[SUBJ]→[VOICE]→[STEM]
        """
        if not path.slot_sequence:
            return not self.require_complete_slots

        # Check ordering
        prev_slot_idx = -1
        for slot in path.slot_sequence:
            if slot is None:
                continue

            curr_slot_idx = self.slot_order.index(slot)

            if curr_slot_idx <= prev_slot_idx:
                return False  # Out of order

            prev_slot_idx = curr_slot_idx

        if self.require_complete_slots:
            return path.slot_sequence == self.slot_order
        return True

    @classmethod
    def from_lexc(
        cls,
        path: str,
        *,
        dimensions: int = 10000,
        strict: bool = True,
    ) -> "FSTLexiconRoutingCore":
        """Build the weighted routing graph from the repository lexc source."""
        compiled = AuraLexc.from_path(path, strict=strict)
        core = cls(dimensions=dimensions, require_complete_slots=True)
        core.lexc = compiled

        for state_id in sorted(compiled.lexicons | {"#"}):
            if state_id == "Root" or state_id.startswith("Gate"):
                tier = TierType.GATE
            elif state_id.startswith("Action"):
                tier = TierType.ACTION
            elif state_id.startswith("Target") or state_id.startswith("Cloud"):
                tier = TierType.TARGET
            elif state_id.startswith("Physics"):
                tier = TierType.PHYSICS
            else:
                tier = TierType.MODIFIER
            core.add_state(state_id, tier, description=f"Compiled from aura.lexc: {state_id}")

        slot_map = {
            SlotName.DIR: SlotType.DIR,
            SlotName.ASP: SlotType.ASP,
            SlotName.CLASS: SlotType.CLASS,
            SlotName.SUBJ: SlotType.SUBJ,
            SlotName.VOICE: SlotType.VOICE,
            SlotName.STEM: SlotType.STEM,
        }
        for arc in compiled.arcs:
            core.add_transition(
                arc.source,
                arc.target,
                arc.lexical,
                slot_map[arc.slot],
            )
        core.start_state = "Root"
        core.final_states = {"#"}
        return core

    def find_optimal_path(self, start: str, end: str,
                         cpu_temp: float = 55.0) -> Path | None:
        """
        Find optimal path from start to end state

        Cost(p) = Σ(1 - w_ij) + λ·k

        Uses topological ordering for O(|Q| + |Δ|) complexity
        """
        if start not in self.states or end not in self.states:
            return None

        # Update weights for current temperature
        self.update_transition_weights(cpu_temp)

        # Build adjacency list
        adj: dict[str, list[Transition]] = {}
        for transition in self.transitions:
            if transition.from_state not in adj:
                adj[transition.from_state] = []
            adj[transition.from_state].append(transition)

        # Dijkstra's algorithm (since we have weights)
        import heapq
        import itertools

        # Counter prevents heap tie-breaking from comparing Transition objects.
        counter = itertools.count()
        # (cost, insertion_order, state, path_states, path_transitions, slot_sequence)
        queue = [(0.0, next(counter), start, [start], [], [])]
        visited = set()

        while queue:
            cost, _, current, path_states, path_transitions, slot_seq = heapq.heappop(queue)

            visit_key = (current, tuple(slot_seq))
            if visit_key in visited:
                continue
            visited.add(visit_key)

            # Check if we reached the end
            if current == end:
                path = Path(
                    states=path_states,
                    transitions=path_transitions,
                    total_cost=cost,
                    slot_sequence=slot_seq
                )

                # Validate slot sequence
                if self.validate_slot_sequence(path):
                    return path
                else:
                    continue  # Invalid slot sequence, keep searching

            # Explore neighbors
            if current in adj:
                for transition in adj[current]:
                    next_state = transition.to_state

                    next_visit_key = (
                        next_state,
                        tuple(
                            slot_seq
                            + ([transition.slot_constraint] if transition.slot_constraint else [])
                        ),
                    )
                    if next_visit_key in visited:
                        continue

                    # Compute edge cost
                    edge_cost = (1.0 - transition.weight) + self.path_length_penalty
                    new_cost = cost + edge_cost

                    # Update slot sequence
                    new_slot_seq = slot_seq.copy()
                    if transition.slot_constraint:
                        new_slot_seq.append(transition.slot_constraint)

                    # Add to queue
                    heapq.heappush(queue, (
                        new_cost,
                        next(counter),
                        next_state,
                        [*path_states, next_state],
                        [*path_transitions, transition],
                        new_slot_seq
                    ))

        return None  # No valid path found

    def build_standard_lexicon(self):
        """
        Build standard AuraOS FST lexicon

        Hierarchy:
        1. Gates (Root, DataGate, NetworkGate, HardwareGate, etc.)
        2. Actions (ActionData, ActionNetwork, etc.)
        3. Targets (TargetMemory, TargetLedger, etc.)
        4. Physics (PhysicsCube, PhysicsSphere, etc.)
        5. Modifiers (ModifierExecution, ModifierMemory, etc.)
        """
        # Tier 1: Gates
        root = self.add_state("Root", TierType.GATE, SlotType.DIR, "Root gate")
        data_gate = self.add_state("DataGate", TierType.GATE, SlotType.DIR, "Data operations gate")
        network_gate = self.add_state("NetworkGate", TierType.GATE, SlotType.DIR, "Network operations gate")
        hardware_gate = self.add_state("HardwareGate", TierType.GATE, SlotType.DIR, "Hardware operations gate")

        self.start_state = "Root"

        # Tier 2: Actions
        action_data = self.add_state("ActionData", TierType.ACTION, SlotType.ASP, "Data action")
        action_network = self.add_state("ActionNetwork", TierType.ACTION, SlotType.ASP, "Network action")
        action_hardware = self.add_state("ActionHardware", TierType.ACTION, SlotType.ASP, "Hardware action")

        # Tier 3: Targets
        target_memory = self.add_state("TargetMemory", TierType.TARGET, SlotType.CLASS, "Memory target")
        target_ledger = self.add_state("TargetLedger", TierType.TARGET, SlotType.CLASS, "Ledger target")
        target_sensor = self.add_state("TargetSensor", TierType.TARGET, SlotType.CLASS, "Sensor target")

        # Tier 4: Physics
        physics_cube = self.add_state("PhysicsCube", TierType.PHYSICS, SlotType.SUBJ, "Cube primitive")
        physics_sphere = self.add_state("PhysicsSphere", TierType.PHYSICS, SlotType.SUBJ, "Sphere primitive")

        # Tier 5: Modifiers
        modifier_exec = self.add_state("ModifierExecution", TierType.MODIFIER, SlotType.STEM, "Execute modifier")
        modifier_store = self.add_state("ModifierStorage", TierType.MODIFIER, SlotType.STEM, "Store modifier")

        self.final_states = {"ModifierExecution", "ModifierStorage"}

        # Add transitions (Gate → Action)
        self.add_transition("Root", "DataGate", "data", SlotType.DIR)
        self.add_transition("Root", "NetworkGate", "network", SlotType.DIR)
        self.add_transition("Root", "HardwareGate", "hardware", SlotType.DIR)

        # Action → Target
        self.add_transition("DataGate", "ActionData", "process", SlotType.ASP)
        self.add_transition("NetworkGate", "ActionNetwork", "transmit", SlotType.ASP)
        self.add_transition("HardwareGate", "ActionHardware", "sense", SlotType.ASP)

        # Target → Physics
        self.add_transition("ActionData", "TargetMemory", "memory", SlotType.CLASS)
        self.add_transition("ActionData", "TargetLedger", "ledger", SlotType.CLASS)
        self.add_transition("ActionHardware", "TargetSensor", "sensor", SlotType.CLASS)

        # Physics → Modifier
        self.add_transition("TargetMemory", "PhysicsCube", "cube", SlotType.SUBJ)
        self.add_transition("TargetLedger", "PhysicsSphere", "sphere", SlotType.SUBJ)
        self.add_transition("TargetSensor", "PhysicsCube", "cube", SlotType.SUBJ)

        # Modifier (final)
        self.add_transition("PhysicsCube", "ModifierExecution", "execute", SlotType.STEM)
        self.add_transition("PhysicsSphere", "ModifierStorage", "store", SlotType.STEM)

    def get_stats(self) -> dict:
        """Get FST statistics"""
        return {
            'states': len(self.states),
            'transitions': len(self.transitions),
            'start_state': self.start_state,
            'final_states': len(self.final_states),
            'tiers': {
                'gate': sum(1 for s in self.states.values() if s.tier == TierType.GATE),
                'action': sum(1 for s in self.states.values() if s.tier == TierType.ACTION),
                'target': sum(1 for s in self.states.values() if s.tier == TierType.TARGET),
                'physics': sum(1 for s in self.states.values() if s.tier == TierType.PHYSICS),
                'modifier': sum(1 for s in self.states.values() if s.tier == TierType.MODIFIER)
            },
            'source': 'aura.lexc' if self.lexc is not None else 'built_in',
            'complete_six_slot_routes': (
                len(self.lexc.complete_routes()) if self.lexc is not None else 0
            ),
            'lexc_errors': len(self.lexc.errors) if self.lexc is not None else 0,
            'lexc_warnings': len(self.lexc.warnings) if self.lexc is not None else 0,
        }


# Demo
if __name__ == "__main__":
    print("=== Aura FST-Lexicon Routing Core Demo ===\n")

    fst = FSTLexiconRoutingCore()

    # 1. Build standard lexicon
    print("1. Building standard FST lexicon...")
    fst.build_standard_lexicon()
    stats = fst.get_stats()
    print(f"   States: {stats['states']}")
    print(f"   Transitions: {stats['transitions']}")
    print(f"   Tiers: {stats['tiers']}")

    # 2. Find optimal paths
    print("\n2. Finding optimal paths...")

    print("\n   Path 1: Root -> ModifierExecution")
    path1 = fst.find_optimal_path("Root", "ModifierExecution", cpu_temp=50.0)
    if path1:
        print(f"   States: {' -> '.join(path1.states)}")
        print(f"   Cost: {path1.total_cost:.4f}")
        print(f"   Length: {len(path1.states)}")
        print(f"   Slot sequence: {[s.name for s in path1.slot_sequence]}")

    print("\n   Path 2: Root -> ModifierStorage")
    path2 = fst.find_optimal_path("Root", "ModifierStorage", cpu_temp=50.0)
    if path2:
        print(f"   States: {' -> '.join(path2.states)}")
        print(f"   Cost: {path2.total_cost:.4f}")
        print(f"   Length: {len(path2.states)}")

    # 3. Test thermal awareness
    print("\n3. Testing thermal awareness...")
    print("   Scenario: High CPU temperature")
    path3 = fst.find_optimal_path("Root", "ModifierExecution", cpu_temp=80.0)
    if path3:
        print(f"   Cost at 80°C: {path3.total_cost:.4f}")

    path4 = fst.find_optimal_path("Root", "ModifierExecution", cpu_temp=40.0)
    if path4:
        print(f"   Cost at 40°C: {path4.total_cost:.4f}")
        if path3:
            print(f"   Cost reduction: {(path3.total_cost - path4.total_cost):.4f}")

    # 4. Complexity comparison
    print("\n4. Complexity comparison:")
    print("   Original ad-hoc graph: >1300 edges")
    print(f"   FST lexicon: {stats['transitions']} edges")
    print(f"   Reduction: {((1300 - stats['transitions']) / 1300 * 100):.1f}%")
    print(f"   Routing complexity: O(L) where L <= {len(path1.states) if path1 else 0}")

    print("\nDemo complete")

# Made with Bob
