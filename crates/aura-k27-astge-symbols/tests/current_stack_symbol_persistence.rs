use aura_k27_astge::{
    BackendAdmissionReasonV1, DataServingBackendV1, GenerationBoundGraphReader,
    StorageGenerationBindingV1, admit_data_serving_backend, load_admitted_node_index,
};
use aura_k27_astge_ingest::{
    EDGE_KIND_AST_CHILD, ParsedAstGraphV1, direct_ast_cone, encode_ast_to_splane,
    parse_python_named_ast,
};
use aura_k27_astge_symbols::index_python_module_symbols;
use std::collections::HashMap;
use std::fs::{File, create_dir_all, remove_dir_all};
use std::io::Write;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

const FIXTURE: &str = include_str!("../fixtures/python_module_symbols.py");

fn temp_root(label: &str) -> PathBuf {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock after epoch")
        .as_nanos();
    let root = std::env::temp_dir().join(format!(
        "aura-k27-current-symbols-{label}-{}-{nonce}",
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

#[test]
fn module_symbols_survive_current_generation_and_safe_backend_without_reclassification() {
    let root = temp_root("persistence");
    let file_id = 91;
    let graph = parse_python_named_ast(FIXTURE, file_id).expect("parse fixture");
    let semantic_handles = handles(&graph);
    let symbols = index_python_module_symbols(FIXTURE, file_id, &semantic_handles)
        .expect("index module symbols");
    assert_eq!(symbols.duplicate_names, vec!["alpha"]);

    let placement_generation = 34;
    let placement_scheme_digest = [0xB7; 32];
    let encoded = encode_ast_to_splane(
        &graph,
        &semantic_handles,
        0,
        placement_generation,
        placement_scheme_digest,
    )
    .expect("encode AST into current storage ABI");
    assert!(!encoded.pages.is_empty());

    let binding = StorageGenerationBindingV1 {
        node_count: encoded.records.len() as u64,
        page_count: encoded.pages.len() as u64,
        placement_generation,
        placement_scheme_digest,
    };
    let node_path = root.join("node-index.bin");
    let page_path = root.join("pages.bin");

    let mut node_file = File::create(&node_path).expect("create node index");
    for record in &encoded.records {
        node_file
            .write_all(&record.encode())
            .expect("write node record");
    }
    node_file.sync_all().expect("sync node index");

    let mut page_file = File::create(&page_path).expect("create page file");
    for (expected_pbn, (pbn, page)) in encoded.pages.iter().enumerate() {
        assert_eq!(*pbn, expected_pbn as u64);
        page_file.write_all(page).expect("write page");
    }
    page_file.sync_all().expect("sync pages");

    let admission = admit_data_serving_backend(&root, &node_path, &page_path, &binding, [0xA4; 32])
        .expect("admit current backend");
    assert_eq!(
        admission.receipt().backend,
        DataServingBackendV1::ReadSeekSafeDefault
    );
    assert_eq!(
        admission.receipt().reason,
        BackendAdmissionReasonV1::CapabilityUnavailable
    );
    assert!(!admission.receipt().human_authority);
    assert!(!admission.receipt().external_effect);

    let admitted_index =
        load_admitted_node_index(&node_path, &binding).expect("admit current node index");
    for symbol in &symbols.symbols {
        let record = admitted_index
            .get(&symbol.node_id)
            .expect("symbol parent AST node must exist in admitted index");
        assert_eq!(record.file_id, symbol.file_id);
        assert_eq!(record.byte_start, symbol.byte_start);
        assert_eq!(record.byte_end, symbol.byte_end);
        assert_eq!(record.semantic_handle_digest, symbol.semantic_handle_digest);
    }

    let mut reader = GenerationBoundGraphReader::open(&node_path, &page_path, binding)
        .expect("open generation-bound reader");
    for symbol in &symbols.symbols {
        let observed = reader
            .query_cone(
                symbol.node_id,
                1,
                graph.nodes.len() + 1,
                Some(EDGE_KIND_AST_CHILD),
            )
            .expect("query symbol parent AST cone");
        let (expected_nodes, expected_edges) =
            direct_ast_cone(&graph, symbol.node_id, 1).expect("direct AST oracle");
        assert_eq!(observed.node_ids, expected_nodes);
        assert_eq!(observed.edges_traversed, expected_edges);
    }

    remove_dir_all(root).expect("remove temp root");
}
