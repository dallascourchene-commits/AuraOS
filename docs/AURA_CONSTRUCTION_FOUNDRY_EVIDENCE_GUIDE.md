# Construction + Pascal Spatial Foundry Evidence Guide

## Purpose

This guide explains how to inspect, classify, preserve, and present the evidence emitted by the merged Construction + Pascal Spatial Foundry runtime.

The evidence package is a current-run proof input for human review. It is not Construction approval, survey truth, professional certification, payment authority, access authority, deployment authority, merge authority, or automatic learning authority.

## Evidence classes

| Evidence | What it establishes | What it does not authorize |
|---|---|---|
| Git head and tree | Exact reviewed source identity | Correctness by itself |
| Pascal lock, manifest, scene, and coordinate receipt | Exact local package, asset, scene, node, and transform chain | Survey or Construction truth |
| Browser screenshots | User-visible presentation from the current run | Hostile-browser pixel attestation |
| Browser evidence | Chapter order, relaunch, browser/runtime errors, request origin, and false authority | Deployment, merge, or physical work |
| Director receipts | Admitted chapter sequence, canonical effect result, evidence, and unchanged Construction digest | Skipped or unexecuted chapters |
| Incident replay packet | Bounded sanitized incident identity and required assets | Unrestricted recording or broader incident claims |
| Runtime Profile V2 proof | Positive, negative, preservation, fault, freshness, verifier, and source-cleanliness obligations | Production mutation, merge, or professional approval |
| Repair attempt and rollback receipt | Proposed route, isolated preview result, and exact technical restoration | Production hot swap or automatic repair deployment |
| Attempt Archive index | Durable references to retained successful and failed software-repair evidence | Automatic retry or promotion |
| U7 current reproof | P0, P1, current reproof, and human-disposition binding | Construction approval or automatic learning |
| Cleanup and server-termination receipts | Bounded resource release and terminal runtime lifecycle | Cleanup of unrelated processes |
| Coding Waboose receipt | Focused review evidence after V1 succeeds | Self-confirmation, source mutation, or merge |

## Run-directory rule

Use one new external directory per run. The final directory must not exist before the proof begins.

Recommended naming:

```text
AuraOS-construction-pascal-evidence/
  20260731T170000Z/
  20260731T181500Z-failure/
  20260731T193000Z-final/
```

Never mix artifacts from different attempts. Never copy a prior screenshot or receipt into a later run. Preserve failed runs separately rather than deleting them or relabeling them as successful.

## Required screenshot set

A complete successful browser run includes:

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

The seventeen screenshots represent the opening state, the visual transitions, three detail captures during candidate review, and the dissolved terminal state. The Director itself executes fifteen ordered chapters.

## Required domain/runtime JSON set

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

The Runtime Harness also emits receipts for readiness, probe execution, server output, server termination, verification commands, environment work, artifact inventory, and the overall runtime run. The V2 adapter emits its bilateral-Waboose receipt after V1 succeeds.

Chapter-specific JSON files may also be present. They contain the exact Director receipt and inspected page state for each chapter and are useful for diagnosis and edit inserts.

## Minimum successful verdict

A proof is not successful merely because screenshots exist. Review the structured evidence.

### `browser-evidence.json`

Confirm:

- `ok` is `true`;
- exactly fifteen chapter receipts were committed;
- the receipt order matches the Director manifest;
- the final state is dissolved;
- relaunch succeeded and returned a fresh non-dissolved session;
- all receipt authority values are false;
- `pageErrors` is empty;
- `requestFailures` is empty;
- `externalRequests` is empty;
- `sourceMutation` is `false`;
- `productionMutation` is `false`;
- `automaticMerge` is `false`;
- `physicalWorkAuthorized` is `false`;
- `professionalAuthority` is `false`;
- `humanReviewRequired` is `true`.

### Runtime Profile V2 proof

Confirm the proof is bound to:

- the intended Runtime Profile V2 identity and digest;
- the external canonical confirmation packet;
- intent, Semantic Ledger, confirmation, guardrail, revision, allowed-path, repository-head, and source-tree identities;
- the independent verifier ID, source path, and source digest;
- the retained V1 artifact inventory;
- positive, negative, preservation, and fault assertions;
- the current source tree before and after execution;
- human review and the false authority matrix.

### Runtime Harness receipt

Confirm:

- the repository identity before and after is unchanged;
- the source checkout remained clean;
- every required artifact was present and within its size limit;
- retained verification commands passed;
- the server reached readiness;
- the probe exited successfully;
- the server terminated and did not remain leased;
- no automatic patch, commit, push, pull request, merge, deployment, or production mutation occurred.

### Cleanup receipt

Confirm the presentation lifecycle is terminal and the retained fields show bounded cleanup of browser/presentation/capture/runtime resources owned by this run.

### Relaunch evidence

Confirm the post-dissolution Restart result is a fresh session with:

- fifteen chapter options;
- zero proven chapters;
- no dissolved status;
- a new current identity/confirmation boundary;
- no reuse of the consumed prior replay state.

## Fast inspection command

From the repository root, with the evidence directory outside the checkout:

```bash
python3 - /absolute/path/to/browser-evidence.json <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
value = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "ok": value.get("ok") is True,
    "chapter_count_15": value.get("chapterCount") == 15,
    "exact_order": value.get("exactOrder") is True,
    "final_dissolved": bool((value.get("finalState") or {}).get("dissolved")),
    "relaunch_succeeded": value.get("relaunchSucceeded") is True,
    "all_authority_false": value.get("allAuthorityFalse") is True,
    "no_page_errors": not value.get("pageErrors"),
    "no_request_failures": not value.get("requestFailures"),
    "no_external_requests": not value.get("externalRequests"),
    "source_not_mutated": value.get("sourceMutation") is False,
    "production_not_mutated": value.get("productionMutation") is False,
    "no_automatic_merge": value.get("automaticMerge") is False,
    "human_review_required": value.get("humanReviewRequired") is True,
}
for name, passed in checks.items():
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
raise SystemExit(0 if all(checks.values()) else 1)
PY
```

