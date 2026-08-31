#![forbid(unsafe_code)]

#[path = "v2.rs"]
mod v2;

pub use v2::*;

use std::collections::{HashMap, HashSet, VecDeque};
use std::fs::{File, Metadata};
use std::io::{Read, Seek, SeekFrom};
use std::path::Path;

/// Identity captured from an already-open file handle.
///
/// This is deliberately stronger than a path string: replacement of the path after open does not
/// change the identity of the file object held by the reader. It is still only physical-storage
/// identity, never semantic/source/currentness/authority identity.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OpenedFileIdentityV1 {
    pub len: u64,
    pub platform: PlatformFileIdentityV1,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PlatformFileIdentityV1 {
    #[cfg(unix)]
    Unix { device: u64, inode: u64 },
    Unsupported,
}

fn platform_identity(metadata: &Metadata) -> PlatformFileIdentityV1 {
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        return PlatformFileIdentityV1::Unix {
            device: metadata.dev(),
            inode: metadata.ino(),
        };
    }

    #[allow(unreachable_code)]
    PlatformFileIdentityV1::Unsupported
}

fn opened_file_identity(file: &File) -> Result<OpenedFileIdentityV1, GenerationStorageError> {
    let metadata = file.metadata()?;
    if !metadata.is_file() {
        return Err(GenerationStorageError::NotRegularFile);
    }
    Ok(OpenedFileIdentityV1 {
        len: metadata.len(),
        platform: platform_identity(&metadata),
    })
}

fn expected_len(count: u64, width: usize) -> Result<u64, GenerationStorageError> {
    count
        .checked_mul(width as u64)
        .ok_or(GenerationStorageError::LengthOverflow)
}

