#![forbid(unsafe_code)]

//! Current, typed hydration boundary for profiled Python lexical scopes.
//!
//! The bridge requires three independent facts to agree:
//! - a PR495 CURRENT full-source-body hydration receipt;
//! - the actual source-derived profiled SyntaxGraph + CPython-conformant scope inventory;
//! - a PR490 typed SourceGeneration coordinate.
//!
//! Current source + profiled lexical scopes is still not runtime name resolution.

use aura_k27_astge_current_syntax::{
    CurrentSyntaxHydrationError, CurrentSyntaxHydrationIdentityV1, admit_current_syntax_hydration,
    canonical_source_generation_ref,
};
use aura_k27_astge_generation_domain::{GenerationCoordinateV1, SourceGenerationV1};
use aura_k27_astge_profiled_scopes::{
    PYTHON_GRAMMAR_ABI_VERSION, PYTHON_GRAMMAR_NAME, PYTHON_GRAMMAR_VERSION,
    PYTHON_NAMED_PROFILE_REF, PYTHON_PARSER_BINDING_NAME, PYTHON_PARSER_BINDING_VERSION,
    ProfiledPythonScopesV1, ProfiledScopeError, build_profiled_python_scopes,
};
use aura_k27_astge_syntax_profile::{
    NodeSelectionPolicyV1, NormalizationProfileV1, ParserGrammarBindingV1, SyntaxEdgeProjectionV1,
    SyntaxGraphIdentityV1, SyntaxNodeProjectionV1,
};
use std::collections::HashMap;
use std::error::Error;
use std::fmt::{Display, Formatter};
use tree_sitter::{Node, Parser};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CurrentTypedProfiledScopesV1 {
    pub current_syntax: CurrentSyntaxHydrationIdentityV1,
    pub profiled_scopes: ProfiledPythonScopesV1,
    pub source_generation: SourceGenerationV1,
    pub source_generation_coordinate: GenerationCoordinateV1,
    pub syntax_graph: SyntaxGraphIdentityV1,
    pub current_body_bound: bool,
    pub profiled_scope_identity_bound: bool,
    pub runtime_name_resolution_proven: bool,
    pub call_graph_proven: bool,
    pub semantic_k27_derived: bool,
    pub human_authority: bool,
    pub external_effect: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CurrentProfiledScopeError {
    CurrentSyntax(CurrentSyntaxHydrationError),
    ProfiledScope(ProfiledScopeError),
    ParserLanguage(String),
    ParseReturnedNone,
    ParseHasError,
    NamedChildMissing {
        parent_kind: String,
        child_index: usize,
    },
    SyntaxOrdinalOverflow,
    ProjectionInvariant,
    FileIdMismatch {
        requested: u32,
        witnessed: u64,
    },
    SyntaxGraphIdentityMismatch,
    SourceGenerationRefMismatch,
}

impl Display for CurrentProfiledScopeError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}
impl Error for CurrentProfiledScopeError {}

impl From<CurrentSyntaxHydrationError> for CurrentProfiledScopeError {
    fn from(value: CurrentSyntaxHydrationError) -> Self {
        Self::CurrentSyntax(value)
    }
}

impl From<ProfiledScopeError> for CurrentProfiledScopeError {
    fn from(value: ProfiledScopeError) -> Self {
        Self::ProfiledScope(value)
    }
}

