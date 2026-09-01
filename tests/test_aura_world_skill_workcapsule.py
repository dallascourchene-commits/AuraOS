from __future__ import annotations

from dataclasses import replace
import sys
import types
import unittest

from tools.aura_external_knowledge_ingress import (
    ExternalObservation,
    ExternalSubject,
    HydrationPayload,
    KnowledgeState,
    build_external_knowledge_node,
)
from tools.aura_world_skill_workcapsule import (
    ObjectiveRouteProfile,
    SKILL_SCHEMA,
    SkillRouteCard,
    compile_world_skill_workcapsule,
    verify_world_skill_workcapsule,
)


def _node(*, state: KnowledgeState = KnowledgeState.CURRENT_REFERENCE, levels: int = 1, revision: str = "v1"):
    subject = ExternalSubject(
        provider="ARXIV",
        source_kind="PAPER",
        canonical_id="2608.27454",
        canonical_uri="https://arxiv.org/abs/2608.27454",
        sector="08_RSH",
    )
    observation = ExternalObservation(
        provider_revision=revision,
        content_digest=("a" if revision == "v1" else "b") * 64,
        observed_at="2026-09-01T12:00:00Z",
        source_generated_at="2026-08-27T17:59:11Z",
        exact_source_uri="https://arxiv.org/abs/2608.27454v1",
        verifier_generation="test-verifier-v1",
        verified_fields=("content_digest", "exact_source_uri", "provider_revision"),
    )
    hydration = tuple(
        HydrationPayload(
            level=f"L{i}",
            data={"level": i, "subject": "wikiskill"},
            derivation_method="TEST_FIXTURE",
        )
        for i in range(levels)
    )
    return build_external_knowledge_node(
        subject=subject,
        observation=observation,
        knowledge_state=state,
        hydration=hydration,
        validator_generation="test-validator-v1",
    )


def _objective(*caps: str, model: str = "GPT-5.6-SOL") -> ObjectiveRouteProfile:
    return ObjectiveRouteProfile(
        objective_id="OBJ-WORLD-SKILL-1",
        objective="Integrate WikiSkill with Aura World routing and WorkCapsules",
        world_id="AURA-WORLD",
        required_capabilities=tuple(sorted(caps)),
        model_family=model,
        available_tools=("github", "web"),
        skill_registry_generation="skills-gen-7",
        tool_registry_generation="tools-gen-3",
        authority_scope="D0_NONPROMOTING",
    )


def _skill(
    skill_id: str,
    caps: tuple[str, ...],
    *,
    min_level: str = "L1",
    tools: tuple[str, ...] = (),
    models: tuple[str, ...] = ("*",),
    status: str = "EVOLVED_ACCEPTED",
    currentness: str = "CURRENT",
    cost: float = 1.0,
) -> SkillRouteCard:
    return SkillRouteCard(
        schema=SKILL_SCHEMA,
        skill_id=skill_id,
        skill_generation="g1",
        name=skill_id,
        kind="procedure",
        path=f"skills/{skill_id}/SKILL.md",
        description=f"Procedure for {skill_id}",
        capabilities=tuple(sorted(caps)),
        purpose_pattern_ids=(f"pattern:{skill_id}",),
        required_tools=tuple(sorted(tools)),
        source_kinds=("PAPER",),
        min_hydration_level=min_level,
        compatible_model_families=tuple(sorted(models)),
        registry_status=status,
        currentness=currentness,
        validation_generation="val-g4",
        provenance_refs=(f"wiki/patterns/{skill_id}.md",),
        estimated_cost=cost,
    )


