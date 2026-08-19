from __future__ import annotations

import sqlite3
import time

import pytest

from aura_custodian_drive_event_adapter import (
    CursorConflictError,
    CustodianDriveEventAdapter,
    EventEnvelope,
    SQLiteCustodianEventStore,
    normalize_drive_change,
    normalize_workspace_event,
)


class FakeDriveClient:
    def __init__(self, pages, *, start_token="start-1"):
        self.pages = dict(pages)
        self.start_token = start_token
        self.calls = []
        self.start_calls = 0

    def get_start_page_token(self):
        self.start_calls += 1
        return self.start_token

    def list_changes(self, page_token):
        self.calls.append(page_token)
        return self.pages[page_token]


def test_workspace_event_normalizes_without_resource_hydration():
    envelope = normalize_workspace_event(
        {
            "id": "evt-1",
            "type": "google.workspace.drive.file.v3.updated",
            "subject": "//drive.googleapis.com/files/file-123",
            "time": "2026-08-10T05:00:00Z",
            "data": {"resource": "files/file-123"},
        }
    )

    assert envelope.provider == "google"
    assert envelope.source == "workspace_events"
    assert envelope.provider_event_id == "evt-1"
    assert envelope.resource_id == "//drive.googleapis.com/files/file-123"
    assert envelope.event_key == "google:evt-1"


def test_workspace_pubsub_message_normalizes_cloudevent_attributes():
    raw = {
        "message": {
            "attributes": {
                "ce-id": "evt-pubsub-1",
                "ce-source": "//workspaceevents.googleapis.com/subscriptions/sub-1",
                "ce-subject": "//drive.googleapis.com/files/file-456",
                "ce-time": "2026-08-19T22:00:00Z",
                "ce-type": "google.workspace.drive.file.v3.updated",
            },
            "data": "ZXZlbnQtZGF0YQ==",
            "messageId": "transport-message-1",
            "publishTime": "2026-08-19T22:00:01Z",
        },
        "subscription": "projects/example/subscriptions/sub-1",
    }

    envelope = normalize_workspace_event(raw)

    assert envelope.provider_event_id == "evt-pubsub-1"
    assert envelope.event_type == "google.workspace.drive.file.v3.updated"
    assert envelope.resource_id == "//drive.googleapis.com/files/file-456"
    assert envelope.observed_at == "2026-08-19T22:00:00Z"
    assert envelope.event_key == "google:evt-pubsub-1"
    assert envelope.payload == raw


def test_content_hash_key_is_stable_when_provider_id_is_absent():
    first = EventEnvelope(
        provider="google",
        source="workspace_events",
        event_type="drive.updated",
        resource_id="f1",
        observed_at="2026-08-10T05:00:00Z",
        payload={"b": 2, "a": 1},
    )
    second = EventEnvelope(
        provider="google",
        source="workspace_events",
        event_type="drive.updated",
        resource_id="f1",
        observed_at="2026-08-10T05:00:00Z",
        payload={"a": 1, "b": 2},
    )

    assert first.event_key == second.event_key
    assert first.event_key.startswith("google:sha256:")


def test_workspace_redelivery_is_idempotent(tmp_path):
    store = SQLiteCustodianEventStore(tmp_path / "custodian.sqlite3")
    adapter = CustodianDriveEventAdapter(store)
    event = {
        "id": "evt-redelivered",
        "type": "drive.updated",
        "subject": "files/f1",
    }

    assert adapter.ingest_workspace_events([event]) == 1
    assert adapter.ingest_workspace_events([event]) == 0
    assert store.pending_count() == 1


def test_idless_workspace_redelivery_without_time_is_still_idempotent(tmp_path):
    store = SQLiteCustodianEventStore(tmp_path / "custodian.sqlite3")
    adapter = CustodianDriveEventAdapter(store)
    event = {
        "type": "drive.updated",
        "subject": "files/f-idless",
        "data": {"resource": "files/f-idless"},
    }

    first = normalize_workspace_event(event)
    second = normalize_workspace_event(event)
    assert first.observed_at == ""
    assert second.observed_at == ""
    assert first.event_key == second.event_key

    assert adapter.ingest_workspace_events([event]) == 1
    assert adapter.ingest_workspace_events([event]) == 0
    assert store.pending_count() == 1


def test_change_row_key_is_replay_stable_for_same_page():
    raw = {"fileId": "file-1", "changeType": "file", "removed": False}
    first = normalize_drive_change(raw, page_token="p1", ordinal=0)
    replay = normalize_drive_change(raw, page_token="p1", ordinal=0)

    assert first.event_key == replay.event_key
    assert first.provider_event_id == "change:p1:0:file-1"


def test_change_page_and_cursor_advance_in_one_local_transaction(tmp_path):
    store = SQLiteCustodianEventStore(tmp_path / "custodian.sqlite3")
    store.set_cursor_if_absent("p1")
    envelope = normalize_drive_change(
        {"fileId": "file-1", "changeType": "file"},
        page_token="p1",
        ordinal=0,
    )

    inserted = store.ingest_change_page(
        [envelope], expected_cursor="p1", next_cursor="p2"
    )

    assert inserted == 1
    assert store.get_cursor() == "p2"
    assert store.pending_count() == 1


