"""Coding Waboose — Aura's graph-guided, breadboarded code-review organ.

``waabooz`` is the widely documented Ojibwe/Anishinaabemowin word for rabbit;
``Waboose`` is retained here as the product spelling selected by the project
founder.  Coding Waboose is the public Aura owner.  It composes the generic
review engine with Aura's Planning Board / Coding Breadboard substrate.

Aura computes exact repository evidence.  A replaceable coding agent supplies
run-specific investigative focus.  The diagnostic breadboard simulates typed
review circuits and records which components are connected, mocked, or
energized.  Verification proves; a human authorizes any separate Forge repair.
"""
from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
import os
from pathlib import Path
import tokenize
from typing import Any

from aura_coding_waboose_breadboard import compile_waboose_breadboard
from aura_review_arena import (
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
    AuraReviewArena,
    AuraReviewRequest,
)
from aura_waboose_learning import DEFAULT_LEARNING_ROOT, CodeRabbitLearningStore
from aura_waboose_semantic_rules import directive_semantic_rule_packs

CODING_WABOOSE_VERSION = "AURA_CODING_WABOOSE_V1"
CODING_WABOOSE_CONTRACT_VERSION = "AURA_CODING_WABOOSE_CONTRACT_V1"
CODING_WABOOSE_AGENT_PACKET_VERSION = "AURA_CODING_WABOOSE_AGENT_PACKET_V1"
CODING_WABOOSE_REVIEW_PACKET_VERSION = "AURA_CODING_WABOOSE_REVIEW_PACKET_V1"
PRODUCT_NAME = "Coding Waboose"


