use aura_k27_astge::{
    admit_data_serving_backend, BackendAdmissionReasonV1, DataServingBackendAdmissionV1,
    DataServingBackendV1, GenerationBoundGraphReader, GenerationStorageError, HydratedConeV1,
    MmapAdmissionError, MmapBackendAdmissionReceiptV1, NodeIndexRecordV1, PhysicalPageV1,
    StorageGenerationBindingV1, BLOCK_SIZE, NODE_INDEX_RECORD_SIZE,
};
use memmap2::{Mmap, MmapOptions};
use std::collections::{HashMap, HashSet, VecDeque};
use std::error::Error;
use std::fmt::{Display, Formatter};
use std::fs::File;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DataServingExecutionErrorV1 {
    Admission(MmapAdmissionError),
    Storage(GenerationStorageError),
    AdmissionReceiptIncoherent,
    ZeroLengthMmapUnsupported,
}

impl Display for DataServingExecutionErrorV1 {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for DataServingExecutionErrorV1 {}

impl From<MmapAdmissionError> for DataServingExecutionErrorV1 {
    fn from(value: MmapAdmissionError) -> Self {
        Self::Admission(value)
    }
}

impl From<GenerationStorageError> for DataServingExecutionErrorV1 {
    fn from(value: GenerationStorageError) -> Self {
        Self::Storage(value)
    }
}

/// Runtime reader selected only through the PR472 source-owned admission boundary.
///
/// There is intentionally no public constructor that accepts a capability record, a trusted
/// boolean, a pre-opened File, or a pre-built admission enum. Production callers can only provide
/// current storage paths/binding/manifest identity to `open_data_serving_reader`.
pub enum DataServingReaderV1 {
    ReadSeek {
        receipt: MmapBackendAdmissionReceiptV1,
        reader: GenerationBoundGraphReader,
    },
    Mmap {
        receipt: MmapBackendAdmissionReceiptV1,
        reader: ExactHandleMmapReaderV1,
    },
}

impl DataServingReaderV1 {
    pub fn receipt(&self) -> &MmapBackendAdmissionReceiptV1 {
        match self {
            Self::ReadSeek { receipt, .. } | Self::Mmap { receipt, .. } => receipt,
        }
    }

    pub fn backend(&self) -> DataServingBackendV1 {
        self.receipt().backend
    }

