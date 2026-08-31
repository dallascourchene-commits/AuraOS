#![forbid(unsafe_code)]

#[path = "v3.rs"]
mod v3;

// V3 remains available for compatibility, but V4 below is the canonical selector for
// snapshot-aware, source-owned mmap admission.
pub use v3::*;

use std::error::Error;
use std::fmt::{Display, Formatter};
use std::fs::{canonicalize, metadata, File};
use std::path::{Path, PathBuf};

#[cfg(unix)]
use std::os::unix::fs::MetadataExt;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DataServingBackendV2 {
    ReadSeekSafeDefault,
    MmapCapabilityGated,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BackendAdmissionReasonV2 {
    CapabilityUnavailable,
    CapabilityExactUnique,
    CapabilityAmbiguous,
    CapabilityRegistryInvalid,
    PlatformIdentityUnsupported,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GenerationOpenPolicyV2 {
    OpenVerifiedHandlesOnce,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExternalMutationDispositionV2 {
    ExcludedByOwnedStorageRoot,
    NotExcluded,
}

/// Source-owned capability record. Snapshot publication and physical placement are
/// independent coordinates and must both match exactly.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct BackingFileImmutabilityCapabilityV2 {
    pub capability_ref: &'static str,
    pub storage_root_device: u64,
    pub storage_root_inode: u64,
    pub snapshot_generation: u64,
    pub placement_generation: u64,
    pub manifest_digest: [u8; 32],
    pub placement_scheme_digest: [u8; 32],
    pub node_file_device: u64,
    pub node_file_inode: u64,
    pub node_file_len: u64,
    pub page_file_device: u64,
    pub page_file_inode: u64,
    pub page_file_len: u64,
    pub generation_open_policy: GenerationOpenPolicyV2,
    pub replacement_generations_only: bool,
    pub no_in_place_write_truncate_reuse: bool,
    pub mapped_lifetime_within_capability: bool,
    pub platform_semantics_ref: &'static str,
    pub filesystem_semantics_ref: &'static str,
    pub platform_semantics_current: bool,
    pub filesystem_semantics_current: bool,
    pub external_mutation_disposition: ExternalMutationDispositionV2,
    pub publisher_ref: &'static str,
    pub verifier_ref: &'static str,
    pub independently_verified: bool,
    pub current: bool,
    pub revoked: bool,
    pub authority: bool,
    pub external_effect: bool,
}

/// Production trust root. Deliberately empty until an independent owner registers
/// a current capability for an exact snapshot + placement + opened-file generation.
static CANONICAL_IMMUTABILITY_CAPABILITIES_V2: &[BackingFileImmutabilityCapabilityV2] = &[];

pub fn canonical_immutability_capability_count_v2() -> usize {
    CANONICAL_IMMUTABILITY_CAPABILITIES_V2.len()
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MmapBackendAdmissionReceiptV2 {
    pub backend: DataServingBackendV2,
    pub reason: BackendAdmissionReasonV2,
    pub capability_ref: Option<&'static str>,
    pub snapshot_generation: u64,
    pub placement_generation: u64,
    pub snapshot_generation_independently_bound: bool,
    pub placement_generation_independently_bound: bool,
    pub exact_opened_file_identity_bound: bool,
    pub final_handle_revalidation_passed: bool,
    pub replacement_generations_only_proven: bool,
    pub no_in_place_mutation_proven: bool,
    pub mapped_lifetime_bounded: bool,
    pub human_authority: bool,
    pub external_effect: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MmapAdmissionErrorV2 {
    Io(String),
    StorageRootNotDirectory,
    PathOutsideStorageRoot,
    PathFdIdentityMismatch,
    NotRegularFile,
    LengthOverflow,
    NodeIndexLengthMismatch { expected: u64, actual: u64 },
    PageFileLengthMismatch { expected: u64, actual: u64 },
    FileIdentityChangedBeforeLease,
}

impl Display for MmapAdmissionErrorV2 {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for MmapAdmissionErrorV2 {}

impl From<std::io::Error> for MmapAdmissionErrorV2 {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value.to_string())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct FileIdentityV2 {
    device: u64,
    inode: u64,
    len: u64,
    platform_supported: bool,
}

#[derive(Debug)]
struct ObservedFileV2 {
    file: File,
    identity: FileIdentityV2,
}

#[derive(Debug)]
struct ObservedStorageContextV2 {
    root_device: u64,
    root_inode: u64,
    platform_supported: bool,
    node: ObservedFileV2,
    page: ObservedFileV2,
}

/// Opaque positive lease. External callers cannot construct one because all fields
/// are private. The only public minting path is the source-owned V4 selector.
pub struct MmapCandidateLeaseV2 {
    receipt: MmapBackendAdmissionReceiptV2,
    node_file: File,
    page_file: File,
    node_identity: FileIdentityV2,
    page_identity: FileIdentityV2,
}

impl MmapCandidateLeaseV2 {
    pub fn receipt(&self) -> &MmapBackendAdmissionReceiptV2 {
        &self.receipt
    }

    /// Final same-handle revalidation at the consumer handoff boundary.
    pub fn into_verified_files(self) -> Result<(File, File), MmapAdmissionErrorV2> {
        if identity_from_open_file(&self.node_file)? != self.node_identity
            || identity_from_open_file(&self.page_file)? != self.page_identity
        {
            return Err(MmapAdmissionErrorV2::FileIdentityChangedBeforeLease);
        }
        Ok((self.node_file, self.page_file))
    }
}

pub enum DataServingBackendAdmissionV2 {
    ReadSeekSafeDefault(MmapBackendAdmissionReceiptV2),
    MmapCapabilityGated(MmapCandidateLeaseV2),
}

impl DataServingBackendAdmissionV2 {
    pub fn receipt(&self) -> &MmapBackendAdmissionReceiptV2 {
        match self {
            Self::ReadSeekSafeDefault(receipt) => receipt,
            Self::MmapCapabilityGated(lease) => lease.receipt(),
        }
    }
}

fn exact_len_v2(count: u64, width: usize) -> Result<u64, MmapAdmissionErrorV2> {
    count
        .checked_mul(width as u64)
        .ok_or(MmapAdmissionErrorV2::LengthOverflow)
}

fn canonical_child_v2(root: &Path, child: &Path) -> Result<PathBuf, MmapAdmissionErrorV2> {
    let root = canonicalize(root)?;
    let child = canonicalize(child)?;
    if !child.starts_with(&root) {
        return Err(MmapAdmissionErrorV2::PathOutsideStorageRoot);
    }
    Ok(child)
}

#[cfg(unix)]
fn root_identity_v2(root: &Path) -> Result<(u64, u64, bool), MmapAdmissionErrorV2> {
    let meta = metadata(root)?;
    if !meta.is_dir() {
        return Err(MmapAdmissionErrorV2::StorageRootNotDirectory);
    }
    Ok((meta.dev(), meta.ino(), true))
}

#[cfg(not(unix))]
fn root_identity_v2(root: &Path) -> Result<(u64, u64, bool), MmapAdmissionErrorV2> {
    let meta = metadata(root)?;
    if !meta.is_dir() {
        return Err(MmapAdmissionErrorV2::StorageRootNotDirectory);
    }
    Ok((0, 0, false))
}

#[cfg(unix)]
fn identity_from_metadata(meta: &std::fs::Metadata) -> FileIdentityV2 {
    FileIdentityV2 {
        device: meta.dev(),
        inode: meta.ino(),
        len: meta.len(),
        platform_supported: true,
    }
}

#[cfg(not(unix))]
fn identity_from_metadata(meta: &std::fs::Metadata) -> FileIdentityV2 {
    FileIdentityV2 {
        device: 0,
        inode: 0,
        len: meta.len(),
        platform_supported: false,
    }
}

fn identity_from_open_file(file: &File) -> Result<FileIdentityV2, MmapAdmissionErrorV2> {
    let meta = file.metadata()?;
    if !meta.is_file() {
        return Err(MmapAdmissionErrorV2::NotRegularFile);
    }
    Ok(identity_from_metadata(&meta))
}

fn open_identity_v2(path: &Path) -> Result<ObservedFileV2, MmapAdmissionErrorV2> {
    let file = File::open(path)?;
    let fd_identity = identity_from_open_file(&file)?;
    let path_meta = metadata(path)?;
    if !path_meta.is_file() {
        return Err(MmapAdmissionErrorV2::NotRegularFile);
    }
    let path_identity = identity_from_metadata(&path_meta);
    if fd_identity.platform_supported && fd_identity != path_identity {
        return Err(MmapAdmissionErrorV2::PathFdIdentityMismatch);
    }
    Ok(ObservedFileV2 {
        file,
        identity: fd_identity,
    })
}

fn observe_storage_context_v2(
    storage_root: &Path,
    node_index_path: &Path,
    page_path: &Path,
    binding: &StorageGenerationBindingV1,
) -> Result<ObservedStorageContextV2, MmapAdmissionErrorV2> {
    let root = canonicalize(storage_root)?;
    let node_path = canonical_child_v2(&root, node_index_path)?;
    let page_path = canonical_child_v2(&root, page_path)?;
    let (root_device, root_inode, root_supported) = root_identity_v2(&root)?;
    let node = open_identity_v2(&node_path)?;
    let page = open_identity_v2(&page_path)?;

    let expected_nodes = exact_len_v2(binding.node_count, NODE_INDEX_RECORD_SIZE)?;
    let expected_pages = exact_len_v2(binding.page_count, BLOCK_SIZE)?;
    if node.identity.len != expected_nodes {
        return Err(MmapAdmissionErrorV2::NodeIndexLengthMismatch {
            expected: expected_nodes,
            actual: node.identity.len,
        });
    }
    if page.identity.len != expected_pages {
        return Err(MmapAdmissionErrorV2::PageFileLengthMismatch {
            expected: expected_pages,
            actual: page.identity.len,
        });
    }

    Ok(ObservedStorageContextV2 {
        root_device,
        root_inode,
        platform_supported: root_supported
            && node.identity.platform_supported
            && page.identity.platform_supported,
        node,
        page,
    })
}

fn structurally_valid_capability_v2(record: &BackingFileImmutabilityCapabilityV2) -> bool {
    !record.capability_ref.trim().is_empty()
        && !record.platform_semantics_ref.trim().is_empty()
        && !record.filesystem_semantics_ref.trim().is_empty()
        && !record.publisher_ref.trim().is_empty()
        && !record.verifier_ref.trim().is_empty()
        && record.publisher_ref != record.verifier_ref
        && record.generation_open_policy == GenerationOpenPolicyV2::OpenVerifiedHandlesOnce
        && record.replacement_generations_only
        && record.no_in_place_write_truncate_reuse
        && record.mapped_lifetime_within_capability
        && !record.authority
        && !record.external_effect
}

fn active_capability_v2(record: &BackingFileImmutabilityCapabilityV2) -> bool {
    record.current
        && !record.revoked
        && record.independently_verified
        && record.platform_semantics_current
        && record.filesystem_semantics_current
        && record.external_mutation_disposition
            == ExternalMutationDispositionV2::ExcludedByOwnedStorageRoot
}

fn exact_capability_match_v2(
    record: &BackingFileImmutabilityCapabilityV2,
    observed: &ObservedStorageContextV2,
    binding: &StorageGenerationBindingV1,
    snapshot_generation: u64,
    manifest_digest: [u8; 32],
) -> bool {
    record.storage_root_device == observed.root_device
        && record.storage_root_inode == observed.root_inode
        && record.snapshot_generation == snapshot_generation
        && record.placement_generation == binding.placement_generation
        && record.manifest_digest == manifest_digest
        && record.placement_scheme_digest == binding.placement_scheme_digest
        && record.node_file_device == observed.node.identity.device
        && record.node_file_inode == observed.node.identity.inode
        && record.node_file_len == observed.node.identity.len
        && record.page_file_device == observed.page.identity.device
        && record.page_file_inode == observed.page.identity.inode
        && record.page_file_len == observed.page.identity.len
}

fn revalidate_observed_v2(observed: &ObservedStorageContextV2) -> Result<(), MmapAdmissionErrorV2> {
    if identity_from_open_file(&observed.node.file)? != observed.node.identity
        || identity_from_open_file(&observed.page.file)? != observed.page.identity
    {
        return Err(MmapAdmissionErrorV2::FileIdentityChangedBeforeLease);
    }
    Ok(())
}

fn safe_default_v2(
    reason: BackendAdmissionReasonV2,
    snapshot_generation: u64,
    placement_generation: u64,
) -> DataServingBackendAdmissionV2 {
    DataServingBackendAdmissionV2::ReadSeekSafeDefault(MmapBackendAdmissionReceiptV2 {
        backend: DataServingBackendV2::ReadSeekSafeDefault,
        reason,
        capability_ref: None,
        snapshot_generation,
        placement_generation,
        snapshot_generation_independently_bound: false,
        placement_generation_independently_bound: false,
        exact_opened_file_identity_bound: false,
        final_handle_revalidation_passed: false,
        replacement_generations_only_proven: false,
        no_in_place_mutation_proven: false,
        mapped_lifetime_bounded: false,
        human_authority: false,
        external_effect: false,
    })
}

fn select_with_records_v2(
    records: &[BackingFileImmutabilityCapabilityV2],
    observed: ObservedStorageContextV2,
    binding: &StorageGenerationBindingV1,
    snapshot_generation: u64,
    manifest_digest: [u8; 32],
) -> Result<DataServingBackendAdmissionV2, MmapAdmissionErrorV2> {
    if records
        .iter()
        .any(|record| !structurally_valid_capability_v2(record))
    {
        return Ok(safe_default_v2(
            BackendAdmissionReasonV2::CapabilityRegistryInvalid,
            snapshot_generation,
            binding.placement_generation,
        ));
    }

    if !observed.platform_supported {
        return Ok(safe_default_v2(
            BackendAdmissionReasonV2::PlatformIdentityUnsupported,
            snapshot_generation,
            binding.placement_generation,
        ));
    }

    let matches: Vec<_> = records
        .iter()
        .filter(|record| active_capability_v2(record))
        .filter(|record| {
            exact_capability_match_v2(
                record,
                &observed,
                binding,
                snapshot_generation,
                manifest_digest,
            )
        })
        .collect();

    if matches.len() > 1 {
        return Ok(safe_default_v2(
            BackendAdmissionReasonV2::CapabilityAmbiguous,
            snapshot_generation,
            binding.placement_generation,
        ));
    }
    let Some(record) = matches.first() else {
        return Ok(safe_default_v2(
            BackendAdmissionReasonV2::CapabilityUnavailable,
            snapshot_generation,
            binding.placement_generation,
        ));
    };

    revalidate_observed_v2(&observed)?;
    let receipt = MmapBackendAdmissionReceiptV2 {
        backend: DataServingBackendV2::MmapCapabilityGated,
        reason: BackendAdmissionReasonV2::CapabilityExactUnique,
        capability_ref: Some(record.capability_ref),
        snapshot_generation,
        placement_generation: binding.placement_generation,
        snapshot_generation_independently_bound: true,
        placement_generation_independently_bound: true,
        exact_opened_file_identity_bound: true,
        final_handle_revalidation_passed: true,
        replacement_generations_only_proven: true,
        no_in_place_mutation_proven: true,
        mapped_lifetime_bounded: true,
        human_authority: false,
        external_effect: false,
    };
    Ok(DataServingBackendAdmissionV2::MmapCapabilityGated(
        MmapCandidateLeaseV2 {
            receipt,
            node_identity: observed.node.identity,
            page_identity: observed.page.identity,
            node_file: observed.node.file,
            page_file: observed.page.file,
        },
    ))
}

/// Canonical V4 consequence boundary. No capability record, registry, trust flag,
/// pre-opened file, mmap authorization or effect flag can be supplied by callers.
/// Production resolves only the source-owned registry above.
pub fn admit_data_serving_backend_v2(
    storage_root: impl AsRef<Path>,
    node_index_path: impl AsRef<Path>,
    page_path: impl AsRef<Path>,
    binding: &StorageGenerationBindingV1,
    snapshot_generation: u64,
    manifest_digest: [u8; 32],
) -> Result<DataServingBackendAdmissionV2, MmapAdmissionErrorV2> {
    let observed = observe_storage_context_v2(
        storage_root.as_ref(),
        node_index_path.as_ref(),
        page_path.as_ref(),
        binding,
    )?;
    select_with_records_v2(
        CANONICAL_IMMUTABILITY_CAPABILITIES_V2,
        observed,
        binding,
        snapshot_generation,
        manifest_digest,
    )
}

#[cfg(test)]
mod v4_tests {
    use super::*;
    use std::fs::{create_dir_all, remove_dir_all, OpenOptions};
    use std::time::{SystemTime, UNIX_EPOCH};

    #[cfg(unix)]
    use std::os::unix::fs::MetadataExt;

    fn temp_root(label: &str) -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = std::env::temp_dir().join(format!(
            "aura-k27-astge-v4-{label}-{}-{nonce}",
            std::process::id()
        ));
        create_dir_all(&root).unwrap();
        root
    }

    fn binding() -> StorageGenerationBindingV1 {
        StorageGenerationBindingV1 {
            node_count: 2,
            page_count: 1,
            placement_generation: 7,
            placement_scheme_digest: [0x22; 32],
        }
    }

    fn files(root: &Path, binding: &StorageGenerationBindingV1) -> (PathBuf, PathBuf) {
        let node = root.join("nodes.idx");
        let page = root.join("pages.bin");
        let node_file = File::create(&node).unwrap();
        node_file
            .set_len(binding.node_count * NODE_INDEX_RECORD_SIZE as u64)
            .unwrap();
        let page_file = File::create(&page).unwrap();
        page_file
            .set_len(binding.page_count * BLOCK_SIZE as u64)
            .unwrap();
        (node, page)
    }

    #[cfg(unix)]
    fn exact_record(
        root: &Path,
        node: &Path,
        page: &Path,
        binding: &StorageGenerationBindingV1,
        snapshot_generation: u64,
        manifest_digest: [u8; 32],
    ) -> BackingFileImmutabilityCapabilityV2 {
        let root_meta = metadata(root).unwrap();
        let node_meta = metadata(node).unwrap();
        let page_meta = metadata(page).unwrap();
        BackingFileImmutabilityCapabilityV2 {
            capability_ref: "capability://astge/snapshot/41/placement/7",
            storage_root_device: root_meta.dev(),
            storage_root_inode: root_meta.ino(),
            snapshot_generation,
            placement_generation: binding.placement_generation,
            manifest_digest,
            placement_scheme_digest: binding.placement_scheme_digest,
            node_file_device: node_meta.dev(),
            node_file_inode: node_meta.ino(),
            node_file_len: node_meta.len(),
            page_file_device: page_meta.dev(),
            page_file_inode: page_meta.ino(),
            page_file_len: page_meta.len(),
            generation_open_policy: GenerationOpenPolicyV2::OpenVerifiedHandlesOnce,
            replacement_generations_only: true,
            no_in_place_write_truncate_reuse: true,
            mapped_lifetime_within_capability: true,
            platform_semantics_ref: "platform://linux/open-file-description-v1",
            filesystem_semantics_ref: "filesystem://owned-replacement-generation-v1",
            platform_semantics_current: true,
            filesystem_semantics_current: true,
            external_mutation_disposition: ExternalMutationDispositionV2::ExcludedByOwnedStorageRoot,
            publisher_ref: "principal://storage-owner",
            verifier_ref: "principal://independent-verifier",
            independently_verified: true,
            current: true,
            revoked: false,
            authority: false,
            external_effect: false,
        }
    }

    #[test]
    fn production_registry_is_empty_and_defaults_to_read_seek() {
        let root = temp_root("production");
        let b = binding();
        let (node, page) = files(&root, &b);
        let out = admit_data_serving_backend_v2(&root, &node, &page, &b, 41, [0x11; 32]).unwrap();
        assert_eq!(canonical_immutability_capability_count_v2(), 0);
        assert_eq!(out.receipt().backend, DataServingBackendV2::ReadSeekSafeDefault);
        assert_eq!(out.receipt().reason, BackendAdmissionReasonV2::CapabilityUnavailable);
        assert_eq!(out.receipt().snapshot_generation, 41);
        assert_eq!(out.receipt().placement_generation, 7);
        assert!(!out.receipt().human_authority);
        assert!(!out.receipt().external_effect);
        remove_dir_all(root).unwrap();
    }

    #[test]
    #[cfg(unix)]
    fn exact_private_record_binds_snapshot_and_placement_separately_and_returns_opaque_lease() {
        let root = temp_root("exact");
        let b = binding();
        let snapshot = 41;
        let manifest = [0x11; 32];
        let (node, page) = files(&root, &b);
        let record = exact_record(&root, &node, &page, &b, snapshot, manifest);
        let observed = observe_storage_context_v2(&root, &node, &page, &b).unwrap();
        let expected_node_inode = observed.node.identity.inode;
        let expected_page_inode = observed.page.identity.inode;
        let out = select_with_records_v2(&[record], observed, &b, snapshot, manifest).unwrap();
        match out {
            DataServingBackendAdmissionV2::MmapCapabilityGated(lease) => {
                assert_eq!(lease.receipt().snapshot_generation, 41);
                assert_eq!(lease.receipt().placement_generation, 7);
                assert!(lease.receipt().snapshot_generation_independently_bound);
                assert!(lease.receipt().placement_generation_independently_bound);
                assert!(lease.receipt().exact_opened_file_identity_bound);
                assert!(lease.receipt().final_handle_revalidation_passed);
                let (node_file, page_file) = lease.into_verified_files().unwrap();
                assert_eq!(node_file.metadata().unwrap().ino(), expected_node_inode);
                assert_eq!(page_file.metadata().unwrap().ino(), expected_page_inode);
            }
            _ => panic!("exact source-owned record should mint a lease"),
        }
        remove_dir_all(root).unwrap();
    }

    #[test]
    #[cfg(unix)]
    fn snapshot_and_placement_substitutions_are_independent_failures() {
        let root = temp_root("axes");
        let b = binding();
        let snapshot = 41;
        let manifest = [0x11; 32];
        let (node, page) = files(&root, &b);
        let record = exact_record(&root, &node, &page, &b, snapshot, manifest);
        let cases = [
            BackingFileImmutabilityCapabilityV2 { snapshot_generation: 42, ..record },
            BackingFileImmutabilityCapabilityV2 { placement_generation: 8, ..record },
        ];
        for changed in cases {
            let observed = observe_storage_context_v2(&root, &node, &page, &b).unwrap();
            let out = select_with_records_v2(&[changed], observed, &b, snapshot, manifest).unwrap();
            assert_eq!(out.receipt().reason, BackendAdmissionReasonV2::CapabilityUnavailable);
        }
        remove_dir_all(root).unwrap();
    }

    #[test]
    #[cfg(unix)]
    fn same_publisher_and_verifier_poison_full_registry() {
        let root = temp_root("principal");
        let b = binding();
        let snapshot = 41;
        let manifest = [0x11; 32];
        let (node, page) = files(&root, &b);
        let record = exact_record(&root, &node, &page, &b, snapshot, manifest);
        let poisoned = BackingFileImmutabilityCapabilityV2 { verifier_ref: record.publisher_ref, ..record };
        let observed = observe_storage_context_v2(&root, &node, &page, &b).unwrap();
        let out = select_with_records_v2(&[poisoned], observed, &b, snapshot, manifest).unwrap();
        assert_eq!(out.receipt().reason, BackendAdmissionReasonV2::CapabilityRegistryInvalid);
        remove_dir_all(root).unwrap();
    }

    #[test]
    #[cfg(unix)]
    fn malformed_unrelated_neighbor_poison_is_not_hidden_by_exact_record() {
        let root = temp_root("neighbor");
        let b = binding();
        let snapshot = 41;
        let manifest = [0x11; 32];
        let (node, page) = files(&root, &b);
        let exact = exact_record(&root, &node, &page, &b, snapshot, manifest);
        let malformed = BackingFileImmutabilityCapabilityV2 { capability_ref: "", snapshot_generation: 99, ..exact };
        let observed = observe_storage_context_v2(&root, &node, &page, &b).unwrap();
        let out = select_with_records_v2(&[exact, malformed], observed, &b, snapshot, manifest).unwrap();
        assert_eq!(out.receipt().reason, BackendAdmissionReasonV2::CapabilityRegistryInvalid);
        remove_dir_all(root).unwrap();
    }

    #[test]
    #[cfg(unix)]
    fn two_exact_active_records_are_ambiguous() {
        let root = temp_root("ambiguous");
        let b = binding();
        let snapshot = 41;
        let manifest = [0x11; 32];
        let (node, page) = files(&root, &b);
        let a = exact_record(&root, &node, &page, &b, snapshot, manifest);
        let second = BackingFileImmutabilityCapabilityV2 { capability_ref: "capability://astge/snapshot/41/placement/7/second", ..a };
        let observed = observe_storage_context_v2(&root, &node, &page, &b).unwrap();
        let out = select_with_records_v2(&[a, second], observed, &b, snapshot, manifest).unwrap();
        assert_eq!(out.receipt().reason, BackendAdmissionReasonV2::CapabilityAmbiguous);
        remove_dir_all(root).unwrap();
    }

    #[test]
    #[cfg(unix)]
    fn stale_revoked_unverified_or_unisolated_records_do_not_mint_leases() {
        let root = temp_root("inactive");
        let b = binding();
        let snapshot = 41;
        let manifest = [0x11; 32];
        let (node, page) = files(&root, &b);
        let record = exact_record(&root, &node, &page, &b, snapshot, manifest);
        let cases = [
            BackingFileImmutabilityCapabilityV2 { current: false, ..record },
            BackingFileImmutabilityCapabilityV2 { revoked: true, ..record },
            BackingFileImmutabilityCapabilityV2 { independently_verified: false, ..record },
            BackingFileImmutabilityCapabilityV2 { platform_semantics_current: false, ..record },
            BackingFileImmutabilityCapabilityV2 { filesystem_semantics_current: false, ..record },
            BackingFileImmutabilityCapabilityV2 { external_mutation_disposition: ExternalMutationDispositionV2::NotExcluded, ..record },
        ];
        for changed in cases {
            let observed = observe_storage_context_v2(&root, &node, &page, &b).unwrap();
            let out = select_with_records_v2(&[changed], observed, &b, snapshot, manifest).unwrap();
            assert_eq!(out.receipt().backend, DataServingBackendV2::ReadSeekSafeDefault);
        }
        remove_dir_all(root).unwrap();
    }

    #[test]
    #[cfg(unix)]
    fn file_identity_substitution_fails_closed() {
        let root = temp_root("identity");
        let b = binding();
        let snapshot = 41;
        let manifest = [0x11; 32];
        let (node, page) = files(&root, &b);
        let record = exact_record(&root, &node, &page, &b, snapshot, manifest);
        let changed = BackingFileImmutabilityCapabilityV2 { node_file_inode: record.node_file_inode + 1, ..record };
        let observed = observe_storage_context_v2(&root, &node, &page, &b).unwrap();
        let out = select_with_records_v2(&[changed], observed, &b, snapshot, manifest).unwrap();
        assert_eq!(out.receipt().reason, BackendAdmissionReasonV2::CapabilityUnavailable);
        remove_dir_all(root).unwrap();
    }

    #[test]
    #[cfg(unix)]
    fn post_observation_truncation_fails_final_handle_revalidation() {
        let root = temp_root("drift");
        let b = binding();
        let snapshot = 41;
        let manifest = [0x11; 32];
        let (node, page) = files(&root, &b);
        let record = exact_record(&root, &node, &page, &b, snapshot, manifest);
        let observed = observe_storage_context_v2(&root, &node, &page, &b).unwrap();
        OpenOptions::new().write(true).open(&node).unwrap().set_len(1).unwrap();
        let err = match select_with_records_v2(&[record], observed, &b, snapshot, manifest) {
            Err(err) => err,
            Ok(_) => panic!("post-observation truncation must fail before lease"),
        };
        assert_eq!(err, MmapAdmissionErrorV2::FileIdentityChangedBeforeLease);
        remove_dir_all(root).unwrap();
    }

    #[test]
    fn malformed_geometry_fails_before_registry_resolution() {
        let root = temp_root("geometry");
        let b = binding();
        let (node, page) = files(&root, &b);
        OpenOptions::new().write(true).open(&node).unwrap().set_len(1).unwrap();
        let err = match admit_data_serving_backend_v2(&root, &node, &page, &b, 41, [0x11; 32]) {
            Err(err) => err,
            Ok(_) => panic!("malformed geometry must fail"),
        };
        assert!(matches!(err, MmapAdmissionErrorV2::NodeIndexLengthMismatch { .. }));
        remove_dir_all(root).unwrap();
    }

    #[test]
    fn file_outside_storage_root_is_rejected() {
        let root = temp_root("root");
        let other = temp_root("outside");
        let b = binding();
        let (node, _) = files(&root, &b);
        let (_, outside_page) = files(&other, &b);
        let err = match admit_data_serving_backend_v2(&root, &node, &outside_page, &b, 41, [0x11; 32]) {
            Err(err) => err,
            Ok(_) => panic!("outside page must fail"),
        };
        assert_eq!(err, MmapAdmissionErrorV2::PathOutsideStorageRoot);
        remove_dir_all(root).unwrap();
        remove_dir_all(other).unwrap();
    }
}
