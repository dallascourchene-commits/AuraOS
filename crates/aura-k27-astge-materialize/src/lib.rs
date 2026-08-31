#![forbid(unsafe_code)]

//! File-ID -> exact source materialization for Aura K27 ASTGE.
//!
//! The storage layer carries a compact `file_id` and byte span. This membrane makes
//! that pair useful without treating a caller-provided path as truth: a higher
//! source/currentness owner must first admit a catalog entry binding file ID to a
//! portable repo-relative path, source generation, exact length, and SHA-256.
//! Materialization revalidates those bytes before returning the requested span.

use aura_k27_astge::NodeIndexRecordV1;
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::error::Error;
use std::fmt::{Display, Formatter};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceLocatorV1 {
    pub file_id: u32,
    /// Portable repo-relative path using `/` separators only.
    pub relative_path: String,
    /// Currentness generation supplied by the source owner, never minted here.
    pub source_generation: u64,
    pub byte_len: u64,
    pub sha256: [u8; 32],
}

impl SourceLocatorV1 {
    pub fn bind(
        file_id: u32,
        relative_path: impl Into<String>,
        source_generation: u64,
        bytes: &[u8],
    ) -> Self {
        Self {
            file_id,
            relative_path: relative_path.into(),
            source_generation,
            byte_len: bytes.len() as u64,
            sha256: sha256(bytes),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MaterializedSourceSliceV1 {
    pub file_id: u32,
    pub relative_path: String,
    pub source_generation: u64,
    pub source_sha256: [u8; 32],
    pub byte_start: u32,
    pub byte_end: u32,
    pub bytes: Vec<u8>,
    pub source_currentness_verified: bool,
    pub semantic_identity_proven: bool,
    pub authority_granted: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MaterializeError {
    RootNotDirectory,
    InvalidRelativePath(String),
    DuplicateFileId(u32),
    DuplicateRelativePath(String),
    MissingPath(String),
    SymlinkInSourcePath(String),
    PathComponentNotDirectory(String),
    TargetNotRegularFile(String),
    LengthMismatch {
        file_id: u32,
        expected: u64,
        actual: u64,
    },
    DigestMismatch(u32),
    UnknownFileId(u32),
    InvalidNodeSpan {
        file_id: u32,
        start: u32,
        end: u32,
        source_len: u64,
    },
    Io(String),
}

impl Display for MaterializeError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for MaterializeError {}

impl From<std::io::Error> for MaterializeError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value.to_string())
    }
}

#[derive(Debug, Clone)]
pub struct AdmittedSourceCatalogV1 {
    root: PathBuf,
    by_file_id: HashMap<u32, SourceLocatorV1>,
}

impl AdmittedSourceCatalogV1 {
    /// Admit the exact source files referenced by ASTGE records.
    ///
    /// Paths use a deliberately narrow portable grammar. Every component below the
    /// root is checked with `symlink_metadata`, so a symlink cannot turn a harmless
    /// relative locator into an escape or alias after lexical admission.
    pub fn admit(
        root: impl AsRef<Path>,
        locators: impl IntoIterator<Item = SourceLocatorV1>,
    ) -> Result<Self, MaterializeError> {
        let root = fs::canonicalize(root)?;
        if !fs::metadata(&root)?.is_dir() {
            return Err(MaterializeError::RootNotDirectory);
        }

        let mut by_file_id = HashMap::new();
        let mut paths = HashSet::new();
        for locator in locators {
            validate_relative_path(&locator.relative_path)?;
            if by_file_id.contains_key(&locator.file_id) {
                return Err(MaterializeError::DuplicateFileId(locator.file_id));
            }
            if !paths.insert(locator.relative_path.clone()) {
                return Err(MaterializeError::DuplicateRelativePath(
                    locator.relative_path,
                ));
            }
            verify_locator_file(&root, &locator)?;
            by_file_id.insert(locator.file_id, locator);
        }

        Ok(Self { root, by_file_id })
    }

    pub fn locator(&self, file_id: u32) -> Option<&SourceLocatorV1> {
        self.by_file_id.get(&file_id)
    }

