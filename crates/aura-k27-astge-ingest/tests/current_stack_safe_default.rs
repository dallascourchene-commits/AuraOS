use aura_k27_astge::{
    admit_data_serving_backend, BackendAdmissionReasonV1, DataServingBackendV1,
    GenerationBoundGraphReader, StorageGenerationBindingV1,
};
use aura_k27_astge_ingest::{
    direct_ast_cone, encode_ast_to_splane, parse_python_named_ast, ParsedAstGraphV1,
    EDGE_KIND_AST_CHILD,
};
use std::collections::HashMap;
use std::fs::{create_dir_all, remove_dir_all, File};
use std::io::Write;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

fn temp_root(label: &str) -> PathBuf {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock after epoch")
        .as_nanos();
    let root = std::env::temp_dir().join(format!(
        "aura-k27-current-ingest-{label}-{}-{nonce}",
        std::process::id()
    ));
    create_dir_all(&root).expect("create temp root");
    root
}

fn fixture_handles(graph: &ParsedAstGraphV1) -> HashMap<u64, [u8; 32]> {
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
fn python_ast_reaches_current_generation_bound_readseek_safe_default() {
    let root = temp_root("safe-default");
    let source: String = (0..180)
        .map(|i| format!("value_{i} = ({i} + 1) * 2\n"))
        .collect();
    let graph = parse_python_named_ast(&source, 77).expect("parse Python fixture");
    let handles = fixture_handles(&graph);
    let placement_generation = 21;
    let placement_scheme_digest = [0xC3; 32];
    let encoded = encode_ast_to_splane(
        &graph,
        &handles,
        0,
        placement_generation,
        placement_scheme_digest,
    )
    .expect("encode AST into current S-plane bytes");
    assert!(encoded.pages.len() > 1, "fixture must exercise multiple physical pages");

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
            .expect("write node index record");
    }
    node_file.sync_all().expect("sync node index");

    let mut page_file = File::create(&page_path).expect("create page file");
    for (expected_pbn, (pbn, page)) in encoded.pages.iter().enumerate() {
        assert_eq!(*pbn, expected_pbn as u64, "current generation uses absolute zero-based PBNs");
        page_file.write_all(page).expect("write physical page");
    }
    page_file.sync_all().expect("sync page file");

    // Production has no source-owned backing-file immutability capability yet.
    // The consequence boundary must therefore route the real ingested generation to
    // the generation-bound Read+Seek backend rather than implicitly promoting mmap.
    let admission = admit_data_serving_backend(
        &root,
        &node_path,
        &page_path,
        &binding,
        [0xD4; 32],
    )
    .expect("admit data-serving backend");
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

    let mut reader = GenerationBoundGraphReader::open(&node_path, &page_path, binding)
        .expect("open generation-bound reader");
    let observed = reader
        .query_cone(
            graph.root_id,
            4,
            graph.nodes.len() + 1,
            Some(EDGE_KIND_AST_CHILD),
        )
        .expect("query current-stack AST cone");
    let (expected_nodes, expected_edges) =
        direct_ast_cone(&graph, graph.root_id, 4).expect("direct AST oracle");

    assert_eq!(observed.node_ids, expected_nodes);
    assert_eq!(observed.edges_traversed, expected_edges);
    assert!(observed.unique_pages > 1, "query must touch multiple S-plane pages");
    assert_eq!(encoded.node_count, graph.nodes.len());
    assert_eq!(encoded.edge_count, graph.edge_count());

    remove_dir_all(root).expect("remove temp root");
}
