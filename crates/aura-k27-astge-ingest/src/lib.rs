#![forbid(unsafe_code)]

//! Tree-Sitter ingestion membrane for Aura K27 ASTGE, rebased onto the current
//! generation-bound storage/backend-admission stack.
//!
//! The parser owns syntax materialization only. It does not mint semantic identity,
//! derive semantic K27 coordinates, choose an mmap backend, or grant authority.

use aura_k27_astge::{
    BLOCK_SIZE, MAX_EDGES, MAX_ROWS, NodeIndexRecordV1, PageRow, PhysicalPageV1, StorageError,
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
    NamedChildMissing {
        parent_kind: String,
        child_index: usize,
    },
    MissingSemanticHandle(u64),
    NodeDegreeTooLarge {
        node_id: u64,
        degree: usize,
    },
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
    /// Deterministic storage-local preorder ID. Never semantic identity.
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

/// PR469 producer contract: named Python nodes are materialized in deterministic preorder.
pub fn parse_python_named_ast(source: &str, file_id: u32) -> Result<ParsedAstGraphV1, IngestError> {
    let source_len =
        u32::try_from(source.len()).map_err(|_| IngestError::SourceTooLarge(source.len()))?;
    let mut parser = Parser::new();
    let language: tree_sitter::Language = tree_sitter_python::LANGUAGE.into();
    parser
        .set_language(&language)
        .map_err(|error| IngestError::ParserLanguage(error.to_string()))?;
    let tree = parser
        .parse(source, None)
        .ok_or(IngestError::ParseReturnedNone)?;
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
    let byte_end =
        u32::try_from(node.end_byte()).map_err(|_| IngestError::SourceTooLarge(node.end_byte()))?;
    let slot = out.len();
    out.push(AstNodeV1 {
        node_id,
        kind: node.kind().to_owned(),
        byte_start,
        byte_end,
        children: Vec::new(),
    });

    for child_index in 0..node.named_child_count() {
        let child =
            node.named_child(child_index)
                .ok_or_else(|| IngestError::NamedChildMissing {
                    parent_kind: node.kind().to_owned(),
                    child_index,
                })?;
        let child_id = walk_named_preorder(child, out)?;
        out[slot].children.push(child_id);
    }
    Ok(node_id)
}

/// Encode syntax into the physical page/index ABI. `base_pbn=0` is required for a standalone
/// generation file because StorageGenerationBindingV1 addresses page-file slots from zero.
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
        kinds.extend(std::iter::repeat_n(
            EDGE_KIND_AST_CHILD,
            node.children.len(),
        ));
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

/// Independent syntax adjacency oracle; does not consume storage bytes.
pub fn direct_ast_cone(
    graph: &ParsedAstGraphV1,
    root_id: u64,
    max_depth: usize,
) -> Result<(Vec<u64>, usize), IngestError> {
    let by_id: HashMap<u64, &AstNodeV1> = graph
        .nodes
        .iter()
        .map(|node| (node.node_id, node))
        .collect();
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
    use aura_k27_astge::{
        BackendAdmissionReasonV1, DataServingBackendV1, GenerationBoundGraphReader,
        GenerationStorageError, PhysicalPageV1, StorageGenerationBindingV1,
        admit_data_serving_backend,
    };
    use std::fs::{File, OpenOptions, create_dir_all, remove_dir_all};
    use std::io::{Seek, SeekFrom, Write};
    use std::path::{Path, PathBuf};
    use std::time::{SystemTime, UNIX_EPOCH};

    const FIXTURE: &str =
        "def add(a, b):\n    total = a + b\n    return total\n\nprint(add(1, 2))\n";

    fn temp_root(label: &str) -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = std::env::temp_dir().join(format!(
            "aura-k27-astge-ingest-current-{label}-{}-{nonce}",
            std::process::id()
        ));
        create_dir_all(&root).unwrap();
        root
    }

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

    fn write_generation(
        root: &Path,
        encoded: &EncodedSPlaneAstV1,
        generation: u64,
        scheme: [u8; 32],
    ) -> (PathBuf, PathBuf, StorageGenerationBindingV1) {
        let node_path = root.join("nodes.idx");
        let page_path = root.join("pages.bin");
        let mut nodes = File::create(&node_path).unwrap();
        for record in &encoded.records {
            nodes.write_all(&record.encode()).unwrap();
        }
        nodes.sync_all().unwrap();
        let mut pages = File::create(&page_path).unwrap();
        for (expected_pbn, (pbn, raw)) in encoded.pages.iter().enumerate() {
            assert_eq!(*pbn, expected_pbn as u64);
            pages.write_all(raw).unwrap();
        }
        pages.sync_all().unwrap();
        (
            node_path,
            page_path,
            StorageGenerationBindingV1 {
                node_count: encoded.node_count as u64,
                page_count: encoded.pages.len() as u64,
                placement_generation: generation,
                placement_scheme_digest: scheme,
            },
        )
    }

    #[test]
    fn pinned_python_producer_round_trips_through_current_safe_backend() {
        let graph = parse_python_named_ast(FIXTURE, 41).unwrap();
        let scheme = [0xA7; 32];
        let encoded = encode_ast_to_splane(&graph, &handles(&graph), 0, 7, scheme).unwrap();
        let root = temp_root("small");
        let (node_path, page_path, binding) = write_generation(&root, &encoded, 7, scheme);

        let admission =
            admit_data_serving_backend(&root, &node_path, &page_path, &binding, [0x55; 32])
                .unwrap();
        assert_eq!(
            admission.receipt().backend,
            DataServingBackendV1::ReadSeekSafeDefault
        );
        assert_eq!(
            admission.receipt().reason,
            BackendAdmissionReasonV1::CapabilityUnavailable
        );

        let mut reader =
            GenerationBoundGraphReader::open(&node_path, &page_path, binding.clone()).unwrap();
        let last = graph.nodes.last().unwrap().node_id;
        for root_id in [graph.root_id, 1, last] {
            for depth in 0..=3 {
                let observed = reader
                    .query_cone(
                        root_id,
                        depth,
                        graph.nodes.len() + 1,
                        Some(EDGE_KIND_AST_CHILD),
                    )
                    .unwrap();
                let (expected_nodes, expected_edges) =
                    direct_ast_cone(&graph, root_id, depth).unwrap();
                assert_eq!(observed.node_ids, expected_nodes);
                assert_eq!(observed.edges_traversed, expected_edges);
            }
        }

        for record in &encoded.records {
            let parsed = &graph.nodes[record.node_id as usize];
            assert_eq!(record.file_id, graph.file_id);
            assert_eq!(record.byte_start, parsed.byte_start);
            assert_eq!(record.byte_end, parsed.byte_end);
            assert_eq!(record.semantic_handle_digest, handles(&graph)[&record.node_id]);
        }
        remove_dir_all(root).unwrap();
    }

    #[test]
    fn large_real_ast_spans_current_generation_pages_and_stays_oracle_equivalent() {
        let source: String = (0..180).map(|i| format!("value_{i} = {i}\n")).collect();
        let graph = parse_python_named_ast(&source, 99).unwrap();
        let scheme = [0x5C; 32];
        let encoded = encode_ast_to_splane(&graph, &handles(&graph), 0, 12, scheme).unwrap();
        assert!(encoded.pages.len() > 1);
        let root = temp_root("multi");
        let (node_path, page_path, binding) = write_generation(&root, &encoded, 12, scheme);
        let admission =
            admit_data_serving_backend(&root, &node_path, &page_path, &binding, [0x66; 32])
                .unwrap();
        assert_eq!(admission.receipt().backend, DataServingBackendV1::ReadSeekSafeDefault);

        let mut reader =
            GenerationBoundGraphReader::open(&node_path, &page_path, binding.clone()).unwrap();
        for depth in 0..=3 {
            let observed = reader
                .query_cone(
                    graph.root_id,
                    depth,
                    graph.nodes.len() + 1,
                    Some(EDGE_KIND_AST_CHILD),
                )
                .unwrap();
            let (expected_nodes, expected_edges) =
                direct_ast_cone(&graph, graph.root_id, depth).unwrap();
            assert_eq!(observed.node_ids, expected_nodes);
            assert_eq!(observed.edges_traversed, expected_edges);
        }
        remove_dir_all(root).unwrap();
    }

    #[test]
    fn generation_metadata_tamper_cannot_change_parser_oracle_into_storage_success() {
        let graph = parse_python_named_ast(FIXTURE, 51).unwrap();
        let scheme = [0xC3; 32];
        let encoded = encode_ast_to_splane(&graph, &handles(&graph), 0, 21, scheme).unwrap();
        let root = temp_root("tamper");
        let (node_path, page_path, binding) = write_generation(&root, &encoded, 21, scheme);

        let mut file = OpenOptions::new().read(true).write(true).open(&page_path).unwrap();
        let mut first = encoded.pages[0].1;
        let mut decoded = PhysicalPageV1::decode(&first).unwrap();
        decoded.placement_generation = 22;
        first = decoded.encode().unwrap();
        file.seek(SeekFrom::Start(0)).unwrap();
        file.write_all(&first).unwrap();
        file.sync_all().unwrap();

        let mut reader =
            GenerationBoundGraphReader::open(&node_path, &page_path, binding.clone()).unwrap();
        assert_eq!(
            reader.query_cone(graph.root_id, 1, graph.nodes.len() + 1, Some(EDGE_KIND_AST_CHILD)),
            Err(GenerationStorageError::PlacementGenerationMismatch {
                expected: 21,
                observed: 22,
            })
        );
        let oracle = direct_ast_cone(&graph, graph.root_id, 1).unwrap();
        assert!(!oracle.0.is_empty());
        remove_dir_all(root).unwrap();
    }

    #[test]
    fn malformed_geometry_fails_at_current_backend_admission_before_query() {
        let graph = parse_python_named_ast(FIXTURE, 61).unwrap();
        let scheme = [0xD4; 32];
        let encoded = encode_ast_to_splane(&graph, &handles(&graph), 0, 31, scheme).unwrap();
        let root = temp_root("truncate");
        let (node_path, page_path, binding) = write_generation(&root, &encoded, 31, scheme);
        OpenOptions::new()
            .write(true)
            .open(&page_path)
            .unwrap()
            .set_len((binding.page_count * BLOCK_SIZE as u64) - 1)
            .unwrap();
        assert!(admit_data_serving_backend(
            &root,
            &node_path,
            &page_path,
            &binding,
            [0x77; 32]
        )
        .is_err());
        remove_dir_all(root).unwrap();
    }

    #[test]
    fn producer_still_fails_closed_on_parse_error_and_missing_higher_owner_handle() {
        assert_eq!(
            parse_python_named_ast("def broken(:\n", 1),
            Err(IngestError::ParseHasError)
        );
        let graph = parse_python_named_ast(FIXTURE, 71).unwrap();
        let mut supplied = handles(&graph);
        supplied.remove(&graph.root_id);
        assert_eq!(
            encode_ast_to_splane(&graph, &supplied, 0, 41, [0xE5; 32]),
            Err(IngestError::MissingSemanticHandle(graph.root_id))
        );
    }
}