fn load_index_from_open_handle(
    file: &mut File,
    binding: &StorageGenerationBindingV1,
) -> Result<HashMap<u64, NodeIndexRecordV1>, GenerationStorageError> {
    let expected = expected_len(binding.node_count, NODE_INDEX_RECORD_SIZE)?;
    let actual = opened_file_identity(file)?.len;
    if actual != expected {
        return Err(GenerationStorageError::NodeIndexLengthMismatch { expected, actual });
    }
    if binding.node_count > 0 && binding.page_count == 0 {
        return Err(GenerationStorageError::IndexPageOutOfRange {
            node_id: 0,
            pbn: 0,
            page_count: 0,
        });
    }

    file.seek(SeekFrom::Start(0))?;
    let mut index = HashMap::with_capacity(binding.node_count as usize);
    let mut raw = [0u8; NODE_INDEX_RECORD_SIZE];
    for _ in 0..binding.node_count {
        file.read_exact(&mut raw)?;
        let record = NodeIndexRecordV1::decode(&raw)?;
        if record.pbn >= binding.page_count {
            return Err(GenerationStorageError::IndexPageOutOfRange {
                node_id: record.node_id,
                pbn: record.pbn,
                page_count: binding.page_count,
            });
        }
        let node_id = record.node_id;
        if index.insert(node_id, record).is_some() {
            return Err(GenerationStorageError::DuplicateNodeId(node_id));
        }
    }
    file.seek(SeekFrom::Start(0))?;
    Ok(index)
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BackingProtectionV1 {
    /// An external owner/isolation layer attests that published generations are replacement-only
    /// and cannot be modified or truncated in place for the capability lifetime.
    OwnerIsolatedReplacementOnly { policy_digest: [u8; 32] },
    /// An external platform verifier attests that the exact opened files are Linux fs-verity files
    /// with the supplied verity digests. This crate does not issue the ioctl or grant the attestation.
    FsVerityExternallyAttested {
        node_verity_digest: [u8; 32],
        page_verity_digest: [u8; 32],
    },
    /// Permission bits alone are not accepted as an immutability proof.
    PermissionBitsOnly,
    Unknown,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExternalMutationDispositionV1 {
    PreventedForCapabilityLifetime,
    NotPrevented,
    Unknown,
}

/// Capability supplied by an independently responsible platform/storage owner.
///
/// The ASTGE crate verifies internal binding consistency against exact opened file identities. It
/// does not self-author the external isolation/fs-verity claim and therefore does not convert this
/// physical capability into semantic or execution authority.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BackingFileImmutabilityCapabilityV1 {
    pub storage_root_identity: [u8; 32],
    pub snapshot_generation: u64,
    pub manifest_digest: [u8; 32],
    pub node_file_identity: OpenedFileIdentityV1,
    pub page_file_identity: OpenedFileIdentityV1,
    pub protection: BackingProtectionV1,
    pub external_mutation: ExternalMutationDispositionV1,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MmapAdmissionErrorV1 {
    SnapshotGenerationMismatch { expected: u64, observed: u64 },
    ManifestDigestMismatch,
    NodeFileIdentityMismatch,
    PageFileIdentityMismatch,
    PlatformFileIdentityUnavailable,
    ProtectionInsufficient,
    ExternalMutationNotPrevented,
    FileIdentityChangedBeforeMap,
    Storage(GenerationStorageError),
}

impl From<GenerationStorageError> for MmapAdmissionErrorV1 {
    fn from(value: GenerationStorageError) -> Self {
        Self::Storage(value)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MmapAdmissionTokenV1 {
    pub storage_root_identity: [u8; 32],
    pub snapshot_generation: u64,
    pub manifest_digest: [u8; 32],
    pub node_file_identity: OpenedFileIdentityV1,
    pub page_file_identity: OpenedFileIdentityV1,
}

/// Exact opened generation. All structural admission happens after opening and against these same
/// file handles; later path replacement cannot redirect this reader to another file object.
pub struct OpenedGenerationFilesV1 {
    node_index_file: File,
    page_file: File,
    index: HashMap<u64, NodeIndexRecordV1>,
    binding: StorageGenerationBindingV1,
    snapshot_generation: u64,
    manifest_digest: [u8; 32],
    node_identity: OpenedFileIdentityV1,
    page_identity: OpenedFileIdentityV1,
}

impl OpenedGenerationFilesV1 {
    pub fn open(
        node_index_path: impl AsRef<Path>,
        page_path: impl AsRef<Path>,
        binding: StorageGenerationBindingV1,
        snapshot_generation: u64,
        manifest_digest: [u8; 32],
    ) -> Result<Self, GenerationStorageError> {
        // Open first, then validate metadata and content through these exact handles. This removes
        // the path-metadata -> later-open TOCTOU seam from the generation reader.
        let mut node_index_file = File::open(node_index_path)?;
        let page_file = File::open(page_path)?;

        let node_identity = opened_file_identity(&node_index_file)?;
        let page_identity = opened_file_identity(&page_file)?;
        let expected_nodes = expected_len(binding.node_count, NODE_INDEX_RECORD_SIZE)?;
        let expected_pages = expected_len(binding.page_count, BLOCK_SIZE)?;
        if node_identity.len != expected_nodes {
            return Err(GenerationStorageError::NodeIndexLengthMismatch {
                expected: expected_nodes,
                actual: node_identity.len,
            });
        }
        if page_identity.len != expected_pages {
            return Err(GenerationStorageError::PageFileLengthMismatch {
                expected: expected_pages,
                actual: page_identity.len,
            });
        }

        let index = load_index_from_open_handle(&mut node_index_file, &binding)?;
        Ok(Self {
            node_index_file,
            page_file,
            index,
            binding,
            snapshot_generation,
            manifest_digest,
            node_identity,
            page_identity,
        })
    }

    pub fn node_file_identity(&self) -> &OpenedFileIdentityV1 {
        &self.node_identity
    }

    pub fn page_file_identity(&self) -> &OpenedFileIdentityV1 {
        &self.page_identity
    }

    pub fn snapshot_generation(&self) -> u64 {
        self.snapshot_generation
    }

    pub fn manifest_digest(&self) -> [u8; 32] {
        self.manifest_digest
    }

    pub fn admit_mmap(
        &self,
        capability: &BackingFileImmutabilityCapabilityV1,
    ) -> Result<MmapAdmissionTokenV1, MmapAdmissionErrorV1> {
        if capability.snapshot_generation != self.snapshot_generation {
            return Err(MmapAdmissionErrorV1::SnapshotGenerationMismatch {
                expected: self.snapshot_generation,
                observed: capability.snapshot_generation,
            });
        }
        if capability.manifest_digest != self.manifest_digest {
            return Err(MmapAdmissionErrorV1::ManifestDigestMismatch);
        }
        if capability.node_file_identity != self.node_identity {
            return Err(MmapAdmissionErrorV1::NodeFileIdentityMismatch);
        }
        if capability.page_file_identity != self.page_identity {
            return Err(MmapAdmissionErrorV1::PageFileIdentityMismatch);
        }
        if matches!(
            self.node_identity.platform,
            PlatformFileIdentityV1::Unsupported
        ) || matches!(
            self.page_identity.platform,
            PlatformFileIdentityV1::Unsupported
        ) {
            return Err(MmapAdmissionErrorV1::PlatformFileIdentityUnavailable);
        }
        if matches!(
            capability.protection,
            BackingProtectionV1::PermissionBitsOnly | BackingProtectionV1::Unknown
        ) {
            return Err(MmapAdmissionErrorV1::ProtectionInsufficient);
        }
        if capability.external_mutation
            != ExternalMutationDispositionV1::PreventedForCapabilityLifetime
        {
            return Err(MmapAdmissionErrorV1::ExternalMutationNotPrevented);
        }

        self.revalidate_opened_identities()?;
        Ok(MmapAdmissionTokenV1 {
            storage_root_identity: capability.storage_root_identity,
            snapshot_generation: self.snapshot_generation,
            manifest_digest: self.manifest_digest,
            node_file_identity: self.node_identity.clone(),
            page_file_identity: self.page_identity.clone(),
        })
    }

    /// Last local check immediately before a downstream mmap layer maps these same handles.
    ///
    /// This detects local size/identity drift that happened after admission. It cannot prove that an
    /// adversarial process will not mutate/truncate the backing object after mapping; that lifetime
    /// invariant is exactly what BackingFileImmutabilityCapabilityV1 must externally attest.
    pub fn revalidate_opened_identities(&self) -> Result<(), MmapAdmissionErrorV1> {
        let current_node = opened_file_identity(&self.node_index_file)?;
        let current_page = opened_file_identity(&self.page_file)?;
        if current_node != self.node_identity || current_page != self.page_identity {
            return Err(MmapAdmissionErrorV1::FileIdentityChangedBeforeMap);
        }
        Ok(())
    }

    pub fn into_reader(self) -> HandleBoundGenerationReaderV1 {
        HandleBoundGenerationReaderV1 {
            index: self.index,
            page_file: self.page_file,
            binding: self.binding,
        }
    }
}

impl From<std::io::Error> for MmapAdmissionErrorV1 {
    fn from(value: std::io::Error) -> Self {
        Self::Storage(GenerationStorageError::Io(value.to_string()))
    }
}

/// Read+Seek fallback that consumes the exact page handle opened and admitted above.
pub struct HandleBoundGenerationReaderV1 {
    index: HashMap<u64, NodeIndexRecordV1>,
    page_file: File,
    binding: StorageGenerationBindingV1,
}

impl HandleBoundGenerationReaderV1 {
    fn read_bound_page(&mut self, pbn: u64) -> Result<PhysicalPageV1, GenerationStorageError> {
        if pbn >= self.binding.page_count {
            return Err(GenerationStorageError::PageOutOfRange {
                pbn,
                page_count: self.binding.page_count,
            });
        }
        let offset = pbn
            .checked_mul(BLOCK_SIZE as u64)
            .ok_or(GenerationStorageError::LengthOverflow)?;
        self.page_file.seek(SeekFrom::Start(offset))?;
        let mut raw = [0u8; BLOCK_SIZE];
        self.page_file.read_exact(&mut raw)?;
        let page = PhysicalPageV1::decode(&raw)?;
        if page.pbn != pbn {
            return Err(GenerationStorageError::PageNumberMismatch {
                requested: pbn,
                encoded: page.pbn,
            });
        }
        if page.placement_generation != self.binding.placement_generation {
            return Err(GenerationStorageError::PlacementGenerationMismatch {
                expected: self.binding.placement_generation,
                observed: page.placement_generation,
            });
        }
        if page.placement_scheme_digest != self.binding.placement_scheme_digest {
            return Err(GenerationStorageError::PlacementSchemeMismatch);
        }
        Ok(page)
    }

    pub fn query_cone(
        &mut self,
        root_id: u64,
        max_depth: usize,
        max_nodes: usize,
        edge_kind_filter: Option<u8>,
    ) -> Result<HydratedConeV1, GenerationStorageError> {
        if max_nodes == 0 {
            return Err(GenerationStorageError::ConeBudgetExceeded { max_nodes });
        }
        if !self.index.contains_key(&root_id) {
            return Err(GenerationStorageError::MissingRoot(root_id));
        }

        let mut queue = VecDeque::from([(root_id, 0usize)]);
        let mut visited = HashSet::from([root_id]);
        let mut node_ids = Vec::new();
        let mut unique_pages = HashSet::new();
        let mut edges_traversed = 0usize;

        while let Some((node_id, depth)) = queue.pop_front() {
            if node_ids.len() >= max_nodes {
                return Err(GenerationStorageError::ConeBudgetExceeded { max_nodes });
            }
            let record = self
                .index
                .get(&node_id)
                .cloned()
                .ok_or(GenerationStorageError::MissingTarget(node_id))?;
            node_ids.push(node_id);

            if depth >= max_depth || record.out_degree == 0 {
                continue;
            }

            let page = self.read_bound_page(record.pbn)?;
            unique_pages.insert(record.pbn);
            let row_index = record.row as usize;
            if row_index >= page.rows.len() {
                return Err(GenerationStorageError::InvalidRowIndex {
                    node_id,
                    row: row_index,
                    row_count: page.rows.len(),
                });
            }
            let row = page.rows[row_index];
            if row.degree != record.out_degree {
                return Err(GenerationStorageError::NodeDegreeMismatch {
                    node_id,
                    index_degree: record.out_degree,
                    page_degree: row.degree,
                });
            }
            let first = row.first_edge as usize;
            let end = first + row.degree as usize;
            for edge_index in first..end {
                let kind = page.edge_kinds[edge_index];
                if edge_kind_filter.is_some_and(|wanted| kind != wanted) {
                    continue;
                }
                edges_traversed += 1;
                let target = page.targets[edge_index];
                if !self.index.contains_key(&target) {
                    return Err(GenerationStorageError::MissingTarget(target));
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
}

#[cfg(test)]
mod mmap_admission_tests {
    use super::*;
    use std::fs::{remove_file, rename, File, OpenOptions};
    use std::io::Write;
    use std::path::{Path, PathBuf};
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(0);

    fn digest(byte: u8) -> [u8; 32] {
        [byte; 32]
    }

    fn temp_path(label: &str) -> PathBuf {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        std::env::temp_dir().join(format!(
            "aura-k27-astge-v3-{label}-{}-{n}.bin",
            std::process::id()
        ))
    }

    fn node(node_id: u64, pbn: u64, row: u16, degree: u16) -> NodeIndexRecordV1 {
        NodeIndexRecordV1 {
            node_id,
            semantic_handle_digest: digest(node_id as u8),
            pbn,
            row,
            out_degree: degree,
            file_id: 1,
            byte_start: 0,
            byte_end: 0,
        }
    }

    fn binding() -> StorageGenerationBindingV1 {
        StorageGenerationBindingV1 {
            node_count: 2,
            page_count: 1,
            placement_generation: 7,
            placement_scheme_digest: digest(0xA7),
        }
    }

    fn write_fixture(index_path: &Path, page_path: &Path) {
        let mut index = File::create(index_path).unwrap();
        index.write_all(&node(0, 0, 0, 1).encode()).unwrap();
        index.write_all(&node(1, 0, 1, 0).encode()).unwrap();
        index.sync_all().unwrap();

        let page = PhysicalPageV1 {
            pbn: 0,
            placement_generation: 7,
            placement_scheme_digest: digest(0xA7),
            rows: vec![
                PageRow {
                    first_edge: 0,
                    degree: 1,
                },
                PageRow {
                    first_edge: 1,
                    degree: 0,
                },
            ],
            targets: vec![1],
            edge_kinds: vec![0],
        }
        .encode()
        .unwrap();
        let mut pages = File::create(page_path).unwrap();
        pages.write_all(&page).unwrap();
        pages.sync_all().unwrap();
    }

    fn open_fixture() -> (PathBuf, PathBuf, OpenedGenerationFilesV1) {
        let index_path = temp_path("index");
        let page_path = temp_path("pages");
        write_fixture(&index_path, &page_path);
        let opened = OpenedGenerationFilesV1::open(
            &index_path,
            &page_path,
            binding(),
            42,
            digest(0x42),
        )
        .unwrap();
        (index_path, page_path, opened)
    }

    fn capable(opened: &OpenedGenerationFilesV1) -> BackingFileImmutabilityCapabilityV1 {
        BackingFileImmutabilityCapabilityV1 {
            storage_root_identity: digest(0x11),
            snapshot_generation: opened.snapshot_generation(),
            manifest_digest: opened.manifest_digest(),
            node_file_identity: opened.node_file_identity().clone(),
            page_file_identity: opened.page_file_identity().clone(),
            protection: BackingProtectionV1::OwnerIsolatedReplacementOnly {
                policy_digest: digest(0x22),
            },
            external_mutation: ExternalMutationDispositionV1::PreventedForCapabilityLifetime,
        }
    }

    #[test]
    fn read_seek_fallback_works_without_mmap_capability() {
        let (index_path, page_path, opened) = open_fixture();
        let mut reader = opened.into_reader();
        let cone = reader.query_cone(0, 1, 4, None).unwrap();
        assert_eq!(cone.node_ids, vec![0, 1]);
        assert_eq!(cone.edges_traversed, 1);
        let _ = remove_file(index_path);
        let _ = remove_file(page_path);
    }

    #[test]
    fn permission_bits_alone_do_not_admit_mmap() {
        let (index_path, page_path, opened) = open_fixture();
        let mut capability = capable(&opened);
        capability.protection = BackingProtectionV1::PermissionBitsOnly;
        assert_eq!(
            opened.admit_mmap(&capability),
            Err(MmapAdmissionErrorV1::ProtectionInsufficient)
        );
        let _ = remove_file(index_path);
        let _ = remove_file(page_path);
    }

    #[test]
    fn unknown_external_mutation_state_does_not_admit_mmap() {
        let (index_path, page_path, opened) = open_fixture();
        let mut capability = capable(&opened);
        capability.external_mutation = ExternalMutationDispositionV1::Unknown;
        assert_eq!(
            opened.admit_mmap(&capability),
            Err(MmapAdmissionErrorV1::ExternalMutationNotPrevented)
        );
        let _ = remove_file(index_path);
        let _ = remove_file(page_path);
    }

    #[test]
    fn exact_open_file_identity_and_external_capability_admit_mmap_token() {
        let (index_path, page_path, opened) = open_fixture();
        let capability = capable(&opened);
        let token = opened.admit_mmap(&capability).unwrap();
        assert_eq!(token.snapshot_generation, 42);
        assert_eq!(token.node_file_identity, *opened.node_file_identity());
        assert_eq!(token.page_file_identity, *opened.page_file_identity());
        let _ = remove_file(index_path);
        let _ = remove_file(page_path);
    }

    #[test]
    fn manifest_and_snapshot_generation_must_match_exactly() {
        let (index_path, page_path, opened) = open_fixture();
        let mut capability = capable(&opened);
        capability.snapshot_generation = 43;
        assert_eq!(
            opened.admit_mmap(&capability),
            Err(MmapAdmissionErrorV1::SnapshotGenerationMismatch {
                expected: 42,
                observed: 43,
            })
        );
        capability = capable(&opened);
        capability.manifest_digest = digest(0x99);
        assert_eq!(
            opened.admit_mmap(&capability),
            Err(MmapAdmissionErrorV1::ManifestDigestMismatch)
        );
        let _ = remove_file(index_path);
        let _ = remove_file(page_path);
    }

    #[test]
    fn capability_cannot_substitute_another_opened_file_identity() {
        let (index_path, page_path, opened) = open_fixture();
        let mut capability = capable(&opened);
        capability.node_file_identity = opened.page_file_identity().clone();
        assert_eq!(
            opened.admit_mmap(&capability),
            Err(MmapAdmissionErrorV1::NodeFileIdentityMismatch)
        );
        let _ = remove_file(index_path);
        let _ = remove_file(page_path);
    }

    #[cfg(unix)]
    #[test]
    fn path_replacement_after_open_cannot_redirect_handle_bound_reader() {
        let (index_path, page_path, opened) = open_fixture();
        let replacement_backup = temp_path("pages-old");
        rename(&page_path, &replacement_backup).unwrap();
        File::create(&page_path)
            .unwrap()
            .write_all(&vec![0u8; BLOCK_SIZE])
            .unwrap();

        // The reader consumes the already-open original page handle, not the replacement path.
        let mut reader = opened.into_reader();
        let cone = reader.query_cone(0, 1, 4, None).unwrap();
        assert_eq!(cone.node_ids, vec![0, 1]);
        assert_eq!(cone.edges_traversed, 1);

        let _ = remove_file(index_path);
        let _ = remove_file(page_path);
        let _ = remove_file(replacement_backup);
    }

    #[cfg(unix)]
    #[test]
    fn post_open_truncation_is_detected_before_mapping() {
        let (index_path, page_path, opened) = open_fixture();
        OpenOptions::new()
            .write(true)
            .open(&page_path)
            .unwrap()
            .set_len(0)
            .unwrap();
        assert_eq!(
            opened.revalidate_opened_identities(),
            Err(MmapAdmissionErrorV1::FileIdentityChangedBeforeMap)
        );
        let _ = remove_file(index_path);
        let _ = remove_file(page_path);
    }
}