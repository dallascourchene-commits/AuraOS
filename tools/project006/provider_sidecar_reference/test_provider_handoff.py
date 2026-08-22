from __future__ import annotations

import json
import unittest

from tools.project006.provider_sidecar_reference.provider_handoff import (
    HANDOFF_VERSION,
    HandoffError,
    dispatch_handoff,
    validate_handoff,
)
from tools.project006.provider_sidecar_reference.provider_sidecar import (
    ProviderSidecarReference,
)


_SECRET = "sk-test-provider-handoff-never-emit"


def _credentials(provider: str, _cfg: dict) -> tuple[str, ...]:
    return (_SECRET,) if provider == "deepseek" else ()


class _SuccessTransport:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def post(self, endpoint, payload, *, bearer, timeout):
        self.calls.append(
            {
                "endpoint": endpoint,
                "payload": payload,
                "bearer": bearer,
                "timeout": timeout,
            }
        )
        return {
            "id": "provider-request-test",
            "choices": [{"message": {"content": "handoff-ok"}}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 3},
        }


def _handoff() -> dict:
    return {
        "handoff_version": HANDOFF_VERSION,
        "root_dispatch_id": "dispatch-c81-canary-0001",
        "dispatch_generation": 0,
        "intent_digest": "a" * 64,
        "validation_receipt_ref": "WP06-PRE-HANDOFF-RECEIPT-0001",
        "route_ref": "premium",
        "capsule_id": "capsule-c81-canary-0001",
        "lease_generation": 7,
        "fencing_token": "private-fence-0007",
        "currentness_ref": "currentness-c81-0001",
        "messages": [{"role": "user", "content": "Return exactly: handoff-ok"}],
        "max_tokens": 32,
        "temperature_milli": 0,
        "deadline_ms": 10_000,
        "retry_budget": 0,
    }


class ProviderHandoffTests(unittest.TestCase):
    def test_valid_handoff_executes_provider_sidecar_and_binds_receipt(self) -> None:
        transport = _SuccessTransport()
        sidecar = ProviderSidecarReference(
            credential_resolver=_credentials,
            transport=transport,
            concurrency_limit=1,
            queue_limit=0,
        )

        receipt = dispatch_handoff(_handoff(), sidecar=sidecar)

        self.assertEqual(receipt["provider_attempt_status"], "OK")
        self.assertEqual(receipt["root_dispatch_id"], "dispatch-c81-canary-0001")
        self.assertEqual(receipt["dispatch_generation"], 0)
        self.assertEqual(receipt["lease_generation"], 7)
        self.assertEqual(receipt["provider_receipt"]["provider"], "deepseek")
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(transport.calls[0]["bearer"], _SECRET)
        self.assertEqual(
            transport.calls[0]["payload"]["messages"][0]["content"],
            "Return exactly: handoff-ok",
        )
        rendered = json.dumps(receipt, sort_keys=True)
        self.assertNotIn(_SECRET, rendered)
        self.assertNotIn("private-fence-0007", rendered)
        self.assertIsNotNone(receipt["handoff_digest"])
        self.assertIsNotNone(receipt["response_digest"])

    def test_missing_lease_generation_fails_closed_before_provider_call(self) -> None:
        transport = _SuccessTransport()
        sidecar = ProviderSidecarReference(
            credential_resolver=_credentials,
            transport=transport,
        )
        handoff = _handoff()
        del handoff["lease_generation"]

        with self.assertRaisesRegex(HandoffError, "HANDOFF_MISSING_REQUIRED_FIELD"):
            dispatch_handoff(handoff, sidecar=sidecar)
        self.assertEqual(transport.calls, [])

    def test_missing_validation_receipt_fails_closed(self) -> None:
        handoff = _handoff()
        del handoff["validation_receipt_ref"]
        with self.assertRaisesRegex(HandoffError, "HANDOFF_MISSING_REQUIRED_FIELD"):
            validate_handoff(handoff)

    def test_arbitrary_endpoint_or_credential_field_is_rejected(self) -> None:
        for field, value in (
            ("provider_url", "https://evil.example/v1/chat"),
            ("api_key", "secret"),
        ):
            with self.subTest(field=field):
                handoff = _handoff()
                handoff[field] = value
                with self.assertRaisesRegex(HandoffError, "HANDOFF_UNKNOWN_FIELD"):
                    validate_handoff(handoff)

    def test_fencing_token_changes_handoff_and_provider_attempt_identity(self) -> None:
        first_transport = _SuccessTransport()
        second_transport = _SuccessTransport()
        first_sidecar = ProviderSidecarReference(
            credential_resolver=_credentials,
            transport=first_transport,
        )
        second_sidecar = ProviderSidecarReference(
            credential_resolver=_credentials,
            transport=second_transport,
        )
        first = _handoff()
        second = _handoff()
        second["fencing_token"] = "private-fence-0008"

        first_receipt = dispatch_handoff(first, sidecar=first_sidecar)
        second_receipt = dispatch_handoff(second, sidecar=second_sidecar)

        self.assertNotEqual(first_receipt["handoff_digest"], second_receipt["handoff_digest"])
        self.assertNotEqual(
            first_receipt["provider_receipt"]["dispatch_attempt_id"],
            second_receipt["provider_receipt"]["dispatch_attempt_id"],
        )

    def test_message_change_changes_provider_attempt_identity(self) -> None:
        first_sidecar = ProviderSidecarReference(
            credential_resolver=_credentials,
            transport=_SuccessTransport(),
        )
        second_sidecar = ProviderSidecarReference(
            credential_resolver=_credentials,
            transport=_SuccessTransport(),
        )
        first = _handoff()
        second = _handoff()
        second["messages"] = [{"role": "user", "content": "different execution"}]

        first_receipt = dispatch_handoff(first, sidecar=first_sidecar)
        second_receipt = dispatch_handoff(second, sidecar=second_sidecar)
        self.assertNotEqual(
            first_receipt["provider_receipt"]["dispatch_attempt_id"],
            second_receipt["provider_receipt"]["dispatch_attempt_id"],
        )


if __name__ == "__main__":
    unittest.main()
