#![forbid(unsafe_code)]

#[path = "lib.rs"]
mod v1;

pub use v1::*;

use std::collections::{HashMap, HashSet, VecDeque};
use std::error::Error;
use std::fmt::{Display, Formatter};
use std::fs::{metadata, File};
use std::io::{Read, Seek, SeekFrom};
use std::path::Path;

/// Physical-generation binding supplied by the owning AuraOS placement/currentness layer.
///
/// This is deliberately not semantic identity or authority. It only defines which concrete
/// node-index/page generation a data-serving reader is allowed to consume.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StorageGenerationBindingV1 {
    pub node_count: u64,
    pub page_count: u64,
    pub placement_generation: u64,
    pub placement_scheme_digest: [u8; 32],
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GenerationStorageError {
    Storage(StorageError),
    NotRegularFile,
    LengthOverflow,
    NodeIndexLengthMismatch { expected: u64, actual: u64 },
    PageFileLengthMismatch { expected: u64, actual: u64 },
    DuplicateNodeId(u64),
    IndexPageOutOfRange { node_id: u64, pbn: u64, page_count: u64 },
    PageOutOfRange { pbn: u64, page_count: u64 },
    PageNumberMismatch { requested: u64, encoded: u64 },
    PlacementGenerationMismatch { expected: u64, observed: u64 },
    PlacementSchemeMismatch,
    MissingRoot(u64),
    MissingTarget(u64),
    InvalidRowIndex { node_id: u64, row: usize, row_count: usize },
    NodeDegreeMismatch { node_id: u64, index_degree: u16, page_degree: u16 },
    ConeBudgetExceeded { max_nodes: usize },
    Io(String),
}

impl Display for GenerationStorageError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for GenerationStorageError {}

impl From<std::io::Error> for GenerationStorageError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value.to_string())
    }
}

impl From<StorageError> for GenerationStorageError {
    fn from(value: StorageError) -> Self {
        Self::Storage(value)
    }
}

fn exact_len(count: u64, width: usize) -> Result<u64, GenerationStorageError> {
    count
        .checked_mul(width as u64)
        .ok_or(GenerationStorageError::LengthOverflow)
}

fn require_regular_file(path: &Path) -> Result<u64, GenerationStorageError> {
    let meta = metadata(path)?;
    if !meta.is_file() {
        return Err(GenerationStorageError::NotRegularFile);
    }
    Ok(meta.len())
}

/// Load and structurally admit the complete node index before any query can consume it.
///
/// Page payloads remain out-of-core and are validated on first read; the compact node index is
/// the generation-level admission surface. This mirrors Aura's fail-closed reader law without
/// converting physical storage currentness into semantic currentness.
pub fn load_admitted_node_index(
    path: impl AsRef<Path>,
    binding: &StorageGenerationBindingV1,
) -> Result<HashMap<u64, NodeIndexRecordV1>, GenerationStorageError> {
    let path = path.as_ref();
    let actual = require_regular_file(path)?;
    let expected = exact_len(binding.node_count, NODE_INDEX_RECORD_SIZE)?;
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

    let mut file = File::open(path)?;
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
    Ok(index)
}

/// Read+Seek baseline whose every returned page is generation-bound before it reaches traversal.
/// A later mmap backend must be observationally equivalent to this boundary before it can replace it.
pub struct GenerationBoundFilePages {
    file: File,
    binding: StorageGenerationBindingV1,
}

impl GenerationBoundFilePages {
    pub fn open(
        path: impl AsRef<Path>,
        binding: StorageGenerationBindingV1,
    ) -> Result<Self, GenerationStorageError> {
        let path = path.as_ref();
        let actual = require_regular_file(path)?;
        let expected = exact_len(binding.page_count, BLOCK_SIZE)?;
        if actual != expected {
            return Err(GenerationStorageError::PageFileLengthMismatch { expected, actual });
        }
        Ok(Self {
            file: File::open(path)?,
            binding,
        })
    }

