#![forbid(unsafe_code)]

//! AuraOS physical S-plane graph storage contract.
//!
//! This crate deliberately does **not** derive semantic identity or authority from K27.
//! Higher layers own semantic/source/currentness admission. The storage layer consumes an
//! opaque semantic-handle digest plus a scheme-qualified physical-placement digest and owns
//! only fixed-page layout and bounded graph reads.

use std::collections::{HashMap, HashSet, VecDeque};
use std::error::Error;
use std::fmt::{Display, Formatter};
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::path::Path;

pub const BLOCK_SIZE: usize = 4096;
pub const PAGE_MAGIC: [u8; 8] = *b"AURAK27S";
pub const PAGE_VERSION: u16 = 1;
pub const MAX_ROWS: usize = 256;
pub const MAX_EDGES: usize = 320;
pub const NODE_INDEX_RECORD_SIZE: usize = 64;

const HEADER_SIZE: usize = 64;
const ROW_ENTRY_SIZE: usize = 4;
const ROW_TABLE_OFFSET: usize = HEADER_SIZE;
const ROW_TABLE_SIZE: usize = MAX_ROWS * ROW_ENTRY_SIZE;
const TARGETS_OFFSET: usize = ROW_TABLE_OFFSET + ROW_TABLE_SIZE;
const TARGETS_SIZE: usize = MAX_EDGES * 8;
const KINDS_OFFSET: usize = TARGETS_OFFSET + TARGETS_SIZE;
const KINDS_SIZE: usize = MAX_EDGES;
const TRAILER_OFFSET: usize = KINDS_OFFSET + KINDS_SIZE;
const TRAILER_SIZE: usize = BLOCK_SIZE - TRAILER_OFFSET;

const _: () = assert!(HEADER_SIZE == 64);
const _: () = assert!(ROW_TABLE_SIZE == 1024);
const _: () = assert!(TARGETS_OFFSET == 1088);
const _: () = assert!(KINDS_OFFSET == 3648);
const _: () = assert!(TRAILER_OFFSET == 3968);
const _: () = assert!(TRAILER_SIZE == 128);

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StorageError {
    InvalidMagic,
    UnsupportedVersion(u16),
    RowCapacityExceeded(usize),
    EdgeCapacityExceeded(usize),
    EdgeVectorLengthMismatch,
    InvalidRowRange { row: usize, first_edge: usize, degree: usize, edge_count: usize },
    NonZeroReservedTrailer,
    InvalidNodeIndexLength(usize),
    DuplicateNodeId(u64),
    MissingRoot(u64),
    MissingTarget(u64),
    InvalidRowIndex { node_id: u64, row: usize, row_count: usize },
    NodeDegreeMismatch { node_id: u64, index_degree: u16, page_degree: u16 },
    PageNumberMismatch { requested: u64, encoded: u64 },
    ConeBudgetExceeded { max_nodes: usize },
    Io(String),
}

impl Display for StorageError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for StorageError {}

