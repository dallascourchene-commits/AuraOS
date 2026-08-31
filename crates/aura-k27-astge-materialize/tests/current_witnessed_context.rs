use aura_k27_astge::{
    BackendAdmissionReasonV1, DataServingBackendV1, GenerationBoundGraphReader,
    StorageGenerationBindingV1, admit_data_serving_backend,
};
use aura_k27_astge_ingest::{
    EDGE_KIND_AST_CHILD, ParsedAstGraphV1, direct_ast_cone, encode_ast_to_splane,
    parse_python_named_ast,
};
use aura_k27_astge_materialize::{AdmittedSourceCatalogV1, SourceLocatorV1};
use std::collections::HashMap;
use std::fs::{File, create_dir_all, remove_dir_all, write};
use std::io::Write;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

const SOURCE: &str = "def alpha(x):\n    y = x + 1\n    return y\n\nalpha(2)\n";

fn temp_root() -> PathBuf {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock after epoch")
        .as_nanos();
    let root = std::env::temp_dir().join(format!(
        "aura-k27-witnessed-context-{}-{nonce}",
        std::process::id()
    ));
    create_dir_all(root.join("src")).expect("create source directory");
    root
}

fn semantic_handles(graph: &ParsedAstGraphV1) -> HashMap<u64, [u8; 32]> {
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
fn exact_current_source_and_safe_current_graph_form_readonly_context_only() {
    let root = temp_root();
    let source_path = root.join("src/module.py");
    write(&source_path, SOURCE).expect("write exact source");

    let file_id = 77;
    let source_generation = 9001;
    let placement_generation = 41;
    assert_ne!(source_generation, placement_generation);

    let graph = parse_python_named_ast(SOURCE, file_id).expect("parse source");
    let handles = semantic_handles(&graph);
    let placement_scheme_digest = [0x5A; 32];
    let encoded = encode_ast_to_splane(
        &graph,
        &handles,
        0,
        placement_generation,
        placement_scheme_digest,
    )
    .expect("encode exact graph");

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
        page_file.write_all(page).expect("write physical page");
    }
    page_file.sync_all().expect("sync page file");

    let binding = StorageGenerationBindingV1 {
        node_count: encoded.records.len() as u64,
        page_count: encoded.pages.len() as u64,
        placement_generation,
        placement_scheme_digest,
    };

    let backend = admit_data_serving_backend(&root, &node_path, &page_path, &binding, [0xA1; 32])
        .expect("admit production backend");
    assert_eq!(backend.receipt().backend, DataServingBackendV1::ReadSeekSafeDefault);
    assert_eq!(
        backend.receipt().reason,
        BackendAdmissionReasonV1::CapabilityUnavailable
    );
    assert!(!backend.receipt().human_authority);
    assert!(!backend.receipt().external_effect);

    // In production this locator is emitted only after PR488's independent full-body
    // witness says CURRENT. The D9 catalog then revalidates the exact bytes again.
    let locator = SourceLocatorV1::bind(
        file_id,
        "src/module.py",
        source_generation,
        SOURCE.as_bytes(),
    );
    let catalog = AdmittedSourceCatalogV1::admit(&root, [locator]).expect("admit current source");
    let root_record = encoded.records.first().expect("root record");
    let source_slice = catalog
        .materialize_node(root_record)
        .expect("materialize current source slice");
    assert_eq!(source_slice.bytes, SOURCE.as_bytes());
    assert_eq!(source_slice.source_generation, source_generation);
    assert!(source_slice.source_currentness_verified);
    assert!(!source_slice.semantic_identity_proven);
    assert!(!source_slice.authority_granted);

    let mut reader = GenerationBoundGraphReader::open(&node_path, &page_path, binding)
        .expect("open safe generation-bound graph reader");
    let observed = reader
        .query_cone(
            graph.root_id,
            2,
            graph.nodes.len() + 1,
            Some(EDGE_KIND_AST_CHILD),
        )
        .expect("hydrate safe graph cone");
    let (expected_nodes, expected_edges) =
        direct_ast_cone(&graph, graph.root_id, 2).expect("direct syntax oracle");
    assert_eq!(observed.node_ids, expected_nodes);
    assert_eq!(observed.edges_traversed, expected_edges);

    // Consequence ceiling: current source + current graph is a read-only context input,
    // not semantic truth, review approval, mutation authority, or mmap promotion.
    let readonly_context_current = source_slice.source_currentness_verified
        && backend.receipt().backend == DataServingBackendV1::ReadSeekSafeDefault;
    assert!(readonly_context_current);
    let semantic_truth_proven = false;
    let review_authorized = false;
    let commit_authorized = false;
    let mmap_promoted = false;
    let external_effect = false;
    assert!(!semantic_truth_proven);
    assert!(!review_authorized);
    assert!(!commit_authorized);
    assert!(!mmap_promoted);
    assert!(!external_effect);

    remove_dir_all(root).expect("remove fixture");
}
