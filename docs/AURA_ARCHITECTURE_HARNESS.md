# Aura Architecture Harness

The Aura Architecture Harness is the reproducible full-repository environment used to run Aura's own architectural intelligence against its current codebase.

It combines five read-only or proposal-only surfaces:

1. **Capability Connectome** — capability anatomy and execution traits.
2. **Relational Index** — exact repository participants and structural relationships.
3. **Relationship Atlas** — relationship meaning, missing roles, and prohibitions.
4. **Emergent Properties** — evidence-bound candidate combinations.
5. **Architect Fusion Loop** — bounded plan, grounding, Shadow review, and refactor-arena preparation.

The harness does **not** apply patches, authorize execution, or treat advisory similarity as source truth.

## Why the harness is saved in the repository

A chat container and its virtual environment are temporary. The scripts and export workflow in AuraOS are persistent, so a later coding session can reconstruct the same environment from the latest `main` branch.

## Recreate the complete repository in a network-isolated agent session

The permanent workflow `.github/workflows/aura-architecture-harness-export.yml` is intentionally push-only. It avoids opening a pull request and avoids triggering Aura's broad PR review fan-out.

1. Create a temporary branch from current `main` named like:

   ```text
   analysis/aura-harness-export/20260721-120000
   ```

2. On that branch, create or update:

   ```text
   .aura/HARNESS_EXPORT_REQUEST
   ```

   The file may contain the requested main SHA and timestamp.

3. Read the combined commit statuses for the request commit. The status context `aura-architecture-harness-export` links to the workflow run.

4. Read that run's artifacts and download `AuraOS-architecture-harness-<main-sha>`.

5. Unzip the outer Actions artifact, verify `AuraOS-full-repository.zip.sha256`, then extract `AuraOS-full-repository.zip`.

The export is pinned to the current `main` commit discovered by the workflow, and its manifest records both the source main SHA and the request commit SHA.

## Prepare the environment

For a normal clone with Git metadata:

```bash
python scripts/aura_architecture_harness.py \
  --repo-root . \
  prepare \
  --venv ../.AuraOS-architecture-harness-venv \
  --install-requirements
```

For an exported archive in an offline agent container:

```bash
python scripts/aura_architecture_harness.py \
  --repo-root ./AuraOS \
  prepare \
  --venv ./.AuraOS-architecture-harness-venv \
  --system-site-packages \
  --initialize-local-git \
  --source-sha <SOURCE_MAIN_SHA>
```

`--initialize-local-git` creates a synthetic local commit only when `.git` is absent. The local commit is explicitly marked as synthetic and stores the real GitHub source SHA in local Git config. It must never be represented as the original GitHub commit.

`--install-requirements` is optional. Do not use it in a network-isolated runtime unless the packages are already cached. The target architecture path is validated independently from unrelated optional Aura surfaces.

## Validate the environment

```bash
python scripts/aura_architecture_harness.py \
  --repo-root ./AuraOS \
  doctor \
  --venv ./.AuraOS-architecture-harness-venv
```

The doctor checks repository completeness, Git identity, CODEMAP presence, and imports for the Connectome, Relational Index, Atlas, Relational Synthesis, Emergent Properties, and Architect Loop.

## Run the architecture harness

```bash
python scripts/aura_architecture_harness.py \
  --repo-root ./AuraOS \
  run \
  --venv ./.AuraOS-architecture-harness-venv \
  --objective "make a new function that combines the properties of Connectome, Relational Synthesis, and Atlas to code better" \
  --combine-with Connectome "Relational Synthesis" Atlas \
  --atlas-profile MINIMAL
```

Outputs are written beside the repository under `AuraOS-architecture-harness-runs/<UTC timestamp>/` unless `--output-dir` is supplied. This avoids dirtying the source checkout.

For execution surfaces that impose a short command window, reuse one explicit output directory. If a run is interrupted after the Connectome, Relational Index, or Atlas completes, rerun the same command with `--resume`; the harness validates the request digest and continues from the retained artifacts instead of rebuilding them.

```bash
python scripts/aura_architecture_harness.py \
  --repo-root ./AuraOS \
  run \
  --venv ./.AuraOS-architecture-harness-venv \
  --output-dir ./aura-harness-run \
  --resume
```

## Atlas scale guard

The current repository can contain many thousands of Relational Index participants. A full pairwise Atlas scan grows quadratically:

```text
candidate_pairs = participant_count × (participant_count - 1) / 2
```

The harness therefore defaults to `MINIMAL`, which compiles exact/declarative relationships, missing motifs, and prohibitions without a repository-wide pairwise candidate scan. `STANDARD` or `DEEP` is refused when the estimated pair count exceeds the configured limit unless `--allow-expansive-atlas` is explicitly supplied.

This is a safety and efficiency guard, not a claim that deeper analysis is unnecessary. Deeper reasoning should be applied to an objective-bounded participant neighborhood.

## Generated artifacts

Each run records:

- `connectome.json`
- `relational_index.json`
- `relational_index_summary.json`
- `relationship_atlas.json`
- `emergent_properties.json`
- `architect_preparation.json`
- `harness_summary.json`

Canonical source ownership remains unchanged. Generated snapshots are navigation and analysis artifacts, never patch authority.

## Invariants

```yaml
full_repository_required: true
exact_source_sha_recorded: true
synthetic_local_git_identity_disclosed: true
connectome_is_advisory: true
relationship_atlas_is_compiled_view: true
relationship_atlas_is_patch_authority: false
emergent_properties_are_proposals: true
architect_run_is_prepare_only: true
production_mutation: false
human_review_required: true
patch_authority: exact_source_spans_and_hashes_only
```
