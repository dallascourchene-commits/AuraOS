//! Optional immutable-generation mmap boundary for `aura-k27-astge`.
//!
//! The parent S-plane crate remains `#![forbid(unsafe_code)]` and owns the byte
//! contract plus bounded graph semantics. This sibling isolates the one unsafe
//! OS mapping boundary and adds generation publication. It does not grant K27
//! semantic identity/currentness/authority and makes no mmap/NVMe performance claim.

use aura_k27_astge::{
    NodeIndexRecordV1, PageSource, PhysicalPageV1, SPlaneGraphReader, StorageError, BLOCK_SIZE,
    NODE_INDEX_RECORD_SIZE,
};
use memmap2::{Mmap, MmapOptions};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs::{self, File, OpenOptions};
use std::io::{Error, ErrorKind, Read, Result as IoResult, Write};
use std::path::{Path, PathBuf};
use std::sync::Arc;

const MANIFEST_SCHEMA: &str = "AuraK27AstgeMmapManifestV1";
const CURRENT_SCHEMA: &str = "AuraK27AstgeMmapCurrentV1";
const INDEX_FILE: &str = "node-index.bin";
const PAGES_FILE: &str = "pages.bin";
const MANIFEST_FILE: &str = "manifest.txt";
const CURRENT_FILE: &str = "CURRENT";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GenerationManifestV1 {
    pub storage_generation: u64,
    pub placement_generation: u64,
    pub record_count: u64,
    pub page_count: u64,
    pub index_sha256: String,
    pub pages_sha256: String,
    pub k27_physical_locality_proven: bool,
    pub external_post_map_mutation_protected: bool,
}

impl GenerationManifestV1 {
    fn encode(&self) -> Vec<u8> {
        format!(
            "schema={MANIFEST_SCHEMA}\nstorage_generation={}\nplacement_generation={}\nrecord_count={}\npage_count={}\nindex_sha256={}\npages_sha256={}\nk27_physical_locality_proven={}\nexternal_post_map_mutation_protected={}\n",
            self.storage_generation,
            self.placement_generation,
            self.record_count,
            self.page_count,
            self.index_sha256,
            self.pages_sha256,
            self.k27_physical_locality_proven,
            self.external_post_map_mutation_protected,
        )
        .into_bytes()
    }

    fn parse(bytes: &[u8]) -> IoResult<Self> {
        let text = std::str::from_utf8(bytes)
            .map_err(|_| invalid("manifest is not UTF-8"))?;
        let mut fields = parse_fields(text, "manifest")?;
        if fields.remove("schema") != Some(MANIFEST_SCHEMA) {
            return Err(invalid("manifest schema mismatch"));
        }
        let storage_generation = take_u64(&mut fields, "storage_generation")?;
        let placement_generation = take_u64(&mut fields, "placement_generation")?;
        let record_count = take_u64(&mut fields, "record_count")?;
        let page_count = take_u64(&mut fields, "page_count")?;
        let index_sha256 = take_digest(&mut fields, "index_sha256")?;
        let pages_sha256 = take_digest(&mut fields, "pages_sha256")?;
        let k27_physical_locality_proven = take_exact_bool(&mut fields, "k27_physical_locality_proven")?;
        let external_post_map_mutation_protected =
            take_exact_bool(&mut fields, "external_post_map_mutation_protected")?;
        if !fields.is_empty() {
            return Err(invalid("unexpected manifest field"));
        }
        if record_count == 0 || page_count == 0 {
            return Err(invalid("published generation must contain records and pages"));
        }
        if k27_physical_locality_proven || external_post_map_mutation_protected {
            return Err(invalid("V1 claim ceiling widened"));
        }
        Ok(Self {
            storage_generation,
            placement_generation,
            record_count,
            page_count,
            index_sha256,
            pages_sha256,
            k27_physical_locality_proven,
            external_post_map_mutation_protected,
        })
    }
}

#[derive(Clone)]
pub struct MmapPageSource {
    pages: Arc<Mmap>,
    page_count: u64,
    storage_generation: u64,
    placement_generation: u64,
}

