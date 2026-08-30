use crate::format::{
    put_u16, put_u32, put_u64, NodeRecord, BLOCK_SIZE, EDGE_DATA_OFFSET, EDGE_ENTRY_SIZE,
    EDGE_HEADER_SIZE, EDGE_MAGIC, MAX_EDGES_PER_BLOCK, MAX_ROWS_PER_BLOCK, NODE_RECORD_SIZE,
};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs::{self, File, OpenOptions};
use std::io::{Error, ErrorKind, Read, Result as IoResult, Write};
use std::path::{Path, PathBuf};

pub(crate) const MANIFEST_SCHEMA: &str = "AuraK27AstgeSnapshotV0";
pub(crate) const CURRENT_SCHEMA: &str = "AuraK27AstgeCurrentV0";
pub(crate) const NODES_FILE: &str = "nodes.bin";
pub(crate) const EDGES_FILE: &str = "edges.bin";
pub(crate) const MANIFEST_FILE: &str = "manifest.txt";
pub(crate) const CURRENT_FILE: &str = "CURRENT";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct EdgeInput {
    pub target_node_id: u64,
    pub kind: u8,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NodeInput {
    pub node_id: u64,
    pub placement_coord_packed: u64,
    pub type_id: u32,
    pub file_id: u32,
    pub byte_start: u32,
    pub byte_end: u32,
    pub flags: u32,
    pub edges: Vec<EdgeInput>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SnapshotManifest {
    pub generation: u64,
    pub coordinate_generation: u64,
    pub node_count: u64,
    pub edge_block_count: u64,
    pub nodes_sha256: String,
    pub edges_sha256: String,
    pub k27_physical_ordering_proven: bool,
}

impl SnapshotManifest {
    pub(crate) fn encode(&self) -> Vec<u8> {
        format!(
            "schema={MANIFEST_SCHEMA}\ngeneration={}\ncoordinate_generation={}\nnode_count={}\nedge_block_count={}\nnodes_sha256={}\nedges_sha256={}\nk27_physical_ordering_proven={}\n",
            self.generation,
            self.coordinate_generation,
            self.node_count,
            self.edge_block_count,
            self.nodes_sha256,
            self.edges_sha256,
            self.k27_physical_ordering_proven,
        )
        .into_bytes()
    }

    pub(crate) fn parse(bytes: &[u8]) -> IoResult<Self> {
        let text = std::str::from_utf8(bytes)
            .map_err(|_| Error::new(ErrorKind::InvalidData, "manifest is not utf-8"))?;
        let mut fields = BTreeMap::<&str, &str>::new();
        for line in text.lines() {
            let (key, value) = line
                .split_once('=')
                .ok_or_else(|| Error::new(ErrorKind::InvalidData, "manifest line missing '='"))?;
            if fields.insert(key, value).is_some() {
                return Err(Error::new(ErrorKind::InvalidData, "duplicate manifest field"));
            }
        }
        if fields.remove("schema") != Some(MANIFEST_SCHEMA) {
            return Err(Error::new(ErrorKind::InvalidData, "manifest schema mismatch"));
        }
        let generation = parse_u64_field(&mut fields, "generation")?;
        let coordinate_generation = parse_u64_field(&mut fields, "coordinate_generation")?;
        let node_count = parse_u64_field(&mut fields, "node_count")?;
        let edge_block_count = parse_u64_field(&mut fields, "edge_block_count")?;
        let nodes_sha256 = parse_digest_field(&mut fields, "nodes_sha256")?;
        let edges_sha256 = parse_digest_field(&mut fields, "edges_sha256")?;
        let k27_physical_ordering_proven = match fields.remove("k27_physical_ordering_proven") {
            Some("true") => true,
            Some("false") => false,
            _ => return Err(Error::new(ErrorKind::InvalidData, "invalid K27 ordering flag")),
        };
        if !fields.is_empty() {
            return Err(Error::new(ErrorKind::InvalidData, "unexpected manifest field"));
        }
        Ok(Self {
            generation,
            coordinate_generation,
            node_count,
            edge_block_count,
            nodes_sha256,
            edges_sha256,
            k27_physical_ordering_proven,
        })
    }
}

fn parse_u64_field(fields: &mut BTreeMap<&str, &str>, key: &str) -> IoResult<u64> {
    fields
        .remove(key)
        .ok_or_else(|| Error::new(ErrorKind::InvalidData, format!("missing {key}")))?
        .parse::<u64>()
        .map_err(|_| Error::new(ErrorKind::InvalidData, format!("invalid {key}")))
}

fn parse_digest_field(fields: &mut BTreeMap<&str, &str>, key: &str) -> IoResult<String> {
    let value = fields
        .remove(key)
        .ok_or_else(|| Error::new(ErrorKind::InvalidData, format!("missing {key}")))?;
    if value.len() != 64 || !value.bytes().all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase()) {
        return Err(Error::new(ErrorKind::InvalidData, format!("invalid {key}")));
    }
    Ok(value.to_owned())
}

struct EdgePageBuilder {
    generation: u64,
    pbn: u64,
    row_count: usize,
    edge_count: usize,
    bytes: [u8; BLOCK_SIZE],
}

impl EdgePageBuilder {
    fn new(generation: u64, pbn: u64) -> Self {
        let mut out = Self {
            generation,
            pbn,
            row_count: 0,
            edge_count: 0,
            bytes: [0u8; BLOCK_SIZE],
        };
        out.bytes[..8].copy_from_slice(EDGE_MAGIC);
        put_u64(&mut out.bytes, 8, generation);
        put_u64(&mut out.bytes, 16, pbn);
        out
    }

    fn can_fit(&self, degree: usize) -> bool {
        self.row_count < MAX_ROWS_PER_BLOCK && self.edge_count + degree <= MAX_EDGES_PER_BLOCK
    }

    fn add_row(&mut self, edges: &[EdgeInput]) -> IoResult<(u64, u16)> {
        if !self.can_fit(edges.len()) {
            return Err(Error::new(ErrorKind::InvalidInput, "edge row does not fit current block"));
        }
        let row = self.row_count;
        let start = self.edge_count;
        put_u16(&mut self.bytes, EDGE_HEADER_SIZE + row * 2, start as u16);

        for edge in edges {
            let offset = EDGE_DATA_OFFSET + self.edge_count * EDGE_ENTRY_SIZE;
            put_u64(&mut self.bytes, offset, edge.target_node_id);
            self.bytes[offset + 8] = edge.kind;
            self.edge_count += 1;
        }

        self.row_count += 1;
        put_u16(
            &mut self.bytes,
            EDGE_HEADER_SIZE + self.row_count * 2,
            self.edge_count as u16,
        );
        put_u16(&mut self.bytes, 24, self.row_count as u16);
        put_u16(&mut self.bytes, 26, self.edge_count as u16);
        put_u32(&mut self.bytes, 28, 0);
        Ok((self.pbn, row as u16))
    }

    fn finish(self) -> [u8; BLOCK_SIZE] {
        debug_assert_eq!(&self.bytes[..8], EDGE_MAGIC);
        debug_assert_eq!(self.generation, u64::from_le_bytes(self.bytes[8..16].try_into().unwrap()));
        self.bytes
    }
}

/// Publish one immutable full graph snapshot and atomically advance `CURRENT`.
///
/// V0 deliberately uses immutable generations instead of mutating mmap-backed
/// files in place. A crash before `CURRENT` rename leaves at most an orphan
/// generation; a reader never observes a partially written published generation.
pub fn publish_snapshot(
    root: impl AsRef<Path>,
    generation: u64,
    coordinate_generation: u64,
    nodes: &[NodeInput],
) -> IoResult<SnapshotManifest> {
    let root = root.as_ref();
    fs::create_dir_all(root)?;
    validate_inputs(nodes)?;

    let generation_name = generation_dir_name(generation);
    let final_dir = root.join(&generation_name);
    if final_dir.exists() {
        return Err(Error::new(ErrorKind::AlreadyExists, "snapshot generation already exists"));
    }
    let temp_dir = root.join(format!(
        ".{generation_name}.tmp-{}-{}",
        std::process::id(),
        unique_nonce()
    ));
    fs::create_dir(&temp_dir)?;

    let result = (|| -> IoResult<SnapshotManifest> {
        let mut records = Vec::<NodeRecord>::with_capacity(nodes.len());
        let mut pages = Vec::<[u8; BLOCK_SIZE]>::new();
        let mut page = EdgePageBuilder::new(generation, 0);

        for node in nodes {
            if !page.can_fit(node.edges.len()) && page.row_count > 0 {
                pages.push(page.finish());
                page = EdgePageBuilder::new(generation, pages.len() as u64);
            }
            let (pbn, row) = page.add_row(&node.edges)?;
            records.push(NodeRecord {
                node_id: node.node_id,
                placement_coord_packed: node.placement_coord_packed,
                coordinate_generation,
                type_id: node.type_id,
                file_id: node.file_id,
                byte_start: node.byte_start,
                byte_end: node.byte_end,
                edge_block_pbn: pbn,
                edge_row_idx: row,
                out_degree: node.edges.len() as u16,
                flags: node.flags,
            });
        }
        if page.row_count > 0 {
            pages.push(page.finish());
        }

        let nodes_path = temp_dir.join(NODES_FILE);
        let edges_path = temp_dir.join(EDGES_FILE);
        write_nodes(&nodes_path, &records)?;
        write_edges(&edges_path, &pages)?;

        let manifest = SnapshotManifest {
            generation,
            coordinate_generation,
            node_count: records.len() as u64,
            edge_block_count: pages.len() as u64,
            nodes_sha256: sha256_file(&nodes_path)?,
            edges_sha256: sha256_file(&edges_path)?,
            // V0 hashes coordinates but does not yet reorder physical blocks by K27.
            k27_physical_ordering_proven: false,
        };
        let manifest_bytes = manifest.encode();
        write_synced(&temp_dir.join(MANIFEST_FILE), &manifest_bytes)?;

        make_generation_files_read_only(&temp_dir)?;
        sync_dir(&temp_dir)?;
        fs::rename(&temp_dir, &final_dir)?;
        sync_dir(root)?;

        let current_bytes = format!(
            "schema={CURRENT_SCHEMA}\ngeneration_dir={generation_name}\nmanifest_sha256={}\n",
            sha256_bytes(&manifest_bytes)
        )
        .into_bytes();
        publish_current(root, &current_bytes)?;
        Ok(manifest)
    })();

    if result.is_err() && temp_dir.exists() {
        let _ = fs::remove_dir_all(&temp_dir);
    }
    result
}

fn validate_inputs(nodes: &[NodeInput]) -> IoResult<()> {
    for (index, node) in nodes.iter().enumerate() {
        if node.node_id != index as u64 {
            return Err(Error::new(
                ErrorKind::InvalidInput,
                "V0 node ids must be dense and equal to record order",
            ));
        }
        if node.byte_end < node.byte_start {
            return Err(Error::new(ErrorKind::InvalidInput, "node byte span is inverted"));
        }
        if node.edges.len() > MAX_EDGES_PER_BLOCK {
            return Err(Error::new(ErrorKind::InvalidInput, "single node degree exceeds V0 edge block capacity"));
        }
        for edge in &node.edges {
            if edge.target_node_id >= nodes.len() as u64 {
                return Err(Error::new(ErrorKind::InvalidInput, "edge target node id is out of range"));
            }
        }
    }
    Ok(())
}

fn write_nodes(path: &Path, records: &[NodeRecord]) -> IoResult<()> {
    let mut file = create_new(path)?;
    for record in records {
        file.write_all(&record.encode())?;
    }
    file.sync_all()?;
    let expected = records.len() as u64 * NODE_RECORD_SIZE as u64;
    if file.metadata()?.len() != expected {
        return Err(Error::new(ErrorKind::Other, "node table length mismatch after write"));
    }
    Ok(())
}

fn write_edges(path: &Path, pages: &[[u8; BLOCK_SIZE]]) -> IoResult<()> {
    let mut file = create_new(path)?;
    for page in pages {
        file.write_all(page)?;
    }
    file.sync_all()?;
    let expected = pages.len() as u64 * BLOCK_SIZE as u64;
    if file.metadata()?.len() != expected {
        return Err(Error::new(ErrorKind::Other, "edge table length mismatch after write"));
    }
    Ok(())
}

fn create_new(path: &Path) -> IoResult<File> {
    OpenOptions::new().write(true).create_new(true).open(path)
}

fn write_synced(path: &Path, bytes: &[u8]) -> IoResult<()> {
    let mut file = create_new(path)?;
    file.write_all(bytes)?;
    file.sync_all()
}

fn publish_current(root: &Path, bytes: &[u8]) -> IoResult<()> {
    let temp = root.join(format!(".{CURRENT_FILE}.tmp-{}-{}", std::process::id(), unique_nonce()));
    write_synced(&temp, bytes)?;
    fs::rename(&temp, root.join(CURRENT_FILE))?;
    sync_dir(root)
}

pub(crate) fn generation_dir_name(generation: u64) -> String {
    format!("gen-{generation:020}")
}

pub(crate) fn sha256_bytes(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    to_hex(&digest)
}

pub(crate) fn sha256_file(path: &Path) -> IoResult<String> {
    let mut file = File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = [0u8; 64 * 1024];
    loop {
        let count = file.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        hasher.update(&buffer[..count]);
    }
    Ok(to_hex(&hasher.finalize()))
}

fn to_hex(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0f) as usize] as char);
    }
    out
}

fn unique_nonce() -> u128 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos()
}

#[cfg(unix)]
fn make_generation_files_read_only(dir: &Path) -> IoResult<()> {
    use std::os::unix::fs::PermissionsExt;
    for name in [NODES_FILE, EDGES_FILE, MANIFEST_FILE] {
        let path = dir.join(name);
        let mut permissions = fs::metadata(&path)?.permissions();
        permissions.set_mode(0o444);
        fs::set_permissions(path, permissions)?;
    }
    Ok(())
}

#[cfg(not(unix))]
fn make_generation_files_read_only(_dir: &Path) -> IoResult<()> {
    Ok(())
}

#[cfg(unix)]
fn sync_dir(path: &Path) -> IoResult<()> {
    File::open(path)?.sync_all()
}

#[cfg(not(unix))]
fn sync_dir(_path: &Path) -> IoResult<()> {
    Ok(())
}

pub(crate) fn read_all(path: impl Into<PathBuf>) -> IoResult<Vec<u8>> {
    fs::read(path.into())
}
