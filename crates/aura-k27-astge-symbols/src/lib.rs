#![forbid(unsafe_code)]

//! Conservative semantic symbol membrane over the verified ASTGE Python ingestion layer.
//!
//! V1 indexes only module-level function/class definitions. It preserves the storage-local AST
//! node id and an externally supplied semantic-handle digest, but it does not resolve calls,
//! imports, inheritance, attributes, runtime rebinding, or execution authority.

use aura_k27_astge_ingest::{IngestError, ParsedAstGraphV1, parse_python_named_ast};
use std::collections::{BTreeMap, HashMap};
use std::error::Error;
use std::fmt::{Display, Formatter};
use tree_sitter::{Node, Parser};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ModuleSymbolKindV1 {
    Function,
    Class,
}

impl ModuleSymbolKindV1 {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Function => "FUNCTION",
            Self::Class => "CLASS",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ModuleSymbolV1 {
    pub ordinal: u32,
    pub node_id: u64,
    pub kind: ModuleSymbolKindV1,
    pub name: String,
    pub file_id: u32,
    pub byte_start: u32,
    pub byte_end: u32,
    pub semantic_handle_digest: [u8; 32],
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PythonModuleSymbolIndexV1 {
    pub file_id: u32,
    pub source_len: u32,
    pub symbols: Vec<ModuleSymbolV1>,
    pub duplicate_names: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SymbolIndexError {
    Ingest(IngestError),
    ParserLanguage(String),
    ParseReturnedNone,
    ParseHasError,
    DefinitionNameMissing {
        definition_kind: String,
        byte_start: usize,
    },
    InvalidNameSpan {
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
    OrdinalOverflow,
}

impl Display for SymbolIndexError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for SymbolIndexError {}

impl From<IngestError> for SymbolIndexError {
    fn from(value: IngestError) -> Self {
        Self::Ingest(value)
    }
}

/// Index only definitions that bind names directly in the module block.
///
/// This function deliberately does not interpret these symbols as runtime targets. Python names
/// can be rebound dynamically, and nested/class/function scopes have additional binding rules.
pub fn index_python_module_symbols(
    source: &str,
    file_id: u32,
    semantic_handles: &HashMap<u64, [u8; 32]>,
) -> Result<PythonModuleSymbolIndexV1, SymbolIndexError> {
    let ingested = parse_python_named_ast(source, file_id)?;
    let mut parser = Parser::new();
    let language: tree_sitter::Language = tree_sitter_python::LANGUAGE.into();
    parser
        .set_language(&language)
        .map_err(|error| SymbolIndexError::ParserLanguage(error.to_string()))?;
    let tree = parser.parse(source, None).ok_or(SymbolIndexError::ParseReturnedNone)?;
    let root = tree.root_node();
    if root.has_error() {
        return Err(SymbolIndexError::ParseHasError);
    }

    let mut symbols = Vec::new();
    for child_index in 0..root.named_child_count() {
        let Some(top_level) = root.named_child(child_index) else {
            continue;
        };
        let Some(definition) = module_definition(top_level) else {
            continue;
        };
        let kind = match definition.kind() {
            "function_definition" => ModuleSymbolKindV1::Function,
            "class_definition" => ModuleSymbolKindV1::Class,
            _ => continue,
        };
        let name_node = definition.child_by_field_name("name").ok_or_else(|| {
            SymbolIndexError::DefinitionNameMissing {
                definition_kind: definition.kind().to_owned(),
                byte_start: definition.start_byte(),
            }
        })?;
        let name = source
            .get(name_node.start_byte()..name_node.end_byte())
            .ok_or(SymbolIndexError::InvalidNameSpan {
                byte_start: name_node.start_byte(),
                byte_end: name_node.end_byte(),
            })?
            .to_owned();
        let node_id = match_ast_node(&ingested, definition)?;
        let semantic_handle_digest = *semantic_handles
            .get(&node_id)
            .ok_or(SymbolIndexError::MissingSemanticHandle(node_id))?;
        let ordinal = u32::try_from(symbols.len()).map_err(|_| SymbolIndexError::OrdinalOverflow)?;
        symbols.push(ModuleSymbolV1 {
            ordinal,
            node_id,
            kind,
            name,
            file_id,
            byte_start: u32::try_from(definition.start_byte()).map_err(|_| {
                SymbolIndexError::InvalidNameSpan {
                    byte_start: definition.start_byte(),
                    byte_end: definition.end_byte(),
                }
            })?,
            byte_end: u32::try_from(definition.end_byte()).map_err(|_| {
                SymbolIndexError::InvalidNameSpan {
                    byte_start: definition.start_byte(),
                    byte_end: definition.end_byte(),
                }
            })?,
            semantic_handle_digest,
        });
    }

    let mut counts = BTreeMap::<String, usize>::new();
    for symbol in &symbols {
        *counts.entry(symbol.name.clone()).or_default() += 1;
    }
    let duplicate_names = counts
        .into_iter()
        .filter_map(|(name, count)| (count > 1).then_some(name))
        .collect();

    Ok(PythonModuleSymbolIndexV1 {
        file_id,
        source_len: ingested.source_len,
        symbols,
        duplicate_names,
    })
}

fn module_definition(top_level: Node<'_>) -> Option<Node<'_>> {
    match top_level.kind() {
        "function_definition" | "class_definition" => Some(top_level),
        "decorated_definition" => top_level
            .child_by_field_name("definition")
            .or_else(|| {
                (0..top_level.named_child_count())
                    .filter_map(|index| top_level.named_child(index))
                    .find(|child| matches!(child.kind(), "function_definition" | "class_definition"))
            }),
        _ => None,
    }
}

fn match_ast_node(
    ingested: &ParsedAstGraphV1,
    definition: Node<'_>,
) -> Result<u64, SymbolIndexError> {
    let mut matches = ingested.nodes.iter().filter(|node| {
        node.kind == definition.kind()
            && node.byte_start as usize == definition.start_byte()
            && node.byte_end as usize == definition.end_byte()
    });
    let Some(first) = matches.next() else {
        return Err(SymbolIndexError::AstNodeMissing {
            definition_kind: definition.kind().to_owned(),
            byte_start: definition.start_byte(),
            byte_end: definition.end_byte(),
        });
    };
    if matches.next().is_some() {
        return Err(SymbolIndexError::AstNodeAmbiguous {
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

    const FIXTURE: &str = include_str!("../fixtures/python_module_symbols.py");

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
    fn indexes_only_module_level_function_and_class_bindings_in_source_order() {
        let index = index_python_module_symbols(FIXTURE, 17, &handles(FIXTURE, 17)).expect("index");
        let observed: Vec<_> = index
            .symbols
            .iter()
            .map(|symbol| (symbol.kind.as_str(), symbol.name.as_str()))
            .collect();
        assert_eq!(
            observed,
            vec![
                ("FUNCTION", "alpha"),
                ("CLASS", "Box"),
                ("FUNCTION", "decorated"),
                ("FUNCTION", "outer"),
                ("FUNCTION", "alpha"),
            ]
        );
        assert!(!index.symbols.iter().any(|symbol| symbol.name == "nested"));
        assert_eq!(index.duplicate_names, vec!["alpha"]);
    }

    #[test]
    fn every_symbol_preserves_parent_ast_node_and_external_semantic_handle() {
        let supplied = handles(FIXTURE, 21);
        let graph = parse_python_named_ast(FIXTURE, 21).expect("parent ingestion");
        let index = index_python_module_symbols(FIXTURE, 21, &supplied).expect("index");
        for symbol in &index.symbols {
            let node = &graph.nodes[symbol.node_id as usize];
            assert_eq!(node.kind, match symbol.kind {
                ModuleSymbolKindV1::Function => "function_definition",
                ModuleSymbolKindV1::Class => "class_definition",
            });
            assert_eq!(symbol.byte_start, node.byte_start);
            assert_eq!(symbol.byte_end, node.byte_end);
            assert_eq!(symbol.semantic_handle_digest, supplied[&symbol.node_id]);
            assert_eq!(symbol.file_id, 21);
        }
    }

    #[test]
    fn missing_higher_owner_handle_fails_closed() {
        let mut supplied = handles(FIXTURE, 4);
        let baseline = index_python_module_symbols(FIXTURE, 4, &supplied).expect("baseline");
        let victim = baseline.symbols[0].node_id;
        supplied.remove(&victim);
        assert_eq!(
            index_python_module_symbols(FIXTURE, 4, &supplied),
            Err(SymbolIndexError::MissingSemanticHandle(victim))
        );
    }

    #[test]
    fn malformed_python_inherits_parent_fail_closed_parser_contract() {
        let source = "def broken(:\n";
        assert!(matches!(
            index_python_module_symbols(source, 1, &HashMap::new()),
            Err(SymbolIndexError::Ingest(IngestError::ParseHasError))
        ));
    }

    #[test]
    fn duplicate_module_names_are_reported_not_resolved() {
        let index = index_python_module_symbols(FIXTURE, 2, &handles(FIXTURE, 2)).expect("index");
        assert_eq!(index.duplicate_names, vec!["alpha"]);
        assert_eq!(index.symbols.iter().filter(|symbol| symbol.name == "alpha").count(), 2);
    }
}
