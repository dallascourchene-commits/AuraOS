#![forbid(unsafe_code)]

//! Conservative crash-state reconstitution for immutable Aura K27 ASTGE generations.
//!
//! This crate does not create another storage ABI and does not parse PR471 manifests.
//! It delegates the only positive serving decision to PR471's existing
//! `ImmutableMmapReader::open_current` validation. Everything else is inventory:
//! complete-looking generations not selected by a valid CURRENT are orphans, temp
//! entries are crash residue, and a missing/invalid CURRENT is a HOLD rather than a
//! license to promote the numerically highest generation.

use aura_k27_astge_mmap::ImmutableMmapReader;
use std::fs;
use std::io;
use std::path::Path;

const CURRENT_FILE: &str = "CURRENT";
const FINAL_GENERATION_PREFIX: &str = "gen-";
const GENERATION_DIGITS: usize = 20;
const CURRENT_TEMP_PREFIX: &str = ".CURRENT.tmp-";

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CurrentRecoveryStateV1 {
    /// PR471's complete CURRENT -> manifest -> lengths -> digests -> generation
    /// validation succeeded. This is the only state that can identify a serving generation.
    ValidCommitted { snapshot_generation: u64 },
    /// No CURRENT exists. Final generation directories are not auto-promoted.
    Missing,
    /// CURRENT exists but PR471 refuses to open it or its selected generation.
    Invalid { reason: String },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RecoveryInventoryV1 {
    pub current_state: CurrentRecoveryStateV1,
    pub serving_generation: Option<u64>,
    pub final_generations: Vec<u64>,
    pub orphan_final_generations: Vec<u64>,
    pub temp_generation_entries: Vec<String>,
    pub current_temp_entries: Vec<String>,
    /// V1 never promotes an orphan merely because it is the highest generation.
    pub auto_promotion_permitted: bool,
    /// Hosted filesystem-state tests are not a physical power-loss durability proof.
    pub physical_crash_durability_proven: bool,
}

impl RecoveryInventoryV1 {
    pub fn hold_required(&self) -> bool {
        self.serving_generation.is_none()
    }
}

/// Inspect one ASTGE immutable-generation storage root after normal startup or a
/// suspected crash.
///
/// Positive serving authority is deliberately narrow: only the generation selected
/// by a CURRENT that PR471 can fully open is returned as `serving_generation`.
/// Numerically newer final directories, temp generations, and temp CURRENT files do
/// not gain serving status from their existence.
pub fn inspect_recovery_state(root: impl AsRef<Path>) -> io::Result<RecoveryInventoryV1> {
    let root = root.as_ref();
    let mut final_generations = Vec::new();
    let mut temp_generation_entries = Vec::new();
    let mut current_temp_entries = Vec::new();

    for entry in fs::read_dir(root)? {
        let entry = entry?;
        let file_name = entry.file_name();
        let Some(name) = file_name.to_str() else {
            continue;
        };
        let file_type = entry.file_type()?;

        if file_type.is_dir() {
            if let Some(generation) = parse_final_generation_name(name) {
                final_generations.push(generation);
                continue;
            }
            if is_temp_generation_name(name) {
                temp_generation_entries.push(name.to_owned());
                continue;
            }
        }
        if name.starts_with(CURRENT_TEMP_PREFIX) {
            current_temp_entries.push(name.to_owned());
        }
    }

    final_generations.sort_unstable();
    temp_generation_entries.sort();
    current_temp_entries.sort();

    let current_path = root.join(CURRENT_FILE);
    let (current_state, serving_generation) = if !current_path.exists() {
        (CurrentRecoveryStateV1::Missing, None)
    } else {
        match ImmutableMmapReader::open_current(root) {
            Ok(reader) => {
                let generation = reader.manifest().snapshot_generation;
                (
                    CurrentRecoveryStateV1::ValidCommitted {
                        snapshot_generation: generation,
                    },
                    Some(generation),
                )
            }
            Err(error) => (
                CurrentRecoveryStateV1::Invalid {
                    reason: error.to_string(),
                },
                None,
            ),
        }
    };

    let orphan_final_generations = final_generations
        .iter()
        .copied()
        .filter(|generation| Some(*generation) != serving_generation)
        .collect();

    Ok(RecoveryInventoryV1 {
        current_state,
        serving_generation,
        final_generations,
        orphan_final_generations,
        temp_generation_entries,
        current_temp_entries,
        auto_promotion_permitted: false,
        physical_crash_durability_proven: false,
    })
}

fn parse_final_generation_name(name: &str) -> Option<u64> {
    if name.len() != FINAL_GENERATION_PREFIX.len() + GENERATION_DIGITS {
        return None;
    }
    let digits = name.strip_prefix(FINAL_GENERATION_PREFIX)?;
    if !digits.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    digits.parse().ok()
}

fn is_temp_generation_name(name: &str) -> bool {
    let Some(rest) = name.strip_prefix(".gen-") else {
        return false;
    };
    let Some((digits, suffix)) = rest.split_once(".tmp-") else {
        return false;
    };
    digits.len() == GENERATION_DIGITS
        && digits.bytes().all(|byte| byte.is_ascii_digit())
        && !suffix.is_empty()
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge::{
        NodeIndexRecordV1, PageRow, PhysicalPageV1, StorageGenerationBindingV1, BLOCK_SIZE,
    };
    use aura_k27_astge_mmap::publish_generation;
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(0);

    fn temp_root(label: &str) -> PathBuf {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "aura-k27-astge-recovery-{label}-{}-{n}",
            std::process::id()
        ));
        fs::create_dir(&root).unwrap();
        root
    }

    fn digest(byte: u8) -> [u8; 32] {
        [byte; 32]
    }

    fn fixture() -> (StorageGenerationBindingV1, Vec<u8>, Vec<u8>) {
        let placement_generation = 41;
        let scheme = digest(0x5A);
        let binding = StorageGenerationBindingV1 {
            node_count: 1,
            page_count: 1,
            placement_generation,
            placement_scheme_digest: scheme,
        };
        let record = NodeIndexRecordV1 {
            node_id: 7,
            semantic_handle_digest: digest(7),
            pbn: 0,
            row: 0,
            out_degree: 0,
            file_id: 9,
            byte_start: 2,
            byte_end: 6,
        };
        let page = PhysicalPageV1 {
            pbn: 0,
            placement_generation,
            placement_scheme_digest: scheme,
            rows: vec![PageRow {
                first_edge: 0,
                degree: 0,
            }],
            targets: vec![],
            edge_kinds: vec![],
        }
        .encode()
        .unwrap();

        (binding, record.encode().to_vec(), page.to_vec())
    }

    fn publish(root: &Path, generation: u64) {
        let (binding, index, pages) = fixture();
        publish_generation(root, generation, binding, &index, &pages).unwrap();
    }

    #[test]
    fn clean_current_is_the_only_serving_generation() {
        let root = temp_root("clean");
        publish(&root, 1);
        let inventory = inspect_recovery_state(&root).unwrap();
        assert_eq!(Some(1), inventory.serving_generation);
        assert_eq!(vec![1], inventory.final_generations);
        assert!(inventory.orphan_final_generations.is_empty());
        assert!(!inventory.hold_required());
        assert!(!inventory.auto_promotion_permitted);
        assert!(!inventory.physical_crash_durability_proven);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn newer_complete_orphan_does_not_override_valid_old_current() {
        let root = temp_root("orphan-newer");
        publish(&root, 10);
        let old_current = fs::read(root.join(CURRENT_FILE)).unwrap();
        publish(&root, 11);
        fs::write(root.join(CURRENT_FILE), old_current).unwrap();

        let inventory = inspect_recovery_state(&root).unwrap();
        assert_eq!(Some(10), inventory.serving_generation);
        assert_eq!(vec![10, 11], inventory.final_generations);
        assert_eq!(vec![11], inventory.orphan_final_generations);
        assert!(!inventory.hold_required());
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn missing_current_holds_even_with_one_complete_generation() {
        let root = temp_root("missing-current");
        publish(&root, 20);
        fs::remove_file(root.join(CURRENT_FILE)).unwrap();

        let inventory = inspect_recovery_state(&root).unwrap();
        assert_eq!(CurrentRecoveryStateV1::Missing, inventory.current_state);
        assert_eq!(None, inventory.serving_generation);
        assert_eq!(vec![20], inventory.orphan_final_generations);
        assert!(inventory.hold_required());
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn invalid_current_holds_instead_of_selecting_highest_generation() {
        let root = temp_root("invalid-current");
        publish(&root, 30);
        publish(&root, 31);
        fs::write(root.join(CURRENT_FILE), b"not-a-current-pointer\n").unwrap();

        let inventory = inspect_recovery_state(&root).unwrap();
        assert!(matches!(
            inventory.current_state,
            CurrentRecoveryStateV1::Invalid { .. }
        ));
        assert_eq!(None, inventory.serving_generation);
        assert_eq!(vec![30, 31], inventory.orphan_final_generations);
        assert!(inventory.hold_required());
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn temp_generation_and_current_entries_are_inventory_only() {
        let root = temp_root("temp-residue");
        fs::create_dir(root.join(".gen-00000000000000000040.tmp-crash")).unwrap();
        fs::write(root.join(".CURRENT.tmp-crash"), b"partial").unwrap();

        let inventory = inspect_recovery_state(&root).unwrap();
        assert_eq!(CurrentRecoveryStateV1::Missing, inventory.current_state);
        assert_eq!(None, inventory.serving_generation);
        assert_eq!(
            vec![".gen-00000000000000000040.tmp-crash".to_owned()],
            inventory.temp_generation_entries
        );
        assert_eq!(
            vec![".CURRENT.tmp-crash".to_owned()],
            inventory.current_temp_entries
        );
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn corrupt_current_generation_fails_closed_even_if_directory_name_is_valid() {
        let root = temp_root("corrupt-current");
        publish(&root, 50);
        let page_path = root
            .join("gen-00000000000000000050")
            .join("pages.bin");
        let mut permissions = fs::metadata(&page_path).unwrap().permissions();
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            permissions.set_mode(0o644);
        }
        #[cfg(not(unix))]
        permissions.set_readonly(false);
        fs::set_permissions(&page_path, permissions).unwrap();
        let mut bytes = fs::read(&page_path).unwrap();
        bytes[100] ^= 0x01;
        fs::write(&page_path, bytes).unwrap();

        let inventory = inspect_recovery_state(&root).unwrap();
        assert!(matches!(
            inventory.current_state,
            CurrentRecoveryStateV1::Invalid { .. }
        ));
        assert_eq!(None, inventory.serving_generation);
        assert_eq!(vec![50], inventory.orphan_final_generations);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn malformed_generation_names_never_enter_recovery_candidates() {
        let root = temp_root("names");
        fs::create_dir(root.join("gen-1")).unwrap();
        fs::create_dir(root.join("gen-0000000000000000000x")).unwrap();
        fs::create_dir(root.join(".gen-bad.tmp-crash")).unwrap();

        let inventory = inspect_recovery_state(&root).unwrap();
        assert!(inventory.final_generations.is_empty());
        assert!(inventory.temp_generation_entries.is_empty());
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn two_complete_generations_without_current_remain_hold_not_guess() {
        let root = temp_root("two-orphans");
        publish(&root, 60);
        publish(&root, 61);
        fs::remove_file(root.join(CURRENT_FILE)).unwrap();

        let inventory = inspect_recovery_state(&root).unwrap();
        assert_eq!(None, inventory.serving_generation);
        assert_eq!(vec![60, 61], inventory.orphan_final_generations);
        assert!(inventory.hold_required());
        assert!(!inventory.auto_promotion_permitted);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn page_contract_width_remains_inherited_not_redefined() {
        assert_eq!(4096, BLOCK_SIZE);
    }
}
