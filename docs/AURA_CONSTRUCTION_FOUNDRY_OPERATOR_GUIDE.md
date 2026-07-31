# Construction + Pascal Spatial Foundry Operator Guide

## Purpose

This is the practical runbook for rehearsing, presenting, recording, and independently proving the merged Construction + Pascal Spatial Foundry MVP.

The demo has two operating modes:

1. **Manual presenter mode** — recommended for the narrated recording. You control each admitted Director chapter from the browser.
2. **Full bilateral proof mode** — automatically drives real Chromium, captures the complete evidence set, runs focused verification, checks repository cleanliness, terminates the server, and stops at human review.

Use the same clean reviewed checkout for both modes. The manual recording demonstrates the product. The full proof establishes the current-run evidence package. Do not try to narrate the unattended browser probe as though it were a manual presentation.

## What the demo proves—and does not prove

The demo proves one exact local source tree can:

- bind bilateral positive and negative intent;
- project canonical Construction state into synchronized Design, Floor Plan, As-built, and Compare views;
- use the pinned Pascal workbench as a disposable 2D/3D presentation organ;
- keep Construction truth, evidence, authority, runtime proof, archive, rollback, and learning owners in Aura;
- execute the deterministic fifteen-chapter Director sequence;
- capture one explicit software-presentation incident;
- retain replay, Runtime Profile V2, repair, rollback, U7 reproof, cleanup, and relaunch evidence;
- preserve false authority for physical work, professional approval, payment, access, deployment, merge, and learning promotion.

It does not issue a change order, engineering approval, survey drawing, payment certificate, work authorization, deployment approval, or merge authorization.

## Supported recording environment

Use Ubuntu or another Linux environment with:

- a clean checkout of the intended reviewed commit;
- Python 3.10 or newer;
- Node.js and npm;
- Chromium or Google Chrome with WebGL2 available;
- ports `8767` and `8768` free on loopback;
- a 1920×1080 desktop or recording canvas;
- the Python virtual environment, browser cache, and evidence directory outside the repository.

The demo is loopback-only after dependencies are installed. Close unrelated applications and browser tabs before recording, especially anything that could display private data or generate unrelated network requests.

## One-time Ubuntu setup

From the repository root:

```bash
python3 -m venv ../.AuraOS-construction-demo-venv
source ../.AuraOS-construction-demo-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Install the repository-declared Node dependency without creating a lock file.
npm install --no-package-lock

# Install a Playwright package matching the installed playwright-core version,
# then install Chromium and its Linux dependencies.
PW_VERSION="$(node -p "require('./node_modules/playwright-core/package.json').version")"
npm install --no-save --no-package-lock "playwright@${PW_VERSION}"
npx playwright install --with-deps chromium
```

If a compatible system Chromium or Chrome is already installed, the browser probe searches common Linux paths automatically. You may force a specific executable:

```bash
export AURA_CHROMIUM_EXECUTABLE=/usr/bin/google-chrome
# or
export AURA_CHROMIUM_EXECUTABLE=/usr/bin/chromium
```

Verify that dependency installation did not create tracked changes:

```bash
git status --short
```

The output must be empty before the full proof.

## Preflight before every rehearsal or recording

Run this from the repository root:

```bash
set -euo pipefail

git switch main
git pull --ff-only
git status --short
git rev-parse HEAD
git rev-parse HEAD^{tree}
python3 --version
node --version
npm --version

# Both ports must be free for the complete tour.
ss -ltnp | grep -E ':(8767|8768)\b' || true

# Confirm the generated navigation artifacts exist in the reviewed tree.
test -f .aura/CODEMAP.json
test -f .aura/CODEMAP.md
test -f topology_map.json
```

Do not continue if `git status --short` prints anything. Record the displayed commit and tree digest in the production notes for the video.

For a final recording, first perform one complete rehearsal. Confirm that all fifteen chapter options appear, P3 synchronization succeeds, Runtime Profile V2 completes, the session dissolves, and Restart creates a fresh session.

## Mode A — manual presenter mode

### Start the server

Activate the external virtual environment and launch the merged P4 server:

```bash
source ../.AuraOS-construction-demo-venv/bin/activate

python aura_construction_pascal_spatial_foundry_p4_server.py \
  --repo-root . \
  --host 127.0.0.1 \
  --port 8768
```

Expected terminal output:

