"""Terminal client for Aura's live guarded Human and Coding Arena routes.

This stdlib-only client talks to ``aura_human_agent_arena_server`` so workflow state
remains owned by the running local server. It does not execute Git operations,
promote grammars, or bypass guards.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "http://127.0.0.1:8090"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


def _parse_payload(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("payload JSON must be an object")
    return parsed


def _request(base_url: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    url = base_url.rstrip("/") + path
    data = None
    headers: dict[str, str] = {"accept": "application/json"}
    method = "GET"
    if payload is not None:
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        headers["content-type"] = "application/json"
        method = "POST"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310 - explicit local URL supplied by operator
            body = response.read().decode("utf-8")
            parsed = json.loads(body or "{}")
            return int(response.status), parsed if isinstance(parsed, dict) else {"ok": False, "error": "response_not_object"}
    except HTTPError as exc:
        try:
            parsed = json.loads(exc.read().decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            parsed = {"ok": False, "error": str(exc)}
        return int(exc.code), parsed if isinstance(parsed, dict) else {"ok": False, "error": "response_not_object"}
    except (URLError, TimeoutError) as exc:
        return 503, {
            "ok": False,
            "error": f"arena_server_unavailable:{type(exc).__name__}",
            "base_url": base_url,
            "remediation": "Start python -m aura_human_agent_arena_server",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aura live guarded Arena client")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("human-state", "Show Human Agent workflow state"),
        ("human-routes", "Show admitted Human Agent transitions"),
        ("coding-state", "Show Coding Workbench state"),
        ("coding-routes", "Show admitted Coding Workbench transitions"),
    ):
        sub.add_parser(name, help=help_text)

    human_command = sub.add_parser("human-command", help="Send a guarded Human Agent command")
    human_command.add_argument("text")
    human_command.add_argument("--payload", default="{}", help="JSON object")

    human_action = sub.add_parser("human-action", help="Request a guarded Human Agent action")
    human_action.add_argument("action_id")
    human_action.add_argument("--payload", default="{}", help="JSON object")

    coding_command = sub.add_parser("coding-command", help="Send a guarded Coding Workbench command")
    coding_command.add_argument("text")
    coding_command.add_argument("--payload", default="{}", help="JSON object")

    coding_action = sub.add_parser("coding-action", help="Request a guarded Coding Workbench action")
    coding_action.add_argument("action_id")
    coding_action.add_argument("--payload", default="{}", help="JSON object")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    endpoints = {
        "human-state": ("/api/human-agent/workflow", None),
        "human-routes": ("/api/human-agent/routes", None),
        "coding-state": ("/api/coding-workbench/state", None),
        "coding-routes": ("/api/coding-workbench/routes", None),
    }
    try:
        if args.command in endpoints:
            path, payload = endpoints[args.command]
        elif args.command == "human-command":
            path, payload = "/api/human-agent/workflow/command", {"command": args.text, "payload": _parse_payload(args.payload)}
        elif args.command == "human-action":
            path, payload = "/api/human-agent/workflow/action", {"action_id": args.action_id, "payload": _parse_payload(args.payload)}
        elif args.command == "coding-command":
            path, payload = "/api/coding-workbench/command", {"command": args.text, "payload": _parse_payload(args.payload)}
        else:
            path, payload = "/api/coding-workbench/action", {"action_id": args.action_id, "payload": _parse_payload(args.payload)}
    except (json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 2

    status, result = _request(args.base_url, path, payload)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    return 0 if 200 <= status < 300 and result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
