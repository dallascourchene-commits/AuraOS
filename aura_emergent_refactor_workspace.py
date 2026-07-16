"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xab10-[Q-SYS:EMERGENT_REFACTOR_WORKSPACE]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Persistent evidence before refactoring)
DEPENDENCIES: __future__, dataclasses, hashlib, json, os, pathlib, re, time, typing
FUNCTIONS: EmergentResultsStore, store_report, import_seed_reports, search_findings,
           build_refactor_packet, store_research_evidence, list_research_evidence
SYNOPSIS: Content-addressed, append-only storage and search for complete emergent-property
reports, refactor evidence packets, and bounded external research evidence. Stored findings
remain advisory until exact repository spans, tests, verifier gates, and human approval exist.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Iterable, Iterator, Sequence


WORKSPACE_VERSION = "AURA_EMERGENT_REFACTOR_WORKSPACE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
DEFAULT_STORE_PATH = Path("Aura_Memory/emergent_results")
TRUTH_STORED_REPORT = "STORED_EMERGENT_REPORT"
TRUTH_EXTERNAL_EVIDENCE = "EXTERNAL_RESEARCH_EVIDENCE_REQUIRES_LOCAL_VERIFICATION"


@dataclass(frozen=True)
class FindingSummary:
    finding_id: str
    run_id: str
    probe_id: str
    kind: str
    emergent_ability: str
    missing_wire: str
    status: str
    score: float
    source: dict[str, str] = field(default_factory=dict)
    target: dict[str, str] = field(default_factory=dict)
    required_tests: tuple[str, ...] = ()
    evidence_count: int = 0
    safe_to_patch: bool = False
    focus: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "run_id": self.run_id,
            "probe_id": self.probe_id,
            "kind": self.kind,
            "emergent_ability": self.emergent_ability,
            "missing_wire": self.missing_wire,
            "status": self.status,
            "score": self.score,
            "source": dict(self.source),
            "target": dict(self.target),
            "required_tests": list(self.required_tests),
            "evidence_count": self.evidence_count,
            "safe_to_patch": self.safe_to_patch,
            "focus": self.focus,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


