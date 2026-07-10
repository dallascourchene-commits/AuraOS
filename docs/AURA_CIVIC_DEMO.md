# Aura Civic Commons Arena — Demo Guide

## Story A: Community-Owned Hairstyling Service

```bash
python -m aura_agent_arena_cli civic-demo --story hairstylist
```

Objective: "Our neighbourhood needs an affordable hairstylist. We want the community to own and benefit from it."

Shows: IntentPacket, civic FST, Capability Resolution, Winnipeg profile, ephemeral organs, map, contributions, MITOSIS workstreams, MUSIC scenarios (cooperative, chair rental, mobile pilot, social enterprise), legal questions, Consent Arc, What-If, Pilot Tunnel, Decision Packet, organ dissolution receipts.

## Story B: Youth Healing, Training, and Employment Centre

```bash
python -m aura_agent_arena_cli civic-demo --story youth_centre
```

## Story C: Civic Issue Pulse

```bash
python -m aura_agent_arena_cli civic-demo --story council_pulse
```

Shows council agenda items, meeting dates, dispositions, vote records, source dates, extraction confidence, and missing records. Does not infer councillor motives.

## All Offline

All demos run in fixture mode. No internet required. No model API key required. Zero raw network calls.

## Invariants

- patch_authority: exact_source_spans_and_hashes_only
- vsa_patch_authority: false
- No Web3, payments, binding voting, or government submissions
- No invented Indigenous-language translations
- No universal Indigenous-governance assumption
