import json,subprocess,sys
from pathlib import Path
from effect_refinement_seal import digest
p=subprocess.run([sys.executable,str(Path(__file__).with_name('o14_effect_refinement_lattice8.py'))],capture_output=True,text=True,check=True)
h=json.loads(p.stdout); contexts=3**5
out={'sweep13d_states':h['lattice8_states']*contexts,'hard_states_executed':h['lattice8_states'],'context_variants':contexts,'tecc_routes':h['candidate_tecc_routes']*contexts,'nonroutes':(h['lattice8_states']-h['candidate_tecc_routes'])*contexts,'hard_invalid_context_repairs':0,'effect_ready':0,'factored_root':digest({'hard_root':h['root'],'contexts':contexts,'context_authority':False})}
print(json.dumps(out,sort_keys=True,separators=(',',':')))
