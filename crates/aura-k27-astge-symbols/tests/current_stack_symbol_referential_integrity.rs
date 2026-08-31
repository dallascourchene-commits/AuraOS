use aura_k27_astge::{
    BackendAdmissionReasonV1, DataServingBackendV1, GenerationBoundGraphReader,
    StorageGenerationBindingV1, admit_data_serving_backend,
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

fn temp_root(label: &str) -> PathBuf {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock after epoch")
        .as_nanos();
    let root = std::env::temp_dir().join(format!(
        "aura-k27-symbol-current-{label}-{}-{nonce}",
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

fn source_fixture() -> String {
    let mut source = String::from(
        "@trace\ndef target(x):\n    return x + 1\n\nclass Box:\n    pass\n\ndef target(y):\n    return y * 2\n\nasync def runner():\n    return 1\n\n",
    );
    for index in 0..90 {
        source.push_str(&format!(
            "def helper_{index}(value):\n    return value + {index}\n\n"
        ));
    }
    source
}

#[test]
fn module_symbols_bind_exact_current_ast_records_and_consequences() {
    let root = temp_root("referential");
    let source = source_fixture();
    let file_id = 88;
    let graph = parse_python_named_ast(&source, file_id).expect("parse Python fixture");
    let semantic_handles = handles(&graph);
    let symbols = index_python_module_symbols(&source, file_id, &semantic_handles)
        .expect("index module symbols");

    assert_eq!(symbols.duplicate_names, vec!["target"]);
    let duplicate_targets: Vec<_> = symbols
        .symbols
        .iter()
        .filter(|symbol| symbol.name == "target")
        .collect();
    assert_eq!(duplicate_targets.len(), 2);
    assert_ne!(duplicate_targets[0].node_id, duplicate_targets[1].node_id);
    assert_ne!(duplicate_targets[0].byte_start, duplicate_targets[1].byte_start);

    let placement_generation = 31;
    let placement_scheme_digest = [0xA5; 32];
    let encoded = encode_ast_to_splane(
        &graph,
        &semantic_handles,
        0,
        placement_generation,
        placement_scheme_digest,
    )
    .expect("encode current S-plane graph");
    assert!(encoded.pages.len() > 1, "fixture must span multiple physical pages");

    // Representation-order substitution: the current S-plane reader indexes by storage-local
    // node ID. Symbol referential integrity must therefore survive a different record order.
    let mut persisted_records = encoded.records.clone();
    persisted_records.reverse();
    let records_by_id: HashMap<_, _> = persisted_records
        .iter()
        .map(|record| (record.node_id, record))
        .collect();

    for symbol in &symbols.symbols {
        let ast_node = graph
            .nodes
            .iter()
            .find(|node| node.node_id == symbol.node_id)
            .expect("symbol AST node exists");
        let record = records_by_id
            .get(&symbol.node_id)
            .expect("symbol physical record exists");
        assert_eq!(symbol.file_id, file_id);
        assert_eq!(symbol.byte_start, ast_node.byte_start);
        assert_eq!(symbol.byte_end, ast_node.byte_end);
        assert_eq!(record.file_id, symbol.file_id);
        assert_eq!(record.byte_start, symbol.byte_start);
        assert_eq!(record.byte_end, symbol.byte_end);
        assert_eq!(record.semantic_handle_digest, symbol.semantic_handle_digest);
        assert_eq!(symbol.semantic_handle_digest, semantic_handles[&symbol.node_id]);
    }

    let binding = StorageGenerationBindingV1 {
        node_count: persisted_records.len() as u64,
        page_count: encoded.pages.len() as u64,
        placement_generation,
        placement_scheme_digest,
    };
    let node_path = root.join("node-index.bin");
    let page_path = root.join("pages.bin");

    let mut node_file = File::create(&node_path).expect("create node index");
    for record in &persisted_records {
        node_file
            .write_all(&record.encode())
            .expect("write node record");
    }
    node_file.sync_all().expect("sync node index");

    let mut page_file = File::create(&page_path).expect("create pages");
    for (expected_pbn, (pbn, page)) in encoded.pages.iter().enumerate() {
        assert_eq!(*pbn, expected_pbn as u64);
        page_file.write_all(page).expect("write page");
    }
    page_file.sync_all().expect("sync pages");

    let admission = admit_data_serving_backend(
        &root,
        &node_path,
        &page_path,
        &binding,
        [0xD9; 32],
    )
    .expect("admit safe-default backend");
    assert_eq!(
        admission.receipt().backend,
        DataServingBackendV1::ReadSeekSafeDefault
    );
    assert_eq!(
        admission.receipt().reason,
        BackendAdmissionReasonV1::CapabilityUnavailable
    );

    let mut reader = GenerationBoundGraphReader::open(&node_path, &page_path, binding)
        .expect("open current generation");
    for symbol in &symbols.symbols {
        let observed = reader
            .query_cone(
                symbol.node_id,
                2,
                graph.nodes.len() + 1,
                Some(EDGE_KIND_AST_CHILD),
            )
            .expect("hydrate symbol AST consequence");
        let (expected_nodes, expected_edges) =
            direct_ast_cone(&graph, symbol.node_id, 2).expect("direct syntax oracle");
        assert_eq!(observed.node_ids, expected_nodes, "symbol {} node consequence", symbol.name);
        assert_eq!(
            observed.edges_traversed, expected_edges,
            "symbol {} edge consequence",
            symbol.name
        );
    }

    remove_dir_all(root).expect("remove temp root");
}