/// Admit current profiled lexical scopes for one exact, independently witnessed source body.
///
/// The returned source generation is typed as `SourceGenerationV1`; snapshot, placement and
/// graph-serving generations cannot inhabit that field without an explicit domain projection.
pub fn admit_current_typed_profiled_python_scopes(
    hydration_json: &str,
    anchor_id: &str,
    source: &str,
    file_id: u32,
    semantic_handles: &HashMap<u64, [u8; 32]>,
) -> Result<CurrentTypedProfiledScopesV1, CurrentProfiledScopeError> {
    let grammar = canonical_python_grammar();
    let profile = canonical_python_profile();
    let (nodes, edges) = project_named_python_syntax(source)?;

    let current_syntax = admit_current_syntax_hydration(
        hydration_json,
        anchor_id,
        &grammar,
        &profile,
        &nodes,
        &edges,
    )?;
    if current_syntax.file_id != u64::from(file_id) {
        return Err(CurrentProfiledScopeError::FileIdMismatch {
            requested: file_id,
            witnessed: current_syntax.file_id,
        });
    }

    let source_generation = SourceGenerationV1::new(current_syntax.source_generation);
    if current_syntax.source_generation_ref
        != canonical_source_generation_ref(source_generation.value())
    {
        return Err(CurrentProfiledScopeError::SourceGenerationRefMismatch);
    }

    let profiled_scopes = build_profiled_python_scopes(
        source,
        file_id,
        current_syntax.anchor_owner_ref.clone(),
        current_syntax.source_generation_ref.clone(),
        semantic_handles,
    )?;
    if profiled_scopes.syntax_graph != current_syntax.syntax_graph {
        return Err(CurrentProfiledScopeError::SyntaxGraphIdentityMismatch);
    }

    Ok(CurrentTypedProfiledScopesV1 {
        syntax_graph: current_syntax.syntax_graph.clone(),
        current_syntax,
        profiled_scopes,
        source_generation,
        source_generation_coordinate: source_generation.coordinate(),
        current_body_bound: true,
        profiled_scope_identity_bound: true,
        runtime_name_resolution_proven: false,
        call_graph_proven: false,
        semantic_k27_derived: false,
        human_authority: false,
        external_effect: false,
    })
}

/// Require a source-axis generation at compile time.
///
/// ```compile_fail
/// use aura_k27_astge_current_profiled_scopes::require_source_generation;
/// use aura_k27_astge_generation_domain::PlacementGenerationV1;
/// let placement = PlacementGenerationV1::new(41);
/// require_source_generation(placement);
/// ```
pub const fn require_source_generation(generation: SourceGenerationV1) -> SourceGenerationV1 {
    generation
}

fn canonical_python_grammar() -> ParserGrammarBindingV1 {
    ParserGrammarBindingV1 {
        parser_binding_name: PYTHON_PARSER_BINDING_NAME.to_owned(),
        parser_binding_version: PYTHON_PARSER_BINDING_VERSION.to_owned(),
        grammar_name: PYTHON_GRAMMAR_NAME.to_owned(),
        grammar_version: PYTHON_GRAMMAR_VERSION.to_owned(),
        grammar_abi_version: PYTHON_GRAMMAR_ABI_VERSION,
    }
}

fn canonical_python_profile() -> NormalizationProfileV1 {
    NormalizationProfileV1 {
        profile_ref: PYTHON_NAMED_PROFILE_REF.to_owned(),
        node_selection: NodeSelectionPolicyV1::NamedNodesOnly,
        direct_parent_child_edges_only: true,
    }
}

fn project_named_python_syntax(
    source: &str,
) -> Result<(Vec<SyntaxNodeProjectionV1>, Vec<SyntaxEdgeProjectionV1>), CurrentProfiledScopeError> {
    let mut parser = Parser::new();
    let language: tree_sitter::Language = tree_sitter_python::LANGUAGE.into();
    parser
        .set_language(&language)
        .map_err(|error| CurrentProfiledScopeError::ParserLanguage(error.to_string()))?;
    let tree = parser
        .parse(source, None)
        .ok_or(CurrentProfiledScopeError::ParseReturnedNone)?;
    let root = tree.root_node();
    if root.has_error() {
        return Err(CurrentProfiledScopeError::ParseHasError);
    }

    let mut nodes = Vec::new();
    let mut edges = Vec::new();
    project_named_preorder(root, &mut nodes, &mut edges)?;
    Ok((nodes, edges))
}

