from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"documentation anchor missing: {label}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def insert_before(path: Path, marker: str, addition: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if addition.strip() in text:
        return
    if marker not in text:
        raise RuntimeError(f"documentation marker missing: {label}")
    path.write_text(
        text.replace(marker, addition + "\n\n" + marker, 1),
        encoding="utf-8",
    )


def main() -> None:
    readme = Path("README.md")
    replace_once(
        readme,
        "| **Coding Waboose** | Computes exact diff/symbol/dependency impact, runs deterministic scans, and lets coding agents steer run-specific evidence review | Review only; agent findings cannot self-confirm or mutate, commit, push, open, or merge |\n",
        "| **Coding Waboose** | Computes exact diff/symbol/dependency impact, runs deterministic scans, and lets coding agents steer run-specific evidence review | Review only; agent findings cannot self-confirm or mutate, commit, push, open, or merge |\n"
        "| **Runtime Refactor Harness** | Boots a repository-declared loopback application in an external virtual environment, drives a real probe/browser, captures exact artifacts, and binds failing and repaired receipts | Observation and verification only; no automatic patch, commit, push, PR, or merge |\n",
        "README system-map runtime row",
    )
    replace_once(
        readme,
        "The output contains a compact manifest, a sorted source-review file list, and a deterministic ZIP built from immutable `HEAD` Git blobs. Generated CODEMAP/topology/P9 artifacts, binaries, symlinks, sensitive/runtime paths, and oversized files are digest-only and never treated as ordinary source. Dirty trees fail closed by default. Long `run` operations emit a structured watchdog check-in every 10 minutes (`HEALTHY_CONTINUE`, `SLOW_BUT_PROGRESSING`, `STALLED_REASSESS`, or `UNKNOWN_REASSESS`) and pause safely at 20 minutes with completed-artifact inventory and an exact `--resume` receipt. The exact full Git archive remains available separately for forensic reconstruction. See [`docs/AURA_ARCHITECTURE_HARNESS.md`](docs/AURA_ARCHITECTURE_HARNESS.md).",
        "The output contains a compact manifest, a sorted source-review file list, and a deterministic ZIP built from immutable `HEAD` Git blobs. Generated CODEMAP/topology/P9 artifacts, binaries, symlinks, sensitive/runtime paths, and oversized files are digest-only and never treated as ordinary source. Dirty trees fail closed by default. Long `run` operations emit a structured watchdog check-in every 10 minutes (`HEALTHY_CONTINUE`, `SLOW_BUT_PROGRESSING`, `STALLED_REASSESS`, or `UNKNOWN_REASSESS`) and pause safely at 20 minutes with completed-artifact inventory and an exact `--resume` receipt. The exact full Git archive remains available separately for forensic reconstruction.\n\nThe same entrypoint now exposes repository-owned runtime profiles. A runtime profile creates an external virtual environment, starts one loopback-only application, runs a real probe and retained verification commands, hashes the evidence, terminates the process, and confirms that the source tree did not change:\n\n```bash\npython scripts/aura_architecture_harness.py \\\n  --repo-root . \\\n  runtime \\\n  --profile .aura/runtime_profiles/construction_demo.v1.json \\\n  --output-dir ../AuraOS-runtime-evidence/construction \\\n  --install-requirements\n```\n\nSee [`docs/AURA_ARCHITECTURE_HARNESS.md`](docs/AURA_ARCHITECTURE_HARNESS.md) and [`docs/AURA_RUNTIME_REFACTOR_HARNESS.md`](docs/AURA_RUNTIME_REFACTOR_HARNESS.md).",
        "README architecture harness runtime command",
    )
    replace_once(
        readme,
        "- [`docs/AURA_SCO_PHASE5_E9_E14_COMPLETION_PLAN.md`](docs/AURA_SCO_PHASE5_E9_E14_COMPLETION_PLAN.md)\n",
        "- [`docs/AURA_SCO_PHASE5_E9_E14_COMPLETION_PLAN.md`](docs/AURA_SCO_PHASE5_E9_E14_COMPLETION_PLAN.md)\n"
        "- [`docs/AURA_RUNTIME_REFACTOR_HARNESS.md`](docs/AURA_RUNTIME_REFACTOR_HARNESS.md) — isolated loopback runtime reproduction, browser evidence, before/after repair binding, and authority boundaries\n",
        "README documentation list",
    )
    replace_once(
        readme,
        "The recording client currently renders the deterministic Gaussian fallback plus graph and overlay context. Browser GLB/SPZ decoding and a real mesh draw pass are not implemented, so mesh/hybrid controls are disabled. Real asset packs may be compiled and contract-validated, but the browser refuses to substitute fallback geometry for real digests.",
        "The recording client renders the deterministic Gaussian fallback plus a bounds-derived wireframe mesh presentation and graph/overlay context. Mesh, Splats, and Hybrid are all live for the synthetic fallback. The wireframe is explicitly presentation-derived and does not claim browser GLB decoding; real asset packs may be compiled and contract-validated, but the browser still refuses to substitute fallback geometry for real digests.",
        "README Construction presentation modes",
    )
    replace_once(
        readme,
        "- **Aura Architecture Harness** — `scripts/aura_architecture_harness.py` reconstructs a reproducible environment, runs doctor checks, exports AI-safe source handoffs, supervises long runs with 10-minute check-ins and a 20-minute reassessment pause, and invokes the Connectome, Relational Index, Relationship Atlas, Emergent Properties, and Architect Fusion Loop without granting patch authority.\n",
        "- **Aura Architecture Harness** — `scripts/aura_architecture_harness.py` reconstructs a reproducible environment, runs doctor checks, exports AI-safe source handoffs, supervises long runs with 10-minute check-ins and a 20-minute reassessment pause, and invokes the Connectome, Relational Index, Relationship Atlas, Emergent Properties, and Architect Fusion Loop without granting patch authority.\n"
        "- **Runtime Refactor Harness** — the `runtime` command consumes a repository-owned profile, creates an external virtual environment, starts a loopback server, drives a real probe/browser, captures screenshots/logs/receipts, runs retained gates, dissolves the process, and binds a failing baseline to a later `REPAIRED_AND_VERIFIED` receipt. It observes and proves; it never patches or merges.\n",
        "README AI-agent Runtime Refactor Harness bullet",
    )
    replace_once(
        readme,
        "python scripts/aura_architecture_harness.py --repo-root . handoff --output-dir ../AuraOS-ai-handoff\n",
        "python scripts/aura_architecture_harness.py --repo-root . handoff --output-dir ../AuraOS-ai-handoff\n"
        "python scripts/aura_architecture_harness.py --repo-root . runtime --profile .aura/runtime_profiles/construction_demo.v1.json --output-dir ../AuraOS-runtime-evidence/construction\n",
        "README harness starter commands",
    )
    replace_once(
        readme,
        "Then use the focused guide in [`docs/AURA_ARCHITECTURE_HARNESS.md`](docs/AURA_ARCHITECTURE_HARNESS.md) and the Waboose contract in [`docs/AURA_CODING_WABOOSE.md`](docs/AURA_CODING_WABOOSE.md).",
        "Then use the focused guides in [`docs/AURA_ARCHITECTURE_HARNESS.md`](docs/AURA_ARCHITECTURE_HARNESS.md), [`docs/AURA_RUNTIME_REFACTOR_HARNESS.md`](docs/AURA_RUNTIME_REFACTOR_HARNESS.md), and the Waboose contract in [`docs/AURA_CODING_WABOOSE.md`](docs/AURA_CODING_WABOOSE.md).",
        "README harness guide links",
    )

    user_guide = Path("USER_GUIDE.md")
    replace_once(
        user_guide,
        "**Audit window:** architecture and work reviewed through July 22, 2026, including Relational Synthesis R2, Gate Phase 2, Spatial S0–S5 and Construction-only S6, Coding Relationship Compass C0–C9, typed Coding Waboose review learning, source-integrity/Crucible replay hardening, browser/interchange/Gaussian security, and the atomic Agent Bridge GitHub publication lane.",
        "**Audit window:** architecture and work reviewed through July 24, 2026, including Relational Synthesis R2, Gate Phase 2, Spatial S0–S6, Construction Arena G0–G8, Coding Relationship Compass C0–C9, typed Coding Waboose review learning, source-integrity/Crucible replay hardening, browser/interchange/Gaussian security, the Runtime Refactor Harness, and the atomic Agent Bridge GitHub publication lane.",
        "USER_GUIDE audit window",
    )
    replace_once(
        user_guide,
        "| **Coding Waboose** | Graph-guided diff review, deterministic scans, coding-agent focus, exact-source corroboration, and Forge repair handoff | `python3 aura_coding_waboose_cli.py run --request review_request.json` |\n",
        "| **Coding Waboose** | Graph-guided diff review, deterministic scans, coding-agent focus, exact-source corroboration, and Forge repair handoff | `python3 aura_coding_waboose_cli.py run --request review_request.json` |\n"
        "| **Runtime Refactor Harness** | Isolated loopback application boot, real browser/probe interaction, runtime artifacts, retained gates, and before/after repair binding | `python3 scripts/aura_architecture_harness.py --repo-root . runtime --profile <profile> --output-dir <external-dir>` |\n",
        "USER_GUIDE interface row",
    )
    insert_before(
        user_guide,
        "## 5. Orient yourself before changing code",
        """### Reproduce and verify a real runtime before declaring a refactor complete

Use a repository-owned Runtime Refactor profile when a feature includes a server, browser, renderer, process lifecycle, protocol, or multi-component integration:

```bash
python scripts/aura_architecture_harness.py \\
  --repo-root . \\
  runtime \\
  --profile .aura/runtime_profiles/construction_demo.v1.json \\
  --output-dir ../AuraOS-runtime-evidence/before \\
  --install-requirements
```

The harness must write evidence outside the checkout. It records exact Git identity, readiness, bounded stdout/stderr, probe receipts, required artifact hashes, retained verification, and process dissolution. It fails when the tree changes during observation.

After an authorized repair, rerun the exact profile and bind the failed baseline:

```bash
python scripts/aura_architecture_harness.py \\
  --repo-root . \\
  runtime \\
  --profile .aura/runtime_profiles/construction_demo.v1.json \\
  --output-dir ../AuraOS-runtime-evidence/after \\
  --baseline-receipt ../AuraOS-runtime-evidence/before/runtime_harness_receipt.json
```

A successful after-run may report `REPAIRED_AND_VERIFIED`. That proves the declared runtime profile for one exact tree; it is not patch, publication, production, or merge authority. Run Waboose and the subsystem's retained gates before the human decision.

For the Construction demo, the profile verifies the real local server, WebGL2 availability, canvas dimensions, storeys, orbit/zoom/explode/collapse, Mesh/Splats/Hybrid, the complete director tour, browser errors, screenshots, and zero-resource dissolution. See `docs/AURA_RUNTIME_REFACTOR_HARNESS.md`.""",
        "USER_GUIDE runtime refactor section",
    )

    architecture = Path(".aura/ARCHITECTURE.md")
    replace_once(
        architecture,
        "**Architecture audit:** reviewed through July 22, 2026 and the preceding merged development, including Relational Synthesis R2, Gate Phase 2, Spatial S0–S5 and Construction-only S6, Coding Relationship Compass C0–C9, typed Coding Waboose review learning, source-integrity and Crucible ancestry hardening, bounded browser/interchange/Gaussian representation support, and the atomic Agent Bridge GitHub publication lane merged in PRs #162–#170.",
        "**Architecture audit:** reviewed through July 24, 2026 and the preceding merged development, including Relational Synthesis R2, Gate Phase 2, Spatial S0–S6, Construction Arena G0–G8, Coding Relationship Compass C0–C9, typed Coding Waboose review learning, source-integrity and Crucible ancestry hardening, bounded browser/interchange/Gaussian representation support, the Runtime Refactor Harness, and the atomic Agent Bridge GitHub publication lane.",
        "ARCHITECTURE audit window",
    )
    insert_before(
        architecture,
        "## 4. Constitutional invariants",
        """## 3A. Runtime Refactor Harness boundary

The Runtime Refactor Harness is an observation-and-proof owner attached to the stable Architecture Harness entrypoint. It does not replace Coding Arena, Forge, Waboose, Council, Crucible, Observatory, or Agent Bridge.

```text
repository-owned runtime profile + exact Git identity
  → external virtual environment
  → loopback-only server
  → readiness evidence
  → bounded real probe/browser sequence
  → retained verification commands
  → artifact hashes + cleanup receipt
  → RUNTIME_FAILURE_REPRODUCED or RUNTIME_VERIFIED
  → separately authorized repair
  → exact-profile rerun bound to the failed baseline
  → REPAIRED_AND_VERIFIED
  → Waboose + human review
```

Primary owners are `scripts/aura_runtime_refactor_harness.py`, the `runtime` delegation in `scripts/aura_architecture_harness.py`, repository profiles under `.aura/runtime_profiles/`, subsystem probes under `tests/runtime/`, and `docs/AURA_RUNTIME_REFACTOR_HARNESS.md`.

The harness distinguishes source truth, presentation truth, performance evidence, integrity evidence, and authority. A valid performance overrun may emit a degraded receipt without destroying a verified presentation; malformed timing, stale identity, unsafe paths, failed integrity, missing artifacts, non-loopback serving, process timeout, source mutation, or failed retained verification remain hard blockers.

```yaml
runtime_profile_authority: false
runtime_evidence_authority: false
production_mutation: false
automatic_fix: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
human_review_required: true
```

Runtime evidence can localize defects and prove a candidate repair on one exact tree. It cannot grant patch, publication, Construction, renderer, professional, or merge authority.""",
        "ARCHITECTURE runtime boundary",
    )
    replace_once(
        architecture,
        "automatic_fix: false\n",
        "automatic_fix: false\nruntime_evidence_authority: false\nautomatic_runtime_patch: false\n",
        "ARCHITECTURE constitutional runtime invariants",
    )

    operator = Path("docs/AURA_CONSTRUCTION_DEMO_OPERATOR_GUIDE.md")
    replace_once(
        operator,
        "The browser recording client currently renders the deterministic Gaussian fallback plus graph and overlay context. Mesh contracts remain part of the architecture, but browser GLB decoding and a real mesh draw pass are not implemented; mesh and hybrid controls therefore remain disabled and fail closed.",
        "The browser recording client renders the deterministic Gaussian fallback, a deterministic bounds-derived wireframe mesh presentation, and graph/overlay context. Mesh, Splats, and Hybrid are available for the synthetic fallback. The wireframe remains presentation-derived and does not claim that browser GLB decoding exists.",
        "operator implemented modes",
    )
    replace_once(
        operator,
        "orbit · zoom · storey isolation · show all · explode · collapse\nsplats · floor plans · work status · trades · blockers · budgets",
        "orbit · zoom · storey isolation · show all · explode · collapse\nmesh · splats · hybrid · floor plans · work status · trades · blockers · budgets",
        "operator controls list",
    )
    replace_once(
        operator,
        "Mesh and hybrid buttons are visibly disabled until repository-owned browser GLB decoding and a real mesh draw pass exist.",
        "Mesh uses the admitted storey bounds to draw a deterministic wireframe fallback. Hybrid combines that wireframe with the verified Gaussian fallback. These modes are recording aids, not decoded BIM truth or physical authority.",
        "operator mode explanation",
    )
    replace_once(
        operator,
        "The browser intentionally refuses real-pack rendering until GLB/SPZ browser decoders and a real mesh draw pass are implemented. It never substitutes fabricated fallback geometry for admitted real digests.",
        "The browser intentionally refuses admitted real-pack rendering until repository-owned GLB/SPZ browser decoders exist. The bounds-derived wireframe applies only to the deterministic fallback and never substitutes fabricated fallback geometry for admitted real digests.",
        "operator real pack boundary",
    )
    insert_before(
        operator,
        "## Troubleshooting",
        """## Runtime Refactor Harness

Run the complete local server and browser path through Aura's Architecture Harness:

```bash
mkdir -p /tmp/aura-playwright
cd /tmp/aura-playwright
npm init -y
npm install --no-audit --no-fund playwright@1.55.0
npx playwright install chromium
cd -

NODE_PATH=/tmp/aura-playwright/node_modules \\
python scripts/aura_architecture_harness.py \\
  --repo-root . \\
  runtime \\
  --profile .aura/runtime_profiles/construction_demo.v1.json \\
  --output-dir /tmp/aura-construction-runtime \\
  --venv /tmp/aura-construction-venv \\
  --install-requirements
```

A healthy receipt reports `RUNTIME_VERIFIED`; a successful run bound to a failed baseline reports `REPAIRED_AND_VERIFIED`. Inspect `browser-evidence.json`, `initial.png`, `after-tour.png`, readiness and command receipts, server logs, artifact hashes, and the source-identity comparison.

The runtime incident that motivated this harness was a real first-frame WebGL warm-up exceeding the normal Gaussian frame budget. Performance evidence had been misclassified as an integrity failure, causing renderer dissolution. The current renderer preserves invalid timing as fatal while reporting a valid slow frame as measured degraded performance and continuing safely.""",
        "operator runtime harness section",
    )


if __name__ == "__main__":
    main()
