from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "test_aura_functions.py"

DAG_OLD = '''def _test_dag_simple():
    # execute_dag_plan() reads JSON from stdin — test via JSON roundtrip
    plan = {
        "nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
        "edges": [{"source": "A", "target": "B"}, {"source": "B", "target": "C"}]
    }
    old_stdin = sys.stdin
    sys.stdin = io.StringIO(json.dumps(plan))
    try:
        execute_dag_plan()
        result = True
    except SystemExit:
        result = True
    except Exception as e:
        result = False
    finally:
        sys.stdin = old_stdin
    assert result
'''

DAG_NEW = '''def _test_dag_simple():
    # Exercise the actual binary IPC contract: 16-byte activator, little-endian
    # payload length, then JSON bytes with canonical from/to edges.
    import struct
    plan = {
        "nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
        "edges": [{"from": "A", "to": "B"}, {"from": "B", "to": "C"}],
    }
    payload = json.dumps(plan, separators=(",", ":")).encode("utf-8")
    stream = io.BytesIO(b"AURA-ACTIVATOR!!" + struct.pack("<I", len(payload)) + payload)
    old_stdin, old_stdout = sys.stdin, sys.stdout
    sys.stdin = io.TextIOWrapper(stream, encoding="utf-8")
    captured = io.StringIO()
    sys.stdout = captured
    try:
        execute_dag_plan()
    finally:
        sys.stdout = old_stdout
        sys.stdin = old_stdin
    result = json.loads(captured.getvalue())
    assert result == {"status": "success", "execution_path": ["A", "B", "C"]}
'''

HEAP_OLD = '''def _test_heap_snapshot():
    snap = heap_snapshot()
    assert isinstance(snap, dict)
'''

HEAP_NEW = '''def _test_heap_snapshot():
    # heap_snapshot() deliberately walks every GC-tracked object.  Validate it
    # in a clean child interpreter so this omnibus smoke harness does not turn
    # the check into an accidental full-process heap stress benchmark.
    import subprocess
    probe = (
        "from pvm_memory_guard import heap_snapshot; "
        "s=heap_snapshot(); assert isinstance(s, dict); print(len(s))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=str(Path(__file__).resolve().parent),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    text = replace_once(text, DAG_OLD, DAG_NEW, "DAG smoke")
    text = replace_once(text, HEAP_OLD, HEAP_NEW, "heap smoke")
    TARGET.write_text(text, encoding="utf-8")
    print("WC-02 standalone smoke contracts aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
