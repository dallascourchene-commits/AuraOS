"""D0 indexed E8-derived expert-page reference for the AWJ032 GLM-5.3 campaign.

This is a clean-room research/falsifier implementation. It is not QuIP#, QTIP,
EXL3/TR3, or a production GLM quantizer.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import itertools
import json
import math
import struct
from typing import Any

import numpy as np

SCHEME = "AURA_E8_BALL10_16BIT_REF_V1"
K27_SCHEME = "K27-SHA256-MOD27-v1"
MAGIC = b"A8Q1"
VECTOR_DIM = 8
INDEX_BITS = 16
DEFAULT_BLOCK_SIZE = 64
TENSOR_ROLES = frozenset({"gate_up_proj", "down_proj"})


def _json(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _half_away(x: np.ndarray) -> np.ndarray:
    return np.where(x >= 0, np.floor(x + 0.5), np.ceil(x - 0.5))


def quantize_dn(x: np.ndarray) -> np.ndarray:
    """Nearest D_n point: integer coordinates with even coordinate sum."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim < 1:
        raise ValueError("x must have at least one dimension")
    q = _half_away(x)
    odd = (np.abs(q.sum(axis=-1).astype(np.int64)) % 2) == 1
    if not np.any(odd):
        return q
    err = np.abs(x - q)
    k = np.argmax(err, axis=-1)
    xf, qf, of, kf = x.reshape(-1, x.shape[-1]), q.reshape(-1, q.shape[-1]), odd.reshape(-1), k.reshape(-1)
    for i in np.flatnonzero(of):
        j = int(kf[i])
        qf[i, j] += 1.0 if xf[i, j] >= qf[i, j] else -1.0
    return q


def quantize_e8_unbounded(x: np.ndarray) -> np.ndarray:
    """Nearest point in E8 = D8 union (D8 + 1/2 * 1)."""
    x = np.asarray(x, dtype=np.float64)
    if x.shape[-1] != 8:
        raise ValueError("E8 requires 8D vectors")
    a = quantize_dn(x)
    b = quantize_dn(x - 0.5) + 0.5
    da = np.sum((x - a) ** 2, axis=-1, keepdims=True)
    db = np.sum((x - b) ** 2, axis=-1, keepdims=True)
    return np.where(da <= db, a, b)


def doubled_coordinates(points: np.ndarray) -> np.ndarray:
    """Losslessly witness integer/half-integer lattice coordinates as 2*x int16."""
    p = np.asarray(points, dtype=np.float64)
    z = np.rint(p * 2.0)
    if p.shape[-1] != 8 or not np.array_equal(p * 2.0, z):
        raise ValueError("not a half-integer 8D lattice point")
    return z.astype(np.int16)


def undouble_coordinates(encoded: np.ndarray) -> np.ndarray:
    z = np.asarray(encoded, dtype=np.int16)
    if z.shape[-1] != 8:
        raise ValueError("encoded point must be 8D")
    return z.astype(np.float64) * 0.5


def _build_codebook() -> np.ndarray:
    """Build a deterministic finite E8-derived shifted codebook.

    227 absolute D8+1/2 representatives inside radius^2<=10 are expanded by
    parity-valid signs and +/-1/4 shifts. The resulting 58,112 vectors fit in
    uint16. Unlike raw lattice coordinates, a uint16 code index is actually
    16 bits per 8 weights.
    """
    reps: list[np.ndarray] = []
    for vals in itertools.product((0.5, 1.5, 2.5, 3.5), repeat=8):
        v = np.asarray(vals, dtype=np.float32)
        if float(v @ v) <= 10.0:
            reps.append(v)
    if len(reps) != 227:
        raise AssertionError(f"unexpected representative count {len(reps)}")
    signs = np.asarray(list(itertools.product((-1.0, 1.0), repeat=8)), dtype=np.float32)
    parts: list[np.ndarray] = []
    for rep in reps:
        s = rep[None, :] * signs
        s = s[(np.rint(s.sum(axis=1)).astype(np.int64) % 2) == 0]
        if s.shape[0] != 128:
            raise AssertionError("parity expansion failed")
        parts.extend((s - 0.25, s + 0.25))
    grid = np.unique(np.concatenate(parts), axis=0).astype(np.float32, copy=False)
    if grid.shape != (58112, 8):
        raise AssertionError(f"unexpected codebook shape {grid.shape}")
    return grid


_GRID: np.ndarray | None = None
_GRID_N2: np.ndarray | None = None


def codebook() -> tuple[np.ndarray, np.ndarray]:
    global _GRID, _GRID_N2
    if _GRID is None:
        _GRID = _build_codebook()
        _GRID_N2 = np.sum(_GRID * _GRID, axis=1)
    return _GRID, _GRID_N2  # type: ignore[return-value]