This is a convenience inspection only. The canonical verdict remains the retained runtime proof and receipts.

## Freshness and identity rules

- Begin from a clean exact checkout.
- Record `HEAD` and `HEAD^{tree}` before the run.
- Use the Runtime V2 profile and confirmation compiled for that exact source tree.
- Use a new external output directory.
- Treat a missing artifact as unproved.
- Treat a changed verifier digest as a hard failure.
- Treat a changed source tree as a hard failure.
- Treat a dirty checkout as a hard failure.
- Treat copied or reused evidence as stale.
- Preserve the original generated timestamps and receipt digests.
- Verify the checkout still has the same head/tree and an empty status after the run.

## Network rules

All application traffic during the proof must remain at the declared loopback origin.

The browser evidence records any request whose origin differs from the declared server origin. A request to another local port is still an origin mismatch and must fail the proof. A successful external redirect or subresource load cannot be ignored merely because it returned HTTP 200.

Dependency installation may use the network before the proof. The proof itself must not depend on a remote model, CDN, live API, or remote asset.

## Browser-policy and WebGL failures

An `ERR_BLOCKED_BY_ADMINISTRATOR` result means the execution environment prevented loopback browser navigation. It is neither a passing proof nor proof that Aura source failed.

A missing WebGL2 context is also an environment limitation unless source evidence identifies an application defect. Preserve:

- `runtime-failure.png` when emitted;
- `browser-evidence.json` with page errors;
- server output;
- probe receipt;
- server-termination receipt;
- exact head/tree identity.

Rerun in a permitted Chromium/WebGL environment against the same reviewed source identity.

## Failure classification

### Application or contract failure

Examples:

- chapter order differs from the manifest;
- required artifact is missing;
- P3 synchronization cannot be acknowledged;
- a digest or identity binding mismatches;
- an authority field becomes true;
- an unexpected request origin appears;
- the source tree changes;
- cleanup or termination is incomplete.

Disposition: retain the complete failed run. Route exact local implementation failures to Surgeon and structural/interface/sequence/authority failures to Council V3.

### Environment failure

Examples:

- Chromium is absent;
- browser navigation is administratively blocked;
- WebGL2 is unavailable due to host policy;
- required OS libraries are missing;
- ports are occupied by unrelated processes.

Disposition: retain the failure evidence, correct the environment, and rerun in a fresh directory. Do not modify evidence to manufacture a pass.

### Operator interruption

Examples:

- server stopped during Runtime V2;
- browser closed before dissolution;
- output directory deleted while the run was active;
- repeated control actions were issued during a pending synchronization gate.

Disposition: classify the attempt as interrupted, preserve available evidence, restart from a fresh session and output directory, and do not combine the interrupted and successful runs.

## Evidence archive checklist

For a published or stakeholder-facing demonstration, preserve:

```text
run-id/
  source-identity.txt
  operator-notes.md
  result.json
  evidence/                 # unmodified runtime output directory
  recording/
    raw-capture.*
    narration.*
    final-edit.*
  hashes.sha256
```

Suggested `source-identity.txt`:

```bash
{
  date -u +%Y-%m-%dT%H:%M:%SZ
  git rev-parse HEAD
  git rev-parse HEAD^{tree}
  git status --short
} > source-identity.txt
```

Suggested archive hashes:

```bash
find /path/to/run-id -type f -print0 \
  | sort -z \
  | xargs -0 sha256sum \
  > /path/to/run-id/hashes.sha256
```

Keep the runtime evidence directory read-only after review when practical.

## Privacy and publication review

Before publishing screenshots, video, logs, or JSON:

- remove or crop unrelated desktop content;
- do not expose API keys, credentials, environment variables, browser profiles, usernames, private paths, or unrelated repository information;
- verify the fixture contains no live project data;
- preserve receipt/digest fields needed for audit;
- clearly label any redacted public copy as a derivative presentation copy;
- retain the original unredacted local evidence under appropriate access controls;
- avoid narrating a redacted field as though its value were independently visible.

## Review disposition

A complete proof may yield `RUNTIME_VERIFIED` and `READY_FOR_HUMAN_REVIEW`.

Those dispositions mean the exact candidate satisfied the declared software/runtime obligations on the exact reviewed source tree. They do not grant:

- Construction truth mutation;
- engineering, survey, safety, or code approval;
- physical work;
- payment release;
- access or equipment operation;
- patch publication;
- deployment;
- merge;
- automatic learning promotion.

All such decisions remain separately governed human or professional actions.

## Related documents

- [`AURA_CONSTRUCTION_FOUNDRY_OPERATOR_GUIDE.md`](AURA_CONSTRUCTION_FOUNDRY_OPERATOR_GUIDE.md)
- [`AURA_CONSTRUCTION_FOUNDRY_VIDEO_SCRIPT.md`](AURA_CONSTRUCTION_FOUNDRY_VIDEO_SCRIPT.md)
- [`AURA_PASCAL_CONSTRUCTION_SPATIAL_FOUNDRY_MVP.md`](AURA_PASCAL_CONSTRUCTION_SPATIAL_FOUNDRY_MVP.md)
