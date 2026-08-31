use aura_k27_astge::{
    NodeIndexRecordV1, PageRow, PageSource, PhysicalPageV1, SPlaneGraphReader, StorageError,
    BLOCK_SIZE,
};
use std::collections::HashMap;

const PBN: u64 = 7;
const PLACEMENT_GENERATION: u64 = 17;

struct MemoryPageSource {
    pages: HashMap<u64, [u8; BLOCK_SIZE]>,
}

impl PageSource for MemoryPageSource {
    fn read_page(&mut self, pbn: u64) -> Result<[u8; BLOCK_SIZE], StorageError> {
        self.pages
            .get(&pbn)
            .copied()
            .ok_or_else(|| StorageError::Io(format!("missing in-memory page {pbn}")))
    }
}

fn balanced_tree(depth: usize, branching: usize) -> Vec<Vec<u64>> {
    let mut adjacency = vec![Vec::new()];
    let mut queue = std::collections::VecDeque::from([(0usize, 0usize)]);
    let mut next_id = 1usize;
    while let Some((node, level)) = queue.pop_front() {
        if level >= depth {
            continue;
        }
        for _ in 0..branching {
            let child = next_id;
            next_id += 1;
            adjacency.push(Vec::new());
            adjacency[node].push(child as u64);
            queue.push_back((child, level + 1));
        }
    }
    adjacency
}

fn build_reader() -> Result<SPlaneGraphReader<MemoryPageSource>, StorageError> {
    let adjacency = balanced_tree(3, 2);
    let mut rows = Vec::with_capacity(adjacency.len());
    let mut targets = Vec::new();
    let mut kinds = Vec::new();
    let mut cursor = 0usize;

    for children in &adjacency {
        rows.push(PageRow {
            first_edge: cursor as u16,
            degree: children.len() as u16,
        });
        targets.extend(children.iter().copied());
        kinds.extend(std::iter::repeat_n(0u8, children.len()));
        cursor += children.len();
    }

    let page = PhysicalPageV1 {
        pbn: PBN,
        placement_generation: PLACEMENT_GENERATION,
        placement_scheme_digest: [0xA5; 32],
        rows,
        targets,
        edge_kinds: kinds,
    };
    let encoded = page.encode()?;
    let pages = MemoryPageSource {
        pages: HashMap::from([(PBN, encoded)]),
    };

    // Intentionally reverse physical record order. Correct lookup must be by node ID,
    // never by the record's vector position.
    let records = (0..adjacency.len())
        .rev()
        .map(|node_id| NodeIndexRecordV1 {
            node_id: node_id as u64,
            semantic_handle_digest: [node_id as u8; 32],
            pbn: PBN,
            row: node_id as u16,
            out_degree: adjacency[node_id].len() as u16,
            file_id: 0,
            byte_start: 0,
            byte_end: 0,
        })
        .collect::<Vec<_>>();

    SPlaneGraphReader::new(records, pages)
}

fn nodes_json(nodes: &[u64]) -> String {
    nodes
        .iter()
        .map(u64::to_string)
        .collect::<Vec<_>>()
        .join(",")
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    for depth in 0..=3usize {
        for root in [0u64, 1, 2, 6, 14] {
            let mut reader = build_reader()?;
            let cone = reader.query_cone(root, depth, 64, None)?;
            println!(
                "{{\"root\":{root},\"depth\":{depth},\"nodes\":[{}],\"edges\":{}}}",
                nodes_json(&cone.node_ids),
                cone.edges_traversed
            );
        }
    }

    let mut reader = build_reader()?;
    match reader.query_cone(99, 2, 64, None) {
        Err(StorageError::MissingRoot(99)) => println!("RUST_MISSING_ROOT=MissingRoot"),
        Err(other) => return Err(format!("unexpected missing-root error: {other:?}").into()),
        Ok(_) => return Err("missing root unexpectedly succeeded".into()),
    }

    let mut reader = build_reader()?;
    match reader.query_cone(0, 2, 0, None) {
        Err(StorageError::ConeBudgetExceeded { max_nodes: 0 }) => {
            println!("RUST_ZERO_BUDGET=ConeBudgetExceeded")
        }
        Err(other) => return Err(format!("unexpected zero-budget error: {other:?}").into()),
        Ok(_) => return Err("zero budget unexpectedly succeeded".into()),
    }

    Ok(())
}