class EmergentResultsStore:
    """Content-addressed persistent store for complete emergent-property evidence.

    Every imported report is stored verbatim inside an envelope under ``runs/``. The
    JSONL indexes contain only summaries and digests; deleting an index never deletes
    the full report. Seed reports committed with AuraOS are imported idempotently.
    """

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        store_root: str | Path | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        root = Path(store_root) if store_root is not None else self.repo_root / DEFAULT_STORE_PATH
        self.store_root = root.resolve()
        self.runs_dir = self.store_root / "runs"
        self.research_dir = self.store_root / "research"
        self.packets_dir = self.store_root / "refactor_packets"
        self.seed_dir = self.store_root / "seed_runs"
        self.runs_index = self.store_root / "runs_index.jsonl"
        self.research_index = self.store_root / "research_index.jsonl"
        for directory in (self.runs_dir, self.research_dir, self.packets_dir, self.seed_dir):
            directory.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Complete report storage
    # ------------------------------------------------------------------

    def store_report(
        self,
        report: dict[str, Any],
        *,
        source: str = "human_agent_arena",
        label: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(report, dict) or not report:
            raise ValueError("report must be a non-empty object")
        canonical = _canonical_json(report)
        digest = hashlib.sha256(canonical).hexdigest()
        run_id = f"EMR-{digest[:20]}"
        path = self.runs_dir / f"{run_id}.json"
        stored_at = time.time()
        envelope = {
            "workspace_version": WORKSPACE_VERSION,
            "run_id": run_id,
            "digest": digest,
            "stored_at": stored_at,
            "source": str(source or "unknown"),
            "label": str(label or ""),
            "metadata": dict(metadata or {}),
            "truth_class": TRUTH_STORED_REPORT,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "report": report,
        }
        created = not path.exists()
        if created:
            _atomic_write_json(path, envelope)
            summary = self._run_summary(envelope)
            _append_jsonl(self.runs_index, summary)
        else:
            existing = _read_json(path)
            stored_at = float(existing.get("stored_at", stored_at)) if isinstance(existing, dict) else stored_at
        return {
            "ok": True,
            "run_id": run_id,
            "digest": digest,
            "created": created,
            "stored_at": stored_at,
            "path": str(path.relative_to(self.repo_root)) if _is_relative_to(path, self.repo_root) else str(path),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def import_seed_reports(self) -> dict[str, Any]:
        imported: list[str] = []
        skipped: list[str] = []
        failed: list[dict[str, str]] = []
        if not self.seed_dir.exists():
            return {"ok": True, "imported": [], "skipped": [], "failed": []}
        for path in sorted(self.seed_dir.rglob("*.json")):
            try:
                payload = _read_json(path)
                if not isinstance(payload, dict):
                    raise ValueError("seed payload must be an object")
                report = payload.get("report", payload)
                result = self.store_report(
                    report,
                    source=str(payload.get("source") or "seed_report"),
                    label=str(payload.get("label") or path.stem),
                    metadata={
                        "seed_path": str(path.relative_to(self.store_root)),
                        **dict(payload.get("metadata") or {}),
                    },
                )
                (imported if result.get("created") else skipped).append(str(result.get("run_id")))
            except Exception as exc:  # noqa: BLE001
                failed.append({"path": str(path), "error": f"{type(exc).__name__}: {exc}"})
        return {
            "ok": not failed,
            "imported": imported,
            "skipped": skipped,
            "failed": failed,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def list_runs(self, *, limit: int = 50) -> dict[str, Any]:
        rows = _read_jsonl(self.runs_index)
        if not rows:
            for path in sorted(self.runs_dir.glob("EMR-*.json")):
                payload = _read_json(path)
                if isinstance(payload, dict):
                    rows.append(self._run_summary(payload))
        rows.sort(key=lambda item: float(item.get("stored_at", 0.0)), reverse=True)
        bounded = rows[: max(1, min(int(limit), 500))]
        return {
            "ok": True,
            "version": WORKSPACE_VERSION,
            "runs": bounded,
            "count": len(bounded),
            "total": len(rows),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def get_run(self, run_id: str) -> dict[str, Any]:
        safe_id = _safe_identifier(run_id, prefix="EMR-")
        path = self.runs_dir / f"{safe_id}.json"
        if not path.exists():
            return {"ok": False, "error": "emergent_run_not_found", "run_id": safe_id}
        payload = _read_json(path)
        return {"ok": True, "run": payload}

    # ------------------------------------------------------------------
    # Finding projection and search
    # ------------------------------------------------------------------

    def search_findings(
        self,
        query: str,
        *,
        limit: int = 20,
        statuses: Sequence[str] = (),
        run_ids: Sequence[str] = (),
    ) -> dict[str, Any]:
        query_text = str(query or "").strip()
        query_tokens = set(_tokens(query_text))
        status_filter = {str(item).upper() for item in statuses if str(item).strip()}
        run_filter = {str(item) for item in run_ids if str(item).strip()}
        ranked: list[tuple[float, FindingSummary]] = []
        for envelope in self._iter_run_envelopes(run_filter):
            for finding in self._iter_findings(envelope):
                if status_filter and finding.status.upper() not in status_filter:
                    continue
                text = " ".join(
                    [
                        finding.emergent_ability,
                        finding.missing_wire,
                        finding.status,
                        finding.focus,
                        finding.source.get("file", ""),
                        finding.source.get("symbol", ""),
                        finding.target.get("file", ""),
                        finding.target.get("symbol", ""),
                        " ".join(finding.required_tests),
                    ]
                )
                candidate_tokens = set(_tokens(text))
                overlap = len(query_tokens & candidate_tokens)
                coverage = overlap / max(1, len(query_tokens)) if query_tokens else 1.0
                exact_bonus = 0.35 if query_text and query_text.lower() in text.lower() else 0.0
                status_bonus = 0.25 if finding.status.upper() == "FUTURE_PATCHABLE" else 0.0
                evidence_bonus = min(0.25, finding.evidence_count * 0.025)
                rank = coverage + exact_bonus + status_bonus + evidence_bonus + min(0.35, finding.score / 12.0)
                if query_tokens and overlap == 0:
                    continue
                ranked.append((rank, finding))
        ranked.sort(key=lambda item: (-item[0], -item[1].score, item[1].finding_id))
        bounded = ranked[: max(1, min(int(limit), 100))]
        return {
            "ok": True,
            "query": query_text,
            "findings": [{**finding.to_dict(), "search_score": round(rank, 4)} for rank, finding in bounded],
            "count": len(bounded),
            "truth_class": TRUTH_STORED_REPORT,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def get_finding(self, finding_id: str) -> dict[str, Any]:
        needle = str(finding_id or "")
        for envelope in self._iter_run_envelopes(set()):
            for finding, raw in self._iter_findings_with_raw(envelope):
                if finding.finding_id == needle:
                    return {
                        "ok": True,
                        "finding": finding.to_dict(),
                        "raw": raw,
                        "truth_class": TRUTH_STORED_REPORT,
                        "patch_authority": PATCH_AUTHORITY,
                        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
                    }
        return {"ok": False, "error": "emergent_finding_not_found", "finding_id": needle}

    def build_refactor_packet(
        self,
        objective: str,
        *,
        finding_ids: Sequence[str] = (),
        research_evidence_ids: Sequence[str] = (),
        max_findings: int = 8,
        persist: bool = True,
    ) -> dict[str, Any]:
        objective_text = str(objective or "").strip()
        if not objective_text:
            raise ValueError("objective is required")
        selected: list[dict[str, Any]] = []
        if finding_ids:
            for finding_id in finding_ids:
                packet = self.get_finding(str(finding_id))
                if packet.get("ok"):
                    selected.append(dict(packet["finding"]))
        else:
            selected = list(self.search_findings(objective_text, limit=max_findings).get("findings", []))

        target_files = _unique(
            value
            for finding in selected
            for value in (
                (finding.get("source") or {}).get("file"),
                (finding.get("target") or {}).get("file"),
            )
            if value
        )
        target_symbols = _unique(
            value
            for finding in selected
            for value in (
                (finding.get("source") or {}).get("symbol"),
                (finding.get("target") or {}).get("symbol"),
            )
            if value
        )
        required_tests = _unique(
            test for finding in selected for test in list(finding.get("required_tests") or []) if test
        )
        missing_wires = _unique(
            str(finding.get("missing_wire") or "") for finding in selected if finding.get("missing_wire")
        )
        research_gaps: list[dict[str, Any]] = []
        acceptance_criteria: list[str] = []
        for finding in selected:
            ability = str(finding.get("emergent_ability") or "").strip()
            status = str(finding.get("status") or "").upper()
            evidence_count = int(finding.get("evidence_count") or 0)
            tests = list(finding.get("required_tests") or [])
            if ability:
                acceptance_criteria.append(f"Preserve or measurably improve: {ability}")
            if status == "NEEDS_GROUNDING" or evidence_count == 0:
                research_gaps.append(
                    {
                        "finding_id": finding.get("finding_id"),
                        "gap": "ground architecture and research evidence before implementation",
                        "suggested_queries": _suggested_queries(objective_text, ability, missing_wires),
                    }
                )
            if not tests:
                research_gaps.append(
                    {
                        "finding_id": finding.get("finding_id"),
                        "gap": "define deterministic acceptance test",
                        "suggested_queries": [],
                    }
                )

        linked_research = [
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
            "external_evidence_is_patch_authority": False,
            "local_verification_required": True,
            "human_approval_required": True,
            "truth_class": "EMERGENT_REFACTOR_EVIDENCE_PACKET",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        digest = hashlib.sha256(_canonical_json(payload)).hexdigest()
        packet_id = f"ERP-{digest[:20]}"
        payload["packet_id"] = packet_id
        if persist:
            _atomic_write_json(self.packets_dir / f"{packet_id}.json", payload)
        return {"ok": True, "packet": payload}

    # ------------------------------------------------------------------
    # External research evidence storage
    # ------------------------------------------------------------------

    def store_research_evidence(
        self,
        *,
        provider: str,
        query: str,
        results: Sequence[dict[str, Any]],
        linked_finding_ids: Sequence[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "workspace_version": WORKSPACE_VERSION,
            "provider": str(provider or "unknown").lower(),
            "query": str(query or ""),
            "stored_at": time.time(),
            "linked_finding_ids": [str(item) for item in linked_finding_ids if item],
            "metadata": dict(metadata or {}),
            "results": [dict(item) for item in results if isinstance(item, dict)],
            "truth_class": TRUTH_EXTERNAL_EVIDENCE,
            "external_evidence_is_patch_authority": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        digest = hashlib.sha256(_canonical_json(payload)).hexdigest()
        evidence_id = f"ERE-{digest[:20]}"
        payload["evidence_id"] = evidence_id
        path = self.research_dir / f"{evidence_id}.json"
        created = not path.exists()
        if created:
            _atomic_write_json(path, payload)
            _append_jsonl(
                self.research_index,
                {
                    "evidence_id": evidence_id,
                    "provider": payload["provider"],
                    "query": payload["query"],
                    "stored_at": payload["stored_at"],
                    "result_count": len(payload["results"]),
                    "linked_finding_ids": payload["linked_finding_ids"],
                    "digest": digest,
                },
            )
        return {
            "ok": True,
            "evidence_id": evidence_id,
            "created": created,
            "result_count": len(payload["results"]),
            "truth_class": TRUTH_EXTERNAL_EVIDENCE,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def list_research_evidence(self, *, limit: int = 50) -> dict[str, Any]:
        rows = _read_jsonl(self.research_index)
        rows.sort(key=lambda item: float(item.get("stored_at", 0.0)), reverse=True)
        bounded = rows[: max(1, min(int(limit), 500))]
        return {
            "ok": True,
            "evidence": bounded,
            "count": len(bounded),
            "total": len(rows),
            "truth_class": TRUTH_EXTERNAL_EVIDENCE,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def get_research_evidence(self, evidence_id: str) -> dict[str, Any]:
        safe_id = _safe_identifier(evidence_id, prefix="ERE-")
        path = self.research_dir / f"{safe_id}.json"
        if not path.exists():
            return {"ok": False, "error": "research_evidence_not_found", "evidence_id": safe_id}
        return {"ok": True, "evidence": _read_json(path)}

    # ------------------------------------------------------------------
    # Internal projection helpers
    # ------------------------------------------------------------------

    def _run_summary(self, envelope: dict[str, Any]) -> dict[str, Any]:
        report = dict(envelope.get("report") or {})
        probe_count = len(report.get("results", [])) if isinstance(report.get("results"), list) else 1
        finding_count = sum(1 for _ in self._iter_findings(envelope))
        return {
            "run_id": envelope.get("run_id"),
            "digest": envelope.get("digest"),
            "stored_at": envelope.get("stored_at"),
            "source": envelope.get("source"),
            "label": envelope.get("label"),
            "metadata": envelope.get("metadata", {}),
            "suite_version": report.get("suite_version") or report.get("version") or "",
            "probe_count": probe_count,
            "finding_count": finding_count,
            "truth_class": TRUTH_STORED_REPORT,
        }

    def _iter_run_envelopes(self, run_filter: set[str]) -> Iterator[dict[str, Any]]:
        for path in sorted(self.runs_dir.glob("EMR-*.json")):
            if run_filter and path.stem not in run_filter:
                continue
            payload = _read_json(path)
            if isinstance(payload, dict):
                yield payload

    def _iter_findings(self, envelope: dict[str, Any]) -> Iterator[FindingSummary]:
        for finding, _raw in self._iter_findings_with_raw(envelope):
            yield finding

    def _iter_findings_with_raw(
        self,
        envelope: dict[str, Any],
    ) -> Iterator[tuple[FindingSummary, dict[str, Any]]]:
        run_id = str(envelope.get("run_id") or "")
        report = dict(envelope.get("report") or {})
        for probe in _probe_reports(report):
            probe_id = str(probe.get("id") or probe.get("probe_id") or "report")
            focus = str(probe.get("focus") or "")
            inner = dict(probe.get("report") or probe)
            for kind, raw_items in (
                ("connection", inner.get("connections", [])),
                ("verified_cluster", inner.get("verified_clusters", inner.get("clusters", []))),
            ):
                for raw in raw_items or []:
                    if not isinstance(raw, dict):
                        continue
                    connection = dict(raw.get("best_connection") or raw)
                    source = dict(connection.get("source") or {})
                    target = dict(connection.get("target") or {})
                    identity = str(
                        raw.get("cluster_id")
                        or connection.get("connection_id")
                        or _stable_id(source, target, connection.get("missing_wire"), connection.get("emergent_ability"))
                    )
                    finding_id = "EMF-" + hashlib.sha256(
                        f"{run_id}:{probe_id}:{kind}:{identity}".encode("utf-8")
                    ).hexdigest()[:20]
                    score = float(raw.get("final_score", connection.get("emergence_score", 0.0)) or 0.0)
                    status = str(connection.get("status") or ("FUTURE_PATCHABLE" if raw.get("safe_to_patch") else ""))
                    evidence = list(connection.get("evidence") or [])
                    tests = tuple(str(item) for item in connection.get("required_tests", []) if item)
                    yield (
                        FindingSummary(
                            finding_id=finding_id,
                            run_id=run_id,
                            probe_id=probe_id,
                            kind=kind,
                            emergent_ability=str(raw.get("emergent_ability") or connection.get("emergent_ability") or ""),
                            missing_wire=str(raw.get("missing_wire") or connection.get("missing_wire") or ""),
                            status=status,
                            score=score,
                            source={"file": str(source.get("file") or ""), "symbol": str(source.get("symbol") or "")},
                            target={"file": str(target.get("file") or ""), "symbol": str(target.get("symbol") or "")},
                            required_tests=tests,
                            evidence_count=len(evidence),
                            safe_to_patch=bool(raw.get("safe_to_patch") or status.upper() == "FUTURE_PATCHABLE"),
                            focus=focus,
                        ),
                        raw,
                    )


def _probe_reports(report: dict[str, Any]) -> Iterator[dict[str, Any]]:
    results = report.get("results")
    if isinstance(results, list):
        for item in results:
            if isinstance(item, dict):
                yield item
        return
    if isinstance(report.get("report"), dict):
        yield report
        return
    yield {"id": report.get("id", "report"), "focus": report.get("focus", ""), "report": report}


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str), encoding="utf-8")
    os.replace(temp, path)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str) + "\n")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]+", str(text).lower()) if len(token) >= 3]


def _unique(values: Iterable[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for value in values:
        key = json.dumps(value, sort_keys=True, default=str) if isinstance(value, (dict, list)) else str(value)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _stable_id(*parts: Any) -> str:
    return hashlib.sha256(_canonical_json(parts)).hexdigest()[:24]


def _safe_identifier(value: str, *, prefix: str) -> str:
    text = str(value or "")
    if not text.startswith(prefix) or not re.fullmatch(r"[A-Z]{3}-[a-f0-9]{20}", text):
        raise ValueError(f"invalid identifier: {text}")
    return text


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _suggested_queries(objective: str, ability: str, missing_wires: Sequence[str]) -> list[dict[str, str]]:
    core = " ".join(part for part in (objective, ability) if part).strip()
    wire = " ".join(str(item) for item in missing_wires[:3])
    return [
        {"provider": "arxiv", "query": f"{core} {wire} empirical benchmark".strip()},
        {"provider": "github", "query": f"{core} {wire} language:Python".strip()},
    ]