def codebook_digest() -> str:
    return _sha(np.asarray(codebook()[0], dtype="<f4").tobytes(order="C"))


def nearest_code(vectors: np.ndarray, chunk: int = 64) -> tuple[np.ndarray, np.ndarray]:
    v = np.asarray(vectors, dtype=np.float32)
    if v.ndim != 2 or v.shape[1] != 8 or chunk <= 0:
        raise ValueError("vectors must be [N,8] and chunk positive")
    grid, n2 = codebook()
    out = np.empty_like(v)
    idxs = np.empty(v.shape[0], dtype=np.uint16)
    for start in range(0, len(v), chunk):
        x = v[start:start + chunk]
        idx = np.argmax(2.0 * (x @ grid.T) - n2[None, :], axis=1)
        out[start:start + len(x)] = grid[idx]
        idxs[start:start + len(x)] = idx.astype(np.uint16)
    return out, idxs


@dataclass(frozen=True)
class Compressed:
    indices: np.ndarray
    scales: np.ndarray
    shape: tuple[int, ...]
    pad: int
    block_size: int

    def validate(self) -> None:
        if self.indices.dtype != np.uint16 or self.scales.dtype != np.float16:
            raise TypeError("indices/scales dtype mismatch")
        if self.block_size <= 0 or self.block_size % 8:
            raise ValueError("invalid block size")
        if self.indices.ndim != 2 or self.indices.shape[1] != self.block_size // 8:
            raise ValueError("invalid index shape")
        if self.scales.shape != (self.indices.shape[0],):
            raise ValueError("invalid scale shape")
        if self.pad < 0 or self.pad >= self.block_size:
            raise ValueError("invalid pad")
        if self.indices.size and int(self.indices.max()) >= len(codebook()[0]):
            raise ValueError("code index outside codebook")


