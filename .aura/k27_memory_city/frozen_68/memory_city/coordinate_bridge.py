"""Versioned coordinate types. A hash bucket is never a city address."""
from dataclasses import dataclass
import re
from k27_city import K27Path, digit_from_xyz
from world_atlas import FrameAddress

CITY_SCHEME = 'MC-K27-RECURSIVE-TRITS-v1'
BUCKET_SCHEME = 'K27-B3MOD27-XYZ-v1'
OCTANT_SCHEME = 'K27-LOCAL-CORNERS-v1'

def nonempty(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be a nonempty string')
    return value

def checked_path(value):
    if not isinstance(value, tuple) or any(type(d) is not int or not 0 <= d <= 26 for d in value):
        raise ValueError('recursive path requires a tuple of integer digits 0..26')
    if len(value) > 128:
        raise ValueError('reference implementation path depth limit is 128')
    return K27Path(value)

def checked_address(address):
    if not isinstance(address, FrameAddress):
        raise ValueError('explicit Memory City FrameAddress required')
    for key in ('frame_id', 'frame_generation', 'canonical_ref'):
        nonempty(getattr(address, key), key)
    checked_path(address.path)
    return address

def path_key(digits):
    checked_path(digits)
    return '/' + ''.join(f'{d:02d}/' for d in digits)

@dataclass(frozen=True)
class DigestBucket:
    xyz: tuple[int, int, int]
    scheme: str = BUCKET_SCHEME

def digest_bucket(full_digest):
    if not isinstance(full_digest, str) or not re.fullmatch('[0-9a-f]{64}', full_digest):
        raise ValueError('bucket requires a full lowercase SHA-256 digest')
    return DigestBucket(tuple(b % 27 for b in bytes.fromhex(full_digest)[:3]))

def local_octants():
    """The eight corner cells of one 3x3x3 neighborhood, not eight universes."""
    return tuple(digit_from_xyz(x,y,z) for x in (0,2) for y in (0,2) for z in (0,2))

def address_record(address):
    checked_address(address)
    return {'scheme':CITY_SCHEME, 'frame_id':address.frame_id,
            'frame_generation':address.frame_generation, 'path':list(address.path),
            'canonical_ref':address.canonical_ref}
