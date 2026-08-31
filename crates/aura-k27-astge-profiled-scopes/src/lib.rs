#![forbid(unsafe_code)]

//! Bind the conservative Python nested-scope inventory to an exact grammar/profile/source
//! SyntaxGraph identity without promoting storage-local AST or scope IDs into semantic identity.

use aura_k27_astge_ingest::{IngestError, ParsedAstGraphV1, parse_python_named_ast};
use aura_k27_astge_scopes::{
    PythonLexicalScopeIndexV1, PythonScopeV1, ScopeBindingV1, ScopeIndexError,
    index_python_nested_scopes,
};
use aura_k27_astge_syntax_profile::{
    NodeSelectionPolicyV1, NormalizationProfileV1, ParserGrammarBindingV1,
    SourceBindingV1 as SyntaxSourceBindingV1, SyntaxEdgeProjectionV1, SyntaxGraphAdmissionError,
    SyntaxGraphIdentityV1, SyntaxNodeProjectionV1, admit_syntax_graph,
};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::error::Error;
use std::fmt::{Display, Formatter};
use tree_sitter::{Node, Parser};

pub const PYTHON_PARSER_BINDING_NAME: &str = "tree-sitter";
pub const PYTHON_PARSER_BINDING_VERSION: &str = "0.25.10";
pub const PYTHON_GRAMMAR_NAME: &str = "python";
pub const PYTHON_GRAMMAR_VERSION: &str = "0.25.0";
pub const PYTHON_GRAMMAR_ABI_VERSION: u32 = 15;
pub const PYTHON_NAMED_PROFILE_REF: &str = "python/NAMED_ONLY/v1";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProfiledScopeAnchorV1 {
    /// Inventory-local only. Not semantic identity.
    pub scope_id: u64,
    /// Inventory-local only. Not semantic identity.
    pub parent_scope_id: Option<u64>,
    /// Canonical node ordinal inside the admitted SyntaxGraph projection.
    pub syntax_ordinal: Option<u64>,
    /// Parser/storage-local witness only. Excluded from SyntaxGraph identity.
    pub ast_local_node_id: Option<u64>,
    pub kind: String,
    pub name: String,
    pub file_id: u32,
    pub byte_start: u32,
    pub byte_end: u32,
    pub semantic_handle_digest: Option<[u8; 32]>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProfiledScopeBindingV1 {
    /// Inventory-local owner only. Not semantic identity.
    pub owner_scope_id: u64,
    pub ordinal_in_scope: u32,
    /// Inventory-local child scope only. Not semantic identity.
    pub target_scope_id: u64,
    /// Canonical node ordinal inside the admitted SyntaxGraph projection.
    pub syntax_ordinal: u64,
    /// Parser/storage-local witness only. Excluded from SyntaxGraph identity.
    pub ast_local_node_id: u64,
    pub kind: String,
    pub name: String,
    pub file_id: u32,
    pub byte_start: u32,
    pub byte_end: u32,
    pub semantic_handle_digest: [u8; 32],
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProfiledPythonScopesV1 {
    pub syntax_graph: SyntaxGraphIdentityV1,
    pub source_owner_ref: String,
    pub source_generation_ref: String,
    pub scope_count: usize,
    pub binding_count: usize,
    pub profiled_scopes: Vec<ProfiledScopeAnchorV1>,
    pub profiled_bindings: Vec<ProfiledScopeBindingV1>,
    pub duplicate_name_scope_count: usize,
    pub local_ast_node_id_is_semantic_identity: bool,
    pub local_scope_id_is_semantic_identity: bool,
    pub runtime_name_resolution_proven: bool,
    pub call_graph_proven: bool,
    pub semantic_k27_derived: bool,
    pub external_effect_authorized: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProfiledScopeError {
    Ingest(IngestError),
    Scope(ScopeIndexError),
    Syntax(SyntaxGraphAdmissionError),
    ParserLanguage(String),
    ParseReturnedNone,
    ParseHasError,
    NamedChildMissing {
        parent_kind: String,
        child_index: usize,
    },
    ProjectionCountMismatch {
        ingest_nodes: usize,
        projected_nodes: usize,
    },
    ProjectionMismatch {
        local_node_id: u64,
    },
    ScopeAstNodeMissing(u64),
    ScopeFileMismatch {
        ast_node_id: u64,
        expected: u32,
        actual: u32,
    },
    ScopeSpanMismatch(u64),
    ScopeHandleMissing(u64),
    ScopeHandleMismatch(u64),
    SyntaxOrdinalOverflow,
}

impl Display for ProfiledScopeError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for ProfiledScopeError {}

impl From<IngestError> for ProfiledScopeError {
    fn from(value: IngestError) -> Self {
        Self::Ingest(value)
    }
}

impl From<ScopeIndexError> for ProfiledScopeError {
    fn from(value: ScopeIndexError) -> Self {
        Self::Scope(value)
    }
}

impl From<SyntaxGraphAdmissionError> for ProfiledScopeError {
    fn from(value: SyntaxGraphAdmissionError) -> Self {
        Self::Syntax(value)
    }
}

/// Build a CPython-conformant nested scope inventory whose anchors are explicitly bound to
/// one exact parser/grammar/normalization/source SyntaxGraph identity.
///
/// The source owner and generation references are supplied by a higher owner and become part
/// of SyntaxGraph identity. Local AST and scope IDs remain witnesses only.
pub fn build_profiled_python_scopes(
    source: &str,
    file_id: u32,
    source_owner_ref: impl Into<String>,
    source_generation_ref: impl Into<String>,
    semantic_handles: &HashMap<u64, [u8; 32]>,
) -> Result<ProfiledPythonScopesV1, ProfiledScopeError> {
    let source_owner_ref = source_owner_ref.into();
    let source_generation_ref = source_generation_ref.into();
    let ingested = parse_python_named_ast(source, file_id)?;
    let (nodes, edges) = project_named_python_syntax(source)?;
    require_projection_matches_ingest(&ingested, &nodes)?;

    let grammar = canonical_python_grammar();
    let profile = canonical_python_profile();
    let source_binding = syntax_source_binding(
        source,
        file_id,
        source_owner_ref.clone(),
        source_generation_ref.clone(),
    );
    let syntax_graph = admit_syntax_graph(&grammar, &profile, &source_binding, &nodes, &edges)?;
    let scope_index = index_python_nested_scopes(source, file_id, semantic_handles)?;
    let (profiled_scopes, profiled_bindings) =
        bind_scope_anchors(&scope_index, &ingested, semantic_handles)?;

    Ok(ProfiledPythonScopesV1 {
        syntax_graph,
        source_owner_ref,
        source_generation_ref,
        scope_count: scope_index.scopes.len(),
        binding_count: scope_index.bindings.len(),
        profiled_scopes,
        profiled_bindings,
        duplicate_name_scope_count: scope_index.duplicate_names_by_scope.len(),
        local_ast_node_id_is_semantic_identity: false,
        local_scope_id_is_semantic_identity: false,
        runtime_name_resolution_proven: false,
        call_graph_proven: false,
        semantic_k27_derived: false,
        external_effect_authorized: false,
    })
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

fn syntax_source_binding(
    source: &str,
    file_id: u32,
    source_owner_ref: String,
    source_generation_ref: String,
) -> SyntaxSourceBindingV1 {
    SyntaxSourceBindingV1 {
        source_owner_ref,
        source_generation_ref,
        file_id: u64::from(file_id),
        source_sha256: Sha256::digest(source.as_bytes()).into(),
    }
}

fn project_named_python_syntax(
    source: &str,
) -> Result<(Vec<SyntaxNodeProjectionV1>, Vec<SyntaxEdgeProjectionV1>), ProfiledScopeError> {
    let mut parser = Parser::new();
    let language: tree_sitter::Language = tree_sitter_python::LANGUAGE.into();
    parser
        .set_language(&language)
        .map_err(|error| ProfiledScopeError::ParserLanguage(error.to_string()))?;
    let tree = parser
        .parse(source, None)
        .ok_or(ProfiledScopeError::ParseReturnedNone)?;
    let root = tree.root_node();
    if root.has_error() {
        return Err(ProfiledScopeError::ParseHasError);
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
) -> Result<u64, ProfiledScopeError> {
    let local_node_id =
        u64::try_from(nodes.len()).map_err(|_| ProfiledScopeError::SyntaxOrdinalOverflow)?;
    nodes.push(SyntaxNodeProjectionV1 {
        local_node_id,
        grammar_kind_id: u32::from(node.kind_id()),
        grammar_kind_name: node.kind().to_owned(),
        named: node.is_named(),
        start_byte: node.start_byte() as u64,
        end_byte: node.end_byte() as u64,
    });

    for child_index in 0..node.named_child_count() {
        let child =
            node.named_child(child_index)
                .ok_or_else(|| ProfiledScopeError::NamedChildMissing {
                    parent_kind: node.kind().to_owned(),
                    child_index,
                })?;
        let child_local_node_id =
            u64::try_from(nodes.len()).map_err(|_| ProfiledScopeError::SyntaxOrdinalOverflow)?;
        edges.push(SyntaxEdgeProjectionV1 {
            parent_local_node_id: local_node_id,
            child_local_node_id,
        });
        let observed = project_named_preorder(child, nodes, edges)?;
        if observed != child_local_node_id {
            return Err(ProfiledScopeError::ProjectionMismatch {
                local_node_id: child_local_node_id,
            });
        }
    }
    Ok(local_node_id)
}

fn require_projection_matches_ingest(
    ingested: &ParsedAstGraphV1,
    projected: &[SyntaxNodeProjectionV1],
) -> Result<(), ProfiledScopeError> {
    if ingested.nodes.len() != projected.len() {
        return Err(ProfiledScopeError::ProjectionCountMismatch {
            ingest_nodes: ingested.nodes.len(),
            projected_nodes: projected.len(),
        });
    }
    for (ingest, profile) in ingested.nodes.iter().zip(projected) {
        if ingest.node_id != profile.local_node_id
            || ingest.kind != profile.grammar_kind_name
            || u64::from(ingest.byte_start) != profile.start_byte
            || u64::from(ingest.byte_end) != profile.end_byte
            || !profile.named
        {
            return Err(ProfiledScopeError::ProjectionMismatch {
                local_node_id: ingest.node_id,
            });
        }
    }
    Ok(())
}

fn bind_scope_anchors(
    scope_index: &PythonLexicalScopeIndexV1,
    ingested: &ParsedAstGraphV1,
    semantic_handles: &HashMap<u64, [u8; 32]>,
) -> Result<(Vec<ProfiledScopeAnchorV1>, Vec<ProfiledScopeBindingV1>), ProfiledScopeError> {
    let ordinal_by_node: HashMap<u64, u64> = ingested
        .nodes
        .iter()
        .enumerate()
        .map(|(ordinal, node)| {
            u64::try_from(ordinal)
                .map(|ordinal| (node.node_id, ordinal))
                .map_err(|_| ProfiledScopeError::SyntaxOrdinalOverflow)
        })
        .collect::<Result<_, _>>()?;
    let node_by_id: HashMap<u64, _> = ingested
        .nodes
        .iter()
        .map(|node| (node.node_id, node))
        .collect();

    let mut scopes = Vec::with_capacity(scope_index.scopes.len());
    for scope in &scope_index.scopes {
        let syntax_ordinal = match scope.ast_node_id {
            None => None,
            Some(ast_node_id) => {
                validate_scope_node(
                    scope,
                    ast_node_id,
                    ingested.file_id,
                    &node_by_id,
                    semantic_handles,
                )?;
                Some(
                    *ordinal_by_node
                        .get(&ast_node_id)
                        .ok_or(ProfiledScopeError::ScopeAstNodeMissing(ast_node_id))?,
                )
            }
        };
        scopes.push(ProfiledScopeAnchorV1 {
            scope_id: scope.scope_id,
            parent_scope_id: scope.parent_scope_id,
            syntax_ordinal,
            ast_local_node_id: scope.ast_node_id,
            kind: scope.kind.as_str().to_owned(),
            name: scope.name.clone(),
            file_id: scope.file_id,
            byte_start: scope.byte_start,
            byte_end: scope.byte_end,
            semantic_handle_digest: scope.semantic_handle_digest,
        });
    }

    let mut bindings = Vec::with_capacity(scope_index.bindings.len());
    for binding in &scope_index.bindings {
        validate_binding_node(binding, ingested.file_id, &node_by_id, semantic_handles)?;
        let syntax_ordinal = *ordinal_by_node
            .get(&binding.ast_node_id)
            .ok_or(ProfiledScopeError::ScopeAstNodeMissing(binding.ast_node_id))?;
        bindings.push(ProfiledScopeBindingV1 {
            owner_scope_id: binding.owner_scope_id,
            ordinal_in_scope: binding.ordinal_in_scope,
            target_scope_id: binding.target_scope_id,
            syntax_ordinal,
            ast_local_node_id: binding.ast_node_id,
            kind: binding.kind.as_str().to_owned(),
            name: binding.name.clone(),
            file_id: binding.file_id,
            byte_start: binding.byte_start,
            byte_end: binding.byte_end,
            semantic_handle_digest: binding.semantic_handle_digest,
        });
    }
    Ok((scopes, bindings))
}

fn validate_scope_node(
    scope: &PythonScopeV1,
    ast_node_id: u64,
    expected_file_id: u32,
    node_by_id: &HashMap<u64, &aura_k27_astge_ingest::AstNodeV1>,
    semantic_handles: &HashMap<u64, [u8; 32]>,
) -> Result<(), ProfiledScopeError> {
    let node = node_by_id
        .get(&ast_node_id)
        .ok_or(ProfiledScopeError::ScopeAstNodeMissing(ast_node_id))?;
    if scope.file_id != expected_file_id {
        return Err(ProfiledScopeError::ScopeFileMismatch {
            ast_node_id,
            expected: expected_file_id,
            actual: scope.file_id,
        });
    }
    if scope.byte_start != node.byte_start || scope.byte_end != node.byte_end {
        return Err(ProfiledScopeError::ScopeSpanMismatch(ast_node_id));
    }
    let expected_handle = semantic_handles
        .get(&ast_node_id)
        .ok_or(ProfiledScopeError::ScopeHandleMissing(ast_node_id))?;
    if scope.semantic_handle_digest != Some(*expected_handle) {
        return Err(ProfiledScopeError::ScopeHandleMismatch(ast_node_id));
    }
    Ok(())
}

fn validate_binding_node(
    binding: &ScopeBindingV1,
    expected_file_id: u32,
    node_by_id: &HashMap<u64, &aura_k27_astge_ingest::AstNodeV1>,
    semantic_handles: &HashMap<u64, [u8; 32]>,
) -> Result<(), ProfiledScopeError> {
    let node = node_by_id
        .get(&binding.ast_node_id)
        .ok_or(ProfiledScopeError::ScopeAstNodeMissing(binding.ast_node_id))?;
    if binding.file_id != expected_file_id {
        return Err(ProfiledScopeError::ScopeFileMismatch {
            ast_node_id: binding.ast_node_id,
            expected: expected_file_id,
            actual: binding.file_id,
        });
    }
    if binding.byte_start != node.byte_start || binding.byte_end != node.byte_end {
        return Err(ProfiledScopeError::ScopeSpanMismatch(binding.ast_node_id));
    }
    let expected_handle = semantic_handles
        .get(&binding.ast_node_id)
        .ok_or(ProfiledScopeError::ScopeHandleMissing(binding.ast_node_id))?;
    if binding.semantic_handle_digest != *expected_handle {
        return Err(ProfiledScopeError::ScopeHandleMismatch(binding.ast_node_id));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

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

    fn identity_parts(
        source: &str,
        file_id: u32,
        generation: &str,
    ) -> (
        ParserGrammarBindingV1,
        NormalizationProfileV1,
        SyntaxSourceBindingV1,
        Vec<SyntaxNodeProjectionV1>,
        Vec<SyntaxEdgeProjectionV1>,
    ) {
        let (nodes, edges) = project_named_python_syntax(source).unwrap();
        (
            canonical_python_grammar(),
            canonical_python_profile(),
            syntax_source_binding(
                source,
                file_id,
                "source://fixture/python".to_owned(),
                generation.to_owned(),
            ),
            nodes,
            edges,
        )
    }

    #[test]
    fn profiled_nested_scopes_bind_exact_syntax_graph_and_scope_anchors() {
        let file_id = 91;
        let result = build_profiled_python_scopes(
            FIXTURE,
            file_id,
            "source://fixture/python",
            "git:profiled-scope-v1",
            &handles(FIXTURE, file_id),
        )
        .unwrap();
        assert_eq!(result.scope_count, 15);
        assert_eq!(result.profiled_scopes.len(), 15);
        assert_eq!(result.syntax_graph.grammar_name, "python");
        assert_eq!(
            result.syntax_graph.normalization_profile_ref,
            PYTHON_NAMED_PROFILE_REF
        );
        assert_eq!(result.syntax_graph.file_id, u64::from(file_id));
        assert!(result.profiled_scopes[0].syntax_ordinal.is_none());
        assert!(
            result
                .profiled_scopes
                .iter()
                .skip(1)
                .all(|scope| scope.syntax_ordinal.is_some())
        );
        assert!(
            result
                .profiled_bindings
                .iter()
                .all(|binding| binding.syntax_ordinal == binding.ast_local_node_id)
        );
        assert!(!result.local_ast_node_id_is_semantic_identity);
        assert!(!result.local_scope_id_is_semantic_identity);
        assert!(!result.runtime_name_resolution_proven);
        assert!(!result.call_graph_proven);
        assert!(!result.semantic_k27_derived);
        assert!(!result.external_effect_authorized);
    }

    #[test]
    fn local_node_id_remap_preserves_canonical_syntax_graph_identity() {
        let (grammar, profile, source, nodes, edges) =
            identity_parts(FIXTURE, 92, "git:identity-remap");
        let baseline = admit_syntax_graph(&grammar, &profile, &source, &nodes, &edges).unwrap();
        let remap: HashMap<u64, u64> = nodes
            .iter()
            .map(|node| (node.local_node_id, 10_000 + node.local_node_id * 17))
            .collect();
        let remapped_nodes: Vec<_> = nodes
            .iter()
            .cloned()
            .map(|mut node| {
                node.local_node_id = remap[&node.local_node_id];
                node
            })
            .collect();
        let remapped_edges: Vec<_> = edges
            .iter()
            .map(|edge| SyntaxEdgeProjectionV1 {
                parent_local_node_id: remap[&edge.parent_local_node_id],
                child_local_node_id: remap[&edge.child_local_node_id],
            })
            .collect();
        let remapped = admit_syntax_graph(
            &grammar,
            &profile,
            &source,
            &remapped_nodes,
            &remapped_edges,
        )
        .unwrap();
        assert_eq!(baseline.graph_sha256, remapped.graph_sha256);
    }

    #[test]
    fn normalization_profile_change_produces_distinct_graph_identity() {
        let (grammar, profile, source, nodes, edges) =
            identity_parts(FIXTURE, 93, "git:profile-change");
        let baseline = admit_syntax_graph(&grammar, &profile, &source, &nodes, &edges).unwrap();
        let mut altered = profile.clone();
        altered.profile_ref = "python/NAMED_ONLY/v2".to_owned();
        let changed = admit_syntax_graph(&grammar, &altered, &source, &nodes, &edges).unwrap();
        assert_ne!(baseline.graph_sha256, changed.graph_sha256);
    }

    #[test]
    fn source_generation_change_produces_distinct_graph_identity() {
        let (grammar, profile, source_a, nodes, edges) =
            identity_parts(FIXTURE, 94, "git:generation-a");
        let source_b = syntax_source_binding(
            FIXTURE,
            94,
            "source://fixture/python".to_owned(),
            "git:generation-b".to_owned(),
        );
        let a = admit_syntax_graph(&grammar, &profile, &source_a, &nodes, &edges).unwrap();
        let b = admit_syntax_graph(&grammar, &profile, &source_b, &nodes, &edges).unwrap();
        assert_ne!(a.graph_sha256, b.graph_sha256);
    }

    #[test]
    fn grammar_version_change_produces_distinct_graph_identity() {
        let (grammar, profile, source, nodes, edges) =
            identity_parts(FIXTURE, 95, "git:grammar-change");
        let baseline = admit_syntax_graph(&grammar, &profile, &source, &nodes, &edges).unwrap();
        let mut altered = grammar.clone();
        altered.grammar_version = "0.25.1-falsifier".to_owned();
        let changed = admit_syntax_graph(&altered, &profile, &source, &nodes, &edges).unwrap();
        assert_ne!(baseline.graph_sha256, changed.graph_sha256);
    }

    #[test]
    fn scope_handle_drift_fails_profiled_anchor_binding() {
        let file_id = 96;
        let semantic_handles = handles(FIXTURE, file_id);
        let ingested = parse_python_named_ast(FIXTURE, file_id).unwrap();
        let mut scope_index =
            index_python_nested_scopes(FIXTURE, file_id, &semantic_handles).unwrap();
        let victim = scope_index
            .scopes
            .iter_mut()
            .find(|scope| scope.ast_node_id.is_some())
            .unwrap();
        victim.semantic_handle_digest = Some([0xEE; 32]);
        assert!(matches!(
            bind_scope_anchors(&scope_index, &ingested, &semantic_handles),
            Err(ProfiledScopeError::ScopeHandleMismatch(_))
        ));
    }
}