def test_cursor_conflict_fails_closed_without_inserting_page(tmp_path):
    store = SQLiteCustodianEventStore(tmp_path / "custodian.sqlite3")
    store.set_cursor_if_absent("p2")
    envelope = normalize_drive_change(
        {"fileId": "file-2", "changeType": "file"},
        page_token="p1",
        ordinal=0,
    )

    with pytest.raises(CursorConflictError):
        store.ingest_change_page(
            [envelope], expected_cursor="p1", next_cursor="p3"
        )

    assert store.get_cursor() == "p2"
    assert store.pending_count() == 0


def test_reconcile_changes_drains_pages_and_uses_new_start_token(tmp_path):
    store = SQLiteCustodianEventStore(tmp_path / "custodian.sqlite3")
    adapter = CustodianDriveEventAdapter(store)
    client = FakeDriveClient(
        {
            "start-1": {
                "changes": [{"fileId": "f1", "changeType": "file"}],
                "nextPageToken": "p2",
            },
            "p2": {
                "changes": [
                    {"fileId": "f2", "changeType": "file"},
                    {"fileId": "f3", "changeType": "file", "removed": True},
                ],
                "newStartPageToken": "start-2",
            },
        }
    )

    result = adapter.reconcile_changes(client)

    assert client.start_calls == 1
    assert client.calls == ["start-1", "p2"]
    assert result["pages"] == 2
    assert result["observed"] == 3
    assert result["inserted"] == 3
    assert result["cursor"] == "start-2"
    assert result["pending"] == 3
    assert result["page_limit_reached"] is False


def test_reconcile_reuses_persisted_cursor_after_restart(tmp_path):
    path = tmp_path / "custodian.sqlite3"
    first_store = SQLiteCustodianEventStore(path)
    first_store.set_cursor_if_absent("resume-token")

    restarted = CustodianDriveEventAdapter(SQLiteCustodianEventStore(path))
    client = FakeDriveClient(
        {
            "resume-token": {
                "changes": [],
                "newStartPageToken": "after-resume",
            }
        },
        start_token="should-not-be-used",
    )

    result = restarted.reconcile_changes(client)

    assert client.start_calls == 0
    assert client.calls == ["resume-token"]
    assert result["cursor"] == "after-resume"


def test_claim_done_and_stale_processing_recovery(tmp_path):
    store = SQLiteCustodianEventStore(tmp_path / "custodian.sqlite3")
    envelope = EventEnvelope(
        provider="google",
        source="workspace_events",
        provider_event_id="evt-claim",
        event_type="drive.updated",
        resource_id="f1",
    )
    store.enqueue([envelope])

    claimed = store.claim_pending(limit=1)
    assert [row["event_key"] for row in claimed] == ["google:evt-claim"]
    assert claimed[0]["attempts"] == 1
    assert store.pending_count() == 1

    # Simulate an abandoned claim by aging it beyond the recovery threshold.
    with sqlite3.connect(store.path) as conn:
        conn.execute(
            "UPDATE event_inbox SET claimed_at=? WHERE event_key=?",
            (time.time() - 60, "google:evt-claim"),
        )

    assert store.requeue_stale_processing(stale_after_seconds=30) == 1
    reclaimed = store.claim_pending(limit=1)
    assert reclaimed[0]["attempts"] == 2
    assert store.mark_done("google:evt-claim") is True
    assert store.pending_count() == 0


def test_failed_consumer_can_retry_or_dead_letter(tmp_path):
    store = SQLiteCustodianEventStore(tmp_path / "custodian.sqlite3")
    envelope = EventEnvelope(
        provider="google",
        source="workspace_events",
        provider_event_id="evt-error",
        event_type="drive.updated",
    )
    store.enqueue([envelope])

    store.claim_pending(limit=1)
    assert store.mark_error("google:evt-error", "temporary", retry=True) is True
    assert store.claim_pending(limit=1)[0]["attempts"] == 2
    assert store.mark_error("google:evt-error", "permanent", retry=False) is True
    assert store.pending_count() == 0


def test_resource_registry_keeps_provider_identity_separate_from_semantic_owner(tmp_path):
    store = SQLiteCustodianEventStore(tmp_path / "custodian.sqlite3")
    store.upsert_resource(
        "drive-file-1",
        semantic_id="AD:SYS:JSPACE:001",
        route="AURA > JSPACE",
        metadata={"kind": "canonical_owner"},
    )

    record = store.resource_record("drive-file-1")

    assert record is not None
    assert record["semantic_id"] == "AD:SYS:JSPACE:001"
    assert record["route"] == "AURA > JSPACE"
    assert record["active"] is True
    assert record["metadata"] == {"kind": "canonical_owner"}


def test_health_explicitly_has_no_write_or_semantic_mutation_capability(tmp_path):
    adapter = CustodianDriveEventAdapter(
        SQLiteCustodianEventStore(tmp_path / "custodian.sqlite3")
    )

    health = adapter.health()

    assert health["mode"] == "read_only"
    assert health["drive_write_capability"] is False
    assert health["semantic_mutation_capability"] is False