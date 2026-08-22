from __future__ import annotations

import threading
import time
import unittest
import urllib.error

from tools.project006.provider_sidecar_reference.provider_sidecar import (
    CircuitState,
    DispatchBinding,
    ProviderSidecarReference,
    SidecarStatus,
)


_SECRET = "sk-test-DO-NOT-LEAK-1234567890"


def _credentials(provider: str, _cfg: dict) -> tuple[str, ...]:
    return (_SECRET,) if provider == "deepseek" else ()


def _binding(capsule_id: str) -> DispatchBinding:
    return DispatchBinding(
        capsule_id=capsule_id,
        lease_generation=4,
        fencing_token="FENCE-9",
        currentness_ref="SRC-1d05ee3e",
    )


class _ClientErrorTransport:
    def __init__(self, code: int = 400) -> None:
        self.code = code

    def post(self, endpoint, payload, *, bearer, timeout):
        raise urllib.error.HTTPError(endpoint, self.code, "client error", {}, None)


class _429RetryAfterTransport:
    def __init__(self, retry_after: str) -> None:
        self.retry_after = retry_after

    def post(self, endpoint, payload, *, bearer, timeout):
        raise urllib.error.HTTPError(
            endpoint,
            429,
            "pressure",
            {"Retry-After": self.retry_after},
            None,
        )


class ProviderSidecarRepairG3FollowupTests(unittest.TestCase):
    def test_queue_wait_deadline_expiry_is_timeout_not_queue_full(self):
        entered = threading.Event()
        release = threading.Event()

        class BlockingTransport:
            def post(self, endpoint, payload, *, bearer, timeout):
                entered.set()
                release.wait(timeout=2.0)
                return {"ok": True}

        sidecar = ProviderSidecarReference(
            credential_resolver=_credentials,
            transport=BlockingTransport(),
            concurrency_limit=1,
            queue_limit=1,
        )
        first_result: list = []
        worker = threading.Thread(
            target=lambda: first_result.append(
                sidecar.dispatch(
                    route_ref="premium",
                    binding=_binding("CAP-BLOCKING"),
                    messages=[{"role": "user", "content": "blocking"}],
                )
            )
        )
        worker.start()
        self.assertTrue(entered.wait(timeout=1.0))
        started = time.monotonic()
        waiting = sidecar.dispatch(
            route_ref="premium",
            binding=_binding("CAP-WAITING"),
            messages=[{"role": "user", "content": "waiting"}],
            total_deadline_sec=0.05,
            retry_budget=0,
        )
        elapsed = time.monotonic() - started
        self.assertEqual(waiting.receipt.status, SidecarStatus.TIMEOUT)
        self.assertGreaterEqual(elapsed, 0.04)
        release.set()
        worker.join(timeout=2.0)
        self.assertFalse(worker.is_alive())
        self.assertEqual(first_result[0].receipt.status, SidecarStatus.OK)

    def test_request_specific_4xx_does_not_poison_provider_circuit(self):
        sidecar = ProviderSidecarReference(
            credential_resolver=_credentials,
            transport=_ClientErrorTransport(400),
            circuit_failure_threshold=1,
        )
        first = sidecar.dispatch(
            route_ref="premium",
            binding=_binding("CAP-400-A"),
            messages=[{"role": "user", "content": "bad request"}],
            retry_budget=0,
        )
        second = sidecar.dispatch(
            route_ref="premium",
            binding=_binding("CAP-400-B"),
            messages=[{"role": "user", "content": "bad request again"}],
            retry_budget=0,
        )
        self.assertEqual(first.receipt.status, SidecarStatus.PROVIDER_UNAVAILABLE)
        self.assertEqual(second.receipt.status, SidecarStatus.PROVIDER_UNAVAILABLE)
        circuit = sidecar._circuits["deepseek"]
        self.assertEqual(circuit.state, CircuitState.CLOSED)
        self.assertEqual(circuit.failures, 0)
        self.assertFalse(circuit.half_open_probe_active)

    def test_non_finite_retry_after_is_ignored_without_escaping_typed_pressure(self):
        for value in ("Infinity", "NaN", "1e309"):
            sidecar = ProviderSidecarReference(
                credential_resolver=_credentials,
                transport=_429RetryAfterTransport(value),
            )
            result = sidecar.dispatch(
                route_ref="premium",
                binding=_binding(f"CAP-429-{value}"),
                messages=[{"role": "user", "content": "pressure"}],
                retry_budget=0,
            )
            self.assertEqual(
                result.receipt.status,
                SidecarStatus.RETRYABLE_PROVIDER_PRESSURE,
            )
            self.assertIsNone(result.receipt.retry_after_ms)


if __name__ == "__main__":
    unittest.main()