"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9e0-[Q-SYS:ICM_WORKSPACE]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Audit/Edit/Review Control Surface)
DEPENDENCIES: __future__, dataclasses, hashlib, json, os, pathlib, re, time, typing, aura_liquid_planning_arena, aura_qdkt, aura_dream_retrieval
FUNCTIONS: ICMStageDescriptor, ICMWorkspaceExport, ICMTransactionRef, export_arena_transaction, import_workspace, record_human_edit, record_dream_scores, build_icm_aura_md, build_icm_context_md
SYNOPSIS: ICM-compatible workspace export/import layer. Human-readable filesystem control surface for Arena runs. NOT a replacement for Liquid Planning Arena, Fusion Council, QDKT, DREAM-lite, sidecars, or verifier gates. Stores references, reports, and audit artifacts while exact truth remains in sidecars.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any

from aura_liquid_planning_arena import (
    ActionCapsule,
    BoundaryContract,
)
from aura_qdkt import UnifiedQDKT
from aura_dream_retrieval import DreamCandidate, DreamRetrievalExample, DreamReranker

ICM_VERSION = "AURA_ICM_WORKSPACE_V1"
ICM_LAYER_VERSION = "AURA_ICM_LAYER_V1"

# Layer mapping
# Layer 0 = Aura identity / domain axioms         -> AURA.md
# Layer 1 = Arena workspace routing                 -> CONTEXT.md
# Layer 2 = stage ActionCapsule + BoundaryContract  -> stages/NN_name/CONTEXT.md
# Layer 3 = stable references / schemas / policies  -> stages/NN_name/references/
# Layer 4 = per-run artifacts, outputs, deltas     -> stages/NN_name/output/


@dataclass
class ICMStageDescriptor:
    """Canonical descriptor for one stage inside an ICM workspace."""
    stage_number: int
    stage_name: str
    capsule: ActionCapsule | dict[str, Any]
    contracts: list[BoundaryContract | dict[str, Any]]
    inputs: list[str] = field(default_factory=list)
    process: str = ""
    outputs: list[str] = field(default_factory=list)
    allowed_actions: list[str] = field(default_factory=list)
    forbidden_actions: list[str] = field(default_factory=list)
    verifier_gates: list[str] = field(default_factory=list)
    human_review_status: str = "pending"
    references: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "icm_version": ICM_LAYER_VERSION,
            "stage_number": self.stage_number,
            "stage_name": self.stage_name,
            "inputs": list(self.inputs),
            "process": self.process,
            "outputs": list(self.outputs),
            "allowed_actions": list(self.allowed_actions),
            "forbidden_actions": list(self.forbidden_actions),
            "verifier_gates": list(self.verifier_gates),
            "human_review_status": self.human_review_status,
            "capsule": _capsule_to_dict(self.capsule),
            "contracts": [_contract_to_dict(c) for c in self.contracts],
            "references": dict(self.references),
            "artifacts": dict(self.artifacts),
        }


@dataclass
class ICMTransactionRef:
    """Lightweight reference to an exported ICM workspace."""
    workspace_path: str
    txn_id: str
    domain: str
    arena_id: str
    exported_at: float


@dataclass
class ICMWorkspaceExport:
    """In-memory representation of an ICM workspace export."""
    version: str
    workspace_id: str
    domain: str
    arena_id: str
    stages: list[ICMStageDescriptor]
    boundary_contracts: list[dict[str, Any]] = field(default_factory=list)
    verifier_report: dict[str, Any] = field(default_factory=dict)
    qdkt_events: list[dict[str, Any]] = field(default_factory=list)
    dream_scores: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "workspace_id": self.workspace_id,
            "domain": self.domain,
            "arena_id": self.arena_id,
            "stages": [s.to_dict() for s in self.stages],
            "boundary_contracts": list(self.boundary_contracts),
            "verifier_report": dict(self.verifier_report),
            "qdkt_events": list(self.qdkt_events),
            "dream_scores": list(self.dream_scores),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(text: str) -> str:
    """Stable filesystem slug from arbitrary text."""
    s = re.sub(r"[^\w\-]+", "_", str(text).strip().lower())
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:64]


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _hash_payload(payload: dict[str, Any], *, size: int = 16) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=size).hexdigest()


def _capsule_to_dict(capsule: ActionCapsule | dict[str, Any]) -> dict[str, Any]:
    if isinstance(capsule, ActionCapsule):
        return capsule.to_dict()
    return dict(capsule)


