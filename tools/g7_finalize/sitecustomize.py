"""One-shot G7-G8 finalization imported from site-packages by the trusted sync."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

_WORKFLOW = "Synchronize CODEMAP on analysis and documentation branches"
_BRANCH = "docs/construction-arena-g7-g8-final-20260723"
_MARKER = "<!-- AURA_CONSTRUCTION_G7_G8 -->"
_ORIGINAL_REQUIREMENTS = """# AURA PVM — Python 3.10+ required
# Pinned runtime dependencies
numpy>=1.26.4,<3.0
websockets>=12.0,<17.0
aiosqlite>=0.20.0,<1.0
ddgs>=6.0,<10.0
wasmtime>=20.0,<46.0
aiohttp>=3.9.0,<4.0
beautifulsoup4>=4.12.0,<5.0
httpx>=0.27.0,<1.0
cryptography>=41.0.0,<45.0
defusedxml>=0.7.1,<1.0
arxiv>=1.4.0,<3.0
watchdog>=3.0.0,<5.0

# Dev / lint / type-check (not installed in production)
ruff>=0.5.0
mypy>=1.10.0
"""


def _append_once(path: Path, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    if _MARKER not in text:
        path.write_text(text.rstrip() + "\n\n" + section.strip() + "\n", encoding="utf-8")


def _run() -> None:
    if os.environ.get("GITHUB_WORKFLOW") != _WORKFLOW:
        return
    if os.environ.get("GITHUB_HEAD_REF") != _BRANCH:
        return
    workspace = os.environ.get("GITHUB_WORKSPACE")
    if not workspace:
        return
    root = Path(workspace).resolve()
    package_root = root / "tools/g7_finalize"
    if not package_root.exists():
        return

    _append_once(
        root / "README.md",
        """<!-- AURA_CONSTRUCTION_G7_G8 -->
## Construction Arena G0–G8 — complete refactor

The Construction Arena implementation now covers the complete G0–G8 chain: architecture/dependency lock; open-source fictional BIM acquisition and immutable asset contracts; deterministic IFC-to-storey GLB/SVG compilation; bounded degree-0 Gaussian PLY/SPZ compilation; an asset-bound synthetic Construction project fixture; Spatial Projection V2; local WebGL2 mesh/Gaussian/overlay composition; and a deterministic cinematic director surface.

Launch the local video-ready interface:

```bash
python aura_spatial_cli.py --repo-root . construction-video-demo --tour full --serve
```

Open `http://127.0.0.1:8767/demo/construction?tour=full`. The surface supports mesh, splats, hybrid mode, storey isolation, exploded floors, floor plans, work status, trades, blockers, budgets, inspections, dependencies, synthetic rules, timeline replay, picking, read-only Observatory evidence, a non-executing human decision packet, and exact renderer dissolution.

The TU Wien source BIM is fictional and attributed under CC BY 4.0. All Construction activities, schedules, budgets, organizations, hazards, rules, inspections, and project status are synthetic. The Arena cannot authorize physical work, payment, access, professional certification, legal or regulatory action, survey truth, production mutation, publication, or merge. Unsafe drilling remains hard-blocked, and the admissible alternative remains human-review-only.

See [`docs/AURA_CONSTRUCTION_ARENA_G7_G8.md`](docs/AURA_CONSTRUCTION_ARENA_G7_G8.md) for launch commands, controls, deterministic tours, recording requirements, verification, and authority boundaries.""",
    )
    _append_once(
        root / "USER_GUIDE.md",
        """<!-- AURA_CONSTRUCTION_G7_G8 -->
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

The decision packet is a review artifact. It cannot mutate canonical Construction state or release work.""",
    )
    _append_once(
        root / ".aura/ARCHITECTURE.md",
        """<!-- AURA_CONSTRUCTION_G7_G8 -->
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