```text
Aura Construction Pascal Spatial Foundry P4: http://127.0.0.1:8768
```

Open:

```text
http://127.0.0.1:8768/
```

In a second terminal, optionally verify readiness:

```bash
curl -fsS http://127.0.0.1:8768/api/construction/director/status \
  | python3 -m json.tool
```

The status should report the Director available, the P3 fallback available, offline deterministic operation, human review required, and false automatic/physical authority.

### Recommended recording layout

Use a browser-only capture at 1920×1080. Keep the browser zoom at a stable level that shows:

- the Construction Director controls and status;
- the central 2D/3D presentation;
- the selected evidence, candidate, and decision panels;
- the current receipt or proof surface when the chapter calls for it.

Record a short opening slate separately containing:

- `git rev-parse HEAD`;
- `git rev-parse HEAD^{tree}`;
- “Local loopback demo — no live Construction data”; and
- “Decision support only — no physical-work or professional authority.”

For narration, use **Next** rather than **Play**. This lets you pause at each state and prevents the presentation from advancing while you are explaining it. Play is useful for rehearsal and unattended validation, but it is not the recommended narrated-recording control.

### Controls

- **Next:** execute the next admitted chapter.
- **Play:** execute admitted chapters in order and stop on a blocked or failed synchronization.
- **Pause:** halt autoplay without changing committed proof state.
- **Previous / chapter selection:** presentation navigation only. These controls cannot execute an unproven consequential chapter.
- **Re-sync P3:** retry synchronization for the last committed presentation chapter without discarding its Director receipt.
- **Restart:** available only after dissolution. It creates a fresh exact identity, confirmation, and session.

When P3 synchronization is pending, Play, Next, and chapter jumping are intentionally blocked. Wait for synchronization or use Re-sync P3. Do not repeatedly click controls while the gate is pending.

## Manual recording sequence

The Director contains exactly fifteen consequentially ordered chapters. The recording package contains seventeen named screenshots because the initial frame is captured before chapter execution and three separate detail shots are taken during candidate review.

### Opening frame — bilateral intent

Before pressing Next:

- show the intent/guardrail presentation and Director status;
- explain that Aura owns truth, evidence, authority, verification, and governance;
- explain that Pascal is the pinned, disposable visual working body;
- state that the demonstration uses local fixture data and loopback-only services.

### 1. Frame the Construction objective

Press Next to enter **Design**.

Show the 3D building representation and explain that the presentation is bound to canonical Construction identity rather than becoming a new Construction truth store.

### 2. Open the exact floor plan

Press Next to enter **Floor Plan**.

Show the selected storey, Pascal node, dimensions, and deterministic coordinate binding.

### 3. Project the Aura-derived as-built state

Press Next to enter **As-built**.

Say clearly that this is derived coordination evidence—not survey truth or professional certification.

### 4. Compare design and as-built

Press Next to enter **Compare**.

Show the synchronized views and explain that the Aura and Pascal renderers remain technically separate while sharing exact bound selection state.

### 5. Review bounded Construction alternatives

Press Next to open the candidate review state. Pause here for four shots:

1. obligation/evidence inspector;
2. timeline, budget, and crews;
3. candidate roles (`HARD_BLOCKED`, `NEEDS_EVIDENCE`, `READY_FOR_HUMAN_REVIEW`);
4. digest-bound Construction decision-support packet.

State that “ready for human review” is not approval.

### 6. Aura, watch this

Press Next to begin one explicit bounded capture.

Explain that unrestricted background recording remains off. Only the authorized incident window is retained.

### 7. Mark the exact presentation fault

Press Next to mark the deterministic Pascal-selection synchronization fixture.

Describe it as a software presentation-interface fault. Do not imply that a physical Construction error occurred.

### 8. Dissolve capture and retain replay

Press Next to finalize capture.

Show that listeners, timers, and active buffers dissolve before the sanitized replay packet is retained.

### 9. Run exact Runtime Profile V2 replay

Press Next and allow the runtime proof to complete. This chapter can take substantially longer than the visual chapters because it launches the inner Construction Demo profile, runs a real probe, verifies retained evidence, and terminates its server.

For a polished video, leave the chapter running but cut or time-compress the waiting period in editing. Do not skip the chapter or replace its result with an unsupported narration claim.

