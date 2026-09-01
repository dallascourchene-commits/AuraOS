"""
Aura Skill Cockpit Adapter — SkillWeaver + Affordance Directory fusion.

Dependencies: stdlib only. All Aura imports are lazy.
"""
from __future__ import annotations
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
ADAPTER_VERSION = "AURA_SKILL_COCKPIT_ADAPTER_V1"


def discover_skills_for_objective(objective: str, repo_root: str = ".") -> dict:
    """Discover the bounded SkillWeaver modules actually routed for an objective.

    Historical V1 code computed ``target_modules`` and then ignored it, returning
    the first ten registry entries instead.  This adapter remains advisory, but
    it now preserves the router consequence rather than silently substituting
    registry order for objective relevance.
    """
    skills = []
    target_modules = []
    try:
        from aura_skillweaver import AuraSkillWeaver, find_target_modules
        weaver = AuraSkillWeaver(repo_root=repo_root)
        all_skills = weaver.skills
        target_modules = find_target_modules(objective, all_skills)

        by_path = {}
        for skill in all_skills:
            if skill.kind == "module" and skill.path and skill.path not in by_path:
                by_path[skill.path] = skill

        for path in target_modules:
            skill = by_path.get(path)
            if skill is None:
                continue
            skills.append({
                "name": skill.name,
                "kind": skill.kind,
                "path": skill.path,
                "description": skill.description,
                "status": "existing",
                "selection_basis": "SkillWeaver.find_target_modules",
            })
    except Exception:
        skills = []
        target_modules = []

    for s in skills:
        if isinstance(s, dict):
            s.setdefault("status", "existing")
    return {
        "ok": True,
        "objective": objective,
        "skills": skills,
        "target_modules": target_modules,
        "negative_space": "NO_ROUTED_MODULE_IN_CURRENT_REGISTRY" if not skills else None,
        "global_absence_claimed": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def weave_skills_for_intent(intent_packet: dict, repo_root: str = ".") -> dict:
    """Weave skills for an intent packet."""
    objective = intent_packet.get("objective", "")
    discovery = discover_skills_for_objective(objective, repo_root)
    return {"ok": True, "woven_skills": discovery.get("skills", []),
             "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def skillweaver_to_affordance_cards(skills: list, repo_root: str = ".") -> dict:
    """Convert skills to affordance card format."""
    cards = []
    for s in skills:
        if isinstance(s, dict):
            status = s.get("status", "existing")
            cards.append({
                "id": s.get("id", s.get("name", "unknown")),
                "name": s.get("name", ""),
                "description": s.get("description", ""),
                "status": status,
                "patch_authority": False,
                "vsa_patch_authority": False,
            })
            if status == "hypothetical":
                cards[-1]["route_to"] = "emergent_capability_audit"
    return {"ok": True, "cards": cards, "patch_authority": PATCH_AUTHORITY,
             "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def skillweaver_to_qdkt_feedback(skills: list, repo_root: str = ".") -> dict:
    """Log skill discovery to QDKT."""
    try:
        from aura_qdkt import get_qdkt
        qdkt = get_qdkt()
        skill_names = [s.get("name", "") if isinstance(s, dict) else str(s) for s in skills[:5]]
        qdkt.observe(
            "skill_discovery",
            {"skills": skill_names, "count": len(skills)},
            rationale=f"Discovered {len(skills)} skills",
            concept="skillweaver",
            confidence=0.7,
            subsystem="cockpit",
        )
        return {"ok": True, "logged": True, "patch_authority": PATCH_AUTHORITY,
                 "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    except Exception:
        return {"ok": True, "logged": False, "note": "QDKT unavailable",
                 "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
