use crate::storage::{CsrPage, GraphSegment, NodeRecord, StorageError, NODE_RECORD_SIZE, PAGE_SIZE};
use core::fmt;
use std::collections::BTreeSet;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

const MANIFEST_MAGIC: &[u8; 8] = b"AK27GEN1";
const MANIFEST_SCHEMA: u32 = 1;
const MANIFEST_SIZE: usize = 128;
const MANIFEST_CHECKSUM_OFFSET: usize = 72;
const MANIFEST_RESERVED_OFFSET: usize = 76;
const STAGE_COUNTER: AtomicU64 = AtomicU64::new(1);

#[derive(Debug)]
pub enum GenerationError {
    Io(std::io::Error),
    Storage(StorageError),
    EmptySegment,
    UnsupportedManifestSchema { actual: u32 },
    InvalidManifestLength { actual: usize },
    InvalidManifestMagic,
    InvalidManifestChecksum,
    NonZeroManifestReservedBytes,
    ManifestSizeMismatch,
    NodeChecksumMismatch,
    CsrChecksumMismatch,
    GenerationSequenceMismatch { expected: u32, actual: u32 },
    BaseNodeMismatch { expected: u64, actual: u64 },
    BasePbnMismatch { expected: u64, actual: u64 },
    PublishedGenerationGap { expected: u32, actual: u32 },
    GenerationAlreadyMaterialized { generation: u32 },
    CommittedArtifactMissing { generation: u32, kind: &'static str },
    SimulatedCrash(&'static str),
    DurabilityUnsupportedPlatform,
}

impl fmt::Display for GenerationError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io(error) => write!(f, "generation I/O error: {error}"),
            Self::Storage(error) => write!(f, "generation storage error: {error}"),
            Self::EmptySegment => write!(f, "empty graph segments cannot be published"),
            Self::UnsupportedManifestSchema { actual } => {
                write!(f, "unsupported generation manifest schema {actual}")
            }
            Self::InvalidManifestLength { actual } => {
                write!(f, "generation manifest has {actual} bytes instead of {MANIFEST_SIZE}")
            }
            Self::InvalidManifestMagic => write!(f, "generation manifest magic mismatch"),
            Self::InvalidManifestChecksum => write!(f, "generation manifest checksum mismatch"),
            Self::NonZeroManifestReservedBytes => {
                write!(f, "generation manifest reserved bytes are nonzero")
            }
            Self::ManifestSizeMismatch => write!(f, "generation manifest size/count mismatch"),
            Self::NodeChecksumMismatch => write!(f, "generation node-table checksum mismatch"),
            Self::CsrChecksumMismatch => write!(f, "generation CSR checksum mismatch"),
            Self::GenerationSequenceMismatch { expected, actual } => {
                write!(f, "expected generation {expected}, received {actual}")
            }
            Self::BaseNodeMismatch { expected, actual } => {
                write!(f, "expected base node {expected}, received {actual}")
            }
            Self::BasePbnMismatch { expected, actual } => {
                write!(f, "expected base PBN {expected}, received {actual}")
            }
            Self::PublishedGenerationGap { expected, actual } => {
                write!(f, "published generation sequence expected {expected}, found {actual}")
            }
            Self::GenerationAlreadyMaterialized { generation } => {
                write!(f, "generation {generation} already has materialized files")
            }
            Self::CommittedArtifactMissing { generation, kind } => {
                write!(f, "committed generation {generation} is missing {kind}")
            }
            Self::SimulatedCrash(point) => write!(f, "simulated crash at {point}"),
            Self::DurabilityUnsupportedPlatform => {
                write!(f, "directory fsync durability contract is not implemented on this platform")
            }
        }
    }
}

impl std::error::Error for GenerationError {}

impl From<std::io::Error> for GenerationError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value)
    }
}

