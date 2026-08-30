use crate::format::{
    get_u16, get_u32, get_u64, K27Coordinate, NodeRecord, BLOCK_SIZE, EDGE_DATA_OFFSET,
    EDGE_ENTRY_SIZE, EDGE_HEADER_SIZE, EDGE_MAGIC, MAX_EDGES_PER_BLOCK, MAX_ROWS_PER_BLOCK,
    NODE_RECORD_SIZE,
};
use crate::storage::{
    generation_dir_name, read_all, sha256_bytes, sha256_file, SnapshotManifest, CURRENT_FILE,
    CURRENT_SCHEMA, EDGES_FILE, MANIFEST_FILE, NODES_FILE,
};
use memmap2::{Mmap, MmapOptions};
use std::collections::{BTreeMap, HashSet, VecDeque};
use std::fs::File;
use std::io::{Error, ErrorKind, Result as IoResult};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HydratedCone {
    pub root_node_id: u64,
    pub nodes: Vec<NodeRecord>,
    pub edge_traversals: u64,
    pub unique_blocks_accessed: usize,
    pub snapshot_generation: u64,
    pub coordinate_generation: u64,
}

pub struct SnapshotReader {
    root: PathBuf,
    generation_dir: PathBuf,
    manifest: SnapshotManifest,
    nodes: Mmap,
    edges: Mmap,
}

impl SnapshotReader {
    /// Open the exact immutable generation named by `CURRENT`.
    ///
    /// The only unsafe operation is creating read-only mmaps after verifying the
    /// immutable generation manifest, file lengths, and SHA-256 digests. The
    /// writer never modifies a published generation in place.
    pub fn open_current(root: impl AsRef<Path>) -> IoResult<Self> {
        let root = root.as_ref().to_path_buf();
        let current = parse_current(&read_all(root.join(CURRENT_FILE))?)?;
        let generation_dir = root.join(&current.generation_dir);
        let manifest_bytes = read_all(generation_dir.join(MANIFEST_FILE))?;
        if sha256_bytes(&manifest_bytes) != current.manifest_sha256 {
            return Err(Error::new(ErrorKind::InvalidData, "CURRENT manifest digest mismatch"));
        }
        let manifest = SnapshotManifest::parse(&manifest_bytes)?;
        if current.generation_dir != generation_dir_name(manifest.generation) {
            return Err(Error::new(ErrorKind::InvalidData, "CURRENT generation directory mismatch"));
        }
        if manifest.node_count == 0 {
            return Err(Error::new(ErrorKind::InvalidData, "V0 snapshots require at least one node"));
        }
        if manifest.edge_block_count == 0 {
            return Err(Error::new(ErrorKind::InvalidData, "nonempty V0 snapshot has no edge block"));
        }

        let nodes_path = generation_dir.join(NODES_FILE);
        let edges_path = generation_dir.join(EDGES_FILE);
        verify_file(
            &nodes_path,
            manifest.node_count * NODE_RECORD_SIZE as u64,
            &manifest.nodes_sha256,
        )?;
        verify_file(
            &edges_path,
            manifest.edge_block_count * BLOCK_SIZE as u64,
            &manifest.edges_sha256,
        )?;

        let nodes_file = File::open(&nodes_path)?;
        let edges_file = File::open(&edges_path)?;
        // SAFETY: published generation files are immutable by this crate, opened
        // read-only, length/hash verified before mapping, and never reused for a
        // later generation. External mutation of published files violates the
        // storage-root contract and is outside this safe wrapper's authority.
        let nodes = unsafe { MmapOptions::new().map(&nodes_file)? };
        // SAFETY: same immutable-generation contract as the node map above.
        let edges = unsafe { MmapOptions::new().map(&edges_file)? };

        Ok(Self {
            root,
            generation_dir,
            manifest,
            nodes,
            edges,
        })
    }

    pub fn manifest(&self) -> &SnapshotManifest {
        &self.manifest
    }

    pub fn root(&self) -> &Path {
        &self.root
    }