    /// Revalidate and materialize the exact source bytes referenced by one S-plane
    /// node record. The storage-local node ID and semantic-handle digest are not used
    /// to guess a path or to mint source identity.
    pub fn materialize_node(
        &self,
        record: &NodeIndexRecordV1,
    ) -> Result<MaterializedSourceSliceV1, MaterializeError> {
        let locator = self
            .by_file_id
            .get(&record.file_id)
            .ok_or(MaterializeError::UnknownFileId(record.file_id))?;
        let bytes = verify_locator_file(&self.root, locator)?;
        if record.byte_start > record.byte_end || record.byte_end as u64 > locator.byte_len {
            return Err(MaterializeError::InvalidNodeSpan {
                file_id: record.file_id,
                start: record.byte_start,
                end: record.byte_end,
                source_len: locator.byte_len,
            });
        }
        let start = record.byte_start as usize;
        let end = record.byte_end as usize;
        Ok(MaterializedSourceSliceV1 {
            file_id: record.file_id,
            relative_path: locator.relative_path.clone(),
            source_generation: locator.source_generation,
            source_sha256: locator.sha256,
            byte_start: record.byte_start,
            byte_end: record.byte_end,
            bytes: bytes[start..end].to_vec(),
            source_currentness_verified: true,
            semantic_identity_proven: false,
            authority_granted: false,
        })
    }
}

fn validate_relative_path(path: &str) -> Result<(), MaterializeError> {
    if path.is_empty()
        || path.starts_with('/')
        || path.ends_with('/')
        || path.contains('\\')
        || path.contains(':')
        || path.chars().any(char::is_control)
    {
        return Err(MaterializeError::InvalidRelativePath(path.to_owned()));
    }
    if path
        .split('/')
        .any(|component| component.is_empty() || component == "." || component == "..")
    {
        return Err(MaterializeError::InvalidRelativePath(path.to_owned()));
    }
    Ok(())
}

fn verify_locator_file(
    root: &Path,
    locator: &SourceLocatorV1,
) -> Result<Vec<u8>, MaterializeError> {
    let components: Vec<&str> = locator.relative_path.split('/').collect();
    let mut current = root.to_path_buf();
    for (index, component) in components.iter().enumerate() {
        current.push(component);
        let metadata = fs::symlink_metadata(&current)
            .map_err(|_| MaterializeError::MissingPath(locator.relative_path.clone()))?;
        if metadata.file_type().is_symlink() {
            return Err(MaterializeError::SymlinkInSourcePath(
                locator.relative_path.clone(),
            ));
        }
        let is_last = index + 1 == components.len();
        if is_last {
            if !metadata.is_file() {
                return Err(MaterializeError::TargetNotRegularFile(
                    locator.relative_path.clone(),
                ));
            }
        } else if !metadata.is_dir() {
            return Err(MaterializeError::PathComponentNotDirectory(
                locator.relative_path.clone(),
            ));
        }
    }

    let bytes = fs::read(&current)?;
    if bytes.len() as u64 != locator.byte_len {
        return Err(MaterializeError::LengthMismatch {
            file_id: locator.file_id,
            expected: locator.byte_len,
            actual: bytes.len() as u64,
        });
    }
    if sha256(&bytes) != locator.sha256 {
        return Err(MaterializeError::DigestMismatch(locator.file_id));
    }
    Ok(bytes)
}

fn sha256(bytes: &[u8]) -> [u8; 32] {
    Sha256::digest(bytes).into()
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge_ingest::{encode_ast_to_splane, parse_python_named_ast};
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(0);
    const PYTHON: &str = "def add(a, b):\n    return a + b\n\nprint(add(1, 2))\n";

    fn temp_root(label: &str) -> PathBuf {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "aura-k27-materialize-{label}-{}-{n}",
            std::process::id()
        ));
        fs::create_dir_all(root.join("src")).unwrap();
        root
    }

    fn handles(node_count: usize) -> HashMap<u64, [u8; 32]> {
        (0..node_count)
            .map(|id| {
                let mut digest = [0u8; 32];
                digest[..8].copy_from_slice(&(id as u64).to_le_bytes());
                (id as u64, digest)
            })
            .collect()
    }

    fn encoded_records(file_id: u32) -> Vec<NodeIndexRecordV1> {
        let graph = parse_python_named_ast(PYTHON, file_id).unwrap();
        encode_ast_to_splane(&graph, &handles(graph.nodes.len()), 0, 1, [0x55; 32])
            .unwrap()
            .records
    }

    #[test]
    fn pr469_record_materializes_exact_bound_source_span() {
        let root = temp_root("roundtrip");
        fs::write(root.join("src/module.py"), PYTHON).unwrap();
        let locator = SourceLocatorV1::bind(77, "src/module.py", 9, PYTHON.as_bytes());
        let catalog = AdmittedSourceCatalogV1::admit(&root, [locator]).unwrap();
        let records = encoded_records(77);

        let root_slice = catalog.materialize_node(&records[0]).unwrap();
        assert_eq!(PYTHON.as_bytes(), root_slice.bytes.as_slice());
        assert_eq!("src/module.py", root_slice.relative_path);
        assert_eq!(9, root_slice.source_generation);
        assert!(root_slice.source_currentness_verified);
        assert!(!root_slice.semantic_identity_proven);
        assert!(!root_slice.authority_granted);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn file_id_selects_catalog_entry_not_hardcoded_filename() {
        let root = temp_root("two-files");
        let first = b"first = 1\n";
        let second = b"second = 2\n";
        fs::write(root.join("src/one.py"), first).unwrap();
        fs::write(root.join("src/two.py"), second).unwrap();
        let catalog = AdmittedSourceCatalogV1::admit(
            &root,
            [
                SourceLocatorV1::bind(1, "src/one.py", 1, first),
                SourceLocatorV1::bind(2, "src/two.py", 1, second),
            ],
        )
        .unwrap();
        let record = NodeIndexRecordV1 {
            node_id: 0,
            semantic_handle_digest: [0; 32],
            pbn: 0,
            row: 0,
            out_degree: 0,
            file_id: 2,
            byte_start: 0,
            byte_end: second.len() as u32,
        };
        let slice = catalog.materialize_node(&record).unwrap();
        assert_eq!(second, slice.bytes.as_slice());
        assert_eq!("src/two.py", slice.relative_path);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn source_drift_after_catalog_admission_fails_closed() {
        let root = temp_root("drift");
        fs::write(root.join("src/module.py"), PYTHON).unwrap();
        let catalog = AdmittedSourceCatalogV1::admit(
            &root,
            [SourceLocatorV1::bind(
                4,
                "src/module.py",
                2,
                PYTHON.as_bytes(),
            )],
        )
        .unwrap();
        fs::write(
            root.join("src/module.py"),
            PYTHON.replace("return a + b", "return a - b"),
        )
        .unwrap();
        let record = &encoded_records(4)[0];
        assert!(matches!(
            catalog.materialize_node(record),
            Err(MaterializeError::DigestMismatch(4))
                | Err(MaterializeError::LengthMismatch { file_id: 4, .. })
        ));
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn traversal_absolute_and_windows_style_paths_fail_admission() {
        let root = temp_root("paths");
        for bad in [
            "../outside.py",
            "/abs.py",
            "src/../x.py",
            "C:/x.py",
            "src\\x.py",
        ] {
            let result =
                AdmittedSourceCatalogV1::admit(&root, [SourceLocatorV1::bind(1, bad, 1, b"")]);
            assert_eq!(
                result.err(),
                Some(MaterializeError::InvalidRelativePath(bad.to_owned()))
            );
        }
        fs::remove_dir_all(root).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn symlinked_source_path_is_rejected() {
        use std::os::unix::fs::symlink;
        let root = temp_root("symlink");
        fs::write(root.join("real.py"), PYTHON).unwrap();
        symlink(root.join("real.py"), root.join("src/link.py")).unwrap();
        let result = AdmittedSourceCatalogV1::admit(
            &root,
            [SourceLocatorV1::bind(
                8,
                "src/link.py",
                1,
                PYTHON.as_bytes(),
            )],
        );
        assert_eq!(
            result.err(),
            Some(MaterializeError::SymlinkInSourcePath(
                "src/link.py".to_owned()
            ))
        );
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn duplicate_file_id_and_duplicate_path_fail_closed() {
        let root = temp_root("duplicates");
        fs::write(root.join("src/a.py"), b"a\n").unwrap();
        fs::write(root.join("src/b.py"), b"b\n").unwrap();

        let duplicate_id = AdmittedSourceCatalogV1::admit(
            &root,
            [
                SourceLocatorV1::bind(3, "src/a.py", 1, b"a\n"),
                SourceLocatorV1::bind(3, "src/b.py", 1, b"b\n"),
            ],
        );
        assert_eq!(
            duplicate_id.err(),
            Some(MaterializeError::DuplicateFileId(3))
        );

        let duplicate_path = AdmittedSourceCatalogV1::admit(
            &root,
            [
                SourceLocatorV1::bind(3, "src/a.py", 1, b"a\n"),
                SourceLocatorV1::bind(4, "src/a.py", 1, b"a\n"),
            ],
        );
        assert_eq!(
            duplicate_path.err(),
            Some(MaterializeError::DuplicateRelativePath(
                "src/a.py".to_owned()
            ))
        );
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn unknown_file_id_and_out_of_bounds_span_fail_closed() {
        let root = temp_root("record-errors");
        let bytes = b"abcde";
        fs::write(root.join("src/a.py"), bytes).unwrap();
        let catalog = AdmittedSourceCatalogV1::admit(
            &root,
            [SourceLocatorV1::bind(12, "src/a.py", 5, bytes)],
        )
        .unwrap();

        let mut record = NodeIndexRecordV1 {
            node_id: 0,
            semantic_handle_digest: [0; 32],
            pbn: 0,
            row: 0,
            out_degree: 0,
            file_id: 99,
            byte_start: 0,
            byte_end: 1,
        };
        assert_eq!(
            catalog.materialize_node(&record).err(),
            Some(MaterializeError::UnknownFileId(99))
        );
        record.file_id = 12;
        record.byte_start = 4;
        record.byte_end = 9;
        assert_eq!(
            catalog.materialize_node(&record).err(),
            Some(MaterializeError::InvalidNodeSpan {
                file_id: 12,
                start: 4,
                end: 9,
                source_len: 5,
            })
        );
        fs::remove_dir_all(root).unwrap();
    }
}
