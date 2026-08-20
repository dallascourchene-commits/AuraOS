from __future__ import annotations

import json
import ssl
import threading
import time
import unittest
from unittest import mock
import urllib.error

from tools.project006.provider_sidecar_reference.provider_sidecar import (
    CircuitState,
    DispatchBinding,
    ProviderSidecarReference,
    SidecarStatus,
    StrictJsonTransport,
)


_SECRET = "sk-test-DO-NOT-LEAK-1234567890"


def _credentials(provider: str, _cfg: dict) -> tuple[str, ...]:
    return (_SECRET,) if provider == "deepseek" else ()


class _SuccessTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def post(self, endpoint, payload, *, bearer, timeout):
        self.calls.append((endpoint, bearer))
        return {"choices": [{"message": {"content": "ok"}}]}


class _429Transport:
    def post(self, endpoint, payload, *, bearer, timeout):
        raise urllib.error.HTTPError(endpoint, 429, "pressure", {}, None)


class _UnavailableTransport:
    def post(self, endpoint, payload, *, bearer, timeout):
        raise urllib.error.HTTPError(endpoint, 503, "unavailable", {}, None)


class ProviderSidecarReferenceTests(unittest.TestCase):
    def binding(self, **overrides):
        values = {
            "capsule_id": "CAP-1",
            "lease_generation": 4,
            "fencing_token": "FENCE-9",
            "currentness_ref": "SRC-50ef5c3",
        }
        values.update(overrides)
        return DispatchBinding(**values)

    def test_route_ref_cannot_be_url_host_or_arbitrary_provider(self):
        sidecar = ProviderSidecarReference(credential_resolver=_credentials)
        for route_ref in (
            "https://api.deepseek.com/chat/completions",
            "api.deepseek.com/path",
            "deepseek",
            "127.0.0.1",
            "user@example.com",
        ):
            result = sidecar.dispatch(
                route_ref=route_ref,
                binding=self.binding(),
                messages=[{"role": "user", "content": "hello"}],
            )
            self.assertEqual(result.receipt.status, SidecarStatus.INVALID_ROUTE)

    def test_logical_premium_route_resolves_registry_owned_deepseek(self):
        transport = _SuccessTransport()
        sidecar = ProviderSidecarReference(
            credential_resolver=_credentials,
            transport=transport,
        )
        result = sidecar.dispatch(
            route_ref="premium",
            binding=self.binding(),
            messages=[{"role": "user", "content": "hello"}],
        )
        self.assertEqual(result.receipt.status, SidecarStatus.OK)
        self.assertEqual(result.receipt.provider, "deepseek")
        self.assertEqual(result.receipt.model, "deepseek-v4-pro")
        self.assertEqual(result.receipt.fallback_index, 0)
        self.assertEqual(transport.calls[0][0], "https://api.deepseek.com/chat/completions")

    def test_strict_tls_failure_never_retries_with_disabled_verification(self):
        transport = StrictJsonTransport()
        with mock.patch(
            "urllib.request.urlopen",
            side_effect=ssl.SSLError("certificate verify failed"),
        ) as urlopen:
            with self.assertRaises(Exception) as raised:
                transport.post(
                    "https://example.invalid/v1/chat/completions",
                    {"model": "x", "messages": []},
                    bearer=_SECRET,
                    timeout=1.0,
                )
        self.assertEqual(raised.exception.__class__.__name__, "StrictTLSFailure")
        self.assertEqual(urlopen.call_count, 1)
        self.assertNotIn("context", urlopen.call_args.kwargs)

    def test_health_and_receipts_contain_zero_credential_material(self):
        transport = _SuccessTransport()
        sidecar = ProviderSidecarReference(
            credential_resolver=_credentials,
            transport=transport,
        )
        health = sidecar.health_report("premium")
        result = sidecar.dispatch(
            route_ref="premium",
            binding=self.binding(),
            messages=[{"role": "user", "content": "hello"}],
        )
        serialized = json.dumps(
            {"health": health, "receipt": result.receipt.to_jsonable()},
            sort_keys=True,
        )
        forbidden_fragments = {
            _SECRET,
            _SECRET[:4],
            _SECRET[-4:],
            _SECRET[:8],
            _SECRET[-8:],
        }
        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, serialized)
        deepseek = next(p for p in health["providers"] if p["provider"] == "deepseek")
        self.assertTrue(deepseek["configured"])
        self.assertEqual(deepseek["key_count"], 1)
        self.assertNotIn("api_key", deepseek)

    def test_attempt_identity_binds_lease_fence_and_currentness(self):
        base = self.binding().attempt_id("premium")
        self.assertEqual(base, self.binding().attempt_id("premium"))
        self.assertNotEqual(base, self.binding(lease_generation=5).attempt_id("premium"))
        self.assertNotEqual(base, self.binding(fencing_token="FENCE-10").attempt_id("premium"))
        self.assertNotEqual(base, self.binding(currentness_ref="SRC-new").attempt_id("premium"))

    def test_429_is_provider_pressure_not_key_rotation_capacity(self):
        calls: list[str] = []

        def two_keys(provider: str, _cfg: dict):
            if provider == "deepseek":
                calls.append(provider)
                return (_SECRET, "second-key-that-must-not-be-used-as-extra-capacity")
            return ()

        sidecar = ProviderSidecarReference(
            credential_resolver=two_keys,
            transport=_429Transport(),
        )
        result = sidecar.dispatch(
            route_ref="premium",
            binding=self.binding(),
            messages=[{"role": "user", "content": "hello"}],
            retry_budget=4,
        )
        self.assertEqual(result.receipt.status, SidecarStatus.RETRYABLE_PROVIDER_PRESSURE)
        self.assertEqual(result.receipt.attempts, 1)
        self.assertEqual(calls, ["deepseek"])

    def test_queue_bound_fails_closed_when_capacity_is_occupied(self):
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
            queue_limit=0,
        )
        first_result: list = []

        worker = threading.Thread(
            target=lambda: first_result.append(
                sidecar.dispatch(
                    route_ref="premium",
                    binding=self.binding(capsule_id="CAP-FIRST"),
                    messages=[{"role": "user", "content": "first"}],
                )
            )
        )
        worker.start()
        self.assertTrue(entered.wait(timeout=1.0))
        second = sidecar.dispatch(
            route_ref="premium",
            binding=self.binding(capsule_id="CAP-SECOND"),
            messages=[{"role": "user", "content": "second"}],
            total_deadline_sec=0.2,
        )
        self.assertEqual(second.receipt.status, SidecarStatus.QUEUE_FULL)
        release.set()
        worker.join(timeout=2.0)
        self.assertFalse(worker.is_alive())
        self.assertEqual(first_result[0].receipt.status, SidecarStatus.OK)

    def test_circuit_opens_and_blocks_until_cooldown(self):
        sidecar = ProviderSidecarReference(
            credential_resolver=_credentials,
            transport=_UnavailableTransport(),
            circuit_failure_threshold=1,
            circuit_cooldown_sec=60.0,
        )
        first = sidecar.dispatch(
            route_ref="premium",
            binding=self.binding(capsule_id="CAP-A"),
            messages=[{"role": "user", "content": "a"}],
            retry_budget=0,
        )
        self.assertIn(
            first.receipt.status,
            (SidecarStatus.PROVIDER_UNAVAILABLE, SidecarStatus.CIRCUIT_OPEN),
        )
        self.assertEqual(first.receipt.circuit_state, CircuitState.OPEN)
        second = sidecar.dispatch(
            route_ref="premium",
            binding=self.binding(capsule_id="CAP-B"),
            messages=[{"role": "user", "content": "b"}],
            retry_budget=0,
        )
        self.assertEqual(second.receipt.status, SidecarStatus.CIRCUIT_OPEN)


if __name__ == "__main__":
    unittest.main()
