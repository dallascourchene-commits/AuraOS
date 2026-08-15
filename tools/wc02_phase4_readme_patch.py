from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "README.md"

ANCHOR = """```

### Six-slot FST / WFST boundary
"""

REPLACEMENT = """```

### Construction Human Agent profile

The Construction review surface exposes a bounded **Construction Human Agent profile** through `/api/human-agent/construction/profile`, paired with the read-only Construction Observatory and explicit handoff/checkpoint endpoints. This surface is advisory and evidence-oriented: it does **not** grant physical-work authority, payment release, access control, professional certification, commits, pushes, pull requests, merges, or any other human disposition.

### Six-slot FST / WFST boundary
"""


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    if "### Construction Human Agent profile" in text:
        print("WC-02 README Construction profile witness already present")
        return 0
    count = text.count(ANCHOR)
    if count != 1:
        raise RuntimeError(f"README insertion anchor expected once, found {count}")
    TARGET.write_text(text.replace(ANCHOR, REPLACEMENT, 1), encoding="utf-8")
    print("WC-02 README Construction profile witness applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
