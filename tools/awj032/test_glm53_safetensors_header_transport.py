import hashlib
import json
import struct

import pytest

from tools.awj032.glm53_safetensors_header_transport import (
    HeaderTransportError,
    collect_header_evidence,
    fetch_index,
    fetch_safetensors_header,
    hf_resolve_url,
    representative_expert_keys,
)

REV = "7cda81930d6e4cef42f48555de830aa32ecdde28"
REPO = "zai-org/GLM-5.3"


def _fixture():
    prefix = "model.layers.3.mlp.experts.0."
    wm = {}
    roles = [
        ("gate_proj.weight", "model-00005-of-00141.safetensors", "F8_E4M3", [2048, 6144], [0, 12]),
        ("gate_proj.weight_scale_inv", "model-00005-of-00141.safetensors", "F32", [16, 48], [12, 24]),
        ("up_proj.weight", "model-00005-of-00141.safetensors", "F8_E4M3", [2048, 6144], [24, 36]),
        ("up_proj.weight_scale_inv", "model-00005-of-00141.safetensors", "F32", [16, 48], [36, 48]),
        ("down_proj.weight", "model-00006-of-00141.safetensors", "F8_E4M3", [6144, 2048], [0, 12]),
        ("down_proj.weight_scale_inv", "model-00006-of-00141.safetensors", "F32", [48, 16], [12, 24]),
    ]
    headers = {}
    for suffix, shard, dtype, shape, offsets in roles:
        key = prefix + suffix
        wm[key] = shard
        headers.setdefault(shard, {})[key] = {
            "dtype": dtype,
            "shape": shape,
            "data_offsets": offsets,
        }
    idx = json.dumps({"weight_map": wm}, sort_keys=True, separators=(",", ":")).encode()
    return idx, hashlib.sha256(idx).hexdigest(), wm, headers


def _transports():
    idx, sha, wm, headers = _fixture()

    def full(url, max_bytes):
        assert "model.safetensors.index.json" in url
        assert max_bytes >= len(idx)
        return idx

    calls = []

    def rng(url, start, length):
        shard = url.split("/")[-1].split("?")[0]
        raw = json.dumps(headers[shard], sort_keys=True, separators=(",", ":")).encode()
        if start == 0:
            assert length == 8
            out = struct.pack("<Q", len(raw))
        else:
            assert start == 8 and length == len(raw)
            out = raw
        calls.append((shard, start, length))
        return out

    return idx, sha, wm, headers, full, rng, calls


def test_resolve_url_pins_commit():
    url = hf_resolve_url(REPO, REV, "model.safetensors.index.json")
    assert REV in url and "/resolve/" in url and "main" not in url


@pytest.mark.parametrize("bad", ["main", "7cda819", "", "z" * 40])
def test_revision_must_be_40hex(bad):
    with pytest.raises(HeaderTransportError):
        hf_resolve_url(REPO, bad, "x")


@pytest.mark.parametrize(
    "bad", ["../x", "/x", "model-x.safetensors", "model-00001-of-00141.bin"]
)
def test_shard_names_fail_closed_via_index(bad):
    idx, _, _, _, _, _, _ = _transports()
    broken = json.loads(idx)
    broken["weight_map"][next(iter(broken["weight_map"]))] = bad
    raw = json.dumps(broken, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(HeaderTransportError):
        fetch_index(
            repo_id=REPO,
            model_revision=REV,
            expected_index_sha256=hashlib.sha256(raw).hexdigest(),
            read_full=lambda _u, _m: raw,
        )


def test_index_digest_mismatch():
    idx, _, _, _ = _fixture()
    with pytest.raises(HeaderTransportError) as exc:
        fetch_index(
            repo_id=REPO,
            model_revision=REV,
            expected_index_sha256="0" * 64,
            read_full=lambda _u, _m: idx,
        )
    assert exc.value.code == "INDEX_SHA256_MISMATCH"


def test_representative_six_keys_required():
    _, _, wm, _ = _fixture()
    keys = representative_expert_keys(wm, layer=3, expert=0)
    assert len(keys) == 6
    wm.pop(keys[-1])
    with pytest.raises(HeaderTransportError) as exc:
        representative_expert_keys(wm, layer=3, expert=0)
    assert exc.value.code == "REPRESENTATIVE_KEYS_MISSING"


def test_header_length_ceiling():
    def rr(_url, start, _length):
        return struct.pack("<Q", 65 * 1024 * 1024) if start == 0 else b""

    with pytest.raises(HeaderTransportError) as exc:
        fetch_safetensors_header(shard_url="x", read_range=rr)
    assert exc.value.code == "HEADER_LENGTH_OUT_OF_BOUNDS"


def test_collect_reads_headers_only_and_groups_shards():
    _, sha, _, _, full, rng, calls = _transports()
    receipt = collect_header_evidence(
        repo_id=REPO,
        model_revision=REV,
        expected_index_sha256=sha,
        read_full=full,
        read_range=rng,
    )
    assert len(receipt.entries) == 6
    assert receipt.payload_bytes_read == 0
    assert not receipt.g2_admitted and not receipt.authority
    assert len([call for call in calls if call[1] == 0]) == 2
    assert len([call for call in calls if call[1] == 8]) == 2
    entries = {entry.tensor_key: entry for entry in receipt.entries}
    assert entries["model.layers.3.mlp.experts.0.gate_proj.weight"].shape == (2048, 6144)
    assert entries["model.layers.3.mlp.experts.0.down_proj.weight_scale_inv"].shape == (48, 16)


def test_missing_tensor_in_header_fails():
    _, sha, _, headers, full, rng, _ = _transports()
    first_shard = next(iter(headers))
    headers[first_shard].pop(next(iter(headers[first_shard])))
    with pytest.raises(HeaderTransportError) as exc:
        collect_header_evidence(
            repo_id=REPO,
            model_revision=REV,
            expected_index_sha256=sha,
            read_full=full,
            read_range=rng,
        )
    assert exc.value.code == "TENSOR_HEADER_ENTRY_MISSING"


@pytest.mark.parametrize(
    "field,bad",
    [
        ("dtype", ""),
        ("shape", []),
        ("shape", [1, -1]),
        ("data_offsets", [5, 4]),
        ("data_offsets", [0, "1"]),
    ],
)
def test_invalid_header_fields_fail(field, bad):
    _, sha, _, headers, full, rng, _ = _transports()
    first_shard = next(iter(headers))
    first_key = next(iter(headers[first_shard]))
    headers[first_shard][first_key][field] = bad
    with pytest.raises(HeaderTransportError):
        collect_header_evidence(
            repo_id=REPO,
            model_revision=REV,
            expected_index_sha256=sha,
            read_full=full,
            read_range=rng,
        )


def test_receipt_digest_deterministic():
    _, sha, _, _, full, rng, _ = _transports()
    a = collect_header_evidence(
        repo_id=REPO,
        model_revision=REV,
        expected_index_sha256=sha,
        read_full=full,
        read_range=rng,
    )
    _, sha, _, _, full, rng, _ = _transports()
    b = collect_header_evidence(
        repo_id=REPO,
        model_revision=REV,
        expected_index_sha256=sha,
        read_full=full,
        read_range=rng,
    )
    assert a.receipt_digest == b.receipt_digest
