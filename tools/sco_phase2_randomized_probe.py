from __future__ import annotations

import random
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aura_event_contracts import ActorType, MeasurementClass
from aura_construction_contracts import (
    ConstructionAuthorityClass,
    ConstructionClaim,
    ConstructionEvidence,
    ConstructionEvidenceClass,
    ConstructionEvent,
    ConstructionPrivacyClass,
    ConstructionScope,
    GENESIS_CHAIN_DIGEST,
)
from aura_construction_state import ConstructionProjectState, replay_construction_events


def evidence(scope: ConstructionScope, index: int, digest: str) -> ConstructionEvidence:
    return ConstructionEvidence.create(
        scope=scope,
        subject_id=f"subject-{index % 4}",
        evidence_class=ConstructionEvidenceClass.DOCUMENT,
        source_ref=f"source-{index % 4}",
        payload_digest=digest,
        measurement_class=MeasurementClass.EMPIRICAL,
        confidence=0.8,
        authority_class=ConstructionAuthorityClass.INFORMATIVE,
        privacy_class=ConstructionPrivacyClass.PROJECT,
        observed_at=float(index * 10 + 1),
        expires_at=float(index * 10 + 100),
    )


def event(record, sequence, previous, *, supersedes=()):
    return ConstructionEvent.create(
        ledger_id="construction/P-RANDOM",
        sequence_number=sequence,
        previous_chain_digest=previous,
        trace_id="randomized-probe",
        record=record,
        actor_id="probe",
        actor_type=ActorType.VERIFIER,
        supersedes_event_ids=tuple(supersedes),
        created_at=float(sequence * 10 + 2),
    )


def run(seed: int = 731, histories: int = 250) -> None:
    rng = random.Random(seed)
    for history in range(histories):
        scope = ConstructionScope("P-RANDOM", f"Z{history % 3}", f"W{history % 5}")
        events = []
        active_by_key = {}
        previous = GENESIS_CHAIN_DIGEST
        sequence = 1
        evidence_ids = []
        for _index in range(rng.randint(2, 10)):
            payload = f"{rng.getrandbits(128):032x}"
            record = evidence(scope, sequence, payload)
            supersedes = ()
            prior = active_by_key.get(record.state_key)
            if prior is not None and rng.random() < 0.65:
                supersedes = (prior.event_id,)
            current = event(record, sequence, previous, supersedes=supersedes)
            events.append(current)
            active_by_key[record.state_key] = current
            evidence_ids.append(record.evidence_id)
            previous = current.chain_digest
            sequence += 1

        claim = ConstructionClaim.create(
            scope=scope,
            subject_id="subject-0",
            predicate="represented-complete",
            value_digest=f"{rng.getrandbits(128):032x}",
            claimant_id="probe-claimant",
            evidence_refs=tuple(sorted(set(evidence_ids[:2]))),
            measurement_class=MeasurementClass.EMPIRICAL,
            confidence=0.7,
            authority_class=ConstructionAuthorityClass.CONTRACTOR,
            privacy_class=ConstructionPrivacyClass.PROJECT,
            created_at=float(sequence * 10 + 1),
            expires_at=float(sequence * 10 + 100),
        )
        current = event(claim, sequence, previous)
        events.append(current)

        state = replay_construction_events(tuple(events))
        repeated = replay_construction_events(tuple(events))
        if state != repeated:
            raise AssertionError("deterministic replay diverged")
        loaded = ConstructionProjectState.from_dict(state.to_dict())
        if loaded != state:
            raise AssertionError("round-trip state diverged")

        if len(events) > 1:
            tampered = list(events)
            try:
                tampered[-1] = replace(
                    tampered[-1],
                    previous_chain_digest=GENESIS_CHAIN_DIGEST,
                )
            except ValueError:
                pass
            else:
                try:
                    replay_construction_events(tuple(tampered))
                except ValueError:
                    pass
                else:
                    raise AssertionError("tampered chain was accepted")

    print(f"RANDOMIZED_REPLAY_PROBE_PASS histories={histories} seed={seed}")


if __name__ == "__main__":
    run()