impl From<StorageError> for GenerationError {
    fn from(value: StorageError) -> Self {
        Self::Storage(value)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GenerationManifest {
    pub generation: u32,
    pub base_node_id: u64,
    pub base_pbn: u64,
    pub node_count: u64,
    pub page_count: u64,
    pub node_bytes: u64,
    pub csr_bytes: u64,
    pub node_crc32: u32,
    pub csr_crc32: u32,
}

impl GenerationManifest {
    fn from_segment(segment: &GraphSegment, node_bytes: &[u8], csr_bytes: &[u8]) -> Self {
        Self {
            generation: segment.generation(),
            base_node_id: segment.base_node_id(),
            base_pbn: segment.base_pbn(),
            node_count: segment.node_count() as u64,
            page_count: segment.page_count() as u64,
            node_bytes: node_bytes.len() as u64,
            csr_bytes: csr_bytes.len() as u64,
            node_crc32: crc32(node_bytes),
            csr_crc32: crc32(csr_bytes),
        }
    }

    pub fn next_node_id(self) -> u64 {
        self.base_node_id + self.node_count
    }

    pub fn next_pbn(self) -> u64 {
        self.base_pbn + self.page_count
    }

    fn encode(self) -> [u8; MANIFEST_SIZE] {
        let mut bytes = [0_u8; MANIFEST_SIZE];
        bytes[0..8].copy_from_slice(MANIFEST_MAGIC);
        write_u32(&mut bytes, 8, MANIFEST_SCHEMA);
        write_u32(&mut bytes, 12, self.generation);
        write_u64(&mut bytes, 16, self.base_node_id);
        write_u64(&mut bytes, 24, self.base_pbn);
        write_u64(&mut bytes, 32, self.node_count);
        write_u64(&mut bytes, 40, self.page_count);
        write_u64(&mut bytes, 48, self.node_bytes);
        write_u64(&mut bytes, 56, self.csr_bytes);
        write_u32(&mut bytes, 64, self.node_crc32);
        write_u32(&mut bytes, 68, self.csr_crc32);
        let manifest_crc = crc32(&bytes[..MANIFEST_CHECKSUM_OFFSET]);
        write_u32(&mut bytes, MANIFEST_CHECKSUM_OFFSET, manifest_crc);
        bytes
    }

    fn decode(bytes: &[u8]) -> Result<Self, GenerationError> {
        if bytes.len() != MANIFEST_SIZE {
            return Err(GenerationError::InvalidManifestLength { actual: bytes.len() });
        }
        if &bytes[..8] != MANIFEST_MAGIC {
            return Err(GenerationError::InvalidManifestMagic);
        }
        let schema = read_u32(bytes, 8);
        if schema != MANIFEST_SCHEMA {
            return Err(GenerationError::UnsupportedManifestSchema { actual: schema });
        }
        let expected_crc = read_u32(bytes, MANIFEST_CHECKSUM_OFFSET);
        if crc32(&bytes[..MANIFEST_CHECKSUM_OFFSET]) != expected_crc {
            return Err(GenerationError::InvalidManifestChecksum);
        }
        if bytes[MANIFEST_RESERVED_OFFSET..].iter().any(|value| *value != 0) {
            return Err(GenerationError::NonZeroManifestReservedBytes);
        }
        let manifest = Self {
            generation: read_u32(bytes, 12),
            base_node_id: read_u64(bytes, 16),
            base_pbn: read_u64(bytes, 24),
            node_count: read_u64(bytes, 32),
            page_count: read_u64(bytes, 40),
            node_bytes: read_u64(bytes, 48),
            csr_bytes: read_u64(bytes, 56),
            node_crc32: read_u32(bytes, 64),
            csr_crc32: read_u32(bytes, 68),
        };
        if manifest.generation == 0
            || manifest.node_count == 0
            || manifest.page_count == 0
            || manifest.node_bytes != manifest.node_count * NODE_RECORD_SIZE as u64
            || manifest.csr_bytes != manifest.page_count * PAGE_SIZE as u64
        {
            return Err(GenerationError::ManifestSizeMismatch);
        }
        Ok(manifest)
    }
}

#[derive(Debug, Clone)]
pub struct GenerationStore {
    root: PathBuf,
}

impl GenerationStore {
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self { root: root.into() }
    }

    pub fn root(&self) -> &Path {
        &self.root
    }

    pub fn current_manifest(&self) -> Result<Option<GenerationManifest>, GenerationError> {
        let generations = self.published_generations()?;
        let Some(generation) = generations.last().copied() else {
            return Ok(None);
        };
        Ok(Some(self.read_manifest(generation)?))
    }

    pub fn publish(&self, segment: &GraphSegment) -> Result<GenerationManifest, GenerationError> {
        self.publish_inner(segment, None)
    }

    pub fn load_current_chain(&self) -> Result<Vec<GraphSegment>, GenerationError> {
        let generations = self.published_generations()?;
        let mut segments = Vec::with_capacity(generations.len());
        let mut expected_generation = 1_u32;
        let mut expected_node = 0_u64;
        let mut expected_pbn = 0_u64;
        for generation in generations {
            if generation != expected_generation {
                return Err(GenerationError::PublishedGenerationGap {
                    expected: expected_generation,
                    actual: generation,
                });
            }
            let segment = self.load_segment(generation)?;
            if segment.base_node_id() != expected_node {
                return Err(GenerationError::BaseNodeMismatch {
                    expected: expected_node,
                    actual: segment.base_node_id(),
                });
            }
            if segment.base_pbn() != expected_pbn {
                return Err(GenerationError::BasePbnMismatch {
                    expected: expected_pbn,
                    actual: segment.base_pbn(),
                });
            }
            expected_node = segment.next_node_id();
            expected_pbn = segment.next_pbn();
            expected_generation += 1;
            segments.push(segment);
        }
        Ok(segments)
    }

    pub fn orphaned_generations(&self) -> Result<Vec<u32>, GenerationError> {
        if !self.root.exists() {
            return Ok(Vec::new());
        }
        let published: BTreeSet<u32> = self.published_generations()?.into_iter().collect();
        let mut materialized = BTreeSet::new();
        for entry in fs::read_dir(&self.root)? {
            let entry = entry?;
            if let Some(generation) = parse_generation_artifact_name(&entry.file_name().to_string_lossy()) {
                materialized.insert(generation);
            }
        }
        Ok(materialized.difference(&published).copied().collect())
    }

    fn publish_inner(
        &self,
        segment: &GraphSegment,
        fault: Option<PublishFault>,
    ) -> Result<GenerationManifest, GenerationError> {
        segment.validate()?;
        if segment.node_count() == 0 || segment.page_count() == 0 {
            return Err(GenerationError::EmptySegment);
        }
        fs::create_dir_all(&self.root)?;

        let current = self.current_manifest()?;
        let (expected_generation, expected_node, expected_pbn) = current
            .map(|manifest| {
                (
                    manifest.generation + 1,
                    manifest.next_node_id(),
                    manifest.next_pbn(),
                )
            })
            .unwrap_or((1, 0, 0));
        if segment.generation() != expected_generation {
            return Err(GenerationError::GenerationSequenceMismatch {
                expected: expected_generation,
                actual: segment.generation(),
            });
        }
        if segment.base_node_id() != expected_node {
            return Err(GenerationError::BaseNodeMismatch {
                expected: expected_node,
                actual: segment.base_node_id(),
            });
        }
        if segment.base_pbn() != expected_pbn {
            return Err(GenerationError::BasePbnMismatch {
                expected: expected_pbn,
                actual: segment.base_pbn(),
            });
        }

        let node_bytes = segment.node_table_bytes();
        let csr_bytes = segment.csr_bytes();
        let manifest = GenerationManifest::from_segment(segment, &node_bytes, &csr_bytes);
        let generation = manifest.generation;
        let nodes_final = self.nodes_path(generation);
        let csr_final = self.csr_path(generation);
        let manifest_final = self.manifest_path(generation);
        let ready_final = self.ready_path(generation);
        for path in [&nodes_final, &csr_final, &manifest_final, &ready_final] {
            if path.exists() {
                return Err(GenerationError::GenerationAlreadyMaterialized { generation });
            }
        }

        let nodes_stage = self.stage_path(&nodes_final);
        let csr_stage = self.stage_path(&csr_final);
        write_new_synced(&nodes_stage, &node_bytes)?;
        write_new_synced(&csr_stage, &csr_bytes)?;
        fs::rename(&nodes_stage, &nodes_final)?;
        fs::rename(&csr_stage, &csr_final)?;
        sync_directory(&self.root)?;
        if fault == Some(PublishFault::AfterDataInstall) {
            return Err(GenerationError::SimulatedCrash("AFTER_DATA_INSTALL"));
        }

        let manifest_stage = self.stage_path(&manifest_final);
        write_new_synced(&manifest_stage, &manifest.encode())?;
        fs::rename(&manifest_stage, &manifest_final)?;
        sync_directory(&self.root)?;
        if fault == Some(PublishFault::AfterManifestInstall) {
            return Err(GenerationError::SimulatedCrash("AFTER_MANIFEST_INSTALL"));
        }

        write_new_synced(&ready_final, &[])?;
        sync_directory(&self.root)?;
        self.load_segment(generation)?;
        Ok(manifest)
    }

    fn published_generations(&self) -> Result<Vec<u32>, GenerationError> {
        if !self.root.exists() {
            return Ok(Vec::new());
        }
        let mut generations = Vec::new();
        for entry in fs::read_dir(&self.root)? {
            let entry = entry?;
            let name = entry.file_name();
            let name = name.to_string_lossy();
            if let Some(generation) = parse_ready_name(&name) {
                generations.push(generation);
            }
        }
        generations.sort_unstable();
        for (index, generation) in generations.iter().copied().enumerate() {
            let expected = index as u32 + 1;
            if generation != expected {
                return Err(GenerationError::PublishedGenerationGap {
                    expected,
                    actual: generation,
                });
            }
        }
        Ok(generations)
    }

    fn load_segment(&self, generation: u32) -> Result<GraphSegment, GenerationError> {
        let ready = self.ready_path(generation);
        if !ready.exists() {
            return Err(GenerationError::CommittedArtifactMissing {
                generation,
                kind: "ready marker",
            });
        }
        let manifest_path = self.manifest_path(generation);
        let nodes_path = self.nodes_path(generation);
        let csr_path = self.csr_path(generation);
        for (path, kind) in [
            (&manifest_path, "manifest"),
            (&nodes_path, "node table"),
            (&csr_path, "CSR pages"),
        ] {
            if !path.exists() {
                return Err(GenerationError::CommittedArtifactMissing { generation, kind });
            }
        }
        let manifest = self.read_manifest(generation)?;
        if manifest.generation != generation {
            return Err(GenerationError::GenerationSequenceMismatch {
                expected: generation,
                actual: manifest.generation,
            });
        }
        let node_bytes = read_exact_file(&nodes_path)?;
        let csr_bytes = read_exact_file(&csr_path)?;
        if node_bytes.len() as u64 != manifest.node_bytes
            || csr_bytes.len() as u64 != manifest.csr_bytes
        {
            return Err(GenerationError::ManifestSizeMismatch);
        }
        if crc32(&node_bytes) != manifest.node_crc32 {
            return Err(GenerationError::NodeChecksumMismatch);
        }
        if crc32(&csr_bytes) != manifest.csr_crc32 {
            return Err(GenerationError::CsrChecksumMismatch);
        }
        let mut nodes = Vec::with_capacity(manifest.node_count as usize);
        for frame in node_bytes.chunks_exact(NODE_RECORD_SIZE) {
            nodes.push(NodeRecord::decode(frame)?);
        }
        let mut pages = Vec::with_capacity(manifest.page_count as usize);
        for frame in csr_bytes.chunks_exact(PAGE_SIZE) {
            pages.push(CsrPage::from_bytes(frame)?);
        }
        let segment = GraphSegment::from_parts(
            manifest.base_node_id,
            manifest.base_pbn,
            manifest.generation,
            nodes,
            pages,
        )?;
        if segment.node_count() as u64 != manifest.node_count
            || segment.page_count() as u64 != manifest.page_count
        {
            return Err(GenerationError::ManifestSizeMismatch);
        }
        Ok(segment)
    }

    fn read_manifest(&self, generation: u32) -> Result<GenerationManifest, GenerationError> {
        let path = self.manifest_path(generation);
        if !path.exists() {
            return Err(GenerationError::CommittedArtifactMissing {
                generation,
                kind: "manifest",
            });
        }
        GenerationManifest::decode(&read_exact_file(&path)?)
    }

    fn nodes_path(&self, generation: u32) -> PathBuf {
        self.root.join(format!("gen-{generation:010}.nodes"))
    }

    fn csr_path(&self, generation: u32) -> PathBuf {
        self.root.join(format!("gen-{generation:010}.csr"))
    }

    fn manifest_path(&self, generation: u32) -> PathBuf {
        self.root.join(format!("gen-{generation:010}.manifest"))
    }

    fn ready_path(&self, generation: u32) -> PathBuf {
        self.root.join(format!("gen-{generation:010}.ready"))
    }

    fn stage_path(&self, final_path: &Path) -> PathBuf {
        let nonce = STAGE_COUNTER.fetch_add(1, Ordering::Relaxed);
        let name = final_path.file_name().unwrap_or_default().to_string_lossy();
        self.root.join(format!(".{name}.stage-{}-{nonce}", std::process::id()))
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum PublishFault {
    AfterDataInstall,
    AfterManifestInstall,
}

fn write_new_synced(path: &Path, bytes: &[u8]) -> Result<(), GenerationError> {
    let mut file = OpenOptions::new().create_new(true).write(true).open(path)?;
    file.write_all(bytes)?;
    file.sync_all()?;
    Ok(())
}

fn read_exact_file(path: &Path) -> Result<Vec<u8>, GenerationError> {
    let mut file = File::open(path)?;
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)?;
    Ok(bytes)
}

#[cfg(unix)]
fn sync_directory(path: &Path) -> Result<(), GenerationError> {
    File::open(path)?.sync_all()?;
    Ok(())
}

#[cfg(not(unix))]
fn sync_directory(_path: &Path) -> Result<(), GenerationError> {
    Err(GenerationError::DurabilityUnsupportedPlatform)
}

fn parse_ready_name(name: &str) -> Option<u32> {
    let body = name.strip_prefix("gen-")?.strip_suffix(".ready")?;
    if body.len() != 10 || !body.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    body.parse().ok()
}

fn parse_generation_artifact_name(name: &str) -> Option<u32> {
    for suffix in [".nodes", ".csr", ".manifest"] {
        if let Some(body) = name.strip_prefix("gen-").and_then(|value| value.strip_suffix(suffix)) {
            if body.len() == 10 && body.bytes().all(|byte| byte.is_ascii_digit()) {
                return body.parse().ok();
            }
        }
    }
    None
}

fn crc32(bytes: &[u8]) -> u32 {
    let mut crc = 0xffff_ffff_u32;
    for byte in bytes {
        let mut value = (crc ^ u32::from(*byte)) & 0xff;
        for _ in 0..8 {
            value = if value & 1 == 1 {
                (value >> 1) ^ 0xedb8_8320
            } else {
                value >> 1
            };
        }
        crc = (crc >> 8) ^ value;
    }
    !crc
}

fn write_u32(bytes: &mut [u8], offset: usize, value: u32) {
    bytes[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
}

fn write_u64(bytes: &mut [u8], offset: usize, value: u64) {
    bytes[offset..offset + 8].copy_from_slice(&value.to_le_bytes());
}

fn read_u32(bytes: &[u8], offset: usize) -> u32 {
    u32::from_le_bytes(bytes[offset..offset + 4].try_into().expect("validated fixed frame"))
}

fn read_u64(bytes: &[u8], offset: usize) -> u64 {
    u64::from_le_bytes(bytes[offset..offset + 8].try_into().expect("validated fixed frame"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU64, Ordering};

    static TEST_COUNTER: AtomicU64 = AtomicU64::new(1);

    struct TestDir(PathBuf);

    impl TestDir {
        fn new(label: &str) -> Self {
            let nonce = TEST_COUNTER.fetch_add(1, Ordering::Relaxed);
            let path = std::env::temp_dir().join(format!(
                "aura-k27-astge-generation-{label}-{}-{nonce}",
                std::process::id()
            ));
            let _ = fs::remove_dir_all(&path);
            fs::create_dir_all(&path).expect("create test directory");
            Self(path)
        }
    }

    impl Drop for TestDir {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }

    fn segment(base_node_id: u64, base_pbn: u64, generation: u32) -> GraphSegment {
        let mut page = CsrPage::new(base_pbn, 0, generation);
        let row = page.push_row(&[]).expect("empty CSR row");
        let node = NodeRecord {
            node_id: base_node_id,
            coord_packed: 0,
            type_id: 1,
            file_id: 1,
            byte_start: 0,
            byte_end: 1,
            edge_block_pbn: base_pbn,
            edge_row_idx: row,
            out_degree: 0,
            generation,
            flags: 0,
        };
        GraphSegment::from_parts(
            base_node_id,
            base_pbn,
            generation,
            vec![node],
            vec![page],
        )
        .expect("valid segment")
    }

    #[test]
    fn publish_and_load_two_immutable_generations() {
        let dir = TestDir::new("two-generations");
        let store = GenerationStore::new(&dir.0);
        let first = store.publish(&segment(0, 0, 1)).expect("publish first");
        let second = store.publish(&segment(1, 1, 2)).expect("publish second");
        assert_eq!(1, first.generation);
        assert_eq!(2, second.generation);
        let chain = store.load_current_chain().expect("load chain");
        assert_eq!(2, chain.len());
        assert_eq!(0, chain[0].base_node_id());
        assert_eq!(1, chain[1].base_node_id());
        assert!(store.orphaned_generations().unwrap().is_empty());
    }

    #[test]
    fn crash_after_data_install_does_not_publish_generation() {
        let dir = TestDir::new("crash-data");
        let store = GenerationStore::new(&dir.0);
        store.publish(&segment(0, 0, 1)).unwrap();
        let error = store
            .publish_inner(&segment(1, 1, 2), Some(PublishFault::AfterDataInstall))
            .unwrap_err();
        assert!(matches!(error, GenerationError::SimulatedCrash("AFTER_DATA_INSTALL")));
        let chain = store.load_current_chain().unwrap();
        assert_eq!(1, chain.len());
        assert_eq!(vec![2], store.orphaned_generations().unwrap());
    }

    #[test]
    fn crash_after_manifest_install_does_not_publish_generation() {
        let dir = TestDir::new("crash-manifest");
        let store = GenerationStore::new(&dir.0);
        store.publish(&segment(0, 0, 1)).unwrap();
        let error = store
            .publish_inner(&segment(1, 1, 2), Some(PublishFault::AfterManifestInstall))
            .unwrap_err();
        assert!(matches!(
            error,
            GenerationError::SimulatedCrash("AFTER_MANIFEST_INSTALL")
        ));
        assert_eq!(1, store.load_current_chain().unwrap().len());
        assert_eq!(vec![2], store.orphaned_generations().unwrap());
    }

    #[test]
    fn ready_marker_with_missing_artifacts_fails_closed_without_fallback() {
        let dir = TestDir::new("missing-committed");
        let store = GenerationStore::new(&dir.0);
        store.publish(&segment(0, 0, 1)).unwrap();
        write_new_synced(&store.ready_path(2), &[]).unwrap();
        sync_directory(&dir.0).unwrap();
        let error = store.load_current_chain().unwrap_err();
        assert!(matches!(
            error,
            GenerationError::CommittedArtifactMissing {
                generation: 2,
                kind: "manifest"
            }
        ));
    }

    #[test]
    fn committed_node_corruption_fails_checksum_before_decode() {
        let dir = TestDir::new("node-corruption");
        let store = GenerationStore::new(&dir.0);
        store.publish(&segment(0, 0, 1)).unwrap();
        let path = store.nodes_path(1);
        let mut bytes = fs::read(&path).unwrap();
        bytes[0] ^= 0x80;
        fs::write(&path, bytes).unwrap();
        let error = store.load_current_chain().unwrap_err();
        assert!(matches!(error, GenerationError::NodeChecksumMismatch));
    }

    #[test]
    fn committed_manifest_corruption_fails_checksum() {
        let dir = TestDir::new("manifest-corruption");
        let store = GenerationStore::new(&dir.0);
        store.publish(&segment(0, 0, 1)).unwrap();
        let path = store.manifest_path(1);
        let mut bytes = fs::read(&path).unwrap();
        bytes[20] ^= 0x40;
        fs::write(&path, bytes).unwrap();
        let error = store.load_current_chain().unwrap_err();
        assert!(matches!(error, GenerationError::InvalidManifestChecksum));
    }

    #[test]
    fn generation_gap_is_rejected_before_materialization() {
        let dir = TestDir::new("generation-gap");
        let store = GenerationStore::new(&dir.0);
        store.publish(&segment(0, 0, 1)).unwrap();
        let error = store.publish(&segment(1, 1, 3)).unwrap_err();
        assert!(matches!(
            error,
            GenerationError::GenerationSequenceMismatch {
                expected: 2,
                actual: 3
            }
        ));
    }

    #[test]
    fn append_base_node_and_pbn_are_consumer_bound() {
        let dir = TestDir::new("base-binding");
        let store = GenerationStore::new(&dir.0);
        store.publish(&segment(0, 0, 1)).unwrap();
        let node_error = store.publish(&segment(2, 1, 2)).unwrap_err();
        assert!(matches!(
            node_error,
            GenerationError::BaseNodeMismatch {
                expected: 1,
                actual: 2
            }
        ));
        let pbn_error = store.publish(&segment(1, 2, 2)).unwrap_err();
        assert!(matches!(
            pbn_error,
            GenerationError::BasePbnMismatch {
                expected: 1,
                actual: 2
            }
        ));
    }

    #[test]
    fn crc32_known_vector_is_stable() {
        assert_eq!(0xcbf4_3926, crc32(b"123456789"));
    }
}