impl PageSource for MmapPageSource {
    fn read_page(&mut self, pbn: u64) -> Result<[u8; BLOCK_SIZE], StorageError> {
        if pbn >= self.page_count {
            return Err(StorageError::Io(format!("PBN {pbn} outside mapped generation")));
        }
        let offset = (pbn as usize)
            .checked_mul(BLOCK_SIZE)
            .ok_or_else(|| StorageError::Io("mmap page offset overflow".to_string()))?;
        let end = offset + BLOCK_SIZE;
        let mut out = [0u8; BLOCK_SIZE];
        out.copy_from_slice(&self.pages[offset..end]);
        let decoded = PhysicalPageV1::decode(&out)?;
        if decoded.pbn != pbn {
            return Err(StorageError::PageNumberMismatch {
                requested: pbn,
                encoded: decoded.pbn,
            });
        }
        if decoded.placement_generation != self.placement_generation {
            return Err(StorageError::Io(format!(
                "placement generation mismatch in storage generation {}",
                self.storage_generation
            )));
        }
        Ok(out)
    }
}

pub struct MappedGenerationV1 {
    root: PathBuf,
    generation_dir: PathBuf,
    manifest: GenerationManifestV1,
    index: Mmap,
    pages: Arc<Mmap>,
}

impl MappedGenerationV1 {
    /// Open only the exact immutable generation named by the small `CURRENT` pointer.
    ///
    /// # Safety boundary
    /// `memmap2` requires an unsafe map operation because another process could mutate
    /// or truncate the backing file. This constructor first validates the current
    /// pointer, manifest digest, exact file lengths, SHA-256 contents, and all encoded
    /// pages, and the publisher makes generation files read-only on Unix. Those checks
    /// reduce accidental mutation risk but cannot prove protection against a privileged
    /// or hostile external process. The manifest therefore hard-falses that stronger claim.
    pub fn open_current(root: impl AsRef<Path>) -> IoResult<Self> {
        let root = root.as_ref().to_path_buf();
        let current_bytes = fs::read(root.join(CURRENT_FILE))?;
        let current = CurrentPointerV1::parse(&current_bytes)?;
        let generation_dir = root.join(&current.generation_dir);
        let manifest_bytes = fs::read(generation_dir.join(MANIFEST_FILE))?;
        if sha256_bytes(&manifest_bytes) != current.manifest_sha256 {
            return Err(invalid("CURRENT manifest digest mismatch"));
        }
        let manifest = GenerationManifestV1::parse(&manifest_bytes)?;
        if current.generation_dir != generation_dir_name(manifest.storage_generation) {
            return Err(invalid("CURRENT generation path mismatches manifest generation"));
        }

        let index_path = generation_dir.join(INDEX_FILE);
        let pages_path = generation_dir.join(PAGES_FILE);
        verify_file(
            &index_path,
            manifest.record_count * NODE_INDEX_RECORD_SIZE as u64,
            &manifest.index_sha256,
        )?;
        verify_file(
            &pages_path,
            manifest.page_count * BLOCK_SIZE as u64,
            &manifest.pages_sha256,
        )?;

        let index_file = File::open(&index_path)?;
        let pages_file = File::open(&pages_path)?;
        // SAFETY: the exact bytes and lengths were verified above; this crate never
        // mutates a published generation in place. External mutation by another
        // process remains explicitly outside the proved claim ceiling.
        let index = unsafe { MmapOptions::new().map(&index_file)? };
        // SAFETY: same immutable-generation contract as the index mapping above.
        let pages = Arc::new(unsafe { MmapOptions::new().map(&pages_file)? });

        let opened = Self {
            root,
            generation_dir,
            manifest,
            index,
            pages,
        };
        opened.validate_mapped_generation()?;
        Ok(opened)
    }

    pub fn manifest(&self) -> &GenerationManifestV1 {
        &self.manifest
    }

    pub fn root(&self) -> &Path {
        &self.root
    }

    pub fn generation_dir(&self) -> &Path {
        &self.generation_dir
    }

