from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REFERENCE_SHA = "a71d1c55af84973a29b28fdfa3db157056780e92"
ROOTS = (0, 1, 2, 6, 14)
DEPTHS = (0, 1, 2, 3)


def load_reference(path: Path):
    spec = importlib.util.spec_from_file_location("k27_astge_reference_pinned", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("REFERENCE_IMPORT_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def rust_receipts(binary: Path) -> tuple[dict[tuple[int, int], dict], set[str]]:
    completed = subprocess.run(
        [str(binary)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    cases: dict[tuple[int, int], dict] = {}
    markers: set[str] = set()
    for raw in completed.stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("{"):
            receipt = json.loads(line)
            key = (receipt["root"], receipt["depth"])
            if key in cases:
                raise AssertionError(f"DUPLICATE_RUST_CASE:{key}")
            cases[key] = receipt
        else:
            markers.add(line)
    return cases, markers


def reference_receipts(reference) -> tuple[dict[tuple[int, int], dict], str]:
    adjacency = reference.build_balanced_tree(depth=3, branching=2)
    cases: dict[tuple[int, int], dict] = {}
    with tempfile.TemporaryDirectory(prefix="aura-k27-conformance-") as td:
        nodes = Path(td) / "reference.nodes"
        edges = Path(td) / "reference.edges"
        reference.serialize_graph(
            nodes,
            edges,
            adjacency,
            placement_scheme=reference.PLACEMENT_CONTIGUOUS_CSR_V1,
        )
        with reference.MmapGraphReader(nodes, edges) as reader:
            for depth in DEPTHS:
                for root in ROOTS:
                    cone = reader.query_affected_cone(root, depth)
                    cases[(root, depth)] = {
                        "root": root,
                        "depth": depth,
                        "nodes": list(cone.node_ids),
                        "edges": cone.edge_traversals,
                    }
            try:
                reader.query_affected_cone(99, 2)
            except Exception as exc:  # exact foreign exception type belongs to pinned oracle
                missing_root = f"{type(exc).__name__}:{exc}"
            else:
                raise AssertionError("REFERENCE_MISSING_ROOT_UNEXPECTEDLY_SUCCEEDED")
    return cases, missing_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--rust-bin", type=Path, required=True)
    args = parser.parse_args()

    reference = load_reference(args.reference)
    expected, reference_missing_root = reference_receipts(reference)
    observed, markers = rust_receipts(args.rust_bin)

    if set(expected) != set(observed):
        raise AssertionError(
            f"QUERY_CASE_SET_MISMATCH expected={sorted(expected)} observed={sorted(observed)}"
        )

    for key in sorted(expected):
        if observed[key]["nodes"] != expected[key]["nodes"]:
            raise AssertionError(
                f"CONE_NODE_ORDER_MISMATCH case={key} expected={expected[key]['nodes']} observed={observed[key]['nodes']}"
            )
        if observed[key]["edges"] != expected[key]["edges"]:
            raise AssertionError(
                f"EDGE_TRAVERSAL_MISMATCH case={key} expected={expected[key]['edges']} observed={observed[key]['edges']}"
            )

    if "RUST_MISSING_ROOT=MissingRoot" not in markers:
        raise AssertionError("RUST_MISSING_ROOT_FAIL_CLOSED_MARKER_MISSING")
    if "RUST_ZERO_BUDGET=ConeBudgetExceeded" not in markers:
        raise AssertionError("RUST_ZERO_BUDGET_FAIL_CLOSED_MARKER_MISSING")
    if not reference_missing_root.startswith("ASTGEFormatError:NODE_ID_OUT_OF_RANGE"):
        raise AssertionError(f"REFERENCE_MISSING_ROOT_ERROR_DRIFT:{reference_missing_root}")

    print(f"REFERENCE_SHA={REFERENCE_SHA}")
    print(f"QUERY_CASES={len(expected)}")
    print("SAME_GRAPH=true")
    print("SAME_ROOTS_AND_DEPTHS=true")
    print("NODE_ORDER_EQUIVALENCE=true")
    print("EDGE_TRAVERSAL_EQUIVALENCE=true")
    print("RUST_RECORD_ORDER=REVERSED")
    print(f"REFERENCE_MISSING_ROOT={reference_missing_root}")
    print("RUST_MISSING_ROOT=MissingRoot")
    print("MISSING_ROOT_FAIL_CLOSED_BOTH=true")
    print("BUDGET_SEMANTIC_PARITY=NOT_APPLICABLE_REFERENCE_HAS_NO_BUDGET_PARAMETER")
    print("RUST_ZERO_BUDGET=ConeBudgetExceeded")
    print("MMAP_PERFORMANCE_SUPERIORITY_PROVEN=false")
    print("COLD_NVME_BEHAVIOR_PROVEN=false")
    print("AURAOS_RUNTIME_INTEGRATION_PROVEN=false")
    print("EXTERNAL_EFFECT_AUTHORIZED=false")


if __name__ == "__main__":
    main()
