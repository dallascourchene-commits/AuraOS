from __future__ import annotations

from pathlib import Path


def replace_required(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"core hardening target not found: {label}")
    return text.replace(old, new)


def main() -> None:
    path = Path("aura_emergent_evidence_spine.py")
    text = path.read_text(encoding="utf-8")

    text = replace_required(
        text,
        "from dataclasses import asdict, dataclass",
        "from dataclasses import dataclass",
        "unused asdict import",
    )
    text = replace_required(
        text,
        "    CodeTopoEdge,\n",
        "",
        "unused CodeTopoEdge import",
    )
    text = replace_required(
        text,
        '        value: Mapping[str, Any] | "EmergentEvidenceRequest",',
        "        value: Mapping[str, Any] | EmergentEvidenceRequest,",
        "quoted request annotation",
    )
    text = replace_required(
        text,
        "        except Exception as exc:  # noqa: BLE001 - sanitized fail-closed facade",
        "        except Exception as exc:",
        "unused BLE001 directive",
    )

    old_tests = '''def _tests_for_nodes(
    anchor: CodeTopoAnchor,
    node_ids: Sequence[str],
    repo_root: Path,
) -> list[str]:
    tests: list[str] = []
    try:
        tests.extend(anchor._tests_for_nodes(list(node_ids)))  # noqa: SLF001 - no public batch accessor
    except Exception:
        pass
    for node_id in node_ids:
        node = anchor.nodes.get(node_id)
        if node is None:
            continue
        path = PurePosixPath(node.file_path)
        candidates = (
            path.parent / f"test_{path.name}",
            PurePosixPath("tests") / f"test_{path.name}",
        )
        for candidate in candidates:
            if (repo_root / candidate).is_file():
                tests.append(candidate.as_posix())
    return sorted(dict.fromkeys(tests))
'''
    new_tests = '''def _tests_for_nodes(
    anchor: CodeTopoAnchor,
    node_ids: Sequence[str],
    repo_root: Path,
) -> list[str]:
    target_files = {
        anchor.nodes[node_id].file_path
        for node_id in node_ids
        if node_id in anchor.nodes
    }
    if not target_files:
        return []
    tests: set[str] = set()
    target_module_ids = {
        anchor.module_nodes.get(file_path)
        for file_path in target_files
    }
    target_module_ids.discard(None)
    for edge in anchor.edges:
        if edge.edge_type != "test":
            continue
        targets_selected_module = edge.dst_id in target_module_ids
        targets_selected_file = (
            edge.dst_id in anchor.nodes
            and anchor.nodes[edge.dst_id].file_path in target_files
        )
        if not (targets_selected_module or targets_selected_file):
            continue
        source = anchor.nodes.get(edge.src_id)
        if source is not None:
            tests.add(source.file_path)
    for file_path in target_files:
        path = PurePosixPath(file_path)
        candidates = (
            path.parent / f"test_{path.name}",
            PurePosixPath("tests") / f"test_{path.name}",
        )
        for candidate in candidates:
            candidate_text = candidate.as_posix()
            if candidate_text in anchor.source_texts or (repo_root / candidate).is_file():
                tests.add(candidate_text)
    return sorted(tests)
'''
    text = replace_required(
        text,
        old_tests,
        new_tests,
        "deterministic test discovery",
    )

    old_paths = '''def _repo_paths(values: Any) -> tuple[str, ...]:
    result: list[str] = []
    for value in _sequence(values):
        normalized = _normalize_repo_path(value)
        if normalized and normalized not in result:
            result.append(normalized)
    return tuple(result)
'''
    new_paths = '''def _repo_paths(values: Any) -> tuple[str, ...]:
    result: list[str] = []
    for value in _sequence(values):
        raw = str(value or "").strip()
        normalized = _normalize_repo_path(value)
        if raw and not normalized:
            raise ValueError("repository paths must be relative and may not escape the repository")
        if normalized and normalized not in result:
            result.append(normalized)
    return tuple(result)
'''
    text = replace_required(
        text,
        old_paths,
        new_paths,
        "fail-closed repository paths",
    )

    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
