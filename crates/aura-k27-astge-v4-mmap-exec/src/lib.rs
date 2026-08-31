use aura_k27_astge::{
    admit_data_serving_backend_v2, BackendAdmissionReasonV2, DataServingBackendAdmissionV2,
    DataServingBackendV2, GenerationBoundGraphReader, GenerationStorageError, HydratedConeV1,
    MmapAdmissionErrorV2, MmapBackendAdmissionReceiptV2, MmapCandidateLeaseV2, NodeIndexRecordV1,
    PhysicalPageV1, StorageGenerationBindingV1, BLOCK_SIZE, NODE_INDEX_RECORD_SIZE,
};
use memmap2::{Mmap, MmapOptions};
use std::collections::{HashMap, HashSet, VecDeque};
use std::error::Error;
use std::fmt::{Display, Formatter};
use std::fs::File;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum V4ExecutionError {
    Admission(MmapAdmissionErrorV2),
    Storage(GenerationStorageError),
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
        Self::Storage(value)
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
                .map_err(Into::into),
            Self::Mmap { reader, .. } => reader
                .query_cone(root_id, max_depth, max_nodes, edge_kind_filter)
                .map_err(Into::into),
        }
    }
}

/// Canonical V4 execution boundary.
///
/// Callers provide current paths + the independent snapshot and placement binding inputs only.
/// They cannot provide a capability, registry, lease, trusted boolean, opened file or mmap token.
/// Production therefore remains ReadSeekSafeDefault while the V4 source-owned registry is empty.
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

pub struct LeaseBoundMmapReaderV2 {
    binding: StorageGenerationBindingV1,
    index: HashMap<u64, NodeIndexRecordV1>,
    _node_mmap: Mmap,
    pages_mmap: Mmap,
}

impl LeaseBoundMmapReaderV2 {
    /// The only public mmap constructor consumes the opaque V4 lease. External code cannot
    /// manufacture that lease because PR489 keeps its fields private and owns the sole minting path.
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
        &self,
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

            let page = self.decode_page(record.pbn)?;
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

    fn decode_page(&self, pbn: u64) -> Result<PhysicalPageV1, GenerationStorageError> {
        if pbn >= self.binding.page_count {
            return Err(GenerationStorageError::PageOutOfRange {
                pbn,
                page_count: self.binding.page_count,
            });
        }
        let offset = usize::try_from(pbn)
            .map_err(|_| GenerationStorageError::LengthOverflow)?
            .checked_mul(BLOCK_SIZE)
            .ok_or(GenerationStorageError::LengthOverflow)?;
        let end = offset
            .checked_add(BLOCK_SIZE)
            .ok_or(GenerationStorageError::LengthOverflow)?;
        let raw: [u8; BLOCK_SIZE] = self.pages_mmap[offset..end]
            .try_into()
            .map_err(|_| GenerationStorageError::PageFileLengthMismatch {
                expected: exact_len(self.binding.page_count, BLOCK_SIZE)?,
                actual: self.pages_mmap.len() as u64,
            })?;
        let page = PhysicalPageV1::decode(&raw)?;
        bind_page(&page, pbn, &self.binding)?;
        Ok(page)
    }
}

fn map_verified_files(
    node_file: File,
    page_file: File,
    binding: StorageGenerationBindingV1,
) -> Result<LeaseBoundMmapReaderV2, V4ExecutionError> {
    let expected_nodes = exact_len(binding.node_count, NODE_INDEX_RECORD_SIZE)?;
    let expected_pages = exact_len(binding.page_count, BLOCK_SIZE)?;
    let node_len = node_file.metadata()?.len();
    let page_len = page_file.metadata()?.len();
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

    // SAFETY: the public mmap path can reach this point only after consuming a V4 opaque lease.
    // `into_verified_files()` performs the final same-handle identity revalidation immediately
    // before transfer. PR489's source-owned capability owns replacement-only/no-in-place-mutation
    // and mapped-lifetime assertions. This crate does not generalize that into intrinsic mmap safety.
    let node_mmap = unsafe { MmapOptions::new().map(&node_file)? };
    // SAFETY: same exact-handle / source-owned lifetime invariant as the node mapping above.
    let pages_mmap = unsafe { MmapOptions::new().map(&page_file)? };
    let index = decode_index(&node_mmap, &binding)?;
    Ok(LeaseBoundMmapReaderV2 {
        binding,
        index,
        _node_mmap: node_mmap,
        pages_mmap,
    })
}

fn decode_index(
    bytes: &[u8],
    binding: &StorageGenerationBindingV1,
) -> Result<HashMap<u64, NodeIndexRecordV1>, GenerationStorageError> {
    let expected = exact_len(binding.node_count, NODE_INDEX_RECORD_SIZE)?;
    if bytes.len() as u64 != expected {
        return Err(GenerationStorageError::NodeIndexLengthMismatch {
            expected,
            actual: bytes.len() as u64,
        });
    }
    let mut out = HashMap::with_capacity(binding.node_count as usize);
    for chunk in bytes.chunks_exact(NODE_INDEX_RECORD_SIZE) {
        let raw: &[u8; NODE_INDEX_RECORD_SIZE] = chunk
            .try_into()
            .map_err(|_| GenerationStorageError::NodeIndexLengthMismatch {
                expected,
                actual: bytes.len() as u64,
            })?;
        let record = NodeIndexRecordV1::decode(raw)?;
        if record.pbn >= binding.page_count {
            return Err(GenerationStorageError::IndexPageOutOfRange {
                node_id: record.node_id,
                pbn: record.pbn,
                page_count: binding.page_count,
            });
        }
        let node_id = record.node_id;
        if out.insert(node_id, record).is_some() {
            return Err(GenerationStorageError::DuplicateNodeId(node_id));
        }
    }
    Ok(out)
}

fn bind_page(
    page: &PhysicalPageV1,
    pbn: u64,
    binding: &StorageGenerationBindingV1,
) -> Result<(), GenerationStorageError> {
    if page.pbn != pbn {
        return Err(GenerationStorageError::PageNumberMismatch {
            requested: pbn,
            encoded: page.pbn,
        });
    }
    if page.placement_generation != binding.placement_generation {
        return Err(GenerationStorageError::PlacementGenerationMismatch {
            expected: binding.placement_generation,
            observed: page.placement_generation,
        });
    }
    if page.placement_scheme_digest != binding.placement_scheme_digest {
        return Err(GenerationStorageError::PlacementSchemeMismatch);
    }
    Ok(())
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
        let mut reader = open_canonical_data_serving_reader_v2(
            &root,
            &node,
            &pages,
            binding,
            41,
            [0x44; 32],
        )
        .unwrap();
        assert_eq!(reader.backend(), DataServingBackendV2::ReadSeekSafeDefault);
        assert_eq!(reader.receipt().reason, BackendAdmissionReasonV2::CapabilityUnavailable);
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
        let mapped = map_verified_files(File::open(&node).unwrap(), File::open(&pages).unwrap(), binding).unwrap();
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
        let mapped = map_verified_files(node_file, page_file, binding).unwrap();
        assert_eq!(mapped.query_cone(0, 1, 10, None).unwrap().node_ids, vec![0, 1, 2]);
        fs::remove_dir_all(root).unwrap();
    }
}
