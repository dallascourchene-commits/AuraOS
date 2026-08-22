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
    InvalidContentType,
    ProviderSidecarReference,
    RedirectBlocked,
    ResponseTooLarge,
    SidecarStatus,
    StrictJsonTransport,
    StrictTLSFailure,
    _Circuit,
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


class _Response:
    def __init__(self, body: bytes, headers: dict[str, str]) -> None:
        self.body = body
        self.headers = headers
        self.read_calls = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, limit: int) -> bytes:
        self.read_calls += 1
        return self.body[:limit]


class _Opener:
    def __init__(self, result=None, error: BaseException | None = None) -> None:
        self.result = result
        self.error = error
        self.calls = 0

    def open(self, req, timeout):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


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

    def digest(self, messages=None, max_tokens=900, temperature=0.0):
        return ProviderSidecarReference.execution_digest(
            messages or [{"role": "user", "content": "hello"}],
            max_tokens=max_tokens,
            temperature=temperature,
        )

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

    def test_validate_route_ref_rejects_network_destination_markers(self):
        for route_ref in (
            "premium://",
            "premium/host",
            "premium\\host",
            "premium@deepseek",
        ):
            with self.assertRaises(ValueError):
                ProviderSidecarReference.validate_route_ref(route_ref)

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

    def test_strict_tls_failure_is_one_shot_and_never_insecure_retry(self):
        opener = _Opener(error=ssl.SSLError("certificate verify failed"))
        transport = StrictJsonTransport(opener=opener)
        with self.assertRaises(StrictTLSFailure):
            transport.post(
                "https://example.invalid/v1/chat/completions",
                {"model": "x", "messages": []},
                bearer=_SECRET,
                timeout=1.0,
            )
        self.assertEqual(opener.calls, 1)

    def test_redirect_is_blocked_without_following_destination(self):
        error = urllib.error.HTTPError(
            "https://api.deepseek.com/chat/completions",
            302,
            "redirect",
            {"Location": "https://attacker.invalid/capture"},
            None,
        )
        opener = _Opener(error=error)
        transport = StrictJsonTransport(opener=opener)
        with self.assertRaises(RedirectBlocked):
            transport.post(
                "https://api.deepseek.com/chat/completions",
                {"model": "x", "messages": []},
                bearer=_SECRET,
                timeout=1.0,
            )
        self.assertEqual(opener.calls, 1)

    def test_response_content_length_is_bounded_before_read(self):
        response = _Response(
            b'{}',
            {
                "Content-Type": "application/json",
                "Content-Length": "1000",
            },
        )
        transport = StrictJsonTransport(max_response_bytes=32, opener=_Opener(result=response))
        with self.assertRaises(ResponseTooLarge):
            transport.post(
                "https://api.deepseek.com/chat/completions",
                {"model": "x", "messages": []},
                bearer=_SECRET,
                timeout=1.0,
            )
        self.assertEqual(response.read_calls, 0)

    def test_response_body_is_bounded_even_without_content_length(self):
        response = _Response(
            b"{" + b"x" * 100 + b"}",
            {"Content-Type": "application/json"},
        )
        transport = StrictJsonTransport(max_response_bytes=32, opener=_Opener(result=response))
        with self.assertRaises(ResponseTooLarge):
            transport.post(
                "https://api.deepseek.com/chat/completions",
                {"model": "x", "messages": []},
                bearer=_SECRET,
                timeout=1.0,
            )
        self.assertEqual(response.read_calls, 1)

    def test_non_json_content_type_is_rejected_before_body_parse(self):
        response = _Response(b"not-json", {"Content-Type": "text/html"})
        transport = StrictJsonTransport(opener=_Opener(result=response))
        with self.assertRaises(InvalidContentType):
            transport.post(
                "https://api.deepseek.com/chat/completions",
                {"model": "x", "messages": []},
                bearer=_SECRET,
                timeout=1.0,
            )
        self.assertEqual(response.read_calls, 0)

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

    def test_attempt_identity_binds_lease_fence_currentness_and_execution(self):
        digest = self.digest()
        base = self.binding().attempt_id("premium", digest)
        self.assertEqual(base, self.binding().attempt_id("premium", digest))
        self.assertNotEqual(base, self.binding(lease_generation=5).attempt_id("premium", digest))
        self.assertNotEqual(base, self.binding(fencing_token="FENCE-10").attempt_id("premium", digest))
        self.assertNotEqual(base, self.binding(currentness_ref="SRC-new").attempt_id("premium", digest))
        self.assertNotEqual(base, self.binding().attempt_id("premium", self.digest(messages=[{"role": "user", "content": "different"}])))
        self.assertNotEqual(base, self.binding().attempt_id("premium", self.digest(max_tokens=901)))
        self.assertNotEqual(base, self.binding().attempt_id("premium", self.digest(temperature=0.25)))

    def test_dispatch_attempt_id_changes_when_execution_inputs_change(self):
        sidecar = ProviderSidecarReference(
            credential_resolver=_credentials,
            transport=_SuccessTransport(),
        )
        first = sidecar.dispatch(
            route_ref="premium",
            binding=self.binding(),
            messages=[{"role": "user", "content": "one"}],
            max_tokens=100,
            temperature=0.0,
        )
        second = sidecar.dispatch(
            route_ref="premium",
            binding=self.binding(),
            messages=[{"role": "user", "content": "two"}],
            max_tokens=100,
            temperature=0.0,
        )
        self.assertNotEqual(
            first.receipt.dispatch_attempt_id,
            second.receipt.dispatch_attempt_id,
        )
        self.assertNotEqual(first.receipt.execution_digest, second.receipt.execution_digest)

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

    def test_429_releases_half_open_probe_and_reopens_circuit(self):
        sidecar = ProviderSidecarReference(
            credential_resolver=_credentials,
            transport=_429Transport(),
            circuit_failure_threshold=1,
            circuit_cooldown_sec=0.0,
        )
        sidecar._circuits["deepseek"] = _Circuit(
            state=CircuitState.OPEN,
            failures=1,
            opened_at=0.0,
            half_open_probe_active=False,
        )
        result = sidecar.dispatch(
            route_ref="premium",
            binding=self.binding(),
            messages=[{"role": "user", "content": "probe"}],
            retry_budget=0,
        )
        self.assertEqual(result.receipt.status, SidecarStatus.RETRYABLE_PROVIDER_PRESSURE)
        circuit = sidecar._circuits["deepseek"]
        self.assertEqual(circuit.state, CircuitState.OPEN)
        self.assertFalse(circuit.half_open_probe_active)

    def test_circuit_state_introspection_is_side_effect_free(self):
        sidecar = ProviderSidecarReference(credential_resolver=_credentials)
        self.assertEqual(sidecar._circuits, {})
        self.assertEqual(sidecar._circuit_state("deepseek"), CircuitState.CLOSED)
        self.assertEqual(sidecar._circuits, {})

        circuit = _Circuit(
            state=CircuitState.OPEN,
            failures=3,
            opened_at=time.monotonic(),
            half_open_probe_active=False,
        )
        sidecar._circuits["deepseek"] = circuit
        before = (
            circuit.state,
            circuit.failures,
            circuit.opened_at,
            circuit.half_open_probe_active,
        )
        self.assertEqual(sidecar._circuit_state("deepseek"), CircuitState.OPEN)
        after = (
            circuit.state,
            circuit.failures,
            circuit.opened_at,
            circuit.half_open_probe_active,
        )
        self.assertEqual(before, after)

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
