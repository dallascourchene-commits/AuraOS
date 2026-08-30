use aura_k27_astge::{
    coordinate_for_sid, publish_snapshot, EdgeInput, NodeInput, SnapshotReader, BLOCK_SIZE,
    MAX_EDGES_PER_BLOCK, NODE_RECORD_SIZE,
};
use std::fs;
use std::io::ErrorKind;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

fn temp_root(label: &str) -> PathBuf {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let root = std::env::temp_dir().join(format!(
        "aura-k27-astge-{label}-{}-{nonce}",
        std::process::id()
    ));
    fs::create_dir(&root).unwrap();
    root
}

fn node(node_id: u64, sid: &str, start: u32, end: u32, edges: &[(u64, u8)]) -> NodeInput {
    NodeInput {
        node_id,
        placement_coord_packed: coordinate_for_sid(sid, 0).packed,
        type_id: 100 + node_id as u32,
        file_id: 7,
        byte_start: start,
        byte_end: end,
        flags: 0,
        edges: edges
            .iter()
            .map(|(target_node_id, kind)| EdgeInput {
                target_node_id: *target_node_id,
                kind: *kind,
            })
            .collect(),
    }
}

fn sample_nodes(root_end: u32) -> Vec<NodeInput> {
    vec![
        node(0, "src/lib.rs:0:root", 0, root_end, &[(1, 0), (2, 0)]),
        node(1, "src/lib.rs:1:left", 1, 10, &[(3, 1)]),
        node(2, "src/lib.rs:2:right", 11, 20, &[]),
        node(3, "src/lib.rs:3:leaf", 2, 5, &[]),
    ]
}

#[test]
fn binary_layout_constants_are_exact() {
    assert_eq!(64, NODE_RECORD_SIZE);
    assert_eq!(4096, BLOCK_SIZE);
    assert!(MAX_EDGES_PER_BLOCK >= 384);
}

#[test]
fn node_id_zero_round_trips_to_the_root_record() {
    let root = temp_root("root-roundtrip");
    let manifest = publish_snapshot(&root, 1, 7, &sample_nodes(21)).unwrap();
    assert_eq!(4, manifest.node_count);
    assert_eq!(1, manifest.edge_block_count);
    assert!(!manifest.k27_physical_ordering_proven);

    let reader = SnapshotReader::open_current(&root).unwrap();
    let root_node = reader.get_node(0).unwrap().unwrap();
    assert_eq!(0, root_node.node_id);
    assert_eq!(0, root_node.byte_start);
    assert_eq!(21, root_node.byte_end);
    assert_eq!(2, root_node.out_degree);
    assert_eq!(7, root_node.coordinate_generation);

    fs::remove_dir_all(root).unwrap();
}

#[test]
fn affected_cone_uses_exact_record_ids_and_edges() {
    let root = temp_root("cone");
    publish_snapshot(&root, 3, 11, &sample_nodes(21)).unwrap();
    let reader = SnapshotReader::open_current(&root).unwrap();
    let cone = reader
        .query_affected_cone(0, 3, None, None)
        .unwrap()
        .unwrap();
    let ids: Vec<u64> = cone.nodes.iter().map(|record| record.node_id).collect();
    assert_eq!(vec![0, 1, 2, 3], ids);
    assert_eq!(3, cone.edge_traversals);
    assert_eq!(1, cone.unique_blocks_accessed);
    assert_eq!(3, cone.snapshot_generation);
    assert_eq!(11, cone.coordinate_generation);

    let call_only = reader
        .query_affected_cone(0, 3, None, Some(1))
        .unwrap()
        .unwrap();
    assert_eq!(vec![0], call_only.nodes.iter().map(|n| n.node_id).collect::<Vec<_>>());

    fs::remove_dir_all(root).unwrap();
}

#[test]
fn existing_reader_stays_pinned_when_current_advances() {
    let root = temp_root("generation-pin");
    publish_snapshot(&root, 9, 40, &sample_nodes(21)).unwrap();
    let old_reader = SnapshotReader::open_current(&root).unwrap();
    assert_eq!(21, old_reader.get_node(0).unwrap().unwrap().byte_end);

    publish_snapshot(&root, 10, 41, &sample_nodes(33)).unwrap();
    assert_eq!(9, old_reader.manifest().generation);
    assert_eq!(40, old_reader.manifest().coordinate_generation);
    assert_eq!(21, old_reader.get_node(0).unwrap().unwrap().byte_end);

    let new_reader = SnapshotReader::open_current(&root).unwrap();
    assert_eq!(10, new_reader.manifest().generation);
    assert_eq!(41, new_reader.manifest().coordinate_generation);
    assert_eq!(33, new_reader.get_node(0).unwrap().unwrap().byte_end);
    assert_ne!(
        old_reader.generation_dir(),
        new_reader.generation_dir(),
        "published generations must never alias the same mutable mmap target"
    );

    fs::remove_dir_all(root).unwrap();
}

#[test]
fn coordinate_generation_is_bound_even_when_coordinate_value_is_unchanged() {
    let root = temp_root("coordinate-generation");
    let nodes = sample_nodes(21);
    let coord = nodes[0].placement_coord_packed;
    publish_snapshot(&root, 20, 100, &nodes).unwrap();
    let first = SnapshotReader::open_current(&root).unwrap();
    assert_eq!(coord, first.get_node(0).unwrap().unwrap().placement_coord_packed);

    publish_snapshot(&root, 21, 101, &nodes).unwrap();
    let second = SnapshotReader::open_current(&root).unwrap();
    assert_eq!(coord, second.get_node(0).unwrap().unwrap().placement_coord_packed);
    assert_ne!(
        first.manifest().coordinate_generation,
        second.manifest().coordinate_generation
    );

    fs::remove_dir_all(root).unwrap();
}

#[test]
fn nondense_node_ids_fail_closed_instead_of_corrupting_direct_lookup() {
    let root = temp_root("nondense");
    let nodes = vec![node(1, "bad", 0, 1, &[])];
    let err = publish_snapshot(&root, 1, 1, &nodes).unwrap_err();
    assert_eq!(ErrorKind::InvalidInput, err.kind());
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn oversized_single_row_fails_closed() {
    let root = temp_root("oversized-row");
    let mut edges = Vec::with_capacity(MAX_EDGES_PER_BLOCK + 1);
    for _ in 0..=MAX_EDGES_PER_BLOCK {
        edges.push((0, 0));
    }
    let nodes = vec![node(0, "root", 0, 1, &edges)];
    let err = publish_snapshot(&root, 1, 1, &nodes).unwrap_err();
    assert_eq!(ErrorKind::InvalidInput, err.kind());
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn duplicate_generation_is_never_overwritten() {
    let root = temp_root("generation-reuse");
    publish_snapshot(&root, 1, 1, &sample_nodes(21)).unwrap();
    let err = publish_snapshot(&root, 1, 2, &sample_nodes(99)).unwrap_err();
    assert_eq!(ErrorKind::AlreadyExists, err.kind());
    let reader = SnapshotReader::open_current(&root).unwrap();
    assert_eq!(21, reader.get_node(0).unwrap().unwrap().byte_end);
    fs::remove_dir_all(root).unwrap();
}
