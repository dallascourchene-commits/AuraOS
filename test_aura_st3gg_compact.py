import os
import shutil
import struct
import subprocess
from pathlib import Path

import pytest


SOURCE = Path("aura_st3gg_compact.rs")


def _djb2_hash(raw: bytes, seed: int) -> int:
    value = (5381 + seed) & 0xFFFFFFFFFFFFFFFF
    for byte in raw:
        value = ((value * 33) + byte) & 0xFFFFFFFFFFFFFFFF
    return value


def test_st3gg_compactor_source_is_std_only():
    source = SOURCE.read_text(encoding="utf-8")

    assert "extern crate" not in source
    assert "serde" not in source
    assert "bincode" not in source
    assert "phf" not in source
    assert "libc" not in source


def test_st3gg_compactor_compiles_and_emits_pilots(tmp_path: Path):
    rustc = shutil.which("rustc")
    if rustc is None:
        pytest.skip("rustc is not available on PATH")
    binary = tmp_path / ("st3gg_compact.exe" if os.name == "nt" else "st3gg_compact")

    subprocess.run([rustc, "-O", str(SOURCE), "-o", str(binary)], check=True)
    keys = [
        "aura_ccr_0001",
        "ST3GG-L2::JSON:ABCD:0123456789abcdef",
        "0123456789abcdef",
        "aura_ccr_0002",
        "ST3GG-L2::PAPER:DCBA:fedcba9876543210",
    ]
    proc = subprocess.run(
        [str(binary)],
        input=("\n".join(keys) + "\n").encode("utf-8"),
        capture_output=True,
        check=True,
    )

    assert len(proc.stdout) == 4 + len(keys)
    count = struct.unpack_from("<I", proc.stdout, 0)[0]
    pilots = list(proc.stdout[4:])
    assert count == len(keys)
    assert len(pilots) == len(keys)
    table_size = len(keys) * 2
    slots = {
        _djb2_hash(key.encode("utf-8"), pilot) % table_size
        for key, pilot in zip(keys, pilots)
    }
    assert len(slots) == len(keys)
