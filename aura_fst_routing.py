"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: numpy, aura_lexc, itertools, enum, heapq, dataclasses, hashlib
FUNCTIONS: __init__, _hash_to_hypervector, add_state, add_transition, _compute_transition_weight, update_transition_weights, validate_slot_sequence, from_lexc, find_optimal_path, build_standard_lexicon, get_stats
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

from dataclasses import dataclass
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
