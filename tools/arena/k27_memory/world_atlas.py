from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple, FrozenSet

KPath = Tuple[int, ...]

def validate_path(path: KPath) -> None:
    if any(type(d) is not int or d < 0 or d > 26 for d in path):
        raise ValueError('K27 digit out of range')

@dataclass(frozen=True)
class WorldFrame:
    frame_id: str
    generation: str
    epoch: str
    kind: str  # CANONICAL/OBSERVATIONAL/CONVENTIONAL/GENERATED
    current: bool = True

@dataclass(frozen=True)
class FrameAddress:
    frame_id: str
    frame_generation: str
    path: KPath
    canonical_ref: str

    def __post_init__(self):
        frozen = tuple(self.path)
        validate_path(frozen)
        object.__setattr__(self, 'path', frozen)

@dataclass(frozen=True)
class FrameTransform:
    src_frame: str
    src_generation: str
    dst_frame: str
    dst_generation: str
    # reversible digit transform: axis permutation and optional per-axis inversion
    axis_perm: Tuple[int, int, int] = (0, 1, 2)
    invert: Tuple[bool, bool, bool] = (False, False, False)
    current: bool = True

    def __post_init__(self):
        if (not isinstance(self.axis_perm, tuple) or len(self.axis_perm) != 3
                or any(type(v) is not int for v in self.axis_perm)
                or tuple(sorted(self.axis_perm)) != (0,1,2)):
            raise ValueError('axis_perm must be a permutation of exact ints (0,1,2)')
        if (not isinstance(self.invert, tuple) or len(self.invert) != 3
                or any(type(v) is not bool for v in self.invert)):
            raise ValueError('invert must contain exactly three bool flags')

    @staticmethod
    def _decode(d: int) -> Tuple[int,int,int]:
        if type(d) is not int or not 0 <= d < 27:
            raise ValueError('digit must be exact int 0..26')
        return d % 3, (d // 3) % 3, (d // 9) % 3

    @staticmethod
    def _encode(t: Tuple[int,int,int]) -> int:
        x,y,z=t
        return x + 3*y + 9*z

    def apply_digit(self, d: int) -> int:
        xyz = self._decode(d)
        out=[]
        for j, src_axis in enumerate(self.axis_perm):
            v=xyz[src_axis]
            if self.invert[j]:
                v=2-v
            out.append(v)
        return self._encode(tuple(out))

    def apply(self, path: KPath) -> KPath:
        if not self.current:
            raise ValueError('stale transform')
        validate_path(path)
        return tuple(self.apply_digit(d) for d in path)

class FrameAtlas:
    def __init__(self):
        self.frames: Dict[str, WorldFrame] = {}
        self.transforms: Dict[Tuple[str,str], FrameTransform] = {}

    def add_frame(self, frame: WorldFrame):
        self.frames[frame.frame_id] = frame

    def add_transform(self, t: FrameTransform):
        # FrameTransform construction already proves reversibility shape. Keep the
        # check here as a fail-closed boundary for subclass/foreign objects.
        if not isinstance(t, FrameTransform):
            raise ValueError('transform must be a validated FrameTransform')
        self.transforms[(t.src_frame, t.dst_frame)] = t

    def project(self, addr: FrameAddress, dst_frame_id: str) -> FrameAddress:
        src = self.frames.get(addr.frame_id)
        dst = self.frames.get(dst_frame_id)
        if not src or not dst or not src.current or not dst.current:
            raise ValueError('frame unavailable/stale')
        if src.generation != addr.frame_generation:
            raise ValueError('source address generation stale')
        if src.frame_id == dst.frame_id:
            return addr
        t = self.transforms.get((src.frame_id, dst.frame_id))
        if not t or not t.current:
            raise ValueError('current explicit transform required')
        if t.src_generation != src.generation or t.dst_generation != dst.generation:
            raise ValueError('transform generation mismatch')
        return FrameAddress(dst.frame_id, dst.generation, t.apply(addr.path), addr.canonical_ref)

class PrefixCoverage:
    """Frame-local coverage. Prefixes summarize all descendant K27 cells."""
    def __init__(self, frame_id: str, frame_generation: str, prefixes: Iterable[KPath]=()):
        self.frame_id=frame_id
        self.frame_generation=frame_generation
        self.prefixes=frozenset(self._normalize(set(prefixes)))

    @staticmethod
    def _normalize(ps: set[KPath]) -> set[KPath]:
        for p in ps: validate_path(p)
        # If ancestor exists, descendant is redundant.
        out=set(ps)
        for p in list(out):
            for k in range(len(p)):
                if p[:k] in out:
                    out.discard(p); break
        # K27 recursion: 27 complete children collapse to parent.
        changed=True
        while changed:
            changed=False
            parents={p[:-1] for p in out if p}
            for par in sorted(parents, key=len, reverse=True):
                children={par+(d,) for d in range(27)}
                if children <= out:
                    out.difference_update(children)
                    out.add(par)
                    changed=True
        return out

    def covers(self, addr: FrameAddress) -> bool:
        if addr.frame_id != self.frame_id or addr.frame_generation != self.frame_generation:
            return False
        return any(addr.path[:len(p)] == p for p in self.prefixes)

    def records(self) -> int:
        return len(self.prefixes)

@dataclass(frozen=True)
class WorldPortal:
    portal_id: str
    src_frame: str
    dst_frame: str
    transform_key: Tuple[str,str]
    # Navigation only. Authority is explicitly absent.
    authority: None = None

def zoom_lineage(addr: FrameAddress) -> Tuple[KPath, ...]:
    """World/city/neighborhood-like zoom is just prefixes; labels are external profiles."""
    return tuple(addr.path[:i] for i in range(len(addr.path)+1))
