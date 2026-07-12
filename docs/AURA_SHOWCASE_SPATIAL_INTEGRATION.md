# Aura Showcase Spatial Integration

## Purpose

The unified Winnipeg showcase now embeds Aura's existing Coding Arena topology as a bounded spatial lens inside the Human Agent Coding Arena.

This is an integration layer, not a second topology implementation.

```text
starter task
  -> declared six-slot intent
  -> exact seed files and symbols
  -> existing CODEMAP / Coding Arena topology
  -> bounded micro-arena
  -> rotatable 3D canvas projection
  -> click-to-inspect exact node facts
  -> guarded Human Agent workflow
```

The visual graph helps a human orient, select, and ask better questions. It does not authorize a patch.

## Starter tasks

The demonstration exposes four presenter-safe tasks:

1. **Trace version and documentation drift**
   - compares version properties and repository snapshot claims;
   - connects the guides, architecture context, CODEMAP, and server constants.

2. **Reduce friction in Aura's memory architecture**
   - surfaces interfaces among QDKT, Context Crusher, ST3GG recall, paper memory, and route-capsule apertures;
   - exposes architecture and call boundaries, not private memory contents.

3. **Investigate the Civic map overlay**
   - traces the Civic fixture, policy-filtered projection, showcase server, browser map renderer, and focused tests;
   - is loaded automatically when the Civic issue handoff is opened.

4. **Audit emergent Arena capabilities**
   - connects the emergent-potential auditor, Human Agent concepts, Tensor Evidence, and Agent Arena Bridge;
   - separates implemented composition from hypotheses that still need proof.

Each task declares:

- `DIR`, `ASP`, `CLASS`, `SUBJ`, `VOICE`, and `STEM`;
- seed files and symbols;
- acceptance criteria;
- prohibited actions;
- a presenter cue.

## Bounded topology contract

The browser never receives Aura's full topology.

Server limits:

```yaml
selected_node_limit: 4
workspace_node_limit: 96
workspace_link_limit: 220
depth_limit: 2
```

The existing `select_micro_arena()` function remains the topology-selection implementation. The showcase adapter only:

- chooses grounded seed nodes for a declared task;
- invokes the existing micro-arena selector;
- caps the response;
- labels visual provenance;
- preserves non-authority metadata.

## API

```text
GET  /api/showcase/coding-tasks
GET  /api/showcase/topology/tasks/{task_id}?depth=1
POST /api/showcase/topology/select
```

Example selection request:

```json
{
  "node_ids": ["aura_showcase/civic.js::global_scope"],
  "depth": 2,
  "task_id": "civic_map_overlay"
}
```

Every response preserves:

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
production_mutation: false
automatic_commit: false
automatic_push: false
automatic_merge: false
```

## Spatial controls

- drag the canvas to rotate;
- use the mouse wheel to zoom;
- click a node to select and inspect it;
- choose **Depth 1** or **Depth 2** for bounded expansion;
- choose **Fit** to restore the default view.

The inspector exposes:

- file path;
- symbol;
- node type;
- line range;
- topology provenance;
- estimated tokens;
- bounded callers and dependencies;
- connected tests;
- candidate topology risks.

## Truth and provenance

Nodes are labelled as one of:

- `EXACT_TOPOLOGY`;
- `CODEMAP_PROJECTED`.

The UI states explicitly that visual nodes have no patch authority. Exact source spans, hashes, tests, verifier results, and human review remain authoritative.

## Launch

```bash
python aura_showcase_server.py --demo-project winnipeg_pathways
```

Open:

```text
http://127.0.0.1:8091
```

Or use the showcase container:

```bash
docker compose -f docker-compose.showcase.yml up --build
```

## Recording path

1. Run the Civic project until the map issue becomes available.
2. Click **Investigate with Human Agent Arena**.
3. The **Investigate the Civic map overlay** task loads into the 3D lens.
4. Rotate the graph and click a file or function node.
5. Show exact path, symbol, line range, tests, and candidate risks.
6. Expand to depth 2 only when useful.
7. Continue through the guarded WFST cards.
8. End at human review without committing, pushing, or merging.

The other starter tasks can be selected directly to demonstrate that the same bounded interface works for documentation, memory architecture, and emergent-capability audits.

## Validation

The dedicated showcase workflow validates:

- Python 3.10 and 3.12 compilation;
- fatal Ruff checks;
- task-registry and bounded-workspace contracts;
- API dispatch;
- browser asset presence;
- JavaScript syntax;
- live real-CODEMAP workspace loading;
- container startup;
- preservation of no-merge authority.
