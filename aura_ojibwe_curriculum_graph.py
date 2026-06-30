"""
Aura Ojibwe Curriculum Graph
================================
Schema version: AURA_CURRICULUM_GRAPH_V1

Defines the Treaty #1 / Plains Ojibwe language learning curriculum as a
directed graph. Each node is a learning unit with prerequisite nodes,
difficulty level, and seed vocabulary. The graph is compatible with the
existing Aura SceneGraph/SceneNode topology for visual rendering.

Learning path (default):
  GREETINGS → KINSHIP → HOME_COMMUNITY → LAND_WATER
                ↓
            ANIMACY → VERBS_PERSON_MARKERS → TENSE_ASPECT

Nodes emit SceneNode-compatible dicts for Cytoscape/Three.js rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

AURA_CURRICULUM_GRAPH_V1 = "AURA_CURRICULUM_GRAPH_V1"


class CurriculumNodeId(str, Enum):
    GREETINGS = "GREETINGS"
    KINSHIP = "KINSHIP"
    HOME_COMMUNITY = "HOME_COMMUNITY"
    LAND_WATER = "LAND_WATER"
    ANIMACY = "ANIMACY"
    VERBS_PERSON_MARKERS = "VERBS_PERSON_MARKERS"
    TENSE_ASPECT = "TENSE_ASPECT"


class DifficultyLevel(int, Enum):
    BEGINNER = 1
    ELEMENTARY = 2
    INTERMEDIATE = 3
    ADVANCED = 4


@dataclass
class CurriculumNode:
    """A single learning unit in the curriculum graph."""
    schema_version: str
    node_id: CurriculumNodeId
    title: str
    description: str
    difficulty: DifficultyLevel
    prerequisites: List[CurriculumNodeId]
    seed_words: List[str]              # Words from lexicon sidecar
    learning_goals: List[str]
    dialect_notes: Optional[str] = None

    def to_scene_node(self, mastered: bool = False) -> dict:
        """
        Export as a SceneNode-compatible dict for topology rendering.
        Luminance = mastery state. Shape = difficulty level.
        """
        shapes = {
            DifficultyLevel.BEGINNER: "sphere",
            DifficultyLevel.ELEMENTARY: "cube",
            DifficultyLevel.INTERMEDIATE: "pyramid",
            DifficultyLevel.ADVANCED: "octahedron",
        }
        return {
            "schema_version": AURA_CURRICULUM_GRAPH_V1,
            "node_id": self.node_id.value,
            "title": self.title,
            "difficulty": self.difficulty.value,
            "shape": shapes[self.difficulty],
            "luminance": 1.0 if mastered else 0.3,
            "color": "#ffd700" if mastered else "#4a9eff",
            "seed_words": self.seed_words,
            "learning_goals": self.learning_goals,
            "prerequisites": [p.value for p in self.prerequisites],
            "dialect_notes": self.dialect_notes,
        }


@dataclass
class CurriculumEdge:
    """A prerequisite edge between two curriculum nodes."""
    from_node: CurriculumNodeId
    to_node: CurriculumNodeId
    edge_type: str = "prerequisite"

    def to_scene_edge(self) -> dict:
        return {
            "from": self.from_node.value,
            "to": self.to_node.value,
            "type": self.edge_type,
        }


class CurriculumGraph:
    """
    The Treaty #1 / Plains Ojibwe language learning curriculum graph.

    Integrates with aura_ojibwe_lexicon_sidecar.py for seed vocabulary
    and aura_topology_snapshot_builder.py for visual rendering.
    """

    def __init__(self) -> None:
        self._nodes: Dict[CurriculumNodeId, CurriculumNode] = {}
        self._edges: List[CurriculumEdge] = []
        self._build_default_curriculum()

    def _build_default_curriculum(self) -> None:
        nodes = [
            CurriculumNode(
                schema_version=AURA_CURRICULUM_GRAPH_V1,
                node_id=CurriculumNodeId.GREETINGS,
                title="Greetings & Basic Expressions",
                description=(
                    "First words in Treaty #1 Anishinaabemowin: "
                    "how to say hello, thank you, and respond to greetings."
                ),
                difficulty=DifficultyLevel.BEGINNER,
                prerequisites=[],
                seed_words=["boozhoo", "aaniin", "miigwech", "gaawin"],
                learning_goals=[
                    "Say 'boozhoo' (hello) and 'aaniin' (greetings / how are you)",
                    "Say 'miigwech' (thank you)",
                    "Respond 'gaawin' (no / not yet) appropriately",
                    "Understand that greetings carry relational meaning",
                ],
                dialect_notes=(
                    "These greetings are widely shared across Anishinaabe communities. "
                    "'Boozhoo' is pan-Anishinaabe. 'Aaniin' is common in Plains Ojibwe."
                ),
            ),
            CurriculumNode(
                schema_version=AURA_CURRICULUM_GRAPH_V1,
                node_id=CurriculumNodeId.KINSHIP,
                title="Kinship Terms",
                description=(
                    "Anishinaabe family relationships and how they shape the language. "
                    "Kinship terms are always possessed — you say 'my grandfather', "
                    "not just 'grandfather'."
                ),
                difficulty=DifficultyLevel.BEGINNER,
                prerequisites=[CurriculumNodeId.GREETINGS],
                seed_words=["nimishoomis", "nookomis", "nimaamaaa", "nindede"],
                learning_goals=[
                    "Say 'nimishoomis' (my grandfather) and 'nookomis' (my grandmother)",
                    "Say 'nimaamaaa' (my mother) and 'nindede' (my father)",
                    "Understand the ni-/gi-/o- possession prefix system",
                    "Understand why kinship terms are animate nouns (NAD class)",
                ],
                dialect_notes=(
                    "Dependent animate nouns (NAD) must always carry a possessive prefix. "
                    "The stem alone ('mishoomis') is not a complete word."
                ),
            ),
            CurriculumNode(
                schema_version=AURA_CURRICULUM_GRAPH_V1,
                node_id=CurriculumNodeId.HOME_COMMUNITY,
                title="Home & Community",
                description=(
                    "Words for the places and things of everyday community life."
                ),
                difficulty=DifficultyLevel.ELEMENTARY,
                prerequisites=[CurriculumNodeId.GREETINGS, CurriculumNodeId.KINSHIP],
                seed_words=["aki", "ziibi", "zaaga'igan", "ishkode"],
                learning_goals=[
                    "Name key elements of the community and home",
                    "Distinguish animate (NA) from inanimate (NI) nouns",
                    "Understand basic singular/plural noun forms",
                ],
                dialect_notes=None,
            ),
            CurriculumNode(
                schema_version=AURA_CURRICULUM_GRAPH_V1,
                node_id=CurriculumNodeId.LAND_WATER,
                title="Land, Water & Territory",
                description=(
                    "The language of Treaty #1 territory — names for the land, "
                    "rivers, lakes, and our relationship to them. "
                    "'Aki' (land/earth) is central to Anishinaabe worldview."
                ),
                difficulty=DifficultyLevel.ELEMENTARY,
                prerequisites=[CurriculumNodeId.HOME_COMMUNITY],
                seed_words=["aki", "ziibi", "zaaga'igan"],
                learning_goals=[
                    "Understand 'aki' as more than just 'land' — it is a relational term",
                    "Name the rivers and lakes of Treaty #1 territory",
                    "Connect language learning to land-based knowledge",
                ],
                dialect_notes=(
                    "Place names in Treaty #1 territory are often derived from Ojibwe. "
                    "Winnipeg comes from 'win-nipi' (muddy waters). "
                    "These names carry history and territory."
                ),
            ),
            CurriculumNode(
                schema_version=AURA_CURRICULUM_GRAPH_V1,
                node_id=CurriculumNodeId.ANIMACY,
                title="Animacy — The Life of Words",
                description=(
                    "In Anishinaabemowin, every noun is either animate or inanimate. "
                    "This is not about biological life — it is about relational status. "
                    "Rocks, fire, and dreams can be animate."
                ),
                difficulty=DifficultyLevel.INTERMEDIATE,
                prerequisites=[CurriculumNodeId.HOME_COMMUNITY, CurriculumNodeId.KINSHIP],
                seed_words=["aki", "ishkode", "nimishoomis"],
                learning_goals=[
                    "Understand animate (NA) vs inanimate (NI) noun classes",
                    "Know that animacy in Ojibwe is cultural, not biological",
                    "Use correct verb agreement for animate vs inanimate subjects",
                    "Understand VAI vs VII verb choice based on animacy",
                ],
                dialect_notes=(
                    "Animacy categories can vary slightly between dialects. "
                    "When in doubt, ask a Treaty #1 fluent speaker."
                ),
            ),
            CurriculumNode(
                schema_version=AURA_CURRICULUM_GRAPH_V1,
                node_id=CurriculumNodeId.VERBS_PERSON_MARKERS,
                title="Verbs & Person Markers",
                description=(
                    "Ojibwe verbs carry person, number, animacy, and transitivity "
                    "all within the verb form itself. "
                    "The VAI verb 'nibaa' (s/he sleeps) demonstrates the system."
                ),
                difficulty=DifficultyLevel.INTERMEDIATE,
                prerequisites=[CurriculumNodeId.ANIMACY],
                seed_words=["nibaa", "miijiw"],
                learning_goals=[
                    "Conjugate a VAI verb (animate intransitive) in present tense",
                    "Identify ni- (1SG), gi- (2SG), o- (3SG) person prefixes",
                    "Distinguish VAI, VTA, VTI, VII verb classes",
                    "Form a simple sentence: subject + VAI verb",
                ],
                dialect_notes=None,
            ),
            CurriculumNode(
                schema_version=AURA_CURRICULUM_GRAPH_V1,
                node_id=CurriculumNodeId.TENSE_ASPECT,
                title="Tense, Aspect & Mode",
                description=(
                    "Ojibwe encodes tense, aspect, and mode within the verb — "
                    "independent (Ind), conjunct (Conj), and imperative (Imp) orders, "
                    "with preterit and dubitative modes."
                ),
                difficulty=DifficultyLevel.ADVANCED,
                prerequisites=[CurriculumNodeId.VERBS_PERSON_MARKERS],
                seed_words=["nibaa", "miijiw"],
                learning_goals=[
                    "Understand independent vs conjunct order",
                    "Form a basic past (preterit) statement",
                    "Use 'gaawin' + conjunct order for negation",
                    "Understand how OjibweMorph FST tags encode these distinctions",
                ],
                dialect_notes=(
                    "Tense/aspect morphology is a rich area where Plains Ojibwe "
                    "may differ from Central Southwestern. Consult Treaty #1 "
                    "verified sources for confirmation."
                ),
            ),
        ]
        for node in nodes:
            self._nodes[node.node_id] = node

        edges = [
            CurriculumEdge(CurriculumNodeId.GREETINGS, CurriculumNodeId.KINSHIP),
            CurriculumEdge(CurriculumNodeId.KINSHIP, CurriculumNodeId.HOME_COMMUNITY),
            CurriculumEdge(CurriculumNodeId.HOME_COMMUNITY, CurriculumNodeId.LAND_WATER),
            CurriculumEdge(CurriculumNodeId.HOME_COMMUNITY, CurriculumNodeId.ANIMACY),
            CurriculumEdge(CurriculumNodeId.KINSHIP, CurriculumNodeId.ANIMACY),
            CurriculumEdge(CurriculumNodeId.ANIMACY, CurriculumNodeId.VERBS_PERSON_MARKERS),
            CurriculumEdge(CurriculumNodeId.VERBS_PERSON_MARKERS, CurriculumNodeId.TENSE_ASPECT),
        ]
        self._edges.extend(edges)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_node(self, node_id: CurriculumNodeId) -> Optional[CurriculumNode]:
        return self._nodes.get(node_id)

    def get_next_nodes(self, node_id: CurriculumNodeId) -> List[CurriculumNode]:
        """Return nodes that depend on node_id as a prerequisite."""
        return [
            self._nodes[e.to_node]
            for e in self._edges
            if e.from_node == node_id and e.to_node in self._nodes
        ]

    def get_available_nodes(
        self, mastered: List[CurriculumNodeId]
    ) -> List[CurriculumNode]:
        """Return nodes whose prerequisites are all mastered."""
        mastered_set = set(mastered)
        return [
            node for node in self._nodes.values()
            if node.node_id not in mastered_set
            and all(p in mastered_set for p in node.prerequisites)
        ]

    def all_nodes(self) -> List[CurriculumNode]:
        return list(self._nodes.values())

    # ------------------------------------------------------------------
    # Scene graph export
    # ------------------------------------------------------------------

    def to_scene_graph(self, mastered: Optional[List[str]] = None) -> dict:
        """
        Export the full curriculum as a scene graph dict compatible with
        aura_scene_graph_exporter.py.
        """
        mastered_ids = set(mastered or [])
        nodes = [
            node.to_scene_node(mastered=node.node_id.value in mastered_ids)
            for node in self._nodes.values()
        ]
        edges = [e.to_scene_edge() for e in self._edges]
        return {
            "schema_version": AURA_CURRICULUM_GRAPH_V1,
            "dialect": "Treaty1_Plains_Ojibwe",
            "nodes": nodes,
            "edges": edges,
        }
