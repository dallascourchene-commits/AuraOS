#![forbid(unsafe_code)]

#[path = "v2.rs"]
mod v2;

pub use v2::*;

use std::error::Error;
use std::fmt::{Display, Formatter};
use std::fs::{canonicalize, metadata, File};
use std::path::{Path, PathBuf};

#[cfg(unix)]
use std::os::unix::fs::MetadataExt;

/// The safe baseline stays Read+Seek. mmap is only a candidate backend when a
/// source-owned, independently verified immutability capability exactly binds
/// the current storage generation and the exact opened file identities.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DataServingBackendV1 {
    ReadSeekSafeDefault,
    MmapCapabilityGated,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BackendAdmissionReasonV1 {
    CapabilityUnavailable,
    CapabilityExactUnique,
    CapabilityAmbiguous,
    CapabilityRegistryInvalid,
    PlatformIdentityUnsupported,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GenerationOpenPolicyV1 {
    OpenVerifiedHandlesOnce,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExternalMutationDispositionV1 {
    ExcludedByOwnedStorageRoot,
    NotExcluded,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct BackingFileImmutabilityCapabilityV1 {
    pub capability_ref: &'static str,
    pub storage_root_device: u64,
    pub storage_root_inode: u64,
    pub snapshot_generation: u64,
    pub manifest_digest: [u8; 32],
    pub placement_scheme_digest: [u8; 32],
    pub node_file_device: u64,
    pub node_file_inode: u64,
    pub node_file_len: u64,
    pub page_file_device: u64,
    pub page_file_inode: u64,
    pub page_file_len: u64,
    pub generation_open_policy: GenerationOpenPolicyV1,
    pub replacement_generations_only: bool,
    pub no_in_place_write_truncate_reuse: bool,
    pub mapped_lifetime_within_capability: bool,
    pub platform_semantics_current: bool,
    pub filesystem_semantics_current: bool,
    pub external_mutation_disposition: ExternalMutationDispositionV1,
    pub independently_verified: bool,
    pub current: bool,
    pub revoked: bool,
    pub authority: bool,
    pub external_effect: bool,
}

/// Production trust root. Deliberately empty until Aura has an independently
/// verified owner/isolation capability for an exact published generation.
static CANONICAL_IMMUTABILITY_CAPABILITIES: &[BackingFileImmutabilityCapabilityV1] = &[];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MmapBackendAdmissionReceiptV1 {
    pub backend: DataServingBackendV1,
    pub reason: BackendAdmissionReasonV1,
    pub capability_ref: Option<&'static str>,
    pub exact_opened_file_identity_bound: bool,
    pub replacement_generations_only_proven: bool,
    pub no_in_place_mutation_proven: bool,
    pub mapped_lifetime_bounded: bool,
    pub human_authority: bool,
    pub external_effect: bool,
}

/// A positive mmap candidate carries the exact opened handles that were checked.
/// Downstream code must map these handles; path-based re-open would discard the
/// identity proof and is not represented by this API.
pub enum DataServingBackendAdmissionV1 {
    ReadSeekSafeDefault(MmapBackendAdmissionReceiptV1),
    MmapCapabilityGated {
        receipt: MmapBackendAdmissionReceiptV1,
        node_file: File,
        page_file: File,
    },
}

impl DataServingBackendAdmissionV1 {
    pub fn receipt(&self) -> &MmapBackendAdmissionReceiptV1 {
        match self {
            Self::ReadSeekSafeDefault(receipt) => receipt,
            Self::MmapCapabilityGated { receipt, .. } => receipt,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MmapAdmissionError {
    Io(String),
    StorageRootNotDirectory,
    PathOutsideStorageRoot,
    PathFdIdentityMismatch,
    NotRegularFile,
    LengthOverflow,
    NodeIndexLengthMismatch { expected: u64, actual: u64 },
    PageFileLengthMismatch { expected: u64, actual: u64 },
}

impl Display for MmapAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for MmapAdmissionError {}

impl From<std::io::Error> for MmapAdmissionError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value.to_string())
    }
}

#[derive(Debug)]
struct ObservedFileIdentityV1 {
    file: File,
    device: u64,
    inode: u64,
    len: u64,
}

#[derive(Debug)]
struct ObservedStorageContextV1 {
    root_device: u64,
    root_inode: u64,
    node: ObservedFileIdentityV1,
    page: ObservedFileIdentityV1,
}

fn exact_len(count: u64, width: usize) -> Result<u64, MmapAdmissionError> {
    count
        .checked_mul(width as u64)
        .ok_or(MmapAdmissionError::LengthOverflow)
}

fn canonical_child(root: &Path, child: &Path) -> Result<PathBuf, MmapAdmissionError> {
    let root = canonicalize(root)?;
    let child = canonicalize(child)?;
    if !child.starts_with(&root) {
        return Err(MmapAdmissionError::PathOutsideStorageRoot);
    }
    Ok(child)
}

#[cfg(unix)]
fn root_identity(root: &Path) -> Result<(u64, u64), MmapAdmissionError> {
    let meta = metadata(root)?;
    if !meta.is_dir() {
        return Err(MmapAdmissionError::StorageRootNotDirectory);
    }
    Ok((meta.dev(), meta.ino()))
}

#[cfg(not(unix))]
fn root_identity(_root: &Path) -> Result<(u64, u64), MmapAdmissionError> {
    Ok((0, 0))
}

#[cfg(unix)]
fn open_identity(path: &Path) -> Result<ObservedFileIdentityV1, MmapAdmissionError> {
    let file = File::open(path)?;
    let fd_meta = file.metadata()?;
    let path_meta = metadata(path)?;
    if !fd_meta.is_file() || !path_meta.is_file() {
        return Err(MmapAdmissionError::NotRegularFile);
    }
    if (fd_meta.dev(), fd_meta.ino()) != (path_meta.dev(), path_meta.ino()) {
        return Err(MmapAdmissionError::PathFdIdentityMismatch);
    }
    Ok(ObservedFileIdentityV1 {
        file,
        device: fd_meta.dev(),
        inode: fd_meta.ino(),
        len: fd_meta.len(),
    })
}

#[cfg(not(unix))]
fn open_identity(path: &Path) -> Result<ObservedFileIdentityV1, MmapAdmissionError> {
    let file = File::open(path)?;
    let meta = file.metadata()?;
    if !meta.is_file() {
        return Err(MmapAdmissionError::NotRegularFile);
    }
    Ok(ObservedFileIdentityV1 {
        file,
        device: 0,
        inode: 0,
        len: meta.len(),
    })
}

fn observe_storage_context(
    storage_root: &Path,
    node_index_path: &Path,
    page_path: &Path,
    binding: &StorageGenerationBindingV1,
) -> Result<ObservedStorageContextV1, MmapAdmissionError> {
    let root = canonicalize(storage_root)?;
    let node_path = canonical_child(&root, node_index_path)?;
    let page_path = canonical_child(&root, page_path)?;
    let (root_device, root_inode) = root_identity(&root)?;
    let node = open_identity(&node_path)?;
    let page = open_identity(&page_path)?;
    let expected_nodes = exact_len(binding.node_count, NODE_INDEX_RECORD_SIZE)?;
    let expected_pages = exact_len(binding.page_count, BLOCK_SIZE)?;
    if node.len != expected_nodes {
        return Err(MmapAdmissionError::NodeIndexLengthMismatch {
            expected: expected_nodes,
            actual: node.len,
        });
    }
    if page.len != expected_pages {
        return Err(MmapAdmissionError::PageFileLengthMismatch {
            expected: expected_pages,
            actual: page.len,
        });
    }
    Ok(ObservedStorageContextV1 {
        root_device,
        root_inode,
        node,
        page,
    })
}

fn structurally_valid_capability(record: &BackingFileImmutabilityCapabilityV1) -> bool {
    !record.capability_ref.trim().is_empty()
        && record.generation_open_policy == GenerationOpenPolicyV1::OpenVerifiedHandlesOnce
        && record.replacement_generations_only
        && record.no_in_place_write_truncate_reuse
        && record.mapped_lifetime_within_capability
        && !record.authority
        && !record.external_effect
}

fn active_capability(record: &BackingFileImmutabilityCapabilityV1) -> bool {
    record.current
        && !record.revoked
        && record.independently_verified
        && record.platform_semantics_current
        && record.filesystem_semantics_current
        && record.external_mutation_disposition
            == ExternalMutationDispositionV1::ExcludedByOwnedStorageRoot
}

fn exact_capability_match(
    record: &BackingFileImmutabilityCapabilityV1,
    observed: &ObservedStorageContextV1,
    binding: &StorageGenerationBindingV1,
    manifest_digest: [u8; 32],
) -> bool {
    record.storage_root_device == observed.root_device
        && record.storage_root_inode == observed.root_inode
        && record.snapshot_generation == binding.placement_generation
        && record.manifest_digest == manifest_digest
        && record.placement_scheme_digest == binding.placement_scheme_digest
        && record.node_file_device == observed.node.device
        && record.node_file_inode == observed.node.inode
        && record.node_file_len == observed.node.len
        && record.page_file_device == observed.page.device
        && record.page_file_inode == observed.page.inode
        && record.page_file_len == observed.page.len
}

fn safe_default(reason: BackendAdmissionReasonV1) -> DataServingBackendAdmissionV1 {
    DataServingBackendAdmissionV1::ReadSeekSafeDefault(MmapBackendAdmissionReceiptV1 {
        backend: DataServingBackendV1::ReadSeekSafeDefault,
        reason,
        capability_ref: None,
        exact_opened_file_identity_bound: false,
        replacement_generations_only_proven: false,
        no_in_place_mutation_proven: false,
        mapped_lifetime_bounded: false,
        human_authority: false,
        external_effect: false,
    })
}

fn select_with_records(
    records: &[BackingFileImmutabilityCapabilityV1],
    observed: ObservedStorageContextV1,
    binding: &StorageGenerationBindingV1,
    manifest_digest: [u8; 32],
) -> DataServingBackendAdmissionV1 {
    if records.iter().any(|record| !structurally_valid_capability(record)) {
        return safe_default(BackendAdmissionReasonV1::CapabilityRegistryInvalid);
    }

    #[cfg(not(unix))]
    {
        let _ = (records, observed, binding, manifest_digest);
        return safe_default(BackendAdmissionReasonV1::PlatformIdentityUnsupported);
    }

    #[cfg(unix)]
    {
        let matches: Vec<_> = records
            .iter()
            .filter(|record| active_capability(record))
            .filter(|record| exact_capability_match(record, &observed, binding, manifest_digest))
            .collect();
        if matches.len() > 1 {
            return safe_default(BackendAdmissionReasonV1::CapabilityAmbiguous);
        }
        let Some(record) = matches.first() else {
            return safe_default(BackendAdmissionReasonV1::CapabilityUnavailable);
        };
        DataServingBackendAdmissionV1::MmapCapabilityGated {
            receipt: MmapBackendAdmissionReceiptV1 {
                backend: DataServingBackendV1::MmapCapabilityGated,
                reason: BackendAdmissionReasonV1::CapabilityExactUnique,
                capability_ref: Some(record.capability_ref),
                exact_opened_file_identity_bound: true,
                replacement_generations_only_proven: true,
                no_in_place_mutation_proven: true,
                mapped_lifetime_bounded: true,
                human_authority: false,
                external_effect: false,
            },
            node_file: observed.node.file,
            page_file: observed.page.file,
        }
    }
}

/// Canonical consequence boundary. Callers provide paths/current owner generation
/// and manifest identity, but cannot provide capability records, registry lookup,
/// trust flags, mmap authorization or pre-opened files. Production resolves only
/// the source-owned capability registry, which is deliberately empty today.
pub fn admit_data_serving_backend(
    storage_root: impl AsRef<Path>,
    node_index_path: impl AsRef<Path>,
    page_path: impl AsRef<Path>,
    binding: &StorageGenerationBindingV1,
    manifest_digest: [u8; 32],
) -> Result<DataServingBackendAdmissionV1, MmapAdmissionError> {
    let observed = observe_storage_context(
        storage_root.as_ref(),
        node_index_path.as_ref(),
        page_path.as_ref(),
        binding,
    )?;
    Ok(select_with_records(
        CANONICAL_IMMUTABILITY_CAPABILITIES,
        observed,
        binding,
        manifest_digest,
    ))
}

#[cfg(test)]
mod tests {
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
            "aura-k27-astge-v3-{label}-{}-{nonce}",
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
        manifest_digest: [u8; 32],
    ) -> BackingFileImmutabilityCapabilityV1 {
        let root_meta = metadata(root).unwrap();
        let node_meta = metadata(node).unwrap();
        let page_meta = metadata(page).unwrap();
        BackingFileImmutabilityCapabilityV1 {
            capability_ref: "capability://astge/immutable-generation/7",
            storage_root_device: root_meta.dev(),
            storage_root_inode: root_meta.ino(),
            snapshot_generation: binding.placement_generation,
            manifest_digest,
            placement_scheme_digest: binding.placement_scheme_digest,
            node_file_device: node_meta.dev(),
            node_file_inode: node_meta.ino(),
            node_file_len: node_meta.len(),
            page_file_device: page_meta.dev(),
            page_file_inode: page_meta.ino(),
            page_file_len: page_meta.len(),
            generation_open_policy: GenerationOpenPolicyV1::OpenVerifiedHandlesOnce,
            replacement_generations_only: true,
            no_in_place_write_truncate_reuse: true,
            mapped_lifetime_within_capability: true,
            platform_semantics_current: true,
            filesystem_semantics_current: true,
            external_mutation_disposition: ExternalMutationDispositionV1::ExcludedByOwnedStorageRoot,
            independently_verified: true,
            current: true,
            revoked: false,
            authority: false,
            external_effect: false,
        }
    }

    #[test]
    fn production_registry_defaults_to_read_seek() {
        let root = temp_root("production-hold");
        let b = binding();
        let (node, page) = files(&root, &b);
        let out = admit_data_serving_backend(&root, &node, &page, &b, [0x11; 32]).unwrap();
        assert_eq!(out.receipt().backend, DataServingBackendV1::ReadSeekSafeDefault);
        assert_eq!(out.receipt().reason, BackendAdmissionReasonV1::CapabilityUnavailable);
        assert!(!out.receipt().human_authority);
        assert!(!out.receipt().external_effect);
        remove_dir_all(root).unwrap();
    }

    #[test]
    #[cfg(unix)]
    fn exact_private_capability_returns_same_verified_open_handles() {
        let root = temp_root("exact");
        let b = binding();
        let manifest = [0x11; 32];
        let (node, page) = files(&root, &b);
        let record = exact_record(&root, &node, &page, &b, manifest);
        let observed = observe_storage_context(&root, &node, &page, &b).unwrap();
        let expected_node = observed.node.inode;
        let expected_page = observed.page.inode;
        let out = select_with_records(&[record], observed, &b, manifest);
        match out {
            DataServingBackendAdmissionV1::MmapCapabilityGated { receipt, node_file, page_file } => {
                assert_eq!(receipt.reason, BackendAdmissionReasonV1::CapabilityExactUnique);
                assert_eq!(receipt.capability_ref, Some(record.capability_ref));
                assert!(receipt.exact_opened_file_identity_bound);
                assert!(!receipt.human_authority);
                assert!(!receipt.external_effect);
                assert_eq!(node_file.metadata().unwrap().ino(), expected_node);
                assert_eq!(page_file.metadata().unwrap().ino(), expected_page);
            }
            _ => panic!("exact capability should admit mmap candidate"),
        }
        remove_dir_all(root).unwrap();
    }

    #[test]
    #[cfg(unix)]
    fn generation_manifest_and_scheme_substitutions_fall_back() {
        let root = temp_root("bindings");
        let b = binding();
        let manifest = [0x11; 32];
        let (node, page) = files(&root, &b);
        let record = exact_record(&root, &node, &page, &b, manifest);
        for changed in [
            BackingFileImmutabilityCapabilityV1 { snapshot_generation: 8, ..record },
            BackingFileImmutabilityCapabilityV1 { manifest_digest: [0x33; 32], ..record },
            BackingFileImmutabilityCapabilityV1 { placement_scheme_digest: [0x44; 32], ..record },
        ] {
            let observed = observe_storage_context(&root, &node, &page, &b).unwrap();
            let out = select_with_records(&[changed], observed, &b, manifest);
            assert_eq!(out.receipt().backend, DataServingBackendV1::ReadSeekSafeDefault);
        }
        remove_dir_all(root).unwrap();
    }

    #[test]
    #[cfg(unix)]
    fn exact_file_identity_substitution_falls_back() {
        let root = temp_root("file-id");
        let b = binding();
        let manifest = [0x11; 32];
        let (node, page) = files(&root, &b);
        let record = exact_record(&root, &node, &page, &b, manifest);
        let replacements = [
            BackingFileImmutabilityCapabilityV1 { node_file_inode: record.node_file_inode + 1, ..record },
            BackingFileImmutabilityCapabilityV1 { page_file_inode: record.page_file_inode + 1, ..record },
            BackingFileImmutabilityCapabilityV1 { storage_root_inode: record.storage_root_inode + 1, ..record },
        ];
        for changed in replacements {
            let observed = observe_storage_context(&root, &node, &page, &b).unwrap();
            let out = select_with_records(&[changed], observed, &b, manifest);
            assert_eq!(out.receipt().reason, BackendAdmissionReasonV1::CapabilityUnavailable);
        }
        remove_dir_all(root).unwrap();
    }

    #[test]
    #[cfg(unix)]
    fn stale_revoked_unverified_or_unisolated_capability_does_not_admit_mmap() {
        let root = temp_root("inactive");
        let b = binding();
        let manifest = [0x11; 32];
        let (node, page) = files(&root, &b);
        let record = exact_record(&root, &node, &page, &b, manifest);
        let cases = [
            BackingFileImmutabilityCapabilityV1 { current: false, ..record },
            BackingFileImmutabilityCapabilityV1 { revoked: true, ..record },
            BackingFileImmutabilityCapabilityV1 { independently_verified: false, ..record },
            BackingFileImmutabilityCapabilityV1 { platform_semantics_current: false, ..record },
            BackingFileImmutabilityCapabilityV1 { filesystem_semantics_current: false, ..record },
            BackingFileImmutabilityCapabilityV1 {
                external_mutation_disposition: ExternalMutationDispositionV1::NotExcluded,
                ..record
            },
        ];
        for changed in cases {
            let observed = observe_storage_context(&root, &node, &page, &b).unwrap();
            let out = select_with_records(&[changed], observed, &b, manifest);
            assert_eq!(out.receipt().backend, DataServingBackendV1::ReadSeekSafeDefault);
        }
        remove_dir_all(root).unwrap();
    }

    #[test]
    #[cfg(unix)]
    fn malformed_source_owned_capability_poison_falls_back() {
        let root = temp_root("malformed");
        let b = binding();
        let manifest = [0x11; 32];
        let (node, page) = files(&root, &b);
        let record = exact_record(&root, &node, &page, &b, manifest);
        for changed in [
            BackingFileImmutabilityCapabilityV1 { capability_ref: "", ..record },
            BackingFileImmutabilityCapabilityV1 { replacement_generations_only: false, ..record },
            BackingFileImmutabilityCapabilityV1 { no_in_place_write_truncate_reuse: false, ..record },
            BackingFileImmutabilityCapabilityV1 { mapped_lifetime_within_capability: false, ..record },
            BackingFileImmutabilityCapabilityV1 { authority: true, ..record },
            BackingFileImmutabilityCapabilityV1 { external_effect: true, ..record },
        ] {
            let observed = observe_storage_context(&root, &node, &page, &b).unwrap();
            let out = select_with_records(&[changed], observed, &b, manifest);
            assert_eq!(out.receipt().reason, BackendAdmissionReasonV1::CapabilityRegistryInvalid);
        }
        remove_dir_all(root).unwrap();
    }

    #[test]
    #[cfg(unix)]
    fn two_exact_capabilities_are_ambiguous_and_fall_back() {
        let root = temp_root("ambiguous");
        let b = binding();
        let manifest = [0x11; 32];
        let (node, page) = files(&root, &b);
        let a = exact_record(&root, &node, &page, &b, manifest);
        let b_record = BackingFileImmutabilityCapabilityV1 {
            capability_ref: "capability://astge/immutable-generation/7/second",
            ..a
        };
        let observed = observe_storage_context(&root, &node, &page, &b).unwrap();
        let out = select_with_records(&[a, b_record], observed, &b, manifest);
        assert_eq!(out.receipt().backend, DataServingBackendV1::ReadSeekSafeDefault);
        assert_eq!(out.receipt().reason, BackendAdmissionReasonV1::CapabilityAmbiguous);
        remove_dir_all(root).unwrap();
    }

    #[test]
    fn geometry_is_checked_before_backend_selection() {
        let root = temp_root("geometry");
        let b = binding();
        let (node, page) = files(&root, &b);
        OpenOptions::new().write(true).open(&node).unwrap().set_len(1).unwrap();
        let err = match admit_data_serving_backend(&root, &node, &page, &b, [0x11; 32]) {
            Err(err) => err,
            Ok(_) => panic!("short node index must fail"),
        };
        assert!(matches!(err, MmapAdmissionError::NodeIndexLengthMismatch { .. }));
        remove_dir_all(root).unwrap();
    }

    #[test]
    fn file_outside_storage_root_is_rejected() {
        let root = temp_root("root");
        let other = temp_root("outside");
        let b = binding();
        let (node, _) = files(&root, &b);
        let (_, outside_page) = files(&other, &b);
        let err = match admit_data_serving_backend(&root, &node, &outside_page, &b, [0x11; 32]) {
            Err(err) => err,
            Ok(_) => panic!("outside page must fail"),
        };
        assert_eq!(err, MmapAdmissionError::PathOutsideStorageRoot);
        remove_dir_all(root).unwrap();
        remove_dir_all(other).unwrap();
    }
}
