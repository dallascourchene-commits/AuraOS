from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import hashlib, json

TRITS = (0,1,2)

def _trit(value:int)->bool:
    return type(value) is int and value in TRITS

def digit_from_xyz(x:int,y:int,z:int)->int:
    if not _trit(x) or not _trit(y) or not _trit(z):
        raise ValueError('trits must be exact ints 0..2')
    return x + 3*y + 9*z

def xyz_from_digit(d:int)->Tuple[int,int,int]:
    if type(d) is not int or not 0 <= d < 27: raise ValueError('digit must be exact int 0..26')
    return d%3, (d//3)%3, d//9

@dataclass(frozen=True, order=True)
class K27Path:
    digits: Tuple[int,...] = ()
    def __post_init__(self):
        if any(type(d) is not int or not 0 <= d < 27 for d in self.digits):
            raise ValueError('bad K27 digit')
    def child(self, d:int)->'K27Path': return K27Path(self.digits+(d,))
    @property
    def parent(self)->Optional['K27Path']:
        return None if not self.digits else K27Path(self.digits[:-1])
    def is_prefix_of(self, other:'K27Path')->bool:
        return other.digits[:len(self.digits)] == self.digits
    def xyz_trits(self)->Tuple[Tuple[int,...],Tuple[int,...],Tuple[int,...]]:
        xs,ys,zs=[],[],[]
        for d in self.digits:
            x,y,z=xyz_from_digit(d); xs.append(x); ys.append(y); zs.append(z)
        return tuple(xs),tuple(ys),tuple(zs)
    def morton27(self)->int:
        n=0
        for d in self.digits: n=n*27+d
        return n
    def label(self)->str: return 'K27:/' + '/'.join(f'{d:02d}' for d in self.digits)

@dataclass(frozen=True)
class OverlayRule:
    key: str
    value: str
    hard: bool=True
    delegable: bool=False
    generation: int=0

@dataclass
class Cell:
    path: K27Path
    canonical_ref: str
    semantic_role: str='cell'
    display_name: str=''
    rules: Dict[str,OverlayRule]=field(default_factory=dict)

class K27City:
    def __init__(self): self.cells: Dict[K27Path,Cell]={}
    def add(self, cell:Cell):
        if cell.path in self.cells: raise ValueError('duplicate path')
        self.cells[cell.path]=cell
    def lineage(self,path:K27Path)->List[Cell]:
        out=[]
        for i in range(len(path.digits)+1):
            p=K27Path(path.digits[:i])
            if p in self.cells: out.append(self.cells[p])
        return out
    def effective_rules(self,path:K27Path)->Dict[str,OverlayRule]:
        eff: Dict[str,OverlayRule]={}
        for cell in self.lineage(path):
            for k,r in cell.rules.items():
                prior=eff.get(k)
                if prior:
                    if prior.hard and not r.hard:
                        raise ValueError(f'illegal hard-guard weakening: {k}')
                    if not prior.delegable and r.delegable:
                        raise ValueError(f'illegal delegation widening: {k}')
                    if prior.hard and not prior.delegable and prior.value != r.value:
                        raise ValueError(f'illegal hard-guard override: {k}')
                eff[k]=r
        return eff
    def rename(self,path:K27Path,new_name:str): self.cells[path].display_name=new_name
    def stable_identity(self,path:K27Path)->str:
        c=self.cells[path]
        raw=json.dumps({'canonical_ref':c.canonical_ref,'k27':c.path.digits},sort_keys=True,separators=(',',':'))
        return hashlib.sha256(raw.encode()).hexdigest()

SCALE_DEFAULT=('world','continent','country','region','city','neighborhood','block','building','room')
def scale_role(depth:int, profile:Sequence[str]=SCALE_DEFAULT)->str:
    return profile[depth] if depth < len(profile) else f'cell_d{depth}'
