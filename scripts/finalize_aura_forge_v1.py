from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"missing source fragment in {path}: {old[:80]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def insert_before(path: str, anchor: str, block: str, marker: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if marker in text:
        return
    if anchor not in text:
        raise SystemExit(f"missing anchor in {path}: {anchor}")
    target.write_text(text.replace(anchor, block.rstrip() + "\n\n" + anchor, 1), encoding="utf-8")


def insert_after(path: str, anchor: str, block: str, marker: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if marker in text:
        return
    if anchor not in text:
        raise SystemExit(f"missing anchor in {path}: {anchor}")
    target.write_text(text.replace(anchor, anchor + "\n" + block.rstrip(), 1), encoding="utf-8")


def harden_source() -> None:
    replace_once(
        "aura_forge.py",
        '''DEFAULT_REQUIRED_GATES = (
    "patch_apply",
    "compile",
    "visible_tests",
    "hidden_tests",
    "regression_tests",
    "api_compatibility",
    "scope",
    "security",
)
''',
        '''DEFAULT_REQUIRED_GATES = (
    "canonical_arena_verifier",
    "hotswap_readiness",
)
SUPPORTED_REQUIRED_GATES = frozenset(DEFAULT_REQUIRED_GATES)
''',
    )
    replace_once(
        "aura_forge.py",
        '''_SECRET_FRAGMENTS = (
    "api_key",
    "password",
    "private_key",
    "secret",
    "token",
    "credential",
)
''',
        '''_SECRET_KEYS = frozenset({
    "api_key",
    "password",
    "private_key",
    "secret",
    "credential",
    "credentials",
    "access_token",
    "auth_token",
    "bearer_token",
    "refresh_token",
})
_SECRET_SUFFIXES = ("_api_key", "_password", "_private_key", "_secret", "_credential")
''',
    )
    replace_once(
        "aura_forge.py",
        '    normalized = path.as_posix().lstrip("./")\n',
        '    normalized = path.as_posix()\n    while normalized.startswith("./"):\n        normalized = normalized[2:]\n',
    )
    replace_once(
        "aura_forge.py",
        '            if any(fragment in lowered for fragment in _SECRET_FRAGMENTS):\n                continue\n',
        '            if lowered in _SECRET_KEYS or lowered.endswith(_SECRET_SUFFIXES):\n                continue\n',
    )
    replace_once(
        "aura_forge.py",
        '        if not gates:\n            raise ValueError("required_gates must not be empty")\n',
        '        if not gates:\n            raise ValueError("required_gates must not be empty")\n        unsupported = sorted(set(gates) - SUPPORTED_REQUIRED_GATES)\n        if unsupported:\n            raise ValueError(f"unsupported required_gates: {unsupported}")\n',
    )
    replace_once(
        "aura_forge.py",
        '        self._runs: dict[str, dict[str, Any]] = {}\n',
        '        self._runs: dict[str, dict[str, Any]] = {}\n        self._run_counter = 0\n',
    )
    replace_once(
        "aura_forge.py",
        '        run_id = f"FORGE-{contract.contract_id[:20]}"\n',
        '        self._run_counter += 1\n        run_id = f"FORGE-{contract.contract_id[:16]}-{self._run_counter:04d}"\n',
    )
    replace_once(
        "aura_forge.py",
        '''        return {
            "version": FORGE_VERSION,
            "run_id": run_id,
            **_sanitize(result),
''',
        '''        return {
            **_sanitize(result),
            "version": FORGE_VERSION,
            "run_id": run_id,
''',
    )
    replace_once(
        "aura_forge.py",
        '''        ready = state["status"] == REVIEW_READY_STATUS
        proof_ready = verification.get("hotswap_ready") is True or hotswap_status.get("hotswap_ready") is True
        decision_eligible = bool(ready and proof_ready)
''',
        '''        ready = state["status"] == REVIEW_READY_STATUS
        gate_results = {
            "canonical_arena_verifier": bool(
                verification.get("ok") is True and not list(verification.get("failures") or [])
            ),
            "hotswap_readiness": bool(
                verification.get("hotswap_ready") is True
                or hotswap_status.get("hotswap_ready") is True
            ),
        }
        required = state["contract"].required_gates
        decision_eligible = bool(ready and all(gate_results.get(name) is True for name in required))
''',
    )
    replace_once(
        "aura_forge.py",
        '            "decision_eligible": decision_eligible,\n',
        '            "required_gate_results": gate_results,\n            "decision_eligible": decision_eligible,\n',
    )
    replace_once(
        "aura_forge.py",
        '''        return {
            "version": FORGE_VERSION,
            "run_id": run_id,
            "contract_id": state["contract"].contract_id,
            **_sanitize(result),
''',
        '''        return {
            **_sanitize(result),
            "version": FORGE_VERSION,
            "run_id": run_id,
            "contract_id": state["contract"].contract_id,
''',
    )
    replace_once(
        "aura_forge.py",
        '    "REVIEW_READY_STATUS",\n',
        '    "REVIEW_READY_STATUS",\n    "SUPPORTED_REQUIRED_GATES",\n',
    )


def harden_tests() -> None:
    replace_once(
        "tests/test_aura_forge.py",
        '            "verification": {"hotswap_ready": True, "tests": {"passed": 8, "total": 8}},\n',
        '            "verification": {"ok": True, "hotswap_ready": True, "failures": [], "tests": {"passed": 8, "total": 8}},\n',
    )
    replace_once(
        "tests/test_aura_forge.py",
        '    assert first["run_id"] == second["run_id"]\n',
        '    assert first["run_id"].endswith("-0001")\n    assert second["run_id"].endswith("-0001")\n',
    )
    replace_once(
        "tests/test_aura_forge.py",
        '    assert packet["promotion_performed"] is False\n',
        '''    assert packet["required_gate_results"] == {
        "canonical_arena_verifier": True,
        "hotswap_readiness": True,
    }
    assert packet["promotion_performed"] is False
''',
    )
    replace_once(
        "tests/test_aura_forge.py",
        '''    else:
        raise AssertionError("invalid max_turns was accepted")


def test_export_delegates_to_safe_session_owner''',
        '''    else:
        raise AssertionError("invalid max_turns was accepted")

    try:
        ForgeRunRequest.from_value({"objective": "x", "required_gates": ["hidden_tests"]})
    except ValueError as exc:
        assert "unsupported required_gates" in str(exc)
    else:
        raise AssertionError("unsupported gate was accepted")


def test_dot_prefixed_repository_paths_are_preserved() -> None:
    parsed = ForgeRunRequest.from_value({"objective": "x", "target_file": ".aura/ARCHITECTURE.md"})
    assert parsed.target_file == ".aura/ARCHITECTURE.md"


def test_export_delegates_to_safe_session_owner''',
    )


def update_docs() -> None:
    readme_row_anchor = (
        "| **Coding Workbench / Coding Arena** | Localizes code, ranks bounded regions, "
        "builds change graphs, prepares capsules, and verifies candidate work | Exact source "
        "spans and hashes remain patch authority |"
    )
    readme_row = (
        "| **Aura Forge** | Compiles a frozen Coding Arena plan and Arena Evidence Contract, "
        "then runs bounded Council–Surgeon slice sessions | Stops at verifier-backed human "
        "review; no automatic commit, PR, merge, or production mutation |"
    )
    insert_after("README.md", readme_row_anchor, readme_row, "| **Aura Forge** |")

    readme_block = '''<!-- AURA_FORGE_V1:START -->
## Aura Forge — Verified Engineering OS

Aura Forge is the first commercial product surface over Aura's existing Coding Arena and
controlled refactor owners. It does not introduce a second planner, patch store, verifier,
or learning path.

```text
engineering objective
  → CODEMAP/topology grounding
  → frozen Architect/Coding Arena plan
  → AURA_FORGE_ARENA_EVIDENCE_CONTRACT_V1
  → bounded source/test slice lease
  → external worker unified diff
  → canonical staging, verification, and repair
  → READY_FOR_HUMAN_REVIEW
  → separate authorized promotion decision
```

`aura_forge.py` binds the objective, exact repository identity, plan phase, Act Capsules,
source/test references, allowed files, required gates, worker budgets, authority, and
lifecycle into one deterministic contract. External workers remain replaceable and receive
no ambient repository or release authority.

See [`docs/AURA_FORGE.md`](docs/AURA_FORGE.md).
<!-- AURA_FORGE_V1:END -->'''
    insert_before("README.md", "## Canonical architecture", readme_block, "<!-- AURA_FORGE_V1:START -->")

    architecture_block = '''<!-- AURA_FORGE_V1:START -->
#### Aura Forge verified engineering surface

Aura Forge is a product façade over the canonical Coding Arena, Agent Bridge, frozen
Architect plan, Controlled Refactor Session, safe external-LLM slice leasing, staging,
verification, output-vault, and human-review owners.

```text
FRAME → GROUND → PLAN
  → Arena Evidence Contract
  → ACT through bounded Surgeon turns
  → PROVE through canonical verifiers
  → DECIDE through a human review packet
  → DISSOLVE or enter a separately authorized promotion workflow
```

`AURA_FORGE_ARENA_EVIDENCE_CONTRACT_V1` preserves exact repository/CODEMAP identity,
plan-phase identity, Act Capsules, source line ranges, dependencies, tests, route evidence,
allowed files, required gates, model budgets, and non-promotion authority invariants.

Forge cannot commit, push, open a pull request, merge, mutate production, or convert
hotswap readiness into promotion authority.
<!-- AURA_FORGE_V1:END -->'''
    insert_before(
        ".aura/ARCHITECTURE.md",
        "### Plane 8 — Observatory and glass-box explanation",
        architecture_block,
        "<!-- AURA_FORGE_V1:START -->",
    )

    guide_row_anchor = (
        "| **Agent Arena CLI** | Repository health, localization, prepared coding tasks, "
        "staging, verification, cost, and domain commands | `python3 -m aura_agent_arena_cli` |"
    )
    guide_row = (
        "| **Aura Forge API** | Frozen-plan verified engineering runs with an exact Arena "
        "Evidence Contract and bounded worker sessions | `from aura_forge import AuraForgeRuntime` |"
    )
    insert_after("USER_GUIDE.md", guide_row_anchor, guide_row, "| **Aura Forge API** |")

    guide_block = '''### Aura Forge V1

Use Forge when a coding task needs a stable product-level contract around the existing
Coding Arena workflow.

```python
from aura_forge import AuraForgeRuntime

forge = AuraForgeRuntime(repo_root=".")
opened = forge.start({
    "objective": "Refactor failure routing while preserving public APIs",
    "target_file": "pkg/router.py",
    "target_symbol": "route_failure",
    "acceptance_criteria": ["canonical Arena verification passes"],
    "risk_map": ["interface drift", "scope expansion"],
    "provider": "external",
    "model": "provider-model",
})
```

Inspect `opened["contract"]` before sending the leased turn to a worker. The contract
includes exact task evidence, allowed files, supported required gates, budgets, and
authority limits. Submit only the worker's bounded unified diff through `forge.submit(...)`.

A completed run stops at `READY_FOR_HUMAN_REVIEW`. `human_review_packet` reports the
canonical Arena verifier and hotswap-readiness gates. It never performs promotion, commit,
push, pull-request creation, merge, or production mutation.

Focused validation:

```bash
python -m py_compile aura_forge.py tests/test_aura_forge.py
python -m pytest -q tests/test_aura_forge.py
```

See `docs/AURA_FORGE.md` for the complete contract and failure boundaries.
'''
    insert_before("USER_GUIDE.md", "### Grounded phase capsules", guide_block, "### Aura Forge V1")


def main() -> None:
    harden_source()
    harden_tests()
    update_docs()


if __name__ == "__main__":
    main()