If this chapter cannot complete because Chromium, WebGL2, loopback navigation, or another environment capability is blocked, stop the final recording and correct the environment. Preserve the failure evidence rather than presenting it as a pass.

### 10. Derive the repair route

Press Next.

Show that local exact-span failures route to Surgeon and structural/interface/sequence/authority failures route to Council V3. The route remains proposal-only.

### 11. Demonstrate exact rollback

Press Next.

Show the deliberately degraded isolated preview, the detected health failure, and restoration of the exact last-verified digest.

### 12. Demonstrate successful isolated preview

Press Next.

Show the healthy isolated candidate preview. State that a successful preview still cannot deploy itself.

### 13. Run current reproof and disposition

Press Next.

Show P0, P1, current reproof, and the human disposition. The expected disposition remains review-gated; do not narrate it as automatic learning promotion.

### 14. Return to Construction without changing truth

Press Next.

Return to the Construction comparison view and show that the canonical Construction state digest remains unchanged.

### 15. Dissolve the presentation session

Press Next.

Show terminal cleanup, zero active presentation resources, and the final cleanup receipt.

After the final chapter, optionally click **Restart** to demonstrate a fresh `0/15 chapters proven` session with a new identity and unconsumed confirmation. Restart is a relaunch demonstration, not a sixteenth Director chapter.

## Mode B — full bilateral proof mode

Run this mode before the final recording as a dress rehearsal and after the recording as the evidence package for the exact source tree.

The target output directory must not already exist. Never reuse or pre-create it.

```bash
set -euo pipefail
source ../.AuraOS-construction-demo-venv/bin/activate

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_PARENT="../AuraOS-construction-pascal-evidence"
EVIDENCE_DIR="${EVIDENCE_PARENT}/${RUN_ID}"
mkdir -p "${EVIDENCE_PARENT}"
test ! -e "${EVIDENCE_DIR}"

python scripts/aura_construction_pascal_spatial_foundry_pr5_runtime.py \
  --repo-root . \
  --venv ../.AuraOS-pr5-runtime-venv \
  --output-dir "${EVIDENCE_DIR}" \
  --install-requirements \
  | tee "${EVIDENCE_PARENT}/${RUN_ID}-result.json"
```

The wrapper:

1. requires `.aura/CODEMAP.md` and a clean exact source tree;
2. compiles a canonical bilateral confirmation outside the checkout;
3. delegates to the existing Runtime Profile V2 owner;
4. boots the P4 server on loopback;
5. drives the complete Director tour in headless Chromium at 1920×1080;
6. captures the current-run screenshot and JSON contracts;
7. runs the focused JavaScript and Python verification commands;
8. regenerates and verifies CODEMAP inside the proof flow;
9. runs bilateral Waboose after V1 succeeds;
10. proves source identity is unchanged and the server terminates;
11. returns a structured result requiring human review.

A successful process exits with code `0` and prints a JSON object whose `ok` field is `true`. A failed process exits with code `1` and prints a structured fail-closed result.

## Required proof artifacts

The output directory must include the seventeen screenshots:

```text
00-bilateral-intent.png
01-design-3d.png
02-floorplan-2d.png
03-as-built.png
04-compare.png
05-obligation-inspector.png
06-timeline-budget-crews.png
07-construction-candidates.png
08-construction-decision.png
09-capture-started.png
10-incident-marked.png
11-replay-proof.png
12-repair-route.png
13-preview-rollback.png
14-current-reproof.png
15-observatory.png
16-dissolved.png
```

It must also include:

```text
browser-evidence.json
construction-foundry-projection.json
incident-replay-packet.json
runtime-profile-v2-proof.json
repair-attempt.json
preview-rollback-receipt.json
u7-current-reproof.json
attempt-archive-index.json
cleanup-receipt.json
```

The Runtime Harness adds readiness, probe, server-output, server-termination, verification-command, and runtime-harness receipts. The V2 adapter adds the bilateral-Waboose receipt after V1 succeeds.

## Post-run verification

Keep the evidence directory outside the repository. Do not rename individual artifacts after the run.

Check the browser result:

