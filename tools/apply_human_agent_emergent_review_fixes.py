#!/usr/bin/env python3
"""Apply the three reviewed Human Agent emergent-integration repairs.

Temporary branch-maintenance helper. It is idempotent and fails when an expected source
shape is absent rather than guessing at a patch location.
"""

from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"patch target not found in {path}: {old[:120]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_workspace() -> None:
    path = "aura_emergent_refactor_workspace.py"
    replace_once(
        path,
        '''                        finding.status,
                        finding.focus,
                        finding.source.get("file", ""),
''',
        '''                        finding.status,
                        finding.source.get("file", ""),
''',
    )
    replace_once(
        path,
        '''                overlap = len(query_tokens & candidate_tokens)
                coverage = overlap / max(1, len(query_tokens)) if query_tokens else 1.0
                exact_bonus = 0.35 if query_text and query_text.lower() in text.lower() else 0.0
                status_bonus = 0.25 if finding.status.upper() == "FUTURE_PATCHABLE" else 0.0
                evidence_bonus = min(0.25, finding.evidence_count * 0.025)
                rank = coverage + exact_bonus + status_bonus + evidence_bonus + min(0.35, finding.score / 12.0)
                if query_tokens and overlap == 0:
                    continue
''',
        '''                overlap = len(query_tokens & candidate_tokens)
                query_size = len(query_tokens)
                coverage = overlap / max(1, query_size) if query_tokens else 1.0
                min_overlap = 1 if query_size <= 2 else 2
                min_coverage = 0.20 if query_size <= 2 else 0.34
                if query_tokens and (overlap < min_overlap or coverage < min_coverage):
                    continue
                exact_bonus = 0.50 if query_text and query_text.lower() in text.lower() else 0.0
                status_bonus = 0.10 if finding.status.upper() == "FUTURE_PATCHABLE" else 0.0
                evidence_bonus = min(0.10, finding.evidence_count * 0.01)
                emergence_bonus = min(0.10, max(0.0, finding.score) / 40.0)
                rank = coverage * 4.0 + exact_bonus + status_bonus + evidence_bonus + emergence_bonus
''',
    )
    replace_once(
        path,
        '''    def build_refactor_packet(
        self,
        objective: str,
        *,
        finding_ids: Sequence[str] = (),
        research_evidence_ids: Sequence[str] = (),
        max_findings: int = 8,
        persist: bool = True,
    ) -> dict[str, Any]:
''',
        '''    def _research_evidence_ids_for_findings(
        self,
        finding_ids: Sequence[str],
        *,
        limit: int = 100,
    ) -> list[str]:
        needles = {str(item) for item in finding_ids if str(item).strip()}
        if not needles:
            return []
        rows = [
            row
            for row in _read_jsonl(self.research_index)
            if needles & {str(item) for item in row.get("linked_finding_ids", []) if item}
        ]
        rows.sort(key=lambda item: float(item.get("stored_at", 0.0)), reverse=True)
        return _unique(
            str(row.get("evidence_id") or "")
            for row in rows[: max(1, min(int(limit), 500))]
            if row.get("evidence_id")
        )

    def build_refactor_packet(
        self,
        objective: str,
        *,
        finding_ids: Sequence[str] = (),
        research_evidence_ids: Sequence[str] = (),
        max_findings: int = 8,
        persist: bool = True,
    ) -> dict[str, Any]:
''',
    )
    replace_once(
        path,
        '''        linked_research = [
            item
            for evidence_id in research_evidence_ids
            if (item := self.get_research_evidence(str(evidence_id))).get("ok")
        ]
        payload = {
            "workspace_version": WORKSPACE_VERSION,
            "objective": objective_text,
            "created_at": time.time(),
            "selected_findings": selected,
            "selected_finding_ids": [item.get("finding_id") for item in selected],
            "target_files": target_files,
            "target_symbols": target_symbols,
            "missing_wires": missing_wires,
            "required_tests": required_tests,
            "acceptance_criteria": _unique(acceptance_criteria),
            "research_gaps": research_gaps,
            "research_evidence": [item.get("evidence") for item in linked_research],
''',
        '''        selected_finding_ids = [
            str(item.get("finding_id") or "") for item in selected if item.get("finding_id")
        ]
        auto_research_ids = self._research_evidence_ids_for_findings(selected_finding_ids)
        linked_research_ids = _unique(
            [
                *[str(item) for item in research_evidence_ids if str(item).strip()],
                *auto_research_ids,
            ]
        )
        linked_research: list[dict[str, Any]] = []
        for evidence_id in linked_research_ids:
            item = self.get_research_evidence(str(evidence_id))
            if item.get("ok"):
                linked_research.append(item)
        research_evidence = [
            dict(item.get("evidence") or {}) for item in linked_research if item.get("evidence")
        ]
        evidence_ids_by_finding: dict[str, list[str]] = {}
        for evidence in research_evidence:
            evidence_id = str(evidence.get("evidence_id") or "")
            for finding_id in evidence.get("linked_finding_ids", []) or []:
                if evidence_id:
                    evidence_ids_by_finding.setdefault(str(finding_id), []).append(evidence_id)
        for gap in research_gaps:
            finding_id = str(gap.get("finding_id") or "")
            linked_ids = _unique(evidence_ids_by_finding.get(finding_id, []))
            gap["linked_research_evidence_ids"] = linked_ids
            gap["status"] = (
                "EVIDENCE_FOUND_REQUIRES_LOCAL_VERIFICATION" if linked_ids else "OPEN"
            )

        payload = {
            "workspace_version": WORKSPACE_VERSION,
            "objective": objective_text,
            "created_at": time.time(),
            "selected_findings": selected,
            "selected_finding_ids": selected_finding_ids,
            "target_files": target_files,
            "target_symbols": target_symbols,
            "missing_wires": missing_wires,
            "required_tests": required_tests,
            "acceptance_criteria": _unique(acceptance_criteria),
            "research_gaps": research_gaps,
            "research_evidence_ids": linked_research_ids,
            "research_evidence": research_evidence,
''',
    )
    replace_once(
        path,
        '''    def get_run(self, run_id: str) -> dict[str, Any]:
        safe_id = _safe_identifier(run_id, prefix="EMR-")
        path = self.runs_dir / f"{safe_id}.json"
''',
        '''    def get_run(self, run_id: str) -> dict[str, Any]:
        try:
            safe_id = _safe_identifier(run_id, prefix="EMR-")
        except ValueError:
            return {"ok": False, "error": "invalid_emergent_run_id", "run_id": str(run_id or "")}
        path = self.runs_dir / f"{safe_id}.json"
''',
    )
    replace_once(
        path,
        '''    def get_research_evidence(self, evidence_id: str) -> dict[str, Any]:
        safe_id = _safe_identifier(evidence_id, prefix="ERE-")
        path = self.research_dir / f"{safe_id}.json"
''',
        '''    def get_research_evidence(self, evidence_id: str) -> dict[str, Any]:
        try:
            safe_id = _safe_identifier(evidence_id, prefix="ERE-")
        except ValueError:
            return {
                "ok": False,
                "error": "invalid_research_evidence_id",
                "evidence_id": str(evidence_id or ""),
            }
        path = self.research_dir / f"{safe_id}.json"
''',
    )


