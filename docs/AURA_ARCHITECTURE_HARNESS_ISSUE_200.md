# Exact-head transport repair

Issue #200 adds `scripts/aura_exact_head_transport.py` for clean exact-head export, external materialization, dirty-path diagnostics, and all-or-nothing whole-file publication bundles under formatter drift.

All generated files and diagnostics remain outside the repository checkout. Publication bundles remain proposal evidence for Aura's existing Agent Bridge atomic compare-and-swap lane and grant no automatic publication, merge, or production authority.