def _contract_to_dict(contract: BoundaryContract | dict[str, Any]) -> dict[str, Any]:
    if isinstance(contract, BoundaryContract):
        return contract.to_dict()
    return dict(contract)


def _ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v is not None]
    return [str(value)]


def _next_workspace_number(workspace_root: Path) -> int:
    """Return the next integer folder number under *workspace_root*."""
    if not workspace_root.exists():
        return 1
    nums = []
    for p in workspace_root.iterdir():
        if p.is_dir():
            m = re.match(r"^(\d{3,})_", p.name)
            if m:
                nums.append(int(m.group(1)))
    return max(nums, default=0) + 1



# ---------------------------------------------------------------------------
# Layer 0 — AURA.md
# ---------------------------------------------------------------------------

def build_icm_aura_md(*, domain: str, arena_id: str, arena_version: str, workspace_id: str) -> str:
    """Generate Layer 0 AURA.md — identity and domain axioms."""
    lines = [
        "# AURA Identity & Domain Axioms",
        "",
        f"- **ICM Version**: `{ICM_VERSION}`",
        f"- **Workspace ID**: `{workspace_id}`",
        f"- **Arena ID**: `{arena_id}`",
        f"- **Arena Version**: `{arena_version}`",
        f"- **Domain**: `{domain}`",
        f"- **Exported At**: {_now_iso()}",
        "",
        "## Axioms",
        "",
        "1. Exact truth remains in sidecars: prices, transactions, posts, timestamps, balances, source snapshots, code files, and tests.",
        "2. ICM folders are an audit / edit / review layer, not the source of deterministic truth.",
        "3. ICM does not replace live routing, multi-agent orchestration, or any Arena subsystem.",
        "4. Human edits to stage outputs are recorded as QDKT observations.",
        "5. Context candidates and verifier outcomes are emitted as DREAM-lite training rows.",
        "",
        "## Layer Mapping",
        "",
        "- **Layer 0** — Aura identity / domain axioms (`AURA.md`)",
        "- **Layer 1** — Arena workspace routing (`CONTEXT.md`)",
        "- **Layer 2** — Stage ActionCapsule + BoundaryContract (`stages/NN_name/CONTEXT.md`)",
        "- **Layer 3** — Stable references / schemas / policies / CODEMAP / sidecar schemas (`stages/NN_name/references/`)",
        "- **Layer 4** — Per-run artifacts, outputs, deltas, verifier results (`stages/NN_name/output/`)",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Layer 1 — CONTEXT.md
# ---------------------------------------------------------------------------

def build_icm_context_md(*, arena_id: str, domain: str, stages: list[ICMStageDescriptor]) -> str:
    """Generate Layer 1 CONTEXT.md — workspace routing overview."""
    lines = [
        "# Arena Workspace Routing",
        "",
        f"- **Arena ID**: `{arena_id}`",
        f"- **Domain**: `{domain}`",
        f"- **Stages**: {len(stages)}",
        "",
        "## Stage Routing",
        "",
        "| # | Stage | Inputs | Outputs | Verifier Gates | Review Status |",
        "|---|-------|--------|---------|----------------|---------------|",
    ]
    for st in stages:
        lines.append(
            f"| {st.stage_number:03d} | `{st.stage_name}` | {', '.join(st.inputs) or '-'} | "
            f"{', '.join(st.outputs) or '-'} | {', '.join(st.verifier_gates) or '-'} | {st.human_review_status} |"
        )
    lines += [
        "",
        "## Invariants",
        "",
        "1. Every stage declares explicit inputs, process, outputs, allowed actions, forbidden actions, verifier gates, and human review status.",
        "2. No stage may skip verifier gates or human review before production mutation.",
        "3. BoundaryContracts are materialized as JSONL but their deterministic truth lives in the Arena lease ledger.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stage CONTEXT.md (Layer 2)
# ---------------------------------------------------------------------------

def build_stage_context_md(stage: ICMStageDescriptor) -> str:
    """Generate Layer 2 stage CONTEXT.md — ActionCapsule + BoundaryContract details."""
    capsule = _capsule_to_dict(stage.capsule)
    lines = [
        f"# Stage {stage.stage_number:03d}: {stage.stage_name}",
        "",
        "## Inputs",
        "",
        *([f"- {item}" for item in stage.inputs] if stage.inputs else ["- None"]),
        "",
        "## Process",
        "",
        stage.process or "-",
        "",
        "## Outputs",
        "",
        *([f"- {item}" for item in stage.outputs] if stage.outputs else ["- None"]),
        "",
        "## Allowed Actions",
        "",
        *([f"- {item}" for item in stage.allowed_actions] if stage.allowed_actions else ["- None"]),
        "",
        "## Forbidden Actions",
        "",
        *([f"- {item}" for item in stage.forbidden_actions] if stage.forbidden_actions else ["- None"]),
        "",
        "## Verifier Gates",
        "",
        *([f"- {item}" for item in stage.verifier_gates] if stage.verifier_gates else ["- None"]),
        "",
        f"## Human Review Status: `{stage.human_review_status}`",
        "",
        "## ActionCapsule",
        "",
        "```json",
        json.dumps(capsule, indent=2, sort_keys=True, default=str),
        "```",
        "",
        "## BoundaryContracts",
        "",
    ]
    for c in stage.contracts:
        cd = _contract_to_dict(c)
        lines += [
            f"### Contract `{cd.get('contract_id', 'unknown')}`",
            "",
            "```json",
            json.dumps(cd, indent=2, sort_keys=True, default=str),
            "```",
            "",
        ]
    lines += [
        "## References",
        "",
        "Stable references, schemas, and policies are stored under `references/` (Layer 3).",
        "",
        "## Artifacts",
        "",
        "Per-run artifacts, deltas, and verifier results are stored under `output/` (Layer 4).",
        "",
    ]
    return "\n".join(lines)



# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_arena_transaction(
    txn: dict[str, Any],
    workspace_root: str | Path,
    *,
    domain: str = "",
    arena_id: str = "",
    arena_version: str = "",
    stages: list[ICMStageDescriptor] | None = None,
    verifier_report: dict[str, Any] | None = None,
    dream_candidates: list[DreamCandidate | dict[str, Any]] | None = None,
    dream_query: str = "",
    dream_target_type: str = "",
    qdkt: UnifiedQDKT | None = None,
    metadata: dict[str, Any] | None = None,
) -> ICMTransactionRef:
    """Export an Arena transaction into a numbered ICM workspace folder.

    Parameters
    ----------
    txn:
        Arena transaction payload (opaque dict). ICM stores a reference copy,
        not the deterministic source of truth.
    workspace_root:
        Base directory where numbered folders are created.
    stages:
        Stage descriptors. If None, a single default stage is synthesized from *txn*.
    verifier_report:
        Verifier outcomes per stage or globally.
    dream_candidates:
        Candidates for DREAM-lite scoring. If provided, a DREAM-lite rerank is run
        and results are written to ``dream_scores.jsonl``.
    qdkt:
        Optional ``UnifiedQDKT`` instance for recording export events.

    Returns
    -------
    ICMTransactionRef pointing to the created workspace path.
    """
    root = Path(workspace_root)
    root.mkdir(parents=True, exist_ok=True)

    num = _next_workspace_number(root)
    txn_id = str(txn.get("txn_id") or _hash_payload({"txn": txn, "ts": time.time()}, size=8))
    slug = _slug(str(txn.get("objective") or txn.get("task_id") or txn.get("capsule_id") or "arena_run"))
    folder_name = f"{num:03d}_{slug}"
    ws = root / folder_name
    ws.mkdir(parents=True, exist_ok=True)

    workspace_id = f"icm-{arena_id or 'unknown'}-{txn_id}"

    # Layer 0
    (ws / "AURA.md").write_text(
        build_icm_aura_md(
            domain=domain or str(txn.get("domain") or "generic"),
            arena_id=arena_id or str(txn.get("arena_id") or "unknown"),
            arena_version=arena_version or str(txn.get("arena_version") or "unknown"),
            workspace_id=workspace_id,
        ),
        encoding="utf-8",
    )

    resolved_stages: list[ICMStageDescriptor] = list(stages or [])
    if not resolved_stages:
        # Synthesize a single stage from txn if none provided
        capsule = txn.get("capsule") or {}
        contracts = txn.get("contracts") or []
        resolved_stages.append(
            ICMStageDescriptor(
                stage_number=1,
                stage_name="synthesized",
                capsule=capsule,
                contracts=contracts,
                inputs=_ensure_list(txn.get("inputs")),
                process=str(txn.get("process") or ""),
                outputs=_ensure_list(txn.get("outputs")),
                allowed_actions=_ensure_list(
                    capsule.get("allowed_actions") if isinstance(capsule, dict) else []
                ),
                forbidden_actions=_ensure_list(
                    capsule.get("forbidden_actions") if isinstance(capsule, dict) else []
                ),
                verifier_gates=_ensure_list(txn.get("verifier_gates")),
                human_review_status=str(txn.get("human_review_status") or "pending"),
            )
        )

    # Layer 1
    (ws / "CONTEXT.md").write_text(
        build_icm_context_md(
            arena_id=arena_id or str(txn.get("arena_id") or "unknown"),
            domain=domain or str(txn.get("domain") or "generic"),
            stages=resolved_stages,
        ),
        encoding="utf-8",
    )



    # Layers 2–4 per stage
    all_contracts: list[dict[str, Any]] = []
    for st in resolved_stages:
        stage_dir = ws / "stages" / f"{st.stage_number:02d}_{_slug(st.stage_name)}"
        stage_dir.mkdir(parents=True, exist_ok=True)
        (stage_dir / "references").mkdir(exist_ok=True)
        (stage_dir / "output").mkdir(exist_ok=True)

        # Layer 2
        (stage_dir / "CONTEXT.md").write_text(
            build_stage_context_md(st), encoding="utf-8"
        )

        # Layer 3 references
        if st.references:
            for ref_name, ref_payload in st.references.items():
                ref_path = stage_dir / "references" / f"{_slug(ref_name)}.json"
                ref_path.write_text(
                    json.dumps(ref_payload, indent=2, sort_keys=True, default=str),
                    encoding="utf-8",
                )

        # Layer 4 artifacts
        if st.artifacts:
            for art_name, art_payload in st.artifacts.items():
                art_path = stage_dir / "output" / f"{_slug(art_name)}.json"
                art_path.write_text(
                    json.dumps(art_payload, indent=2, sort_keys=True, default=str),
                    encoding="utf-8",
                )

        for c in st.contracts:
            all_contracts.append(_contract_to_dict(c))

    # boundary_contracts.jsonl
    bc_path = ws / "boundary_contracts.jsonl"
    with bc_path.open("w", encoding="utf-8") as fh:
        for c in all_contracts:
            fh.write(json.dumps(c, sort_keys=True, default=str) + "\n")



    # verifier_report.json
    vr = dict(verifier_report or {})
    if not vr and txn.get("verifier_report"):
        vr = dict(txn["verifier_report"])
    (ws / "verifier_report.json").write_text(
        json.dumps(vr, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )

    # QDKT events
    qdkt_events: list[dict[str, Any]] = []
    export_event = {
        "event_id": f"icm-export-{workspace_id}",
        "event_type": "icm_workspace_export",
        "concept": f"icm:{workspace_id}",
        "rationale": f"Exported Arena transaction to ICM workspace {folder_name}",
        "confidence": 0.95,
        "ts": time.time(),
    }
    qdkt_events.append(export_event)

    if qdkt is not None:
        try:
            qdkt.observe(
                "icm_workspace_export",
                {
                    "workspace_id": workspace_id,
                    "folder": str(ws),
                    "txn_id": txn_id,
                },
                rationale=export_event["rationale"],
                concept=export_event["concept"],
                confidence=export_event["confidence"],
            )
        except Exception:
            pass

    qdkt_path = ws / "qdkt_events.jsonl"
    with qdkt_path.open("w", encoding="utf-8") as fh:
        for e in qdkt_events:
            fh.write(json.dumps(e, sort_keys=True, default=str) + "\n")

    # DREAM-lite scores
    dream_scores: list[dict[str, Any]] = []
    if dream_candidates:
        normalized: list[DreamCandidate] = []
        for dc in dream_candidates:
            if isinstance(dc, DreamCandidate):
                normalized.append(dc)
            else:
                normalized.append(DreamCandidate.from_any(dc))
        example = DreamRetrievalExample(
            query=dream_query or str(txn.get("objective") or ""),
            target_type=dream_target_type or "arena_context",
            candidates=normalized,
            arena_domain=domain or str(txn.get("domain") or "generic"),
        )
        reranker = DreamReranker(ledger=None)
        result = reranker.rerank(example, record=False)
        dream_scores = list(result.get("scores", []))

    dream_path = ws / "dream_scores.jsonl"
    with dream_path.open("w", encoding="utf-8") as fh:
        for row in dream_scores:
            fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")

    # Metadata snapshot
    meta = {
        "icm_version": ICM_VERSION,
        "workspace_id": workspace_id,
        "folder_name": folder_name,
        "txn_id": txn_id,
        "exported_at": _now_iso(),
        "domain": domain or str(txn.get("domain") or "generic"),
        "arena_id": arena_id or str(txn.get("arena_id") or "unknown"),
        "stage_count": len(resolved_stages),
        **(dict(metadata or {})),
    }
    (ws / "metadata.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )

    return ICMTransactionRef(
        workspace_path=str(ws),
        txn_id=txn_id,
        domain=meta["domain"],
        arena_id=meta["arena_id"],
        exported_at=time.time(),
    )



# ---------------------------------------------------------------------------
# Human edit → QDKT observation
# ---------------------------------------------------------------------------

def record_human_edit(
    workspace_path: str | Path,
    stage_name: str,
    *,
    old_text: str,
    new_text: str,
    editor_id: str = "human",
    rationale: str = "",
    qdkt: UnifiedQDKT | None = None,
) -> dict[str, Any]:
    """Record a human edit to a stage output.

    Writes a diff into the stage ``output/`` directory and records a QDKT
    observation via ``UnifiedQDKT.observe(...)`` if *qdkt* is provided.
    """
    ws = Path(workspace_path)
    stage_dirs = list((ws / "stages").glob(f"??_{_slug(stage_name)}"))
    if not stage_dirs:
        raise FileNotFoundError(f"Stage '{stage_name}' not found in {ws / 'stages'}")
    stage_dir = stage_dirs[0]
    output_dir = stage_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    edit_filename = f"human_edit_{editor_id}_{ts}.md"
    edit_path = output_dir / edit_filename

    diff_lines = [
        f"# Human Edit — {stage_name}",
        "",
        f"- **Editor**: `{editor_id}`",
        f"- **Timestamp**: {_now_iso()}",
        f"- **Rationale**: {rationale or 'None provided'}",
        "",
        "## Before",
        "",
        "```text",
        old_text,
        "```",
        "",
        "## After",
        "",
        "```text",
        new_text,
        "```",
        "",
    ]
    edit_path.write_text("\n".join(diff_lines), encoding="utf-8")

    event = {
        "event_id": f"icm-human-edit-{ts}-{editor_id}",
        "event_type": "human_edit",
        "concept": f"icm:{ws.name}:{stage_name}",
        "rationale": rationale or f"Human edit on stage {stage_name}",
        "confidence": 0.9,
        "ts": time.time(),
        "metadata": {
            "workspace_path": str(ws),
            "stage_name": stage_name,
            "editor_id": editor_id,
            "edit_file": str(edit_path.relative_to(ws)),
        },
    }

    if qdkt is not None:
        try:
            qdkt.observe(
                "human_edit",
                {
                    "workspace_path": str(ws),
                    "stage_name": stage_name,
                    "editor_id": editor_id,
                    "edit_file": str(edit_path.relative_to(ws)),
                },
                rationale=event["rationale"],
                concept=event["concept"],
                confidence=event["confidence"],
            )
        except Exception:
            pass

    # Append to qdkt_events.jsonl
    qdkt_path = ws / "qdkt_events.jsonl"
    with qdkt_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True, default=str) + "\n")

    return event


# ---------------------------------------------------------------------------
# DREAM-lite score append
# ---------------------------------------------------------------------------

def record_dream_scores(
    workspace_path: str | Path,
    scores: list[dict[str, Any]],
) -> None:
    """Append DREAM-lite training rows to ``dream_scores.jsonl``."""
    ws = Path(workspace_path)
    dream_path = ws / "dream_scores.jsonl"
    with dream_path.open("a", encoding="utf-8") as fh:
        for row in scores:
            fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")



# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def import_workspace(workspace_path: str | Path) -> ICMWorkspaceExport:
    """Import an ICM workspace from the filesystem.

    Reads the file tree back into structured dicts for validation or replay.
    Exact truth remains in sidecars; this is an audit/review reconstruction.
    """
    ws = Path(workspace_path)
    if not ws.is_dir():
        raise NotADirectoryError(f"Not a directory: {ws}")

    meta_path = ws / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    # Stages
    stages: list[ICMStageDescriptor] = []
    stages_dir = ws / "stages"
    if stages_dir.is_dir():
        for stage_dir in sorted(stages_dir.iterdir()):
            if not stage_dir.is_dir():
                continue
            m = re.match(r"^(\d{2})_(.+)$", stage_dir.name)
            if not m:
                continue
            stage_number = int(m.group(1))
            stage_name = m.group(2)

            ctx_path = stage_dir / "CONTEXT.md"
            ctx_text = ctx_path.read_text(encoding="utf-8") if ctx_path.exists() else ""

            # Pull references
            refs: dict[str, Any] = {}
            ref_dir = stage_dir / "references"
            if ref_dir.is_dir():
                for rp in sorted(ref_dir.glob("*.json")):
                    refs[rp.stem] = json.loads(rp.read_text(encoding="utf-8"))

            # Pull artifacts
            arts: dict[str, Any] = {}
            out_dir = stage_dir / "output"
            if out_dir.is_dir():
                for ap in sorted(out_dir.glob("*.json")):
                    arts[ap.stem] = json.loads(ap.read_text(encoding="utf-8"))

            # Extract bullet lists from markdown sections
            def _bullets_after(header: str) -> list[str]:
                in_section = False
                items: list[str] = []
                for line in ctx_text.splitlines():
                    if line.strip().startswith(f"## {header}"):
                        in_section = True
                        continue
                    if in_section:
                        if line.strip().startswith("## "):
                            break
                        if line.strip().startswith("- "):
                            items.append(line.strip()[2:].strip())
                return items

            def _extract_section(title: str) -> str:
                pat = re.compile(rf"##\s*{re.escape(title)}\s*:?\s*(.*?)(?=\n##\s|\Z)", re.S)
                mat = pat.search(ctx_text)
                return (mat.group(1).strip() if mat else "").replace("- ", "").replace("\n", ", ")

            # Try to extract JSON capsule and contracts from markdown code blocks
            capsule: dict[str, Any] = {}
            contracts: list[dict[str, Any]] = []
            json_blocks = re.findall(r"```json\s*\n(.*?)\n```", ctx_text, re.S)
            if json_blocks:
                try:
                    capsule = json.loads(json_blocks[0])
                except json.JSONDecodeError:
                    pass
                for block in json_blocks[1:]:
                    try:
                        contracts.append(json.loads(block))
                    except json.JSONDecodeError:
                        pass

            stages.append(
                ICMStageDescriptor(
                    stage_number=stage_number,
                    stage_name=stage_name,
                    capsule=capsule,
                    contracts=contracts,
                    inputs=_bullets_after("Inputs"),
                    process=_extract_section("Process"),
                    outputs=_bullets_after("Outputs"),
                    allowed_actions=_bullets_after("Allowed Actions"),
                    forbidden_actions=_bullets_after("Forbidden Actions"),
                    verifier_gates=_bullets_after("Verifier Gates"),
                    human_review_status=_extract_section("Human Review Status").strip("`"),
                    references=refs,
                    artifacts=arts,
                )
            )

    stages.sort(key=lambda s: s.stage_number)

    # boundary_contracts.jsonl
    bc_path = ws / "boundary_contracts.jsonl"
    boundary_contracts: list[dict[str, Any]] = []
    if bc_path.exists():
        for line in bc_path.read_text(encoding="utf-8").strip().splitlines():
            if line.strip():
                boundary_contracts.append(json.loads(line))

    # verifier_report.json
    vr_path = ws / "verifier_report.json"
    verifier_report = json.loads(vr_path.read_text(encoding="utf-8")) if vr_path.exists() else {}

    # qdkt_events.jsonl
    qdkt_path = ws / "qdkt_events.jsonl"
    qdkt_events: list[dict[str, Any]] = []
    if qdkt_path.exists():
        for line in qdkt_path.read_text(encoding="utf-8").strip().splitlines():
            if line.strip():
                qdkt_events.append(json.loads(line))

    # dream_scores.jsonl
    dream_path = ws / "dream_scores.jsonl"
    dream_scores: list[dict[str, Any]] = []
    if dream_path.exists():
        for line in dream_path.read_text(encoding="utf-8").strip().splitlines():
            if line.strip():
                dream_scores.append(json.loads(line))

    return ICMWorkspaceExport(
        version=meta.get("icm_version", ICM_VERSION),
        workspace_id=meta.get("workspace_id", ws.name),
        domain=meta.get("domain", "generic"),
        arena_id=meta.get("arena_id", "unknown"),
        stages=stages,
        boundary_contracts=boundary_contracts,
        verifier_report=verifier_report,
        qdkt_events=qdkt_events,
        dream_scores=dream_scores,
        metadata=meta,
    )

