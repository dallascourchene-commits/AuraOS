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
    source = "//workspaceevents.googleapis.com/subscriptions/sub-1"
    raw = {
        "message": {
            "attributes": {
                "ce-id": "evt-pubsub-1",
                "ce-source": source,
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

    assert envelope.provider_event_id == f"cloudevent:{source}:evt-pubsub-1"
    assert envelope.event_type == "google.workspace.drive.file.v3.updated"
    assert envelope.resource_id == "//drive.googleapis.com/files/file-456"
    assert envelope.observed_at == "2026-08-19T22:00:00Z"
    assert envelope.event_key == f"google:cloudevent:{source}:evt-pubsub-1"
    assert envelope.payload == raw


def test_workspace_cloudevent_same_id_from_different_sources_does_not_collide():
    def wrapped(source):
        return {
            "message": {
                "attributes": {
                    "ce-id": "shared-id",
                    "ce-source": source,
                    "ce-type": "google.workspace.drive.file.v3.updated",
                }
            }
        }

    first = normalize_workspace_event(
        wrapped("//workspaceevents.googleapis.com/subscriptions/sub-1")
    )
    second = normalize_workspace_event(
        wrapped("//workspaceevents.googleapis.com/subscriptions/sub-2")
    )

    assert first.event_key != second.event_key


def test_workspace_pubsub_fallback_message_id_is_subscription_scoped():
    def wrapped(subscription):
        return {
            "message": {
                "messageId": "same-message-id",
                "attributes": {"ce-type": "google.workspace.drive.file.v3.updated"},
                "data": "same-payload",
            },
            "subscription": subscription,
        }

    first = normalize_workspace_event(
        wrapped("projects/p/subscriptions/workspace-a")
    )
    second = normalize_workspace_event(
        wrapped("projects/p/subscriptions/workspace-b")
    )

    assert first.provider_event_id.startswith("pubsub:")
    assert second.provider_event_id.startswith("pubsub:")
    assert first.event_key != second.event_key


def test_workspace_pubsub_bare_message_id_does_not_claim_global_uniqueness():
    raw = {
        "message": {
            "messageId": "bare-message-id",
            "attributes": {"ce-type": "google.workspace.drive.file.v3.updated"},
            "data": "payload",
        }
    }
    envelope = normalize_workspace_event(raw)

    assert envelope.provider_event_id == ""
    assert envelope.event_key.startswith("google:sha256:")


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


def _enqueue_claimable(store, event_id):
    envelope = EventEnvelope(
        provider="google",
        source="workspace_events",
        provider_event_id=event_id,
        event_type="drive.updated",
        resource_id="f1",
    )
    store.enqueue([envelope])
    return envelope.event_key


def test_claim_done_and_stale_processing_recovery(tmp_path):
    store = SQLiteCustodianEventStore(tmp_path / "custodian.sqlite3")
    event_key = _enqueue_claimable(store, "evt-claim")

    first = store.claim_pending(limit=1)[0]
    assert first["event_key"] == event_key
    assert first["attempts"] == 1
    assert first["claim_token"]
    assert store.pending_count() == 1

    with sqlite3.connect(store.path) as conn:
        conn.execute(
            "UPDATE event_inbox SET claimed_at=? WHERE event_key=?",
            (time.time() - 60, event_key),
        )

    assert store.requeue_stale_processing(stale_after_seconds=30) == 1
    reclaimed = store.claim_pending(limit=1)[0]
    assert reclaimed["attempts"] == 2
    assert reclaimed["claim_token"] != first["claim_token"]
    assert store.mark_done(event_key, reclaimed["claim_token"]) is True
    assert store.pending_count() == 0


def test_stale_claim_cannot_complete_reclaimed_work(tmp_path):
    store = SQLiteCustodianEventStore(tmp_path / "custodian.sqlite3")
    event_key = _enqueue_claimable(store, "evt-fence-done")

    worker_a = store.claim_pending(limit=1)[0]
    with sqlite3.connect(store.path) as conn:
        conn.execute(
            "UPDATE event_inbox SET claimed_at=? WHERE event_key=?",
            (time.time() - 60, event_key),
        )
    assert store.requeue_stale_processing(stale_after_seconds=30) == 1
    worker_b = store.claim_pending(limit=1)[0]

    assert worker_a["claim_token"] != worker_b["claim_token"]
    assert store.mark_done(event_key, worker_a["claim_token"]) is False
    assert store.pending_count() == 1
    assert store.mark_done(event_key, worker_b["claim_token"]) is True
    assert store.pending_count() == 0


def test_stale_claim_cannot_error_or_retry_reclaimed_work(tmp_path):
    store = SQLiteCustodianEventStore(tmp_path / "custodian.sqlite3")
    event_key = _enqueue_claimable(store, "evt-fence-error")

    worker_a = store.claim_pending(limit=1)[0]
    with sqlite3.connect(store.path) as conn:
        conn.execute(
            "UPDATE event_inbox SET claimed_at=? WHERE event_key=?",
            (time.time() - 60, event_key),
        )
    assert store.requeue_stale_processing(stale_after_seconds=30) == 1
    worker_b = store.claim_pending(limit=1)[0]

    assert (
        store.mark_error(
            event_key,
            "stale-a",
            claim_token=worker_a["claim_token"],
            retry=True,
        )
        is False
    )
    assert store.pending_count() == 1
    assert (
        store.mark_error(
            event_key,
            "b-retry",
            claim_token=worker_b["claim_token"],
            retry=True,
        )
        is True
    )
    worker_c = store.claim_pending(limit=1)[0]
    assert worker_c["attempts"] == 3
    assert worker_c["claim_token"] not in {
        worker_a["claim_token"],
        worker_b["claim_token"],
    }


def test_failed_consumer_can_retry_or_dead_letter(tmp_path):
    store = SQLiteCustodianEventStore(tmp_path / "custodian.sqlite3")
    event_key = _enqueue_claimable(store, "evt-error")

    first = store.claim_pending(limit=1)[0]
    assert (
        store.mark_error(
            event_key,
            "temporary",
            claim_token=first["claim_token"],
            retry=True,
        )
        is True
    )
    second = store.claim_pending(limit=1)[0]
    assert second["attempts"] == 2
    assert (
        store.mark_error(
            event_key,
            "permanent",
            claim_token=second["claim_token"],
            retry=False,
        )
        is True
    )
    assert store.pending_count() == 0


def test_blank_claim_token_is_rejected(tmp_path):
    store = SQLiteCustodianEventStore(tmp_path / "custodian.sqlite3")
    event_key = _enqueue_claimable(store, "evt-blank-token")
    store.claim_pending(limit=1)

    with pytest.raises(ValueError):
        store.mark_done(event_key, "")
    with pytest.raises(ValueError):
        store.mark_error(event_key, "error", claim_token="", retry=True)


def test_legacy_processing_rows_without_token_are_requeued_on_migration(tmp_path):
    path = tmp_path / "custodian.sqlite3"
    store = SQLiteCustodianEventStore(path)
    event_key = _enqueue_claimable(store, "evt-migration")
    claim = store.claim_pending(limit=1)[0]
    assert claim["claim_token"]

    with sqlite3.connect(path) as conn:
        conn.execute(
            "UPDATE event_inbox SET claim_token='' WHERE event_key=?",
            (event_key,),
        )

    reopened = SQLiteCustodianEventStore(path)
    assert reopened.pending_count() == 1
    replacement = reopened.claim_pending(limit=1)[0]
    assert replacement["claim_token"]


def test_resource_registry_is_candidate_cache_not_semantic_owner(tmp_path):
    store = SQLiteCustodianEventStore(tmp_path / "custodian.sqlite3")
    store.upsert_resource_candidate(
        "drive-file-1",
        candidate_semantic_id="AD:SYS:JSPACE:001",
        candidate_route="AURA > JSPACE",
        metadata={"kind": "provider_observation"},
    )

    record = store.resource_record("drive-file-1")

    assert record is not None
    assert record["candidate_semantic_id"] == "AD:SYS:JSPACE:001"
    assert record["candidate_route"] == "AURA > JSPACE"
    assert record["mapping_verification_state"] == "UNVERIFIED"
    assert record["canonical_owner_ref"] == ""
    assert "semantic_id" not in record
    assert "route" not in record
    assert record["active"] is True


def test_owner_bound_candidate_requires_exact_provenance(tmp_path):
    store = SQLiteCustodianEventStore(tmp_path / "custodian.sqlite3")

    with pytest.raises(ValueError):
        store.upsert_resource_candidate(
            "drive-file-1",
            candidate_semantic_id="AD:SYS:JSPACE:001",
            candidate_route="AURA > JSPACE",
            mapping_verification_state="OWNER_BOUND",
        )

    store.upsert_resource_candidate(
        "drive-file-1",
        candidate_semantic_id="AD:SYS:JSPACE:001",
        candidate_route="AURA > JSPACE",
        mapping_verification_state="OWNER_BOUND",
        canonical_owner_ref="AD:SYS:JSPACE:OWNER",
        canonical_source_ref="drive:owner-source",
        canonical_generation="g17",
    )
    record = store.resource_record("drive-file-1")

    assert record["mapping_verification_state"] == "OWNER_BOUND"
    assert record["canonical_owner_ref"] == "AD:SYS:JSPACE:OWNER"
    assert record["canonical_source_ref"] == "drive:owner-source"
    assert record["canonical_generation"] == "g17"


def test_legacy_resource_semantic_fields_migrate_to_unverified_candidate(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE resource_registry (
                resource_id TEXT PRIMARY KEY,
                semantic_id TEXT NOT NULL DEFAULT '',
                route TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                updated_at REAL NOT NULL
            );
            INSERT INTO resource_registry(
                resource_id, semantic_id, route, active, metadata_json, updated_at
            ) VALUES (
                'drive-file-legacy', 'AD:OLD:001', 'AURA > OLD', 1, '{}', 1.0
            );
            """
        )

    store = SQLiteCustodianEventStore(path)
    record = store.resource_record("drive-file-legacy")

    assert record["candidate_semantic_id"] == "AD:OLD:001"
    assert record["candidate_route"] == "AURA > OLD"
    assert record["mapping_verification_state"] == "LEGACY_UNVERIFIED"
    assert "semantic_id" not in record
    assert "route" not in record
    with sqlite3.connect(path) as conn:
        old = conn.execute(
            "SELECT semantic_id, route FROM resource_registry "
            "WHERE resource_id='drive-file-legacy'"
        ).fetchone()
    assert old == ("", "")


def test_health_explicitly_has_no_write_or_semantic_mutation_capability(tmp_path):
    adapter = CustodianDriveEventAdapter(
        SQLiteCustodianEventStore(tmp_path / "custodian.sqlite3")
    )

    health = adapter.health()

    assert health["mode"] == "read_only"
    assert health["drive_write_capability"] is False
    assert health["semantic_mutation_capability"] is False
    assert (
        health["resource_registry_semantics"]
        == "provider_local_candidate_cache_only"
    )