def codec_bpw(num_weights: int, block_size: int = 64) -> float:
    if num_weights <= 0 or block_size <= 0 or block_size % 8:
        raise ValueError("invalid rate input")
    padded = num_weights + (-num_weights % block_size)
    return ((padded // 8) * 16 + (padded // block_size) * 16) / num_weights


def compress(weight: np.ndarray, block_size: int = 64) -> Compressed:
    w = np.asarray(weight, dtype=np.float32)
    if w.size == 0 or block_size <= 0 or block_size % 8:
        raise ValueError("invalid tensor/block size")
    flat = w.reshape(-1)
    pad = -flat.size % block_size
    if pad:
        flat = np.pad(flat, (0, pad))
    blocks = flat.reshape(-1, block_size)
    scales = np.sqrt(np.mean(blocks * blocks, axis=1, dtype=np.float64)).astype(np.float32)
    scales = np.maximum(scales, np.float32(1e-12))
    _, idx = nearest_code((blocks / scales[:, None]).reshape(-1, 8))
    c = Compressed(idx.reshape(len(blocks), block_size // 8), scales.astype(np.float16), tuple(w.shape), int(pad), block_size)
    c.validate()
    return c


def decompress(c: Compressed) -> np.ndarray:
    c.validate()
    q = codebook()[0][c.indices.reshape(-1)].reshape(len(c.indices), c.block_size)
    flat = (q * c.scales.astype(np.float32)[:, None]).reshape(-1)
    if c.pad:
        flat = flat[:-c.pad]
    return flat.reshape(c.shape)


def scalar4_reference(weight: np.ndarray, block_size: int = 64) -> np.ndarray:
    """Four-level scalar comparator with the same RMS-scale overhead."""
    w = np.asarray(weight, dtype=np.float32)
    flat = w.reshape(-1)
    pad = -flat.size % block_size
    if pad:
        flat = np.pad(flat, (0, pad))
    b = flat.reshape(-1, block_size)
    s = np.sqrt(np.mean(b * b, axis=1, dtype=np.float64)).astype(np.float32)
    s = np.maximum(s, np.float32(1e-12))
    z = b / s[:, None]
    levels = np.asarray([-1.5, -0.5, 0.5, 1.5], dtype=np.float32)
    i = np.argmin((z[..., None] - levels) ** 2, axis=-1)
    out = (levels[i] * s[:, None]).reshape(-1)
    if pad:
        out = out[:-pad]
    return out.reshape(w.shape)


def k27_from_digest(digest: str) -> tuple[int, int, int]:
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("SHA-256 digest required")
    try:
        raw = bytes.fromhex(digest)
    except ValueError as exc:
        raise ValueError("hex digest required") from exc
    return raw[0] % 27, raw[1] % 27, raw[2] % 27


@dataclass(frozen=True)
class ExpertPageIdentity:
    model_revision: str
    representation_revision: str
    layer_id: int
    expert_id: int
    tensor_role: str
    source_tensor_sha256: str
    source_shape: tuple[int, ...]
    block_size: int = 64
    scheme: str = SCHEME

    def validate(self) -> None:
        if not self.model_revision or not self.representation_revision:
            raise ValueError("revision identity required")
        if type(self.layer_id) is not int or self.layer_id < 0 or type(self.expert_id) is not int or self.expert_id < 0:
            raise ValueError("invalid layer/expert")
        if self.tensor_role not in TENSOR_ROLES:
            raise ValueError("unsupported tensor role")
        if not self.source_shape or any(type(x) is not int or x <= 0 for x in self.source_shape):
            raise ValueError("invalid source shape")
        if len(self.source_tensor_sha256) != 64:
            raise ValueError("source SHA-256 required")
        bytes.fromhex(self.source_tensor_sha256)
        if self.block_size <= 0 or self.block_size % 8 or self.scheme != SCHEME:
            raise ValueError("representation mismatch")

    def digest(self) -> str:
        self.validate()
        x = asdict(self)
        x["source_shape"] = list(self.source_shape)
        return _sha(_json(x).encode())


@dataclass(frozen=True)
class ExpertPage:
    identity: ExpertPageIdentity
    payload: bytes
    payload_sha256: str
    k27_coordinate: tuple[int, int, int]
    codec_bits_per_weight: float
    serialized_bits_per_weight: float

    def validate(self) -> None:
        self.identity.validate()
        if _sha(self.payload) != self.payload_sha256:
            raise ValueError("payload digest mismatch")
        if self.k27_coordinate != k27_from_digest(self.identity.digest()):
            raise ValueError("K27 metadata mismatch")
        n = math.prod(self.identity.source_shape)
        if not math.isclose(self.codec_bits_per_weight, codec_bpw(n, self.identity.block_size), abs_tol=1e-12):
            raise ValueError("codec rate mismatch")
        if not math.isclose(self.serialized_bits_per_weight, len(self.payload) * 8.0 / n, abs_tol=1e-12):
            raise ValueError("serialized rate mismatch")


def pack_expert_page(weight: np.ndarray, *, model_revision: str, representation_revision: str,
                     layer_id: int, expert_id: int, tensor_role: str, block_size: int = 64) -> ExpertPage:
    w = np.asarray(weight, dtype=np.float32)
    src = np.asarray(w, dtype="<f4").tobytes(order="C")
    ident = ExpertPageIdentity(model_revision, representation_revision, layer_id, expert_id,
                               tensor_role, _sha(src), tuple(int(x) for x in w.shape), block_size)
    ident.validate()
    c = compress(w, block_size)
    header = {
        "version": 1, "identity_digest": ident.digest(), "codebook_digest": codebook_digest(),
        "shape": list(c.shape), "pad": c.pad, "block_size": c.block_size,
        "num_blocks": len(c.indices), "indices_per_block": c.indices.shape[1],
        "index_dtype": "uint16-le", "scale_dtype": "float16-le",
    }
    h = _json(header).encode()
    payload = MAGIC + struct.pack("<I", len(h)) + h + np.asarray(c.indices, dtype="<u2").tobytes() + np.asarray(c.scales, dtype="<f2").tobytes()
    page = ExpertPage(ident, payload, _sha(payload), k27_from_digest(ident.digest()),
                      codec_bpw(w.size, block_size), len(payload) * 8.0 / w.size)
    page.validate()
    return page


def unpack_expert_page(page: ExpertPage) -> np.ndarray:
    page.validate()
    p = page.payload
    if len(p) < 8 or p[:4] != MAGIC:
        raise ValueError("invalid magic")
    hlen = struct.unpack("<I", p[4:8])[0]
    hend = 8 + hlen
    if hend > len(p):
        raise ValueError("truncated header")
    try:
        h = json.loads(p[8:hend])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid header") from exc
    required = {"version", "identity_digest", "codebook_digest", "shape", "pad", "block_size",
                "num_blocks", "indices_per_block", "index_dtype", "scale_dtype"}
    if set(h) != required or h["version"] != 1:
        raise ValueError("header schema/version mismatch")
    if h["identity_digest"] != page.identity.digest() or h["codebook_digest"] != codebook_digest():
        raise ValueError("identity/codebook mismatch")
    if tuple(h["shape"]) != page.identity.source_shape or h["block_size"] != page.identity.block_size:
        raise ValueError("shape/block mismatch")
    if h["index_dtype"] != "uint16-le" or h["scale_dtype"] != "float16-le":
        raise ValueError("dtype mismatch")
    nb, ipb = int(h["num_blocks"]), int(h["indices_per_block"])
    if nb <= 0 or ipb != page.identity.block_size // 8:
        raise ValueError("compressed shape mismatch")
    ib, sb = nb * ipb * 2, nb * 2
    if len(p) != hend + ib + sb:
        raise ValueError("payload length mismatch")
    idx = np.frombuffer(p, dtype="<u2", count=nb * ipb, offset=hend).copy().reshape(nb, ipb).astype(np.uint16, copy=False)
    scales = np.frombuffer(p, dtype="<f2", count=nb, offset=hend + ib).copy().astype(np.float16, copy=False)
    return decompress(Compressed(idx, scales, page.identity.source_shape, int(h["pad"]), page.identity.block_size))


def expert_page_receipt(page: ExpertPage) -> dict[str, Any]:
    page.validate()
    r = {
        "schema": "AURA_GLM53_E8_INDEXED_EXPERT_PAGE_RECEIPT_V1",
        "identity_digest": page.identity.digest(), "model_revision": page.identity.model_revision,
        "representation_revision": page.identity.representation_revision, "layer_id": page.identity.layer_id,
        "expert_id": page.identity.expert_id, "tensor_role": page.identity.tensor_role,
        "source_tensor_sha256": page.identity.source_tensor_sha256, "codebook_digest": codebook_digest(),
        "payload_sha256": page.payload_sha256, "codec_bits_per_weight": page.codec_bits_per_weight,
        "serialized_bits_per_weight": page.serialized_bits_per_weight, "k27_scheme": K27_SCHEME,
        "k27_coordinate": list(page.k27_coordinate),
        "claim_ceiling": {
            "k27_coordinate_is_expert_identity": False, "model_router_semantics_changed": False,
            "glm53_quality_preserved": False, "production_quantizer_ready": False,
            "owner_host_benchmark_performed": False, "gate10_promoted": False,
        },
    }
    r["receipt_sha256"] = _sha(_json(r).encode())
    return r


def benchmark_receipt(seed: int = 42, shape: tuple[int, int] = (32, 64), block_size: int = 64) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    w = rng.normal(0.0, 0.02, size=shape).astype(np.float32)
    e8 = decompress(compress(w, block_size))
    scalar = scalar4_reference(w, block_size)
    mse_e8 = float(np.mean((w - e8) ** 2, dtype=np.float64))
    mse_scalar = float(np.mean((w - scalar) ** 2, dtype=np.float64))
    signal = float(np.mean(w * w, dtype=np.float64))
    r = {
        "schema": "AURA_E8_QUANTIZATION_REFERENCE_RECEIPT_V1", "scheme": SCHEME,
        "seed": seed, "shape": list(shape), "block_size": block_size,
        "codebook_entries": len(codebook()[0]), "index_bits_per_8_weights": 16,
        "payload_bits_per_weight": codec_bpw(math.prod(shape), block_size),
        "mse_e8": mse_e8, "mse_scalar_4level": mse_scalar,
        "snr_e8_db": 10.0 * math.log10(signal / mse_e8),
        "snr_scalar_4level_db": 10.0 * math.log10(signal / mse_scalar),
        "e8_beats_scalar_on_fixture": mse_e8 < mse_scalar,
        "claim_ceiling": {
            "glm53_quality_preserved": False, "production_quantizer_ready": False,
            "sub_2_bpw_including_scale_overhead": False, "inference_kernel_speedup_proven": False,
            "kv_cache_toroidal_equivalence_proven": False, "physical_thinkpad_result": False,
            "gate10_promoted": False,
        },
    }
    r["receipt_sha256"] = _sha(_json(r).encode())
    return r


def verify_benchmark_receipt(r: dict[str, Any]) -> bool:
    if r.get("schema") != "AURA_E8_QUANTIZATION_REFERENCE_RECEIPT_V1" or not isinstance(r.get("receipt_sha256"), str):
        return False
    x = dict(r)
    got = x.pop("receipt_sha256")
    return got == _sha(_json(x).encode())


# Focused D0 compatibility aliases.
get_codebook = codebook
encode_e8_doubled_coordinates = doubled_coordinates
decode_e8_doubled_coordinates = undouble_coordinates
compress_weights = compress
decompress_weights = decompress
payload_bits_per_weight = codec_bpw
scalar_2bit_reference = scalar4_reference
PackedExpertPage = ExpertPage
k27_coordinate_from_digest = k27_from_digest

if __name__ == "__main__":
    print(json.dumps(benchmark_receipt(), sort_keys=True))
