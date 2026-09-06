"""Recover the prior 1000-route research queue; add scoped implementation work.

There are 100 change families and 10 evaluation routes per family, not 1000
independent inventions. IDs and original questions are preserved verbatim.
"""
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
import csv, json, tempfile, time
from research_factory import generate
from persistent_memory import MemoryStore, canonical
from world_atlas import FrameAddress

OUT = Path(__file__).resolve().parents[1]
SOURCE = 'https://docs.google.com/document/d/1cSfomuQTT1yvbQtbHojpz8kccDbGT3g7D6mqWIqqPQM/edit'
CONCERNS = ('COHERENCE','RETRIEVAL','CURRENTNESS','AUTHORITY','PRIVACY','PERFORMANCE','ACCESSIBILITY','RECOVERY','INTEROPERABILITY','COGNITION_USABILITY')
FAMILIES = {
 'K27_RECURSION': (
  'Bind each recursive path to an explicit frame generation and stable object ID',
  'Add indexed ancestor and descendant lookup with exact scope boundaries',
  'Invalidate stored addresses when their frame generation changes',
  'Keep navigation coordinates separate from effect grants in address records',
  'Partition coordinate search by an explicit visibility context',
  'Measure prefix-index lookup against full scans at matched record counts',
  'Expose keyboard and text equivalents for each hierarchical navigation action',
  'Persist revision bindings and reopen the same city after process restart',
  'Version recursive-trit and digest-bucket schemes and reject implicit conversion',
  'Distinguish stable record identity from labels, coordinates, and content revisions'),
 'MULTIPLEX_OVERLAY': (
  'Resolve overlay conflicts with explicit precedence and declared scope',
  'Filter overlay retrieval by layer and preserve the underlying canonical record',
  'Track source revisions for each overlay and invalidate only dependent views',
  'Require separate grant resolution for jurisdiction overlays before any effect',
  'Prevent private overlay fields from leaking into public projections',
  'Cache overlays by source generation and layer selection',
  'Provide non-color labels for overlapping overlay states',
  'Restore overlay configuration separately from immutable source history',
  'Export typed overlays without flattening their provenance and precedence',
  'Explain why a layer is visible and which source produced its value'),
 'SPATIAL_WFST': (
  'Reject conflicting transition definitions in the spatial navigation graph',
  'Return route evidence with the exact graph generation and endpoints',
  'Invalidate route caches when relevant graph edges change',
  'Resolve route reachability independently of action permission',
  'Hide restricted nodes while preserving explicit incomplete-coverage status',
  'Compare indexed route search with exhaustive shortest paths on bounded graphs',
  'Offer text route instructions and non-spatial navigation controls',
  'Rebuild route indexes deterministically from a persisted graph snapshot',
  'Translate between route graph IDs and frame-qualified endpoints losslessly',
  'Explain route cost and alternative paths without implying a best real-world action'),
 'PHYSICAL_JURISDICTION': (
  'Represent overlapping jurisdiction boundaries as typed independent claims',
  'Return bounded jurisdiction matches with source coverage and uncertainty',
  'Recheck jurisdiction evidence at the intended time of use',
  'Bind scoped grants to the existing jurisdiction owner instead of city labels',
  'Separate sensitive location observations from public jurisdiction geometry',
  'Index relevant jurisdiction boundaries with an exhaustive correctness oracle',
  'Show textual boundary and uncertainty descriptions for nonvisual users',
  'Retain historical boundary versions without authorizing their current reuse',
  'Carry coordinate reference system and epoch through boundary imports',
  'Explain observed location, interpreted boundary, and granted action separately'),
 'XR_ANCHOR': (
  'Bind XR anchors to explicit tracking sessions and frame generations',
  'Resolve anchor aliases through exact stable IDs without nearest-match substitution',
  'Expire anchor projections when tracking or calibration generations change',
  'Keep anchor proximity separate from interaction permission',
  'Remove device identifiers and private spatial meshes from shared anchor records',
  'Measure anchor reconciliation cost under controlled tracking churn',
  'Provide accessible anchor selection independent of precise head or hand motion',
  'Reacquire anchors after tracking loss without silently reusing stale poses',
  'Translate anchor frames with explicit units, axis order, and handedness',
  'Show anchor uncertainty and distinguish remembered pose from live tracking'),
 'LOD_CULLING': (
  'Preserve record identity and coverage when scene detail levels change',
  'Distinguish culled visual nodes from absent underlying memory records',
  'Invalidate visibility decisions when camera or scene generations change',
  'Prevent visual culling from suppressing required permission indicators',
  'Apply visibility policy before geometry reaches a rendering cache',
  'Measure frame time and memory against an uncullled matched scene baseline',
  'Retain accessible text navigation for visually culled nodes',
  'Recover visibility state after device loss from authoritative scene inputs',
  'Export level-of-detail metadata without changing canonical geometry identity',
  'Explain hidden detail levels and expose a predictable reveal action'),
 'VISUAL_SKIN': (
  'Keep visual assets separate from the semantic city skeleton',
  'Resolve assets by exact skin revision with deterministic fallbacks',
  'Invalidate skin plans after asset or skeleton generation changes',
  'Ensure color and decoration cannot introduce authority claims',
  'Remove hidden personal data from distributed skin asset metadata',
  'Measure asset transfer and texture residency under a declared byte budget',
  'Validate contrast and semantic labels across skin changes',
  'Recover missing assets with a legible neutral rendering',
  'Preserve skeleton bindings through skin import and export',
  'Make the distinction between a record and its decorative appearance visible'),
 'BREADBOARD': (
  'Keep experimental zones versioned and separate from published scene bindings',
  'Index experiments by exact parent sources and declared evaluation scope',
  'Mark experimental results stale when their source snapshots change',
  'Require explicit promotion bindings before experimental output affects live owners',
  'Use redacted fixtures when cloning shared experiments from private memory',
  'Bound experiment storage and execution costs with measured receipts',
  'Provide text creation and inspection controls for experiment zones',
  'Restore experiments and their source pins after an interrupted session',
  'Export reproducible experiment manifests with versioned coordinate adapters',
  'Display hypothesis, observation, and accepted result as separate states'),
 'XR_INTERACTION': (
  'Deduplicate interaction events with exact event and scene-generation IDs',
  'Resolve selected records by stable identity after scene reordering',
  'Revalidate selected record and frame generations when an action is used',
  'Bind intended effects to explicit grants independently of the gesture',
  'Minimize stored gaze, motion, and interaction telemetry',
  'Measure input-to-feedback latency under a matched event replay',
  'Provide switch, keyboard, and voice-compatible interaction alternatives',
  'Recover pending interaction state without replaying completed effects',
  'Map device-specific gestures into a versioned semantic action vocabulary',
  'Make selection, preview, confirmation, and completion distinguishable'),
 'TENANCY_MULTIUSER': (
  'Resolve concurrent city edits using exact revision compare-and-swap',
  'Scope exact and approximate retrieval to the requesting tenant context',
  'Invalidate shared projections when membership or source revisions change',
  'Consult the existing tenant grant owner before cross-user effects',
  'Prevent cross-tenant keys and payloads from entering shared cache entries',
  'Measure contention and fairness at declared concurrent-reader counts',
  'Preserve accessibility preferences independently for each user',
  'Replay committed shared edits without reviving withdrawn membership',
  'Export tenant-scoped references without copying private owner records',
  'Explain edit conflicts and show whose revision is currently visible'),
}
METHODS = {
 'BLIND_ABLATION': ('paired baseline report','Compare the proposed component enabled and disabled on identical inputs, with results scored before revealing the condition.'),
 'MUTATION': ('invariant regression suite','Mutate one relevant source, generation, or context field at a time; assert the declared invariant or an explicit refusal.'),
 'FUZZ': ('seeded property campaign','Generate bounded valid and invalid inputs, preserve failing seeds, and compare results to a simple exhaustive reference.'),
 'USER_STUDY': ('human evaluation protocol','Predefine tasks and success criteria; obtain appropriate participant consent and record completion/error rates. Human evidence remains required.'),
 'HEADSET_BENCH': ('headset measurement protocol','Pin scene, device, runtime, workload and baseline; measure on a real headset. No physical execution is inferred from simulation.'),
 'MOBILE_BENCH': ('mobile measurement protocol','Pin scene, device, runtime, workload and baseline; measure on a real mobile device. Report correctness separately from latency.'),
 'CROSS_DEVICE_REPLAY': ('portable replay fixture','Replay the same versioned inputs on two declared runtimes/devices and compare semantic outputs within declared numeric tolerances.'),
 'FAILURE_INJECTION': ('interruption recovery fixture','Interrupt the operation at persistence and publication boundaries; require either the complete old state or the complete new state.'),
 'OWNER_CHALLENGE': ('owner integration review','Compare the change to the current owning implementation, document overlap, and require evidence for every claimed residual improvement.'),
 'INTEGRATION_TEST': ('executable integration scenario','Exercise the proposed behavior through the actual public module APIs and assert observable results, including an independent unaffected record.'),
}
MODULES = {'K27_RECURSION':'k27_city.py / world_atlas.py / persistent_memory.py',
 'MULTIPLEX_OVERLAY':'K27City.effective_rules / urban multiplex owner',
 'SPATIAL_WFST':'spatial route owner; canonical path unresolved',
 'PHYSICAL_JURISDICTION':'xr_jurisdiction.py / jurisdiction owner',
 'XR_ANCHOR':'xr_scene.py / spatial_adapter.py', 'LOD_CULLING':'xr_scene.py / renderer',
 'VISUAL_SKIN':'visual_skin.py', 'BREADBOARD':'spatial_adapter.py / BreadboardZone',
 'XR_INTERACTION':'xr_jurisdiction.py / interaction owner', 'TENANCY_MULTIUSER':'tenant owner / persistent_memory.py local revision seam'}
