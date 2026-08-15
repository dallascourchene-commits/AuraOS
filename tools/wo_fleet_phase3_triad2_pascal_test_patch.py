from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "tests/test_aura_construction_pascal_spatial_foundry_pr5.py"

ANCHOR = '''    real_coord["pascal_artifact_digest"] = "".join(bad_digest)

    # Monkeypatch _load_json_object so that when the coordinate receipt is
'''

REPLACEMENT = '''    real_coord["pascal_artifact_digest"] = "".join(bad_digest)
    # Keep the tampered receipt internally self-consistent so this test reaches
    # the intended cross-artifact mismatch boundary rather than failing earlier
    # on the enclosing receipt digest.
    from aura_pascal_spatial_presentation_part1 import sha256_digest
    real_coord["receipt_digest"] = sha256_digest({
        key: value for key, value in real_coord.items() if key != "receipt_digest"
    })

    # Monkeypatch _load_json_object so that when the coordinate receipt is
'''


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    count = text.count(ANCHOR)
    if count != 1:
        raise RuntimeError(f"Pascal test anchor expected once, found {count}")
    TARGET.write_text(text.replace(ANCHOR, REPLACEMENT, 1), encoding="utf-8")
    print("Phase-3 Pascal cross-artifact negative fixture repair applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
