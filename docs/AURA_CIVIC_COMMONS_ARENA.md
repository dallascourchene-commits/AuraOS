# Aura Civic Commons Arena

## What This Is

The Civic Commons Arena is a user-facing civic-planning product. It transforms a community objective into a transparent environment where needs, knowledge, resources, laws, evidence, trade-offs, and dissent become visible together — without transferring final authority to the machine.

Ephemeral organs are the internal assembly and lifecycle mechanism. The Civic Arena is the product.

## Architecture

```text
human/community objective
→ Aura IntentPacket
→ Capability Resolution Packet
→ Civic profile set
→ Civic Commons session
→ ephemeral civic-organ manifests
→ minimum capability leases
→ fixture/snapshot evidence
→ Civic World Model
→ community needs and offers
→ MITOSIS workstream decomposition
→ resource-constellation matching
→ MUSIC multi-objective scenario synthesis
→ legal/policy/funding constraint display
→ map and heatmap projection
→ Consent Arc and deliberation loop
→ preserved dissent and representation gaps
→ What-If simulation
→ Pilot Tunnel
→ Civic Decision Packet
→ organ dissolution receipts
→ governed Community Memory
```

## Universal Core vs Local Profiles

The universal substrate includes evidence provenance, truth classes, privacy, consent, dissent preservation, non-binding scenarios, governed memory, capability-bounded execution, and dissolution.

Local profiles are explicitly activated. Never auto-activate cultural or governance profiles based on model inference.

## Aura's Origin

Aura began as a locally controlled AI tutor intended to help its founder learn and preserve his language without surrendering data to large external platforms. This origin informs universal architectural lessons: local control, purpose limitation, inspectable memory, external-provider boundaries, data minimization, and community-defined governance.

## Launch Commands

```bash
# Full demo (offline, fixture mode)
python -m aura_agent_arena_cli civic-demo --story hairstylist

# Create session
python -m aura_agent_arena_cli civic-create --objective "Our neighbourhood needs an affordable hairstylist"

# Check status
python -m aura_agent_arena_cli civic-status --session-id <id>

# Run MITOSIS
python -m aura_agent_arena_cli civic-mitosis --session-id <id>

# Run MUSIC scenarios
python -m aura_agent_arena_cli civic-scenarios --session-id <id>

# Export decision packet
python -m aura_agent_arena_cli civic-export --session-id <id>
```

## Known Limitations

- In-memory session store (SQLite for production)
- GeoJSON-only basemap (PMTiles requires byte-range support not yet implemented)
- Fixture mode only (live source broker is stretch)
- No Human Agent Arena frontend integration yet (CLI-only)
- No Web3, payments, binding voting, or government submissions