SOURCES = {'COHERENCE':['K27-EXT-001','K27-EXT-004'], 'RETRIEVAL':['K27-EXT-006','K27-EXT-007'],
 'CURRENTNESS':['K27-EXT-003','K27-EXT-005'], 'AUTHORITY':['K27-EXT-001'], 'PRIVACY':['K27-EXT-005'],
 'PERFORMANCE':['K27-EXT-010'], 'ACCESSIBILITY':[], 'RECOVERY':['K27-EXT-002','K27-EXT-008'],
 'INTEROPERABILITY':['K27-EXT-001'], 'COGNITION_USABILITY':['K27-EXT-009']}

def build():
    families, routes = {}, []
    for t in generate():
        family_id = t.primitive + '/' + t.concern
        change = FAMILIES[t.primitive][CONCERNS.index(t.concern)]
        evidence_keys = list(SOURCES[t.concern])
        # These papers do not establish XR performance, accessibility, grants,
        # or tenant privacy. Keep unsupported family-level citations empty.
        if t.concern in ('AUTHORITY','PRIVACY','PERFORMANCE','ACCESSIBILITY'):
            evidence_keys = []
        family = {'family_id':family_id,'primitive':t.primitive,'concern':t.concern,'proposed_change':change,
            'module_target':MODULES[t.primitive],'status':'candidate; full family not verified',
            'source_url':SOURCE,'external_source_keys':evidence_keys,
            'evidence_scope':'External sources motivate design only; they do not prove this Aura-specific feature.'}
        families[family_id] = family
        artifact, acceptance = METHODS[t.operator]
        score = (30 if t.primitive=='K27_RECURSION' else 15 if t.primitive=='MULTIPLEX_OVERLAY' else 5)
        score += {'CURRENTNESS':20,'COHERENCE':15,'INTEROPERABILITY':15,'RECOVERY':15,'RETRIEVAL':10}.get(t.concern,0)
        score += {'INTEGRATION_TEST':20,'MUTATION':10,'FAILURE_INJECTION':15,'OWNER_CHALLENGE':5}.get(t.operator,-5)
        routes.append({**asdict(t),**family,'operator':t.operator,'original_question':t.question,
            'deliverable':f'{change}: {artifact}', 'acceptance':acceptance,
            'priority_score':score,'provenance':'recovered O7 route, enriched with a proposed change; not a new discovery',
            'original_coordinate_scheme':'MCXR-RESEARCH-MATRIX-2STEP-v1',
            'coordinate_is_authority':False,'claim':'research route; not demonstrated advancement'})
    routes.sort(key=lambda r:(-r['priority_score'],r['id']))
    (OUT/'research_routes_1000.json').write_text(json.dumps(routes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'change_families_100.json').write_text(json.dumps(list(families.values()),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (OUT/'research_routes_1000.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['id','family_id','operator','proposed_change','module_target','deliverable','acceptance','status','priority_score','source_url']
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(routes)
    hot=[]; selected=set()
    for r in routes:
        if r['family_id'] not in selected:
            hot.append(r);selected.add(r['family_id'])
        if len(hot)==27:break
    (OUT/'hot27.json').write_text(json.dumps(hot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return routes,families,hot

if __name__=='__main__':
    routes,families,hot=build()
    print(json.dumps({'research_routes':len(routes),'unique_ids':len({r['id'] for r in routes}),
        'change_families':len(families),'hot_families':len(hot),'verified_advancements':0,
        'note':'1000 routes are recovered candidate evaluation work, not 1000 independent advances.'},indent=2))
