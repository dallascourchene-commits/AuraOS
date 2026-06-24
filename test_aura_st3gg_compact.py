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


def _compile_compactor(tmp_path: Path) -> Path:
    rustc = shutil.which("rustc")
    if rustc is None:
        pytest.skip("rustc is not available on PATH")
    binary = tmp_path / ("st3gg_compact.exe" if os.name == "nt" else "st3gg_compact")
    subprocess.run([rustc, "-O", str(SOURCE), "-o", str(binary)], check=True)
    return binary


def test_st3gg_compactor_source_is_std_only():
    source = SOURCE.read_text(encoding="utf-8")

    assert "extern crate" not in source
    assert "serde" not in source
    assert "bincode" not in source
    assert "phf" not in source
    assert "libc" not in source


def test_st3gg_compactor_compiles_and_emits_pilots(tmp_path: Path):
    binary = _compile_compactor(tmp_path)
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


def test_st3gg_compaction_decoder_rejects_profile_mismatches():
    good = struct.pack(
        "<8sIIIII",
        ST3GG_COMPACTION_MAGIC,
        ST3GG_COMPACTION_VERSION,
        1,
        ST3GG_COMPACTION_TABLE_SCALE,
        ST3GG_COMPACTION_TABLE_SCALE,
        ST3GG_COMPACTION_HASH_PROFILE_DJB2_SEED8,
    ) + bytes([0])

    bad_scale = good[:20] + struct.pack("<I", ST3GG_COMPACTION_TABLE_SCALE + 1) + good[24:]
    with pytest.raises(ValueError, match="table_scale_mismatch"):
        decode_st3gg_compaction_blob(bad_scale)

    bad_hash_profile = good[:24] + struct.pack("<I", ST3GG_COMPACTION_HASH_PROFILE_DJB2_SEED8 + 1) + good[28:]
    with pytest.raises(ValueError, match="hash_profile_mismatch"):
        decode_st3gg_compaction_blob(bad_hash_profile)


def test_djb2_hash_function_is_deterministic():
    assert _djb2_hash(b"hello", 0) == _djb2_hash(b"hello", 0)


def test_djb2_hash_different_seeds_produce_different_values():
    result_seed0 = _djb2_hash(b"aura_key", 0)
    result_seed1 = _djb2_hash(b"aura_key", 1)
    result_seed255 = _djb2_hash(b"aura_key", 255)

    assert result_seed0 != result_seed1
    assert result_seed0 != result_seed255


def test_djb2_hash_empty_bytes_uses_seed_only():
    assert _djb2_hash(b"", 0) == 5381


def test_djb2_hash_matches_rust_formula():
    assert _djb2_hash(b"\x41", 0) == ((5381 * 33) + 0x41) & 0xFFFFFFFFFFFFFFFF


def test_st3gg_compactor_rejects_duplicate_keys(tmp_path: Path):
    binary = _compile_compactor(tmp_path)

    proc = subprocess.run(
        [str(binary)],
        input=b"key_alpha\nkey_beta\nkey_alpha\n",
        capture_output=True,
    )

    assert proc.returncode != 0
    assert b"duplicate" in proc.stderr.lower()


def test_st3gg_compactor_empty_input_emits_versioned_header(tmp_path: Path):
    binary = _compile_compactor(tmp_path)

    proc = subprocess.run([str(binary)], input=b"", capture_output=True, check=True)

    assert len(proc.stdout) == 28
    decoded = decode_st3gg_compaction_blob(proc.stdout)
    assert decoded["key_count"] == 0
    assert decoded["table_size"] == 0
    assert decoded["pilots"] == ()


def test_st3gg_compactor_single_key_has_valid_pilot(tmp_path: Path):
    binary = _compile_compactor(tmp_path)
    key = "single_st3gg_key"

    proc = subprocess.run(
        [str(binary)],
        input=(key + "\n").encode("utf-8"),
        capture_output=True,
        check=True,
    )

    assert len(proc.stdout) == 29
    decoded = decode_st3gg_compaction_blob(proc.stdout)
    assert decoded["key_count"] == 1
    assert decoded["table_size"] == ST3GG_COMPACTION_TABLE_SCALE
    pilot = decoded["pilots"][0]
    slot = _djb2_hash(key.encode("utf-8"), pilot) % decoded["table_size"]
    assert 0 <= slot < decoded["table_size"]


def test_st3gg_compactor_output_has_no_collision(tmp_path: Path):
    binary = _compile_compactor(tmp_path)
    keys = [
        f"ST3GG-L2::CCR:{hex(idx * 0x1234)[2:].upper():>4}:{idx:016x}"
        for idx in range(20)
    ]

    proc = subprocess.run(
        [str(binary)],
        input=("\n".join(keys) + "\n").encode("utf-8"),
        capture_output=True,
        check=True,
    )

    decoded = decode_st3gg_compaction_blob(proc.stdout)
    assert decoded["key_count"] == len(keys)
    assert decoded["table_size"] == len(keys) * ST3GG_COMPACTION_TABLE_SCALE
    used_slots = {
        _djb2_hash(key.encode("utf-8"), pilot) % decoded["table_size"]
        for key, pilot in zip(keys, decoded["pilots"])
    }
    assert len(used_slots) == len(keys)
