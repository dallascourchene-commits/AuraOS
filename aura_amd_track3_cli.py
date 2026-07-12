"""CLI and status dashboard for the AMD Track 3 Sovereign Learning Arena demo."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import time
from typing import Any

from aura_amd_track3_worker import (
    FixtureProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    load_tasks,
    run_task,
)

DEFAULT_TASKS = ".aura/amd_track3_demo_tasks.json"
DEFAULT_CRYSTALS = ".aura/runtime/amd_track3/verified_crystals.jsonl"
DEFAULT_OLLAMA_MODEL = os.environ.get("AURA_OLLAMA_MODEL", "qwen2.5-coder:3b")
DEFAULT_OLLAMA_HOST = os.environ.get("AURA_OLLAMA_HOST", "http://127.0.0.1:11434")


def _provider(args):
    if args.provider == "fixture":
        return FixtureProvider()
    if args.provider == "ollama":
        return OllamaProvider(
            endpoint=args.endpoint or DEFAULT_OLLAMA_HOST,
            model=args.model or DEFAULT_OLLAMA_MODEL,
            context_tokens=args.context_tokens,
            output_tokens=args.output_tokens,
        )
    if args.provider == "auto":
        candidate = OllamaProvider(
            endpoint=args.endpoint or DEFAULT_OLLAMA_HOST,
            model=args.model or DEFAULT_OLLAMA_MODEL,
            context_tokens=args.context_tokens,
            output_tokens=args.output_tokens,
        )
        health = candidate.health()
        if health.get("ok") and health.get("model_available"):
            return candidate
        return FixtureProvider()
    return OpenAICompatibleProvider(
        endpoint=args.endpoint or os.environ.get("AURA_TRACK3_ENDPOINT", "https://api.deepseek.com/v1"),
        model=args.model or os.environ.get("AURA_TRACK3_MODEL", "deepseek-chat"),
        api_key=os.environ.get("AURA_TRACK3_API_KEY") or os.environ.get("DEEPSEEK_API_KEY", ""),
    )


def _rows(path: str) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            continue
    return rows


def run_cycle(args) -> dict[str, Any]:
    provider = _provider(args)
    tasks = load_tasks(args.tasks)
    results = [
        run_task(
            task=task,
            provider=provider,
            repo_root=args.repo_root,
            crystal_path=args.crystals,
            amd_backend=args.amd_backend,
        )
        for task in tasks
    ]
    return {
        "ok": all(item.get("ok") for item in results),
        "status": "SOVEREIGN_ARENA_CYCLE_COMPLETED",
        "provider": provider.name,
        "model": provider.model,
        "amd_backend": args.amd_backend,
        "task_count": len(tasks),
        "verified_count": sum(1 for item in results if item.get("ok")),
        "reuse_count": sum(len(item.get("prior_crystal_matches") or ()) for item in results),
        "results": results,
        "pipeline": [
            "human_objective",
            "polysynthetic_intent_packet",
            "guarded_wfst_admission",
            "bounded_coding_arena",
            "replaceable_llm_worker",
            "detached_verification",
            "verified_crystal",
            "procedure_reuse",
        ],
        "training_command": f"python aura_amd_track3_train.py --crystals {args.crystals}",
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
    }


def demo_sequence(args) -> dict[str, Any]:
    if args.reset_demo:
        Path(args.crystals).unlink(missing_ok=True)
    result = run_cycle(args)
    result["status"] = "TRACK3_DEMO_SEQUENCE_COMPLETED" if result.get("ok") else "TRACK3_DEMO_SEQUENCE_FAILED"
    result["demo_claim"] = (
        "Aura compiles intent into governed Arenas and preserves only verifier-passing "
        "experience as reusable procedural memory."
    )
    return result


def status(args) -> dict[str, Any]:
    rows = _rows(args.crystals)
    latest = rows[-1] if rows else None
    reuse_links = [
        {
            "crystal_id": row.get("crystal_id"),
            "task_id": row.get("task_id"),
            "reused_crystal_ids": row.get("reused_crystal_ids") or [],
            "reusable_procedure": row.get("reusable_procedure"),
        }
        for row in rows
        if row.get("reused_crystal_ids")
    ]
    return {
        "ok": True,
        "status": "READY",
        "product": "Aura Sovereign Learning Arena",
        "track": "AMD Hackathon Act II Track 3",
        "current_execution": {
            "default_inspection_provider": "fixture",
            "local_live_provider": "Ollama",
            "local_model": DEFAULT_OLLAMA_MODEL,
            "ollama_host": DEFAULT_OLLAMA_HOST,
        },
        "amd_path": {
            "implemented": True,
            "currently_required": False,
            "inference": "Gemma through a ROCm-compatible OpenAI endpoint",
            "learning": "verified crystals -> optional PEFT/LoRA adapter",
            "inspection_mode": "deterministic container requires no model or secret",
        },
        "pipeline": [
            "Objective",
            "DIR -> ASP -> CLASS -> SUBJ -> VOICE -> STEM",
            "Guarded WFST",
            "Bounded Arena",
            "Ollama / AMD Gemma / fixture worker",
            "Detached verifier",
            "Verified crystal",
            "Reusable procedure",
        ],
        "guarded_wfst": {
            "rule": "hard guards -> admissible transitions -> deterministic ranking -> capability binding",
            "allowed": ["inspect", "bounded patch proposal", "declared verifier"],
            "blocked": ["secret access", "unrelated files", "commit", "push", "merge"],
        },
        "sovereign_knowledge_contract": {
            "domain": "Anishinaabemowin tutor",
            "rule": "No naked language answer strings",
            "required_fields": ["confidence_status", "source_refs", "dialect_notes", "governance_status"],
            "uncertain_output": "teacher/community review queue",
            "restricted_material_to_external_models": False,
        },
        "crystal_count": len(rows),
        "verified_count": sum(1 for row in rows if row.get("test_returncode") == 0),
        "reuse_links": reuse_links,
        "latest_crystal": latest,
        "main_code_path": "aura_amd_track3_cli.py -> aura_amd_track3_worker.py -> verified_crystals.jsonl",
        "c3_authority_preserved": True,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
    }


def _dashboard_html() -> bytes:
    return r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aura Sovereign Learning Arena</title>
<style>
:root{color-scheme:dark;--panel:#101c25;--line:#28404f;--text:#e8f4f6;--muted:#91aab5;--ok:#5ee6a8;--warn:#ffd166}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top,#183444,#091016 48%);font:15px/1.45 system-ui,sans-serif;color:var(--text)}
main{max-width:1180px;margin:auto;padding:28px}.hero{padding:24px;border:1px solid var(--line);background:rgba(9,16,22,.78);border-radius:18px}
h1{margin:.1em 0;font-size:clamp(28px,5vw,54px)}h2{font-size:18px;margin:0 0 12px}.tag{color:var(--ok);font-weight:700;letter-spacing:.08em;text-transform:uppercase}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin-top:16px}.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px;min-height:160px}
.flow{display:flex;gap:8px;overflow:auto;padding:16px 0}.step{white-space:nowrap;border:1px solid var(--line);border-radius:999px;padding:8px 12px;background:#102733}.arrow{align-self:center;color:var(--muted)}
pre{font-family:ui-monospace,Consolas,monospace;white-space:pre-wrap;overflow:auto;background:#071016;border-radius:10px;padding:12px;color:#cce6ec}.ok{color:var(--ok)}.muted{color:var(--muted)}.metric{font-size:30px;font-weight:750}
</style></head><body><main>
<section class="hero"><div class="tag">AMD Hackathon Act II · Track 3</div><h1>Aura Sovereign Learning Arena</h1>
<p>Models are replaceable workers. Intent is compiled, authority is guarded, work is bounded, and only verifier-passing experience becomes reusable procedural memory.</p><div id="flow" class="flow"></div></section>
<div class="grid">
<section class="card"><h2>Polysynthetic Intent</h2><pre>DIR → ASP → CLASS → SUBJ → VOICE → STEM</pre><p class="muted">Distinct governance and morphotactic inspirations remain explicitly attributed.</p></section>
<section class="card"><h2>Guarded WFST</h2><div class="ok">Allowed</div><p id="allowed"></p><div style="color:var(--warn)">Blocked</div><p id="blocked"></p></section>
<section class="card"><h2>Verified Crystals</h2><div id="count" class="metric">0</div><p id="reuse" class="muted">No reuse link yet.</p></section>
<section class="card"><h2>Current Worker</h2><pre id="worker">Loading…</pre></section>
<section class="card"><h2>Sovereign Knowledge</h2><p>No naked language answer strings.</p><ul id="knowledge"></ul></section>
<section class="card"><h2>AMD Path</h2><pre id="amd">Loading…</pre></section>
</div><section class="card" style="margin-top:14px"><h2>Latest Crystal</h2><pre id="latest">Run the demo sequence to create crystals.</pre></section>
<p class="muted">No automatic commit · no push · no merge · Phase C3 authority preserved</p>
</main><script>
async function refresh(){const r=await fetch('/status');const s=await r.json();
document.getElementById('flow').innerHTML=s.pipeline.map((x,i)=>`<span class="step">${x}</span>${i<s.pipeline.length-1?'<span class="arrow">→</span>':''}`).join('');
document.getElementById('allowed').textContent=s.guarded_wfst.allowed.join(' · ');document.getElementById('blocked').textContent=s.guarded_wfst.blocked.join(' · ');
document.getElementById('count').textContent=s.verified_count;document.getElementById('reuse').textContent=s.reuse_links.length?`${s.reuse_links.length} crystal reuse link(s) recorded`:'No reuse link yet.';
document.getElementById('worker').textContent=JSON.stringify(s.current_execution,null,2);document.getElementById('amd').textContent=JSON.stringify(s.amd_path,null,2);
document.getElementById('knowledge').innerHTML=s.sovereign_knowledge_contract.required_fields.map(x=>`<li>${x}</li>`).join('');document.getElementById('latest').textContent=s.latest_crystal?JSON.stringify(s.latest_crystal,null,2):'Run the demo sequence to create crystals.';}
refresh();setInterval(refresh,3000);</script></body></html>'''.encode("utf-8")


def serve(args) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in {"/", "/index.html"}:
                body = _dashboard_html()
                content_type = "text/html; charset=utf-8"
            elif self.path == "/crystals":
                body = json.dumps(_rows(args.crystals), indent=2, ensure_ascii=False, default=str).encode("utf-8")
                content_type = "application/json"
            else:
                body = json.dumps(status(args), indent=2, ensure_ascii=False, default=str).encode("utf-8")
                content_type = "application/json"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *values):
            return

    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


def _add_provider_args(cmd: argparse.ArgumentParser) -> None:
    cmd.add_argument("--provider", choices=("fixture", "ollama", "auto", "openai-compatible"), default="fixture")
    cmd.add_argument("--endpoint", default="")
    cmd.add_argument("--model", default="")
    cmd.add_argument("--context-tokens", type=int, default=4096)
    cmd.add_argument("--output-tokens", type=int, default=1024)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aura AMD Track 3 Sovereign Learning Arena")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--crystals", default=DEFAULT_CRYSTALS)
    parser.add_argument("--amd-backend", default=os.environ.get("AURA_AMD_BACKEND", "AMD ROCm / approved compute"))
    sub = parser.add_subparsers(dest="command", required=True)
    run_once = sub.add_parser("run-once")
    _add_provider_args(run_once)
    run_loop = sub.add_parser("run-loop")
    _add_provider_args(run_loop)
    run_loop.add_argument("--interval-seconds", type=int, default=60)
    run_loop.add_argument("--cycles", type=int, default=0, help="0 means continue until interrupted")
    demo = sub.add_parser("demo-sequence")
    _add_provider_args(demo)
    demo.add_argument("--reset-demo", action="store_true")
    sub.add_parser("status")
    server = sub.add_parser("serve")
    server.add_argument("--host", default="0.0.0.0")
    server.add_argument("--port", type=int, default=8080)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "status":
        result = status(args)
    elif args.command == "serve":
        serve(args)
        return 0
    elif args.command == "run-once":
        result = run_cycle(args)
    elif args.command == "demo-sequence":
        result = demo_sequence(args)
    else:
        completed = 0
        result = {"ok": True, "status": "STOPPED"}
        while args.cycles == 0 or completed < args.cycles:
            try:
                result = run_cycle(args)
            except Exception as exc:
                result = {"ok": False, "status": "CYCLE_FAILED", "error": str(exc), "error_type": type(exc).__name__, "cycle": completed + 1}
            print(json.dumps(result, ensure_ascii=False, default=str), flush=True)
            completed += 1
            if args.cycles == 0 or completed < args.cycles:
                time.sleep(max(1, args.interval_seconds))
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
