from tools.arena.triadic_confluence_runtime import *
import json, sys


def c(k,v,con): return Clause(k,v,con,authority=1)
def art(i, clauses): return Artifact(i,tuple(clauses),authority_ceiling=5)

# Structural benchmark only: number of durable generations and serialized semantic bytes.
def run(n=10000, material_every=997):
    base_clause=c("stop_rule","fixed_point","avoid endless refinement")
    current=[base_clause]
    prior=semantic_normal_form_hash(current)
    naive_generations=0
    naive_bytes=0
    confluence_generations=1
    confluence_bytes=len(canonical_json([canonicalize(x.__dict__) for x in current]))
    collapsed=0
    material=0
    holds=0
    digest_xor=0

    for i in range(1,n+1):
        left=art(f"A{i}",current)
        if i % material_every == 0:
            material += 1
            new=c(f"earned_{i}","enabled",f"new consequence {i}")
            right=art(f"B{i}",[base_clause,new])
            delta=[MaterialDelta("SEMANTIC",f"new consequence {i}",True)]
            candidate_nf=tuple(current)+ (new,)
        else:
            right=art(f"B{i}",[base_clause])
            delta=[]
            candidate_nf=tuple(current)

        naive_generations += 1
        naive_bytes += len(canonical_json([canonicalize(x.__dict__) for x in candidate_nf]))

        r=confluence_rebase(left,right,material_deltas=delta,prior_normal_form_hash=prior)
        if r.action == RebaseAction.HOLD:
            holds += 1
        if r.durable_generation:
            confluence_generations += 1
            current=list(r.clauses)
            prior=r.normal_form_hash
            confluence_bytes += len(canonical_json([canonicalize(x.__dict__) for x in current]))
        else:
            collapsed += 1
        digest_xor ^= int(result_digest(r)[:16],16)

    return {
      "cases":n,
      "material_cases":material,
      "surface_only_cases":n-material,
      "naive_durable_generations":naive_generations+1,
      "confluence_durable_generations":confluence_generations,
      "collapsed_noop_attempts":collapsed,
      "holds":holds,
      "naive_serialized_semantic_bytes":naive_bytes,
      "confluence_serialized_semantic_bytes":confluence_bytes,
      "generation_ratio":confluence_generations/(naive_generations+1),
      "serialized_byte_ratio":confluence_bytes/naive_bytes if naive_bytes else 0,
      "digest_xor":f"{digest_xor:016x}",
      "claim_ceiling":"STRUCTURAL_D0_ONLY; no token/latency/quality claim"
    }

if __name__ == '__main__':
    n=int(sys.argv[1]) if len(sys.argv)>1 else 10000
    print(json.dumps(run(n),sort_keys=True,indent=2))
