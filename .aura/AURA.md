# AURA — Orchestration Substrate Guardrail

Aura is an AI orchestration substrate / middleware proxy. It sits between a
user (or tool) and an external LLM. Aura runs **no language model of her own** —
she is a fast, deterministic substrate. The model is only ever touched at the
external egress, purely so Aura's structured data can be verbalized.

Aura's job is to:

1. Compress a natural-language request into a deterministic, bracketed task
   packet (a *polysynthetic task frame*).
2. Select only the **surgical** code context required for the task, using the
   topology / `[AURA_MASTER_KEY]` header index and (optionally) a vector index.
3. Inject deterministic Markdown guardrails (the files in this `.aura/` folder).
4. Forward the guarded, minimal prompt to the external model.

The model receiving an Aura packet is expected to:

- Treat the bracketed packet as the authoritative task specification.
- Obey every guardrail in this `.aura/` folder.
- Never invent files, paths, or symbols that were not provided in context.
- Never add new third-party dependencies unless the packet explicitly allows it.
- Emit output in exactly the format requested by the `[OUTPUT:...]` tag.

If a packet and a raw prose request disagree, the packet wins.
