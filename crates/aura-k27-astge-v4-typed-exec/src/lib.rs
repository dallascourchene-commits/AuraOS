#![forbid(unsafe_code)]

//! Typed generation-domain membrane over the exact-green V4 execution owner.
//!
//! PR493 remains the owner of capability selection, opaque lease consumption, exact-handle mmap
//! mechanics, Read+Seek fallback and graph traversal. This crate owns only one consequence:
//! snapshot and placement generations must be distinct Rust types at the composition boundary.
//!
//! Swapping the axes does not compile:
//! ```compile_fail
//! use aura_k27_astge_generation_domain::{
//!     MmapGenerationAxesV1, PlacementGenerationV1, SnapshotGenerationV1,
//! };
//!
//! let _bad = MmapGenerationAxesV1::new(
//!     PlacementGenerationV1::new(41),
//!     SnapshotGenerationV1::new(7),
//! );
//! ```

use aura_k27_astge::{
    DataServingBackendV2, HydratedConeV1, MmapBackendAdmissionReceiptV2, StorageGenerationBindingV1,
};
use aura_k27_astge_generation_domain::{
    require_placement_generation, require_snapshot_generation, GenerationDomainErrorV1,
    MmapGenerationAxesV1, PlacementGenerationV1, SnapshotGenerationV1,
};
use aura_k27_astge_v4_mmap_exec::{
    open_canonical_data_serving_reader_v2, CanonicalDataServingReaderV2, V4ExecutionError,
};
use std::error::Error;
use std::fmt::{Display, Formatter};
use std::path::Path;

#[derive(Debug)]
pub enum TypedV4ExecutionErrorV1 {
    Generation(GenerationDomainErrorV1),
    Execution(V4ExecutionError),
    ReceiptAuthorityIncoherent,
}

impl Display for TypedV4ExecutionErrorV1 {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for TypedV4ExecutionErrorV1 {}

impl From<GenerationDomainErrorV1> for TypedV4ExecutionErrorV1 {
    fn from(value: GenerationDomainErrorV1) -> Self {
        Self::Generation(value)
    }
}

impl From<V4ExecutionError> for TypedV4ExecutionErrorV1 {
    fn from(value: V4ExecutionError) -> Self {
        Self::Execution(value)
    }
}

pub struct TypedCanonicalDataServingReaderV1 {
    axes: MmapGenerationAxesV1,
    inner: CanonicalDataServingReaderV2,
}

impl TypedCanonicalDataServingReaderV1 {
    pub const fn axes(&self) -> MmapGenerationAxesV1 {
        self.axes
    }

    pub fn receipt(&self) -> &MmapBackendAdmissionReceiptV2 {
        self.inner.receipt()
    }

    pub fn backend(&self) -> DataServingBackendV2 {
        self.inner.backend()
    }

