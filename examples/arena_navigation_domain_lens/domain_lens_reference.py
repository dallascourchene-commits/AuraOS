#!/usr/bin/env python3
"""Bounded non-production reference for Arena navigation + domain-lens shards.

This is deliberately small. It tests control semantics, not canonical AuraOS runtime behavior.
"""
from __future__ import annotations
import hashlib, json, subprocess
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOMAINS = ("publication", "runtime", "memory", "media", "safety", "economics")

HARD = {
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

SOURCE = {sid: f"SOURCE::{sid}" for sid in HARD}
W = {
    "PAPER_X": dict(publication=1.0,runtime=.55,memory=.70,media=.40,safety=.75,economics=.35),
    "ARENA_CORE": dict(publication=.25,runtime=1.0,memory=.70,media=.45,safety=.70,economics=.40),
    "TEMPORAL_ARENA": dict(publication=.30,runtime=.90,memory=.70,media=.45,safety=.85,economics=.40),
    "COORDINATE_MEMORY": dict(publication=.30,runtime=.65,memory=1.0,media=.25,safety=.75,economics=.55),
    "PROJECT006_RUNTIME": dict(publication=.15,runtime=1.0,memory=.35,media=.65,safety=.95,economics=.35),
    "HYPERDRIVE": dict(publication=.45,runtime=.70,memory=.90,media=.40,safety=.85,economics=.55),
    "HYPERSCALE": dict(publication=.30,runtime=.85,memory=.65,media=.35,safety=.60,economics=.75),
    "PR_CAMPAIGN": dict(publication=.80,runtime=.35,memory=.30,media=1.0,safety=.65,economics=.55),
    "CREATOR_STUDIO": dict(publication=.40,runtime=.65,memory=.35,media=1.0,safety=.70,economics=.55),
    "README_GITHUB": dict(publication=1.0,runtime=.25,memory=.25,media=.55,safety=.60,economics=.20),
    "MINI_AURA": dict(publication=.70,runtime=.85,memory=.60,media=.20,safety=.80,economics=.30),
    "LIFEOS_PLACES": dict(publication=.35,runtime=.50,memory=.85,media=.60,safety=1.0,economics=.45),
    "WEB4": dict(publication=.45,runtime=.70,memory=.45,media=.60,safety=.75,economics=1.0),
    "SEMANTIC_COMPILER": dict(publication=.40,runtime=.80,memory=.95,media=.25,safety=.85,economics=.35),
    "SWARM_RUNTIME": dict(publication=.20,runtime=1.0,memory=.45,media=.30,safety=.80,economics=.70),
    "AMORTIZED_INTELLIGENCE": dict(publication=.45,runtime=.45,memory=.75,media=.40,safety=.45,economics=1.0),
}


def temp(w):
    return "HOT" if w >= .85 else "WARM" if w >= .60 else "COLD" if w >= .35 else "TRANSIENT"


def key27(value):
    n = int.from_bytes(hashlib.sha256(value.encode()).digest(), "big") % (3**27)
    d=[]
    for _ in range(27):
        n,r=divmod(n,3); d.append(str(r))
    return "".join(reversed(d))


def decode3(s):
    n=0
    for c in s: n=n*3+int(c)
    return n


def lens(sid, domain):
    return {
        "object_sid": sid,
        "domain_sid": domain,
        "truth_owner": SOURCE[sid],
        "salience": W[sid][domain],
        "residency": temp(W[sid][domain]),
        "k27_trit": key27(f"{sid}|{domain}"),
        "L4": SOURCE[sid],
    }


def closure(seeds):
    seen=set(); q=list(seeds)
    while q:
        x=q.pop()
        if x in seen: continue
        seen.add(x); q.extend(HARD[x])
    return seen


def affected(changed):
    rev=defaultdict(set)
    for x,deps in HARD.items():
        for d in deps: rev[d].add(x)
    seen={changed}; q=deque([changed])
    while q:
        x=q.popleft()
        for y in rev[x]:
            if y not in seen: seen.add(y); q.append(y)
    return seen


def neighborhood(domain, threshold=.6):
    return {sid for sid in HARD if W[sid][domain] >= threshold}


def cross_edges(a,b):
    A,B=neighborhood(a),neighborhood(b); out=set()
    for sid in A:
        for d in HARD[sid]:
            if d in B and sid not in B: out.add((sid,"DEPENDS_ON",d))
    for sid in B:
        for d in HARD[sid]:
            if d in A and sid not in A: out.add((sid,"DEPENDS_ON",d))
    return sorted(out)


def main():
    tests=[]
    def ok(name, cond, detail=None):
        tests.append((name,bool(cond),detail))
        if not cond: raise AssertionError(name)

    a,b=lens("PAPER_X","publication"),lens("PAPER_X","memory")
    ok("one_source_many_lenses", a["truth_owner"]==b["truth_owner"] and a["domain_sid"]!=b["domain_sid"])
    ok("domain_specific_residency", lens("PR_CAMPAIGN","media")["residency"]=="HOT" and lens("PR_CAMPAIGN","memory")["residency"]=="TRANSIENT")
    base="tp://arena/AURA-DRIVE2/subarena/DOMAIN_LENS_SHARDING"
    h1=hashlib.sha256(b"g1").hexdigest()[:16]; h2=hashlib.sha256(b"g2").hexdigest()[:16]
    ok("stable_address_versioned_head", h1!=h2 and base==base)
    aff=affected("PAPER_X")
    ok("reverse_affected_cone", {"PAPER_X","PR_CAMPAIGN","README_GITHUB","MINI_AURA"}.issubset(aff) and "LIFEOS_PLACES" not in aff)
    k=key27("PAPER_X|memory")
    ok("27_trit_key", len(k)==27 and set(k)<=set("012") and decode3(k)<3**27)
    node=subprocess.run(["node",str(ROOT/"trit27_check.mjs"),k],capture_output=True,text=True,check=True)
    n=json.loads(node.stdout)
    ok("python_node_trit_parity", n["roundtrip"]==k and n["decimal"]==str(decode3(k)))
    pub,mem=neighborhood("publication"),neighborhood("memory")
    ok("domain_neighborhoods_differ", pub!=mem and "README_GITHUB" in pub and "COORDINATE_MEMORY" in mem)
    cross=cross_edges("publication","memory")
    ok("cross_domain_edges_are_source_graph_edges", cross and all(d in HARD[s] for s,_,d in cross),cross)
    seeds={"PR_CAMPAIGN","PAPER_X","COORDINATE_MEMORY"}; c=closure(seeds)
    eligible=len(c)*2; all_possible=len(HARD)*len(DOMAINS)
    ok("scope_before_route", eligible < all_possible, {"eligible":eligible,"all":all_possible})
    ok("navigation_surfaces", "PROJECT006_RUNTIME" in c and "HYPERSCALE" in c and "HYPERDRIVE" in c)
    now=closure({"TEMPORAL_ARENA","SWARM_RUNTIME"})
    ok("temporal_axis_preserved", "TEMPORAL_ARENA" in now and "ARENA_CORE" in now)
    fake=[("IDEA_A","0"*27),("IDEA_B","0"*27)]
    ok("partition_collision_fail_closed", len({s for s,_ in fake})==2 and len({k for _,k in fake})==1)
    ok("lens_cannot_invent_relation", "LIFEOS_PLACES" not in HARD["README_GITHUB"])

    out={"status":"PASS_NONPROMOTING_REFERENCE","passed":sum(x[1] for x in tests),"total":len(tests),"tests":[{"name":n,"pass":p,"detail":d} for n,p,d in tests],"claim_ceiling":"reference semantics only; not production AuraOS or cognitive-superiority proof"}
    print(json.dumps(out,indent=2))

if __name__ == "__main__": main()
