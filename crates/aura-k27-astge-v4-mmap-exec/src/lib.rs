use aura_k27_astge::{
    admit_data_serving_backend_v2, BackendAdmissionReasonV2, DataServingBackendAdmissionV2,
    DataServingBackendV2, GenerationBoundGraphReader, GenerationStorageError, HydratedConeV1,
    MmapAdmissionErrorV2, MmapBackendAdmissionReceiptV2, MmapCandidateLeaseV2, NodeIndexRecordV1,
    PageSource, PhysicalPageV1, SPlaneGraphReader, StorageError, StorageGenerationBindingV1,
    BLOCK_SIZE, NODE_INDEX_RECORD_SIZE,
};
use memmap2::{Mmap, MmapOptions};
use std::error::Error;
use std::fmt::{Display, Formatter};
use std::fs::File;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum V4ExecutionError {
    Admission(MmapAdmissionErrorV2),
    ReadSeek(GenerationStorageError),
    Mmap(StorageError),
    ReceiptIncoherent,
    ZeroLengthMapping,
}

impl Display for V4ExecutionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}
impl Error for V4ExecutionError {}
impl From<MmapAdmissionErrorV2> for V4ExecutionError {
    fn from(value: MmapAdmissionErrorV2) -> Self {
        Self::Admission(value)
    }
}
impl From<GenerationStorageError> for V4ExecutionError {
    fn from(value: GenerationStorageError) -> Self {
        Self::ReadSeek(value)
    }
}
impl From<StorageError> for V4ExecutionError {
    fn from(value: StorageError) -> Self {
        Self::Mmap(value)
    }
}

pub enum CanonicalDataServingReaderV2 {
    ReadSeek {
        receipt: MmapBackendAdmissionReceiptV2,
        reader: GenerationBoundGraphReader,
    },
    Mmap {
        receipt: MmapBackendAdmissionReceiptV2,
        reader: LeaseBoundMmapReaderV2,
    },
}

impl CanonicalDataServingReaderV2 {
    pub fn receipt(&self) -> &MmapBackendAdmissionReceiptV2 {
        match self {
            Self::ReadSeek { receipt, .. } | Self::Mmap { receipt, .. } => receipt,
        }
    }

    pub fn backend(&self) -> DataServingBackendV2 {
        self.receipt().backend
    }

    pub fn query_cone(
        &mut self,
        root_id: u64,
        max_depth: usize,
        max_nodes: usize,
        edge_kind_filter: Option<u8>,
    ) -> Result<HydratedConeV1, V4ExecutionError> {
        match self {
            Self::ReadSeek { reader, .. } => reader
                .query_cone(root_id, max_depth, max_nodes, edge_kind_filter)
                .map_err(V4ExecutionError::ReadSeek),
            Self::Mmap { reader, .. } => reader
                .query_cone(root_id, max_depth, max_nodes, edge_kind_filter)
                .map_err(V4ExecutionError::Mmap),
        }
    }
}

/// Canonical V4 execution boundary.
///
/// Callers provide current paths plus independent snapshot and placement inputs only.
/// They cannot provide a capability, registry, lease, opened File, trust flag, or mmap token.
/// Production therefore stays on ReadSeekSafeDefault while PR489's V4 registry is empty.
pub fn open_canonical_data_serving_reader_v2(
    storage_root: impl AsRef<Path>,
    node_index_path: impl AsRef<Path>,
    page_path: impl AsRef<Path>,
    binding: StorageGenerationBindingV1,
    snapshot_generation: u64,
    manifest_digest: [u8; 32],
) -> Result<CanonicalDataServingReaderV2, V4ExecutionError> {
    let storage_root: PathBuf = storage_root.as_ref().to_path_buf();
    let node_index_path: PathBuf = node_index_path.as_ref().to_path_buf();
    let page_path: PathBuf = page_path.as_ref().to_path_buf();
    let admission = admit_data_serving_backend_v2(
        &storage_root,
        &node_index_path,
        &page_path,
        &binding,
        snapshot_generation,
        manifest_digest,
    )?;

    match admission {
        DataServingBackendAdmissionV2::ReadSeekSafeDefault(receipt) => {
            require_safe_receipt(&receipt, snapshot_generation, binding.placement_generation)?;
            let reader = GenerationBoundGraphReader::open(&node_index_path, &page_path, binding)?;
            Ok(CanonicalDataServingReaderV2::ReadSeek { receipt, reader })
        }
        DataServingBackendAdmissionV2::MmapCapabilityGated(lease) => {
            let receipt = *lease.receipt();
            let reader = LeaseBoundMmapReaderV2::from_lease(lease, binding)?;
            Ok(CanonicalDataServingReaderV2::Mmap { receipt, reader })
        }
    }
}

