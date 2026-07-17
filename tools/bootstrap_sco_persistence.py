"""Assemble the bounded temporal-persistence source bundle once."""
from __future__ import annotations

from pathlib import Path


TARGETS = (
    "aura_temporal_persistence.py",
    "aura_arena_persistence_adapters.py",
    "tools/apply_sco_persistence_integration.py",
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    payload = root / "tools" / ".sco_persistence_payload"
    for target in TARGETS:
        stem = Path(target).name
        parts = sorted(payload.glob(f"{stem}.part*"))
        if not parts:
            raise RuntimeError(f"missing source parts for {target}")
        content = "".join(part.read_text(encoding="utf-8") for part in parts)
        destination = root / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    for part in payload.iterdir():
        part.unlink()
    payload.rmdir()


if __name__ == "__main__":
    main()
