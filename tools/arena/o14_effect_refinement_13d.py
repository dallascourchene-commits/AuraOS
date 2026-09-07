from __future__ import annotations
from hashlib import sha256
import itertools,json
from campaign_memory_city_effect_refinement_handoff_o14 import fixture
from memory_city_effect_handoff_o13 import HandoffDisposition
from memory_city_effect_refinement_handoff_o14 import compile_effect_refined_handoff
from o14_effect_refinement_lattice import run as run8

def run():
    hard=run8(); cert,kw,ref,current=fixture("13d-context"); roots=set(); routes=0; effect_ready=0
    for _context in itertools.product(range(3),repeat=5):
        d=compile_effect_refined_handoff(cert,**kw,refinement=ref,refinement_verification=current)
        routes+=d.disposition is HandoffDisposition.HOLD_TECC_REQUIRED_D0;effect_ready+=d.effect_authority;roots.add(d.tecc_input_root)
    total=hard["counts"]["states"]*243; valid=hard["counts"]["candidate_tecc"]*243
    payload={"schema":"AURA-O14-13D-FACTORED-v2-INTEGRATED","hard_states":hard["counts"]["states"],"hard_keepers":hard["counts"]["candidate_tecc"],"context_states":243,"total_states":total,"valid_contextual_tecc_routes":valid,"nonroutes":total-valid,"hard_invalid_repairs":hard["counts"]["false_tecc"],"context_execution_routes":routes,"tecc_root_variants_across_context":len(roots),"effect_ready":effect_ready,"omega8_root":hard["root"]};payload["root"]=sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest();return payload
if __name__=="__main__":print(json.dumps(run(),sort_keys=True,separators=(",",":")))