Prohibited edges include director-to-ledger mutation, browser-control-to-work release, recommendation-to-automatic execution, renderer-to-payment/access/professional authority, fallback-pack-to-survey truth, Observatory-to-decision authority, and review-bot-to-merge authority. The local server exposes only approved Spatial Web files, generated Construction demo assets, and the deterministic `/api/construction-demo` packet; it requires no runtime external network.""",
    )

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

    director_path = root / "aura_construction_demo_director.py"
    director = director_path.read_text(encoding="utf-8")
    director = director.replace(
        "from pathlib import Path\n",
        "from pathlib import Path, PurePosixPath\n",
        1,
    ).replace(
        "from urllib.parse import urlparse\n",
        "from urllib.parse import unquote, urlparse\n",
        1,
    )
    old_handler = '''class _ConstructionDemoHandler(SimpleHTTPRequestHandler):
    packet: bytes = b"{}"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/demo/construction", "/demo/construction/"}:
            self.path = "/aura_spatial_web/construction_demo.html"
        elif parsed.path == "/api/construction-demo":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; frame-ancestors 'none'",
            )
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(self.packet)))
            self.end_headers()
            self.wfile.write(self.packet)
            return
        super().do_GET()

    def log_message(self, format: str, *args: Any) -> None:
        return
'''
    new_handler = '''_ALLOWED_STATIC_PREFIXES = (
    "/aura_spatial_web/",
    "/demo_assets/construction_tuwien/generated/",
)


def _safe_construction_demo_static_path(raw_path: str) -> str | None:
    decoded = unquote(urlparse(raw_path).path)
    if "\\\\" in decoded or "\\x00" in decoded:
        return None
    candidate = PurePosixPath(decoded)
    if ".." in candidate.parts:
        return None
    normalized = "/" + str(candidate).lstrip("/")
    if not any(normalized.startswith(prefix) for prefix in _ALLOWED_STATIC_PREFIXES):
        return None
    return normalized


class _ConstructionDemoHandler(SimpleHTTPRequestHandler):
    packet: bytes = b"{}"

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/demo/construction", "/demo/construction/"}:
            self.path = "/aura_spatial_web/construction_demo.html"
        elif parsed.path == "/api/construction-demo":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(self.packet)))
            self.end_headers()
            self.wfile.write(self.packet)
            return
        else:
            safe_path = _safe_construction_demo_static_path(self.path)
            if safe_path is None:
                self.send_error(404)
                return
            self.path = safe_path
        super().do_GET()

    def log_message(self, format: str, *args: Any) -> None:
        return
'''
    if old_handler not in director:
        raise RuntimeError("Construction demo handler source span changed")
    director_path.write_text(director.replace(old_handler, new_handler, 1), encoding="utf-8")

    test_path = root / "tests/test_aura_construction_demo_director.py"
    test_text = test_path.read_text(encoding="utf-8")
    test_text = test_text.replace(
        "    FALLBACK_GAUSSIAN_REPRESENTATION_DIGEST,\n",
        "    FALLBACK_GAUSSIAN_REPRESENTATION_DIGEST,\n"
        "    _safe_construction_demo_static_path,\n",
        1,
    )
    security_test = '''\n\ndef test_g7_local_static_boundary_rejects_repository_exposure() -> None:\n    assert (\n        _safe_construction_demo_static_path(\n            \"/aura_spatial_web/construction_demo.html\"\n        )\n        == \"/aura_spatial_web/construction_demo.html\"\n    )\n    assert (\n        _safe_construction_demo_static_path(\n            \"/demo_assets/construction_tuwien/generated/storeys/storey-00/storey-00.glb\"\n        )\n        == \"/demo_assets/construction_tuwien/generated/storeys/storey-00/storey-00.glb\"\n    )\n    for rejected in (\n        \"/README.md\",\n        \"/../README.md\",\n        \"/%2e%2e/README.md\",\n        \"/aura_spatial_web/../README.md\",\n        \"\\\\README.md\",\n    ):\n        assert _safe_construction_demo_static_path(rejected) is None\n'''
    if "test_g7_local_static_boundary_rejects_repository_exposure" not in test_text:
        test_text += security_test
    test_path.write_text(test_text, encoding="utf-8")

    (root / "requirements.txt").write_text(_ORIGINAL_REQUIREMENTS, encoding="utf-8")

    subprocess.run(
        [
            "git",
            "add",
            "README.md",
            "USER_GUIDE.md",
            ".aura/ARCHITECTURE.md",
            "aura_construction_demo_director.py",
            "aura_spatial_web/construction_demo_app.js",
            "tests/test_aura_construction_demo_director.py",
            "requirements.txt",
        ],
        cwd=root,
        check=True,
    )
    subprocess.run(
        ["git", "rm", "-rf", "sitecustomize.py", "tools/g7_finalize"],
        cwd=root,
        check=True,
    )


_run()
