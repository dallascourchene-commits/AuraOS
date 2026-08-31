#![forbid(unsafe_code)]

use aura_k27_astge::{
    admit_data_serving_backend, BackendAdmissionReasonV1, DataServingBackendAdmissionV1,
    MmapAdmissionError, StorageGenerationBindingV1,
};
use std::path::Path;

/// Current convergence disposition for the canonical Aura data-serving path.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CanonicalMmapDispositionV1 {
    /// Production remains on the safe generation-bound Read+Seek path.
    ReadSeekSafeDefault,
    /// A future positive capability is held because PR472 does not bind the
    /// actual immutable snapshot generation independently from placement generation.
    HoldSnapshotGenerationAxisUnbound,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CanonicalMmapReasonV1 {
    CoreSafeDefault(BackendAdmissionReasonV1),
    SnapshotGenerationAxisNotIndependentlyBound,
}

/// Receipt for the convergence membrane.  Snapshot generation and placement
/// generation are always recorded as separate coordinates even though the
/// underlying PR472 selector currently collapses the former onto the latter.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CanonicalMmapPreflightReceiptV1 {
    pub disposition: CanonicalMmapDispositionV1,
    pub reason: CanonicalMmapReasonV1,
    pub snapshot_generation: u64,
    pub placement_generation: u64,
    pub selector_binds_actual_snapshot_generation: bool,
    pub exact_opened_file_identity_bound: bool,
    pub mmap_executor_present: bool,
    pub mmap_executor_invoked: bool,
    pub human_authority: bool,
    pub external_effect: bool,
}

/// PR471 is intentionally linked into this convergence child, but its mmap
/// executor is not invoked while the snapshot-generation capability axis is
/// unbound.  This function is a compile-time ownership witness only.
pub fn mmap_executor_type_name() -> &'static str {
    std::any::type_name::<aura_k27_astge_mmap::ImmutableMmapReader>()
}

/// Canonical preflight.  Callers cannot provide a capability record, registry,
/// trusted boolean, mmap token, or pre-opened handle.  The source-owned PR472
/// selector is consulted internally.  If it ever returns a positive mmap
/// candidate before a successor independently binds the *actual* snapshot
/// generation, the canonical path still refuses to execute mmap.
pub fn canonical_mmap_preflight(
    storage_root: impl AsRef<Path>,
    node_index_path: impl AsRef<Path>,
    page_path: impl AsRef<Path>,
    binding: &StorageGenerationBindingV1,
    snapshot_generation: u64,
    manifest_digest: [u8; 32],
) -> Result<CanonicalMmapPreflightReceiptV1, MmapAdmissionError> {
    let admission = admit_data_serving_backend(
        storage_root,
        node_index_path,
        page_path,
        binding,
        manifest_digest,
    )?;

    let mmap_executor_present = !mmap_executor_type_name().is_empty();
    match admission {
        DataServingBackendAdmissionV1::ReadSeekSafeDefault(receipt) => {
            Ok(CanonicalMmapPreflightReceiptV1 {
                disposition: CanonicalMmapDispositionV1::ReadSeekSafeDefault,
                reason: CanonicalMmapReasonV1::CoreSafeDefault(receipt.reason),
                snapshot_generation,
                placement_generation: binding.placement_generation,
                selector_binds_actual_snapshot_generation: false,
                exact_opened_file_identity_bound: receipt.exact_opened_file_identity_bound,
                mmap_executor_present,
                mmap_executor_invoked: false,
                human_authority: false,
                external_effect: false,
            })
        }
        DataServingBackendAdmissionV1::MmapCapabilityGated {
            receipt,
            node_file: _,
            page_file: _,
        } => Ok(CanonicalMmapPreflightReceiptV1 {
            disposition: CanonicalMmapDispositionV1::HoldSnapshotGenerationAxisUnbound,
            reason: CanonicalMmapReasonV1::SnapshotGenerationAxisNotIndependentlyBound,
            snapshot_generation,
            placement_generation: binding.placement_generation,
            selector_binds_actual_snapshot_generation: false,
            exact_opened_file_identity_bound: receipt.exact_opened_file_identity_bound,
            mmap_executor_present,
            mmap_executor_invoked: false,
            human_authority: false,
            external_effect: false,
        }),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs::{create_dir_all, remove_dir_all, File};
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(0);

    fn temp_root(label: &str) -> PathBuf {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "aura-k27-canonical-backend-{label}-{}-{n}",
            std::process::id()
        ));
        create_dir_all(&root).unwrap();
        root
    }

    fn fixture_files(
        root: &Path,
        binding: &StorageGenerationBindingV1,
    ) -> (PathBuf, PathBuf) {
        let node = root.join("node-index.bin");
        let pages = root.join("pages.bin");
        let node_file = File::create(&node).unwrap();
        node_file
            .set_len(binding.node_count * aura_k27_astge::NODE_INDEX_RECORD_SIZE as u64)
            .unwrap();
        let page_file = File::create(&pages).unwrap();
        page_file
            .set_len(binding.page_count * aura_k27_astge::BLOCK_SIZE as u64)
            .unwrap();
        (node, pages)
    }

    #[test]
    fn source_contract_retains_snapshot_placement_axis_collapse_scar() {
        let source = include_str!("../../aura-k27-astge/src/v3.rs");
        let compact: String = source.chars().filter(|ch| !ch.is_whitespace()).collect();
        assert!(compact.contains(
            "record.snapshot_generation==binding.placement_generation"
        ));
    }

    #[test]
    fn production_preflight_stays_readseek_and_records_distinct_axes() {
        let root = temp_root("safe-default");
        let binding = StorageGenerationBindingV1 {
            node_count: 2,
            page_count: 1,
            placement_generation: 7,
            placement_scheme_digest: [0x22; 32],
        };
        let (node, pages) = fixture_files(&root, &binding);
        let receipt = canonical_mmap_preflight(
            &root,
            &node,
            &pages,
            &binding,
            41,
            [0x44; 32],
        )
        .unwrap();

        assert_eq!(
            receipt.disposition,
            CanonicalMmapDispositionV1::ReadSeekSafeDefault
        );
        assert_eq!(
            receipt.reason,
            CanonicalMmapReasonV1::CoreSafeDefault(
                BackendAdmissionReasonV1::CapabilityUnavailable
            )
        );
        assert_eq!(receipt.snapshot_generation, 41);
        assert_eq!(receipt.placement_generation, 7);
        assert!(!receipt.selector_binds_actual_snapshot_generation);
        assert!(receipt.mmap_executor_present);
        assert!(!receipt.mmap_executor_invoked);
        assert!(!receipt.human_authority);
        assert!(!receipt.external_effect);
        let _ = remove_dir_all(root);
    }

    #[test]
    fn mmap_executor_is_present_but_not_promoted_by_convergence() {
        assert!(mmap_executor_type_name().contains("ImmutableMmapReader"));
    }
}
