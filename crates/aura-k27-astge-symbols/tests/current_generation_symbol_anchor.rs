use aura_k27_astge::{
    BackendAdmissionReasonV1, DataServingBackendV1, GenerationBoundGraphReader,
    NODE_INDEX_RECORD_SIZE, NodeIndexRecordV1, StorageGenerationBindingV1,
    admit_data_serving_backend,
};
use aura_k27_astge_ingest::{
    EDGE_KIND_AST_CHILD, ParsedAstGraphV1, direct_ast_cone, encode_ast_to_splane,
    parse_python_named_ast,
};
use aura_k27_astge_symbols::index_python_module_symbols;
use std::collections::HashMap;
use std::fs::{File, create_dir_all, remove_dir_all};
use std::io::{Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

const FIXTURE: &str = include_str!("../fixtures/python_module_symbols.py");

fn temp_root() -> PathBuf {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    let root = std::env::temp_dir().join(format!(
        "aura-k27-astge-current-symbols-{}-{nonce}",
        std::process::id()
    ));
    create_dir_all(&root).expect("create temp root");
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
    graph: &ParsedAstGraphV1,
    supplied: &HashMap<u64, [u8; 32]>,
) -> (PathBuf, PathBuf, StorageGenerationBindingV1) {
    let generation = 17_u64;
    let scheme = [0x71; 32];
    let encoded = encode_ast_to_splane(graph, supplied, 0, generation, scheme)
        .expect("encode symbol-parent AST");
    let node_path = root.join("nodes.idx");
    let page_path = root.join("pages.bin");

    let mut nodes = File::create(&node_path).expect("create node file");
    for record in &encoded.records {
        nodes.write_all(&record.encode()).expect("write node record");
    }
    nodes.sync_all().expect("sync node file");

    let mut pages = File::create(&page_path).expect("create page file");
    for (expected, (pbn, page)) in encoded.pages.iter().enumerate() {
        assert_eq!(*pbn, expected as u64);
        pages.write_all(page).expect("write page");
    }
    pages.sync_all().expect("sync page file");

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

fn persisted_record(node_path: &Path, node_id: u64) -> NodeIndexRecordV1 {
    let mut file = File::open(node_path).expect("open node file");
    file.seek(SeekFrom::Start(
        node_id * NODE_INDEX_RECORD_SIZE as u64,
    ))
    .expect("seek node record");
    let mut raw = [0u8; NODE_INDEX_RECORD_SIZE];
    file.read_exact(&mut raw).expect("read node record");
    NodeIndexRecordV1::decode(&raw).expect("decode node record")
}

#[test]
fn cpython_validated_module_symbols_remain_exact_current_generation_ast_anchors() {
    let file_id = 83_u32;
    let graph = parse_python_named_ast(FIXTURE, file_id).expect("parse parent AST");
    let supplied = handles(&graph);
    let symbols =
        index_python_module_symbols(FIXTURE, file_id, &supplied).expect("module symbols");
    assert_eq!(symbols.duplicate_names, vec!["alpha"]);

    let root = temp_root();
    let (node_path, page_path, binding) = write_generation(&root, &graph, &supplied);
    let admission = admit_data_serving_backend(
        &root,
        &node_path,
        &page_path,
        &binding,
        [0x83; 32],
    )
    .expect("backend admission");
    assert_eq!(
        admission.receipt().backend,
        DataServingBackendV1::ReadSeekSafeDefault
    );
    assert_eq!(
        admission.receipt().reason,
        BackendAdmissionReasonV1::CapabilityUnavailable
    );

    let mut reader =
        GenerationBoundGraphReader::open(&node_path, &page_path, binding).expect("current reader");
    for symbol in &symbols.symbols {
        let persisted = persisted_record(&node_path, symbol.node_id);
        assert_eq!(persisted.node_id, symbol.node_id);
        assert_eq!(persisted.file_id, symbol.file_id);
        assert_eq!(persisted.byte_start, symbol.byte_start);
        assert_eq!(persisted.byte_end, symbol.byte_end);
        assert_eq!(persisted.semantic_handle_digest, symbol.semantic_handle_digest);

        let observed = reader
            .query_cone(
                symbol.node_id,
                1,
                graph.nodes.len() + 1,
                Some(EDGE_KIND_AST_CHILD),
            )
            .expect("hydrate symbol AST anchor");
        let (expected_nodes, expected_edges) =
            direct_ast_cone(&graph, symbol.node_id, 1).expect("direct AST anchor oracle");
        assert_eq!(observed.node_ids, expected_nodes);
        assert_eq!(observed.edges_traversed, expected_edges);
    }

    let alpha: Vec<_> = symbols
        .symbols
        .iter()
        .filter(|symbol| symbol.name == "alpha")
        .collect();
    assert_eq!(alpha.len(), 2);
    assert_ne!(alpha[0].node_id, alpha[1].node_id);
    assert_ne!(alpha[0].byte_start, alpha[1].byte_start);
    assert_eq!(symbols.duplicate_names, vec!["alpha"]);

    remove_dir_all(root).expect("cleanup");
}

#[test]
fn storage_does_not_resolve_duplicate_module_names_or_mint_new_semantic_handles() {
    let file_id = 97_u32;
    let graph = parse_python_named_ast(FIXTURE, file_id).expect("parse parent AST");
    let supplied = handles(&graph);
    let before = index_python_module_symbols(FIXTURE, file_id, &supplied).expect("module symbols");
    let root = temp_root();
    let (node_path, page_path, binding) = write_generation(&root, &graph, &supplied);
    let mut reader =
        GenerationBoundGraphReader::open(&node_path, &page_path, binding).expect("current reader");

    let alpha: Vec<_> = before
        .symbols
        .iter()
        .filter(|symbol| symbol.name == "alpha")
        .collect();
    assert_eq!(alpha.len(), 2);
    for symbol in alpha {
        let persisted = persisted_record(&node_path, symbol.node_id);
        assert_eq!(persisted.semantic_handle_digest, supplied[&symbol.node_id]);
        let cone = reader
            .query_cone(symbol.node_id, 0, 1, Some(EDGE_KIND_AST_CHILD))
            .expect("hydrate exact duplicate anchor");
        assert_eq!(cone.node_ids, vec![symbol.node_id]);
    }
    assert_eq!(before.duplicate_names, vec!["alpha"]);

    remove_dir_all(root).expect("cleanup");
}
