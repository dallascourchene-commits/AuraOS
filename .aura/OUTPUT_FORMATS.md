# OUTPUT FORMATS

The `[OUTPUT:...]` tag in the packet selects exactly one of these formats.
Emit only the requested artifact — nothing before or after it.

## `[OUTPUT:UNIFIED_DIFF]`

A single unified diff. Must start with `--- a/<path>` and `+++ b/<path>` header
lines and contain at least one `@@` hunk header. Mark every changed line with a
leading `+` (added) or `-` (removed); unchanged context lines start with a
space. Use the real target path from the packet. Example skeleton:

```
--- a/aura_mesh.py
+++ b/aura_mesh.py
@@ -164,7 +164,7 @@
         try:
-            secure_packet = self.pack_secure_polysynthetic_packet("EXEC_NODE", payload_data)
+            secure_packet = self.pack_secure_polysynthetic_packet([0, 0, 0, 0, 0, 0], 1.0)
             reader, writer = await asyncio.open_connection(target_ip, 4445)
```

## `[OUTPUT:JSON_EDIT_PLAN]`  (compact / output-token efficient)

Return ONLY a JSON object describing minimal line edits. No diff, no prose, no
code fences. Aura validates this plan and expands it into a real diff locally,
so you must keep it tiny. Schema:

```json
{
  "edits": [
    {
      "file": "aura_mesh.py",
      "start_line": 174,
      "end_line": 174,
      "replacement": "            secure_packet = self.pack_secure_polysynthetic_packet([0, 0, 0, 0, 0, 0], 1.0)"
    }
  ]
}
```

Rules:
- `file` must be the real target file from the packet.
- `start_line`/`end_line` are 1-indexed inclusive line numbers in the ORIGINAL
  file (use the line numbers shown in the surgical context). `end_line >= start_line`.
- `replacement` is the full new text for that line range (may contain `\n` for
  multiple lines). Preserve indentation. To insert without deleting, set
  `start_line == end_line` and include the original line plus your addition.
- Emit the smallest set of edits that satisfies the packet. This minimizes
  output tokens, which Aura measures.

## `[OUTPUT:PYTHON]`

A single fenced ```python code block. The code inside must parse with the
Python AST (`ast.parse`). No prose outside the block.

## `[OUTPUT:JSON]`

A single JSON object. Must parse with `json.loads`. No prose outside it.

## `[OUTPUT:TEXT]`

Plain prose. Keep it under the length implied by the packet.

If no `[OUTPUT:...]` tag is present, default to `[OUTPUT:TEXT]`.