    pub fn generation_dir(&self) -> &Path {
        &self.generation_dir
    }

    pub fn get_node(&self, node_id: u64) -> IoResult<Option<NodeRecord>> {
        if node_id >= self.manifest.node_count {
            return Ok(None);
        }
        let offset = node_id as usize * NODE_RECORD_SIZE;
        let record = NodeRecord::decode(&self.nodes[offset..offset + NODE_RECORD_SIZE])?;
        if record.node_id != node_id {
            return Err(Error::new(ErrorKind::InvalidData, "node id does not equal record position"));
        }
        if record.coordinate_generation != self.manifest.coordinate_generation {
            return Err(Error::new(ErrorKind::InvalidData, "node coordinate generation mismatch"));
        }
        if record.edge_block_pbn >= self.manifest.edge_block_count {
            return Err(Error::new(ErrorKind::InvalidData, "node edge block is out of range"));
        }
        Ok(Some(record))
    }

    pub fn edges_for_node(&self, node: NodeRecord) -> IoResult<Vec<(u64, u8)>> {
        let pbn = node.edge_block_pbn;
        if pbn >= self.manifest.edge_block_count {
            return Err(Error::new(ErrorKind::InvalidData, "edge block PBN is out of range"));
        }
        let page_offset = pbn as usize * BLOCK_SIZE;
        let page = &self.edges[page_offset..page_offset + BLOCK_SIZE];
        validate_edge_page_header(page, self.manifest.generation, pbn)?;

        let row_count = get_u16(page, 24) as usize;
        let edge_count = get_u16(page, 26) as usize;
        if row_count > MAX_ROWS_PER_BLOCK || edge_count > MAX_EDGES_PER_BLOCK {
            return Err(Error::new(ErrorKind::InvalidData, "edge block count exceeds V0 capacity"));
        }
        let row = node.edge_row_idx as usize;
        if row >= row_count {
            return Err(Error::new(ErrorKind::InvalidData, "edge row index is out of range"));
        }
        let start = get_u16(page, EDGE_HEADER_SIZE + row * 2) as usize;
        let end = get_u16(page, EDGE_HEADER_SIZE + (row + 1) * 2) as usize;
        if start > end || end > edge_count || end - start != node.out_degree as usize {
            return Err(Error::new(ErrorKind::InvalidData, "edge row offsets disagree with node degree"));
        }

        let mut out = Vec::with_capacity(end - start);
        for edge_index in start..end {
            let offset = EDGE_DATA_OFFSET + edge_index * EDGE_ENTRY_SIZE;
            let target = get_u64(page, offset);
            let kind = page[offset + 8];
            if target >= self.manifest.node_count {
                return Err(Error::new(ErrorKind::InvalidData, "edge target is outside node table"));
            }
            out.push((target, kind));
        }
        Ok(out)
    }

    pub fn query_affected_cone(
        &self,
        root_node_id: u64,
        max_depth: usize,
        prefix_filter: Option<(K27Coordinate, usize)>,
        edge_kind_filter: Option<u8>,
    ) -> IoResult<Option<HydratedCone>> {
        if self.get_node(root_node_id)?.is_none() {
            return Ok(None);
        }

        let mut visited = HashSet::<u64>::new();
        let mut blocks = HashSet::<u64>::new();
        let mut queue = VecDeque::<(u64, usize)>::new();
        let mut hydrated = Vec::<NodeRecord>::new();
        let mut edge_traversals = 0u64;
        visited.insert(root_node_id);
        queue.push_back((root_node_id, 0));

        while let Some((node_id, depth)) = queue.pop_front() {
            let node = self
                .get_node(node_id)?
                .ok_or_else(|| Error::new(ErrorKind::InvalidData, "queued node disappeared"))?;
            if let Some((expected, prefix_len)) = prefix_filter {
                let actual = K27Coordinate {
                    packed: node.placement_coord_packed,
                };
                if !actual.matches_prefix(expected, prefix_len) {
                    continue;
                }
            }
            hydrated.push(node);
            if depth >= max_depth || node.out_degree == 0 {
                continue;
            }

            blocks.insert(node.edge_block_pbn);
            for (target, kind) in self.edges_for_node(node)? {
                if edge_kind_filter.is_some_and(|required| kind != required) {
                    continue;
                }
                edge_traversals += 1;
                if visited.insert(target) {
                    queue.push_back((target, depth + 1));
                }
            }
        }

        Ok(Some(HydratedCone {
            root_node_id,
            nodes: hydrated,
            edge_traversals,
            unique_blocks_accessed: blocks.len(),
            snapshot_generation: self.manifest.generation,
            coordinate_generation: self.manifest.coordinate_generation,
        }))
    }
}

