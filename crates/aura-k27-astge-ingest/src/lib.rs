#![forbid(unsafe_code)]

//! Tree-Sitter ingestion membrane for Aura K27 ASTGE.
//!
//! This crate owns only syntax-tree materialization into the already-owned physical
//! S-plane contract. It does not mint semantic identity, derive K27 coordinates,
//! infer symbols/calls, or grant source/currentness/review/effect authority.

use aura_k27_astge::{
    NodeIndexRecordV1, PageRow, PageSource, PhysicalPageV1, StorageError, BLOCK_SIZE,
    MAX_EDGES, MAX_ROWS,
};
use std::collections::{HashMap, HashSet, VecDeque};
use std::error::Error;
use std::fmt::{Display, Formatter};
use tree_sitter::{Node, Parser};

pub const EDGE_KIND_AST_CHILD: u8 = 1;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum IngestError {
    ParserLanguage(String),
    ParseReturnedNone,
    ParseHasError,
    SourceTooLarge(usize),
    NamedChildMissing { parent_kind: String, child_index: usize },
    MissingSemanticHandle(u64),
    NodeDegreeTooLarge { node_id: u64, degree: usize },
    MissingAstTarget(u64),
    Storage(StorageError),
}

impl Display for IngestError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for IngestError {}

impl From<StorageError> for IngestError {
    fn from(value: StorageError) -> Self {
        Self::Storage(value)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AstNodeV1 {
    /// Storage-local deterministic preorder ID. It is not a semantic identity.
    pub node_id: u64,
    pub kind: String,
    pub byte_start: u32,
    pub byte_end: u32,
    pub children: Vec<u64>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParsedAstGraphV1 {
    pub file_id: u32,
    pub source_len: u32,
    pub root_id: u64,
    pub nodes: Vec<AstNodeV1>,
}

impl ParsedAstGraphV1 {
    pub fn edge_count(&self) -> usize {
        self.nodes.iter().map(|node| node.children.len()).sum()
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EncodedSPlaneAstV1 {
    pub records: Vec<NodeIndexRecordV1>,
    pub pages: Vec<(u64, [u8; BLOCK_SIZE])>,
    pub node_count: usize,
    pub edge_count: usize,
}

/// Parse named Python syntax nodes in deterministic preorder.
///
/// Preorder assignment is deliberate: a node record is materialized before its
/// descendants receive IDs, preventing the prototype's preorder-ID/postorder-record
/// mismatch. Only Tree-Sitter named syntax nodes are included.
pub fn parse_python_named_ast(source: &str, file_id: u32) -> Result<ParsedAstGraphV1, IngestError> {
    let source_len = u32::try_from(source.len()).map_err(|_| IngestError::SourceTooLarge(source.len()))?;
    let mut parser = Parser::new();
    let language: tree_sitter::Language = tree_sitter_python::LANGUAGE.into();
    parser
        .set_language(&language)
        .map_err(|error| IngestError::ParserLanguage(error.to_string()))?;
    let tree = parser.parse(source, None).ok_or(IngestError::ParseReturnedNone)?;
    let root = tree.root_node();
    if root.has_error() {
        return Err(IngestError::ParseHasError);
    }

    let mut nodes = Vec::new();
    let root_id = walk_named_preorder(root, &mut nodes)?;
    Ok(ParsedAstGraphV1 {
        file_id,
        source_len,
        root_id,
        nodes,
    })
}

fn walk_named_preorder(node: Node<'_>, out: &mut Vec<AstNodeV1>) -> Result<u64, IngestError> {
    let node_id = out.len() as u64;
    let byte_start = u32::try_from(node.start_byte())
        .map_err(|_| IngestError::SourceTooLarge(node.start_byte()))?;
    let byte_end = u32::try_from(node.end_byte())
        .map_err(|_| IngestError::SourceTooLarge(node.end_byte()))?;
    let slot = out.len();
    out.push(AstNodeV1 {
        node_id,
        kind: node.kind().to_owned(),
        byte_start,
        byte_end,
        children: Vec::new(),
    });

    for child_index in 0..node.named_child_count() {
        let child = node
            .named_child(child_index as u32)
            .ok_or_else(|| IngestError::NamedChildMissing {
                parent_kind: node.kind().to_owned(),
                child_index,
            })?;
        let child_id = walk_named_preorder(child, out)?;
        out[slot].children.push(child_id);
    }
    Ok(node_id)
}

/// Encode a parsed AST into PR461's physical S-plane contract.
///
/// `semantic_handles` must come from the higher semantic/source owner. This ingestion
/// membrane refuses to synthesize them from syntax kind, source bytes, node ID, or K27.
pub fn encode_ast_to_splane(
    graph: &ParsedAstGraphV1,
    semantic_handles: &HashMap<u64, [u8; 32]>,
    base_pbn: u64,
    placement_generation: u64,
    placement_scheme_digest: [u8; 32],
) -> Result<EncodedSPlaneAstV1, IngestError> {
    let known_ids: HashSet<u64> = graph.nodes.iter().map(|node| node.node_id).collect();
    let mut records = Vec::with_capacity(graph.nodes.len());
    let mut pages = Vec::new();
    let mut rows = Vec::<PageRow>::new();
    let mut targets = Vec::<u64>::new();
    let mut kinds = Vec::<u8>::new();
    let mut pbn = base_pbn;

    for node in &graph.nodes {
        if node.children.len() > MAX_EDGES {
            return Err(IngestError::NodeDegreeTooLarge {
                node_id: node.node_id,
                degree: node.children.len(),
            });
        }
        for target in &node.children {
            if !known_ids.contains(target) {
                return Err(IngestError::MissingAstTarget(*target));
            }
        }
        let semantic_handle_digest = *semantic_handles
            .get(&node.node_id)
            .ok_or(IngestError::MissingSemanticHandle(node.node_id))?;

        if !rows.is_empty()
            && (rows.len() == MAX_ROWS || targets.len() + node.children.len() > MAX_EDGES)
        {
            flush_page(
                &mut pages,
                pbn,
                placement_generation,
                placement_scheme_digest,
                &mut rows,
                &mut targets,
                &mut kinds,
            )?;
            pbn = pbn
                .checked_add(1)
                .ok_or_else(|| IngestError::Storage(StorageError::Io("PBN overflow".to_owned())))?;
        }

        let row = rows.len() as u16;
        let first_edge = targets.len() as u16;
        rows.push(PageRow {
            first_edge,
            degree: node.children.len() as u16,
        });
        targets.extend(node.children.iter().copied());
        kinds.extend(std::iter::repeat_n(EDGE_KIND_AST_CHILD, node.children.len()));
        records.push(NodeIndexRecordV1 {
            node_id: node.node_id,
            semantic_handle_digest,
            pbn,
            row,
            out_degree: node.children.len() as u16,
            file_id: graph.file_id,
            byte_start: node.byte_start,
            byte_end: node.byte_end,
        });
    }

    if !rows.is_empty() {
        flush_page(
            &mut pages,
            pbn,
            placement_generation,
            placement_scheme_digest,
            &mut rows,
            &mut targets,
            &mut kinds,
        )?;
    }

    Ok(EncodedSPlaneAstV1 {
        records,
        pages,
        node_count: graph.nodes.len(),
        edge_count: graph.edge_count(),
    })
}

fn flush_page(
    pages: &mut Vec<(u64, [u8; BLOCK_SIZE])>,
    pbn: u64,
    placement_generation: u64,
    placement_scheme_digest: [u8; 32],
    rows: &mut Vec<PageRow>,
    targets: &mut Vec<u64>,
    kinds: &mut Vec<u8>,
) -> Result<(), IngestError> {
    let page = PhysicalPageV1 {
        pbn,
        placement_generation,
        placement_scheme_digest,
        rows: std::mem::take(rows),
        targets: std::mem::take(targets),
        edge_kinds: std::mem::take(kinds),
    };
    pages.push((pbn, page.encode()?));
    Ok(())
}

#[derive(Debug, Clone)]
pub struct MemoryPageSource {
    pages: HashMap<u64, [u8; BLOCK_SIZE]>,
}

impl MemoryPageSource {
    pub fn from_encoded(encoded: &EncodedSPlaneAstV1) -> Self {
        Self {
            pages: encoded.pages.iter().copied().collect(),
        }
    }
}

impl PageSource for MemoryPageSource {
    fn read_page(&mut self, pbn: u64) -> Result<[u8; BLOCK_SIZE], StorageError> {
        self.pages
            .get(&pbn)
            .copied()
            .ok_or_else(|| StorageError::Io(format!("missing in-memory page {pbn}")))
    }
}

/// Independent direct adjacency oracle for ingestion tests/conformance.
pub fn direct_ast_cone(
    graph: &ParsedAstGraphV1,
    root_id: u64,
    max_depth: usize,
) -> Result<(Vec<u64>, usize), IngestError> {
    let by_id: HashMap<u64, &AstNodeV1> = graph.nodes.iter().map(|node| (node.node_id, node)).collect();
    if !by_id.contains_key(&root_id) {
        return Err(IngestError::MissingAstTarget(root_id));
    }
    let mut queue = VecDeque::from([(root_id, 0usize)]);
    let mut visited = HashSet::from([root_id]);
    let mut nodes = Vec::new();
    let mut edges = 0usize;
    while let Some((node_id, depth)) = queue.pop_front() {
        nodes.push(node_id);
        if depth >= max_depth {
            continue;
        }
        let node = by_id[&node_id];
        for target in &node.children {
            edges += 1;
            if visited.insert(*target) {
                queue.push_back((*target, depth + 1));
            }
        }
    }
    Ok((nodes, edges))
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge::{PhysicalPageV1, SPlaneGraphReader};

    const FIXTURE: &str = "def add(a, b):\n    total = a + b\n    return total\n\nprint(add(1, 2))\n";

    fn handles(graph: &ParsedAstGraphV1) -> HashMap<u64, [u8; 32]> {
        graph
            .nodes
            .iter()
            .map(|node| {
                let mut digest = [0u8; 32];
                digest[0..8].copy_from_slice(&node.node_id.to_le_bytes());
                digest[8..12].copy_from_slice(&graph.file_id.to_le_bytes());
                digest[12..16].copy_from_slice(&node.byte_start.to_le_bytes());
                digest[16..20].copy_from_slice(&node.byte_end.to_le_bytes());
                (node.node_id, digest)
            })
            .collect()
    }

    #[test]
    fn python_named_ast_is_preorder_span_bound_and_error_free() {
        let graph = parse_python_named_ast(FIXTURE, 7).expect("parse fixture");
        assert_eq!(graph.root_id, 0);
        assert_eq!(graph.nodes[0].kind, "module");
        assert_eq!(graph.nodes[0].byte_start, 0);
        assert_eq!(graph.nodes[0].byte_end as usize, FIXTURE.len());
        assert_eq!(graph.source_len as usize, FIXTURE.len());
        assert!(!graph.nodes.is_empty());
        assert_eq!(graph.edge_count(), graph.nodes.len() - 1);
        for (index, node) in graph.nodes.iter().enumerate() {
            assert_eq!(node.node_id, index as u64);
            assert!(node.byte_start <= node.byte_end);
            assert!(node.byte_end <= graph.source_len);
            for child in &node.children {
                assert!(*child > node.node_id, "preorder child must follow parent");
            }
        }
    }

    #[test]
    fn tree_sitter_ingest_round_trips_through_pr461_splane_cone() {
        let graph = parse_python_named_ast(FIXTURE, 11).expect("parse fixture");
        let encoded = encode_ast_to_splane(&graph, &handles(&graph), 41, 3, [0xA5; 32])
            .expect("encode S-plane");
        let source = MemoryPageSource::from_encoded(&encoded);
        let mut reader = SPlaneGraphReader::new(encoded.records.clone(), source).expect("reader");
        let observed = reader
            .query_cone(graph.root_id, 3, graph.nodes.len() + 1, Some(EDGE_KIND_AST_CHILD))
            .expect("query");
        let (expected_nodes, expected_edges) = direct_ast_cone(&graph, graph.root_id, 3).expect("oracle");
        assert_eq!(observed.node_ids, expected_nodes);
        assert_eq!(observed.edges_traversed, expected_edges);
        assert!(observed.unique_pages >= 1);
        assert_eq!(encoded.node_count, graph.nodes.len());
        assert_eq!(encoded.edge_count, graph.edge_count());
        for record in &encoded.records {
            let parsed = &graph.nodes[record.node_id as usize];
            assert_eq!(record.file_id, graph.file_id);
            assert_eq!(record.byte_start, parsed.byte_start);
            assert_eq!(record.byte_end, parsed.byte_end);
        }
    }

    #[test]
    fn semantic_handle_must_be_supplied_by_higher_owner() {
        let graph = parse_python_named_ast(FIXTURE, 13).expect("parse fixture");
        let mut supplied = handles(&graph);
        supplied.remove(&0);
        assert_eq!(
            encode_ast_to_splane(&graph, &supplied, 0, 1, [1; 32]),
            Err(IngestError::MissingSemanticHandle(0))
        );
    }

    #[test]
    fn invalid_python_fails_closed_instead_of_materializing_error_tree() {
        assert_eq!(
            parse_python_named_ast("def broken(:\n", 1),
            Err(IngestError::ParseHasError)
        );
    }

    #[test]
    fn large_ast_spans_multiple_exact_splane_pages_without_reclassifying_identity() {
        let source: String = (0..180).map(|i| format!("value_{i} = {i}\n")).collect();
        let graph = parse_python_named_ast(&source, 99).expect("parse large fixture");
        let supplied = handles(&graph);
        let encoded = encode_ast_to_splane(&graph, &supplied, 700, 12, [0x5C; 32])
            .expect("encode large graph");
        assert!(encoded.pages.len() > 1);
        for (offset, (pbn, raw)) in encoded.pages.iter().enumerate() {
            assert_eq!(*pbn, 700 + offset as u64);
            let page = PhysicalPageV1::decode(raw).expect("decode page");
            assert_eq!(page.pbn, *pbn);
            assert_eq!(page.placement_generation, 12);
            assert_eq!(page.placement_scheme_digest, [0x5C; 32]);
        }
        for (index, record) in encoded.records.iter().enumerate() {
            assert_eq!(record.node_id, index as u64);
            assert_eq!(record.semantic_handle_digest, supplied[&record.node_id]);
        }
    }
}
