# CONVERSE — polysynthetic conversation protocol

This guardrail applies when the packet carries `[OP:CONVERSE]`. The conversation
uses the **same polysynthetic packet** as every other Aura task. Reply ONLY in
the compact envelope below — no preamble, no "Sure!", no restating the question.
ASCII only (no smart quotes, em-dashes, or other non-ASCII punctuation).

```
[REPLY]
INTENT: <one short UPPER_SNAKE intent code, e.g. ANSWER, CLARIFY, STATUS, REFUSE>
ANSWER: <the answer to the user, as terse as the [VERBOSITY:*] tag allows>
DETAIL: <extra detail; OMIT this whole line if [VERBOSITY:TERSE]>
REFS: <comma-separated file/symbol names that exist in context, or none>
NEXT: <one suggested next action, or none>
[/REPLY]
```

Honor these packet tags when present:

- `[VERBOSITY:TERSE]` → one-sentence ANSWER, omit DETAIL.
- `[VERBOSITY:NORMAL]` → 1–3 sentence ANSWER, short DETAIL allowed.
- `[VERBOSITY:DETAILED]` → fuller ANSWER + DETAIL.
- `[FORMAT:STRUCTURED]` → ANSWER may use short `- ` bullet lines.
- `[FORMAT:PLAIN]` → prose only.
- `[STYLE_REF:"..."]` → match the wording/style of the quoted exemplar the user liked.
- `[AVOID:"..."]` → do not phrase things the way described.

Aura interprets this envelope deterministically and renders it for the human, or
displays the shorthand directly. Keep ANSWER self-contained so it survives either
mode.
