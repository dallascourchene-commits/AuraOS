# Construction + Pascal Spatial Foundry Operator Guide

## Prerequisites

Use a Linux checkout at the exact reviewed head. The source tree must be clean. Install Python requirements and Playwright/Chromium before the final proof. Keep the virtual environment and output directory outside the repository.

```bash
git status --short
git rev-parse HEAD
git rev-parse HEAD^{tree}
python -m pip install -r requirements.txt
npm install --no-save playwright
npx playwright install chromium
```

## Full bilateral PR5 proof

Use one fresh output directory:

```bash
python scripts/aura_construction_pascal_spatial_foundry_pr5_runtime.py \
  --repo-root . \
  --venv ../.AuraOS-pr5-runtime-venv \
  --output-dir ../AuraOS-pr5-runtime-evidence \
  --install-requirements
```

The command fails closed when the checkout is dirty, the exact source identity moves, the verifier hash differs, the output is stale, a required artifact is missing, the browser tour fails, Waboose fails, CODEMAP is stale, the server does not terminate, or an authority obligation is violated.

## Manual presentation launch

```bash
python aura_construction_pascal_spatial_foundry_p4_server.py \
  --repo-root . \
  --host 127.0.0.1 \
  --port 8768
```

Open `http://127.0.0.1:8768/`. The Director starts automatically after exact P3 projection and server-issued bilateral identity are available.

Controls:

- **Next:** execute the next admitted chapter.
- **Play:** execute admitted chapters in order and stop on any blocked or failed synchronization.
- **Pause:** halt autoplay without changing proven state.
- **Previous / chapter selection:** presentation navigation only; cannot execute an unproven chapter.
- **Re-sync P3:** retry a failed P3 presentation synchronization without losing the committed Director receipt.
- **Restart:** available only after dissolution; creates a fresh exact identity, confirmation, and session.

## Operator checks

Before recording, confirm:

- P4 status is available and P3 fallback is available;
- exactly fifteen chapter options exist;
- Design, Floor Plan, As-built, and Compare views render;
- no remote request occurs;
- all authority fields remain false;
- the deterministic incident is clearly labeled as a software presentation-interface fault;
- U7 disposition remains `NOT_REVIEWED`;
- the final state is `DISSOLVED`;
- Restart creates a fresh unconsumed session;
- the source checkout remains clean.

## Failure handling

Do not restart blindly after a failed consequential effect. Retain the browser evidence, server output, termination receipt, failing chapter receipt, and Attempt Archive reference. Route local exact-span failures to Surgeon and structural/interface/sequence/authority failures to Council V3.

An `ERR_BLOCKED_BY_ADMINISTRATOR` loopback-navigation error is an environment policy failure, not proof that the application failed or passed. Re-run in a permitted isolated browser environment and bind the new proof to the exact same reviewed source head.
