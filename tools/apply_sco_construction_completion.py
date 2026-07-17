"""Apply the bounded final SCO Construction Human Agent/Observatory wiring."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one anchor, found {count}: {old[:80]!r}")
    write(path, text.replace(old, new, 1))


def insert_before(path: str, marker: str, insertion: str, sentinel: str) -> None:
    text = read(path)
    if sentinel in text:
        return
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f"{path}: expected one marker, found {count}: {marker[:80]!r}")
    write(path, text.replace(marker, insertion + marker, 1))


def patch_profile_service() -> None:
    path = "aura_construction_human_agent.py"
    method = '''    def bind_checkpoint(self, checkpoint_id: str) -> ConstructionHumanAgentProfile:
        """Rebuild the immutable profile with one reviewed checkpoint reference."""
        if (
            self.fixture is None
            or self.state is None
            or self.evaluation is None
            or self.profile is None
        ):
            raise KeyError("Construction Human Agent profile is unavailable")
        profile = build_construction_human_agent_profile(
            self.state,
            self.evaluation,
            candidates=self.fixture.candidates,
            checkpoint_id=checkpoint_id,
            synthetic=self.profile.synthetic,
        )
        self.profile = profile
        return profile

'''
    insert_before(path, "    def status(self) -> dict[str, Any]:\n", method, "    def bind_checkpoint(")


def patch_completion_order() -> None:
    path = "aura_construction_refactor_completion.py"
    replace_once(
        path,
        "        for node_id, owners in sorted(_REQUIRED_SYMBOLS.items())\n",
        "        for node_id, owners in sorted(\n"
        "            _REQUIRED_SYMBOLS.items(), key=lambda item: int(item[0][1:])\n"
        "        )\n",
    )


def patch_profile_test() -> None:
    path = "tests/test_aura_construction_human_agent.py"
    replace_once(
        path,
        "from dataclasses import replace\n\nimport pytest\n",
        "from dataclasses import asdict\n\nimport pytest\n",
    )
    replace_once(
        path,
        "    ConstructionArenaMode,\n    evaluate_construction_candidates,\n",
        "    ConstructionArenaMode,\n"
        "    ConstructionCoordinationEvaluation,\n"
        "    evaluate_construction_candidates,\n",
    )
    replace_once(
        path,
        "from aura_construction_human_agent import (\n",
        "from aura_event_contracts import stable_digest, stable_id\n"
        "from aura_construction_human_agent import (\n",
    )
    old = '''def test_profile_rejects_evaluation_from_another_state():
    fixture, evaluation = _profile_inputs()
    mismatched = replace(evaluation, state_digest="wrong-state-digest")

    with pytest.raises(ValueError, match="evaluation does not bind"):
        build_construction_human_agent_profile(
            fixture.state,
            mismatched,
            candidates=fixture.candidates,
        )
'''
    new = '''def test_profile_rejects_evaluation_from_another_state():
    fixture, evaluation = _profile_inputs()
    values = asdict(evaluation)
    values.pop("evaluation_id")
    values.pop("evaluation_digest")
    values["state_digest"] = "wrong-state-digest"
    payload = dict(values)
    mismatched = ConstructionCoordinationEvaluation(
        evaluation_id=stable_id("construction-evaluation", payload),
        evaluation_digest=stable_digest(payload),
        **values,
    )

    with pytest.raises(ValueError, match="evaluation does not bind"):
        build_construction_human_agent_profile(
            fixture.state,
            mismatched,
            candidates=fixture.candidates,
        )
'''
    replace_once(path, old, new)


def patch_server() -> None:
    path = "aura_human_agent_arena_server.py"
    replace_once(
        path,
        "from aura_coding_workbench_wfst_adapter import CodingWorkbenchWFSTSession\n",
        "from aura_coding_workbench_wfst_adapter import CodingWorkbenchWFSTSession\n"
        "from aura_construction_human_agent import ConstructionHumanAgentProfileService\n",
    )
    replace_once(
        path,
        'SERVER_VERSION = "AURA_HUMAN_AGENT_ARENA_SERVER_V0_5"',
        'SERVER_VERSION = "AURA_HUMAN_AGENT_ARENA_SERVER_V0_6"',
    )
    replace_once(
        path,
        "        self.coding_workbench = CodingWorkbenchWFSTSession(self.repo_root)\n",
        "        self.coding_workbench = CodingWorkbenchWFSTSession(self.repo_root)\n"
        "        self.construction_profile = ConstructionHumanAgentProfileService(\n"
        "            demo=self.demo\n"
        "        )\n",
    )
    routes = '''    if method == "GET" and route == "/api/human-agent/construction/status":
        return 200, state.construction_profile.status()

    if method == "GET" and route == "/api/human-agent/construction/profile":
        try:
            return 200, state.construction_profile.get_profile()
        except KeyError as exc:
            return _error(f"construction_profile_unavailable:{exc}", 404)

    if method == "GET" and route == "/api/human-agent/construction/observatory":
        try:
            return 200, state.construction_profile.get_observatory_projection()
        except KeyError as exc:
            return _error(f"construction_observatory_unavailable:{exc}", 404)

    if method == "GET" and route.startswith("/api/human-agent/construction/candidates/"):
        candidate_id = route.rsplit("/", 1)[-1]
        try:
            return 200, state.construction_profile.get_candidate(candidate_id)
        except KeyError as exc:
            return _error(f"construction_candidate_unavailable:{exc}", 404)
        except ValueError as exc:
            return _error(f"construction_candidate_invalid:{exc}")

    if method == "POST" and route == "/api/human-agent/construction/handoff":
        try:
            result = state.construction_profile.prepare_handoff(
                str(body.get("target_arena_id") or "")
            )
        except KeyError as exc:
            return _error(f"construction_profile_unavailable:{exc}", 404)
        except ValueError as exc:
            return _error(f"construction_handoff_invalid:{exc}")
        return 200, result

    if method == "POST" and route == "/api/human-agent/construction/checkpoint":
        construction_state = state.construction_profile.state
        if construction_state is None:
            return _error("construction_profile_unavailable", 404)
        repo_head = str(body.get("repo_head") or "").strip()
        if not repo_head:
            return _error("repo_head is required")
        try:
            result = state.persistence.checkpoint_construction(
                construction_state,
                repo_head=repo_head,
                parent_checkpoint_id=str(body.get("parent_checkpoint_id") or ""),
                branch_name=str(body.get("branch_name") or ""),
            )
            checkpoint_id = str(
                (result.get("checkpoint") or {}).get("checkpoint_id") or ""
            )
            if checkpoint_id:
                profile = state.construction_profile.bind_checkpoint(checkpoint_id)
                result["profile_id"] = profile.profile_id
                result["profile_digest"] = profile.profile_digest
        except (KeyError, ValueError) as exc:
            return _error(f"construction_checkpoint_failed:{exc}")
        return 200, result

'''
    insert_before(
        path,
        '    if method == "GET" and route == "/api/human-agent/state":\n',
        routes,
        'route == "/api/human-agent/construction/status"',
    )
    replace_once(
        path,
        '            "coding_workbench": state.coding_workbench.get_state(),\n',
        '            "coding_workbench": state.coding_workbench.get_state(),\n'
        '            "construction_profile": state.construction_profile.status(),\n',
    )


def patch_index() -> None:
    path = "aura_human_agent_arena/index.html"
    replace_once(
        path,
        '  <link rel="stylesheet" href="emergent.css">\n',
        '  <link rel="stylesheet" href="emergent.css">\n'
        '  <link rel="stylesheet" href="construction.css">\n',
    )
    replace_once(
        path,
        '      <button class="surface-tab" data-surface="civic-workspace" type="button">Civic Arena</button>\n',
        '      <button class="surface-tab" data-surface="civic-workspace" type="button">Civic Arena</button>\n'
        '      <button class="surface-tab" data-surface="construction-workspace" type="button">Construction</button>\n',
    )
    section = '''  <section id="construction-workspace" class="surface construction-surface" aria-label="SCO Construction Human Agent review surface">
    <div class="construction-shell">
      <section class="construction-hero">
        <div>
          <p class="eyebrow">SCO Construction Human Agent profile</p>
          <h1>Review exact blockers and proposal-only options.</h1>
          <p>This surface projects a deterministic synthetic Construction state into bounded candidate summaries. Raw records stay with the canonical Construction owners, and every consequential decision remains external.</p>
        </div>
        <div id="construction-authority" class="construction-authority">
          <strong>Human decision required</strong>
          <span>No physical, payment, access, safety, engineering, legal, or regulatory authority.</span>
        </div>
      </section>
      <div class="construction-toolbar">
        <span id="construction-status" class="status-pill">Open the surface to load the profile.</span>
        <button id="construction-refresh" type="button">Refresh exact profile</button>
        <select id="construction-handoff-target" aria-label="Handoff target">
          <option value="agent_bridge_arena">Agent Bridge Arena</option>
          <option value="coding_arena">Coding Arena</option>
          <option value="human_agent_arena">Human Agent Arena</option>
        </select>
        <button id="construction-handoff" type="button">Prepare digital baton</button>
      </div>
      <section id="construction-summary" class="construction-summary"></section>
      <div class="construction-grid">
        <section>
          <div class="section-heading"><div><p class="eyebrow">Human review queue</p><h2>Admissible and blocked candidates</h2></div></div>
          <div id="construction-candidates" class="construction-candidates"><p class="placeholder">No profile loaded.</p></div>
        </section>
        <aside class="construction-side">
          <section class="construction-panel"><h2>Bounded candidate record</h2><div id="construction-inspector"><p class="placeholder">Inspect a candidate. Raw evidence is never included.</p></div></section>
          <section class="construction-panel"><h2>Read-only Observatory</h2><div id="construction-observatory"><p class="placeholder">IDs, digests, status counts, and gates only.</p></div></section>
          <section class="construction-panel"><h2>Cross-Arena baton</h2><div id="construction-handoff-result"><p class="placeholder">A baton contains references only and never mutates the target Arena.</p></div></section>
        </aside>
      </div>
    </div>
  </section>

'''
    insert_before(
        path,
        '  <section id="civic-workspace" class="surface civic-map-surface" aria-label="Civic Commons Arena">\n',
        section,
        'id="construction-workspace"',
    )
    replace_once(
        path,
        '  <script src="emergent.js"></script>\n  <script src="main.js"></script>\n',
        '  <script src="emergent.js"></script>\n'
        '  <script src="construction.js"></script>\n'
        '  <script src="main.js"></script>\n',
    )


def patch_readme() -> None:
    section = '''## Construction Human Agent profile

The final SCO Construction wiring adds a purpose-limited review surface without creating another project truth store:

```text
ConstructionProjectState + verified evaluation
  → ConstructionHumanAgentProfile
  → bounded candidate summaries and visible hard blockers
  → read-only Observatory IDs/digests/statuses
  → optional review-gated checkpoint or payload-free handoff
  → external authorized human decision
```

Primary files:

- `aura_construction_human_agent.py`
- `aura_construction_refactor_completion.py`
- `aura_human_agent_arena_server.py`
- `aura_human_agent_arena/construction.js`
- `aura_human_agent_arena/construction.css`

The browser surface cannot approve work. It exports no raw Construction evidence and provides no execution methods. Real connectors, physical control, payment release, access control, professional certification, and automatic merge remain explicit policy deferrals.

Run the completion gate with:

```bash
python3 -m aura_construction_refactor_completion --repo-root .
```

'''
    insert_before(
        "README.md",
        "## Temporal persistence across arenas\n",
        section,
        "## Construction Human Agent profile",
    )


def patch_architecture() -> None:
    path = ".aura/ARCHITECTURE.md"
    replace_once(
        path,
        "**Architecture audit:** through SCO Construction Phase 3 E7–E11 verification in PR #148 and the canonical Human Agent, Observatory, Experience, Crucible, Council, and Surgeon boundaries.  \n",
        "**Architecture audit:** through SCO Construction E0–E14 final Human Agent/Observatory integration and the canonical Human Agent, Agent Bridge, persistence, Experience, Crucible, Council, and Surgeon boundaries.  \n",
    )
    section = '''## 7. Construction Human Agent and Observatory

The Construction Human Agent profile is a narrow projection over exact canonical owners:

```text
ConstructionProjectState
  + ConstructionCoordinationEvaluation
  → purpose-limited Human Agent profile
  → read-only Observatory projection
  → checkpoint or payload-free baton when requested
```

The Human Agent profile may expose candidate title, summary, proposal deltas, hard blockers, deterministic score, and the next external authority route. It does not copy raw claims, evidence, source references, actors, or payloads into the profile.

The Observatory projection is stricter: it exposes only project/profile/evaluation identifiers and digests, candidate admissibility/recommendation/blocker counts, option IDs, checkpoint reference, and authority flags. Candidate narratives, amounts, raw records, and execution methods are omitted.

Architectural invariants:

- `ConstructionProjectState` remains the only Construction truth owner;
- evaluation state digest must exactly match the projected state;
- all evaluation candidate IDs must match exact supplied candidates;
- blocked candidates remain visible but cannot be recommended;
- the browser has no approve or execute operation;
- cross-Arena handoff is a payload-free digital baton and cannot mutate the target Arena;
- checkpoint creation remains review-gated temporal persistence;
- physical work, payment, access, equipment, safety, engineering, legal, regulatory, commit, push, PR, and merge authority remain false.

The E0–E14 completion state is machine checked by `aura_construction_refactor_completion.py`; explicit policy deferrals are not misclassified as unfinished implementation.

'''
    insert_before(
        path,
        "## 7. Temporal persistence plane\n",
        section,
        "## 7. Construction Human Agent and Observatory",
    )
    replace_once(path, "## 7. Temporal persistence plane\n", "## 8. Temporal persistence plane\n")
    replace_once(path, "## 8. Benchmark evidence hierarchy\n", "## 9. Benchmark evidence hierarchy\n")


def patch_user_guide() -> None:
    path = "USER_GUIDE.md"
    replace_once(
        path,
        "**Documentation audit:** through SCO Construction Phase 3 E7–E11 verification in PR #148 and the canonical Human Agent, Observatory, Experience, Crucible, Council, and Surgeon documentation sync.  \n",
        "**Documentation audit:** through SCO Construction E0–E14 final Human Agent/Observatory integration and the canonical Human Agent, Agent Bridge, persistence, Experience, Crucible, Council, and Surgeon documentation sync.  \n",
    )
    section = '''## 10. Construction review surface

Launch the Human Agent Arena with the deterministic fictional Construction profile:

```bash
python3 aura_human_agent_arena_server.py --repo-root . --demo
```

Open the **Construction** tab. The surface shows:

- the exact project, state, event-chain, evaluation, and profile identities;
- admissible and blocked proposal candidates;
- hard blockers that cannot be overridden by model or sensor scores;
- projected time/cost/idle deltas labeled as proposal data;
- the next external human/professional/owner/legal authority route;
- a stricter read-only Observatory projection;
- a payload-free cross-Arena baton.

Construction endpoints:

```text
GET  /api/human-agent/construction/status
GET  /api/human-agent/construction/profile
GET  /api/human-agent/construction/observatory
GET  /api/human-agent/construction/candidates/{candidate_id}
POST /api/human-agent/construction/handoff
POST /api/human-agent/construction/checkpoint
```

The checkpoint endpoint requires the exact current repository HEAD:

```json
{
  "repo_head": "<git rev-parse HEAD>",
  "parent_checkpoint_id": "",
  "branch_name": ""
}
```

The profile and browser surface contain no raw Construction records and cannot authorize or execute work. Without `--demo`, the profile remains unavailable until an exact reviewed Construction state is loaded; Aura never invents one.

Validate the completed refactor:

```bash
python3 -m aura_construction_refactor_completion --repo-root .
```

The pre-merge result must contain `runtime_complete: true` and `e14_release_status: READY_FOR_PINNED_MERGE`.

'''
    insert_before(
        path,
        "## 10. Temporal persistence and cross-Arena handoff\n",
        section,
        "## 10. Construction review surface",
    )
    replace_once(
        path,
        "## 10. Temporal persistence and cross-Arena handoff\n",
        "## 11. Temporal persistence and cross-Arena handoff\n",
    )
    replace_once(path, "## 11. Cost and benchmark interpretation\n", "## 12. Cost and benchmark interpretation\n")
    replace_once(path, "## 12. Testing\n", "## 13. Testing\n")
    replace_once(path, "## 13. Troubleshooting\n", "## 14. Troubleshooting\n")
    replace_once(path, "## 14. Safety rules\n", "## 15. Safety rules\n")


def patch_refactor_plan() -> None:
    path = "aura_construction_refactor_plan.py"
    replace_once(
        path,
        '    """Create the E0-E14 skeleton; all implementation remains closed."""\n',
        '    """Create the original E0-E14 planning skeleton.\n\n'
        '    Current completion is validated by aura_construction_refactor_completion.py;\n'
        '    this historical skeleton remains stable for provenance and replay.\n'
        '    """\n',
    )


def main() -> None:
    patch_profile_service()
    patch_completion_order()
    patch_profile_test()
    patch_server()
    patch_index()
    patch_readme()
    patch_architecture()
    patch_user_guide()
    patch_refactor_plan()


if __name__ == "__main__":
    main()
