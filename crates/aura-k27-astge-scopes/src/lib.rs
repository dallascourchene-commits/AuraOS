#![forbid(unsafe_code)]

//! Conservative Python lexical-scope inventory over the verified named-AST ingestion layer.
//!
//! V1 models only module/function/class scope ownership for `def`/`class` bindings. It does not
//! resolve identifier uses, globals/nonlocals, closures, imports, attributes, calls, lambdas,
//! comprehension scopes, annotation/type-parameter scopes, or runtime binding winners.

use aura_k27_astge_ingest::{IngestError, ParsedAstGraphV1, parse_python_named_ast};
use std::collections::{BTreeMap, HashMap};
use std::error::Error;
use std::fmt::{Display, Formatter};
use tree_sitter::{Node, Parser};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ScopeKindV1 {
    Module,
    Function,
    Class,
}

impl ScopeKindV1 {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Module => "MODULE",
            Self::Function => "FUNCTION",
            Self::Class => "CLASS",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ScopeBindingKindV1 {
    Function,
    Class,
}

impl ScopeBindingKindV1 {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Function => "FUNCTION",
            Self::Class => "CLASS",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PythonScopeV1 {
    /// Deterministic inventory-local preorder ID. Not semantic identity.
    pub scope_id: u64,
    pub parent_scope_id: Option<u64>,
    pub ast_node_id: Option<u64>,
    pub kind: ScopeKindV1,
    pub name: String,
    pub file_id: u32,
    pub byte_start: u32,
    pub byte_end: u32,
    /// 0 for module; otherwise one-based source line of the defining `def`/`class`.
    pub line_start: u32,
    pub semantic_handle_digest: Option<[u8; 32]>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScopeBindingV1 {
    pub owner_scope_id: u64,
    pub ordinal_in_scope: u32,
    pub target_scope_id: u64,
    pub ast_node_id: u64,
    pub kind: ScopeBindingKindV1,
    pub name: String,
    pub file_id: u32,
    pub byte_start: u32,
    pub byte_end: u32,
    pub line_start: u32,
    pub semantic_handle_digest: [u8; 32],
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScopeDuplicateNamesV1 {
    pub scope_id: u64,
    pub names: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PythonLexicalScopeIndexV1 {
    pub file_id: u32,
    pub source_len: u32,
    pub scopes: Vec<PythonScopeV1>,
    pub bindings: Vec<ScopeBindingV1>,
    pub duplicate_names_by_scope: Vec<ScopeDuplicateNamesV1>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ScopeIndexError {
    Ingest(IngestError),
    ParserLanguage(String),
    ParseReturnedNone,
    ParseHasError,
    NamedChildMissing {
        parent_kind: String,
        child_index: usize,
    },
    DefinitionNameMissing {
        definition_kind: String,
        byte_start: usize,
    },
    DefinitionBodyMissing {
        definition_kind: String,
        byte_start: usize,
    },
    InvalidSourceSpan {
        byte_start: usize,
        byte_end: usize,
    },
    AstNodeMissing {
        definition_kind: String,
        byte_start: usize,
        byte_end: usize,
    },
    AstNodeAmbiguous {
        definition_kind: String,
        byte_start: usize,
        byte_end: usize,
    },
    MissingSemanticHandle(u64),
    ScopeIdOverflow,
    OrdinalOverflow,
    LineOverflow,
}

impl Display for ScopeIndexError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for ScopeIndexError {}

impl From<IngestError> for ScopeIndexError {
    fn from(value: IngestError) -> Self {
        Self::Ingest(value)
    }
}

pub fn index_python_nested_scopes(
    source: &str,
    file_id: u32,
    semantic_handles: &HashMap<u64, [u8; 32]>,
) -> Result<PythonLexicalScopeIndexV1, ScopeIndexError> {
    let ingested = parse_python_named_ast(source, file_id)?;
    let mut parser = Parser::new();
    let language: tree_sitter::Language = tree_sitter_python::LANGUAGE.into();
    parser
        .set_language(&language)
        .map_err(|error| ScopeIndexError::ParserLanguage(error.to_string()))?;
    let tree = parser
        .parse(source, None)
        .ok_or(ScopeIndexError::ParseReturnedNone)?;
    let root = tree.root_node();
    if root.has_error() {
        return Err(ScopeIndexError::ParseHasError);
    }

    let mut scopes = vec![PythonScopeV1 {
        scope_id: 0,
        parent_scope_id: None,
        ast_node_id: None,
        kind: ScopeKindV1::Module,
        name: "<module>".to_owned(),
        file_id,
        byte_start: 0,
        byte_end: ingested.source_len,
        line_start: 0,
        semantic_handle_digest: None,
    }];
    let mut bindings = Vec::new();

    walk_scope_contents(
        root,
        0,
        source,
        file_id,
        &ingested,
        semantic_handles,
        &mut scopes,
        &mut bindings,
    )?;

    let mut counts = BTreeMap::<(u64, String), usize>::new();
    for binding in &bindings {
        *counts
            .entry((binding.owner_scope_id, binding.name.clone()))
            .or_default() += 1;
    }
    let mut grouped = BTreeMap::<u64, Vec<String>>::new();
    for ((scope_id, name), count) in counts {
        if count > 1 {
            grouped.entry(scope_id).or_default().push(name);
        }
    }
    let duplicate_names_by_scope = grouped
        .into_iter()
        .map(|(scope_id, names)| ScopeDuplicateNamesV1 { scope_id, names })
        .collect();

    Ok(PythonLexicalScopeIndexV1 {
        file_id,
        source_len: ingested.source_len,
        scopes,
        bindings,
        duplicate_names_by_scope,
    })
}

#[allow(clippy::too_many_arguments)]
fn walk_scope_contents(
    container: Node<'_>,
    owner_scope_id: u64,
    source: &str,
    file_id: u32,
    ingested: &ParsedAstGraphV1,
    semantic_handles: &HashMap<u64, [u8; 32]>,
    scopes: &mut Vec<PythonScopeV1>,
    bindings: &mut Vec<ScopeBindingV1>,
) -> Result<(), ScopeIndexError> {
    for child_index in 0..container.named_child_count() {
        let child = container.named_child(child_index).ok_or_else(|| {
            ScopeIndexError::NamedChildMissing {
                parent_kind: container.kind().to_owned(),
                child_index,
            }
        })?;
        if let Some(definition) = scope_definition(child) {
            add_definition_scope(
                definition,
                owner_scope_id,
                source,
                file_id,
                ingested,
                semantic_handles,
                scopes,
                bindings,
            )?;
        } else {
            walk_scope_contents(
                child,
                owner_scope_id,
                source,
                file_id,
                ingested,
                semantic_handles,
                scopes,
                bindings,
            )?;
        }
    }
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn add_definition_scope(
    definition: Node<'_>,
    owner_scope_id: u64,
    source: &str,
    file_id: u32,
    ingested: &ParsedAstGraphV1,
    semantic_handles: &HashMap<u64, [u8; 32]>,
    scopes: &mut Vec<PythonScopeV1>,
    bindings: &mut Vec<ScopeBindingV1>,
) -> Result<(), ScopeIndexError> {
    let (scope_kind, binding_kind) = match definition.kind() {
        "function_definition" => (ScopeKindV1::Function, ScopeBindingKindV1::Function),
        "class_definition" => (ScopeKindV1::Class, ScopeBindingKindV1::Class),
        _ => return Ok(()),
    };
    let name_node = definition.child_by_field_name("name").ok_or_else(|| {
        ScopeIndexError::DefinitionNameMissing {
            definition_kind: definition.kind().to_owned(),
            byte_start: definition.start_byte(),
        }
    })?;
    let name = source
        .get(name_node.start_byte()..name_node.end_byte())
        .ok_or(ScopeIndexError::InvalidSourceSpan {
            byte_start: name_node.start_byte(),
            byte_end: name_node.end_byte(),
        })?
        .to_owned();
    let ast_node_id = match_ast_node(ingested, definition)?;
    let semantic_handle_digest = *semantic_handles
        .get(&ast_node_id)
        .ok_or(ScopeIndexError::MissingSemanticHandle(ast_node_id))?;
    let scope_id = u64::try_from(scopes.len()).map_err(|_| ScopeIndexError::ScopeIdOverflow)?;
    let ordinal_in_scope = u32::try_from(
        bindings
            .iter()
            .filter(|binding| binding.owner_scope_id == owner_scope_id)
            .count(),
    )
    .map_err(|_| ScopeIndexError::OrdinalOverflow)?;
    let byte_start =
        u32::try_from(definition.start_byte()).map_err(|_| ScopeIndexError::InvalidSourceSpan {
            byte_start: definition.start_byte(),
            byte_end: definition.end_byte(),
        })?;
    let byte_end =
        u32::try_from(definition.end_byte()).map_err(|_| ScopeIndexError::InvalidSourceSpan {
            byte_start: definition.start_byte(),
            byte_end: definition.end_byte(),
        })?;
    let line_start = u32::try_from(definition.start_position().row + 1)
        .map_err(|_| ScopeIndexError::LineOverflow)?;

    scopes.push(PythonScopeV1 {
        scope_id,
        parent_scope_id: Some(owner_scope_id),
        ast_node_id: Some(ast_node_id),
        kind: scope_kind,
        name: name.clone(),
        file_id,
        byte_start,
        byte_end,
        line_start,
        semantic_handle_digest: Some(semantic_handle_digest),
    });
    bindings.push(ScopeBindingV1 {
        owner_scope_id,
        ordinal_in_scope,
        target_scope_id: scope_id,
        ast_node_id,
        kind: binding_kind,
        name,
        file_id,
        byte_start,
        byte_end,
        line_start,
        semantic_handle_digest,
    });

    let body = definition.child_by_field_name("body").ok_or_else(|| {
        ScopeIndexError::DefinitionBodyMissing {
            definition_kind: definition.kind().to_owned(),
            byte_start: definition.start_byte(),
        }
    })?;
    walk_scope_contents(
        body,
        scope_id,
        source,
        file_id,
        ingested,
        semantic_handles,
        scopes,
        bindings,
    )
}

fn scope_definition(node: Node<'_>) -> Option<Node<'_>> {
    match node.kind() {
        "function_definition" | "class_definition" => Some(node),
        "decorated_definition" => node.child_by_field_name("definition").or_else(|| {
            (0..node.named_child_count())
                .filter_map(|index| node.named_child(index))
                .find(|child| matches!(child.kind(), "function_definition" | "class_definition"))
        }),
        _ => None,
    }
}

fn match_ast_node(
    ingested: &ParsedAstGraphV1,
    definition: Node<'_>,
) -> Result<u64, ScopeIndexError> {
    let mut matches = ingested.nodes.iter().filter(|node| {
        node.kind == definition.kind()
            && node.byte_start as usize == definition.start_byte()
            && node.byte_end as usize == definition.end_byte()
    });
    let Some(first) = matches.next() else {
        return Err(ScopeIndexError::AstNodeMissing {
            definition_kind: definition.kind().to_owned(),
            byte_start: definition.start_byte(),
            byte_end: definition.end_byte(),
        });
    };
    if matches.next().is_some() {
        return Err(ScopeIndexError::AstNodeAmbiguous {
            definition_kind: definition.kind().to_owned(),
            byte_start: definition.start_byte(),
            byte_end: definition.end_byte(),
        });
    }
    Ok(first.node_id)
}

#[cfg(test)]
mod tests {
    use super::*;

    const FIXTURE: &str = include_str!("../fixtures/python_nested_scopes.py");

    fn handles(source: &str, file_id: u32) -> HashMap<u64, [u8; 32]> {
        let graph = parse_python_named_ast(source, file_id).expect("parent ingestion");
        graph
            .nodes
            .iter()
            .map(|node| {
                let mut digest = [0u8; 32];
                digest[0..8].copy_from_slice(&node.node_id.to_le_bytes());
                digest[8..12].copy_from_slice(&file_id.to_le_bytes());
                (node.node_id, digest)
            })
            .collect()
    }

    #[test]
    fn scope_tree_is_deterministic_preorder_and_preserves_nested_boundaries() {
        let index = index_python_nested_scopes(FIXTURE, 31, &handles(FIXTURE, 31)).unwrap();
        let observed: Vec<_> = index
            .scopes
            .iter()
            .map(|scope| {
                (
                    scope.scope_id,
                    scope.parent_scope_id,
                    scope.kind.as_str(),
                    scope.name.as_str(),
                    scope.line_start,
                )
            })
            .collect();
        assert_eq!(
            observed,
            vec![
                (0, None, "MODULE", "<module>", 0),
                (1, Some(0), "FUNCTION", "deco", 1),
                (2, Some(0), "FUNCTION", "outer", 5),
                (3, Some(2), "FUNCTION", "inner", 6),
                (4, Some(2), "FUNCTION", "conditional", 10),
                (5, Some(2), "FUNCTION", "inner", 13),
                (6, Some(2), "CLASS", "Local", 16),
                (7, Some(6), "FUNCTION", "method", 17),
                (8, Some(7), "FUNCTION", "deeply", 18),
                (9, Some(0), "CLASS", "Box", 24),
                (10, Some(9), "FUNCTION", "method", 25),
                (11, Some(10), "FUNCTION", "helper", 26),
                (12, Some(9), "CLASS", "Nested", 30),
                (13, Some(12), "FUNCTION", "n", 31),
                (14, Some(0), "FUNCTION", "tail", 34),
            ]
        );
    }

    #[test]
    fn statement_nesting_does_not_create_a_false_scope() {
        let index = index_python_nested_scopes(FIXTURE, 32, &handles(FIXTURE, 32)).unwrap();
        let conditional = index
            .bindings
            .iter()
            .find(|binding| binding.name == "conditional")
            .expect("conditional binding");
        let outer = index
            .scopes
            .iter()
            .find(|scope| scope.name == "outer")
            .expect("outer scope");
        assert_eq!(conditional.owner_scope_id, outer.scope_id);
    }

    #[test]
    fn duplicate_names_are_retained_per_scope_without_winner_selection() {
        let index = index_python_nested_scopes(FIXTURE, 33, &handles(FIXTURE, 33)).unwrap();
        let outer = index
            .scopes
            .iter()
            .find(|scope| scope.name == "outer")
            .expect("outer scope");
        let inners: Vec<_> = index
            .bindings
            .iter()
            .filter(|binding| binding.owner_scope_id == outer.scope_id && binding.name == "inner")
            .collect();
        assert_eq!(inners.len(), 2);
        assert_ne!(inners[0].target_scope_id, inners[1].target_scope_id);
        assert_eq!(
            index.duplicate_names_by_scope,
            vec![ScopeDuplicateNamesV1 {
                scope_id: outer.scope_id,
                names: vec!["inner".to_owned()],
            }]
        );
    }

    #[test]
    fn class_and_function_boundaries_keep_exact_definition_owner() {
        let index = index_python_nested_scopes(FIXTURE, 34, &handles(FIXTURE, 34)).unwrap();
        let local = index
            .scopes
            .iter()
            .find(|scope| scope.name == "Local")
            .unwrap();
        let local_method = index
            .scopes
            .iter()
            .find(|scope| scope.parent_scope_id == Some(local.scope_id) && scope.name == "method")
            .unwrap();
        let deeply = index
            .bindings
            .iter()
            .find(|binding| binding.name == "deeply")
            .unwrap();
        assert_eq!(deeply.owner_scope_id, local_method.scope_id);
    }

    #[test]
    fn every_nonmodule_scope_preserves_parent_ast_node_and_higher_owner_handle() {
        let supplied = handles(FIXTURE, 35);
        let graph = parse_python_named_ast(FIXTURE, 35).unwrap();
        let index = index_python_nested_scopes(FIXTURE, 35, &supplied).unwrap();
        for scope in index.scopes.iter().skip(1) {
            let node_id = scope.ast_node_id.expect("definition node");
            let node = &graph.nodes[node_id as usize];
            assert_eq!(scope.byte_start, node.byte_start);
            assert_eq!(scope.byte_end, node.byte_end);
            assert_eq!(scope.semantic_handle_digest, Some(supplied[&node_id]));
        }
    }

    #[test]
    fn missing_higher_owner_handle_fails_closed() {
        let mut supplied = handles(FIXTURE, 36);
        let baseline = index_python_nested_scopes(FIXTURE, 36, &supplied).unwrap();
        let victim = baseline.scopes[2].ast_node_id.unwrap();
        supplied.remove(&victim);
        assert_eq!(
            index_python_nested_scopes(FIXTURE, 36, &supplied),
            Err(ScopeIndexError::MissingSemanticHandle(victim))
        );
    }

    #[test]
    fn malformed_python_inherits_parent_fail_closed_parser_contract() {
        let source = "def broken(:\n";
        assert!(matches!(
            index_python_nested_scopes(source, 37, &HashMap::new()),
            Err(ScopeIndexError::Ingest(IngestError::ParseHasError))
        ));
    }

    #[test]
    fn repeated_indexing_is_exactly_deterministic() {
        let supplied = handles(FIXTURE, 38);
        let a = index_python_nested_scopes(FIXTURE, 38, &supplied).unwrap();
        let b = index_python_nested_scopes(FIXTURE, 38, &supplied).unwrap();
        assert_eq!(a, b);
    }
}