    pub fn query_cone(
        &mut self,
        root_id: u64,
        max_depth: usize,
        max_nodes: usize,
        edge_kind_filter: Option<u8>,
    ) -> Result<HydratedConeV1, TypedV4ExecutionErrorV1> {
        self.inner
            .query_cone(root_id, max_depth, max_nodes, edge_kind_filter)
            .map_err(Into::into)
    }
}

/// Canonical typed generation-domain boundary over PR493's V4 executor.
///
/// The caller supplies one `MmapGenerationAxesV1`; there is no raw snapshot-generation parameter.
/// Placement must agree with the current storage binding before any owner/filesystem execution.
/// Only at the existing PR493 owner call is the typed snapshot value projected back to the raw V4
/// ABI. The returned receipt is immediately rebound to typed axes and checked again.
pub fn open_typed_canonical_data_serving_reader_v1(
    storage_root: impl AsRef<Path>,
    node_index_path: impl AsRef<Path>,
    page_path: impl AsRef<Path>,
    binding: StorageGenerationBindingV1,
    axes: MmapGenerationAxesV1,
    manifest_digest: [u8; 32],
) -> Result<TypedCanonicalDataServingReaderV1, TypedV4ExecutionErrorV1> {
    require_placement_generation(axes.placement, binding.placement_generation)?;

    let expected_snapshot = axes.snapshot;
    let expected_placement = axes.placement;
    let inner = open_canonical_data_serving_reader_v2(
        storage_root,
        node_index_path,
        page_path,
        binding,
        expected_snapshot.value(),
        manifest_digest,
    )?;

    let receipt = inner.receipt();
    require_snapshot_generation(
        SnapshotGenerationV1::new(receipt.snapshot_generation),
        expected_snapshot.value(),
    )?;
    require_placement_generation(
        PlacementGenerationV1::new(receipt.placement_generation),
        expected_placement.value(),
    )?;
    if receipt.human_authority || receipt.external_effect {
        return Err(TypedV4ExecutionErrorV1::ReceiptAuthorityIncoherent);
    }

    Ok(TypedCanonicalDataServingReaderV1 { axes, inner })
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge::{
        BackendAdmissionReasonV2, NodeIndexRecordV1, PageRow, PhysicalPageV1, BLOCK_SIZE,
    };
    use aura_k27_astge_generation_domain::{PlacementGenerationV1, SnapshotGenerationV1};
    use std::fs;
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(1);

    fn root(label: &str) -> PathBuf {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "aura-k27-v4-typed-exec-{label}-{}-{n}",
            std::process::id()
        ));
        fs::create_dir(&path).unwrap();
        path
    }

    fn fixture(root: &Path) -> (StorageGenerationBindingV1, PathBuf, PathBuf) {
        let placement_generation = 7;
        let scheme = [0x31; 32];
        let binding = StorageGenerationBindingV1 {
            node_count: 3,
            page_count: 1,
            placement_generation,
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
        let mut index = Vec::new();
        for record in records {
            index.extend_from_slice(&record.encode());
        }
        let page = PhysicalPageV1 {
            pbn: 0,
            placement_generation,
            placement_scheme_digest: scheme,
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
        let encoded = page.encode().unwrap();
        assert_eq!(encoded.len(), BLOCK_SIZE);
        fs::write(&pages, encoded).unwrap();
        (binding, node, pages)
    }

    #[test]
    fn typed_boundary_preserves_production_readseek_and_exact_cone() {
        let root = root("safe-default");
        let (binding, node, pages) = fixture(&root);
        let axes =
            MmapGenerationAxesV1::new(SnapshotGenerationV1::new(41), PlacementGenerationV1::new(7));
        let mut reader = open_typed_canonical_data_serving_reader_v1(
            &root, &node, &pages, binding, axes, [0x44; 32],
        )
        .unwrap();

        assert_eq!(reader.axes(), axes);
        assert_eq!(reader.backend(), DataServingBackendV2::ReadSeekSafeDefault);
        assert_eq!(
            reader.receipt().reason,
            BackendAdmissionReasonV2::CapabilityUnavailable
        );
        assert_eq!(reader.receipt().snapshot_generation, 41);
        assert_eq!(reader.receipt().placement_generation, 7);
        assert_eq!(
            reader.query_cone(0, 1, 10, None).unwrap().node_ids,
            vec![0, 1, 2]
        );
        assert!(!reader.receipt().human_authority);
        assert!(!reader.receipt().external_effect);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn placement_value_mismatch_fails_before_filesystem_owner_execution() {
        let binding = StorageGenerationBindingV1 {
            node_count: 3,
            page_count: 1,
            placement_generation: 7,
            placement_scheme_digest: [0x31; 32],
        };
        let axes =
            MmapGenerationAxesV1::new(SnapshotGenerationV1::new(41), PlacementGenerationV1::new(8));
        let result = open_typed_canonical_data_serving_reader_v1(
            "/definitely/not/a/storage/root",
            "/definitely/not/nodes.idx",
            "/definitely/not/pages.bin",
            binding,
            axes,
            [0x44; 32],
        );
        assert!(matches!(
            result,
            Err(TypedV4ExecutionErrorV1::Generation(
                GenerationDomainErrorV1::ValueMismatch { .. }
            ))
        ));
    }

    #[test]
    fn equal_numeric_snapshot_and_placement_still_retain_distinct_domains() {
        let axes =
            MmapGenerationAxesV1::new(SnapshotGenerationV1::new(7), PlacementGenerationV1::new(7));
        assert_eq!(axes.snapshot.value(), axes.placement.value());
        assert_ne!(axes.snapshot.coordinate(), axes.placement.coordinate());
    }
}