fn require_safe_receipt(
    receipt: &MmapBackendAdmissionReceiptV2,
    snapshot_generation: u64,
    placement_generation: u64,
) -> Result<(), V4ExecutionError> {
    if receipt.backend != DataServingBackendV2::ReadSeekSafeDefault
        || receipt.snapshot_generation != snapshot_generation
        || receipt.placement_generation != placement_generation
        || receipt.human_authority
        || receipt.external_effect
    {
        return Err(V4ExecutionError::ReceiptIncoherent);
    }
    Ok(())
}

fn require_positive_receipt(
    receipt: &MmapBackendAdmissionReceiptV2,
    binding: &StorageGenerationBindingV1,
) -> Result<(), V4ExecutionError> {
    if receipt.backend != DataServingBackendV2::MmapCapabilityGated
        || receipt.reason != BackendAdmissionReasonV2::CapabilityExactUnique
        || receipt.capability_ref.is_none()
        || receipt.placement_generation != binding.placement_generation
        || !receipt.snapshot_generation_independently_bound
        || !receipt.placement_generation_independently_bound
        || !receipt.exact_opened_file_identity_bound
        || !receipt.final_handle_revalidation_passed
        || !receipt.replacement_generations_only_proven
        || !receipt.no_in_place_mutation_proven
        || !receipt.mapped_lifetime_bounded
        || receipt.human_authority
        || receipt.external_effect
    {
        return Err(V4ExecutionError::ReceiptIncoherent);
    }
    Ok(())
}

struct BoundMmapPagesV2 {
    mmap: Mmap,
    binding: StorageGenerationBindingV1,
}

impl PageSource for BoundMmapPagesV2 {
    fn read_page(&mut self, pbn: u64) -> Result<[u8; BLOCK_SIZE], StorageError> {
        if pbn >= self.binding.page_count {
            return Err(StorageError::Io("PAGE_OUT_OF_RANGE".to_string()));
        }
        let offset = usize::try_from(pbn)
            .map_err(|_| StorageError::Io("PAGE_OFFSET_OVERFLOW".to_string()))?
            .checked_mul(BLOCK_SIZE)
            .ok_or_else(|| StorageError::Io("PAGE_OFFSET_OVERFLOW".to_string()))?;
        let end = offset
            .checked_add(BLOCK_SIZE)
            .ok_or_else(|| StorageError::Io("PAGE_OFFSET_OVERFLOW".to_string()))?;
        let raw: [u8; BLOCK_SIZE] = self.mmap[offset..end]
            .try_into()
            .map_err(|_| StorageError::Io("PAGE_LENGTH_MISMATCH".to_string()))?;
        let page = PhysicalPageV1::decode(&raw)?;
        if page.pbn != pbn {
            return Err(StorageError::PageNumberMismatch {
                requested: pbn,
                encoded: page.pbn,
            });
        }
        if page.placement_generation != self.binding.placement_generation {
            return Err(StorageError::Io(
                "PLACEMENT_GENERATION_MISMATCH".to_string(),
            ));
        }
        if page.placement_scheme_digest != self.binding.placement_scheme_digest {
            return Err(StorageError::Io("PLACEMENT_SCHEME_MISMATCH".to_string()));
        }
        Ok(raw)
    }
}

pub struct LeaseBoundMmapReaderV2 {
    _node_mmap: Mmap,
    reader: SPlaneGraphReader<BoundMmapPagesV2>,
}