class WorldSkillWorkCapsuleTests(unittest.TestCase):
    def test_minimal_skill_bundle_drives_demand_hydration(self) -> None:
        skills = (
            _skill("research-only", ("research",), min_level="L2", tools=("web",)),
            _skill("code-only", ("code",), min_level="L1", tools=("github",)),
            _skill(
                "world-integrator",
                ("code", "research"),
                min_level="L3",
                tools=("github", "web"),
                cost=2.0,
            ),
        )
        receipt = compile_world_skill_workcapsule(
            objective=_objective("code", "research"),
            external_nodes=(_node(levels=1),),
            skill_cards=skills,
        )
        self.assertEqual(receipt["selected_skill_count"], 1)
        self.assertEqual(receipt["selected_skills"][0]["skill_id"], "world-integrator")
        self.assertEqual(receipt["world_routes"][0]["required_hydration_level"], "L3")
        self.assertEqual(receipt["world_routes"][0]["hydration_disposition"], "HYDRATE_L0_TO_L3")
        self.assertTrue(receipt["planning_complete"])
        self.assertEqual(verify_world_skill_workcapsule(receipt), [])

    def test_model_specific_negative_transfer_fails_closed(self) -> None:
        skill = _skill(
            "model-specific-workaround",
            ("research",),
            models=("QWEN-4B",),
        )
        receipt = compile_world_skill_workcapsule(
            objective=_objective("research", model="GPT-5.6-SOL"),
            external_nodes=(_node(),),
            skill_cards=(skill,),
        )
        self.assertEqual(receipt["selected_skill_count"], 0)
        self.assertFalse(receipt["planning_complete"])
        self.assertEqual(receipt["negative_space"][0]["disposition"], "NO_ELIGIBLE_SKILL_IN_SUPPLIED_REGISTRY_GENERATION")
        self.assertFalse(receipt["negative_space"][0]["global_absence_claimed"])

    def test_stale_skill_is_not_selected(self) -> None:
        receipt = compile_world_skill_workcapsule(
            objective=_objective("research"),
            external_nodes=(_node(),),
            skill_cards=(_skill("stale", ("research",), currentness="STALE"),),
        )
        self.assertEqual(receipt["selected_skills"], [])
        self.assertFalse(receipt["planning_complete"])

    def test_noncurrent_world_node_requires_reverification_not_deeper_hydration(self) -> None:
        receipt = compile_world_skill_workcapsule(
            objective=_objective("research"),
            external_nodes=(_node(state=KnowledgeState.METADATA_VERIFIED),),
            skill_cards=(_skill("research", ("research",), min_level="L4"),),
        )
        route = receipt["world_routes"][0]
        self.assertEqual(route["hydration_disposition"], "REVERIFY_CURRENTNESS_BEFORE_ACTIVE_HYDRATION")
        self.assertFalse(receipt["world_current_for_read_only_reference"])
        self.assertIn("CURRENT_REFERENCE_NOT_ESTABLISHED", [x["disposition"] for x in receipt["negative_space"]])

    def test_cache_key_moves_with_source_generation(self) -> None:
        skill = _skill("research", ("research",))
        a = compile_world_skill_workcapsule(
            objective=_objective("research"), external_nodes=(_node(revision="v1"),), skill_cards=(skill,)
        )
        b = compile_world_skill_workcapsule(
            objective=_objective("research"), external_nodes=(_node(revision="v2"),), skill_cards=(skill,)
        )
        self.assertNotEqual(a["route_cache_key"], b["route_cache_key"])

    def test_cache_key_moves_with_skill_generation(self) -> None:
        skill = _skill("research", ("research",))
        a = compile_world_skill_workcapsule(
            objective=_objective("research"), external_nodes=(_node(),), skill_cards=(skill,)
        )
        b = compile_world_skill_workcapsule(
            objective=_objective("research"),
            external_nodes=(_node(),),
            skill_cards=(replace(skill, skill_generation="g2"),),
        )
        self.assertNotEqual(a["route_cache_key"], b["route_cache_key"])

    def test_claim_ceiling_rejects_authority_widening(self) -> None:
        receipt = compile_world_skill_workcapsule(
            objective=_objective("research"),
            external_nodes=(_node(),),
            skill_cards=(_skill("research", ("research",)),),
        )
        receipt["authority"]["code_execution_authorized"] = True
        self.assertIn("PLANNER_MINTED_AUTHORITY", verify_world_skill_workcapsule(receipt))

    def test_coordinate_and_cache_never_become_truth(self) -> None:
        receipt = compile_world_skill_workcapsule(
            objective=_objective("research"),
            external_nodes=(_node(),),
            skill_cards=(_skill("research", ("research",)),),
        )
        self.assertFalse(receipt["world_routes"][0]["coordinate_is_authority"])
        self.assertFalse(receipt["laws"]["cache_hit_is_currentness_witness"])
        self.assertFalse(receipt["laws"]["coordinate_memory_is_model_prefix_kv"])


class SkillCockpitTargetingRegressionTests(unittest.TestCase):
    def test_adapter_returns_target_modules_not_first_ten_registry_entries(self) -> None:
        fake = types.ModuleType("aura_skillweaver")

        class Skill:
            def __init__(self, name: str, path: str):
                self.name = name
                self.kind = "module"
                self.path = path
                self.description = name + " description"

        class Weaver:
            def __init__(self, repo_root: str = "."):
                self.skills = [Skill("wrong", "wrong.py"), Skill("right", "right.py")]

        fake.AuraSkillWeaver = Weaver
        fake.find_target_modules = lambda objective, skills: ["right.py"]
        old = sys.modules.get("aura_skillweaver")
        sys.modules["aura_skillweaver"] = fake
        try:
            import aura_skill_cockpit_adapter

            out = aura_skill_cockpit_adapter.discover_skills_for_objective("right objective")
            self.assertEqual([row["path"] for row in out["skills"]], ["right.py"])
            self.assertEqual(out["target_modules"], ["right.py"])
            self.assertFalse(out["global_absence_claimed"])
        finally:
            if old is None:
                sys.modules.pop("aura_skillweaver", None)
            else:
                sys.modules["aura_skillweaver"] = old


if __name__ == "__main__":
    unittest.main()
