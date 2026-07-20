"""MCP entrypoint for Aura's guarded GitHub publication Agent Bridge."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import aura_agent_arena_mcp as _base_mcp
from aura_agent_arena_github_bridge import GitHubPublishingAuraAgentArenaBridge


GITHUB_MCP_VERSION = "AURA_AGENT_BRIDGE_GITHUB_MCP_V2"

_CHANGE_SCHEMA = {
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "operation": {
                    "type": "string",
                    "const": "upsert",
                    "default": "upsert",
                },
                "mode": {
                    "type": "string",
                    "const": "100644",
                    "default": "100644",
                },
                "encoding": {
                    "type": "string",
                    "enum": ["utf-8", "base64"],
                    "default": "utf-8",
                },
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "operation": {"type": "string", "const": "delete"},
                "mode": {
                    "type": "string",
                    "const": "100644",
                    "default": "100644",
                },
            },
            "required": ["path", "operation"],
            "additionalProperties": False,
        },
    ]
}

_GITHUB_TOOL_DEFINITIONS = [
    {
        "name": "aura_github_prepare_publication",
        "description": (
            "Compile an exact-head GraphQL createCommitOnBranch publication "
            "contract. Rejects temporary materializer workflows by default."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository_full_name": {"type": "string"},
                "publication_mode": {
                    "type": "string",
                    "enum": ["create", "update"],
                    "default": "create",
                },
                "base_branch": {"type": "string", "default": "main"},
                "head_branch": {"type": "string"},
                "expected_base_sha": {"type": "string"},
                "expected_parent_sha": {"type": "string"},
                "commit_message": {"type": "string"},
                "pr_title": {"type": "string"},
                "pr_body": {"type": "string"},
                "pr_number": {"type": "integer", "minimum": 1},
                "draft": {"type": "boolean", "default": True},
                "publish_authorized": {
                    "type": "boolean",
                    "default": False,
                },
                "allow_temporary_transport": {
                    "type": "boolean",
                    "default": False,
                },
                "changes": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 512,
                    "items": _CHANGE_SCHEMA,
                },
            },
            "required": [
                "repository_full_name",
                "head_branch",
                "expected_base_sha",
                "commit_message",
                "pr_title",
                "changes",
            ],
            "additionalProperties": False,
        },
    },
    {
        "name": "aura_github_execute_publication",
        "description": (
            "Execute one stored, explicitly authorized GraphQL-CAS publication "
            "contract using AURA_GITHUB_TOKEN. Creates/advances a branch and "
            "PR; never merges."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "contract_id": {"type": "string"},
            },
            "required": ["contract_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "aura_github_prepare_merge",
        "description": (
            "Prepare non-authoritative exact-head merge evidence. This tool "
            "never returns executable connector arguments or merge authority."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository_full_name": {"type": "string"},
                "pr_number": {"type": "integer", "minimum": 1},
                "expected_head_sha": {"type": "string"},
                "merge_method": {
                    "type": "string",
                    "enum": ["merge", "squash", "rebase"],
                    "default": "squash",
                },
                "checks_passed": {
                    "type": "boolean",
                    "default": False,
                },
                "review_threads_resolved": {
                    "type": "boolean",
                    "default": False,
                },
                "codemap_regenerated": {
                    "type": "boolean",
                    "default": False,
                },
            },
            "required": [
                "repository_full_name",
                "pr_number",
                "expected_head_sha",
            ],
            "additionalProperties": False,
        },
    },
]


def _prepare_handler(
    bridge: GitHubPublishingAuraAgentArenaBridge,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    return bridge.aura_github_prepare_publication(arguments)


def _execute_handler(
    bridge: GitHubPublishingAuraAgentArenaBridge,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    return bridge.aura_github_execute_publication(
        contract_id=str(arguments.get("contract_id") or "")
    )


def _merge_handler(
    bridge: GitHubPublishingAuraAgentArenaBridge,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    return bridge.aura_github_prepare_merge(arguments)


def install_github_tools() -> None:
    """Install GitHub publication tools into the retained Agent Bridge MCP."""

    existing = {
        str(item.get("name") or "")
        for item in _base_mcp.TOOL_DEFINITIONS
        if isinstance(item, Mapping)
    }
    for definition in _GITHUB_TOOL_DEFINITIONS:
        if definition["name"] not in existing:
            _base_mcp.TOOL_DEFINITIONS.append(definition)
    _base_mcp._TOOL_HANDLERS.update(
        {
            "aura_github_prepare_publication": _prepare_handler,
            "aura_github_execute_publication": _execute_handler,
            "aura_github_prepare_merge": _merge_handler,
        }
    )


def handle_request(
    bridge: GitHubPublishingAuraAgentArenaBridge,
    request: dict[str, Any],
) -> dict[str, Any] | None:
    install_github_tools()
    return _base_mcp.handle_request(bridge, request)


def serve_stdio(
    bridge: GitHubPublishingAuraAgentArenaBridge | None = None,
) -> None:
    install_github_tools()
    _base_mcp.serve_stdio(
        bridge or GitHubPublishingAuraAgentArenaBridge()
    )


def main() -> None:
    serve_stdio()


if __name__ == "__main__":
    main()


__all__ = [
    "GITHUB_MCP_VERSION",
    "handle_request",
    "install_github_tools",
    "main",
    "serve_stdio",
]