def patch_server() -> None:
    path = "aura_human_agent_arena_server.py"
    replace_once(
        path,
        "from http.server import BaseHTTPRequestHandler, HTTPServer",
        "from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer",
    )
    replace_once(
        path,
        '''SERVER_VERSION = "AURA_HUMAN_AGENT_ARENA_SERVER_V0_4"


class HumanAgentArenaServerState:
''',
        '''SERVER_VERSION = "AURA_HUMAN_AGENT_ARENA_SERVER_V0_4"


class AuraThreadingHTTPServer(ThreadingHTTPServer):
    """Serve slow research requests without freezing the Arena control surface."""

    daemon_threads = True
    allow_reuse_address = True


class HumanAgentArenaServerState:
''',
    )
    replace_once(path, ") -> HTTPServer:", ") -> AuraThreadingHTTPServer:")
    replace_once(
        path,
        "    server = HTTPServer((host, int(port)), make_handler(state))",
        "    server = AuraThreadingHTTPServer((host, int(port)), make_handler(state))",
    )


def patch_ui() -> None:
    path = "aura_human_agent_arena/emergent.js"
    replace_once(
        path,
        "  let selectedFindingIds = new Set();",
        "  let selectedFindingIds = new Set();\n  let selectedResearchEvidenceIds = new Set();",
    )
    replace_once(
        path,
        '''      objective,
      finding_ids: [...selectedFindingIds],
    });
''',
        '''      objective,
      finding_ids: [...selectedFindingIds],
      research_evidence_ids: [...selectedResearchEvidenceIds],
    });
''',
    )
    replace_once(
        path,
        '''    renderResearchResults(result);
    setStatus(result.ok
''',
        '''    const storedEvidenceId = result.stored_evidence?.evidence_id;
    if (storedEvidenceId) selectedResearchEvidenceIds.add(storedEvidenceId);
    renderResearchResults(result);
    setStatus(result.ok
''',
    )
    replace_once(
        path,
        '''      host.innerHTML = (result.evidence || []).map(item => `
        <article class="evidence-index-card">
          <strong>${escape(item.provider)} · ${escape(item.query)}</strong>
          <small>${Number(item.result_count || 0)} results · ${escape(item.evidence_id)}</small>
        </article>`).join('') || '<p class="placeholder">No research evidence stored yet.</p>';
''',
        '''      host.innerHTML = (result.evidence || []).map(item => {
        const checked = selectedResearchEvidenceIds.has(item.evidence_id) ? 'checked' : '';
        return `<article class="evidence-index-card">
          <label class="finding-select"><input type="checkbox" ${checked} data-select-evidence="${escape(item.evidence_id)}"> attach</label>
          <strong>${escape(item.provider)} · ${escape(item.query)}</strong>
          <small>${Number(item.result_count || 0)} results · ${escape(item.evidence_id)}</small>
        </article>`;
      }).join('') || '<p class="placeholder">No research evidence stored yet.</p>';
      host.querySelectorAll('[data-select-evidence]').forEach(input => {
        input.addEventListener('change', event => {
          const evidenceId = event.currentTarget.dataset.selectEvidence;
          if (event.currentTarget.checked) selectedResearchEvidenceIds.add(evidenceId);
          else selectedResearchEvidenceIds.delete(evidenceId);
        });
      });
''',
    )


