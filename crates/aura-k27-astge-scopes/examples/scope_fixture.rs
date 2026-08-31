use aura_k27_astge_ingest::parse_python_named_ast;
use aura_k27_astge_scopes::index_python_nested_scopes;
use std::collections::HashMap;

const FIXTURE: &str = include_str!("../fixtures/python_nested_scopes.py");

fn main() {
    let file_id = 41u32;
    let graph = parse_python_named_ast(FIXTURE, file_id).expect("parent ingestion");
    let handles: HashMap<u64, [u8; 32]> = graph
        .nodes
        .iter()
        .map(|node| {
            let mut digest = [0u8; 32];
            digest[0..8].copy_from_slice(&node.node_id.to_le_bytes());
            digest[8..12].copy_from_slice(&file_id.to_le_bytes());
            (node.node_id, digest)
        })
        .collect();
    let index = index_python_nested_scopes(FIXTURE, file_id, &handles).expect("scope index");
    for scope in index.scopes {
        let parent = scope
            .parent_scope_id
            .map(|value| value.to_string())
            .unwrap_or_else(|| "-".to_owned());
        println!(
            "{}\t{}\t{}\t{}\t{}",
            scope.scope_id,
            parent,
            scope.kind.as_str(),
            scope.name,
            scope.line_start
        );
    }
}