    pub fn records(&self) -> IoResult<Vec<NodeIndexRecordV1>> {
        let mut records = Vec::with_capacity(self.manifest.record_count as usize);
        for chunk in self.index.chunks_exact(NODE_INDEX_RECORD_SIZE) {
            records.push(
                NodeIndexRecordV1::decode(chunk)
                    .map_err(|err| invalid(format!("invalid node index record: {err}")))?,
            );
        }
        Ok(records)
    }

    pub fn graph_reader(&self) -> IoResult<SPlaneGraphReader<MmapPageSource>> {
        let records = self.records()?;
        let source = MmapPageSource {
            pages: Arc::clone(&self.pages),
            page_count: self.manifest.page_count,
            storage_generation: self.manifest.storage_generation,
            placement_generation: self.manifest.placement_generation,
        };
        SPlaneGraphReader::new(records, source)
            .map_err(|err| invalid(format!("invalid mapped graph index: {err}")))
    }

    fn validate_mapped_generation(&self) -> IoResult<()> {
        for pbn in 0..self.manifest.page_count {
            let offset = pbn as usize * BLOCK_SIZE;
            let end = offset + BLOCK_SIZE;
            let page: &[u8; BLOCK_SIZE] = self.pages[offset..end]
                .try_into()
                .map_err(|_| invalid("mapped page width mismatch"))?;
            let decoded = PhysicalPageV1::decode(page)
                .map_err(|err| invalid(format!("invalid physical page {pbn}: {err}")))?;
            if decoded.pbn != pbn {
                return Err(invalid(format!("physical page {pbn} encodes PBN {}", decoded.pbn)));
            }
            if decoded.placement_generation != self.manifest.placement_generation {
                return Err(invalid(format!("page {pbn} placement generation mismatch")));
            }
        }
        for record in self.records()? {
            if record.pbn >= self.manifest.page_count {
                return Err(invalid(format!("node {} references out-of-range PBN", record.node_id)));
            }
        }
        Ok(())
    }
}

/// Publish one complete immutable storage generation.
///
/// `CURRENT` is advanced only after index/pages/manifest are fully written, synced,
/// digested, validated, and the generation directory has been renamed into place.
/// A crash before the final pointer rename can leave an orphan complete generation;
/// it cannot make this API select a partially written generation.
pub fn publish_generation(
    root: impl AsRef<Path>,
    storage_generation: u64,
    placement_generation: u64,
    records: &[NodeIndexRecordV1],
    pages: &[PhysicalPageV1],
) -> IoResult<GenerationManifestV1> {
    if records.is_empty() || pages.is_empty() {
        return Err(Error::new(
            ErrorKind::InvalidInput,
            "generation requires at least one node record and one physical page",
        ));
    }
    validate_publication_inputs(placement_generation, records, pages)?;

    let root = root.as_ref();
    fs::create_dir_all(root)?;
    let generation_name = generation_dir_name(storage_generation);
    let final_dir = root.join(&generation_name);
    if final_dir.exists() {
        return Err(Error::new(
            ErrorKind::AlreadyExists,
            "storage generation is immutable and already exists",
        ));
    }
    let temp_dir = root.join(format!(
        ".{generation_name}.tmp-{}-{}",
        std::process::id(),
        unique_nonce()
    ));
    fs::create_dir(&temp_dir)?;

    let outcome = (|| -> IoResult<GenerationManifestV1> {
        let index_path = temp_dir.join(INDEX_FILE);
        let pages_path = temp_dir.join(PAGES_FILE);
        write_index(&index_path, records)?;
        write_pages(&pages_path, pages)?;

        let manifest = GenerationManifestV1 {
            storage_generation,
            placement_generation,
            record_count: records.len() as u64,
            page_count: pages.len() as u64,
            index_sha256: sha256_file(&index_path)?,
            pages_sha256: sha256_file(&pages_path)?,
            k27_physical_locality_proven: false,
            external_post_map_mutation_protected: false,
        };
        let manifest_bytes = manifest.encode();
        write_synced_new(&temp_dir.join(MANIFEST_FILE), &manifest_bytes)?;
        make_generation_read_only(&temp_dir)?;
        sync_dir(&temp_dir)?;
        fs::rename(&temp_dir, &final_dir)?;
        sync_dir(root)?;

        let current = CurrentPointerV1 {
            generation_dir: generation_name,
            manifest_sha256: sha256_bytes(&manifest_bytes),
        };
        publish_current(root, &current.encode())?;
        Ok(manifest)
    })();

    if outcome.is_err() && temp_dir.exists() {
        let _ = fs::remove_dir_all(&temp_dir);
    }
    outcome
}

