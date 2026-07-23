"""One-shot finalization hook for the trusted CODEMAP synchronization workflow."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

_WORKFLOW = "Synchronize CODEMAP on analysis and documentation branches"
_BRANCH = "docs/construction-arena-g7-g8-final-20260723"
_MARKER = "<!-- AURA_CONSTRUCTION_G7_G8 -->"


def _run() -> None:
    if os.environ.get("GITHUB_WORKFLOW") != _WORKFLOW:
        return
    if os.environ.get("GITHUB_HEAD_REF") != _BRANCH:
        return

    root = Path.cwd()
    sections = {
        "README.md": """

<!-- AURA_CONSTRUCTION_G7_G8 -->
## Construction Arena G0–G8 — complete refactor

The Construction Arena implementation now covers the complete G0–G8 chain: architecture/dependency lock; open-source fictional BIM acquisition and immutable asset contracts; deterministic IFC-to-storey GLB/SVG compilation; bounded degree-0 Gaussian PLY/SPZ compilation; an asset-bound synthetic Construction project fixture; Spatial Projection V2; local WebGL2 mesh/Gaussian/overlay composition; and a deterministic cinematic director surface.

Launch the local video-ready interface:

```bash
python aura_spatial_cli.py --repo-root . construction-video-demo --tour full --serve
```

Open `http://127.0.0.1:8767/demo/construction?tour=full`. The surface supports mesh, splats, hybrid mode, storey isolation, exploded floors, floor plans, work status, trades, blockers, budgets, inspections, dependencies, synthetic rules, timeline replay, picking, read-only Observatory evidence, a non-executing human decision packet, and exact renderer dissolution.

The TU Wien source BIM is fictional and attributed under CC BY 4.0. All Construction activities, schedules, budgets, organizations, hazards, rules, inspections, and project status are synthetic. The Arena cannot authorize physical work, payment, access, professional certification, legal or regulatory action, survey truth, production mutation, publication, or merge. Unsafe drilling remains hard-blocked, and the admissible alternative remains human-review-only.

See [`docs/AURA_CONSTRUCTION_ARENA_G7_G8.md`](docs/AURA_CONSTRUCTION_ARENA_G7_G8.md) for launch commands, controls, deterministic tours, recording requirements, verification, and authority boundaries.
""",
        "USER_GUIDE.md": """

<!-- AURA_CONSTRUCTION_G7_G8 -->
## 27. Run the cinematic Construction Arena demo

Compile the deterministic browser packet without starting a server:

```bash
python aura_spatial_cli.py --repo-root . construction-video-demo --tour full --output /tmp/aura-construction-demo.packet.json
```

Launch the local interface:

```bash
python aura_spatial_cli.py --repo-root . construction-video-demo --tour full --serve
```

Open `http://127.0.0.1:8767/demo/construction?tour=full`.

Supported tours are `full`, `blocked-work`, `alternatives`, and `timeline`. The full tour contains 18 bounded presentation steps: attribution; complete hybrid building; orbit; exploded storeys; floor plans; timeline replay; blocked drilling; missing dispositive evidence; the hard-blocked unsafe option; safe alternate work; trade history; dependencies; synthetic-rule and inspection gates; schedule/budget comparison; a human-review recommendation; Observatory; a human decision packet; and dissolution.

Controls include orbit, zoom, storey isolation, show all, explode/collapse, mesh/splats/hybrid, floor plans, work status, trades, blockers, budgets, inspections, dependencies, synthetic rules, timeline scrub, picking, reset, play, pause, next step, and dissolve.

Supply `--asset-pack demo_assets/construction_tuwien/generated/asset-pack.manifest.json` when an admitted generated pack exists. Without it, the director uses a deterministic five-storey local fallback for recording and testing. The fallback is presentation-only and is not survey geometry.

Every packet keeps these boundaries explicit:

```yaml
physical_work_authorized: false
payment_released: false
access_controlled: false
professional_certification_claimed: false
legal_or_regulatory_authority_claimed: false
survey_authority_claimed: false
renderer_authority: false
automatic_execution: false
automatic_merge: false
human_review_required: true
```

The decision packet is a review artifact. It cannot mutate canonical Construction state or release work.
""",
        ".aura/ARCHITECTURE.md": """

<!-- AURA_CONSTRUCTION_G7_G8 -->
## Construction Arena G7–G8 presentation and proof layer

Canonical ownership remains unchanged:

- Construction truth: `ConstructionProjectState`;
- Construction filtering/runtime packet: `ConstructionArenaAdapter`;
- demo asset identity and provenance: `ConstructionDemoAssetPack`;
- synthetic project fixture: the G4 fixture/builder;
- spatial scene ownership: `project_construction_demo_to_scene` and the existing Spatial contracts;
- renderer/disposal ownership: `ConstructionSceneRenderer` with the existing mesh, overlay, Gaussian, WebGL2, and accessible-fallback owners.

`aura_construction_demo_director.py` is a presentation-sequence owner only. It composes the admitted asset pack, canonical G4 fixture/runtime packet, G5 scene, negotiated render plan, and bounded tour steps into a local browser packet:

```text
ConstructionDemoAssetPack
  → build_construction_demo_project_fixture
  → build_construction_demo_runtime_packet
  → project_construction_demo_to_scene
  → negotiate_spatial_render_plan
  → compile_construction_demo_packet
  → ConstructionSceneRenderer
  → deterministic presentation tour
  → read-only Observatory / human decision packet
  → exact renderer disposal
```

`aura_spatial_web/construction_demo.html`, `construction_demo.css`, and `construction_demo_app.js` provide the cinematic controls and guided tour without becoming truth or authority owners. Exploded transforms remain presentation-only and do not mutate source coordinates, storey elevation, Construction scope identity, schedule truth, or project state.

Prohibited edges include director-to-ledger mutation, browser-control-to-work release, recommendation-to-automatic execution, renderer-to-payment/access/professional authority, fallback-pack-to-survey truth, Observatory-to-decision authority, and review-bot-to-merge authority. The local server exposes static repository assets plus the deterministic `/api/construction-demo` packet and requires no runtime external network.
""",
    }

    for relative_path, section in sections.items():
        path = root / relative_path
        text = path.read_text(encoding="utf-8")
        if _MARKER not in text:
            path.write_text(text.rstrip() + section + "\n", encoding="utf-8")

    app_path = root / "aura_spatial_web/construction_demo_app.js"
    app = app_path.read_text(encoding="utf-8")
    app = app.replace(
        '  if (state.disposed && step.action !== "DISSOLVE") return;\n',
        '  if (state.disposed && step.action !== "DISSOLVE") return;\n'
        '  if ($("#evidence-dialog").open) $("#evidence-dialog").close();\n',
        1,
    )
    app = app.replace(
        '      document.querySelector(`input[data-layer="${step.target}"]`)?.toggleAttribute("checked", step.value !== "off");\n',
        '      const layerInput = document.querySelector(`input[data-layer="${step.target}"]`);\n'
        '      if (layerInput) layerInput.checked = step.value !== "off";\n',
        1,
    )
    app_path.write_text(app, encoding="utf-8")

    subprocess.run(
        [
            "git",
            "add",
            "README.md",
            "USER_GUIDE.md",
            ".aura/ARCHITECTURE.md",
            "aura_spatial_web/construction_demo_app.js",
        ],
        cwd=root,
        check=True,
    )
    subprocess.run(
        ["git", "rm", "-f", "sitecustomize.py"],
        cwd=root,
        check=True,
    )


_run()
