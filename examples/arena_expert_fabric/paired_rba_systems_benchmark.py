from pathlib import Path
import json
from expert_fabric import Task, choose

DOMAINS=("publication","runtime","memory","media","safety","economics")
HARD={
    "COORDINATE_MEMORY": (),
    "SEMANTIC_COMPILER": ("COORDINATE_MEMORY",),
    "PROJECT006_RUNTIME": ("SEMANTIC_COMPILER",),
    "ARENA_CORE": ("COORDINATE_MEMORY", "SEMANTIC_COMPILER", "PROJECT006_RUNTIME"),
    "TEMPORAL_ARENA": ("ARENA_CORE", "COORDINATE_MEMORY", "PROJECT006_RUNTIME"),
    "HYPERDRIVE": ("COORDINATE_MEMORY", "SEMANTIC_COMPILER"),
    "HYPERSCALE": ("ARENA_CORE", "COORDINATE_MEMORY"),
    "LIFEOS_PLACES": ("COORDINATE_MEMORY", "ARENA_CORE"),
    "CREATOR_STUDIO": ("ARENA_CORE", "COORDINATE_MEMORY", "PROJECT006_RUNTIME"),
    "WEB4": ("ARENA_CORE", "COORDINATE_MEMORY", "PROJECT006_RUNTIME"),
    "PAPER_X": ("SEMANTIC_COMPILER", "HYPERDRIVE", "HYPERSCALE", "ARENA_CORE"),
    "MINI_AURA": ("PAPER_X", "ARENA_CORE", "HYPERDRIVE", "HYPERSCALE"),
    "README_GITHUB": ("PAPER_X", "MINI_AURA"),
    "PR_CAMPAIGN": ("PAPER_X", "CREATOR_STUDIO", "LIFEOS_PLACES", "WEB4"),
    "SWARM_RUNTIME": ("ARENA_CORE", "PROJECT006_RUNTIME", "HYPERSCALE"),
    "AMORTIZED_INTELLIGENCE": ("COORDINATE_MEMORY", "HYPERDRIVE"),
}

def closure(seeds):
    seen=set(); q=list(seeds)
    while q:
        x=q.pop()
        if x in seen: continue
        seen.add(x); q.extend(HARD[x])
    return seen

TASKS=[
  dict(id='T1',name='Paper X claim/currentness audit',seeds=['PAPER_X'],lens=['publication','safety'],expert='source_currentness',cls='audit',det=True),
  dict(id='T2',name='PR campaign refresh',seeds=['PR_CAMPAIGN'],lens=['publication','media'],expert='runtime_code',cls='edit',tool=True),
  dict(id='T3',name='README currentness refresh',seeds=['README_GITHUB'],lens=['publication','runtime'],expert='source_currentness',cls='sync',det=True),
  dict(id='T4',name='Resident runtime housekeeping',seeds=['PROJECT006_RUNTIME','TEMPORAL_ARENA'],lens=['runtime','safety'],expert='runtime_code',cls='repair',tool=True),
  dict(id='T5',name='LifeOS privacy batch review',seeds=['LIFEOS_PLACES'],lens=['safety','memory'],expert='deep_private_reasoning',cls='review',privacy='strict_local',latency='batch'),
  dict(id='T6',name='Web4 cross-domain capability research',seeds=['WEB4'],lens=['economics','safety'],expert='cross_domain_research',cls='research',diversity=True),
  dict(id='T7',name='Creator Studio affected-media currentness',seeds=['CREATOR_STUDIO'],lens=['media','safety'],expert='source_currentness',cls='affected_cone',det=True),
  dict(id='T8',name='Swarm frontier / benchmark allocation',seeds=['SWARM_RUNTIME'],lens=['runtime','economics'],expert='batch_falsification',cls='benchmark',benchmark=True),
  dict(id='T9',name='Amortized-intelligence falsification',seeds=['AMORTIZED_INTELLIGENCE'],lens=['economics','memory'],expert='batch_falsification',cls='falsify',latency='batch'),
]

ALL=len(HARD)*len(DOMAINS)
UNIT_BYTES=4096
CAPSULE_BYTES=2048
rows=[]
for t in TASKS:
    cl=closure(set(t['seeds']))
    r_proj=ALL
    b_proj=len(cl)*len(DOMAINS)
    a_proj=len(cl)*len(t['lens'])
    task=Task(
        sid=f"BENCH:{t['id']}", generation=1, domain=t['expert'], task_class=t['cls'],
        privacy=t.get('privacy','standard'), latency=t.get('latency','normal'),
        tool_required=t.get('tool',False), benchmark_mode=t.get('benchmark',False),
        diversity_needed=t.get('diversity',False), deterministic_sufficient=t.get('det',False)
    )
    route=choose(task,local_airllm_available=True)
    selected=route.get('selected',[])
    model_calls=0 if selected==['NO_MODEL'] else (3 if selected==['OPENROUTER_TRIAD'] else 1)
    rows.append({
        'task':t['id'],'name':t['name'],'closure_objects':len(cl),'lens_domains':t['lens'],
        'R_projections':r_proj,'B_projections':b_proj,'A_projections':a_proj,
        'R_bytes':r_proj*UNIT_BYTES,'B_bytes':b_proj*UNIT_BYTES,'A_bytes':a_proj*UNIT_BYTES+CAPSULE_BYTES,
        'A_route':selected,'A_model_calls_policy':model_calls,'A_k27_prefix6':route.get('k27_prefix_6'),
    })

def total(k): return sum(r[k] for r in rows)
R=total('R_bytes'); B=total('B_bytes'); A=total('A_bytes')
summary={
  'benchmark_class':'DETERMINISTIC_ROUTING_HYDRATION_ABLATION_NOT_MODEL_QUALITY',
  'graph':{'objects':len(HARD),'domains':len(DOMAINS),'all_projections':ALL,'synthetic_equal_projection_bytes':UNIT_BYTES,'workcapsule_bytes_per_A_task':CAPSULE_BYTES},
  'tasks':len(rows),
  'total_bytes':{'R_regular':R,'B_rebase_only':B,'A_full_aura':A},
  'reductions':{'A_vs_R':1-A/R,'A_vs_B':1-A/B,'B_vs_R':1-B/R},
  'projection_totals':{'R_regular':sum(r['R_projections'] for r in rows),'B_rebase_only':sum(r['B_projections'] for r in rows),'A_full_aura':sum(r['A_projections'] for r in rows)},
  'A_policy_model_calls':sum(r['A_model_calls_policy'] for r in rows),
  'A_no_model_tasks':[r['task'] for r in rows if r['A_route']==['NO_MODEL']],
  'A_routes':{r['task']:r['A_route'] for r in rows},
  'rows':rows,
  'claim_ceiling':'Equal-cost routing/hydration benchmark on the checked 16-object/6-domain reference graph. It does not measure LLM task quality, production token billing, provider latency, or causal superiority.'
}
print(json.dumps(summary,indent=2))