fn validate_publication_inputs(
    placement_generation: u64,
    records: &[NodeIndexRecordV1],
    pages: &[PhysicalPageV1],
) -> IoResult<()> {
    for (pbn, page) in pages.iter().enumerate() {
        if page.pbn != pbn as u64 {
            return Err(Error::new(ErrorKind::InvalidInput, "pages must use dense absolute PBN order"));
        }
        if page.placement_generation != placement_generation {
            return Err(Error::new(ErrorKind::InvalidInput, "page placement generation mismatch"));
        }
        page.encode()
            .map_err(|err| Error::new(ErrorKind::InvalidInput, format!("invalid page: {err}")))?;
    }
    for record in records {
        if record.pbn >= pages.len() as u64 {
            return Err(Error::new(ErrorKind::InvalidInput, "node record references missing PBN"));
        }
        if record.byte_end < record.byte_start {
            return Err(Error::new(ErrorKind::InvalidInput, "node source span is inverted"));
        }
        let page = &pages[record.pbn as usize];
        let row = page
            .rows
            .get(record.row as usize)
            .ok_or_else(|| Error::new(ErrorKind::InvalidInput, "node record references missing row"))?;
        if row.degree != record.out_degree {
            return Err(Error::new(ErrorKind::InvalidInput, "node degree disagrees with physical page row"));
        }
    }
    // Reuse the parent's explicit node-ID index to reject duplicate IDs.
    let memory = MemoryPageSource {
        pages: pages.iter().map(|page| page.encode().expect("validated above")).collect(),
    };
    SPlaneGraphReader::new(records.iter().cloned(), memory)
        .map_err(|err| Error::new(ErrorKind::InvalidInput, format!("invalid graph index: {err}")))?;
    Ok(())
}

struct MemoryPageSource {
    pages: Vec<[u8; BLOCK_SIZE]>,
}

impl PageSource for MemoryPageSource {
    fn read_page(&mut self, pbn: u64) -> Result<[u8; BLOCK_SIZE], StorageError> {
        self.pages
            .get(pbn as usize)
            .copied()
            .ok_or_else(|| StorageError::Io(format!("missing in-memory PBN {pbn}")))
    }
}

fn write_index(path: &Path, records: &[NodeIndexRecordV1]) -> IoResult<()> {
    let mut file = create_new(path)?;
    for record in records {
        file.write_all(&record.encode())?;
    }
    file.sync_all()
}

fn write_pages(path: &Path, pages: &[PhysicalPageV1]) -> IoResult<()> {
    let mut file = create_new(path)?;
    for page in pages {
        let encoded = page
            .encode()
            .map_err(|err| Error::new(ErrorKind::InvalidInput, format!("invalid page: {err}")))?;
        file.write_all(&encoded)?;
    }
    file.sync_all()
}

fn create_new(path: &Path) -> IoResult<File> {
    OpenOptions::new().write(true).create_new(true).open(path)
}

fn write_synced_new(path: &Path, bytes: &[u8]) -> IoResult<()> {
    let mut file = create_new(path)?;
    file.write_all(bytes)?;
    file.sync_all()
}

fn publish_current(root: &Path, bytes: &[u8]) -> IoResult<()> {
    let temp = root.join(format!(".{CURRENT_FILE}.tmp-{}-{}", std::process::id(), unique_nonce()));
    write_synced_new(&temp, bytes)?;
    fs::rename(&temp, root.join(CURRENT_FILE))?;
    sync_dir(root)
}

fn generation_dir_name(generation: u64) -> String {
    format!("gen-{generation:020}")
}

#[derive(Debug, Clone)]
struct CurrentPointerV1 {
    generation_dir: String,
    manifest_sha256: String,
}

