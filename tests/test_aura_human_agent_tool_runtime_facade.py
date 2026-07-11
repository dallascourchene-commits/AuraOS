from pathlib import Path

from aura_human_agent_workflow import ToolRuntimeFacade


class FakeArenaToolRuntime:
    def get_tools(self):
        return {"ok": True, "tools": [{"tool_id": "topology_inspector"}]}

    def execute(self, tool_id, *, objective="", inputs=None):
        assert tool_id == "topology_inspector"
        assert objective == "inspect workflow"
        assert inputs == {"limit": 4}
        return {
            "run_id": "TOOL-123",
            "tool_id": tool_id,
            "objective": objective,
            "status": "COMPLETED",
            "outputs": {
                "ok": True,
                "localized_files": ["aura_human_agent_workflow.py"],
                "localized_symbols": ["ToolRuntimeFacade"],
                "line_ranges": [
                    {
                        "file": "aura_human_agent_workflow.py",
                        "symbol": "ToolRuntimeFacade",
                        "line_range": [37, 133],
                    }
                ],
                "ranking": {"tests": ["tests/test_aura_human_agent_tool_runtime_facade.py"]},
                "truth_class": "EXACT_REPOSITORY_FACTS",
            },
            "denial": {},
            "sandbox_receipt": {"sandbox_id": "SB-1"},
            "dissolution_receipt": {"dissolution_verified": True},
        }


def test_facade_delegates_to_arena_tool_runtime_and_preserves_packet_shape(tmp_path: Path):
    facade = ToolRuntimeFacade(tmp_path)
    facade._runtime = FakeArenaToolRuntime()

    packet = facade.execute(
        "topology_inspector",
        objective="inspect workflow",
        inputs={"limit": 4},
    )

    assert packet["run_id"] == "TOOL-123"
    assert packet["tool_id"] == "topology_inspector"
    assert packet["status"] == "COMPLETED"
    assert packet["outputs"]["ok"] is True
    assert packet["outputs"]["localized_files"] == ["aura_human_agent_workflow.py"]
    assert packet["outputs"]["tests"] == ["tests/test_aura_human_agent_tool_runtime_facade.py"]
    assert packet["sandbox_receipt"] == {"sandbox_id": "SB-1"}
    assert packet["dissolution_receipt"] == {"dissolution_verified": True}
    assert facade.get_run("TOOL-123") == {"ok": True, "run": packet}
