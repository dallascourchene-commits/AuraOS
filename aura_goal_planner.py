"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f2-[Q-SYS:AURA_GOAL_PLANNER]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Grounded Goal Decomposition)
DEPENDENCIES: dataclasses, heapq, hashlib, json, time, typing
FUNCTIONS: GoalState, GoalAction, GoalPlan, AuraGOAPPlanner, build_default_actions
SYNOPSIS: GOAP goal planner that converts high-level goals into precondition/effect
          action paths BEFORE ActionCapsules are generated. Output is a proposal of
          act_task dicts consumed by the Architect Loop's build_fractal_plan_capsule.
          The planner CANNOT bypass Architect, Shadow, Judge, or Verifier — every
          GoalAction declares must_pass_gates and the planner emits proposals, not
          capsules. Repeated successful patterns crystallize in QDKT.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import heapq
import json
import time
from typing import Any

AURA_GOAL_PLANNER_VERSION = "AURA_GOAL_PLANNER_V1"

# Gates every planned action must pass. The planner never removes these.
REQUIRED_GATES = ("architect", "shadow", "verifier", "judge")


def _hash_payload(payload: Any, *, size: int = 16) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=size).hexdigest()


def _facts_satisfied(preconditions: dict[str, Any], state: dict[str, Any]) -> bool:
    """Check whether every precondition fact is satisfied by the current state."""
    for key, expected in preconditions.items():
        actual = state.get(key)
        if isinstance(expected, (set, tuple, list)):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def _apply_effects(effects: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Return a new state with effects applied (immutable)."""
    new_state = dict(state)
    new_state.update(effects)
    return new_state


@dataclass(frozen=True)
class GoalState:
    """A snapshot of facts the planner reasons over."""

    facts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.facts)

    def satisfies(self, preconditions: dict[str, Any]) -> bool:
        return _facts_satisfied(preconditions, self.facts)

    def apply(self, effects: dict[str, Any]) -> "GoalState":
        return GoalState(facts=_apply_effects(effects, self.facts))


@dataclass(frozen=True)
class GoalAction:
    """One GOAP action. Declares preconditions, effects, cost, and required gates."""

    name: str
    domain: str
    preconditions: dict[str, Any] = field(default_factory=dict)
    effects: dict[str, Any] = field(default_factory=dict)
    cost: float = 1.0
    required_organ: str = ""
    must_pass_gates: tuple[str, ...] = REQUIRED_GATES
    target_file: str | None = None
    target_symbol: str | None = None
    objective: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "domain": self.domain,
            "preconditions": dict(self.preconditions),
            "effects": dict(self.effects),
            "cost": float(self.cost),
            "required_organ": self.required_organ,
            "must_pass_gates": list(self.must_pass_gates),
            "target_file": self.target_file,
            "target_symbol": self.target_symbol,
            "objective": self.objective,
            "metadata": dict(self.metadata),
        }

    def to_act_task(self) -> dict[str, Any]:
        """Convert to an act_task dict consumable by build_fractal_plan_capsule."""
        return {
            "task_id": self.name,
            "objective": self.objective or self.name,
            "target_file": self.target_file,
            "target_symbol": self.target_symbol,
            "role": "cheap_builder",
            "allowed_scope": "single bounded edit",
            "expected_output": "UNIFIED_DIFF",
            "constraints": [
                f"must_pass_gate:{gate}" for gate in self.must_pass_gates
            ],
            "escalate_if": [
                "missing target file",
                "missing target symbol",
                "requires public API change",
                "requires new dependency",
            ],
            "domain": self.domain,
            "required_organ": self.required_organ,
            "planner_cost": float(self.cost),
            "planner_preconditions": dict(self.preconditions),
            "planner_effects": dict(self.effects),
        }


@dataclass
class GoalPlan:
    """An ordered plan of actions plus the resulting state and phase hash."""

    plan_id: str
    goal: str
    actions: list[GoalAction]
    initial_state: dict[str, Any]
    final_state: dict[str, Any]
    total_cost: float
    phase_hash: str
    must_pass_gates: tuple[str, ...] = REQUIRED_GATES
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": AURA_GOAL_PLANNER_VERSION,
            "plan_id": self.plan_id,
            "goal": self.goal,
            "actions": [a.to_dict() for a in self.actions],
            "initial_state": dict(self.initial_state),
            "final_state": dict(self.final_state),
            "total_cost": float(self.total_cost),
            "phase_hash": self.phase_hash,
            "must_pass_gates": list(self.must_pass_gates),
            "ts": self.ts,
        }

    def to_act_tasks(self) -> list[dict[str, Any]]:
        """Return act_task dicts for the Architect Loop."""
        return [action.to_act_task() for action in self.actions]


class AuraGOAPPlanner:
    """A* GOAP planner over precondition/effect actions.

    The planner produces a GoalPlan whose actions are *proposals*. The
    Architect Loop still owns capsule creation, grounding, shadow, and
    verification. No plan may declare must_pass_gates that omits any of
    the required gates.
    """

    def __init__(self, *, qdkt: Any = None) -> None:
        self.qdkt = qdkt
        self._actions: dict[str, GoalAction] = {}
        self._plan_history: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Action registration
    # ------------------------------------------------------------------

    def register_action(self, action: GoalAction) -> None:
        missing_gates = set(REQUIRED_GATES) - set(action.must_pass_gates)
        if missing_gates:
            raise ValueError(
                f"action '{action.name}' omits required gates: {sorted(missing_gates)}"
            )
        if action.name in self._actions:
            raise ValueError(f"action '{action.name}' is already registered")
        self._actions[action.name] = action

    def list_actions(self) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self._actions.values()]

    # ------------------------------------------------------------------
    # Planning (A* over state graph)
    # ------------------------------------------------------------------

    def plan(
        self,
        goal: str,
        initial_state: dict[str, Any],
        goal_conditions: dict[str, Any],
        *,
        max_steps: int = 32,
    ) -> GoalPlan:
        """Find a minimum-cost action sequence from initial_state to goal_conditions."""
        start = GoalState(facts=dict(initial_state))
        # Priority queue: (cumulative_cost, counter, state_facts_tuple, actions_list)
        counter = 0
        frontier: list[tuple[float, int, tuple, list[GoalAction]]] = [
            (0.0, counter, _state_key(start.facts), [])
        ]
        visited: set[tuple] = set()
        best: list[GoalAction] | None = None
        best_cost = float("inf")
        best_state: dict[str, Any] = dict(initial_state)

        while frontier:
            cost, _, state_key, actions = heapq.heappop(frontier)
            if state_key in visited:
                continue
            visited.add(state_key)
            current_state = GoalState(facts=_state_from_key(state_key, start.facts))

            if _facts_satisfied(goal_conditions, current_state.facts):
                if cost < best_cost:
                    best_cost = cost
                    best = actions
                    best_state = dict(current_state.facts)
                continue

            if len(actions) >= max_steps:
                continue

            for action in self._actions.values():
                if current_state.satisfies(action.preconditions):
                    next_state = current_state.apply(action.effects)
                    next_key = _state_key(next_state.facts)
                    if next_key in visited:
                        continue
                    counter += 1
                    heapq.heappush(
                        frontier,
                        (cost + action.cost, counter, next_key, actions + [action]),
                    )

        if best is None:
            raise ValueError(f"GOAP planner found no path to goal: {goal}")

        payload = {
            "goal": goal,
            "actions": [a.to_dict() for a in best],
            "initial_state": dict(initial_state),
            "final_state": dict(best_state),
            "total_cost": best_cost,
        }
        plan_id = f"GOAL-{_hash_payload(payload)[:12]}"
        phase_hash = _hash_payload({**payload, "plan_id": plan_id})
        plan = GoalPlan(
            plan_id=plan_id,
            goal=goal,
            actions=best,
            initial_state=dict(initial_state),
            final_state=dict(best_state),
            total_cost=best_cost,
            phase_hash=phase_hash,
        )
        self._record_plan(plan)
        return plan

    # ------------------------------------------------------------------
    # QDKT
    # ------------------------------------------------------------------

    def _record_plan(self, plan: GoalPlan) -> None:
        row = plan.to_dict()
        self._plan_history.append(row)
        if self.qdkt is None:
            return
        try:
            self.qdkt.observe(
                "goal_plan",
                {
                    "plan_id": plan.plan_id,
                    "goal": plan.goal,
                    "action_count": len(plan.actions),
                    "total_cost": plan.total_cost,
                },
                rationale=f"GOAP plan for: {plan.goal}",
                concept=f"goal_plan:{plan.plan_id}",
                confidence=0.7,
            )
        except Exception:
            pass

    def record_plan_outcome(self, plan_id: str, *, success: bool) -> None:
        """Record whether a plan succeeded. Repeated successes crystallize."""
        if self.qdkt is None:
            return
        try:
            self.qdkt.observe(
                "goal_plan_outcome",
                {"plan_id": plan_id, "success": bool(success)},
                rationale=f"plan {plan_id} {'succeeded' if success else 'failed'}",
                concept=f"goal_plan_outcome:{plan_id}",
                confidence=0.9 if success else 0.3,
            )
            if success:
                # Crystallize repeated successful patterns.
                self.qdkt.crystallize(
                    f"goal_plan:{plan_id}",
                    f"repeat plan {plan_id}",
                    confidence=0.8,
                    source="goap_repeated_success",
                )
        except Exception:
            pass

    def plan_history(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return list(self._plan_history[-limit:])


# ---------------------------------------------------------------------------
# State key helpers (for visited-set hashing)
# ---------------------------------------------------------------------------

def _state_key(facts: dict[str, Any]) -> tuple:
    return tuple(sorted((k, json.dumps(v, sort_keys=True, default=str)) for k, v in facts.items()))


def _state_from_key(key: tuple, reference: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct a facts dict from a state key, using reference for value types."""
    out: dict[str, Any] = {}
    for k, v_json in key:
        try:
            out[k] = json.loads(v_json)
        except json.JSONDecodeError:
            out[k] = v_json
    return out


# ---------------------------------------------------------------------------
# Default action library
# ---------------------------------------------------------------------------

def build_default_actions() -> list[GoalAction]:
    """A small default GOAP action library spanning Aura domains."""
    return [
        GoalAction(
            name="ground_codemap",
            domain="code",
            preconditions={"codemap_available": True},
            effects={"codemap_grounded": True},
            cost=0.5,
            required_organ="code",
            objective="Refresh and ground CODEMAP for target files.",
        ),
        GoalAction(
            name="build_patch",
            domain="code",
            preconditions={"codemap_grounded": True, "target_file_set": True},
            effects={"patch_proposed": True},
            cost=1.0,
            required_organ="code",
            objective="Emit a bounded unified diff for the target file.",
        ),
        GoalAction(
            name="verify_tests",
            domain="code",
            preconditions={"patch_proposed": True},
            effects={"tests_passed": True},
            cost=0.8,
            required_organ="code",
            objective="Run nearby tests against the staged patch.",
        ),
        GoalAction(
            name="resolve_vsa_pointer",
            domain="travel",
            preconditions={"vsa_id_set": True, "sidecar_available": True},
            effects={"price_resolved": True},
            cost=0.6,
            required_organ="travel",
            objective="Resolve a VSA pointer into an exact sidecar price record.",
        ),
        GoalAction(
            name="verify_price_freshness",
            domain="travel",
            preconditions={"price_resolved": True},
            effects={"price_verified": True},
            cost=0.4,
            required_organ="travel",
            objective="Verify price freshness, provenance, and confidence.",
        ),
        GoalAction(
            name="build_travel_package",
            domain="travel",
            preconditions={"price_verified": True},
            effects={"package_proposed": True},
            cost=0.7,
            required_organ="travel",
            objective="Build a verified travel package candidate pending human approval.",
        ),
        GoalAction(
            name="scan_social_signals",
            domain="social",
            preconditions={"social_query_set": True},
            effects={"social_references_ranked": True},
            cost=0.5,
            required_organ="social",
            objective="Scan and rank social luminance references (redacted).",
        ),
        GoalAction(
            name="verify_ledger_entry",
            domain="fintech",
            preconditions={"ledger_entry_set": True},
            effects={"ledger_verified": True},
            cost=0.5,
            required_organ="fintech",
            objective="Verify fintech ledger entry provenance and balance integrity.",
        ),
        GoalAction(
            name="propose_civic_intervention",
            domain="civic",
            preconditions={"civic_data_available": True},
            effects={"civic_intervention_proposed": True},
            cost=0.6,
            required_organ="civic",
            objective="Propose a civic intervention respecting legal and funding constraints.",
        ),
        GoalAction(
            name="export_icm_audit",
            domain="icm",
            preconditions={"arena_transaction_ready": True},
            effects={"icm_workspace_exported": True},
            cost=0.3,
            required_organ="icm",
            objective="Export an Arena transaction to an ICM audit workspace.",
        ),
        GoalAction(
            name="federate_capsule",
            domain="federation",
            preconditions={"capsule_redacted": True, "capsule_signed": True},
            effects={"capsule_federated": True},
            cost=0.4,
            required_organ="federation",
            objective="Export a redacted signed capsule to a federation peer.",
        ),
    ]


def build_default_planner(*, qdkt: Any = None) -> AuraGOAPPlanner:
    planner = AuraGOAPPlanner(qdkt=qdkt)
    for action in build_default_actions():
        planner.register_action(action)
    return planner


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Aura GOAP Planner — list actions")
    parser.add_argument("--list", action="store_true", help="list registered actions")
    args = parser.parse_args(argv)
    planner = build_default_planner()
    if args.list:
        print(json.dumps(planner.list_actions(), indent=2, sort_keys=True))
    else:
        print(f"Aura GOAP Planner: {len(planner.list_actions())} actions registered")
        for action in planner.list_actions():
            print(f"  - {action['name']} (domain={action['domain']}, cost={action['cost']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())