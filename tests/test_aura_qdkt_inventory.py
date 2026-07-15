from __future__ import annotations

import json

from aura_qdkt_compatibility_types import (
    QDKTInventoryReadiness,
    QDKTUseClass,
)
from aura_qdkt_inventory import scan_qdkt_uses, write_qdkt_inventory


def test_inventory_classifies_live_consumers_tests_archives_and_docs(tmp_path) -> None:
    (tmp_path / "consumer.py").write_text(
        "from quantum_dag import QuantumMerkleDAG\n"
        "import json\n"
        "async def run(node, handle):\n"
        "    dag = QuantumMerkleDAG(node)\n"
        "    result = await dag.generate_epistemic_system_root()\n"
        "    print(result['root'])\n"
        "    belief = result.get('belief')\n"
        "    json.dump(result, handle)\n"
        "    return belief\n",
        encoding="utf-8",
    )
    (tmp_path / "facade.py").write_text(
        "import json\n"
        "async def capture(generator, legacy_result, handle):\n"
        "    method = getattr(generator, 'generate_epistemic_system_root', None)\n"
        "    result = method()\n"
        "    root = legacy_result.get('root')\n"
        "    approval = {'state_snapshot': result, 'root': root}\n"
        "    json.dump(approval, handle)\n"
        "    return result, root\n",
        encoding="utf-8",
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_qdkt.py").write_text(
        "from quantum_dag import QuantumMerkleDAG\n"
        "def test_constructor(node):\n"
        "    assert QuantumMerkleDAG(node)\n",
        encoding="utf-8",
    )
    (tmp_path / "aura_node.py.save").write_text(
        "from quantum_dag import QuantumMerkleDAG\n"
        "dag = QuantumMerkleDAG(None)\n",
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "qdkt.md").write_text(
        "QuantumMerkleDAG exposes generate_epistemic_system_root.\n",
        encoding="utf-8",
    )

    report = scan_qdkt_uses(tmp_path)
    classes = {item.use_class for item in report.entries}
    assert {
        QDKTUseClass.IMPORT,
        QDKTUseClass.CONSTRUCTOR,
        QDKTUseClass.METHOD_CALL,
        QDKTUseClass.ROOT_CONSUMER,
        QDKTUseClass.BELIEF_CONSUMER,
        QDKTUseClass.PERSISTENCE,
        QDKTUseClass.DISPLAY,
        QDKTUseClass.TEST,
        QDKTUseClass.DOCUMENTATION,
    } <= classes
    facade_calls = [
        item
        for item in report.entries
        if item.file_path == "facade.py" and item.use_class is QDKTUseClass.METHOD_CALL
    ]
    assert len(facade_calls) == 2
    facade_persistence = [
        item
        for item in report.entries
        if item.file_path == "facade.py" and item.use_class is QDKTUseClass.PERSISTENCE
    ]
    assert len(facade_persistence) == 1
    archive = [item for item in report.entries if item.file_path.endswith(".save")]
    assert archive
    assert all(item.readiness is QDKTInventoryReadiness.ARCHIVAL_ONLY for item in archive)
    test_entries = [item for item in report.entries if item.file_path.startswith("tests/")]
    assert test_entries
    assert all(item.readiness is QDKTInventoryReadiness.TEST_ONLY for item in test_entries)


def test_inventory_is_deterministic_canonical_and_ignores_its_output(tmp_path) -> None:
    (tmp_path / "quantum_dag.py").write_text(
        "class QuantumMerkleDAG:\n"
        "    async def generate_epistemic_system_root(self):\n"
        "        return {'root': 'A', 'belief': 1}\n",
        encoding="utf-8",
    )
    first = scan_qdkt_uses(tmp_path)
    second = scan_qdkt_uses(tmp_path)
    assert first == second
    assert first.digest == second.digest
    assert any(
        item.use_class is QDKTUseClass.GENERATOR_DEFINITION
        for item in first.entries
    )

    output = write_qdkt_inventory(first, tmp_path / "qdkt-p6-2-inventory.json")
    text = output.read_text(encoding="utf-8")
    assert text.endswith("\n")
    payload = json.loads(text)
    assert payload == first.to_dict()
    third = scan_qdkt_uses(tmp_path)
    assert third == first
    assert third.digest == first.digest


def test_inventory_never_imports_or_executes_scanned_code(tmp_path) -> None:
    marker = tmp_path / "executed"
    (tmp_path / "danger.py").write_text(
        "from quantum_dag import QuantumMerkleDAG\n"
        f"open({str(marker)!r}, 'w').write('bad')\n",
        encoding="utf-8",
    )
    report = scan_qdkt_uses(tmp_path)
    assert report.entries
    assert not marker.exists()
