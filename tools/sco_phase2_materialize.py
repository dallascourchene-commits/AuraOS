from __future__ import annotations

import base64
import gzip
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / '.aura' / 'phase2_payload'

FILES = {
    'aura_construction_contracts.py': ('contracts.py.gz', 'gzip', '8e5e06ee9d1a046d81f99c477b57a9be2d26057e95de3301f8b324a917c09e42'),
    'aura_construction_state.py': ('state.py.gz', 'gzip', 'efd7f393d5411d57ec5669016dfbe9de3fc2215b5c23f4655c4b538363b5f7a0'),
    'aura_construction_authority.py': ('authority.py.gz', 'gzip', '16056d9be7bc4a05dfd2dd7ae921fb7d6119ec810b09c28cf570c02b4a2b01cd'),
    'tests/test_aura_construction_contracts.py': ('test_contracts.py.gz', 'gzip', '95676c8bb4b623607e3d7c5f9a416b108f00fa9db6791f8f13686da91c526700'),
    'tests/test_aura_construction_state.py': ('test_state.py.gz.b64', 'b64_gzip', 'c92c795cda759ac7899bca0e4be331574da828a6ee84d34da876cc47d6b3e771'),
    'tests/test_aura_construction_authority.py': ('test_authority.py.gz.b64.hex', 'hex_b64_gzip', '7e518e73d233447b5bf01b31d8f1d4f36180dc2d7448c1cd9bcc5ac5b6ff6223'),
}


def decode(path: Path, mode: str) -> bytes:
    raw = path.read_bytes()
    if mode == 'gzip':
        return gzip.decompress(raw)
    if mode == 'b64_gzip':
        return gzip.decompress(base64.b64decode(raw, validate=True))
    if mode == 'hex_b64_gzip':
        b64 = bytes.fromhex(raw.decode('ascii'))
        return gzip.decompress(base64.b64decode(b64, validate=True))
    raise ValueError(f'unknown payload mode: {mode}')


def main() -> None:
    for target, (payload_name, mode, expected) in FILES.items():
        data = decode(PAYLOAD / payload_name, mode)
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise SystemExit(f'hash mismatch for {target}: {actual} != {expected}')
        destination = ROOT / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        if hashlib.sha256(destination.read_bytes()).hexdigest() != expected:
            raise SystemExit(f'post-write verification failed for {target}')
        print(f'MATERIALIZED {target} sha256={expected}')


if __name__ == '__main__':
    main()
