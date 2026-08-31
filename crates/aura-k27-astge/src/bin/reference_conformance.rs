use aura_k27_astge::{
    NodeIndexRecordV1, PageRow, PageSource, PhysicalPageV1, SPlaneGraphReader, StorageError,
    BLOCK_SIZE, MAX_EDGES, MAX_ROWS,
};
use std::collections::{HashMap, VecDeque};

const DEPTH: usize = 7;
const BRANCHING: usize = 3;
const MAX_NODES: usize = 10_000;
const ROOTS: &[u64] = &[0, 1, 2, 5, 40, 120, 121, 500, 1_000, 2_000, 3_279];
const QUERY_DEPTHS: &[usize] = &[0, 1, 2, 3];

#[derive(Clone)]
struct MemoryPages {
    pages: HashMap<u64, [u8; BLOCK_SIZE]>,
}

impl PageSource for MemoryPages {
    fn read_page(&mut self, pbn: u64) -> Result<[u8; BLOCK_SIZE], StorageError> {
        self.pages
            .get(&pbn)
            .copied()
            .ok_or_else(|| StorageError::Io(format!("missing fixture page {pbn}")))
    }
}

fn build_balanced_tree(depth: usize, branching: usize) -> Vec<Vec<u64>> {
    let mut adjacency = Vec::<Vec<u64>>::new();
    let mut queue = VecDeque::from([(0_u64, 0_usize)]);
    let mut next_id = 1_u64;

    while let Some((node_id, level)) = queue.pop_front() {
        while adjacency.len() <= node_id as usize {
            adjacency.push(Vec::new());
        }
        if level >= depth {
            continue;
        }
        for _ in 0..branching {
            let child = next_id;
            next_id += 1;
            adjacency[node_id as usize].push(child);
            queue.push_back((child, level + 1));
        }
    }

    while adjacency.len() < next_id as usize {
        adjacency.push(Vec::new());
    }
    adjacency
}

fn native_reader(
    adjacency: &[Vec<u64>],
) -> Result<SPlaneGraphReader<MemoryPages>, StorageError> {
    let mut records = Vec::<NodeIndexRecordV1>::with_capacity(adjacency.len());
    let mut pages = HashMap::<u64, [u8; BLOCK_SIZE]>::new();
    let placement_scheme_digest = [0x51_u8; 32];
    let semantic_handle_digest = [0xA7_u8; 32];
    let placement_generation = 1_u64;

    let mut node_index = 0_usize;
    let mut pbn = 0_u64;
    while node_index < adjacency.len() {
        let mut rows = Vec::<PageRow>::new();
        let mut targets = Vec::<u64>::new();
        let mut edge_kinds = Vec::<u8>::new();
        let mut assignments = Vec::<(u64, u16, u16)>::new();

        while node_index < adjacency.len() && rows.len() < MAX_ROWS {
            let node_targets = &adjacency[node_index];
            if !rows.is_empty() && targets.len() + node_targets.len() > MAX_EDGES {
                break;
            }
            if node_targets.len() > MAX_EDGES {
                return Err(StorageError::EdgeCapacityExceeded(node_targets.len()));
            }

            let row = rows.len() as u16;
            let first_edge = targets.len() as u16;
            let degree = node_targets.len() as u16;
            rows.push(PageRow { first_edge, degree });
            targets.extend(node_targets.iter().copied());
            edge_kinds.extend(std::iter::repeat_n(0_u8, node_targets.len()));
            assignments.push((node_index as u64, row, degree));
            node_index += 1;
        }

        let page = PhysicalPageV1 {
            pbn,
            placement_generation,
            placement_scheme_digest,
            rows,
            targets,
            edge_kinds,
        };
        pages.insert(pbn, page.encode()?);

        for (node_id, row, out_degree) in assignments {
            records.push(NodeIndexRecordV1 {
                node_id,
                semantic_handle_digest,
                pbn,
                row,
                out_degree,
                file_id: 0,
                byte_start: 0,
                byte_end: 0,
            });
        }
        pbn += 1;
    }

    SPlaneGraphReader::new(records, MemoryPages { pages })
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let adjacency = build_balanced_tree(DEPTH, BRANCHING);
    if adjacency.len() != 3_280 {
        return Err(format!("fixture node count drifted: {}", adjacency.len()).into());
    }
    let edge_count: usize = adjacency.iter().map(Vec::len).sum();
    if edge_count != 3_279 {
        return Err(format!("fixture edge count drifted: {edge_count}").into());
    }

    let mut reader = native_reader(&adjacency)?;
    for &root in ROOTS {
        for &depth in QUERY_DEPTHS {
            let cone = reader.query_cone(root, depth, MAX_NODES, None)?;
            let nodes = cone
                .node_ids
                .iter()
                .map(u64::to_string)
                .collect::<Vec<_>>()
                .join(",");
            println!("{root}\t{depth}\t{}\t{nodes}", cone.edges_traversed);
        }
    }
    Ok(())
}
