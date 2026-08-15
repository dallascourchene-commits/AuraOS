from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_codebase_navigator.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '''            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):\n                signature = _symbol_signature(child)\n                kind = "method" if scope else "function"\n''',
        '''            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):\n                signature = _symbol_signature(child)\n                kind = (\n                    "method"\n                    if scope\n                    else ("async_function" if isinstance(child, ast.AsyncFunctionDef) else "function")\n                )\n''',
        "async symbol identity",
    )

    text = replace_once(
        text,
        '''    if absolute.exists() and not refresh:\n        try:\n            existing = json.loads(absolute.read_text(encoding="utf-8"))\n        except (OSError, json.JSONDecodeError):\n            existing = None\n        if isinstance(existing, dict) and is_deep(existing):\n            return existing, "compiled_deep_topology"\n''',
        '''    if absolute.exists() and not refresh:\n        try:\n            existing = json.loads(absolute.read_text(encoding="utf-8"))\n        except (OSError, json.JSONDecodeError):\n            existing = None\n        if isinstance(existing, dict) and _topology_file_index(existing):\n            source = (\n                "compiled_deep_topology"\n                if is_deep(existing)\n                else "existing_source_indexable_topology"\n            )\n            return existing, source\n''',
        "explicit no-refresh topology reuse",
    )

    text = replace_once(
        text,
        "def refresh_index_for_paths(\n    payload: dict[str, Any],\n",
        "def _refresh_index_payload_for_paths(\n    payload: dict[str, Any],\n",
        "payload refresh implementation rename",
    )

    marker = "\n\ndef _command_index(cards: list[dict[str, Any]]) -> dict[str, list[str]]:\n"
    wrapper = '''\n\ndef refresh_index_for_paths(\n    payload_or_index: dict[str, Any] | str | Path,\n    root_or_changed: Path | list[str | Path],\n    changed_paths: list[str | Path] | None = None,\n    *,\n    root: Path | None = None,\n    topology: dict[str, Any] | None = None,\n    include_topology: bool = True,\n    topology_path: Path = DEFAULT_TOPOLOGY_PATH,\n    refresh_topology: bool = False,\n    write_index: bool = True,\n) -> dict[str, Any]:\n    """Refresh paths using the historical or current public calling form.\n\n    Historical: ``refresh_index_for_paths(index_path, changed_paths, root=...)``.\n    Current: ``refresh_index_for_paths(payload, root, changed_paths, topology=...)``.\n    """\n    if isinstance(payload_or_index, (str, Path)):\n        index_path = Path(payload_or_index)\n        legacy_changed = (\n            list(root_or_changed)\n            if isinstance(root_or_changed, list)\n            else [root_or_changed]\n        )\n        payload = _load_json(index_path)\n        repo_root = (root or Path(str(payload.get("root") or "."))).resolve()\n        resolved_topology = topology\n        if resolved_topology is None and include_topology:\n            resolved_topology, _ = load_or_compile_topology(\n                repo_root,\n                topology_path=topology_path,\n                refresh=refresh_topology,\n            )\n        refreshed = _refresh_index_payload_for_paths(\n            payload, repo_root, legacy_changed, topology=resolved_topology\n        )\n        refreshed_paths: list[str] = []\n        removed_paths: list[str] = []\n        for raw in legacy_changed:\n            candidate = Path(raw)\n            absolute = candidate if candidate.is_absolute() else repo_root / candidate\n            try:\n                rel = absolute.resolve().relative_to(repo_root).as_posix()\n            except (OSError, ValueError):\n                continue\n            (refreshed_paths if absolute.exists() else removed_paths).append(rel)\n        refreshed["last_refresh"] = {\n            "mode": "incremental_ast_hook",\n            "refreshed_paths": sorted(set(refreshed_paths)),\n            "removed_paths": sorted(set(removed_paths)),\n            "changed_path_count": len(set(refreshed_paths + removed_paths)),\n            "topology_refreshed": bool(refresh_topology),\n        }\n        if write_index:\n            markdown_path = repo_root / DEFAULT_MARKDOWN_PATH\n            write_navigation_artifacts(refreshed, index_path, markdown_path)\n        return refreshed\n\n    if changed_paths is None:\n        raise TypeError("current refresh form requires changed_paths")\n    if not isinstance(root_or_changed, Path):\n        raise TypeError("current refresh form requires a Path root")\n    return _refresh_index_payload_for_paths(\n        payload_or_index, root_or_changed, changed_paths, topology=topology\n    )\n'''
    if wrapper.strip() not in text:
        if text.count(marker) != 1:
            raise RuntimeError("refresh wrapper insertion marker mismatch")
        text = text.replace(marker, wrapper + marker, 1)

    TARGET.write_text(text, encoding="utf-8")
    print("WC-02 navigator refresh/topology/async semantics applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