class CodingWaboose(AuraReviewArena):
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
    def _brand(packet: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(packet, dict):
            return packet
        packet["version"] = CODING_WABOOSE_VERSION
        packet["product"] = PRODUCT_NAME
        packet["production_mutation"] = False
        packet["automatic_fix"] = False
        packet["automatic_commit"] = False
        packet["automatic_push"] = False
        packet["automatic_pull_request"] = False
        packet["automatic_merge"] = False
        packet["human_review_required"] = True
        packet["patch_authority"] = PATCH_AUTHORITY
        packet["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
        return packet

    def _contract_payload(self, review_id: str) -> dict[str, Any]:
        state = self._reviews[review_id]
        contract = state["contract"].to_dict()
        contract["objective"] = state["request"].objective
        contract["product"] = PRODUCT_NAME
        contract["product_contract_version"] = CODING_WABOOSE_CONTRACT_VERSION
        return contract

    def _energized_ids(self, review_id: str) -> set[str]:
        state = self._reviews[review_id]
        values = state.setdefault("waboose_energized_focus_ids", set())
        if not isinstance(values, set):
            values = set(values)
            state["waboose_energized_focus_ids"] = values
        return values

    def _compile_breadboard(self, review_id: str, *, phase: str) -> dict[str, Any]:
        state = self._reviews[review_id]
        packet = compile_waboose_breadboard(
            self._contract_payload(review_id),
            energized_directive_ids=sorted(self._energized_ids(review_id)),
            phase=phase,
        )
        state["waboose_breadboard"] = packet
        return packet

    def _energize_deterministic_components(self, review_id: str) -> None:
        state = self._reviews[review_id]
        request: AuraReviewRequest = state["request"]
        executed_packs = set(state.get("semantic_rule_packs", []))
        for directive in state["contract"].focus_directives:
            # These three components are actually executed by the deterministic
            # V1 scan: AST/tool correctness checks, topology impact slicing, and
            # focused test discovery/execution when tests were requested.
            if directive.name in {"standard_correctness", "dependency_impact"}:
                self._energized_ids(review_id).add(directive.directive_id)
            elif directive.name == "test_adequacy" and request.run_tests:
                self._energized_ids(review_id).add(directive.directive_id)
            else:
                required_packs = directive_semantic_rule_packs(directive.to_dict())
                if required_packs and required_packs.issubset(executed_packs):
                    self._energized_ids(review_id).add(directive.directive_id)

    def prepare(self, value: AuraReviewRequest | Mapping[str, Any]) -> dict[str, Any]:
        result = super().prepare(value)
        if not result.get("ok"):
            return self._brand(result)
        review_id = str(result["review_id"])
        result["waboose_id"] = review_id.replace("REVIEW-", "WABOOSE-", 1)
        result["contract"]["product"] = PRODUCT_NAME
        result["contract"]["product_contract_version"] = CODING_WABOOSE_CONTRACT_VERSION
        result["diagnostic_breadboard"] = self._compile_breadboard(review_id, phase="PREPARED")
        state = self._reviews[review_id]
        learning = self.learning_store.learning_context(
            state["request"].objective,
            changed_files=list(state["contract"].changed_files),
        )
        state["waboose_learning_context"] = learning
        result["learned_review_memory"] = learning
        result["agent_packet"] = self._agent_packet_from_state(review_id, include_source=False)
        return self._brand(result)

    def scan(self, review_id: str) -> dict[str, Any]:
        result = super().scan(review_id)
        if not result.get("ok"):
            return self._brand(result)
        state = self._reviews[review_id]
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
        result["agent_packet"] = self._agent_packet_from_state(review_id, include_source=False)
        return self._brand(result)

    def agent_packet(
        self,
        review_id: str,
        *,
        include_source: bool = False,
        max_files: int = 24,
        max_lines_per_file: int = 120,
    ) -> dict[str, Any]:
        result = super().agent_packet(
            review_id,
            include_source=include_source,
            max_files=max_files,
            max_lines_per_file=max_lines_per_file,
        )
        return self._brand(result)

    def submit_findings(
        self,
        review_id: str,
        findings: Sequence[Mapping[str, Any]],
        *,
        agent_name: str = "external_agent",
    ) -> dict[str, Any]:
        result = super().submit_findings(review_id, findings, agent_name=agent_name)
        if not result.get("ok"):
            return self._brand(result)
        state = self._reviews[review_id]
        valid_directives = {
            directive.directive_id for directive in state["contract"].focus_directives
        }
        for finding in state.get("agent_findings", []):
            if finding.get("status") != "corroborated":
                continue
            for directive_id in finding.get("focus_directive_ids", []):
                if directive_id in valid_directives:
                    self._energized_ids(review_id).add(directive_id)
        result["diagnostic_breadboard"] = self._compile_breadboard(
            review_id,
            phase="AGENT_FINDINGS",
        )
        return self._brand(result)

    def finalize(self, review_id: str) -> dict[str, Any]:
        result = super().finalize(review_id)
        if not result.get("ok"):
            return self._brand(result)
        breadboard = self._compile_breadboard(review_id, phase="FINALIZE")
        result["packet_version"] = CODING_WABOOSE_REVIEW_PACKET_VERSION
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

    def status(self, review_id: str) -> dict[str, Any]:
        result = super().status(review_id)
        if not result.get("ok"):
            return self._brand(result)
        breadboard = self._reviews[review_id].get("waboose_breadboard")
        if breadboard is None:
            breadboard = self._compile_breadboard(review_id, phase=str(result.get("status") or "STATUS"))
        result["breadboard_status"] = breadboard["circuit_status"]
        result["energized_focus_directives"] = sorted(self._energized_ids(review_id))
        return self._brand(result)

    def _agent_packet_from_state(
        self,
        review_id: str,
        *,
        include_source: bool,
        max_files: int = 24,
        max_lines_per_file: int = 120,
    ) -> dict[str, Any]:
        packet = super()._agent_packet_from_state(
            review_id,
            include_source=include_source,
            max_files=max_files,
            max_lines_per_file=max_lines_per_file,
        )
        breadboard = self._reviews[review_id].get("waboose_breadboard")
        if breadboard is None:
            breadboard = self._compile_breadboard(review_id, phase="AGENT_PACKET")
        packet["packet_type"] = CODING_WABOOSE_AGENT_PACKET_VERSION
        packet["product"] = PRODUCT_NAME
        packet["diagnostic_breadboard"] = breadboard
        packet["learned_review_memory"] = self._reviews[review_id].get(
            "waboose_learning_context", {}
        )
        packet["agent_instructions"] = [
            "Use Coding Waboose focus directives as explicit diagnostic circuit components.",
            "Treat connected topology edges as navigation evidence and mocked inputs as unresolved, never invented, facts.",
            "Trace both forward consequences and backward proof requirements before submitting a finding.",
            *[
                item.replace("Review Arena", PRODUCT_NAME)
                for item in packet.get("agent_instructions", [])
            ],
        ]
        return self._brand(packet)

    def learn_from_coderabbit(self, review_payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._brand(self.learning_store.ingest_review(review_payload))

    def learning_summary(self) -> dict[str, Any]:
        return self._brand(self.learning_store.summary())


# Public request alias.  The underlying generic review request remains reusable.
CodingWabooseRequest = AuraReviewRequest


__all__ = [
    "CODING_WABOOSE_AGENT_PACKET_VERSION",
    "CODING_WABOOSE_CONTRACT_VERSION",
    "CODING_WABOOSE_REVIEW_PACKET_VERSION",
    "CODING_WABOOSE_VERSION",
    "PRODUCT_NAME",
    "CodingWaboose",
    "CodingWabooseRequest",
]