    pub fn read_bound_page(&mut self, pbn: u64) -> Result<PhysicalPageV1, GenerationStorageError> {
        if pbn >= self.binding.page_count {
            return Err(GenerationStorageError::PageOutOfRange {
                pbn,
                page_count: self.binding.page_count,
            });
        }
        let offset = pbn
            .checked_mul(BLOCK_SIZE as u64)
            .ok_or(GenerationStorageError::LengthOverflow)?;
        self.file.seek(SeekFrom::Start(offset))?;
        let mut raw = [0u8; BLOCK_SIZE];
        self.file.read_exact(&mut raw)?;
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
}

pub struct GenerationBoundGraphReader {
    index: HashMap<u64, NodeIndexRecordV1>,
    pages: GenerationBoundFilePages,
}

impl GenerationBoundGraphReader {
    pub fn open(
        node_index_path: impl AsRef<Path>,
        page_path: impl AsRef<Path>,
        binding: StorageGenerationBindingV1,
    ) -> Result<Self, GenerationStorageError> {
        let index = load_admitted_node_index(node_index_path, &binding)?;
        let pages = GenerationBoundFilePages::open(page_path, binding)?;
        Ok(Self { index, pages })
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

            let page = self.pages.read_bound_page(record.pbn)?;
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
mod generation_tests {
    use super::*;
    use std::fs::{remove_file, File};
    use std::io::Write;
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(0);

    fn digest(byte: u8) -> [u8; 32] {
        [byte; 32]
    }

    fn temp_path(label: &str) -> PathBuf {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        std::env::temp_dir().join(format!(
            "aura-k27-astge-{label}-{}-{n}.bin",
            std::process::id()
        ))
    }

    fn node(node_id: u64, semantic: u8, pbn: u64, row: u16, degree: u16) -> NodeIndexRecordV1 {
        NodeIndexRecordV1 {
            node_id,
            semantic_handle_digest: digest(semantic),
            pbn,
            row,
            out_degree: degree,
            file_id: 1,
            byte_start: node_id as u32 * 8,
            byte_end: node_id as u32 * 8 + 4,
        }
    }

    fn page(
        pbn: u64,
        generation: u64,
        scheme: u8,
        rows: Vec<PageRow>,
        targets: Vec<u64>,
        kinds: Vec<u8>,
    ) -> [u8; BLOCK_SIZE] {
        PhysicalPageV1 {
            pbn,
            placement_generation: generation,
            placement_scheme_digest: digest(scheme),
            rows,
            targets,
            edge_kinds: kinds,
        }
        .encode()
        .unwrap()
    }

    fn write_index(path: &Path, records: &[NodeIndexRecordV1]) {
        let mut file = File::create(path).unwrap();
        for record in records {
            file.write_all(&record.encode()).unwrap();
        }
        file.flush().unwrap();
    }

    fn write_pages(path: &Path, pages: &[[u8; BLOCK_SIZE]]) {
        let mut file = File::create(path).unwrap();
        for page in pages {
            file.write_all(page).unwrap();
        }
        file.flush().unwrap();
    }

    fn binding(nodes: u64, pages: u64) -> StorageGenerationBindingV1 {
        StorageGenerationBindingV1 {
            node_count: nodes,
            page_count: pages,
            placement_generation: 7,
            placement_scheme_digest: digest(0xA7),
        }
    }

    #[test]
    fn admitted_generation_opens_and_queries_exact_files() {
        let index_path = temp_path("happy-index");
        let page_path = temp_path("happy-pages");
        let records = vec![node(2, 2, 0, 2, 0), node(0, 0, 0, 0, 2), node(1, 1, 0, 1, 0)];
        write_index(&index_path, &records);
        write_pages(
            &page_path,
            &[page(
                0,
                7,
                0xA7,
                vec![
                    PageRow { first_edge: 0, degree: 2 },
                    PageRow { first_edge: 2, degree: 0 },
                    PageRow { first_edge: 2, degree: 0 },
                ],
                vec![1, 2],
                vec![0, 0],
            )],
        );
        let mut reader = GenerationBoundGraphReader::open(&index_path, &page_path, binding(3, 1)).unwrap();
        let cone = reader.query_cone(0, 1, 8, Some(0)).unwrap();
        assert_eq!(cone.node_ids, vec![0, 1, 2]);
        assert_eq!(cone.unique_pages, 1);
        assert_eq!(cone.edges_traversed, 2);
        let _ = remove_file(index_path);
        let _ = remove_file(page_path);
    }

    #[test]
    fn malformed_node_index_length_fails_before_query() {
        let index_path = temp_path("short-index");
        let page_path = temp_path("short-index-pages");
        File::create(&index_path).unwrap().write_all(&[1u8; 63]).unwrap();
        write_pages(&page_path, &[page(0, 7, 0xA7, vec![], vec![], vec![])]);
        assert_eq!(
            GenerationBoundGraphReader::open(&index_path, &page_path, binding(1, 1)).err(),
            Some(GenerationStorageError::NodeIndexLengthMismatch { expected: 64, actual: 63 })
        );
        let _ = remove_file(index_path);
        let _ = remove_file(page_path);
    }

    #[test]
    fn malformed_page_file_length_fails_before_query() {
        let index_path = temp_path("short-pages-index");
        let page_path = temp_path("short-pages");
        write_index(&index_path, &[node(0, 0, 0, 0, 0)]);
        File::create(&page_path).unwrap().write_all(&vec![0u8; BLOCK_SIZE - 1]).unwrap();
        assert_eq!(
            GenerationBoundGraphReader::open(&index_path, &page_path, binding(1, 1)).err(),
            Some(GenerationStorageError::PageFileLengthMismatch {
                expected: BLOCK_SIZE as u64,
                actual: (BLOCK_SIZE - 1) as u64,
            })
        );
        let _ = remove_file(index_path);
        let _ = remove_file(page_path);
    }

    #[test]
    fn duplicate_node_id_fails_during_generation_admission() {
        let index_path = temp_path("dup-index");
        let page_path = temp_path("dup-pages");
        write_index(&index_path, &[node(4, 1, 0, 0, 0), node(4, 2, 0, 0, 0)]);
        write_pages(&page_path, &[page(0, 7, 0xA7, vec![], vec![], vec![])]);
        assert_eq!(
            GenerationBoundGraphReader::open(&index_path, &page_path, binding(2, 1)).err(),
            Some(GenerationStorageError::DuplicateNodeId(4))
        );
        let _ = remove_file(index_path);
        let _ = remove_file(page_path);
    }

    #[test]
    fn index_page_outside_generation_fails_during_admission() {
        let index_path = temp_path("pbn-index");
        let page_path = temp_path("pbn-pages");
        write_index(&index_path, &[node(0, 0, 1, 0, 0)]);
        write_pages(&page_path, &[page(0, 7, 0xA7, vec![], vec![], vec![])]);
        assert_eq!(
            GenerationBoundGraphReader::open(&index_path, &page_path, binding(1, 1)).err(),
            Some(GenerationStorageError::IndexPageOutOfRange {
                node_id: 0,
                pbn: 1,
                page_count: 1,
            })
        );
        let _ = remove_file(index_path);
        let _ = remove_file(page_path);
    }

    #[test]
    fn placement_generation_mismatch_fails_on_first_data_read() {
        let index_path = temp_path("generation-index");
        let page_path = temp_path("generation-pages");
        write_index(&index_path, &[node(0, 0, 0, 0, 1), node(1, 1, 0, 1, 0)]);
        write_pages(
            &page_path,
            &[page(
                0,
                8,
                0xA7,
                vec![PageRow { first_edge: 0, degree: 1 }, PageRow { first_edge: 1, degree: 0 }],
                vec![1],
                vec![0],
            )],
        );
        let mut reader = GenerationBoundGraphReader::open(&index_path, &page_path, binding(2, 1)).unwrap();
        assert_eq!(
            reader.query_cone(0, 1, 4, None),
            Err(GenerationStorageError::PlacementGenerationMismatch { expected: 7, observed: 8 })
        );
        let _ = remove_file(index_path);
        let _ = remove_file(page_path);
    }

    #[test]
    fn placement_scheme_mismatch_fails_on_first_data_read() {
        let index_path = temp_path("scheme-index");
        let page_path = temp_path("scheme-pages");
        write_index(&index_path, &[node(0, 0, 0, 0, 1), node(1, 1, 0, 1, 0)]);
        write_pages(
            &page_path,
            &[page(
                0,
                7,
                0xB8,
                vec![PageRow { first_edge: 0, degree: 1 }, PageRow { first_edge: 1, degree: 0 }],
                vec![1],
                vec![0],
            )],
        );
        let mut reader = GenerationBoundGraphReader::open(&index_path, &page_path, binding(2, 1)).unwrap();
        assert_eq!(
            reader.query_cone(0, 1, 4, None),
            Err(GenerationStorageError::PlacementSchemeMismatch)
        );
        let _ = remove_file(index_path);
        let _ = remove_file(page_path);
    }

    #[test]
    fn page_number_mismatch_is_typed_and_fail_closed() {
        let index_path = temp_path("page-number-index");
        let page_path = temp_path("page-number-pages");
        write_index(&index_path, &[node(0, 0, 0, 0, 1), node(1, 1, 0, 1, 0)]);
        write_pages(
            &page_path,
            &[page(
                9,
                7,
                0xA7,
                vec![PageRow { first_edge: 0, degree: 1 }, PageRow { first_edge: 1, degree: 0 }],
                vec![1],
                vec![0],
            )],
        );
        let mut reader = GenerationBoundGraphReader::open(&index_path, &page_path, binding(2, 1)).unwrap();
        assert_eq!(
            reader.query_cone(0, 1, 4, None),
            Err(GenerationStorageError::PageNumberMismatch { requested: 0, encoded: 9 })
        );
        let _ = remove_file(index_path);
        let _ = remove_file(page_path);
    }
}