    pub fn query_cone(
        &mut self,
        root_id: u64,
        max_depth: usize,
        max_nodes: usize,
        edge_kind_filter: Option<u8>,
    ) -> Result<HydratedConeV1, DataServingExecutionErrorV1> {
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

/// Canonical execution boundary.
///
/// PR472 decides eligibility from its source-owned capability registry. When capability state is
/// absent/ambiguous/invalid, this function stays on the generation-bound Read+Seek baseline. Only a
/// positive PR472 result reaches the unsafe sibling mapper, and the mapper consumes the exact File
/// handles returned by that result. No positive path-based reopen exists here.
pub fn open_data_serving_reader(
    storage_root: impl AsRef<Path>,
    node_index_path: impl AsRef<Path>,
    page_path: impl AsRef<Path>,
    binding: StorageGenerationBindingV1,
    manifest_digest: [u8; 32],
) -> Result<DataServingReaderV1, DataServingExecutionErrorV1> {
    let storage_root: PathBuf = storage_root.as_ref().to_path_buf();
    let node_index_path: PathBuf = node_index_path.as_ref().to_path_buf();
    let page_path: PathBuf = page_path.as_ref().to_path_buf();

    let admission = admit_data_serving_backend(
        &storage_root,
        &node_index_path,
        &page_path,
        &binding,
        manifest_digest,
    )?;

    match admission {
        DataServingBackendAdmissionV1::ReadSeekSafeDefault(receipt) => {
            if receipt.backend != DataServingBackendV1::ReadSeekSafeDefault
                || receipt.human_authority
                || receipt.external_effect
            {
                return Err(DataServingExecutionErrorV1::AdmissionReceiptIncoherent);
            }
            let reader = GenerationBoundGraphReader::open(
                &node_index_path,
                &page_path,
                binding,
            )?;
            Ok(DataServingReaderV1::ReadSeek { receipt, reader })
        }
        DataServingBackendAdmissionV1::MmapCapabilityGated {
            receipt,
            node_file,
            page_file,
        } => {
            let reader = map_exact_admitted_handles(receipt, node_file, page_file, binding)?;
            Ok(DataServingReaderV1::Mmap { receipt, reader })
        }
    }
}

pub struct ExactHandleMmapReaderV1 {
    binding: StorageGenerationBindingV1,
    index: HashMap<u64, NodeIndexRecordV1>,
    _node_mmap: Mmap,
    pages_mmap: Mmap,
}

impl ExactHandleMmapReaderV1 {
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

            let page = self.decode_bound_page(record.pbn)?;
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

    fn decode_bound_page(&self, pbn: u64) -> Result<PhysicalPageV1, GenerationStorageError> {
        if pbn >= self.binding.page_count {
            return Err(GenerationStorageError::PageOutOfRange {
                pbn,
                page_count: self.binding.page_count,
            });
        }
        let pbn_usize = usize::try_from(pbn).map_err(|_| GenerationStorageError::LengthOverflow)?;
        let offset = pbn_usize
            .checked_mul(BLOCK_SIZE)
            .ok_or(GenerationStorageError::LengthOverflow)?;
        let end = offset
            .checked_add(BLOCK_SIZE)
            .ok_or(GenerationStorageError::LengthOverflow)?;
        let raw: [u8; BLOCK_SIZE] = self.pages_mmap[offset..end]
            .try_into()
            .map_err(|_| GenerationStorageError::PageFileLengthMismatch {
                expected: expected_len(self.binding.page_count, BLOCK_SIZE)?,
                actual: self.pages_mmap.len() as u64,
            })?;
        let page = PhysicalPageV1::decode(&raw).map_err(GenerationStorageError::from)?;
        bind_page(&page, pbn, &self.binding)?;
        Ok(page)
    }
}

fn map_exact_admitted_handles(
    receipt: MmapBackendAdmissionReceiptV1,
    node_file: File,
    page_file: File,
    binding: StorageGenerationBindingV1,
) -> Result<ExactHandleMmapReaderV1, DataServingExecutionErrorV1> {
    require_positive_receipt(&receipt)?;

    let expected_nodes = expected_len(binding.node_count, NODE_INDEX_RECORD_SIZE)?;
    let expected_pages = expected_len(binding.page_count, BLOCK_SIZE)?;
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
        return Err(DataServingExecutionErrorV1::ZeroLengthMmapUnsupported);
    }

    // SAFETY: the only production caller is `open_data_serving_reader`, which reaches this helper
    // only after PR472 has selected one exact source-owned capability and transferred the exact
    // already-opened File handles whose identities it verified. The capability itself owns the
    // replacement-only/no-in-place-mutation and bounded mapped-lifetime assertions. This crate does
    // not claim that mmap is intrinsically safe outside that admitted lifetime.
    let node_mmap = unsafe {
        MmapOptions::new()
            .map(&node_file)
            .map_err(|error| GenerationStorageError::Io(error.to_string()))?
    };
    // SAFETY: same exact-handle and externally owned lifetime invariant as the node mapping above.
    let pages_mmap = unsafe {
        MmapOptions::new()
            .map(&page_file)
            .map_err(|error| GenerationStorageError::Io(error.to_string()))?
    };

    let index = load_index_from_mmap(&node_mmap, &binding)?;
    Ok(ExactHandleMmapReaderV1 {
        binding,
        index,
        _node_mmap: node_mmap,
        pages_mmap,
    })
}

fn require_positive_receipt(
    receipt: &MmapBackendAdmissionReceiptV1,
) -> Result<(), DataServingExecutionErrorV1> {
    if receipt.backend != DataServingBackendV1::MmapCapabilityGated
        || receipt.reason != BackendAdmissionReasonV1::CapabilityExactUnique
        || receipt.capability_ref.is_none()
        || !receipt.exact_opened_file_identity_bound
        || !receipt.replacement_generations_only_proven
        || !receipt.no_in_place_mutation_proven
        || !receipt.mapped_lifetime_bounded
        || receipt.human_authority
        || receipt.external_effect
    {
        return Err(DataServingExecutionErrorV1::AdmissionReceiptIncoherent);
    }
    Ok(())
}

fn load_index_from_mmap(
    bytes: &[u8],
    binding: &StorageGenerationBindingV1,
) -> Result<HashMap<u64, NodeIndexRecordV1>, GenerationStorageError> {
    let expected = expected_len(binding.node_count, NODE_INDEX_RECORD_SIZE)?;
    if bytes.len() as u64 != expected {
        return Err(GenerationStorageError::NodeIndexLengthMismatch {
            expected,
            actual: bytes.len() as u64,
        });
    }
    if binding.node_count > 0 && binding.page_count == 0 {
        return Err(GenerationStorageError::IndexPageOutOfRange {
            node_id: 0,
            pbn: 0,
            page_count: 0,
        });
    }

    let mut index = HashMap::with_capacity(binding.node_count as usize);
    let mut chunks = bytes.chunks_exact(NODE_INDEX_RECORD_SIZE);
    for raw in &mut chunks {
        let record = NodeIndexRecordV1::decode(raw).map_err(GenerationStorageError::from)?;
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
    if !chunks.remainder().is_empty() {
        return Err(GenerationStorageError::NodeIndexLengthMismatch {
            expected,
            actual: bytes.len() as u64,
        });
    }
    Ok(index)
}

fn bind_page(
    page: &PhysicalPageV1,
    requested: u64,
    binding: &StorageGenerationBindingV1,
) -> Result<(), GenerationStorageError> {
    if page.pbn != requested {
        return Err(GenerationStorageError::PageNumberMismatch {
            requested,
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

fn expected_len(count: u64, width: usize) -> Result<u64, GenerationStorageError> {
    count
        .checked_mul(width as u64)
        .ok_or(GenerationStorageError::LengthOverflow)
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge::{PageRow, PhysicalPageV1};
    use std::fs::{self, File};
    use std::sync::atomic::{AtomicU64, Ordering};

    static NONCE: AtomicU64 = AtomicU64::new(1);

    fn temp_root(label: &str) -> PathBuf {
        let id = NONCE.fetch_add(1, Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "aura-k27-astge-mmap-exec-{label}-{}-{id}",
            std::process::id()
        ));
        fs::create_dir(&path).expect("create temp root");
        path
    }

    fn fixture_bytes() -> (StorageGenerationBindingV1, Vec<u8>, Vec<u8>) {
        let scheme = [0x31_u8; 32];
        let binding = StorageGenerationBindingV1 {
            node_count: 3,
            page_count: 1,
            placement_generation: 7,
            placement_scheme_digest: scheme,
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
        let mut index_bytes = Vec::new();
        for record in records {
            index_bytes.extend_from_slice(&record.encode());
        }
        let page = PhysicalPageV1 {
            pbn: 0,
            placement_generation: binding.placement_generation,
            placement_scheme_digest: binding.placement_scheme_digest,
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
        let page_bytes = page.encode().expect("encode page").to_vec();
        (binding, index_bytes, page_bytes)
    }

    fn write_fixture(root: &Path) -> (StorageGenerationBindingV1, PathBuf, PathBuf) {
        let (binding, index_bytes, page_bytes) = fixture_bytes();
        let node_path = root.join("node-index.bin");
        let page_path = root.join("pages.bin");
        fs::write(&node_path, index_bytes).expect("write index");
        fs::write(&page_path, page_bytes).expect("write pages");
        (binding, node_path, page_path)
    }

    fn positive_receipt() -> MmapBackendAdmissionReceiptV1 {
        MmapBackendAdmissionReceiptV1 {
            backend: DataServingBackendV1::MmapCapabilityGated,
            reason: BackendAdmissionReasonV1::CapabilityExactUnique,
            capability_ref: Some("TEST_ONLY_EXTERNAL_CAPABILITY"),
            exact_opened_file_identity_bound: true,
            replacement_generations_only_proven: true,
            no_in_place_mutation_proven: true,
            mapped_lifetime_bounded: true,
            human_authority: false,
            external_effect: false,
        }
    }

    #[test]
    fn production_empty_registry_stays_on_read_seek_safe_default() {
        let root = temp_root("safe-default");
        let (binding, node_path, page_path) = write_fixture(&root);
        let mut reader = open_data_serving_reader(
            &root,
            &node_path,
            &page_path,
            binding,
            [0x44; 32],
        )
        .expect("safe default opens");
        assert_eq!(reader.backend(), DataServingBackendV1::ReadSeekSafeDefault);
        assert_eq!(
            reader.receipt().reason,
            BackendAdmissionReasonV1::CapabilityUnavailable
        );
        let cone = reader.query_cone(0, 1, 10, None).expect("query");
        assert_eq!(cone.node_ids, vec![0, 1, 2]);
        assert_eq!(cone.edges_traversed, 2);
        drop(reader);
        fs::remove_dir_all(root).expect("cleanup");
    }

    #[test]
    fn exact_handle_mmap_matches_generation_bound_read_seek() {
        let root = temp_root("equivalence");
        let (binding, node_path, page_path) = write_fixture(&root);
        let mut safe = GenerationBoundGraphReader::open(
            &node_path,
            &page_path,
            binding.clone(),
        )
        .expect("safe reader");
        let expected = safe.query_cone(0, 2, 10, None).expect("safe cone");
        let mmap = map_exact_admitted_handles(
            positive_receipt(),
            File::open(&node_path).expect("node handle"),
            File::open(&page_path).expect("page handle"),
            binding,
        )
        .expect("exact-handle mmap");
        let observed = mmap.query_cone(0, 2, 10, None).expect("mmap cone");
        assert_eq!(observed, expected);
        drop(mmap);
        drop(safe);
        fs::remove_dir_all(root).expect("cleanup");
    }

    #[cfg(unix)]
    #[test]
    fn path_removal_after_open_cannot_redirect_or_block_exact_handle_mapping() {
        let root = temp_root("no-reopen");
        let (binding, node_path, page_path) = write_fixture(&root);
        let node_file = File::open(&node_path).expect("node handle");
        let page_file = File::open(&page_path).expect("page handle");
        let old_node = root.join("node-index.old");
        let old_page = root.join("pages.old");
        fs::rename(&node_path, &old_node).expect("rename node after open");
        fs::rename(&page_path, &old_page).expect("rename page after open");
        assert!(!node_path.exists());
        assert!(!page_path.exists());

        let mmap = map_exact_admitted_handles(
            positive_receipt(),
            node_file,
            page_file,
            binding,
        )
        .expect("mapping consumes opened handles, not paths");
        let cone = mmap.query_cone(0, 1, 10, None).expect("query");
        assert_eq!(cone.node_ids, vec![0, 1, 2]);
        drop(mmap);
        fs::remove_dir_all(root).expect("cleanup");
    }

    #[test]
    fn incoherent_positive_receipt_cannot_reach_mapping() {
        let root = temp_root("bad-receipt");
        let (binding, node_path, page_path) = write_fixture(&root);
        let mut receipt = positive_receipt();
        receipt.exact_opened_file_identity_bound = false;
        let error = map_exact_admitted_handles(
            receipt,
            File::open(&node_path).expect("node handle"),
            File::open(&page_path).expect("page handle"),
            binding,
        )
        .err()
        .expect("must reject");
        assert_eq!(
            error,
            DataServingExecutionErrorV1::AdmissionReceiptIncoherent
        );
        fs::remove_dir_all(root).expect("cleanup");
    }
}
