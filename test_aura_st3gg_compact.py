import os
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

from aura_st3gg_recall import (
    ST3GG_COMPACTION_HASH_PROFILE_DJB2_SEED8,
    ST3GG_COMPACTION_MAGIC,
    ST3GG_COMPACTION_TABLE_SCALE,
    ST3GG_COMPACTION_VERSION,
    decode_st3gg_compaction_blob,
)


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

    assert len(proc.stdout) == 28 + len(keys)
    magic, version, count, table_size, table_scale, hash_profile = struct.unpack_from("<8sIIIII", proc.stdout, 0)
    assert magic == ST3GG_COMPACTION_MAGIC
    assert version == ST3GG_COMPACTION_VERSION
    assert count == len(keys)
    assert table_size == len(keys) * ST3GG_COMPACTION_TABLE_SCALE
    assert table_scale == ST3GG_COMPACTION_TABLE_SCALE
    assert hash_profile == ST3GG_COMPACTION_HASH_PROFILE_DJB2_SEED8
    decoded = decode_st3gg_compaction_blob(proc.stdout)
    assert decoded["key_count"] == len(keys)
    assert decoded["table_size"] == table_size
    pilots = list(decoded["pilots"])
    assert len(pilots) == len(keys)
    slots = {
        _djb2_hash(key.encode("utf-8"), pilot) % table_size
        for key, pilot in zip(keys, pilots)
    }
    assert len(slots) == len(keys)


def test_st3gg_compaction_decoder_rejects_bad_headers():
    good = struct.pack(
        "<8sIIIII",
        ST3GG_COMPACTION_MAGIC,
        ST3GG_COMPACTION_VERSION,
        2,
        4,
        ST3GG_COMPACTION_TABLE_SCALE,
        ST3GG_COMPACTION_HASH_PROFILE_DJB2_SEED8,
    ) + bytes([0, 1])

    assert decode_st3gg_compaction_blob(good)["pilots"] == (0, 1)
    bad_magic = b"BADMAGIC" + good[8:]
    with pytest.raises(ValueError, match="bad_magic"):
        decode_st3gg_compaction_blob(bad_magic)
    bad_version = good[:8] + struct.pack("<I", ST3GG_COMPACTION_VERSION + 1) + good[12:]
    with pytest.raises(ValueError, match="unsupported_version"):
        decode_st3gg_compaction_blob(bad_version)
    bad_table = good[:16] + struct.pack("<I", 5) + good[20:]
    with pytest.raises(ValueError, match="table_size_mismatch"):
        decode_st3gg_compaction_blob(bad_table)
    with pytest.raises(ValueError, match="pilot_count_mismatch"):
        decode_st3gg_compaction_blob(good[:-1])