fn verify_file(path: &Path, expected_len: u64, expected_sha256: &str) -> IoResult<()> {
    let metadata = std::fs::metadata(path)?;
    if metadata.len() != expected_len {
        return Err(Error::new(ErrorKind::InvalidData, "snapshot file length mismatch"));
    }
    if sha256_file(path)? != expected_sha256 {
        return Err(Error::new(ErrorKind::InvalidData, "snapshot file digest mismatch"));
    }
    Ok(())
}

fn validate_edge_page_header(page: &[u8], generation: u64, pbn: u64) -> IoResult<()> {
    if page.len() != BLOCK_SIZE {
        return Err(Error::new(ErrorKind::InvalidData, "edge page size mismatch"));
    }
    if &page[..8] != EDGE_MAGIC {
        return Err(Error::new(ErrorKind::InvalidData, "edge page magic mismatch"));
    }
    if get_u64(page, 8) != generation {
        return Err(Error::new(ErrorKind::InvalidData, "edge page generation mismatch"));
    }
    if get_u64(page, 16) != pbn {
        return Err(Error::new(ErrorKind::InvalidData, "edge page PBN mismatch"));
    }
    if get_u32(page, 28) != 0 {
        return Err(Error::new(ErrorKind::InvalidData, "edge page reserved header is nonzero"));
    }
    Ok(())
}

struct CurrentPointer {
    generation_dir: String,
    manifest_sha256: String,
}

fn parse_current(bytes: &[u8]) -> IoResult<CurrentPointer> {
    let text = std::str::from_utf8(bytes)
        .map_err(|_| Error::new(ErrorKind::InvalidData, "CURRENT is not utf-8"))?;
    let mut fields = BTreeMap::<&str, &str>::new();
    for line in text.lines() {
        let (key, value) = line
            .split_once('=')
            .ok_or_else(|| Error::new(ErrorKind::InvalidData, "CURRENT line missing '='"))?;
        if fields.insert(key, value).is_some() {
            return Err(Error::new(ErrorKind::InvalidData, "duplicate CURRENT field"));
        }
    }
    if fields.remove("schema") != Some(CURRENT_SCHEMA) {
        return Err(Error::new(ErrorKind::InvalidData, "CURRENT schema mismatch"));
    }
    let generation_dir = fields
        .remove("generation_dir")
        .ok_or_else(|| Error::new(ErrorKind::InvalidData, "CURRENT generation_dir missing"))?;
    if generation_dir.len() != 24
        || !generation_dir.starts_with("gen-")
        || !generation_dir[4..].bytes().all(|b| b.is_ascii_digit())
    {
        return Err(Error::new(ErrorKind::InvalidData, "CURRENT generation_dir invalid"));
    }
    let manifest_sha256 = fields
        .remove("manifest_sha256")
        .ok_or_else(|| Error::new(ErrorKind::InvalidData, "CURRENT manifest digest missing"))?;
    if manifest_sha256.len() != 64
        || !manifest_sha256
            .bytes()
            .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
    {
        return Err(Error::new(ErrorKind::InvalidData, "CURRENT manifest digest invalid"));
    }
    if !fields.is_empty() {
        return Err(Error::new(ErrorKind::InvalidData, "unexpected CURRENT field"));
    }
    Ok(CurrentPointer {
        generation_dir: generation_dir.to_owned(),
        manifest_sha256: manifest_sha256.to_owned(),
    })
}
