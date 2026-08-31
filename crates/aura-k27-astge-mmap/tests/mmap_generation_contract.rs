use aura_k27_astge::{NodeIndexRecordV1, PageRow, PhysicalPageV1, BLOCK_SIZE};
use aura_k27_astge_mmap::{publish_generation, MappedGenerationV1};
use std::fs;
use std::io::ErrorKind;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

fn temp_root(label: &str) -> PathBuf {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let path = std::env::temp_dir().join(format!(
        "aura-k27-astge-mmap-{label}-{}-{nonce}",
        std::process::id()
    ));
    fs::create_dir(&path).unwrap();
    path
}

fn digest(byte: u8) -> [u8; 32] {
    [byte; 32]
}

fn page(pbn: u64, placement_generation: u64, root_target: u64) -> PhysicalPageV1 {
    PhysicalPageV1 {
        pbn,
        placement_generation,
        placement_scheme_digest: digest(0xA0 + pbn as u8),
        rows: if pbn == 0 {
            vec![
                PageRow {
                    first_edge: 0,
                    degree: 1,
                },
                PageRow {
                    first_edge: 1,
                    degree: 0,
                },
            ]
        } else {
            vec![PageRow {
                first_edge: 0,
                degree: 0,
            }]
        },
        targets: if pbn == 0 { vec![root_target] } else { vec![] },
        edge_kinds: if pbn == 0 { vec![3] } else { vec![] },
    }
}

fn records(root_end: u32) -> Vec<NodeIndexRecordV1> {
    vec![
        NodeIndexRecordV1 {
            node_id: 20,
            semantic_handle_digest: digest(0x20),
            pbn: 0,
            row: 1,
            out_degree: 0,
            file_id: 7,
            byte_start: 10,
            byte_end: root_end,
        },
        NodeIndexRecordV1 {
            node_id: 10,
            semantic_handle_digest: digest(0x10),
            pbn: 0,
            row: 0,
            out_degree: 1,
            file_id: 7,
            byte_start: 0,
            byte_end: root_end,
        },
    ]
}

#[test]
fn parent_page_contract_remains_exact() {
    assert_eq!(4096, BLOCK_SIZE);
    assert_eq!(4096, page(0, 4, 20).encode().unwrap().len());
}

#[test]
fn publish_open_and_query_preserve_out_of_order_node_ids() {
    let root = temp_root("query");
    let manifest = publish_generation(&root, 1, 4, &records(30), &[page(0, 4, 20)]).unwrap();
    assert_eq!(1, manifest.storage_generation);
    assert_eq!(4, manifest.placement_generation);
    assert!(!manifest.k27_physical_locality_proven);
    assert!(!manifest.external_post_map_mutation_protected);

    let mapped = MappedGenerationV1::open_current(&root).unwrap();
    let mut graph = mapped.graph_reader().unwrap();
    let cone = graph.query_cone(10, 2, 8, Some(3)).unwrap();
    assert_eq!(vec![10, 20], cone.node_ids);
    assert_eq!(1, cone.unique_pages);
    assert_eq!(1, cone.edges_traversed);
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn mapped_reader_stays_on_old_generation_after_current_advances() {
    let root = temp_root("pinning");
    publish_generation(&root, 7, 70, &records(30), &[page(0, 70, 20)]).unwrap();
    let old = MappedGenerationV1::open_current(&root).unwrap();
    let old_dir = old.generation_dir().to_path_buf();
    assert_eq!(7, old.manifest().storage_generation);
    assert_eq!(30, old.records().unwrap()[1].byte_end);

    publish_generation(&root, 8, 80, &records(44), &[page(0, 80, 20)]).unwrap();
    assert_eq!(7, old.manifest().storage_generation);
    assert_eq!(70, old.manifest().placement_generation);
    assert_eq!(30, old.records().unwrap()[1].byte_end);

    let new = MappedGenerationV1::open_current(&root).unwrap();
    assert_eq!(8, new.manifest().storage_generation);
    assert_eq!(80, new.manifest().placement_generation);
    assert_eq!(44, new.records().unwrap()[1].byte_end);
    assert_ne!(old_dir, new.generation_dir());
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn duplicate_generation_cannot_replace_published_bytes() {
    let root = temp_root("immutable");
    publish_generation(&root, 2, 2, &records(30), &[page(0, 2, 20)]).unwrap();
    let error = publish_generation(&root, 2, 3, &records(99), &[page(0, 3, 20)]).unwrap_err();
    assert_eq!(ErrorKind::AlreadyExists, error.kind());
    let current = MappedGenerationV1::open_current(&root).unwrap();
    assert_eq!(2, current.manifest().storage_generation);
    assert_eq!(30, current.records().unwrap()[1].byte_end);
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn tampered_generation_is_rejected_before_mapping() {
    let root = temp_root("tamper");
    publish_generation(&root, 3, 3, &records(30), &[page(0, 3, 20)]).unwrap();
    let pages_path = root.join("gen-00000000000000000003/pages.bin");
    let mut bytes = fs::read(&pages_path).unwrap();
    bytes[100] ^= 0x5A;
    let mut permissions = fs::metadata(&pages_path).unwrap().permissions();
    permissions.set_readonly(false);
    fs::set_permissions(&pages_path, permissions).unwrap();
    fs::write(&pages_path, bytes).unwrap();
    let error = MappedGenerationV1::open_current(&root).err().unwrap();
    assert_eq!(ErrorKind::InvalidData, error.kind());
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn current_pointer_cannot_escape_generation_namespace() {
    let root = temp_root("pointer");
    publish_generation(&root, 4, 4, &records(30), &[page(0, 4, 20)]).unwrap();
    fs::write(
        root.join("CURRENT"),
        b"schema=AuraK27AstgeMmapCurrentV1\ngeneration_dir=../../outside\nmanifest_sha256=0000000000000000000000000000000000000000000000000000000000000000\n",
    )
    .unwrap();
    let error = MappedGenerationV1::open_current(&root).err().unwrap();
    assert_eq!(ErrorKind::InvalidData, error.kind());
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn placement_generation_mismatch_fails_before_publication() {
    let root = temp_root("placement");
    let error = publish_generation(&root, 5, 5, &records(30), &[page(0, 6, 20)]).unwrap_err();
    assert_eq!(ErrorKind::InvalidInput, error.kind());
    assert!(!root.join("CURRENT").exists());
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn empty_generation_fails_before_current_exists() {
    let root = temp_root("empty");
    let error = publish_generation(&root, 6, 6, &[], &[]).unwrap_err();
    assert_eq!(ErrorKind::InvalidInput, error.kind());
    assert!(!root.join("CURRENT").exists());
    fs::remove_dir_all(root).unwrap();
}
