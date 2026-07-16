"""Generate a reproducible executable refactor benchmark fixture and patch arms.

The fixture models Aura's Council/Surgeon failure-routing problem. All arms start
from the same files and face visible, hidden, regression, API, scope, security,
and maintainability evaluation. Patch responses are single-session assisted
fixtures and are not claimed to be independent provider trials.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

FIXTURE_VERSION = "AURA_EXECUTABLE_REFACTOR_FIXTURE_V1"
OBJECTIVE = (
    "Refactor the failure router and compact State Ledger so false graph-breach fields "
    "stay with local repair, true graph/interface/invariant breaches escalate to a Council "
    "replan, exhausted local repair budget escalates, and compact state preserves identity "
    "without replaying raw history. Preserve public APIs and edit only router.py and state.py."
)

BASE_FILES = {
    "arena_refactor/__init__.py": (
        "from .router import classify_failure\n"
        "from .service import decide_next_action\n"
        "from .state import RefactorState\n\n"
        "__all__ = ['RefactorState', 'classify_failure', 'decide_next_action']\n"
    ),
    "arena_refactor/router.py": (
        "from __future__ import annotations\n\n"
        "import json\n"
        "from typing import Any\n\n"
        "GRAPH_FAILURE_FIELDS = (\n"
        "    'dependency_graph_breach',\n"
        "    'interface_contract_breach',\n"
        "    'invariant_breach',\n"
        ")\n\n"
        "def classify_failure(packet: dict[str, Any]) -> str:\n"
        "    serialized = json.dumps(packet, sort_keys=True).lower()\n"
        "    if any(field in serialized for field in GRAPH_FAILURE_FIELDS):\n"
        "        return 'ESCALATE_TO_COUNCIL_REPLAN'\n"
        "    if int(packet.get('repair_attempt', 0) or 0) >= 2:\n"
        "        return 'ESCALATE_TO_COUNCIL_REPLAN'\n"
        "    return 'SURGEON_LOCAL_REPAIR'\n"
    ),
    "arena_refactor/state.py": (
        "from __future__ import annotations\n\n"
        "from dataclasses import dataclass, field\n"
        "from typing import Any\n\n"
        "@dataclass\n"
        "class RefactorState:\n"
        "    plan_id: str\n"
        "    completed_tasks: list[str] = field(default_factory=list)\n"
        "    current_task: str | None = None\n"
        "    history: list[dict[str, Any]] = field(default_factory=list)\n\n"
        "    def compact_ledger(self) -> dict[str, Any]:\n"
        "        return {\n"
        "            'plan_id': self.plan_id,\n"
        "            'completed_tasks': list(self.completed_tasks),\n"
        "            'current_task': self.current_task,\n"
        "            'history': list(self.history),\n"
        "        }\n"
    ),
    "arena_refactor/service.py": (
        "from __future__ import annotations\n\n"
        "from typing import Any\n\n"
        "from .router import classify_failure\n"
        "from .state import RefactorState\n\n"
        "def decide_next_action(state: RefactorState, failure: dict[str, Any]) -> dict[str, Any]:\n"
        "    return {\n"
        "        'route': classify_failure(failure),\n"
        "        'state_ledger': state.compact_ledger(),\n"
        "    }\n"
    ),
    "arena_refactor/notes.py": "NOTE = 'fixture documentation marker'\n",
    "tests/test_visible.py": (
        "from arena_refactor.router import classify_failure\n\n"
        "def test_false_boolean_graph_fields_stay_local():\n"
        "    packet = {\n"
        "        'message': 'one assertion failed',\n"
        "        'dependency_graph_breach': False,\n"
        "        'interface_contract_breach': False,\n"
        "        'invariant_breach': False,\n"
        "        'repair_attempt': 0,\n"
        "    }\n"
        "    assert classify_failure(packet) == 'SURGEON_LOCAL_REPAIR'\n\n"
        "def test_true_graph_breach_escalates():\n"
        "    assert classify_failure({'dependency_graph_breach': True}) == 'ESCALATE_TO_COUNCIL_REPLAN'\n\n"
        "def test_exhausted_repair_budget_escalates():\n"
        "    assert classify_failure({'repair_attempt': 2}) == 'ESCALATE_TO_COUNCIL_REPLAN'\n"
    ),
    "tests/test_hidden.py": (
        "from arena_refactor.router import classify_failure\n"
        "from arena_refactor.state import RefactorState\n\n"
        "def test_false_string_flag_does_not_escalate():\n"
        "    assert classify_failure({'interface_contract_breach': 'false'}) == 'SURGEON_LOCAL_REPAIR'\n\n"
        "def test_true_string_flag_escalates():\n"
        "    assert classify_failure({'invariant_breach': 'true'}) == 'ESCALATE_TO_COUNCIL_REPLAN'\n\n"
        "def test_compact_ledger_excludes_raw_history_but_preserves_digest_and_count():\n"
        "    state = RefactorState(\n"
        "        plan_id='PLAN-1',\n"
        "        completed_tasks=['A1', 'A2'],\n"
        "        current_task='A3',\n"
        "        history=[{'event': 'stage', 'secret': 'do-not-replay'}],\n"
        "    )\n"
        "    ledger = state.compact_ledger()\n"
        "    assert ledger['plan_id'] == 'PLAN-1'\n"
        "    assert ledger['completed_tasks'] == ['A1', 'A2']\n"
        "    assert ledger['current_task'] == 'A3'\n"
        "    assert ledger['history_count'] == 1\n"
        "    assert len(ledger['last_event_digest']) == 24\n"
        "    assert 'history' not in ledger\n"
        "    assert 'do-not-replay' not in str(ledger)\n"
    ),
    "tests/test_regression.py": (
        "import inspect\n\n"
        "from arena_refactor import RefactorState, classify_failure, decide_next_action\n\n"
        "def test_public_signatures_remain_stable():\n"
        "    assert list(inspect.signature(classify_failure).parameters) == ['packet']\n"
        "    assert list(inspect.signature(RefactorState.compact_ledger).parameters) == ['self']\n"
        "    assert list(inspect.signature(decide_next_action).parameters) == ['state', 'failure']\n\n"
        "def test_service_return_shape_remains_stable():\n"
        "    result = decide_next_action(RefactorState('P1'), {'repair_attempt': 0})\n"
        "    assert set(result) == {'route', 'state_ledger'}\n"
        "    assert result['route'] == 'SURGEON_LOCAL_REPAIR'\n"
    ),
}

BROAD_ROUTER = (
    "from __future__ import annotations\n\n"
    "import json\n"
    "from typing import Any\n\n"
    "GRAPH_FAILURE_FIELDS = (\n"
    "    'dependency_graph_breach',\n"
    "    'interface_contract_breach',\n"
    "    'invariant_breach',\n"
    ")\n\n"
    "def classify_failure(packet: dict[str, Any]) -> str:\n"
    "    if any(packet.get(field) is True for field in GRAPH_FAILURE_FIELDS):\n"
    "        return 'ESCALATE_TO_COUNCIL_REPLAN'\n"
    "    if int(packet.get('repair_attempt', 0) or 0) >= 2:\n"
    "        return 'ESCALATE_TO_COUNCIL_REPLAN'\n"
    "    return 'SURGEON_LOCAL_REPAIR'\n"
)

SLICE_ROUTER = (
    "from __future__ import annotations\n\n"
    "import json\n"
    "from typing import Any\n\n"
    "GRAPH_FAILURE_FIELDS = (\n"
    "    'dependency_graph_breach',\n"
    "    'interface_contract_breach',\n"
    "    'invariant_breach',\n"
    ")\n\n"
    "def classify_failure(packet: dict[str, Any]) -> str:\n"
    "    if any(bool(packet.get(field)) for field in GRAPH_FAILURE_FIELDS):\n"
    "        return 'ESCALATE_TO_COUNCIL_REPLAN'\n"
    "    if int(packet.get('repair_attempt', 0) or 0) >= 2:\n"
    "        return 'ESCALATE_TO_COUNCIL_REPLAN'\n"
    "    return 'SURGEON_LOCAL_REPAIR'\n"
)

COUNCIL_ROUTER = (
    "from __future__ import annotations\n\n"
    "from typing import Any\n\n"
    "GRAPH_FAILURE_FIELDS = (\n"
    "    'dependency_graph_breach',\n"
    "    'interface_contract_breach',\n"
    "    'invariant_breach',\n"
    ")\n\n"
    "def _flag_enabled(value: Any) -> bool:\n"
    "    if isinstance(value, bool):\n"
    "        return value\n"
    "    if isinstance(value, (int, float)):\n"
    "        return value != 0\n"
    "    if isinstance(value, str):\n"
    "        return value.strip().lower() in {'1', 'true', 'yes', 'on', 'breach'}\n"
    "    return False\n\n"
    "def classify_failure(packet: dict[str, Any]) -> str:\n"
    "    if any(_flag_enabled(packet.get(field)) for field in GRAPH_FAILURE_FIELDS):\n"
    "        return 'ESCALATE_TO_COUNCIL_REPLAN'\n"
    "    if int(packet.get('repair_attempt', 0) or 0) >= 2:\n"
    "        return 'ESCALATE_TO_COUNCIL_REPLAN'\n"
    "    return 'SURGEON_LOCAL_REPAIR'\n"
)

COMPACT_STATE = (
    "from __future__ import annotations\n\n"
    "from dataclasses import dataclass, field\n"
    "import hashlib\n"
    "import json\n"
    "from typing import Any\n\n"
    "@dataclass\n"
    "class RefactorState:\n"
    "    plan_id: str\n"
    "    completed_tasks: list[str] = field(default_factory=list)\n"
    "    current_task: str | None = None\n"
    "    history: list[dict[str, Any]] = field(default_factory=list)\n\n"
    "    def compact_ledger(self) -> dict[str, Any]:\n"
    "        last_event = self.history[-1] if self.history else {}\n"
    "        body = json.dumps(last_event, sort_keys=True, separators=(',', ':'), default=str)\n"
    "        digest = hashlib.blake2b(body.encode('utf-8'), digest_size=12).hexdigest()\n"
    "        return {\n"
    "            'plan_id': self.plan_id,\n"
    "            'completed_tasks': list(self.completed_tasks),\n"
    "            'current_task': self.current_task,\n"
    "            'history_count': len(self.history),\n"
    "            'last_event_digest': digest,\n"
    "        }\n"
)


def _digest(text: str) -> str:
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()


def _diff(path: str, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )


def _arm_patch(arm: str) -> str:
    router_before = BASE_FILES["arena_refactor/router.py"]
    state_before = BASE_FILES["arena_refactor/state.py"]
    if arm == "broad_context":
        return _diff("arena_refactor/router.py", router_before, BROAD_ROUTER)
    if arm == "slice_surgeon":
        return (
            _diff("arena_refactor/router.py", router_before, SLICE_ROUTER)
            + _diff("arena_refactor/state.py", state_before, COMPACT_STATE)
        )
    if arm in {"council_v2", "council_v3"}:
        return (
            _diff("arena_refactor/router.py", router_before, COUNCIL_ROUTER)
            + _diff("arena_refactor/state.py", state_before, COMPACT_STATE)
        )
    raise KeyError(arm)


def _planning_tokens(planning: dict[str, Any], arm: str) -> dict[str, Any]:
    source = dict(dict(planning.get("arms") or {}).get(arm) or {})
    return {
        "model_calls": source.get("model_calls"),
        "input_tokens_estimated": source.get("input_tokens"),
        "output_tokens_estimated": source.get("output_tokens"),
        "total_tokens_estimated": source.get("total_tokens"),
        "input_tokens_reported": source.get("input_tokens_reported"),
        "output_tokens_reported": source.get("output_tokens_reported"),
        "reported_cost_usd": source.get("reported_cost_usd"),
    }


def _ablation_tokens(ablation: dict[str, Any], arm: str) -> dict[str, Any]:
    source = dict(dict(ablation.get("arms") or {}).get(arm) or {})
    return {
        "model_calls": source.get("call_count"),
        "input_tokens_estimated": source.get("input_tokens"),
        "output_tokens_estimated": source.get("output_tokens"),
        "total_tokens_estimated": source.get("total_tokens"),
        "input_tokens_reported": None,
        "output_tokens_reported": None,
        "reported_cost_usd": None,
    }


def generate(output_dir: Path, planning: dict[str, Any], ablation: dict[str, Any]) -> dict[str, Any]:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    base_dir = output_dir / "base"
    patch_dir = output_dir / "patches"
    spec_dir = output_dir / "specs"
    for directory in (base_dir, patch_dir, spec_dir):
        directory.mkdir(parents=True, exist_ok=True)
    for rel, text in BASE_FILES.items():
        path = base_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    token_map = {
        "broad_context": _planning_tokens(planning, "raw_broad_context"),
        "slice_surgeon": _planning_tokens(planning, "aura_slice_single"),
        "council_v2": _ablation_tokens(ablation, "v2"),
        "council_v3": _ablation_tokens(ablation, "v3"),
    }
    methods = {
        "broad_context": "BROAD_CONTEXT_SINGLE_IMPLEMENTER",
        "slice_surgeon": "AURA_SLICE_SINGLE_SURGEON",
        "council_v2": "COUNCIL_V2_PLAN_PLUS_SURGEON",
        "council_v3": "COUNCIL_V3_SELECTIVE_PLAN_PLUS_SURGEON",
    }
    records = []
    for arm in methods:
        patch = _arm_patch(arm)
        patch_path = patch_dir / f"{arm}.patch"
        patch_path.write_text(patch, encoding="utf-8")
        spec = {
            "benchmark_id": "AURA_EXECUTABLE_REFACTOR_CODE_QUALITY_V1",
            "run_id": "EXECUTABLE-FIXTURE-V1",
            "case_id": "failure-routing-state-ledger",
            "arm_id": arm,
            "method": methods[arm],
            "objective": OBJECTIVE,
            "fixture_root": str(base_dir),
            "patch_file": str(patch_path),
            "allowed_files": ["arena_refactor/router.py", "arena_refactor/state.py"],
            "visible_test_paths": ["tests/test_visible.py"],
            "hidden_test_paths": ["tests/test_hidden.py"],
            "regression_test_paths": ["tests/test_regression.py"],
            "protected_api_files": [
                "arena_refactor/router.py",
                "arena_refactor/state.py",
                "arena_refactor/service.py"
            ],
            "required_gates": [
                "patch_apply",
                "compile",
                "visible_tests",
                "hidden_tests",
                "regression_tests",
                "api_compatibility",
                "scope",
                "security"
            ],
            "run_ruff": true,
            "run_mypy": false,
            "run_bandit": true,
            "model": str(planning.get("model") or "GPT-5.6 Thinking fixture"),
            "provider": "single-session-assisted-fixture",
            "repository_commit_sha": str(planning.get("repository_commit_sha") or ""),
            "prompt_digest": _digest(OBJECTIVE + methods[arm]),
            "response_digest": _digest(patch),
            "token_usage": token_map[arm],
            "workload": {
                "fixture_version": FIXTURE_VERSION,
                "task_length_class": "CROSS_MODULE",
                "starting_files": 5,
                "authorized_files": 2,
                "visible_test_count": 3,
                "hidden_test_count": 3,
                "regression_test_count": 2,
                "hidden_tests_prompt_exposed": false,
                "patch_fixture_independence": "single_session_assisted_not_blinded"
            },
            "supplemental_metrics": {},
            "timeout_seconds": 60
        }
        (spec_dir / f"{arm}.json").write_text(
            json.dumps(spec, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        records.append({
            "arm_id": arm,
            "method": methods[arm],
            "patch": str(patch_path),
            "patch_digest": _digest(patch),
            "spec": str(spec_dir / f"{arm}.json"),
            "token_usage": token_map[arm],
        })

    manifest = {
        "fixture_version": FIXTURE_VERSION,
        "objective": OBJECTIVE,
        "arms": records,
        "limitations": [
            "Patch fixtures were authored in one assisted session and are not independent provider samples.",
            "The fixture is cross-module and executable but smaller than AuraOS production refactors.",
            "The Council V2 and V3 arms intentionally use the same patch to isolate critic-calling efficiency from implementation variance."
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--planning-report", type=Path, required=True)
    parser.add_argument("--calling-ablation", type=Path, required=True)
    args = parser.parse_args()
    planning = json.loads(args.planning_report.read_text(encoding="utf-8"))
    ablation = json.loads(args.calling_ablation.read_text(encoding="utf-8"))
    manifest = generate(args.output_dir, planning, ablation)
    print(json.dumps({"fixture_version": manifest["fixture_version"], "arm_count": len(manifest["arms"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