impl LeaseBoundMmapReaderV2 {
    /// The sole public mmap constructor consumes PR489's opaque V4 lease.
    /// External code cannot manufacture that lease because its fields are private.
    pub fn from_lease(
        lease: MmapCandidateLeaseV2,
        binding: StorageGenerationBindingV1,
    ) -> Result<Self, V4ExecutionError> {
        let receipt = *lease.receipt();
        require_positive_receipt(&receipt, &binding)?;
        let (node_file, page_file) = lease.into_verified_files()?;
        map_verified_files(node_file, page_file, binding)
    }

    pub fn query_cone(
        &mut self,
        root_id: u64,
        max_depth: usize,
        max_nodes: usize,
        edge_kind_filter: Option<u8>,
    ) -> Result<HydratedConeV1, StorageError> {
        self.reader
            .query_cone(root_id, max_depth, max_nodes, edge_kind_filter)
    }
}

fn map_verified_files(
    node_file: File,
    page_file: File,
    binding: StorageGenerationBindingV1,
) -> Result<LeaseBoundMmapReaderV2, V4ExecutionError> {
    let expected_nodes = exact_len(binding.node_count, NODE_INDEX_RECORD_SIZE)?;
    let expected_pages = exact_len(binding.page_count, BLOCK_SIZE)?;
    let node_len = node_file
        .metadata()
        .map_err(|error| StorageError::Io(error.to_string()))?
        .len();
    let page_len = page_file
        .metadata()
        .map_err(|error| StorageError::Io(error.to_string()))?
        .len();
    if node_len != expected_nodes {
        return Err(GenerationStorageError::NodeIndexLengthMismatch {
            expected: expected_nodes,
            actual: node_len,
        }
        .into());
    }
    if page_len != expected_pages {
        return Err(GenerationStorageError::PageFileLengthMismatch {
            expected: expected_pages,
            actual: page_len,
        }
        .into());
    }
    if expected_nodes == 0 || expected_pages == 0 {
        return Err(V4ExecutionError::ZeroLengthMapping);
    }

    // SAFETY: the public mmap path reaches this helper only after PR489 mints an opaque lease and
    // `into_verified_files()` revalidates the same opened handles at handoff. PR489's source-owned
    // capability owns replacement-only/no-in-place-mutation and bounded-lifetime assertions.
    // This crate does not generalize those conditions into intrinsic mmap safety.
    let node_mmap = unsafe {
        MmapOptions::new()
            .map(&node_file)
            .map_err(|error| StorageError::Io(error.to_string()))?
    };
    // SAFETY: same exact-handle and source-owned lifetime invariant as the node map above.
    let page_mmap = unsafe {
        MmapOptions::new()
            .map(&page_file)
            .map_err(|error| StorageError::Io(error.to_string()))?
    };

    let records = decode_records(&node_mmap, &binding)?;
    let pages = BoundMmapPagesV2 {
        mmap: page_mmap,
        binding,
    };
    let reader = SPlaneGraphReader::new(records, pages)?;
    Ok(LeaseBoundMmapReaderV2 {
        _node_mmap: node_mmap,
        reader,
    })
}

fn decode_records(
    bytes: &[u8],
    binding: &StorageGenerationBindingV1,
) -> Result<Vec<NodeIndexRecordV1>, V4ExecutionError> {
    let expected = exact_len(binding.node_count, NODE_INDEX_RECORD_SIZE)?;
    if bytes.len() as u64 != expected {
        return Err(GenerationStorageError::NodeIndexLengthMismatch {
            expected,
            actual: bytes.len() as u64,
        }
        .into());
    }
    let mut records = Vec::with_capacity(binding.node_count as usize);
    for chunk in bytes.as_chunks::<NODE_INDEX_RECORD_SIZE>().0 {
        let record = NodeIndexRecordV1::decode(chunk)?;
        if record.pbn >= binding.page_count {
            return Err(GenerationStorageError::IndexPageOutOfRange {
                node_id: record.node_id,
                pbn: record.pbn,
                page_count: binding.page_count,
            }
            .into());
        }
        records.push(record);
    }
    Ok(records)
}

