use aura_k27_astge::{
    HydratedConeV1, NodeIndexRecordV1, PageRow, PhysicalPageV1, StorageGenerationBindingV1,
    BLOCK_SIZE, NODE_INDEX_RECORD_SIZE,
};
use memmap2::{Mmap, MmapOptions};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashMap, HashSet, VecDeque};
use std::error::Error;
use std::fmt::{Display, Formatter};
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

const MANIFEST_SCHEMA: &str = "AuraK27AstgeImmutableGenerationV1";
const CURRENT_SCHEMA: &str = "AuraK27AstgeCurrentV1";
const INDEX_FILE: &str = "node-index.bin";
const PAGE_FILE: &str = "pages.bin";
const MANIFEST_FILE: &str = "manifest.txt";
const CURRENT_FILE: &str = "CURRENT";

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MmapStorageError {
    Io(String),
    InvalidCurrent(&'static str),
    InvalidManifest(&'static str),
    ManifestDigestMismatch,
    FileLengthMismatch { file: &'static str, expected: u64, actual: u64 },
    FileDigestMismatch(&'static str),
    IndexRecordInvalid,
    DuplicateNodeId(u64),
    IndexPageOutOfRange { node_id: u64, pbn: u64, page_count: u64 },
    MissingRoot(u64),
    MissingTarget(u64),
    PageNumberMismatch { requested: u64, encoded: u64 },
    PlacementGenerationMismatch { expected: u64, observed: u64 },
    PlacementSchemeMismatch,
    InvalidRowIndex { node_id: u64, row: usize, row_count: usize },
    NodeDegreeMismatch { node_id: u64, index_degree: u16, page_degree: u16 },
    ConeBudgetExceeded { max_nodes: usize },
    PageDecode,
}

impl Display for MmapStorageError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}
impl Error for MmapStorageError {}
impl From<std::io::Error> for MmapStorageError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value.to_string())
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SnapshotManifestV1 {
    pub snapshot_generation: u64,
    pub binding: StorageGenerationBindingV1,
    pub index_sha256: String,
    pub pages_sha256: String,
    /// This adapter does not claim that any K27/hash scheme is physically locality-optimal.
    pub physical_locality_proven: bool,
}

impl SnapshotManifestV1 {
    fn encode(&self) -> Vec<u8> {
        format!(
            "schema={MANIFEST_SCHEMA}\nsnapshot_generation={}\nnode_count={}\npage_count={}\nplacement_generation={}\nplacement_scheme_digest={}\nindex_sha256={}\npages_sha256={}\nphysical_locality_proven={}\n",
            self.snapshot_generation,
            self.binding.node_count,
            self.binding.page_count,
            self.binding.placement_generation,
            hex(&self.binding.placement_scheme_digest),
            self.index_sha256,
            self.pages_sha256,
            self.physical_locality_proven,
        )
        .into_bytes()
    }

    fn parse(bytes: &[u8]) -> Result<Self, MmapStorageError> {
        let text = std::str::from_utf8(bytes).map_err(|_| MmapStorageError::InvalidManifest("utf8"))?;
        let mut fields = parse_fields(text).map_err(|_| MmapStorageError::InvalidManifest("field syntax"))?;
        if fields.remove("schema").as_deref() != Some(MANIFEST_SCHEMA) {
            return Err(MmapStorageError::InvalidManifest("schema"));
        }
        let snapshot_generation = take_u64(&mut fields, "snapshot_generation")?;
        let node_count = take_u64(&mut fields, "node_count")?;
        let page_count = take_u64(&mut fields, "page_count")?;
        let placement_generation = take_u64(&mut fields, "placement_generation")?;
        let placement_scheme_digest = take_digest32(&mut fields, "placement_scheme_digest")?;
        let index_sha256 = take_hash(&mut fields, "index_sha256")?;
        let pages_sha256 = take_hash(&mut fields, "pages_sha256")?;
        let physical_locality_proven = match fields.remove("physical_locality_proven").as_deref() {
            Some("true") => true,
            Some("false") => false,
            _ => return Err(MmapStorageError::InvalidManifest("locality flag")),
        };
        if !fields.is_empty() {
            return Err(MmapStorageError::InvalidManifest("unknown field"));
        }
        Ok(Self {
            snapshot_generation,
            binding: StorageGenerationBindingV1 {
                node_count,
                page_count,
                placement_generation,
                placement_scheme_digest,
            },
            index_sha256,
            pages_sha256,
            physical_locality_proven,
        })
    }
}

/// Publish already-encoded PR465 S-plane bytes as a new immutable generation.
///
/// This function does not define the graph ABI. It validates exact lengths from the supplied
/// PR465 generation binding, persists those bytes, fsyncs files/directories where supported,
/// then advances a small CURRENT pointer by rename. Crash-atomic durability remains a separate
/// proof plane; this function only establishes immutable-generation publication mechanics.
pub fn publish_generation(
    root: impl AsRef<Path>,
    snapshot_generation: u64,
    binding: StorageGenerationBindingV1,
    index_bytes: &[u8],
    page_bytes: &[u8],
) -> Result<SnapshotManifestV1, MmapStorageError> {
    let expected_index = checked_len(binding.node_count, NODE_INDEX_RECORD_SIZE)?;
    let expected_pages = checked_len(binding.page_count, BLOCK_SIZE)?;
    if index_bytes.len() as u64 != expected_index {
        return Err(MmapStorageError::FileLengthMismatch {
            file: INDEX_FILE,
            expected: expected_index,
            actual: index_bytes.len() as u64,
        });
    }
    if page_bytes.len() as u64 != expected_pages {
        return Err(MmapStorageError::FileLengthMismatch {
            file: PAGE_FILE,
            expected: expected_pages,
            actual: page_bytes.len() as u64,
        });
    }
    validate_index_bytes(index_bytes, &binding)?;
    validate_page_bytes(page_bytes, &binding)?;

    let root = root.as_ref();
    fs::create_dir_all(root)?;
    let generation_name = generation_dir_name(snapshot_generation);
    let final_dir = root.join(&generation_name);
    if final_dir.exists() {
        return Err(MmapStorageError::Io("snapshot generation already exists".into()));
    }
    let temp_dir = root.join(format!(".{generation_name}.tmp-{}", nonce()));
    fs::create_dir(&temp_dir)?;

    let result = (|| {
        write_new_synced(&temp_dir.join(INDEX_FILE), index_bytes)?;
        write_new_synced(&temp_dir.join(PAGE_FILE), page_bytes)?;
        let manifest = SnapshotManifestV1 {
            snapshot_generation,
            binding,
            index_sha256: sha256_bytes(index_bytes),
            pages_sha256: sha256_bytes(page_bytes),
            physical_locality_proven: false,
        };
        let manifest_bytes = manifest.encode();
        write_new_synced(&temp_dir.join(MANIFEST_FILE), &manifest_bytes)?;
        set_generation_read_only(&temp_dir)?;
        sync_dir(&temp_dir)?;
        fs::rename(&temp_dir, &final_dir)?;
        sync_dir(root)?;
        let current = format!(
            "schema={CURRENT_SCHEMA}\ngeneration_dir={generation_name}\nmanifest_sha256={}\n",
            sha256_bytes(&manifest_bytes)
        );
        publish_current(root, current.as_bytes())?;
        Ok(manifest)
    })();
    if result.is_err() && temp_dir.exists() {
        let _ = fs::remove_dir_all(&temp_dir);
    }
    result
}

pub struct ImmutableMmapReader {
    manifest: SnapshotManifestV1,
    index: HashMap<u64, NodeIndexRecordV1>,
    _index_mmap: Mmap,
    pages_mmap: Mmap,
}

impl ImmutableMmapReader {
    /// Opens the immutable generation selected by CURRENT.
    ///
    /// Unsafe mmap creation is isolated in this adapter crate. Before mapping, CURRENT,
    /// manifest digest, exact file lengths and SHA-256 file digests are verified. This crate
    /// never mutates a published generation. External truncation/mutation of a mapped file is
    /// outside the admitted lifecycle and therefore mmap safety under hostile mutation is NOT
    /// claimed by this API.
    pub fn open_current(root: impl AsRef<Path>) -> Result<Self, MmapStorageError> {
        let root = root.as_ref();
        let current_bytes = fs::read(root.join(CURRENT_FILE))?;
        let current = parse_current(&current_bytes)?;
        let generation_dir = root.join(&current.generation_dir);
        let manifest_bytes = fs::read(generation_dir.join(MANIFEST_FILE))?;
        if sha256_bytes(&manifest_bytes) != current.manifest_sha256 {
            return Err(MmapStorageError::ManifestDigestMismatch);
        }
        let manifest = SnapshotManifestV1::parse(&manifest_bytes)?;
        if current.generation_dir != generation_dir_name(manifest.snapshot_generation) {
            return Err(MmapStorageError::InvalidCurrent("generation directory"));
        }
        let index_path = generation_dir.join(INDEX_FILE);
        let pages_path = generation_dir.join(PAGE_FILE);
        verify_file(
            &index_path,
            checked_len(manifest.binding.node_count, NODE_INDEX_RECORD_SIZE)?,
            &manifest.index_sha256,
            INDEX_FILE,
        )?;
        verify_file(
            &pages_path,
            checked_len(manifest.binding.page_count, BLOCK_SIZE)?,
            &manifest.pages_sha256,
            PAGE_FILE,
        )?;

        let index_file = File::open(index_path)?;
        let pages_file = File::open(pages_path)?;
        // SAFETY: this adapter maps only a verified, published generation read-only. The
        // publication API never mutates/reuses that generation. Hostile external mutation or
        // truncation remains outside this API's admitted lifecycle and is not claimed safe.
        let index_mmap = unsafe { MmapOptions::new().map(&index_file)? };
        // SAFETY: same immutable-generation invariant as the index map above.
        let pages_mmap = unsafe { MmapOptions::new().map(&pages_file)? };
        let index = validate_index_bytes(&index_mmap, &manifest.binding)?;
        validate_page_bytes(&pages_mmap, &manifest.binding)?;
        Ok(Self {
            manifest,
            index,
            _index_mmap: index_mmap,
            pages_mmap,
        })
    }

    pub fn manifest(&self) -> &SnapshotManifestV1 {
        &self.manifest
    }

    pub fn query_cone(
        &self,
        root_id: u64,
        max_depth: usize,
        max_nodes: usize,
        edge_kind_filter: Option<u8>,
    ) -> Result<HydratedConeV1, MmapStorageError> {
        if max_nodes == 0 {
            return Err(MmapStorageError::ConeBudgetExceeded { max_nodes });
        }
        if !self.index.contains_key(&root_id) {
            return Err(MmapStorageError::MissingRoot(root_id));
        }
        let mut queue = VecDeque::from([(root_id, 0usize)]);
        let mut visited = HashSet::from([root_id]);
        let mut node_ids = Vec::new();
        let mut unique_pages = HashSet::new();
        let mut edges_traversed = 0usize;

        while let Some((node_id, depth)) = queue.pop_front() {
            if node_ids.len() >= max_nodes {
                return Err(MmapStorageError::ConeBudgetExceeded { max_nodes });
            }
            let record = self.index.get(&node_id).cloned().ok_or(MmapStorageError::MissingTarget(node_id))?;
            node_ids.push(node_id);
            if depth >= max_depth || record.out_degree == 0 {
                continue;
            }
            let page = self.decode_page(record.pbn)?;
            unique_pages.insert(record.pbn);
            let row_index = record.row as usize;
            if row_index >= page.rows.len() {
                return Err(MmapStorageError::InvalidRowIndex {
                    node_id,
                    row: row_index,
                    row_count: page.rows.len(),
                });
            }
            let row = page.rows[row_index];
            if row.degree != record.out_degree {
                return Err(MmapStorageError::NodeDegreeMismatch {
                    node_id,
                    index_degree: record.out_degree,
                    page_degree: row.degree,
                });
            }
            let start = row.first_edge as usize;
            let end = start + row.degree as usize;
            for edge_index in start..end {
                let kind = page.edge_kinds[edge_index];
                if edge_kind_filter.is_some_and(|wanted| kind != wanted) {
                    continue;
                }
                edges_traversed += 1;
                let target = page.targets[edge_index];
                if !self.index.contains_key(&target) {
                    return Err(MmapStorageError::MissingTarget(target));
                }
                if visited.insert(target) {
                    queue.push_back((target, depth + 1));
                }
            }
        }
        Ok(HydratedConeV1 {
            root_id,
            node_ids,
            unique_pages: unique_pages.len(),
            edges_traversed,
        })
    }

    fn decode_page(&self, pbn: u64) -> Result<PhysicalPageV1, MmapStorageError> {
        if pbn >= self.manifest.binding.page_count {
            return Err(MmapStorageError::IndexPageOutOfRange {
                node_id: 0,
                pbn,
                page_count: self.manifest.binding.page_count,
            });
        }
        let offset = pbn as usize * BLOCK_SIZE;
        let end = offset + BLOCK_SIZE;
        let raw: [u8; BLOCK_SIZE] = self.pages_mmap[offset..end].try_into().map_err(|_| MmapStorageError::PageDecode)?;
        let page = PhysicalPageV1::decode(&raw).map_err(|_| MmapStorageError::PageDecode)?;
        bind_page(&page, pbn, &self.manifest.binding)?;
        Ok(page)
    }
}

fn validate_index_bytes(
    bytes: &[u8],
    binding: &StorageGenerationBindingV1,
) -> Result<HashMap<u64, NodeIndexRecordV1>, MmapStorageError> {
    let expected = checked_len(binding.node_count, NODE_INDEX_RECORD_SIZE)?;
    if bytes.len() as u64 != expected {
        return Err(MmapStorageError::FileLengthMismatch {
            file: INDEX_FILE,
            expected,
            actual: bytes.len() as u64,
        });
    }
    let mut index = HashMap::with_capacity(binding.node_count as usize);
    for raw in bytes.chunks_exact(NODE_INDEX_RECORD_SIZE) {
        let record = NodeIndexRecordV1::decode(raw).map_err(|_| MmapStorageError::IndexRecordInvalid)?;
        if record.pbn >= binding.page_count {
            return Err(MmapStorageError::IndexPageOutOfRange {
                node_id: record.node_id,
                pbn: record.pbn,
                page_count: binding.page_count,
            });
        }
        let node_id = record.node_id;
        if index.insert(node_id, record).is_some() {
            return Err(MmapStorageError::DuplicateNodeId(node_id));
        }
    }
    Ok(index)
}

fn validate_page_bytes(bytes: &[u8], binding: &StorageGenerationBindingV1) -> Result<(), MmapStorageError> {
    let expected = checked_len(binding.page_count, BLOCK_SIZE)?;
    if bytes.len() as u64 != expected {
        return Err(MmapStorageError::FileLengthMismatch {
            file: PAGE_FILE,
            expected,
            actual: bytes.len() as u64,
        });
    }
    for (pbn, chunk) in bytes.chunks_exact(BLOCK_SIZE).enumerate() {
        let raw: [u8; BLOCK_SIZE] = chunk.try_into().map_err(|_| MmapStorageError::PageDecode)?;
        let page = PhysicalPageV1::decode(&raw).map_err(|_| MmapStorageError::PageDecode)?;
        bind_page(&page, pbn as u64, binding)?;
    }
    Ok(())
}

fn bind_page(page: &PhysicalPageV1, requested: u64, binding: &StorageGenerationBindingV1) -> Result<(), MmapStorageError> {
    if page.pbn != requested {
        return Err(MmapStorageError::PageNumberMismatch { requested, encoded: page.pbn });
    }
    if page.placement_generation != binding.placement_generation {
        return Err(MmapStorageError::PlacementGenerationMismatch {
            expected: binding.placement_generation,
            observed: page.placement_generation,
        });
    }
    if page.placement_scheme_digest != binding.placement_scheme_digest {
        return Err(MmapStorageError::PlacementSchemeMismatch);
    }
    Ok(())
}

struct CurrentPointer {
    generation_dir: String,
    manifest_sha256: String,
}

fn parse_current(bytes: &[u8]) -> Result<CurrentPointer, MmapStorageError> {
    let text = std::str::from_utf8(bytes).map_err(|_| MmapStorageError::InvalidCurrent("utf8"))?;
    let mut fields = parse_fields(text).map_err(|_| MmapStorageError::InvalidCurrent("field syntax"))?;
    if fields.remove("schema").as_deref() != Some(CURRENT_SCHEMA) {
        return Err(MmapStorageError::InvalidCurrent("schema"));
    }
    let generation_dir = fields.remove("generation_dir").ok_or(MmapStorageError::InvalidCurrent("generation_dir"))?;
    if generation_dir.len() != 24 || !generation_dir.starts_with("gen-") || !generation_dir[4..].bytes().all(|b| b.is_ascii_digit()) {
        return Err(MmapStorageError::InvalidCurrent("generation_dir shape"));
    }
    let manifest_sha256 = fields.remove("manifest_sha256").ok_or(MmapStorageError::InvalidCurrent("manifest digest"))?;
    if !valid_hash(&manifest_sha256) || !fields.is_empty() {
        return Err(MmapStorageError::InvalidCurrent("manifest digest/fields"));
    }
    Ok(CurrentPointer { generation_dir, manifest_sha256 })
}

fn parse_fields(text: &str) -> Result<BTreeMap<String, String>, ()> {
    let mut out = BTreeMap::new();
    for line in text.lines() {
        let (key, value) = line.split_once('=').ok_or(())?;
        if key.is_empty() || value.is_empty() || out.insert(key.to_owned(), value.to_owned()).is_some() {
            return Err(());
        }
    }
    Ok(out)
}

fn take_u64(fields: &mut BTreeMap<String, String>, key: &'static str) -> Result<u64, MmapStorageError> {
    fields.remove(key).ok_or(MmapStorageError::InvalidManifest(key))?.parse().map_err(|_| MmapStorageError::InvalidManifest(key))
}
fn take_hash(fields: &mut BTreeMap<String, String>, key: &'static str) -> Result<String, MmapStorageError> {
    let value = fields.remove(key).ok_or(MmapStorageError::InvalidManifest(key))?;
    if !valid_hash(&value) { return Err(MmapStorageError::InvalidManifest(key)); }
    Ok(value)
}
fn take_digest32(fields: &mut BTreeMap<String, String>, key: &'static str) -> Result<[u8; 32], MmapStorageError> {
    let value = take_hash(fields, key)?;
    let mut out = [0u8; 32];
    for (i, byte) in out.iter_mut().enumerate() {
        *byte = u8::from_str_radix(&value[i * 2..i * 2 + 2], 16).map_err(|_| MmapStorageError::InvalidManifest(key))?;
    }
    Ok(out)
}
fn valid_hash(value: &str) -> bool {
    value.len() == 64 && value.bytes().all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
}
fn checked_len(count: u64, width: usize) -> Result<u64, MmapStorageError> {
    count.checked_mul(width as u64).ok_or_else(|| MmapStorageError::Io("length overflow".into()))
}
fn sha256_bytes(bytes: &[u8]) -> String { hex(&Sha256::digest(bytes)) }
fn sha256_file(path: &Path) -> Result<String, MmapStorageError> {
    let mut file = File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buf = [0u8; 64 * 1024];
    loop {
        let count = file.read(&mut buf)?;
        if count == 0 { break; }
        hasher.update(&buf[..count]);
    }
    Ok(hex(&hasher.finalize()))
}
fn hex(bytes: &[u8]) -> String {
    const H: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes { out.push(H[(byte >> 4) as usize] as char); out.push(H[(byte & 0xf) as usize] as char); }
    out
}
fn verify_file(path: &Path, expected: u64, digest: &str, name: &'static str) -> Result<(), MmapStorageError> {
    let meta = fs::metadata(path)?;
    if !meta.is_file() { return Err(MmapStorageError::Io(format!("{name} is not a regular file"))); }
    if meta.len() != expected { return Err(MmapStorageError::FileLengthMismatch { file: name, expected, actual: meta.len() }); }
    if sha256_file(path)? != digest { return Err(MmapStorageError::FileDigestMismatch(name)); }
    Ok(())
}
fn generation_dir_name(generation: u64) -> String { format!("gen-{generation:020}") }
fn nonce() -> u128 { std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_nanos() }
fn write_new_synced(path: &Path, bytes: &[u8]) -> Result<(), MmapStorageError> {
    let mut file = OpenOptions::new().write(true).create_new(true).open(path)?;
    file.write_all(bytes)?;
    file.sync_all()?;
    Ok(())
}
fn publish_current(root: &Path, bytes: &[u8]) -> Result<(), MmapStorageError> {
    let temp = root.join(format!(".{CURRENT_FILE}.tmp-{}", nonce()));
    write_new_synced(&temp, bytes)?;
    fs::rename(&temp, root.join(CURRENT_FILE))?;
    sync_dir(root)
}
#[cfg(unix)]
fn set_generation_read_only(dir: &Path) -> Result<(), MmapStorageError> {
    use std::os::unix::fs::PermissionsExt;
    for name in [INDEX_FILE, PAGE_FILE, MANIFEST_FILE] {
        let path = dir.join(name);
        let mut permissions = fs::metadata(&path)?.permissions();
        permissions.set_mode(0o444);
        fs::set_permissions(path, permissions)?;
    }
    Ok(())
}
#[cfg(not(unix))]
fn set_generation_read_only(_dir: &Path) -> Result<(), MmapStorageError> { Ok(()) }
#[cfg(unix)]
fn sync_dir(path: &Path) -> Result<(), MmapStorageError> { File::open(path)?.sync_all()?; Ok(()) }
#[cfg(not(unix))]
fn sync_dir(_path: &Path) -> Result<(), MmapStorageError> { Ok(()) }

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge::GenerationBoundGraphReader;
    use std::fs::remove_dir_all;
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(0);
    fn d(byte: u8) -> [u8; 32] { [byte; 32] }
    fn temp_root(label: &str) -> PathBuf {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        std::env::temp_dir().join(format!("aura-k27-mmap-{label}-{}-{n}", std::process::id()))
    }
    fn node(id: u64, pbn: u64, row: u16, degree: u16) -> NodeIndexRecordV1 {
        NodeIndexRecordV1 { node_id: id, semantic_handle_digest: d(id as u8 + 1), pbn, row, out_degree: degree, file_id: 1, byte_start: id as u32 * 10, byte_end: id as u32 * 10 + 5 }
    }
    fn page(pbn: u64, gen: u64, scheme: u8, rows: Vec<PageRow>, targets: Vec<u64>, kinds: Vec<u8>) -> [u8; BLOCK_SIZE] {
        PhysicalPageV1 { pbn, placement_generation: gen, placement_scheme_digest: d(scheme), rows, targets, edge_kinds: kinds }.encode().unwrap()
    }
    fn fixture() -> (StorageGenerationBindingV1, Vec<NodeIndexRecordV1>, Vec<[u8; BLOCK_SIZE]>) {
        let binding = StorageGenerationBindingV1 { node_count: 4, page_count: 2, placement_generation: 11, placement_scheme_digest: d(0x5A) };
        let records = vec![node(2, 1, 0, 1), node(0, 0, 0, 2), node(3, 1, 1, 0), node(1, 0, 1, 0)];
        let pages = vec![
            page(0, 11, 0x5A, vec![PageRow { first_edge: 0, degree: 2 }, PageRow { first_edge: 2, degree: 0 }], vec![1, 2], vec![0, 0]),
            page(1, 11, 0x5A, vec![PageRow { first_edge: 0, degree: 1 }, PageRow { first_edge: 1, degree: 0 }], vec![3], vec![0]),
        ];
        (binding, records, pages)
    }
    fn bytes(records: &[NodeIndexRecordV1], pages: &[[u8; BLOCK_SIZE]]) -> (Vec<u8>, Vec<u8>) {
        let mut index = Vec::new();
        for record in records { index.extend_from_slice(&record.encode()); }
        let mut page_bytes = Vec::new();
        for page in pages { page_bytes.extend_from_slice(page); }
        (index, page_bytes)
    }

    #[test]
    fn publication_mmap_and_readseek_are_query_equivalent() {
        let root = temp_root("equivalence");
        let (binding, records, pages) = fixture();
        let (index_bytes, page_bytes) = bytes(&records, &pages);
        publish_generation(&root, 3, binding.clone(), &index_bytes, &page_bytes).unwrap();
        let mut mmap = ImmutableMmapReader::open_current(&root).unwrap();

        let read_index = root.join(generation_dir_name(3)).join(INDEX_FILE);
        let read_pages = root.join(generation_dir_name(3)).join(PAGE_FILE);
        let mut seek = GenerationBoundGraphReader::open(read_index, read_pages, binding).unwrap();
        for (root_id, depth, kind) in [(0, 3, None), (0, 1, Some(0)), (2, 2, None), (3, 3, None)] {
            let a = seek.query_cone(root_id, depth, 16, kind).unwrap();
            let b = mmap.query_cone(root_id, depth, 16, kind).unwrap();
            assert_eq!(a, b);
        }
        assert!(!mmap.manifest().physical_locality_proven);
        let _ = remove_dir_all(root);
    }

    #[test]
    fn successor_publication_does_not_retarget_already_open_reader() {
        let root = temp_root("pin");
        let (binding, records, pages) = fixture();
        let (index_bytes, page_bytes) = bytes(&records, &pages);
        publish_generation(&root, 4, binding.clone(), &index_bytes, &page_bytes).unwrap();
        let old = ImmutableMmapReader::open_current(&root).unwrap();
        publish_generation(&root, 5, binding, &index_bytes, &page_bytes).unwrap();
        let new = ImmutableMmapReader::open_current(&root).unwrap();
        assert_eq!(old.manifest().snapshot_generation, 4);
        assert_eq!(new.manifest().snapshot_generation, 5);
        assert_eq!(old.query_cone(0, 3, 16, None).unwrap(), new.query_cone(0, 3, 16, None).unwrap());
        let _ = remove_dir_all(root);
    }

    #[test]
    fn page_or_index_tamper_after_publication_is_rejected_on_new_open() {
        let root = temp_root("tamper");
        let (binding, records, pages) = fixture();
        let (index_bytes, page_bytes) = bytes(&records, &pages);
        publish_generation(&root, 6, binding, &index_bytes, &page_bytes).unwrap();
        let path = root.join(generation_dir_name(6)).join(PAGE_FILE);
        let mut permissions = fs::metadata(&path).unwrap().permissions();
        permissions.set_readonly(false);
        fs::set_permissions(&path, permissions).unwrap();
        let mut mutated = fs::read(&path).unwrap();
        mutated[100] ^= 1;
        fs::write(&path, mutated).unwrap();
        assert_eq!(ImmutableMmapReader::open_current(&root).err(), Some(MmapStorageError::FileDigestMismatch(PAGE_FILE)));
        let _ = remove_dir_all(root);
    }

    #[test]
    fn current_manifest_digest_substitution_fails_closed() {
        let root = temp_root("current-digest");
        let (binding, records, pages) = fixture();
        let (index_bytes, page_bytes) = bytes(&records, &pages);
        publish_generation(&root, 7, binding, &index_bytes, &page_bytes).unwrap();
        let current_path = root.join(CURRENT_FILE);
        let current = fs::read_to_string(&current_path).unwrap().replace("manifest_sha256=", "manifest_sha256=0");
        fs::write(&current_path, current).unwrap();
        assert!(matches!(ImmutableMmapReader::open_current(&root), Err(MmapStorageError::InvalidCurrent(_)) | Err(MmapStorageError::ManifestDigestMismatch)));
        let _ = remove_dir_all(root);
    }

    #[test]
    fn publication_rejects_generation_incoherent_page_bytes() {
        let root = temp_root("bad-generation");
        let (binding, records, mut pages) = fixture();
        pages[1] = page(1, 12, 0x5A, vec![PageRow { first_edge: 0, degree: 1 }, PageRow { first_edge: 1, degree: 0 }], vec![3], vec![0]);
        let (index_bytes, page_bytes) = bytes(&records, &pages);
        assert_eq!(publish_generation(&root, 8, binding, &index_bytes, &page_bytes).err(), Some(MmapStorageError::PlacementGenerationMismatch { expected: 11, observed: 12 }));
        let _ = remove_dir_all(root);
    }
}
