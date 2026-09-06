import importlib
import sys
import tempfile
import unittest
from pathlib import Path

from process_isolation_membrane import (
    DedicatedProcessService,
    WorkerProtocolError,
    factory_identity_currentness,
    factory_origin_for_spec,
    preimport_factory_identity,
)


class ReviewRepairTests(unittest.TestCase):
    def test_preimport_identity_drift_is_detected_without_import_side_effect(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            module_name = "_aura_preimport_side_effect_fixture"
            path = root / f"{module_name}.py"
            marker = root / "executed.marker"
            path.write_text("class Factory:\n    pass\n")
            sys.path.insert(0, td)
            try:
                importlib.invalidate_caches()
                expected_origin = factory_origin_for_spec(f"{module_name}:Factory")
                expected = preimport_factory_identity(f"{module_name}:Factory", expected_origin)
                path.write_text(
                    "from pathlib import Path\n"
                    f"Path({str(marker)!r}).write_text('executed')\n"
                    "class Factory:\n    pass\n"
                )
                importlib.invalidate_caches()
                current = preimport_factory_identity(f"{module_name}:Factory", expected_origin)
                self.assertEqual(factory_identity_currentness(expected, current), "HOLD")
                self.assertFalse(marker.exists())
                self.assertNotIn(module_name, sys.modules)
            finally:
                sys.path.remove(td)
                sys.modules.pop(module_name, None)

    def test_non_spawn_start_method_fails_closed(self):
        for method in ("fork", "forkserver"):
            with self.subTest(method=method):
                with self.assertRaisesRegex(WorkerProtocolError, "UNSUPPORTED_START_METHOD"):
                    DedicatedProcessService.start(
                        "process_isolation_membrane:IsolationProbe",
                        start_method=method,
                    )

    def test_timeout_poisons_service_and_prevents_late_response_reuse(self):
        service = DedicatedProcessService.start("process_isolation_membrane:IsolationProbe")
        service._call_timeout_seconds = 0.05
        try:
            with self.assertRaisesRegex(WorkerProtocolError, "WORKER_CALL_TIMEOUT"):
                service.call("delayed_value", 0.25, "late")
            self.assertTrue(service._closed)
            self.assertFalse(service._process.is_alive())
            with self.assertRaisesRegex(WorkerProtocolError, "SERVICE_CLOSED"):
                service.call("increment", 1)
        finally:
            service.close()


if __name__ == "__main__":
    unittest.main()
