from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json

from k27_memory_city_spatial_seam import SeamDisposition, validate_spatial_seam

ROOT = Path(__file__).resolve().parents[3]
route = json.loads((ROOT / ".aura/arena_routes/spatial.v1.json").read_text())
manifest = {"files":{"k27_memory/cold_sources/MC-SRC-O1O9.md":{"sha256":"b2cb2a2c1ebe65848d61da4db6225dbce2c686357bb427e1584468c44787a5a7"}}}
compile_idx = next(i for i,t in enumerate(route["transitions"]) if t["transition_id"] == "SPATIAL.GROUND.COMPILE_SCENE")

families = (
    "source_root", "archive_digest", "scene_digest", "schema", "adapter", "projection_law",
    "api_scope", "projection_only", "execution_authority", "effect_authority",
)
receipts=[]; false_accepts=0; valid_failures=0; holds=0
for i in range(1000):
    family=families[i % len(families)]
    r=deepcopy(route); b=r["transitions"][compile_idx]["memory_city_binding"]
    if family=="source_root": b["source_root"]="outputs/other/"
    elif family=="archive_digest": b["provenance_archive_sha256"]="0"*64
    elif family=="scene_digest": b["scene_source_sha256"]="1"*64
    elif family=="schema": b["scene_schema"]="OTHER"
    elif family=="adapter": b["adapters"][i%3]="other"
    elif family=="projection_law": b["projection_laws"][i%4]="Other!=Law"
    elif family=="api_scope": b["read_apis"][sorted(b["read_apis"])[i%6]]="EXECUTE"
    elif family=="projection_only": b["projection_only"]=False
    elif family=="execution_authority": b["execution_authority"]=True
    elif family=="effect_authority": b["effect_authority"]=True
    rec=validate_spatial_seam(json.dumps(r,separators=(",",":")).encode(), manifest)
    if rec.disposition is not SeamDisposition.HOLD: false_accepts+=1
    else: holds+=1
    receipts.append(rec.receipt_root)

valid=validate_spatial_seam((ROOT / ".aura/arena_routes/spatial.v1.json").read_bytes(), manifest)
if valid.disposition is not SeamDisposition.READY_FOR_INDEPENDENT_REVIEW: valid_failures+=1
root=sha256("".join(receipts+[valid.receipt_root]).encode()).hexdigest()
print(json.dumps({
    "schema":"AURA-K27-SPATIAL-SEAM-CAMPAIGN-v1",
    "cases":1000,
    "families":families,
    "holds":holds,
    "false_accepts":false_accepts,
    "valid_failures":valid_failures,
    "campaign_root":root,
}, indent=2))
if false_accepts or valid_failures: raise SystemExit(1)
