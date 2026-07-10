---
aura_doc_type: refactor_intent
intent_id: native_cockpit_v1
created_by: human
parser: polysynthetic_compiler
status: draft
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
---

[AURA_INTENT]
OBJECTIVE: Build Aura Native Cockpit where human interacts with Aura before Hermes.
WHY: Reduce token burn, improve grounding, expose architecture, and route work through Aura-native capsules.

[AURA_CONTEXT]
The Aura Native Cockpit is the primary human coding interface. Hermes, Codex, Fireworks, and GitHub PRs are workers/routes inside Aura's environment. The human should feed Aura structured Markdown/intent docs instead of giant raw prompts. Aura compresses the intent polysynthetically, routes through FST, localizes via CODEMAP, ranks with DREAM-lite, compresses context with Context Crusher/ST3GG, and then sends approved work to agents as compact verifiable packets.

[AURA_POLYSYNTHETIC_PACKET]
[OP:IMPROVE][DOMAIN:CODING_ARENA][TARGET:NATIVE_COCKPIT][ENV:PYTHON][CONSTRAINT:TOKEN_SPARING][OUTPUT:CHECKPOINTED_HANDOFF]

[AURA_LEXC_ROUTE]
DIR: +SYS
ASP: +SYS_ROUTE
CLASS: +POLY
SUBJ: +SHAPE:OCTA+TEMP:COLD+LUM:MID+FRIC:LO+DIR:GIDINAWENDIMIN
VOICE: _VALIDATE
STEM: _MERGE

[AURA_CAPABILITIES]
USE: Concept Workspace
USE: Node Inspector
USE: Affordance Directory
USE: Agent Arena Bridge
USE: Hermes Arena Mode
USE: Context Crusher
USE: ST3GG Arena Codec
USE: DREAM-lite Retrieval
USE: QDKT
USE: FST Routing
USE: Token Economics
USE: AI Router
USE: Coding Arena Grounding
USE: Tokenizer Guard

[AURA_ROUTE_HINTS]
intent: code_refactor
action: modify
scope: subsystem
quality: balanced
cost: local_first

[AURA_CONSTRAINTS]
No external provider calls unless explicitly requested.
No git add . — stage only specific scoped files.
No commits to main.
All paths repo-relative.
Broad hub-file reads blocked.

[AURA_GATES]
GATE_1: Human approves objective.
GATE_2: Aura validates LEXC/FST route.
GATE_3: Aura localizes files/symbols through CODEMAP.
GATE_4: Aura ranks candidates through DREAM-lite.
GATE_5: Aura compresses context through Context Crusher/ST3GG if savings threshold passes.
GATE_6: Human approves agent handoff.
GATE_7: Agent proposes patch.
GATE_8: Aura verifies tests and boundaries.
GATE_9: Human approves commit.
GATE_10: Human approves PR.

[AURA_HANDOFF]
agent: hermes
mode: pr
contract: hermes-arena-mode
handoff_packet: compact_capsule

[AURA_ACCEPTANCE]
- User can store a long refactor plan as .aura/intents/*.aura.md
- Aura parses it into an IntentPacket
- Aura compresses the raw human intent into a polysynthetic packet
- Aura validates or rejects the six-slot LEXC route
- Aura routes the intent through RoutingFrame and RouteDecision
- Aura localizes files/symbols through CODEMAP/AI Router before opening source
- Aura ranks context/capabilities with DREAM-lite without replacing truth boundaries
- Aura produces a token-economy report showing each savings source
- Aura can prepare a Hermes/Agent Arena handoff using Hermes Arena Mode
- No direct production mutation from cockpit commands
- Tests pass without network, provider APIs, or GitHub auth

[AURA_RISKS]
RISK_1: numpy not installed — FST routing and substrate compression use numpy. Fallback to lightweight local routing.
RISK_2: CODEMAP may be stale — refresh after writes.
RISK_3: Advisory layers (DREAM, QDKT, JSpace) must not become patch authority.

[AURA_TOKEN_BUDGET]
raw_estimate: 50000
aura_target: 5000
savings_target_percent: 90

[AURA_MEMORY_FEEDBACK]
Log successful routing patterns to QDKT.
Record DREAM-lite reranking feedback.
Store token economy results in ledger.