impl From<std::io::Error> for StorageError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value.to_string())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PageRow {
    pub first_edge: u16,
    pub degree: u16,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PhysicalPageV1 {
    /// Physical block number inside this storage generation.
    pub pbn: u64,
    /// Physical-placement generation only. It is not source/currentness authority.
    pub placement_generation: u64,
    /// Opaque digest supplied by the placement-scheme owner. This layer does not derive it.
    pub placement_scheme_digest: [u8; 32],
    pub rows: Vec<PageRow>,
    pub targets: Vec<u64>,
    pub edge_kinds: Vec<u8>,
}

impl PhysicalPageV1 {
    pub fn encode(&self) -> Result<[u8; BLOCK_SIZE], StorageError> {
        if self.rows.len() > MAX_ROWS {
            return Err(StorageError::RowCapacityExceeded(self.rows.len()));
        }
        if self.targets.len() > MAX_EDGES {
            return Err(StorageError::EdgeCapacityExceeded(self.targets.len()));
        }
        if self.targets.len() != self.edge_kinds.len() {
            return Err(StorageError::EdgeVectorLengthMismatch);
        }
        let edge_count = self.targets.len();
        validate_rows(&self.rows, edge_count)?;

        let mut page = [0u8; BLOCK_SIZE];
        page[0..8].copy_from_slice(&PAGE_MAGIC);
        put_u16(&mut page, 8, PAGE_VERSION);
        put_u16(&mut page, 10, 0); // flags reserved in V1
        put_u16(&mut page, 12, self.rows.len() as u16);
        put_u16(&mut page, 14, edge_count as u16);
        put_u64(&mut page, 16, self.pbn);
        put_u64(&mut page, 24, self.placement_generation);
        page[32..64].copy_from_slice(&self.placement_scheme_digest);

        for (i, row) in self.rows.iter().enumerate() {
            let offset = ROW_TABLE_OFFSET + i * ROW_ENTRY_SIZE;
            put_u16(&mut page, offset, row.first_edge);
            put_u16(&mut page, offset + 2, row.degree);
        }
        for (i, target) in self.targets.iter().enumerate() {
            put_u64(&mut page, TARGETS_OFFSET + i * 8, *target);
        }
        page[KINDS_OFFSET..KINDS_OFFSET + edge_count].copy_from_slice(&self.edge_kinds);
        // V1 trailer is reserved and therefore remains all-zero.
        Ok(page)
    }