fn project_named_preorder(
    node: Node<'_>,
    nodes: &mut Vec<SyntaxNodeProjectionV1>,
    edges: &mut Vec<SyntaxEdgeProjectionV1>,
) -> Result<u64, CurrentProfiledScopeError> {
    let local_node_id =
        u64::try_from(nodes.len()).map_err(|_| CurrentProfiledScopeError::SyntaxOrdinalOverflow)?;
    nodes.push(SyntaxNodeProjectionV1 {
        local_node_id,
        grammar_kind_id: u32::from(node.kind_id()),
        grammar_kind_name: node.kind().to_owned(),
        named: node.is_named(),
        start_byte: node.start_byte() as u64,
        end_byte: node.end_byte() as u64,
    });

    for child_index in 0..node.named_child_count() {
        let child = node.named_child(child_index).ok_or_else(|| {
            CurrentProfiledScopeError::NamedChildMissing {
                parent_kind: node.kind().to_owned(),
                child_index,
            }
        })?;
        let child_local_node_id = u64::try_from(nodes.len())
            .map_err(|_| CurrentProfiledScopeError::SyntaxOrdinalOverflow)?;
        edges.push(SyntaxEdgeProjectionV1 {
            parent_local_node_id: local_node_id,
            child_local_node_id,
        });
        if project_named_preorder(child, nodes, edges)? != child_local_node_id {
            return Err(CurrentProfiledScopeError::ProjectionInvariant);
        }
    }
    Ok(local_node_id)
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge_generation_domain::{GenerationDomainV1, PlacementGenerationV1};
    use aura_k27_astge_ingest::parse_python_named_ast;
    use serde_json::{Value, json};
    use sha2::{Digest, Sha256};

    const FIXTURE: &str =
        include_str!("../../aura-k27-astge-scopes/fixtures/python_nested_scopes.py");

    fn handles(source: &str, file_id: u32) -> HashMap<u64, [u8; 32]> {
        parse_python_named_ast(source, file_id)
            .unwrap()
            .nodes
            .into_iter()
            .map(|node| {
                let mut digest = [0u8; 32];
                digest[..8].copy_from_slice(&node.node_id.to_le_bytes());
                digest[8..12].copy_from_slice(&file_id.to_le_bytes());
                (node.node_id, digest)
            })
            .collect()
    }

    fn body_sha(source: &str) -> String {
        let digest: [u8; 32] = Sha256::digest(source.as_bytes()).into();
        digest.iter().map(|byte| format!("{byte:02x}")).collect()
    }

    fn hydration(
        source: &str,
        file_id: u32,
        generation: u64,
        status: &str,
        admitted: bool,
        digest_override: Option<&str>,
    ) -> String {
        let sha = digest_override
            .map(str::to_owned)
            .unwrap_or_else(|| body_sha(source));
        let locator = if admitted {
            json!({
                "file_id": file_id,
                "relative_path": "src/profiled.py",
                "source_generation": generation,
                "byte_len": source.len(),
                "sha256": sha,
            })
        } else {
            Value::Null
        };
        json!({
            "version": "AURA_ASTGE_ANCHOR_HYDRATION_V1",
            "anchor_owner_reused": "source-owner://profiled-scopes",
            "source_body_witness_required": true,
            "unknown_or_stale_hydration_admitted": false,
            "codemap_digest8_currentness_authority": false,
            "source_authority_minted": false,
            "project007_runtime_implemented": false,
            "anchor_receipts": [{
                "anchor_id": "anchor.profiled",
                "path": "src/profiled.py",
                "semantic_id": "SEM:PROFILED",
                "signature_hash": "sig",
                "anchor_projection_resolved": true,
                "semantic_identity_minted_by_bridge": false,
                "source_authority_minted": false,
                "body_currentness_status": status,
                "hydration_admitted": admitted,
                "reason": if status == "CURRENT" { "EXACT_SOURCE_BODY_WITNESS_MATCH" } else if status == "STALE" { "SOURCE_BODY_DIGEST_DRIFT" } else { "MISSING_SOURCE_BODY_WITNESS" },
                "witness_ref": if admitted { "witness://profiled/body" } else { "" },
                "expected_byte_len": if admitted { source.len() } else { 0 },
                "observed_byte_len": if admitted { source.len() } else { 0 },
                "expected_body_sha256": if admitted { sha.clone() } else { String::new() },
                "observed_body_sha256": if admitted { sha.clone() } else { String::new() },
                "locator": locator,
            }],
            "source_locators_v1": [],
        })
        .to_string()
    }

    #[test]
    fn current_body_and_profiled_scopes_share_exact_graph_and_typed_source_generation() {
        let file_id = 121;
        let admitted = admit_current_typed_profiled_python_scopes(
            &hydration(FIXTURE, file_id, 41, "CURRENT", true, None),
            "anchor.profiled",
            FIXTURE,
            file_id,
            &handles(FIXTURE, file_id),
        )
        .unwrap();
        assert_eq!(admitted.profiled_scopes.scope_count, 15);
        assert_eq!(
            admitted.current_syntax.syntax_graph,
            admitted.profiled_scopes.syntax_graph
        );
        assert_eq!(admitted.source_generation, SourceGenerationV1::new(41));
        assert_eq!(
            admitted.source_generation_coordinate.domain,
            GenerationDomainV1::Source
        );
        assert_eq!(admitted.source_generation_coordinate.value, 41);
        assert!(admitted.current_body_bound);
        assert!(admitted.profiled_scope_identity_bound);
        assert!(!admitted.runtime_name_resolution_proven);
        assert!(!admitted.call_graph_proven);
        assert!(!admitted.semantic_k27_derived);
        assert!(!admitted.human_authority);
        assert!(!admitted.external_effect);
    }

    #[test]
    fn stale_body_cannot_admit_profiled_scope_currentness() {
        let file_id = 122;
        assert!(matches!(
            admit_current_typed_profiled_python_scopes(
                &hydration(FIXTURE, file_id, 42, "STALE", false, None),
                "anchor.profiled",
                FIXTURE,
                file_id,
                &handles(FIXTURE, file_id),
            ),
            Err(CurrentProfiledScopeError::CurrentSyntax(
                CurrentSyntaxHydrationError::BodyStale
            ))
        ));
    }

    #[test]
    fn current_receipt_for_different_body_cannot_be_pasted_onto_profiled_source() {
        let file_id = 123;
        let other = FIXTURE.replace("return", "yield ");
        let wrong_sha = body_sha(&other);
        assert_eq!(
            admit_current_typed_profiled_python_scopes(
                &hydration(FIXTURE, file_id, 43, "CURRENT", true, Some(&wrong_sha)),
                "anchor.profiled",
                FIXTURE,
                file_id,
                &handles(FIXTURE, file_id),
            )
            .unwrap_err(),
            CurrentProfiledScopeError::SyntaxGraphIdentityMismatch
        );
    }

    #[test]
    fn witnessed_file_id_must_match_profiled_source_file_id() {
        let file_id = 124;
        assert_eq!(
            admit_current_typed_profiled_python_scopes(
                &hydration(FIXTURE, file_id + 1, 44, "CURRENT", true, None),
                "anchor.profiled",
                FIXTURE,
                file_id,
                &handles(FIXTURE, file_id),
            )
            .unwrap_err(),
            CurrentProfiledScopeError::FileIdMismatch {
                requested: file_id,
                witnessed: u64::from(file_id + 1),
            }
        );
    }

    #[test]
    fn equal_numeric_source_and_placement_generations_remain_different_domains() {
        let source = SourceGenerationV1::new(55);
        let placement = PlacementGenerationV1::new(55);
        assert_eq!(source.value(), placement.value());
        assert_ne!(source.coordinate(), placement.coordinate());
        assert_eq!(require_source_generation(source), source);
    }
}
