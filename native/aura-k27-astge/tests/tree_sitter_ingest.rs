use aura_k27_astge::{
    parse_rust_source, publish_snapshot, SnapshotReader, AST_CHILD_EDGE_KIND,
};
use std::collections::{HashSet, VecDeque};
use std::fs;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};
use tree_sitter::{Node, Parser};

const SOURCE: &str = r#"
fn add(a: i32, b: i32) -> i32 {
    let sum = a + b;
    sum
}

fn main() {
    let value = add(1, 2);
    println!("{}", value);
}
"#;

#[derive(Debug, Clone, PartialEq, Eq)]
struct ExpectedNode {
    kind_id: u32,
    byte_start: u32,
    byte_end: u32,
    named: bool,
    children: Vec<u64>,
}

fn parse_tree(source: &str) -> tree_sitter::Tree {
    let language = tree_sitter_rust::LANGUAGE.into();
    let mut parser = Parser::new();
    parser.set_language(&language).unwrap();
    let tree = parser.parse(source.as_bytes(), None).unwrap();
    assert!(!tree.root_node().has_error());
    tree
}

fn collect_expected(node: Node<'_>, out: &mut Vec<ExpectedNode>) -> u64 {
    let node_id = out.len() as u64;
    out.push(ExpectedNode {
        kind_id: u32::from(node.kind_id()),
        byte_start: node.start_byte() as u32,
        byte_end: node.end_byte() as u32,
        named: node.is_named(),
        children: Vec::new(),
    });
    let mut children = Vec::with_capacity(node.child_count());
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        children.push(collect_expected(child, out));
    }
    out[node_id as usize].children = children;
    node_id
}

fn temp_root(label: &str) -> PathBuf {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    std::env::temp_dir().join(format!(
        "aura-k27-astge-{label}-{}-{nonce}",
        std::process::id()
    ))
}

fn memory_bfs(nodes: &[aura_k27_astge::NodeInput], root: u64, max_depth: usize) -> Vec<u64> {
    let mut seen = HashSet::new();
    let mut queue = VecDeque::new();
    let mut out = Vec::new();
    seen.insert(root);
    queue.push_back((root, 0usize));
    while let Some((node_id, depth)) = queue.pop_front() {
        out.push(node_id);
        if depth >= max_depth {
            continue;
        }
        for edge in &nodes[node_id as usize].edges {
            if edge.kind == AST_CHILD_EDGE_KIND && seen.insert(edge.target_node_id) {
                queue.push_back((edge.target_node_id, depth + 1));
            }
        }
    }
    out
}

#[test]
fn real_tree_sitter_ast_normalizes_to_exact_dense_preorder_graph() {
    let ingested = parse_rust_source(SOURCE, 41, "placement://astge/test-a").unwrap();
    assert_eq!(ingested.root_node_id, 0);
    assert_eq!(ingested.file_id, 41);
    assert_eq!(ingested.source_len, SOURCE.len() as u32);

    let tree = parse_tree(SOURCE);
    let mut expected = Vec::new();
    assert_eq!(collect_expected(tree.root_node(), &mut expected), 0);
    assert_eq!(ingested.nodes.len(), expected.len());

    for (node_id, (actual, expected)) in ingested.nodes.iter().zip(&expected).enumerate() {
        assert_eq!(actual.node_id, node_id as u64);
        assert_eq!(actual.type_id, expected.kind_id);
        assert_eq!(actual.file_id, 41);
        assert_eq!(actual.byte_start, expected.byte_start);
        assert_eq!(actual.byte_end, expected.byte_end);
        assert_eq!(actual.flags & 1 == 1, expected.named);
        let actual_children: Vec<_> = actual
            .edges
            .iter()
            .map(|edge| {
                assert_eq!(edge.kind, AST_CHILD_EDGE_KIND);
                edge.target_node_id
            })
            .collect();
        assert_eq!(actual_children, expected.children);
    }
}

#[test]
fn published_snapshot_cone_matches_independent_memory_bfs() {
    let ingested = parse_rust_source(SOURCE, 7, "placement://astge/cone").unwrap();
    let root = temp_root("cone");
    fs::create_dir_all(&root).unwrap();
    publish_snapshot(&root, 11, 29, &ingested.nodes).unwrap();
    let reader = SnapshotReader::open_current(&root).unwrap();
    let actual = reader
        .query_affected_cone(ingested.root_node_id, 2, None, Some(AST_CHILD_EDGE_KIND))
        .unwrap()
        .unwrap();
    let actual_ids: Vec<_> = actual.nodes.iter().map(|node| node.node_id).collect();
    assert_eq!(actual_ids, memory_bfs(&ingested.nodes, 0, 2));
    assert_eq!(actual.snapshot_generation, 11);
    assert_eq!(actual.coordinate_generation, 29);
    assert!(actual.nodes.iter().all(|node| node.file_id == 7));
    assert!(actual.edge_traversals > 0);
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn physical_placement_namespace_can_change_without_changing_ast_semantics() {
    let a = parse_rust_source(SOURCE, 9, "placement://astge/a").unwrap();
    let b = parse_rust_source(SOURCE, 9, "placement://astge/b").unwrap();
    assert_eq!(a.nodes.len(), b.nodes.len());
    assert!(a
        .nodes
        .iter()
        .zip(&b.nodes)
        .any(|(left, right)| left.placement_coord_packed != right.placement_coord_packed));
    for (left, right) in a.nodes.iter().zip(&b.nodes) {
        assert_eq!(left.node_id, right.node_id);
        assert_eq!(left.type_id, right.type_id);
        assert_eq!(left.file_id, right.file_id);
        assert_eq!(left.byte_start, right.byte_start);
        assert_eq!(left.byte_end, right.byte_end);
        assert_eq!(left.flags, right.flags);
        assert_eq!(left.edges, right.edges);
    }
}

#[test]
fn malformed_source_and_missing_placement_namespace_fail_closed() {
    let malformed = "fn broken( {";
    assert!(parse_rust_source(malformed, 1, "placement://astge/bad").is_err());
    assert!(parse_rust_source(SOURCE, 1, "   ").is_err());
}
