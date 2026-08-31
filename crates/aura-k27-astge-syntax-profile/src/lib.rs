#![forbid(unsafe_code)]

use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::error::Error;
use std::fmt::{Display, Formatter};

const SCHEMA: &str = "AuraK27AstgeSyntaxGraphV1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NodeSelectionPolicyV1 {
    NamedNodesOnly,
    AllChildren,
}

impl NodeSelectionPolicyV1 {
    fn tag(self) -> &'static str {
        match self {
            Self::NamedNodesOnly => "NAMED_NODES_ONLY",
            Self::AllChildren => "ALL_CHILDREN",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParserGrammarBindingV1 {
    pub parser_binding_name: String,
    pub parser_binding_version: String,
    pub grammar_name: String,
    pub grammar_version: String,
    pub grammar_abi_version: u32,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NormalizationProfileV1 {
    pub profile_ref: String,
    pub node_selection: NodeSelectionPolicyV1,
    pub direct_parent_child_edges_only: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceBindingV1 {
    pub source_owner_ref: String,
    pub source_generation_ref: String,
    pub file_id: u64,
    pub source_sha256: [u8; 32],
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SyntaxNodeProjectionV1 {
    /// Parser/storage-local handle only. It is excluded from the canonical graph digest.
    pub local_node_id: u64,
    /// Grammar-local numeric kind. It is meaningful only together with ParserGrammarBindingV1.
    pub grammar_kind_id: u32,
    pub grammar_kind_name: String,
    pub named: bool,
    pub start_byte: u64,
    pub end_byte: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct SyntaxEdgeProjectionV1 {
    pub parent_local_node_id: u64,
    pub child_local_node_id: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SyntaxGraphIdentityV1 {
    pub graph_sha256: [u8; 32],
    pub node_count: usize,
    pub edge_count: usize,
    pub grammar_name: String,
    pub grammar_version: String,
    pub normalization_profile_ref: String,
    pub file_id: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SyntaxGraphAdmissionError {
    EmptyField(&'static str),
    InvalidGrammarAbi,
    EmptySourceDigest,
    EmptyProjection,
    InvalidSpan {
        local_node_id: u64,
        start: u64,
        end: u64,
    },
    AnonymousNodeForbidden {
        local_node_id: u64,
    },
    EmptyKindName {
        local_node_id: u64,
    },
    DuplicateLocalNodeId(u64),
    UnknownEdgeEndpoint(u64),
    SelfEdge(u64),
    DuplicateEdge {
        parent: u64,
        child: u64,
    },
    NonDirectEdgePolicy,
}

impl Display for SyntaxGraphAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for SyntaxGraphAdmissionError {}

pub fn admit_syntax_graph(
    grammar: &ParserGrammarBindingV1,
    profile: &NormalizationProfileV1,
    source: &SourceBindingV1,
    ordered_nodes: &[SyntaxNodeProjectionV1],
    ordered_edges: &[SyntaxEdgeProjectionV1],
) -> Result<SyntaxGraphIdentityV1, SyntaxGraphAdmissionError> {
    require_nonempty(&grammar.parser_binding_name, "parser_binding_name")?;
    require_nonempty(&grammar.parser_binding_version, "parser_binding_version")?;
    require_nonempty(&grammar.grammar_name, "grammar_name")?;
    require_nonempty(&grammar.grammar_version, "grammar_version")?;
    require_nonempty(&profile.profile_ref, "normalization_profile_ref")?;
    require_nonempty(&source.source_owner_ref, "source_owner_ref")?;
    require_nonempty(&source.source_generation_ref, "source_generation_ref")?;
    if grammar.grammar_abi_version == 0 {
        return Err(SyntaxGraphAdmissionError::InvalidGrammarAbi);
    }
    if source.source_sha256 == [0; 32] {
        return Err(SyntaxGraphAdmissionError::EmptySourceDigest);
    }
    if ordered_nodes.is_empty() {
        return Err(SyntaxGraphAdmissionError::EmptyProjection);
    }
    if !profile.direct_parent_child_edges_only {
        return Err(SyntaxGraphAdmissionError::NonDirectEdgePolicy);
    }

    let mut local_to_ordinal = HashMap::with_capacity(ordered_nodes.len());
    for (ordinal, node) in ordered_nodes.iter().enumerate() {
        if node.end_byte < node.start_byte {
            return Err(SyntaxGraphAdmissionError::InvalidSpan {
                local_node_id: node.local_node_id,
                start: node.start_byte,
                end: node.end_byte,
            });
        }
        if node.grammar_kind_name.trim().is_empty() {
            return Err(SyntaxGraphAdmissionError::EmptyKindName {
                local_node_id: node.local_node_id,
            });
        }
        if profile.node_selection == NodeSelectionPolicyV1::NamedNodesOnly && !node.named {
            return Err(SyntaxGraphAdmissionError::AnonymousNodeForbidden {
                local_node_id: node.local_node_id,
            });
        }
        if local_to_ordinal
            .insert(node.local_node_id, ordinal)
            .is_some()
        {
            return Err(SyntaxGraphAdmissionError::DuplicateLocalNodeId(
                node.local_node_id,
            ));
        }
    }

    let mut canonical_edges = Vec::with_capacity(ordered_edges.len());
    let mut seen_edges = HashSet::with_capacity(ordered_edges.len());
    for edge in ordered_edges {
        let Some(&parent) = local_to_ordinal.get(&edge.parent_local_node_id) else {
            return Err(SyntaxGraphAdmissionError::UnknownEdgeEndpoint(
                edge.parent_local_node_id,
            ));
        };
        let Some(&child) = local_to_ordinal.get(&edge.child_local_node_id) else {
            return Err(SyntaxGraphAdmissionError::UnknownEdgeEndpoint(
                edge.child_local_node_id,
            ));
        };
        if parent == child {
            return Err(SyntaxGraphAdmissionError::SelfEdge(
                edge.parent_local_node_id,
            ));
        }
        if !seen_edges.insert((parent, child)) {
            return Err(SyntaxGraphAdmissionError::DuplicateEdge {
                parent: edge.parent_local_node_id,
                child: edge.child_local_node_id,
            });
        }
        canonical_edges.push((parent as u64, child as u64));
    }

    let mut hasher = Sha256::new();
    put_str(&mut hasher, SCHEMA);
    put_str(&mut hasher, &grammar.parser_binding_name);
    put_str(&mut hasher, &grammar.parser_binding_version);
    put_str(&mut hasher, &grammar.grammar_name);
    put_str(&mut hasher, &grammar.grammar_version);
    hasher.update(grammar.grammar_abi_version.to_le_bytes());
    put_str(&mut hasher, &profile.profile_ref);
    put_str(&mut hasher, profile.node_selection.tag());
    hasher.update([u8::from(profile.direct_parent_child_edges_only)]);
    put_str(&mut hasher, &source.source_owner_ref);
    put_str(&mut hasher, &source.source_generation_ref);
    hasher.update(source.file_id.to_le_bytes());
    hasher.update(source.source_sha256);
    hasher.update((ordered_nodes.len() as u64).to_le_bytes());

    for (ordinal, node) in ordered_nodes.iter().enumerate() {
        hasher.update((ordinal as u64).to_le_bytes());
        hasher.update(node.grammar_kind_id.to_le_bytes());
        put_str(&mut hasher, &node.grammar_kind_name);
        hasher.update([u8::from(node.named)]);
        hasher.update(node.start_byte.to_le_bytes());
        hasher.update(node.end_byte.to_le_bytes());
    }

    hasher.update((canonical_edges.len() as u64).to_le_bytes());
    for (parent, child) in canonical_edges {
        hasher.update(parent.to_le_bytes());
        hasher.update(child.to_le_bytes());
    }

    let graph_sha256: [u8; 32] = hasher.finalize().into();
    Ok(SyntaxGraphIdentityV1 {
        graph_sha256,
        node_count: ordered_nodes.len(),
        edge_count: ordered_edges.len(),
        grammar_name: grammar.grammar_name.clone(),
        grammar_version: grammar.grammar_version.clone(),
        normalization_profile_ref: profile.profile_ref.clone(),
        file_id: source.file_id,
    })
}

fn require_nonempty(value: &str, field: &'static str) -> Result<(), SyntaxGraphAdmissionError> {
    if value.trim().is_empty() {
        return Err(SyntaxGraphAdmissionError::EmptyField(field));
    }
    Ok(())
}

fn put_str(hasher: &mut Sha256, value: &str) {
    hasher.update((value.len() as u64).to_le_bytes());
    hasher.update(value.as_bytes());
}

#[cfg(test)]
mod tests {
    use super::*;

    fn grammar(name: &str, version: &str, binding_version: &str) -> ParserGrammarBindingV1 {
        ParserGrammarBindingV1 {
            parser_binding_name: "tree-sitter-rust-binding".into(),
            parser_binding_version: binding_version.into(),
            grammar_name: name.into(),
            grammar_version: version.into(),
            grammar_abi_version: 15,
        }
    }

    fn profile(reference: &str, selection: NodeSelectionPolicyV1) -> NormalizationProfileV1 {
        NormalizationProfileV1 {
            profile_ref: reference.into(),
            node_selection: selection,
            direct_parent_child_edges_only: true,
        }
    }

    fn source() -> SourceBindingV1 {
        SourceBindingV1 {
            source_owner_ref: "source://fixture/main".into(),
            source_generation_ref: "git:0123456789abcdef".into(),
            file_id: 7,
            source_sha256: [0x44; 32],
        }
    }

    fn named_nodes(ids: [u64; 3]) -> Vec<SyntaxNodeProjectionV1> {
        vec![
            SyntaxNodeProjectionV1 {
                local_node_id: ids[0],
                grammar_kind_id: 1,
                grammar_kind_name: "module".into(),
                named: true,
                start_byte: 0,
                end_byte: 12,
            },
            SyntaxNodeProjectionV1 {
                local_node_id: ids[1],
                grammar_kind_id: 9,
                grammar_kind_name: "function_definition".into(),
                named: true,
                start_byte: 0,
                end_byte: 12,
            },
            SyntaxNodeProjectionV1 {
                local_node_id: ids[2],
                grammar_kind_id: 17,
                grammar_kind_name: "identifier".into(),
                named: true,
                start_byte: 4,
                end_byte: 5,
            },
        ]
    }

    fn edges(ids: [u64; 3]) -> Vec<SyntaxEdgeProjectionV1> {
        vec![
            SyntaxEdgeProjectionV1 {
                parent_local_node_id: ids[0],
                child_local_node_id: ids[1],
            },
            SyntaxEdgeProjectionV1 {
                parent_local_node_id: ids[1],
                child_local_node_id: ids[2],
            },
        ]
    }

    #[test]
    fn storage_local_node_ids_do_not_define_syntax_graph_identity() {
        let g = grammar("python", "0.25.0", "0.25.10");
        let p = profile(
            "python/NAMED_ONLY/v1",
            NodeSelectionPolicyV1::NamedNodesOnly,
        );
        let a = admit_syntax_graph(
            &g,
            &p,
            &source(),
            &named_nodes([1, 2, 3]),
            &edges([1, 2, 3]),
        )
        .unwrap();
        let b = admit_syntax_graph(
            &g,
            &p,
            &source(),
            &named_nodes([100, 900, 42]),
            &edges([100, 900, 42]),
        )
        .unwrap();
        assert_eq!(a.graph_sha256, b.graph_sha256);
    }

    #[test]
    fn normalization_profile_is_part_of_identity() {
        let g = grammar("python", "0.25.0", "0.25.10");
        let named = profile(
            "python/NAMED_ONLY/v1",
            NodeSelectionPolicyV1::NamedNodesOnly,
        );
        let all = profile("python/ALL_CHILDREN/v1", NodeSelectionPolicyV1::AllChildren);
        let nodes = named_nodes([1, 2, 3]);
        let e = edges([1, 2, 3]);
        let a = admit_syntax_graph(&g, &named, &source(), &nodes, &e).unwrap();
        let b = admit_syntax_graph(&g, &all, &source(), &nodes, &e).unwrap();
        assert_ne!(a.graph_sha256, b.graph_sha256);
    }

    #[test]
    fn grammar_and_binding_versions_are_part_of_identity() {
        let p = profile(
            "language/NAMED_ONLY/v1",
            NodeSelectionPolicyV1::NamedNodesOnly,
        );
        let nodes = named_nodes([1, 2, 3]);
        let e = edges([1, 2, 3]);
        let python = admit_syntax_graph(
            &grammar("python", "0.25.0", "0.25.10"),
            &p,
            &source(),
            &nodes,
            &e,
        )
        .unwrap();
        let rust = admit_syntax_graph(
            &grammar("rust", "0.24.2", "0.26.13"),
            &p,
            &source(),
            &nodes,
            &e,
        )
        .unwrap();
        assert_ne!(python.graph_sha256, rust.graph_sha256);
    }

    #[test]
    fn named_only_profile_rejects_anonymous_nodes() {
        let g = grammar("python", "0.25.0", "0.25.10");
        let p = profile(
            "python/NAMED_ONLY/v1",
            NodeSelectionPolicyV1::NamedNodesOnly,
        );
        let mut nodes = named_nodes([1, 2, 3]);
        nodes[2].named = false;
        assert_eq!(
            admit_syntax_graph(&g, &p, &source(), &nodes, &edges([1, 2, 3])),
            Err(SyntaxGraphAdmissionError::AnonymousNodeForbidden { local_node_id: 3 })
        );
    }

    #[test]
    fn all_children_profile_can_represent_anonymous_nodes_but_stays_distinct() {
        let g = grammar("rust", "0.24.2", "0.26.13");
        let p = profile("rust/ALL_CHILDREN/v1", NodeSelectionPolicyV1::AllChildren);
        let mut nodes = named_nodes([1, 2, 3]);
        nodes[2].named = false;
        nodes[2].grammar_kind_name = "(".into();
        assert!(admit_syntax_graph(&g, &p, &source(), &nodes, &edges([1, 2, 3])).is_ok());
    }

    #[test]
    fn source_generation_is_part_of_identity() {
        let g = grammar("python", "0.25.0", "0.25.10");
        let p = profile(
            "python/NAMED_ONLY/v1",
            NodeSelectionPolicyV1::NamedNodesOnly,
        );
        let nodes = named_nodes([1, 2, 3]);
        let e = edges([1, 2, 3]);
        let a = admit_syntax_graph(&g, &p, &source(), &nodes, &e).unwrap();
        let mut newer = source();
        newer.source_generation_ref = "git:fedcba9876543210".into();
        let b = admit_syntax_graph(&g, &p, &newer, &nodes, &e).unwrap();
        assert_ne!(a.graph_sha256, b.graph_sha256);
    }

    #[test]
    fn malformed_projection_fails_closed() {
        let g = grammar("python", "0.25.0", "0.25.10");
        let p = profile(
            "python/NAMED_ONLY/v1",
            NodeSelectionPolicyV1::NamedNodesOnly,
        );
        let nodes = named_nodes([1, 2, 3]);
        let bad_edge = [SyntaxEdgeProjectionV1 {
            parent_local_node_id: 1,
            child_local_node_id: 99,
        }];
        assert_eq!(
            admit_syntax_graph(&g, &p, &source(), &nodes, &bad_edge),
            Err(SyntaxGraphAdmissionError::UnknownEdgeEndpoint(99))
        );
    }
}
