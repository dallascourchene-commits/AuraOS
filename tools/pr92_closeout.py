from __future__ import annotations

"""Deterministic PR #92 closeout repairs and architecture documentation refresh.

This helper is intentionally deleted before the final CODEMAP regeneration and commit.
It performs only exact, reviewable text transformations against the PR branch.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT_WINDOW = "June 14–July 14, 2026"
METRICS_TOKEN = "__AURA_CODEMAP_METRICS__"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def upsert_block(text: str, start: str, end: str, block: str, *, before: str) -> str:
    if start in text:
        left, remainder = text.split(start, 1)
        if end not in remainder:
            raise RuntimeError(f"unterminated documentation block: {start}")
        _, right = remainder.split(end, 1)
        text = left + right.lstrip("\n")
    if before not in text:
        raise RuntimeError(f"documentation insertion marker not found: {before}")
    rendered = f"{start}\n{block.strip()}\n{end}\n\n"
    return text.replace(before, rendered + before, 1)


def fix_dynamic_import() -> None:
    path = "test_aura_coding_arena_workflow.py"
    text = read(path)
    if "import aura_coding_arena_workflow as acaw" not in text:
        text = replace_once(
            text,
            "import pytest\n\nfrom aura_coding_arena_workflow import (",
            "import pytest\n\nimport aura_coding_arena_workflow as acaw\nfrom aura_coding_arena_workflow import (",
            label="coding arena module import",
        )
    text = text.replace(
        "        import importlib\n        acaw = importlib.import_module(\"aura_coding_arena_workflow\")\n",
        "",
        1,
    )
    if "importlib.import_module" in text:
        raise RuntimeError("dynamic import remains in coding arena workflow test")
    write(path, text)


def fix_symbol_relative_mesh_fixture() -> None:
    benchmark_path = "aura_matrix_benchmark.py"
    text = read(benchmark_path)
    if "from pathlib import Path" not in text:
        text = replace_once(
            text,
            "import os\nimport time\n",
            "import os\nfrom pathlib import Path\nimport time\n",
            label="benchmark Path import",
        )

    helper_start = "# PR92:MESH_FIXTURE_HELPER:START"
    helper = r'''
# PR92:MESH_FIXTURE_HELPER:START
def _mesh_offload_fixture() -> tuple[int, str, str]:
    """Resolve the benchmark edit target inside ``offload_compute`` by symbol.

    The benchmark used to carry a repository-global line number. That became
    invalid as ``aura_mesh.py`` evolved. The fixture now locates the exact
    secure-packet assignment inside the function and returns its current line,
    source text, and indentation.
    """
    source_path = Path(REPO_ROOT) / "aura_mesh.py"
    lines = source_path.read_text(encoding="utf-8").splitlines()
    function_start = next(
        index for index, line in enumerate(lines)
        if line.lstrip().startswith("async def offload_compute(")
    )
    function_indent = len(lines[function_start]) - len(lines[function_start].lstrip())
    function_end = len(lines)
    for index in range(function_start + 1, len(lines)):
        stripped = lines[index].lstrip()
        indent = len(lines[index]) - len(stripped)
        if stripped.startswith(("def ", "async def ")) and indent == function_indent:
            function_end = index
            break
    target_index = next(
        index for index in range(function_start, function_end)
        if "secure_packet:" in lines[index]
        and "pack_length_prefixed_payload(payload_obj)" in lines[index]
    )
    original = lines[target_index]
    indentation = original[: len(original) - len(original.lstrip())]
    return target_index + 1, original, indentation
# PR92:MESH_FIXTURE_HELPER:END
'''.strip()
    if helper_start not in text:
        marker = "# --------------------------------------------------------------------------- #\n# Offline mock egress (deterministic; for pipeline testing only)\n# --------------------------------------------------------------------------- #\n"
        text = replace_once(text, marker, helper + "\n\n\n" + marker, label="benchmark helper insertion")

    old_branch = '''        if is_aura and wants_edit_plan:
            text = (
                '{"edits": [{"file": "aura_mesh.py", "start_line": 174, '
                '"end_line": 174, "replacement": "            secure_packet = '
                'self.pack_secure_polysynthetic_packet([0, 0, 0, 0, 0, 0], 1.0)"}]}'
            )
        elif is_aura:
            text = (
                "--- a/aura_mesh.py\\n+++ b/aura_mesh.py\\n"
                "@@ -172,3 +172,4 @@\\n"
                "         try:\\n"
                "             print(f\"[*] Offloading {module} to {target_ip}:4445...\")\\n"
                "+            # validate target before packing (no new deps)\\n"
                "             secure_packet = self.pack_secure_polysynthetic_packet("
                "[0, 0, 0, 0, 0, 0], 1.0)\\n"
            )
'''
    new_branch = '''        if is_aura:
            target_line, original_line, indentation = _mesh_offload_fixture()
            replacement = (
                f"{indentation}secure_packet = "
                "self.pack_secure_polysynthetic_packet([0, 0, 0, 0, 0, 0], 1.0)"
            )
        if is_aura and wants_edit_plan:
            text = json.dumps(
                {
                    "edits": [
                        {
                            "file": "aura_mesh.py",
                            "start_line": target_line,
                            "end_line": target_line,
                            "replacement": replacement,
                        }
                    ]
                }
            )
        elif is_aura:
            text = (
                "--- a/aura_mesh.py\\n+++ b/aura_mesh.py\\n"
                f"@@ -{target_line},1 +{target_line},2 @@\\n"
                f"-{original_line}\\n"
                f"+{indentation}# validate target before packing (no new deps)\\n"
                f"+{replacement}\\n"
            )
'''
    if old_branch in text:
        text = text.replace(old_branch, new_branch, 1)
    elif "start_line\": 174" in text or "@@ -172,3 +172,4 @@" in text:
        raise RuntimeError("stale benchmark fixture remains but expected block changed")
    write(benchmark_path, text)

    test_path = "test_aura_substrate.py"
    test_text = read(test_path)
    old_test = '''    original = ContextSelector().read("aura_mesh.py")
    good = ('{"edits": [{"file": "aura_mesh.py", "start_line": 174, "end_line": 174, '
            '"replacement": "            secure_packet = '
            'self.pack_secure_polysynthetic_packet([0, 0, 0, 0, 0, 0], 1.0)"}]}')
'''
    new_test = '''    original = ContextSelector().read("aura_mesh.py")
    function_source, function_start, _function_end = extract_function_source(
        original, "offload_compute"
    )
    assert function_source is not None
    target_offset = next(
        offset for offset, line in enumerate(function_source.splitlines())
        if "secure_packet:" in line
        and "pack_length_prefixed_payload(payload_obj)" in line
    )
    target_line = function_start + target_offset
    original_line = original.splitlines()[target_line - 1]
    indentation = original_line[: len(original_line) - len(original_line.lstrip())]
    good = json.dumps(
        {
            "edits": [
                {
                    "file": "aura_mesh.py",
                    "start_line": target_line,
                    "end_line": target_line,
                    "replacement": (
                        f"{indentation}secure_packet = "
                        "self.pack_secure_polysynthetic_packet("
                        "[0, 0, 0, 0, 0, 0], 1.0)"
                    ),
                }
            ]
        }
    )
'''
    if old_test in test_text:
        test_text = test_text.replace(old_test, new_test, 1)
    elif '"start_line": 174' in test_text:
        raise RuntimeError("stale substrate fixture remains but expected block changed")
    write(test_path, test_text)


def update_readme() -> None:
    path = "README.md"
    text = read(path)
    block = f'''
## Current Implemented Architecture

**Implementation audit:** {AUDIT_WINDOW} · **Generated topology:** {METRICS_TOKEN}

The current repository combines the earlier substrate with the major capabilities added during the audit window:

- canonical six-slot and machine-FST routing, guarded WFST challenge paths, and C1/C2 route capsules;
- CODEMAP/deep-topology grounding, the Topological Context Anchor, Capability Connectome, Capability Genome Resolver, and Model Cognome;
- Coding, Agent, Human Agent, Liquid Planning, Civic Commons, Experience/Crucible, and ephemeral-organ execution surfaces;
- reversible context crushing, visible ST3GG egress, JSpace route state, empirical cost telemetry, and governed provider egress;
- C3 proposal-only procedure induction, replay/shadow/drift evidence, federation bundles, and human-reviewed policy promotion gates;
- the unified Showcase and deployment surfaces used to inspect architecture, Winnipeg pathways, observability, and guided approvals.

### Model Cognome and adaptive routing

Aura's public compatibility router keeps `LEGACY` as the default and rollback path. `SHADOW` creates and records a graph-bound plan without provider calls. `PAIRED_LIVE` permits one explicitly authorized comparison only after purpose, current graph digest, endpoint, verifier, expiry, call budget, and egress checks pass. Execution modes are `ZERO_MODEL`, `DIRECT`, `CASCADE`, and `PANEL`.

The adaptive layer may select and execute admitted workers; it may not automatically activate or promote policy, mutate source, commit, push, merge, or replace exact source/hash patch authority. See `docs/AURA_MODEL_COGNOME_ADAPTIVE_ROUTER.md`.
'''
    text = upsert_block(
        text,
        "<!-- PR92:CURRENT_ARCHITECTURE:START -->",
        "<!-- PR92:CURRENT_ARCHITECTURE:END -->",
        block,
        before="## The Core Loop",
    )
    table_anchor = "| **Ephemeral Organ Runtime** | All Arenas | Compiles temporary, capability-bounded applications from intent and dissolves them after use | Minimum explicit lease; no ambient authority |\n"
    model_row = "| **Model Cognome + Adaptive Router** | Operators and governed experiments | Resolves current graph-bound context, admits endpoint profiles, plans routes, and records comparable evidence | `LEGACY` default; `SHADOW` no-call; `PAIRED_LIVE` requires explicit authorization and egress approval |\n"
    if model_row not in text:
        text = replace_once(text, table_anchor, table_anchor + model_row, label="README model cognome table row")
    write(path, text)


def update_architecture() -> None:
    path = ".aura/ARCHITECTURE.md"
    text = read(path)
    old_header = "**Repository snapshot:** `b7180b11a518b4601043bd369b231bd977516d64`  \n**CODEMAP state:** 602 indexed files · 5,881 topology nodes · 12,168 topology edges  \n**Topology source:** `compiled_deep_topology`"
    new_header = f"**Architecture audit:** {AUDIT_WINDOW} (through draft PR #92)  \n**CODEMAP state:** {METRICS_TOKEN}  \n**Topology source:** `compiled_deep_topology`"
    if old_header in text:
        text = text.replace(old_header, new_header, 1)
    elif "**Architecture audit:**" not in text:
        raise RuntimeError("unrecognized ARCHITECTURE metadata header")

    evolution = f'''
## 1A. Implemented Evolution During the Architecture Audit

The {AUDIT_WINDOW} commit/PR audit shows that Aura evolved from a substrate-and-router core into a governed, self-describing application fabric. The authoritative implementation is organized by layer rather than by pull-request number:

| Layer | Implemented current surface | Authority boundary |
|---|---|---|
| Intent and route | Canonical six-slot LEXC, machine FST, guarded WFST challenges, C1 context capsules, and C2 live-route capsules | Grammar and route acceptance constrain work; they do not create permission |
| Grounding and self-model | CODEMAP, compiled topology, Topological Context Anchor, Capability Connectome, Capability Genome Resolver, Model Cognome | Current exact spans, hashes, graph digests, tests, and manifests outrank semantic inference |
| Arenas and temporary applications | Coding, Agent, Human Agent, Liquid Planning, Civic Commons, Experience/Crucible, ephemeral organs | Minimum leases, lifecycle enforcement, verifier gates, human/community authority, mandatory dissolution |
| Learning and procedure evidence | Experience V2, Crucible candidate review, C3 isolated trials, replay/shadow/drift evaluation | Candidates and trials are proposal-only; no automatic procedure or policy activation |
| Model execution | Legacy calibration router plus governed adaptive `SHADOW` and authorized `PAIRED_LIVE` routes | External models are workers; live calls require admission, authorization, current evidence, and approved egress |
| Compression and continuity | Reversible context crushing, visible ST3GG, JSpace, DREAM-lite, QDKT, MUSIC, MITOSIS | Compression and ranking remain advisory and recoverable |
| Observability and federation | Usage normalization, pricing snapshots, cost attribution, policy observations, signed/redacted federation bundles | Unknown cost stays unknown; remote evidence cannot silently become local policy |
| Human inspection and deployment | Native Cockpit, Coding Workbench, Human Agent Arena, unified Showcase, Winnipeg demo, Docker/Render/Hugging Face surfaces | Presentation is not authority; guided gates remain explicit |

This audit supersedes older summaries that described only the pre-Arena or pre-Cognome architecture. Historical reports remain useful as provenance, not as current system maps.
'''
    text = upsert_block(
        text,
        "<!-- PR92:ARCH_EVOLUTION:START -->",
        "<!-- PR92:ARCH_EVOLUTION:END -->",
        evolution,
        before="## 2. Truth and Authority Model",
    )

    text = text.replace(
        "Current healthy map:\n\n```text\nfiles: 602\nnodes: 5,881\nedges: 12,168\nsource: compiled_deep_topology\n```",
        f"Current healthy map:\n\n```text\n{METRICS_TOKEN}\nsource: compiled_deep_topology\n```",
        1,
    )

    model_block = r'''
### 10.1 Model Cognome and governed adaptive routing

The Model Cognome is the evidence and profile layer used to reason about model capabilities without treating model identity, benchmark reputation, or semantic fit as permission. Current routing composes:

```text
objective + explicit targets
  → Capability Genome Resolver
  → Capability Connectome path packet
  → Topological Context Anchor
  → exact source spans, hashes, callers, callees, tests, dependencies
  → graph-bound TaskContext
  → Model Cognome candidate profiles
  → hard admission and policy checks
  → LEGACY, SHADOW, or explicitly authorized PAIRED_LIVE execution
  → unified observations, verifier result, replay/shadow evidence
```

Public compatibility modes:

- `LEGACY`: existing calibration-ledger behavior; default and rollback path.
- `SHADOW`: plans and records a governed route; provider calls are forbidden.
- `PAIRED_LIVE`: performs one explicitly authorized comparison route.

Execution semantics:

- `ZERO_MODEL`: injected deterministic executor only.
- `DIRECT`: one admitted model followed by the named verifier.
- `CASCADE`: fallback only after call failure or verifier rejection.
- `PANEL`: at least two panel profiles plus one judge profile through AuraFusion.

`PAIRED_LIVE` authorization is content-addressed and bound to the named approver, verifier, purpose digest, current Capability Connectome graph digest, allowed routes/profiles, nonce, issue/expiry times, and maximum calls. The router revalidates current capability-path evidence and endpoint lifecycle before execution and fallback calls. Forced-model selection is an override request, never an admission bypass.

Primary modules:

- `aura_model_cognome.py`
- `aura_model_cognome_bridge.py`
- `aura_model_cognome_store_io.py`
- `aura_model_cognome_execution_auth.py`
- `aura_shadow_model_router.py`
- `aura_adaptive_model_router.py`
- `aura_adaptive_model_executor.py`
- `aura_adaptive_fusion.py`
- `aura_router_adaptive_compat.py`
- `aura_ai_router.py`
- `docs/AURA_MODEL_COGNOME_ADAPTIVE_ROUTER.md`

Explicit non-authorities:

```yaml
legacy_default: true
shadow_provider_calls: false
paired_live_requires_authorization: true
automatic_policy_activation: false
automatic_policy_promotion: false
automatic_source_mutation: false
automatic_commit: false
automatic_push: false
automatic_merge: false
patch_authority: exact_source_spans_and_hashes_only
```
'''
    text = upsert_block(
        text,
        "<!-- PR92:MODEL_COGNOME:START -->",
        "<!-- PR92:MODEL_COGNOME:END -->",
        model_block,
        before="Secrets must come from environment variables",
    )

    learning_block = r'''
### 11.5 Experience, Crucible, and C1/C2/C3 evidence gates

Aura's recent learning path is deliberately split so experience cannot silently become procedure or policy:

```text
observed execution
  → Experience V2 record
  → Crucible candidate/proposal
  → C1 graph-bound context capsule
  → C2 explicitly authorized live route capsule
  → C3 isolated trial and procedure evidence
  → replay and SHADOW comparison
  → drift/quality/cost/verifier evidence
  → human-reviewed promotion proposal
```

Key boundaries:

- experience storage is descriptive, not executable authority;
- Crucible outputs are candidates requiring review;
- C1 packets bind context to exact topology and evidence digests;
- C2 live routes require explicit authorization, approved egress, and verifier identity;
- C3 trials are isolated and may propose procedures but never auto-activate them;
- replay, shadow, drift, and federation evidence may support a promotion proposal only;
- policy activation remains separate from model execution and requires human review.

Primary surfaces include `aura_experience_v2.py`, Crucible modules, route-capsule schemas, governed trial/procedure modules, policy observation stores, and the Model Cognome evidence bridge.
'''
    text = upsert_block(
        text,
        "<!-- PR92:LEARNING_GATES:START -->",
        "<!-- PR92:LEARNING_GATES:END -->",
        learning_block,
        before="## 12. Plane 8 — Domain Deployments",
    )

    deployment_block = r'''
### 12.5 Unified Showcase and deployment surfaces

The unified Showcase is the human inspection layer for architecture, guided gates, observability, Winnipeg pathways, and demonstration projects. Recent deployment work adds Docker, Render, and Hugging Face-compatible launch surfaces around the same governed runtime rather than creating a second authority path.

Rules:

- demo fixtures and seeded Winnipeg data must be labelled as fixtures or snapshots;
- observability panels report evidence and measurement class, not guaranteed savings;
- a UI approval control must call the same underlying gate as CLI/API workflows;
- deployment configuration may expose a surface but may not weaken leases, egress policy, verifier requirements, or human/community authority;
- showcase rendering and narrative summaries remain non-authoritative projections.

Primary surfaces include `aura_showcase_server.py`, showcase UI assets, guided-gate APIs, deployment manifests, and the Winnipeg demo project.
'''
    text = upsert_block(
        text,
        "<!-- PR92:SHOWCASE_DEPLOYMENT:START -->",
        "<!-- PR92:SHOWCASE_DEPLOYMENT:END -->",
        deployment_block,
        before="## 13. Canonical Files and Generated Artifacts",
    )

    text = text.replace(
        "  + optional external workers\n  + exact tests/verifiers",
        "  + Model Cognome and governed adaptive routes\n  + optional external workers\n  + Experience/Crucible/C1-C3 proposal gates\n  + exact tests/verifiers",
        1,
    )
    write(path, text)


def update_user_guide() -> None:
    path = "USER_GUIDE.md"
    text = read(path)
    old_header = "**Repository snapshot:** `b7180b11a518b4601043bd369b231bd977516d64`  \n**Validated CODEMAP:** 602 files · 5,881 nodes · 12,168 edges · `compiled_deep_topology`"
    new_header = f"**Operator documentation audit:** {AUDIT_WINDOW} (through draft PR #92)  \n**Validated CODEMAP:** {METRICS_TOKEN} · `compiled_deep_topology`"
    if old_header in text:
        text = text.replace(old_header, new_header, 1)
    elif "**Operator documentation audit:**" not in text:
        raise RuntimeError("unrecognized USER_GUIDE metadata header")

    contents_anchor = "13. [Anishinaabemowin Tutor](#13-anishinaabemowin-tutor)\n"
    contents_row = "13A. [Model Cognome and Adaptive Routing](#13a-model-cognome-and-adaptive-routing)\n"
    if contents_row not in text:
        text = replace_once(text, contents_anchor, contents_anchor + contents_row, label="USER_GUIDE contents")

    interface_row = "| Model Cognome router | Governed legacy, no-call shadow planning, or explicitly authorized paired-live comparison | `python aura_router.py route --help` |\n"
    interface_anchor = "| Agent Arena MCP | MCP-compatible tool surface for external agents | `python3 -m aura_agent_arena_mcp` |\n"
    if interface_row not in text:
        text = replace_once(text, interface_anchor, interface_anchor + interface_row, label="USER_GUIDE interface row")

    adaptive = r'''
## 13A. Model Cognome and Adaptive Routing

Use the adaptive compatibility router only after topology health, capability resolution, and purpose are explicit.

### Public modes

| Mode | Provider calls | Required authority | Use |
|---|---:|---|---|
| `LEGACY` | Existing behavior | Existing router controls | Default and rollback path |
| `SHADOW` | No | Purpose digest and current graph-bound context | Compare plans and collect evidence without egress |
| `PAIRED_LIVE` | Yes | Reviewed authorization JSON, named verifier, current graph digest, approved purpose, and explicit data-egress approval | One bounded live comparison |

Execution plans may select `ZERO_MODEL`, `DIRECT`, `CASCADE`, or `PANEL`. A forced model must still be admitted and cannot replace a required high-risk panel.

### Legacy commands

```powershell
python aura_router.py route --task mesh_offload --mock
python aura_router.py fusion --task "Analyze this architecture" --mock
```

### Shadow planning

```powershell
python aura_router.py route `
  --task mesh_offload `
  --routing-mode shadow `
  --purpose-digest PURPOSE_DIGEST
```

`SHADOW` records the governed plan and evidence but must never call a provider.

### Authorized paired-live comparison

```powershell
python aura_router.py route `
  --task mesh_offload `
  --routing-mode paired_live `
  --purpose-digest PURPOSE_DIGEST `
  --authorization-file .\approved-experiment.json `
  --allow-data-egress
```

Before using `PAIRED_LIVE`, verify that the authorization names the human approver and verifier, matches the current purpose and Capability Connectome graph digest, permits the selected route/profile, has an unused nonce, has not expired, and has sufficient remaining calls.

### Non-goals and rollback

- `AURA_ADAPTIVE_ROUTER_MODE` defaults to `LEGACY`.
- `SHADOW` and `PAIRED_LIVE` do not promote policy.
- No adaptive route may automatically mutate source, commit, push, merge, or activate a learned procedure.
- Exact source spans and hashes remain patch authority.
- Return to `LEGACY` when evidence, authorization, topology freshness, endpoint lifecycle, verifier identity, or egress approval is uncertain.

See `docs/AURA_MODEL_COGNOME_ADAPTIVE_ROUTER.md` for the complete contract.
'''
    text = upsert_block(
        text,
        "<!-- PR92:USER_ADAPTIVE_ROUTER:START -->",
        "<!-- PR92:USER_ADAPTIVE_ROUTER:END -->",
        adaptive,
        before="## 14. Legacy REPL",
    )

    recent_ops = f'''
### Recent operator surfaces ({AUDIT_WINDOW})

The current checkout also includes guarded WFST/Experience/Crucible workflows, C1/C2/C3 evidence gates, the Model Cognome and policy-observation stores, unified cost telemetry, the Human Agent/Coding Workbench improvements, and the unified Showcase/deployment surfaces. Treat these as coordinated views over the same authority model—not independent bypasses.

For any unfamiliar surface, follow the standard sequence: topology health → digest → capability resolution → exact slices → subsystem guide → staged execution → verifier → human review.
'''
    text = upsert_block(
        text,
        "<!-- PR92:RECENT_OPERATOR_SURFACES:START -->",
        "<!-- PR92:RECENT_OPERATOR_SURFACES:END -->",
        recent_ops,
        before="## 20. Documentation Maintenance",
    )
    write(path, text)


def main() -> None:
    fix_dynamic_import()
    fix_symbol_relative_mesh_fixture()
    update_readme()
    update_architecture()
    update_user_guide()
    print("PR #92 closeout source, legacy fixtures, and architecture docs prepared")


if __name__ == "__main__":
    main()