impl CurrentPointerV1 {
    fn encode(&self) -> Vec<u8> {
        format!(
            "schema={CURRENT_SCHEMA}\ngeneration_dir={}\nmanifest_sha256={}\n",
            self.generation_dir, self.manifest_sha256
        )
        .into_bytes()
    }

    fn parse(bytes: &[u8]) -> IoResult<Self> {
        let text = std::str::from_utf8(bytes).map_err(|_| invalid("CURRENT is not UTF-8"))?;
        let mut fields = parse_fields(text, "CURRENT")?;
        if fields.remove("schema") != Some(CURRENT_SCHEMA) {
            return Err(invalid("CURRENT schema mismatch"));
        }
        let generation_dir = fields
            .remove("generation_dir")
            .ok_or_else(|| invalid("CURRENT generation_dir missing"))?;
        if generation_dir.len() != 24
            || !generation_dir.starts_with("gen-")
            || !generation_dir[4..].bytes().all(|byte| byte.is_ascii_digit())
        {
            return Err(invalid("CURRENT generation_dir invalid"));
        }
        let manifest_sha256 = take_digest(&mut fields, "manifest_sha256")?;
        if !fields.is_empty() {
            return Err(invalid("unexpected CURRENT field"));
        }
        Ok(Self {
            generation_dir: generation_dir.to_owned(),
            manifest_sha256,
        })
    }
}

fn parse_fields<'a>(text: &'a str, label: &str) -> IoResult<BTreeMap<&'a str, &'a str>> {
    let mut fields = BTreeMap::new();
    for line in text.lines() {
        let (key, value) = line
            .split_once('=')
            .ok_or_else(|| invalid(format!("{label} line missing '='")))?;
        if fields.insert(key, value).is_some() {
            return Err(invalid(format!("duplicate {label} field")));
        }
    }
    Ok(fields)
}

fn take_u64(fields: &mut BTreeMap<&str, &str>, key: &str) -> IoResult<u64> {
    fields
        .remove(key)
        .ok_or_else(|| invalid(format!("missing {key}")))?
        .parse::<u64>()
        .map_err(|_| invalid(format!("invalid {key}")))
}

fn take_digest(fields: &mut BTreeMap<&str, &str>, key: &str) -> IoResult<String> {
    let value = fields
        .remove(key)
        .ok_or_else(|| invalid(format!("missing {key}")))?;
    if value.len() != 64 || !value.bytes().all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase()) {
        return Err(invalid(format!("invalid {key}")));
    }
    Ok(value.to_owned())
}

fn take_exact_bool(fields: &mut BTreeMap<&str, &str>, key: &str) -> IoResult<bool> {
    match fields.remove(key) {
        Some("true") => Ok(true),
        Some("false") => Ok(false),
        _ => Err(invalid(format!("invalid {key}"))),
    }
}

fn verify_file(path: &Path, expected_len: u64, expected_digest: &str) -> IoResult<()> {
    let metadata = fs::metadata(path)?;
    if metadata.len() != expected_len {
        return Err(invalid("generation file length mismatch"));
    }
    if sha256_file(path)? != expected_digest {
        return Err(invalid("generation file digest mismatch"));
    }
    Ok(())
}

fn sha256_file(path: &Path) -> IoResult<String> {
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
    Ok(hex(&hasher.finalize()))
}

fn sha256_bytes(bytes: &[u8]) -> String {
    hex(&Sha256::digest(bytes))
}

fn hex(bytes: &[u8]) -> String {
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

fn invalid(message: impl Into<String>) -> Error {
    Error::new(ErrorKind::InvalidData, message.into())
}

#[cfg(unix)]
fn make_generation_read_only(dir: &Path) -> IoResult<()> {
    use std::os::unix::fs::PermissionsExt;
    for name in [INDEX_FILE, PAGES_FILE, MANIFEST_FILE] {
        let path = dir.join(name);
        let mut permissions = fs::metadata(&path)?.permissions();
        permissions.set_mode(0o444);
        fs::set_permissions(path, permissions)?;
    }
    Ok(())
}

#[cfg(not(unix))]
fn make_generation_read_only(_dir: &Path) -> IoResult<()> {
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
