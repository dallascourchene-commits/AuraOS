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

## Export artifacts for an AI or network-isolated session

The permanent workflow `.github/workflows/aura-architecture-harness-export.yml` is intentionally push-only. It fetches the exact current `main` commit with read-only contents permission and publishes two separate artifacts:

1. **`AuraOS-ai-review-first-<main-sha>`** — the preferred AI input: `ai_handoff_manifest.json`, `ai_review_files.txt`, and `ai_source_review.zip`.
2. **`AuraOS-architecture-harness-<main-sha>`** — the exact full Git archive and provenance files for forensic reconstruction.

The lightweight artifact is a safe companion, not a substitute for the full snapshot. An AI should read the manifest first and should not open giant generated maps from the full archive as ordinary source.

To request an export, create a temporary branch from `main` named `analysis/aura-harness-export/<timestamp>`, create or update `.aura/HARNESS_EXPORT_REQUEST`, and read the `aura-architecture-harness-export` commit status. The status links to the workflow run. Both artifacts are pinned to the `source_main_sha` recorded by the workflow.

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

## Create an AI-safe handoff locally

Run from a clean Git checkout and write outside the repository:

```bash
python scripts/aura_architecture_harness.py \
  --repo-root . \
  handoff \
  --output-dir ../AuraOS-ai-handoff
```

Default output:

- `ai_handoff_manifest.json` — versioned compact provenance, omission metadata, regeneration instructions, warnings, and the unchanged proposal-only authority contract;
- `ai_review_files.txt` — deterministic newline-delimited list of reviewable tracked text files;
- `ai_source_review.zip` — deterministic source-review archive built from immutable `HEAD` Git blob bytes.

The default inline ceiling is 256 KiB and cannot be raised above the hard 1 MiB limit. `--no-archive` emits only the manifest/list. Dirty repositories fail closed; `--allow-dirty` must be explicit and never changes the archive source from `HEAD`. CRLF/LF or other working-tree differences are reported separately from Git blob OIDs and canonical blob SHA-256 values.

The command rejects output inside the repository, non-empty or symlink output directories, unsafe archive paths, Windows drive prefixes, `..` traversal, and tracked symlinks as archive members. It checks that `HEAD` and repository status remain unchanged during generation.

## Run the architecture harness

```bash
python scripts/aura_architecture_harness.py \
  --repo-root ./AuraOS \
  run \
  --venv ./.AuraOS-architecture-harness-venv \
  --objective "make a new function that combines the properties of Connectome, Relational Synthesis, and Atlas to code better" \
  --combine-with Connectome "Relational Synthesis" Atlas \
  --reference-file ../ARCHITECTURAL_REFERENCE_SPECIFICATION.txt \
  --atlas-profile MINIMAL
```

Outputs are written beside the repository under `AuraOS-architecture-harness-runs/<UTC timestamp>/` unless `--output-dir` is supplied. This avoids dirtying the source checkout.

`--reference-file` may be repeated for bounded external specifications or evidence. The harness records each file's resolved path, basename, byte size, and SHA-256 in the request and summary. It does not copy the content into AuraOS or treat the reference as source or patch authority. At most eight files of two megabytes each are accepted.

The Atlas compile uses an in-memory Relational Index and `persist=False`. Architect grounding uses the checked-in CODEMAP with refresh disabled. A successful clean run therefore leaves tracked repository content unchanged; any mutation fails the final clean-tree gate.

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

## Large/generated artifact policy

One policy in `scripts/aura_architecture_harness.py` assigns every tracked file one of three dispositions:

- `SOURCE_REVIEW` — bounded tracked UTF-8 source/configuration/documentation eligible for the lightweight archive;
- `DIGEST_ONLY` — binaries, oversized files, symlinks, sensitive/runtime paths, and other non-inline content;
- `REGENERATE_FROM_FINAL_TREE` — generated/reproducible content that is never ordinary patch authority.

The following are always `REGENERATE_FROM_FINAL_TREE`, even when small:

```text
.aura/CODEMAP.json
.aura/CODEMAP.md
topology_map.json
Aura_Memory/live_topology_ast.json
docs/aura_substrate_manifest.v1.json
docs/aura_substrate_manifest.files.*.json
docs/aura_substrate_manifest.phases.*.json
docs/aura_substrate_release_index.v1.json
```

Each digest-only row records path, canonical Git blob size/OID/raw SHA-256, reason, disposition, and bounded working-tree identity when available. No raw file body appears in the manifest. File hashes stream in bounded chunks; binary detection inspects only a small canonical blob prefix; subprocess output is retained only as a bounded tail with explicit omitted-byte and omitted-line counts.

Regenerate only after exact source and tests stabilize, in a canonical Linux/LF checkout:

```bash
python aura_codebase_navigator.py
python -m aura_codemap_verify --compare-json .aura/CODEMAP.json

python aura_substrate_release.py \
  --root . \
  --manifest-output-root <temporary-output-root> \
  --output <temporary-output-root>/docs/aura_substrate_release_index.v1.json
```

Until final regeneration, exclude generated paths from ordinary review diffs:

```bash
git diff --stat -- \
  . \
  ':(exclude).aura/CODEMAP.json' \
  ':(exclude).aura/CODEMAP.md' \
  ':(exclude)topology_map.json' \
  ':(exclude)Aura_Memory/live_topology_ast.json'
```

Normal architecture runs still write Connectome, Relational Index, Atlas, Emergent Properties, Architect preparation, request, and summary artifacts outside the checkout. These remain analysis/navigation outputs, never patch authority.

## Invariants

```yaml
full_repository_required_for_forensic_reconstruction: true
ai_first_review_companion_required: true
exact_source_sha_recorded: true
canonical_git_blob_identity_recorded: true
working_tree_sha256_distinguished_from_git_oid: true
synthetic_local_git_identity_disclosed: true
generated_artifacts_inline: false
generated_artifacts_regenerate_last: true
bounded_subprocess_diagnostics: true
connectome_is_advisory: true
relationship_atlas_is_compiled_view: true
relationship_atlas_is_patch_authority: false
emergent_properties_are_proposals: true
architect_run_is_prepare_only: true
production_mutation: false
human_review_required: true
patch_authority: exact_source_spans_and_hashes_only
```
