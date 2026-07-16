"""Native, Coding Arena, and Human Agent Arena clients for one Architect service.

The existing surfaces remain separate.  This module only gives each surface the
same canonical Architect/Surgeon contract, explicit controls, and local output
vault so a user receives identical governance whether working natively, visually,
or through a third-party coding agent.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from aura_architect_control import ArchitectControlProfile, normalize_control_profile
from aura_arena_architect_connector import AuraArenaArchitectConnector

ARENA_ARCHITECT_RUNTIME_VERSION = "AURA_ARENA_ARCHITECT_RUNTIME_V1"
_NATIVE_SURFACES = {"native", "coding_arena", "human_agent_arena"}


class ArenaArchitectRuntime:
    """Stateful client over the shared proposal-only Architect connector."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        surface: str = "native",
        control: Mapping[str, Any] | ArchitectControlProfile | None = None,
        connector: AuraArenaArchitectConnector | None = None,
    ) -> None:
        selected_surface = str(surface or "native").strip().lower()
        if selected_surface not in _NATIVE_SURFACES:
            raise ValueError(f"unsupported native Arena surface: {selected_surface}")
        self.repo_root = Path(repo_root).resolve()
        self.surface = selected_surface
        self.control = normalize_control_profile(control, surface=selected_surface)
        self.connector = connector or AuraArenaArchitectConnector(self.repo_root)

    def configure(
        self,
        control: Mapping[str, Any] | ArchitectControlProfile,
    ) -> dict[str, Any]:
        self.control = normalize_control_profile(control, surface=self.surface)
        return {
            "ok": True,
            "version": ARENA_ARCHITECT_RUNTIME_VERSION,
            "surface": self.surface,
            "control_profile": self.control.to_dict(),
        }

    def compare_plans(
        self,
        *,
        objective: str,
        candidates: Sequence[Mapping[str, Any]],
        required_capabilities: Sequence[str] = (),
        run_id: str = "",
        benchmark: bool = False,
    ) -> dict[str, Any]:
        return self.connector.compare_plans(
            objective=objective,
            candidates=candidates,
            required_capabilities=required_capabilities,
            control=self.control,
            surface=self.surface,
            run_id=run_id,
            benchmark=benchmark,
        )

    def prepare_refactor(
        self,
        *,
        objective: str,
        candidates: Sequence[Mapping[str, Any]],
        required_capabilities: Sequence[str] = (),
        target_file: str | None = None,
        target_symbol: str | None = None,
        run_id: str = "",
        benchmark: bool = False,
    ) -> dict[str, Any]:
        return self.connector.prepare_refactor(
            objective=objective,
            candidates=candidates,
            required_capabilities=required_capabilities,
            target_file=target_file,
            target_symbol=target_symbol,
            control=self.control,
            surface=self.surface,
            run_id=run_id,
            benchmark=benchmark,
        )

    def open_surgeon_session(
        self,
        *,
        objective: str,
        candidates: Sequence[Mapping[str, Any]],
        required_capabilities: Sequence[str] = (),
        provider: str = "native",
        model: str = "",
        run_id: str = "",
    ) -> dict[str, Any]:
        return self.connector.open_surgeon_session(
            objective=objective,
            candidates=candidates,
            required_capabilities=required_capabilities,
            provider=provider,
            model=model,
            control=self.control,
            surface=self.surface,
            run_id=run_id,
        )

    def next_surgeon_turn(self, session_id: str) -> dict[str, Any]:
        return self.connector.surgeon_next(session_id)

    def submit_surgeon_output(
        self,
        *,
        session_id: str,
        turn_id: str,
        response: str,
        provider_usage: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.connector.surgeon_submit(
            session_id=session_id,
            turn_id=turn_id,
            response=response,
            provider_usage=provider_usage,
        )

    def surgeon_status(self, session_id: str) -> dict[str, Any]:
        return self.connector.surgeon_status(session_id)

    def apply_council_replan(
        self,
        *,
        session_id: str,
        remaining_act_capsules: list[dict[str, Any]],
        rationale: str,
        prompt: str = "",
        response: str = "",
        provider_usage: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.connector.surgeon_replan(
            session_id=session_id,
            remaining_act_capsules=remaining_act_capsules,
            rationale=rationale,
            prompt=prompt,
            response=response,
            provider_usage=dict(provider_usage or {}),
        )

    def list_refactor_outputs(self, *, limit: int = 50) -> dict[str, Any]:
        return self.connector.list_refactor_outputs(limit=limit)

    def load_refactor_output(
        self,
        relative_path: str,
        *,
        max_bytes: int = 2_000_000,
    ) -> dict[str, Any]:
        return self.connector.load_refactor_output(relative_path, max_bytes=max_bytes)


class NativeAuraArchitectRuntime(ArenaArchitectRuntime):
    def __init__(self, repo_root: str | Path = ".", **kwargs: Any) -> None:
        super().__init__(repo_root, surface="native", **kwargs)


class CodingArenaArchitectRuntime(ArenaArchitectRuntime):
    def __init__(self, repo_root: str | Path = ".", **kwargs: Any) -> None:
        super().__init__(repo_root, surface="coding_arena", **kwargs)


class HumanAgentArenaArchitectRuntime(ArenaArchitectRuntime):
    def __init__(self, repo_root: str | Path = ".", **kwargs: Any) -> None:
        super().__init__(repo_root, surface="human_agent_arena", **kwargs)


__all__ = [
    "ARENA_ARCHITECT_RUNTIME_VERSION",
    "ArenaArchitectRuntime",
    "CodingArenaArchitectRuntime",
    "HumanAgentArenaArchitectRuntime",
    "NativeAuraArchitectRuntime",
]
