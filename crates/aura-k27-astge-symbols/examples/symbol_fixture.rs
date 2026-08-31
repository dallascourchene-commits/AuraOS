use aura_k27_astge_ingest::parse_python_named_ast;
use aura_k27_astge_symbols::index_python_module_symbols;
use std::collections::HashMap;

fn main() {
    let source = include_str!("../fixtures/python_module_symbols.py");
    let file_id = 77_u32;
    let graph = parse_python_named_ast(source, file_id).expect("parent ingestion");
    let handles: HashMap<u64, [u8; 32]> = graph
        .nodes
        .iter()
        .map(|node| {
            let mut digest = [0_u8; 32];
            digest[0..8].copy_from_slice(&node.node_id.to_le_bytes());
            digest[8..12].copy_from_slice(&file_id.to_le_bytes());
            (node.node_id, digest)
        })
        .collect();
    let index = index_python_module_symbols(source, file_id, &handles).expect("symbol index");
    for symbol in &index.symbols {
        println!("{}|{}|{}", symbol.ordinal, symbol.kind.as_str(), symbol.name);
    }
    println!("DUP|{}", index.duplicate_names.join(","));
}