    pub fn decode(page: &[u8; BLOCK_SIZE]) -> Result<Self, StorageError> {
        if page[0..8] != PAGE_MAGIC {
            return Err(StorageError::InvalidMagic);
        }
        let version = get_u16(page, 8);
        if version != PAGE_VERSION {
            return Err(StorageError::UnsupportedVersion(version));
        }
        let row_count = get_u16(page, 12) as usize;
        let edge_count = get_u16(page, 14) as usize;
        if row_count > MAX_ROWS {
            return Err(StorageError::RowCapacityExceeded(row_count));
        }
        if edge_count > MAX_EDGES {
            return Err(StorageError::EdgeCapacityExceeded(edge_count));
        }
        if page[TRAILER_OFFSET..].iter().any(|byte| *byte != 0) {
            return Err(StorageError::NonZeroReservedTrailer);
        }

        let mut scheme = [0u8; 32];
        scheme.copy_from_slice(&page[32..64]);
        let mut rows = Vec::with_capacity(row_count);
        for i in 0..row_count {
            let offset = ROW_TABLE_OFFSET + i * ROW_ENTRY_SIZE;
            rows.push(PageRow {
                first_edge: get_u16(page, offset),
                degree: get_u16(page, offset + 2),
            });
        }
        validate_rows(&rows, edge_count)?;

        let mut targets = Vec::with_capacity(edge_count);
        for i in 0..edge_count {
            targets.push(get_u64(page, TARGETS_OFFSET + i * 8));
        }
        let edge_kinds = page[KINDS_OFFSET..KINDS_OFFSET + edge_count].to_vec();

        Ok(Self {
            pbn: get_u64(page, 16),
            placement_generation: get_u64(page, 24),
            placement_scheme_digest: scheme,
            rows,
            targets,
            edge_kinds,
        })
    }
}

fn validate_rows(rows: &[PageRow], edge_count: usize) -> Result<(), StorageError> {
    for (row_idx, row) in rows.iter().enumerate() {
        let first = row.first_edge as usize;
        let degree = row.degree as usize;
        if first > edge_count || first.saturating_add(degree) > edge_count {
            return Err(StorageError::InvalidRowRange {
                row: row_idx,
                first_edge: first,
                degree,
                edge_count,
            });
        }
    }
    Ok(())
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NodeIndexRecordV1 {
    /// Storage-local node ID. It is not a semantic ID.
    pub node_id: u64,
    /// Opaque semantic handle digest issued by the higher semantic/source owner.
    pub semantic_handle_digest: [u8; 32],
    pub pbn: u64,
    pub row: u16,
    pub out_degree: u16,
    pub file_id: u32,
    pub byte_start: u32,
    pub byte_end: u32,
}

impl NodeIndexRecordV1 {
    pub fn encode(&self) -> [u8; NODE_INDEX_RECORD_SIZE] {
        let mut out = [0u8; NODE_INDEX_RECORD_SIZE];
        put_u64(&mut out, 0, self.node_id);
        out[8..40].copy_from_slice(&self.semantic_handle_digest);
        put_u64(&mut out, 40, self.pbn);
        put_u16(&mut out, 48, self.row);
        put_u16(&mut out, 50, self.out_degree);
        put_u32(&mut out, 52, self.file_id);
        put_u32(&mut out, 56, self.byte_start);
        put_u32(&mut out, 60, self.byte_end);
        out
    }

    pub fn decode(bytes: &[u8]) -> Result<Self, StorageError> {
        if bytes.len() != NODE_INDEX_RECORD_SIZE {
            return Err(StorageError::InvalidNodeIndexLength(bytes.len()));
        }
        let mut semantic_handle_digest = [0u8; 32];
        semantic_handle_digest.copy_from_slice(&bytes[8..40]);
        Ok(Self {
            node_id: get_u64(bytes, 0),
            semantic_handle_digest,
            pbn: get_u64(bytes, 40),
            row: get_u16(bytes, 48),
            out_degree: get_u16(bytes, 50),
            file_id: get_u32(bytes, 52),
            byte_start: get_u32(bytes, 56),
            byte_end: get_u32(bytes, 60),
        })
    }
}

pub trait PageSource {
    fn read_page(&mut self, pbn: u64) -> Result<[u8; BLOCK_SIZE], StorageError>;
}

pub struct FilePageSource {
    file: File,
    base_offset: u64,
}

impl FilePageSource {
    pub fn open(path: impl AsRef<Path>, base_offset: u64) -> Result<Self, StorageError> {
        Ok(Self {
            file: File::open(path)?,
            base_offset,
        })
    }
}

impl PageSource for FilePageSource {
    fn read_page(&mut self, pbn: u64) -> Result<[u8; BLOCK_SIZE], StorageError> {
        let offset = self
            .base_offset
            .checked_add(pbn.checked_mul(BLOCK_SIZE as u64).ok_or_else(|| {
                StorageError::Io("page offset overflow".to_string())
            })?)
            .ok_or_else(|| StorageError::Io("page offset overflow".to_string()))?;
        self.file.seek(SeekFrom::Start(offset))?;
        let mut page = [0u8; BLOCK_SIZE];
        self.file.read_exact(&mut page)?;
        Ok(page)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HydratedConeV1 {
    pub root_id: u64,
    pub node_ids: Vec<u64>,
    pub unique_pages: usize,
    pub edges_traversed: usize,
}

pub struct SPlaneGraphReader<S: PageSource> {
    index: HashMap<u64, NodeIndexRecordV1>,
    pages: S,
}

impl<S: PageSource> SPlaneGraphReader<S> {
    /// Builds an explicit node-id index. Record order is deliberately irrelevant.
    pub fn new(records: impl IntoIterator<Item = NodeIndexRecordV1>, pages: S) -> Result<Self, StorageError> {
        let mut index = HashMap::new();
        for record in records {
            let node_id = record.node_id;
            if index.insert(node_id, record).is_some() {
                return Err(StorageError::DuplicateNodeId(node_id));
            }
        }
        Ok(Self { index, pages })
    }

    /// Hydrates a bounded physical graph cone.
    ///
    /// This method performs no semantic/currentness/authority admission. The caller must first
    /// provide an already-admitted root and index generation from the owning AuraOS layer.
    pub fn query_cone(
        &mut self,
        root_id: u64,
        max_depth: usize,
        max_nodes: usize,
        edge_kind_filter: Option<u8>,
    ) -> Result<HydratedConeV1, StorageError> {
        if max_nodes == 0 {
            return Err(StorageError::ConeBudgetExceeded { max_nodes });
        }
        if !self.index.contains_key(&root_id) {
            return Err(StorageError::MissingRoot(root_id));
        }

        let mut queue = VecDeque::from([(root_id, 0usize)]);
        let mut visited = HashSet::from([root_id]);
        let mut node_ids = Vec::new();
        let mut unique_pages = HashSet::new();
        let mut edges_traversed = 0usize;

        while let Some((node_id, depth)) = queue.pop_front() {
            if node_ids.len() >= max_nodes {
                return Err(StorageError::ConeBudgetExceeded { max_nodes });
            }
            let record = self.index.get(&node_id).cloned().ok_or(StorageError::MissingTarget(node_id))?;
            node_ids.push(node_id);

            if depth >= max_depth || record.out_degree == 0 {
                continue;
            }

            let raw_page = self.pages.read_page(record.pbn)?;
            let page = PhysicalPageV1::decode(&raw_page)?;
            if page.pbn != record.pbn {
                return Err(StorageError::PageNumberMismatch {
                    requested: record.pbn,
                    encoded: page.pbn,
                });
            }
            unique_pages.insert(record.pbn);
            let row_index = record.row as usize;
            if row_index >= page.rows.len() {
                return Err(StorageError::InvalidRowIndex {
                    node_id,
                    row: row_index,
                    row_count: page.rows.len(),
                });
            }
            let row = page.rows[row_index];
            if row.degree != record.out_degree {
                return Err(StorageError::NodeDegreeMismatch {
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
                    return Err(StorageError::MissingTarget(target));
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

fn put_u16(buf: &mut [u8], offset: usize, value: u16) {
    buf[offset..offset + 2].copy_from_slice(&value.to_le_bytes());
}
fn put_u32(buf: &mut [u8], offset: usize, value: u32) {
    buf[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
}
fn put_u64(buf: &mut [u8], offset: usize, value: u64) {
    buf[offset..offset + 8].copy_from_slice(&value.to_le_bytes());
}
fn get_u16(buf: &[u8], offset: usize) -> u16 {
    u16::from_le_bytes(buf[offset..offset + 2].try_into().expect("slice width"))
}
fn get_u32(buf: &[u8], offset: usize) -> u32 {
    u32::from_le_bytes(buf[offset..offset + 4].try_into().expect("slice width"))
}
fn get_u64(buf: &[u8], offset: usize) -> u64 {
    u64::from_le_bytes(buf[offset..offset + 8].try_into().expect("slice width"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Default)]
    struct MemoryPages(HashMap<u64, [u8; BLOCK_SIZE]>);

    impl PageSource for MemoryPages {
        fn read_page(&mut self, pbn: u64) -> Result<[u8; BLOCK_SIZE], StorageError> {
            self.0.get(&pbn).copied().ok_or_else(|| StorageError::Io(format!("missing page {pbn}")))
        }
    }

    fn digest(byte: u8) -> [u8; 32] {
        [byte; 32]
    }

    fn page(pbn: u64, generation: u64, rows: Vec<PageRow>, targets: Vec<u64>, kinds: Vec<u8>) -> [u8; BLOCK_SIZE] {
        PhysicalPageV1 {
            pbn,
            placement_generation: generation,
            placement_scheme_digest: digest(0xAA),
            rows,
            targets,
            edge_kinds: kinds,
        }
        .encode()
        .unwrap()
    }

    fn node(node_id: u64, semantic: u8, pbn: u64, row: u16, degree: u16) -> NodeIndexRecordV1 {
        NodeIndexRecordV1 {
            node_id,
            semantic_handle_digest: digest(semantic),
            pbn,
            row,
            out_degree: degree,
            file_id: 7,
            byte_start: node_id as u32 * 10,
            byte_end: node_id as u32 * 10 + 5,
        }
    }

    #[test]
    fn physical_page_is_exactly_4096_bytes_and_round_trips() {
        let raw = page(
            9,
            3,
            vec![PageRow { first_edge: 0, degree: 2 }],
            vec![11, 12],
            vec![0, 2],
        );
        assert_eq!(raw.len(), BLOCK_SIZE);
        let decoded = PhysicalPageV1::decode(&raw).unwrap();
        assert_eq!(decoded.pbn, 9);
        assert_eq!(decoded.placement_generation, 3);
        assert_eq!(decoded.rows[0].degree, 2);
        assert_eq!(decoded.targets, vec![11, 12]);
    }

    #[test]
    fn malformed_magic_and_reserved_trailer_fail_closed() {
        let mut raw = page(0, 1, vec![], vec![], vec![]);
        raw[0] ^= 0xFF;
        assert_eq!(PhysicalPageV1::decode(&raw), Err(StorageError::InvalidMagic));

        let mut raw = page(0, 1, vec![], vec![], vec![]);
        raw[TRAILER_OFFSET] = 1;
        assert_eq!(PhysicalPageV1::decode(&raw), Err(StorageError::NonZeroReservedTrailer));
    }

    #[test]
    fn node_index_record_is_exactly_64_bytes_and_round_trips() {
        let record = node(42, 0x44, 5, 7, 3);
        let raw = record.encode();
        assert_eq!(raw.len(), NODE_INDEX_RECORD_SIZE);
        assert_eq!(NodeIndexRecordV1::decode(&raw).unwrap(), record);
    }

    #[test]
    fn query_does_not_assume_table_order_equals_node_id() {
        let mut pages = MemoryPages::default();
        pages.0.insert(
            10,
            page(
                10,
                1,
                vec![
                    PageRow { first_edge: 0, degree: 2 },
                    PageRow { first_edge: 2, degree: 1 },
                ],
                vec![1, 2, 2],
                vec![0, 0, 0],
            ),
        );
        pages.0.insert(11, page(11, 1, vec![PageRow { first_edge: 0, degree: 0 }], vec![], vec![]));

        // Intentionally post-order-like storage order: node 2 appears before root node 0.
        let records = vec![node(2, 0x22, 11, 0, 0), node(0, 0x00, 10, 0, 2), node(1, 0x11, 10, 1, 1)];
        let mut reader = SPlaneGraphReader::new(records, pages).unwrap();
        let cone = reader.query_cone(0, 2, 8, Some(0)).unwrap();
        assert_eq!(cone.node_ids, vec![0, 1, 2]);
        assert_eq!(cone.unique_pages, 1); // page 11 is not read because node 2 has degree 0
        assert_eq!(cone.edges_traversed, 3);
    }

    #[test]
    fn page_number_is_absolute_within_storage_generation() {
        let mut pages = MemoryPages::default();
        pages.0.insert(7, page(7, 4, vec![PageRow { first_edge: 0, degree: 1 }], vec![8], vec![1]));
        pages.0.insert(8, page(8, 4, vec![PageRow { first_edge: 0, degree: 0 }], vec![], vec![]));
        let records = vec![node(7, 0x70, 7, 0, 1), node(8, 0x80, 8, 0, 0)];
        let mut reader = SPlaneGraphReader::new(records, pages).unwrap();
        let cone = reader.query_cone(7, 1, 4, None).unwrap();
        assert_eq!(cone.node_ids, vec![7, 8]);
        assert_eq!(cone.unique_pages, 1);
    }

    #[test]
    fn placement_generation_can_change_without_changing_semantic_handle() {
        let record = node(1, 0x5A, 4, 0, 0);
        let semantic_before = record.semantic_handle_digest;
        let p1 = PhysicalPageV1 {
            pbn: 4,
            placement_generation: 1,
            placement_scheme_digest: digest(1),
            rows: vec![PageRow { first_edge: 0, degree: 0 }],
            targets: vec![],
            edge_kinds: vec![],
        };
        let p2 = PhysicalPageV1 { placement_generation: 2, placement_scheme_digest: digest(2), ..p1.clone() };
        assert_ne!(p1.encode().unwrap(), p2.encode().unwrap());
        assert_eq!(record.semantic_handle_digest, semantic_before);
    }

    #[test]
    fn cone_budget_fails_closed_instead_of_truncating_required_graph() {
        let mut pages = MemoryPages::default();
        pages.0.insert(0, page(0, 1, vec![PageRow { first_edge: 0, degree: 2 }], vec![1, 2], vec![0, 0]));
        let records = vec![node(0, 0, 0, 0, 2), node(1, 1, 0, 0, 0), node(2, 2, 0, 0, 0)];
        let mut reader = SPlaneGraphReader::new(records, pages).unwrap();
        assert_eq!(reader.query_cone(0, 1, 2, None), Err(StorageError::ConeBudgetExceeded { max_nodes: 2 }));
    }
}
