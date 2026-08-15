from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "tests/test_aura_construction_pascal_spatial_foundry_pr5.py"

OLD = '''    real_coord["pascal_artifact_digest"] = "".join(bad_digest)

    # Monkeypatch _load_json_object so that when the coordinate receipt is
'''

NEW = '''    real_coord["pascal_artifact_digest"] = "".join(bad_digest)
    # This test targets the cross-artifact binding, not the receipt's own
    # tamper-evident envelope. Recompute the self-digest after changing the
    # inner artifact reference so AuraPascalCoordinateReceipt.from_mapping()
    # remains internally valid and load_pascal_compatibility_fixture() can
    # exercise the intended manifest/coordinate mismatch boundary.
    receipt_body = {
        key: value
        for key, value in real_coord.items()
        if key != "receipt_digest"
    }
    real_coord["receipt_digest"] = part5.sha256_digest(receipt_body)

    # Monkeypatch _load_json_object so that when the coordinate receipt is
'''


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    count = text.count(OLD)
    if count != 1:
        raise RuntimeError(f"Pascal receipt test anchor expected once, found {count}")
    TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    Path(__file__).unlink()
    print("Pascal cross-artifact mismatch test now preserves receipt self-integrity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