def patch_tests() -> None:
    path = Path("tests/test_aura_emergent_refactor_workspace.py")
    text = path.read_text(encoding="utf-8")
    if "AuraThreadingHTTPServer," not in text:
        old = '''from aura_human_agent_arena_server import (
    HumanAgentArenaServerState,
'''
        new = '''from aura_human_agent_arena_server import (
    AuraThreadingHTTPServer,
    HumanAgentArenaServerState,
'''
        if old not in text:
            raise RuntimeError("test import target not found")
        text = text.replace(old, new, 1)
    marker = "def test_review_fixes_rank_link_and_thread"
    if marker not in text:
        text += r'''


def test_review_fixes_rank_link_and_thread(tmp_path: Path):
    store = EmergentResultsStore(tmp_path)
    seed_root = Path(__file__).resolve().parents[1] / "Aura_Memory" / "emergent_results" / "seed_runs" / "2026-07-16"
    store.store_report(json.loads((seed_root / "emergent_capacity_probes.json").read_text(encoding="utf-8")))
    store.store_report(json.loads((seed_root / "grounded_capacity_projections.json").read_text(encoding="utf-8")))

    ranked = store.search_findings("Refactor the Human Agent Arena", limit=8)
    assert ranked["count"] > 0
    top_files = [
        " ".join(
            [
                str((item.get("source") or {}).get("file") or ""),
                str((item.get("target") or {}).get("file") or ""),
            ]
        ).lower()
        for item in ranked["findings"][:3]
    ]
    assert any("human_agent" in files for files in top_files), ranked["findings"][:3]
    assert not all("coding_arena" in files and "human_agent" not in files for files in top_files)

    sample_store = EmergentResultsStore(tmp_path / "linked")
    sample_store.store_report(sample_report(), source="test")
    finding = sample_store.search_findings("Human Agent Arena research", limit=1)["findings"][0]
    stored = sample_store.store_research_evidence(
        provider="arxiv",
        query="human agent arena verification",
        results=[{"arxiv_id": "2601.00001", "title": "Arena verification"}],
        linked_finding_ids=[finding["finding_id"]],
    )
    packet = sample_store.build_refactor_packet(
        "Refactor the Human Agent Arena",
        finding_ids=[finding["finding_id"]],
    )["packet"]
    assert stored["evidence_id"] in packet["research_evidence_ids"]
    assert packet["research_evidence"][0]["evidence_id"] == stored["evidence_id"]

    assert issubclass(AuraThreadingHTTPServer, ThreadingHTTPServer)
    assert AuraThreadingHTTPServer.daemon_threads is True
    assert sample_store.get_run("invalid")["error"] == "invalid_emergent_run_id"
    assert sample_store.get_research_evidence("invalid")["error"] == "invalid_research_evidence_id"
'''
    if "from http.server import ThreadingHTTPServer" not in text:
        text = text.replace("import json\n", "import json\nfrom http.server import ThreadingHTTPServer\n", 1)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    patch_workspace()
    patch_server()
    patch_ui()
    patch_tests()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