fn exact_len(count: u64, width: usize) -> Result<u64, GenerationStorageError> {
    count
        .checked_mul(width as u64)
        .ok_or(GenerationStorageError::LengthOverflow)
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge::{PageRow, PhysicalPageV1};
    use std::fs;
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(1);

    fn root(label: &str) -> PathBuf {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "aura-k27-v4-mmap-exec-{label}-{}-{n}",
            std::process::id()
        ));
        fs::create_dir(&path).unwrap();
        path
    }

    fn fixture(root: &Path) -> (StorageGenerationBindingV1, PathBuf, PathBuf) {
        let binding = StorageGenerationBindingV1 {
            node_count: 3,
            page_count: 1,
            placement_generation: 7,
            placement_scheme_digest: [0x31; 32],
        };
        let records = [
            NodeIndexRecordV1 {
                node_id: 0,
                semantic_handle_digest: [0x10; 32],
                pbn: 0,
                row: 0,
                out_degree: 2,
                file_id: 1,
                byte_start: 0,
                byte_end: 1,
            },
            NodeIndexRecordV1 {
                node_id: 1,
                semantic_handle_digest: [0x11; 32],
                pbn: 0,
                row: 1,
                out_degree: 0,
                file_id: 1,
                byte_start: 1,
                byte_end: 2,
            },
            NodeIndexRecordV1 {
                node_id: 2,
                semantic_handle_digest: [0x12; 32],
                pbn: 0,
                row: 2,
                out_degree: 0,
                file_id: 1,
                byte_start: 2,
                byte_end: 3,
            },
        ];
        let mut index = Vec::new();
        for record in records {
            index.extend_from_slice(&record.encode());
        }
        let page = PhysicalPageV1 {
            pbn: 0,
            placement_generation: 7,
            placement_scheme_digest: [0x31; 32],
            rows: vec![
                PageRow {
                    first_edge: 0,
                    degree: 2,
                },
                PageRow {
                    first_edge: 2,
                    degree: 0,
                },
                PageRow {
                    first_edge: 2,
                    degree: 0,
                },
            ],
            targets: vec![1, 2],
            edge_kinds: vec![0, 0],
        };
        let node = root.join("nodes.idx");
        let pages = root.join("pages.bin");
        fs::write(&node, index).unwrap();
        fs::write(&pages, page.encode().unwrap()).unwrap();
        (binding, node, pages)
    }

    #[test]
    fn production_route_remains_readseek_without_source_owned_capability() {
        let root = root("safe-default");
        let (binding, node, pages) = fixture(&root);
        let mut reader =
            open_canonical_data_serving_reader_v2(&root, &node, &pages, binding, 41, [0x44; 32])
                .unwrap();
        assert_eq!(reader.backend(), DataServingBackendV2::ReadSeekSafeDefault);
        assert_eq!(
            reader.receipt().reason,
            BackendAdmissionReasonV2::CapabilityUnavailable
        );
        let cone = reader.query_cone(0, 1, 10, None).unwrap();
        assert_eq!(cone.node_ids, vec![0, 1, 2]);
        assert_eq!(cone.edges_traversed, 2);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn verified_file_mapper_is_readseek_equivalent_on_same_bytes() {
        let root = root("mapper-equivalence");
        let (binding, node, pages) = fixture(&root);
        let mut safe = GenerationBoundGraphReader::open(&node, &pages, binding.clone()).unwrap();
        let expected = safe.query_cone(0, 2, 10, None).unwrap();
        let mut mapped = map_verified_files(
            File::open(&node).unwrap(),
            File::open(&pages).unwrap(),
            binding,
        )
        .unwrap();
        let observed = mapped.query_cone(0, 2, 10, None).unwrap();
        assert_eq!(observed, expected);
        fs::remove_dir_all(root).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn mapper_has_no_path_reopen_dependency_after_handles_exist() {
        let root = root("no-reopen");
        let (binding, node, pages) = fixture(&root);
        let node_file = File::open(&node).unwrap();
        let page_file = File::open(&pages).unwrap();
        fs::rename(&node, root.join("nodes.old")).unwrap();
        fs::rename(&pages, root.join("pages.old")).unwrap();
        let mut mapped = map_verified_files(node_file, page_file, binding).unwrap();
        assert_eq!(
            mapped.query_cone(0, 1, 10, None).unwrap().node_ids,
            vec![0, 1, 2]
        );
        fs::remove_dir_all(root).unwrap();
    }
}