```bash
python3 - "${EVIDENCE_DIR}/browser-evidence.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
value = json.loads(path.read_text(encoding="utf-8"))
for key in (
    "ok",
    "chapterCount",
    "exactOrder",
    "relaunchSucceeded",
    "allAuthorityFalse",
    "sourceMutation",
    "productionMutation",
    "automaticMerge",
    "humanReviewRequired",
):
    print(f"{key}: {value.get(key)!r}")
print(f"pageErrors: {len(value.get('pageErrors', []))}")
print(f"requestFailures: {len(value.get('requestFailures', []))}")
print(f"externalRequests: {len(value.get('externalRequests', []))}")
PY
```

Expected terminal conditions:

- `ok: True`;
- fifteen chapter receipts in exact manifest order;
- final state dissolved;
- relaunch succeeded;
- all authority values false;
- no page errors, failed requests, or external-origin requests;
- `sourceMutation`, `productionMutation`, and `automaticMerge` false;
- `humanReviewRequired` true;
- repository identity unchanged in the runtime-harness receipt;
- terminal server-termination and cleanup receipts.

Finally verify the checkout remains clean:

```bash
git status --short
git rev-parse HEAD
git rev-parse HEAD^{tree}
```

## Reset and cleanup

For manual mode:

1. finish the DISSOLVE chapter;
2. use Restart only when demonstrating relaunch;
3. stop the server with `Ctrl+C`;
4. confirm ports 8767 and 8768 are free;
5. confirm the repository remains clean.

For proof mode, the harness owns server termination. Do not manually delete a failed evidence directory. Preserve it under its run ID and use a different fresh directory for the next run.

## Troubleshooting

### Port 8767 or 8768 is already in use

```bash
ss -ltnp | grep -E ':(8767|8768)\b' || true
```

Stop the stale local server before the proof. The full profile requires its declared ports; do not silently change them during a proof run.

### Output directory already exists

Choose a new timestamped path. Existing directories are treated as retained or stale evidence and fail closed.

### `.aura/CODEMAP.md` is missing

On a normal reviewed checkout, restore the generated files from the commit:

```bash
git restore --source=HEAD -- .aura/CODEMAP.json .aura/CODEMAP.md topology_map.json
```

If source or architecture changed, regenerate and commit the maps through the trusted synchronization lane before attempting the proof. Do not generate uncommitted maps immediately before a clean-tree proof and then ignore the dirty checkout.

### Chromium executable is unavailable

Install the matching Playwright browser or set `AURA_CHROMIUM_EXECUTABLE` to a compatible local Chromium/Chrome path.

### `ERR_BLOCKED_BY_ADMINISTRATOR`

This is an environment-policy failure. It does not prove that the application passed or failed. Use an environment that permits browser navigation to loopback, then rerun against the same reviewed source identity.

### WebGL2 is unavailable

Use a Chromium build with WebGL enabled and ensure software rendering is available. The proof probe already requests SwiftShader-compatible flags, but the host or browser policy may still block WebGL2.

### P3 synchronization failed

Use **Re-sync P3** once the UI presents that control. If synchronization repeatedly fails, stop the run, preserve the current receipt/evidence, and investigate rather than forcing chapter progression.

### Runtime Profile V2 chapter appears to pause

The chapter runs a nested real runtime proof and may take much longer than ordinary presentation transitions. Watch the server terminal for active progress. Do not click Next repeatedly or terminate the process unless it is actually failed or beyond the declared timeout.

### The checkout becomes dirty

Do not continue the proof. Inspect `git status --short`. Use a dedicated clean worktree or clone for recording rather than hiding unrelated work with ad hoc changes.

## Related documents

- [`AURA_CONSTRUCTION_FOUNDRY_VIDEO_SCRIPT.md`](AURA_CONSTRUCTION_FOUNDRY_VIDEO_SCRIPT.md) — narrated shot list and edit plan.
- [`AURA_CONSTRUCTION_FOUNDRY_EVIDENCE_GUIDE.md`](AURA_CONSTRUCTION_FOUNDRY_EVIDENCE_GUIDE.md) — evidence interpretation and archival checklist.
- [`AURA_PASCAL_CONSTRUCTION_SPATIAL_FOUNDRY_MVP.md`](AURA_PASCAL_CONSTRUCTION_SPATIAL_FOUNDRY_MVP.md) — canonical PR1–PR5 integration narrative.
- [`AURA_CONSTRUCTION_PASCAL_SPATIAL_FOUNDRY_P4.md`](AURA_CONSTRUCTION_PASCAL_SPATIAL_FOUNDRY_P4.md) — Director and Trust Model A boundary.
