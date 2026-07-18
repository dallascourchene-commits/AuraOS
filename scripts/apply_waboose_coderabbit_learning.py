from __future__ import annotations

from pathlib import Path


def replace_required(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing patch target: {label}")
    return text.replace(old, new, 1)


def patch_learning_module() -> None:
    path = Path("aura_waboose_learning.py")
    text = path.read_text(encoding="utf-8")
    text = replace_required(
        text,
        "        self.qdkt = qdkt or UnifiedQDKT()\n\n    def _load_patterns",
        '''        self.qdkt = qdkt

    def _qdkt(self) -> UnifiedQDKT:
        if self.qdkt is None:
            self.qdkt = UnifiedQDKT()
        return self.qdkt

    def _known_lesson_ids(self) -> set[str]:
        if not self.episodes_path.exists():
            return set()
        result: set[str] = set()
        with self.episodes_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                lesson_id = str(row.get("lesson_id") or "")
                if lesson_id:
                    result.add(lesson_id)
        return result

    def _load_patterns''',
        "lazy QDKT and lesson dedupe",
    )
    text = text.replace("qdkt=self.qdkt,", "qdkt=self._qdkt(),")
    text = replace_required(
        text,
        '''        learned: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for index, finding in enumerate(findings):
''',
        '''        learned: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        known_lesson_ids = self._known_lesson_ids()
        for index, finding in enumerate(findings):
''',
        "lesson dedupe state",
    )
    text = replace_required(
        text,
        '''            self._append_episode(lesson)
            pattern = self._update_pattern(patterns, lesson)
''',
        '''            if lesson.lesson_id in known_lesson_ids:
                rejected.append({"index": index, "reason": "duplicate_grounded_lesson"})
                continue
            known_lesson_ids.add(lesson.lesson_id)
            self._append_episode(lesson)
            pattern = self._update_pattern(patterns, lesson)
''',
        "lesson dedupe admission",
    )
    text = replace_required(
        text,
        '''            **self._result(bool(learned), "learned" if learned else "no_grounded_findings"),
''',
        '''            **self._result(True, "learned" if learned else "no_new_grounded_findings"),
''',
        "successful empty learning result",
    )
    text = replace_required(
        text,
        '''        self.qdkt.observe(
            "coderabbit_review_learning",
''',
        '''        qdkt = self._qdkt()
        qdkt.observe(
            "coderabbit_review_learning",
''',
        "QDKT local owner",
    )
    text = replace_required(
        text,
        '''        if count >= _CRYSTAL_CONFIRMATIONS and confidence >= _CRYSTAL_CONFIDENCE:
            self.qdkt.crystallize(
''',
        '''        qdkt.observe(
            "causal_update",
            {
                "hypothesis": (
                    f"Grounded CodeRabbit pattern {pattern_id} predicts a recurring "
                    "Coding Waboose review defect"
                ),
                "success": True,
                "error": max(0.0, 1.0 - confidence),
                "pattern_id": pattern_id,
                "file_path": lesson.file,
                "source_grounded": True,
                "patch_authority": False,
            },
            rationale="CodeRabbit confirmation updates the Waboose causal learning ledger.",
            concept=f"coding_waboose_causal:{pattern_id}",
            confidence=confidence,
            subsystem="coding_waboose",
        )
        if count >= _CRYSTAL_CONFIRMATIONS and confidence >= _CRYSTAL_CONFIDENCE:
            qdkt.crystallize(
''',
        "causal ledger and crystallization",
    )
    path.write_text(text, encoding="utf-8")


def patch_emergent_spine() -> None:
    path = Path("aura_emergent_evidence_spine.py")
    text = path.read_text(encoding="utf-8")
    text = replace_required(
        text,
        "import subprocess\nfrom typing import Any\n",
        "import subprocess\nimport tokenize\nfrom typing import Any\n",
        "tokenize import",
    )
    text = replace_required(
        text,
        ")\n\n\n@dataclass(frozen=True)\nclass EmergentEvidenceRequest:",
        ''')


def _boolean(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ValueError("expected a boolean")


@dataclass(frozen=True)
class EmergentEvidenceRequest:''',
        "strict boolean helper",
    )
    text = replace_required(
        text,
        '''            include_source=bool(value.get("include_source", True)),
            include_future=bool(value.get("include_future", True)),
            include_research_plan=bool(value.get("include_research_plan", True)),
            include_offline_research=bool(value.get("include_offline_research", True)),
''',
        '''            include_source=_boolean(value.get("include_source"), default=True),
            include_future=_boolean(value.get("include_future"), default=True),
            include_research_plan=_boolean(
                value.get("include_research_plan"), default=True
            ),
            include_offline_research=_boolean(
                value.get("include_offline_research"), default=True
            ),
''',
        "strict request booleans",
    )
    text = replace_required(
        text,
        "        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:\n",
        '''        except (
            OSError,
            TypeError,
            ValueError,
            UnicodeError,
            SyntaxError,
            LookupError,
            json.JSONDecodeError,
        ) as exc:
''',
        "source error boundary",
    )
    text = replace_required(
        text,
        '''            if record["symbol"] in normalized_symbols:
                score += 120
''',
        '''            if normalized_symbols.intersection(
                {record["symbol"], record["qualified_symbol"]}
            ):
                score += 120
''',
        "qualified inventory filter",
    )
    text = replace_required(
        text,
        '''                    record["symbol"],
                    record.get("parent_symbol") or "",
''',
        '''                    record["symbol"],
                    record["qualified_symbol"],
                    record.get("parent_symbol") or "",
''',
        "qualified inventory search",
    )
    text = replace_required(
        text,
        '''def _repo_python_sources(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(root.glob("**/*.py")):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if any(part in EXCLUDE_DIRS for part in relative.parts):
            continue
        try:
            files[relative.as_posix()] = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    return files
''',
        '''def _repo_python_sources(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(root.glob("**/*.py")):
        relative = path.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in relative.parts):
            continue
        with tokenize.open(path) as handle:
            files[relative.as_posix()] = handle.read()
    return files
''',
        "exact repository source ingestion",
    )
    text = replace_required(
        text,
        "def _select_seed_nodes(\n",
        '''def _qualified_symbol(node: CodeTopoNode) -> str:
    return f"{node.parent_symbol}.{node.symbol}" if node.parent_symbol else node.symbol


def _matches_symbol(node: CodeTopoNode, symbol: str) -> bool:
    return symbol in {node.symbol, _qualified_symbol(node)}


def _select_seed_nodes(
''',
        "qualified symbol helpers",
    )
    text = replace_required(
        text,
        "            and node.symbol == symbol\n",
        "            and _matches_symbol(node, symbol)\n",
        "explicit seed qualified match",
    )
    text = replace_required(
        text,
        "                if node.kind not in ATOMIC_KINDS or node.symbol != symbol:\n",
        "                if node.kind not in ATOMIC_KINDS or not _matches_symbol(node, symbol):\n",
        "connectome qualified match",
    )
    text = replace_required(
        text,
        '''        if symbol and node.symbol != symbol:
            continue
''',
        '''        if symbol and not _matches_symbol(node, symbol):
            continue
''',
        "resolver qualified match",
    )
    text = replace_required(
        text,
        '''    visited: list[str] = []
    seen: set[str] = set()
    queue: deque[tuple[str, int]] = deque((node_id, 0) for node_id in seed_ids)
    admitted_edges: list[dict[str, Any]] = []
    edge_keys: set[tuple[str, str, str]] = set()
''',
        '''    visited: list[str] = []
    seen: set[str] = set()
    queue: deque[tuple[str, int]] = deque((node_id, 0) for node_id in seed_ids)
    queued: set[str] = set(seed_ids)
''',
        "closure queued set",
    )
    text = replace_required(
        text,
        '''            key = (edge.src_id, edge.dst_id, edge.edge_type)
            if key not in edge_keys:
                edge_keys.add(key)
                admitted_edges.append(edge.to_dict())
            if other not in seen and len(visited) + len(queue) < max_nodes:
                queue.append((other, distance + 1))
    return visited, admitted_edges
''',
        '''            if (
                other not in seen
                and other not in queued
                and len(visited) + len(queue) < max_nodes
            ):
                queued.add(other)
                queue.append((other, distance + 1))
    selected = set(visited)
    admitted_edges: list[dict[str, Any]] = []
    edge_keys: set[tuple[str, str, str]] = set()
    for edge in sorted(
        anchor.edges,
        key=lambda item: (item.edge_type, item.src_id, item.dst_id, item.evidence),
    ):
        if edge.src_id not in selected or edge.dst_id not in selected:
            continue
        key = (edge.src_id, edge.dst_id, edge.edge_type)
        if key in edge_keys:
            continue
        edge_keys.add(key)
        admitted_edges.append(edge.to_dict())
    return visited, admitted_edges
''',
        "bounded closure endpoint filter",
    )
    text = replace_required(
        text,
        '''    include_files.update(tests)
    for node in anchor.nodes.values():
''',
        '''    include_files.update(tests)
    selected_module_ids = {
        anchor.module_nodes.get(file_path) for file_path in include_files
    }
    selected_module_ids.discard(None)
    test_targets = include_ids | selected_module_ids
    for edge in anchor.edges:
        if edge.edge_type == "test" and edge.dst_id in test_targets:
            include_ids.add(edge.src_id)
    for node in anchor.nodes.values():
''',
        "bounded test callable preservation",
    )
    path.write_text(text, encoding="utf-8")


def patch_review_arena() -> None:
    path = Path("aura_review_arena.py")
    text = path.read_text(encoding="utf-8")
    text = replace_required(
        text,
        "import uuid\n",
        '''import uuid

from aura_waboose_semantic_rules import (
    SEMANTIC_RULE_PACKS,
    scan_semantic_review_rules,
)
''',
        "semantic rule imports",
    )
    text = replace_required(
        text,
        "def _default_command_runner(\n",
        '''def _strict_boolean(value: Any, *, default: bool, field_name: str) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field_name} must be a boolean")


def _default_command_runner(
''',
        "review strict boolean helper",
    )
    text = replace_required(
        text,
        '''            run_tests=bool(value.get("run_tests", True)),
            run_optional_tools=bool(value.get("run_optional_tools", True)),
''',
        '''            run_tests=_strict_boolean(
                value.get("run_tests"), default=True, field_name="run_tests"
            ),
            run_optional_tools=_strict_boolean(
                value.get("run_optional_tools"),
                default=True,
                field_name="run_optional_tools",
            ),
''',
        "review strict booleans",
    )
    text = replace_required(
        text,
        '''            "tool_results": [],
            "status": "PREPARED",
''',
        '''            "tool_results": [],
            "semantic_rule_packs": [],
            "status": "PREPARED",
''',
        "semantic state initialization",
    )
    text = replace_required(
        text,
        '''        findings: list[dict[str, Any]] = []
        deleted_files = set(state.get("deleted_files", ()))
        for file in contract.changed_files:
            if file.endswith(".py") and file not in deleted_files:
                findings.extend(self._scan_python_file(file))
''',
        '''        findings: list[dict[str, Any]] = []
        semantic_rule_packs: set[str] = set()
        deleted_files = set(state.get("deleted_files", ()))
        for file in contract.changed_files:
            if file.endswith(".py") and file not in deleted_files:
                file_findings = self._scan_python_file(file)
                findings.extend(file_findings)
                fatal_rules = {
                    str(item.get("rule") or "") for item in file_findings
                }.intersection(
                    {"changed-file-missing", "changed-file-unreadable", "python-syntax-error"}
                )
                if not fatal_rules:
                    semantic_rule_packs.update(SEMANTIC_RULE_PACKS)
''',
        "semantic scan receipts",
    )
    text = replace_required(
        text,
        '''        state["deterministic_findings"] = normalized
        state["tool_results"] = tool_results
''',
        '''        state["deterministic_findings"] = normalized
        state["tool_results"] = tool_results
        state["semantic_rule_packs"] = sorted(semantic_rule_packs)
''',
        "semantic receipt state",
    )
    text = replace_required(
        text,
        '''            "tool_results": _sanitize(tool_results),
            "agent_packet": self._agent_packet_from_state(review_id, include_source=False),
''',
        '''            "tool_results": _sanitize(tool_results),
            "semantic_rule_packs_executed": sorted(semantic_rule_packs),
            "agent_packet": self._agent_packet_from_state(review_id, include_source=False),
''',
        "semantic receipt response",
    )
    text = replace_required(
        text,
        '''        except OSError:
            return []
        visitor = _ASTReviewVisitor(file=file)
        visitor.visit(tree)
        return visitor.findings
''',
        '''        except OSError as exc:
            return [{
                "origin": "builtin_ast",
                "rule": "changed-file-unreadable",
                "category": "correctness",
                "severity": "high",
                "confidence": 1.0,
                "title": "Changed file could not be read",
                "message": f"{type(exc).__name__}: {exc}",
                "file": file,
                "line_start": 1,
                "line_end": 1,
                "suggested_fix": "Restore exact readable source before review.",
                "evidence": [{"kind": "filesystem", "source": "review_head"}],
                "status": "confirmed",
            }]
        visitor = _ASTReviewVisitor(file=file)
        visitor.visit(tree)
        return [
            *visitor.findings,
            *scan_semantic_review_rules(file=file, source=source, tree=tree),
        ]
''',
        "semantic findings integration",
    )
    path.write_text(text, encoding="utf-8")


def patch_waboose() -> None:
    path = Path("aura_coding_waboose.py")
    text = path.read_text(encoding="utf-8")
    text = replace_required(
        text,
        "from collections.abc import Mapping, Sequence\nfrom typing import Any\n",
        "import ast\nfrom collections.abc import Mapping, Sequence\nimport os\nfrom pathlib import Path\nimport tokenize\nfrom typing import Any\n",
        "Waboose learning imports",
    )
    text = replace_required(
        text,
        "from aura_coding_waboose_breadboard import compile_waboose_breadboard\n",
        '''from aura_coding_waboose_breadboard import compile_waboose_breadboard
from aura_waboose_learning import CodeRabbitLearningStore, DEFAULT_LEARNING_ROOT
from aura_waboose_semantic_rules import directive_semantic_rule_packs
''',
        "Waboose learning owners",
    )
    text = replace_required(
        text,
        '''class CodingWaboose(AuraReviewArena):
    """Canonical public code-review owner for Aura-native and external agents."""

    @staticmethod
''',
        '''class CodingWaboose(AuraReviewArena):
    """Canonical public code-review owner for Aura-native and external agents."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        command_runner: Any = None,
        learning_root: str | Path | None = None,
    ) -> None:
        super().__init__(repo_root, command_runner=command_runner)
        configured = learning_root or os.environ.get(
            "AURA_WABOOSE_LEARNING_ROOT", str(DEFAULT_LEARNING_ROOT)
        )
        self.learning_store = CodeRabbitLearningStore(
            self.repo_root,
            learning_root=configured,
        )

    @staticmethod
''',
        "Waboose learning initialization",
    )
    text = replace_required(
        text,
        '''        request: AuraReviewRequest = state["request"]
        for directive in state["contract"].focus_directives:
''',
        '''        request: AuraReviewRequest = state["request"]
        executed_packs = set(state.get("semantic_rule_packs", []))
        for directive in state["contract"].focus_directives:
''',
        "Waboose semantic packs",
    )
    text = replace_required(
        text,
        '''            elif directive.name == "test_adequacy" and request.run_tests:
                self._energized_ids(review_id).add(directive.directive_id)
''',
        '''            elif directive.name == "test_adequacy" and request.run_tests:
                self._energized_ids(review_id).add(directive.directive_id)
            else:
                required_packs = directive_semantic_rule_packs(directive.to_dict())
                if required_packs and required_packs.issubset(executed_packs):
                    self._energized_ids(review_id).add(directive.directive_id)
''',
        "semantic directive energization",
    )
    text = replace_required(
        text,
        '''        result["diagnostic_breadboard"] = self._compile_breadboard(review_id, phase="PREPARED")
        result["agent_packet"] = self._agent_packet_from_state(review_id, include_source=False)
        return self._brand(result)
''',
        '''        result["diagnostic_breadboard"] = self._compile_breadboard(review_id, phase="PREPARED")
        state = self._reviews[review_id]
        learning = self.learning_store.learning_context(
            state["request"].objective,
            changed_files=list(state["contract"].changed_files),
        )
        state["waboose_learning_context"] = learning
        result["learned_review_memory"] = learning
        result["agent_packet"] = self._agent_packet_from_state(review_id, include_source=False)
        return self._brand(result)
''',
        "prepare learning retrieval",
    )
    text = replace_required(
        text,
        '''        self._energize_deterministic_components(review_id)
        result["diagnostic_breadboard"] = self._compile_breadboard(review_id, phase="SCAN")
''',
        '''        state = self._reviews[review_id]
        learned_findings: list[dict[str, Any]] = []
        for file in state["contract"].changed_files:
            if not file.endswith(".py"):
                continue
            path = self._resolve_file(file)
            if path is None or not path.is_file():
                continue
            try:
                with tokenize.open(path) as handle:
                    source = handle.read()
                tree = ast.parse(source, filename=file)
            except (OSError, SyntaxError, UnicodeError, LookupError):
                continue
            learned_findings.extend(
                self.learning_store.scan_learned_patterns(
                    file=file,
                    source=source,
                    tree=tree,
                )
            )
        if learned_findings:
            state["deterministic_findings"] = self._normalize_findings(
                [*state.get("deterministic_findings", []), *learned_findings],
                origin_default="waboose_learned_pattern",
            )
            result["deterministic_findings"] = state["deterministic_findings"]
        result["learned_pattern_findings"] = len(learned_findings)
        self._energize_deterministic_components(review_id)
        result["diagnostic_breadboard"] = self._compile_breadboard(review_id, phase="SCAN")
''',
        "learned pattern scan",
    )
    text = replace_required(
        text,
        '''        result["packet_version"] = CODING_WABOOSE_REVIEW_PACKET_VERSION
        result["diagnostic_breadboard"] = breadboard
        result["breadboard_status"] = breadboard["circuit_status"]
        return self._brand(result)
''',
        '''        result["packet_version"] = CODING_WABOOSE_REVIEW_PACKET_VERSION
        result["diagnostic_breadboard"] = breadboard
        result["breadboard_status"] = breadboard["circuit_status"]
        state = self._reviews[review_id]
        energized = self._energized_ids(review_id)
        unverified = [
            directive.to_dict()
            for directive in state["contract"].focus_directives
            if directive.origin == "agent" and directive.directive_id not in energized
        ]
        result["semantic_rule_packs_executed"] = list(
            state.get("semantic_rule_packs", [])
        )
        result["unverified_focus_directives"] = unverified
        result["semantic_review_complete"] = not unverified
        result["learned_review_memory"] = state.get(
            "waboose_learning_context", {}
        )
        if unverified:
            result["ok"] = False
            result["error"] = "semantic_review_incomplete"
            result["status"] = "BLOCKED_INCOMPLETE_SEMANTIC_REVIEW"
            result["deferred_forge_repair_requests"] = list(
                result.get("forge_repair_requests") or []
            )
            result["forge_repair_requests"] = []
        return self._brand(result)
''',
        "semantic completeness gate",
    )
    text = replace_required(
        text,
        '''        packet["diagnostic_breadboard"] = breadboard
        packet["agent_instructions"] = [
''',
        '''        packet["diagnostic_breadboard"] = breadboard
        packet["learned_review_memory"] = self._reviews[review_id].get(
            "waboose_learning_context", {}
        )
        packet["agent_instructions"] = [
''',
        "agent learning context",
    )
    text = replace_required(
        text,
        '''        return self._brand(packet)


# Public request alias.
''',
        '''        return self._brand(packet)

    def learn_from_coderabbit(self, review_payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._brand(self.learning_store.ingest_review(review_payload))

    def learning_summary(self) -> dict[str, Any]:
        return self._brand(self.learning_store.summary())


# Public request alias.
''',
        "public learning methods",
    )
    path.write_text(text, encoding="utf-8")


def patch_affordance_directory() -> None:
    path = Path("aura_affordance_directory.py")
    text = path.read_text(encoding="utf-8")
    marker = '''    {
        "id": "aura.llm_egress",
'''
    entry = '''    {
        "id": "aura.coding_waboose.learning",
        "name": "Coding Waboose External Review Learning",
        "description": "Grounds successful CodeRabbit review findings against exact source, maps them through the Capability Connectome, reranks prior lessons with DREAM-lite, and records repeated confirmations in QDKT so Waboose can emulate recurring review patterns.",
        "status": "active",
        "tags": ["coding", "waboose", "review", "coderabbit", "dream", "qdkt", "connectome", "learning", "verification"],
        "when_to_use": "After a successful CodeRabbit review or before a Coding Waboose scan that may benefit from prior grounded review lessons.",
        "when_not_to_use": "Never use external review memory as patch, merge, or verification authority.",
        "implemented_by": ["aura_waboose_learning.py", "aura_waboose_semantic_rules.py", "aura_coderabbit_learning_cli.py"],
        "symbols": ["CodeRabbitLearningStore", "scan_semantic_review_rules", "directive_semantic_rule_packs"],
        "tests": ["tests/test_aura_waboose_learning.py", "tests/test_aura_waboose_semantic_rules.py", "tests/test_aura_waboose_semantic_completeness.py"],
        "docs": ["docs/AURA_CODING_WABOOSE.md"],
        "commands": ["aura_coderabbit_learning_cli.py ingest", "aura_coderabbit_learning_cli.py summary"],
        "requires": ["aura.dream.reranking", "aura.qdkt.memory", "aura.agent_arena.bridge"],
        "outputs": ["grounded_review_lessons", "dream_ranked_patterns", "qdkt_crystals", "semantic_rule_directives"],
        "related_affordances": ["aura.dream.reranking", "aura.qdkt.memory", "aura.agent_arena.bridge", "aura.emergent_potential.audit", "aura.patch_quality_gate"],
        "safety": "CodeRabbit is a teacher signal only. Exact source grounding is required. DREAM/QDKT memory is advisory and never patch or merge authority.",
        "patch_authority": False,
        "vsa_patch_authority": False,
        "prompt_card": "Use Waboose Learning to retrieve grounded external-review lessons, then re-prove any current finding against exact source and tests.",
    },
'''
    text = replace_required(text, marker, entry + marker, "Waboose learning affordance")
    path.write_text(text, encoding="utf-8")


def patch_agent_bridge() -> None:
    path = Path("aura_agent_arena_persistence_bridge.py")
    text = path.read_text(encoding="utf-8")
    marker = '''    def aura_waboose_prepare(
'''
    methods = '''    def aura_waboose_learn_coderabbit(
        self,
        review_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self.coding_waboose.learn_from_coderabbit(review_payload)

    def aura_waboose_learning_summary(self) -> dict[str, Any]:
        return self.coding_waboose.learning_summary()

'''
    text = replace_required(text, marker, methods + marker, "bridge learning methods")
    catalog_marker = '''            {
                "name": "aura_waboose_prepare",
'''
    catalog = '''            {
                "name": "aura_waboose_learn_coderabbit",
                "description": "Ground and learn from one successful CodeRabbit review through Connectome, DREAM-lite, and QDKT.",
                "required_inputs": ["review_payload"],
            },
            {
                "name": "aura_waboose_learning_summary",
                "description": "Report grounded CodeRabbit lessons, learned patterns, and QDKT crystals.",
                "required_inputs": [],
            },
'''
    text = replace_required(text, catalog_marker, catalog + catalog_marker, "bridge learning catalog")
    path.write_text(text, encoding="utf-8")


def patch_mcp() -> None:
    path = Path("aura_agent_arena_mcp.py")
    text = path.read_text(encoding="utf-8")
    definition_marker = '''    {
        "name": "aura_waboose_prepare",
'''
    definitions = '''    {
        "name": "aura_waboose_learn_coderabbit",
        "description": "Learn from a successful CodeRabbit review after exact head/source grounding.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "review_payload": {"type": "object"},
            },
            "required": ["review_payload"],
        },
    },
    {
        "name": "aura_waboose_learning_summary",
        "description": "Show Coding Waboose external-review learning status.",
        "inputSchema": {"type": "object", "properties": {}},
    },
'''
    text = replace_required(text, definition_marker, definitions + definition_marker, "MCP learning definitions")
    handler_marker = '''@_register_tool("aura_waboose_prepare")
'''
    handlers = '''@_register_tool("aura_waboose_learn_coderabbit")
def _handle_waboose_learn_coderabbit(
    bridge: AuraAgentArenaBridge,
    args: dict[str, Any],
) -> dict[str, Any]:
    review_payload = args.get("review_payload")
    if not isinstance(review_payload, Mapping):
        raise ValueError("review_payload must be an object")
    return bridge.aura_waboose_learn_coderabbit(dict(review_payload))


@_register_tool("aura_waboose_learning_summary")
def _handle_waboose_learning_summary(
    bridge: AuraAgentArenaBridge,
    args: dict[str, Any],
) -> dict[str, Any]:
    del args
    return bridge.aura_waboose_learning_summary()


'''
    text = replace_required(text, handler_marker, handlers + handler_marker, "MCP learning handlers")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_learning_module()
    patch_emergent_spine()
    patch_review_arena()
    patch_waboose()
    patch_affordance_directory()
    patch_agent_bridge()
    patch_mcp()


if __name__ == "__main__":
    main()
