use crate::coord::K27Coordinate;
use core::fmt;

pub const PAGE_SIZE: usize = 4096;
pub const NODE_RECORD_SIZE: usize = 64;
pub const MAX_CSR_ROWS: usize = 256;
pub const MAX_CSR_EDGES: usize = 384;

const CSR_MAGIC: &[u8; 8] = b"AK27CSR1";
const CSR_MAGIC_OFFSET: usize = 0;
const CSR_PBN_OFFSET: usize = 8;
const CSR_PREFIX_OFFSET: usize = 16;
const CSR_GENERATION_OFFSET: usize = 24;
const CSR_ROW_COUNT_OFFSET: usize = 28;
const CSR_EDGE_COUNT_OFFSET: usize = 30;
const CSR_ROW_OFFSETS_OFFSET: usize = 32;
const CSR_ROW_OFFSETS_BYTES: usize = (MAX_CSR_ROWS + 1) * 2;
const CSR_TARGETS_OFFSET: usize = CSR_ROW_OFFSETS_OFFSET + CSR_ROW_OFFSETS_BYTES;
const CSR_TARGETS_BYTES: usize = MAX_CSR_EDGES * 8;
const CSR_KINDS_OFFSET: usize = CSR_TARGETS_OFFSET + CSR_TARGETS_BYTES;
const CSR_KINDS_BYTES: usize = MAX_CSR_EDGES;
const CSR_PAYLOAD_END: usize = CSR_KINDS_OFFSET + CSR_KINDS_BYTES;

const NODE_SCHEMA_VERSION: u32 = 1;

const _: () = assert!(CSR_PAYLOAD_END <= PAGE_SIZE);
const _: () = assert!(NODE_RECORD_SIZE == 64);

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StorageError {
    PageFull,
    TooManyEdges { requested: usize, available: usize },
    InvalidPageLength { actual: usize },
    InvalidPageMagic,
    InvalidCsrBounds,
    InvalidNodeFrameLength { actual: usize },
    UnsupportedNodeSchema { actual: u32 },
    NonZeroReservedNodeBytes,
    InvalidCoordinate,
    NonContiguousNodeId { expected: u64, actual: u64 },
    NonContiguousPbn { expected: u64, actual: u64 },
    GenerationMismatch { expected: u32, actual: u32 },
    NodePageMissing { node_id: u64, pbn: u64 },
    NodeRowMissing { node_id: u64, row: u16 },
    DegreeMismatch { node_id: u64, expected: u16, actual: u16 },
}

impl fmt::Display for StorageError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::PageFull => write!(f, "CSR page row capacity exhausted"),
            Self::TooManyEdges { requested, available } => {
                write!(f, "requested {requested} CSR edges with only {available} slots available")
            }
            Self::InvalidPageLength { actual } => {
                write!(f, "CSR page has {actual} bytes instead of {PAGE_SIZE}")
            }
            Self::InvalidPageMagic => write!(f, "CSR page magic/version mismatch"),
            Self::InvalidCsrBounds => write!(f, "CSR row/edge bounds are inconsistent"),
            Self::InvalidNodeFrameLength { actual } => {
                write!(f, "node frame has {actual} bytes instead of {NODE_RECORD_SIZE}")
            }
            Self::UnsupportedNodeSchema { actual } => {
                write!(f, "unsupported node schema version {actual}")
            }
            Self::NonZeroReservedNodeBytes => write!(f, "node frame reserved bytes are nonzero"),
            Self::InvalidCoordinate => write!(f, "node contains an invalid packed K27 coordinate"),
            Self::NonContiguousNodeId { expected, actual } => {
                write!(f, "node table expected id {expected}, found {actual}")
            }
            Self::NonContiguousPbn { expected, actual } => {
                write!(f, "CSR segment expected PBN {expected}, found {actual}")
            }
            Self::GenerationMismatch { expected, actual } => {
                write!(f, "segment generation {expected} does not match record generation {actual}")
            }
            Self::NodePageMissing { node_id, pbn } => {
                write!(f, "node {node_id} references missing CSR page {pbn}")
            }
            Self::NodeRowMissing { node_id, row } => {
                write!(f, "node {node_id} references missing CSR row {row}")
            }
            Self::DegreeMismatch { node_id, expected, actual } => {
                write!(f, "node {node_id} declares degree {expected}, CSR row contains {actual}")
            }
        }
    }
}

impl std::error::Error for StorageError {}

#[derive(Clone, PartialEq, Eq)]
pub struct CsrPage {
    bytes: [u8; PAGE_SIZE],
}

impl fmt::Debug for CsrPage {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("CsrPage")
            .field("pbn", &self.pbn())
            .field("generation", &self.generation())
            .field("row_count", &self.row_count())
            .field("edge_count", &self.edge_count())
            .finish()
    }
}

impl CsrPage {
    pub fn new(pbn: u64, common_prefix: u64, generation: u32) -> Self {
        let mut page = Self { bytes: [0_u8; PAGE_SIZE] };
        page.bytes[CSR_MAGIC_OFFSET..CSR_MAGIC_OFFSET + 8].copy_from_slice(CSR_MAGIC);
        write_u64(&mut page.bytes, CSR_PBN_OFFSET, pbn);
        write_u64(&mut page.bytes, CSR_PREFIX_OFFSET, common_prefix);
        write_u32(&mut page.bytes, CSR_GENERATION_OFFSET, generation);
        page
    }

    pub fn from_bytes(bytes: &[u8]) -> Result<Self, StorageError> {
        if bytes.len() != PAGE_SIZE {
            return Err(StorageError::InvalidPageLength { actual: bytes.len() });
        }
        let mut owned = [0_u8; PAGE_SIZE];
        owned.copy_from_slice(bytes);
        let page = Self { bytes: owned };
        page.validate()?;
        Ok(page)
    }

    pub fn as_bytes(&self) -> &[u8; PAGE_SIZE] {
        &self.bytes
    }

    pub fn pbn(&self) -> u64 {
        read_u64(&self.bytes, CSR_PBN_OFFSET)
    }

    pub fn common_prefix(&self) -> u64 {
        read_u64(&self.bytes, CSR_PREFIX_OFFSET)
    }

    pub fn generation(&self) -> u32 {
        read_u32(&self.bytes, CSR_GENERATION_OFFSET)
    }

    pub fn row_count(&self) -> u16 {
        read_u16(&self.bytes, CSR_ROW_COUNT_OFFSET)
    }

    pub fn edge_count(&self) -> u16 {
        read_u16(&self.bytes, CSR_EDGE_COUNT_OFFSET)
    }

    pub fn can_fit_row(&self, edge_count: usize) -> bool {
        usize::from(self.row_count()) < MAX_CSR_ROWS
            && usize::from(self.edge_count()) + edge_count <= MAX_CSR_EDGES
    }

    pub fn push_row(&mut self, edges: &[(u64, u8)]) -> Result<u16, StorageError> {
        let row = usize::from(self.row_count());
        if row >= MAX_CSR_ROWS {
            return Err(StorageError::PageFull);
        }
        let start = usize::from(self.edge_count());
        let available = MAX_CSR_EDGES - start;
        if edges.len() > available {
            return Err(StorageError::TooManyEdges {
                requested: edges.len(),
                available,
            });
        }

        self.write_row_offset(row, start as u16);
        for (offset, (target, kind)) in edges.iter().copied().enumerate() {
            let edge_index = start + offset;
            write_u64(&mut self.bytes, CSR_TARGETS_OFFSET + edge_index * 8, target);
            self.bytes[CSR_KINDS_OFFSET + edge_index] = kind;
        }
        let end = start + edges.len();
        self.write_row_offset(row + 1, end as u16);
        write_u16(&mut self.bytes, CSR_ROW_COUNT_OFFSET, (row + 1) as u16);
        write_u16(&mut self.bytes, CSR_EDGE_COUNT_OFFSET, end as u16);
        Ok(row as u16)
    }

    pub fn row_edges(&self, row: u16) -> Result<Vec<(u64, u8)>, StorageError> {
        self.validate()?;
        let row = usize::from(row);
        if row >= usize::from(self.row_count()) {
            return Err(StorageError::InvalidCsrBounds);
        }
        let start = usize::from(self.read_row_offset(row));
        let end = usize::from(self.read_row_offset(row + 1));
        let mut edges = Vec::with_capacity(end - start);
        for edge_index in start..end {
            edges.push((
                read_u64(&self.bytes, CSR_TARGETS_OFFSET + edge_index * 8),
                self.bytes[CSR_KINDS_OFFSET + edge_index],
            ));
        }
        Ok(edges)
    }

    pub fn validate(&self) -> Result<(), StorageError> {
        if &self.bytes[CSR_MAGIC_OFFSET..CSR_MAGIC_OFFSET + 8] != CSR_MAGIC {
            return Err(StorageError::InvalidPageMagic);
        }
        let rows = usize::from(self.row_count());
        let edges = usize::from(self.edge_count());
        if rows > MAX_CSR_ROWS || edges > MAX_CSR_EDGES || self.read_row_offset(0) != 0 {
            return Err(StorageError::InvalidCsrBounds);
        }
        let mut previous = 0_usize;
        for row in 0..=rows {
            let offset = usize::from(self.read_row_offset(row));
            if offset < previous || offset > edges {
                return Err(StorageError::InvalidCsrBounds);
            }
            previous = offset;
        }
        if previous != edges {
            return Err(StorageError::InvalidCsrBounds);
        }
        Ok(())
    }

    fn read_row_offset(&self, row: usize) -> u16 {
        read_u16(&self.bytes, CSR_ROW_OFFSETS_OFFSET + row * 2)
    }

    fn write_row_offset(&mut self, row: usize, value: u16) {
        write_u16(&mut self.bytes, CSR_ROW_OFFSETS_OFFSET + row * 2, value);
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct NodeRecord {
    pub node_id: u64,
    pub coord_packed: u64,
    pub type_id: u32,
    pub file_id: u32,
    pub byte_start: u32,
    pub byte_end: u32,
    pub edge_block_pbn: u64,
    pub edge_row_idx: u16,
    pub out_degree: u16,
    pub generation: u32,
    pub flags: u32,
}

impl NodeRecord {
    pub fn encode(self) -> [u8; NODE_RECORD_SIZE] {
        let mut bytes = [0_u8; NODE_RECORD_SIZE];
        write_u64(&mut bytes, 0, self.node_id);
        write_u64(&mut bytes, 8, self.coord_packed);
        write_u32(&mut bytes, 16, self.type_id);
        write_u32(&mut bytes, 20, self.file_id);
        write_u32(&mut bytes, 24, self.byte_start);
        write_u32(&mut bytes, 28, self.byte_end);
        write_u64(&mut bytes, 32, self.edge_block_pbn);
        write_u16(&mut bytes, 40, self.edge_row_idx);
        write_u16(&mut bytes, 42, self.out_degree);
        write_u32(&mut bytes, 44, self.generation);
        write_u32(&mut bytes, 48, self.flags);
        write_u32(&mut bytes, 52, NODE_SCHEMA_VERSION);
        bytes
    }

    pub fn decode(bytes: &[u8]) -> Result<Self, StorageError> {
        if bytes.len() != NODE_RECORD_SIZE {
            return Err(StorageError::InvalidNodeFrameLength { actual: bytes.len() });
        }
        let schema = read_u32(bytes, 52);
        if schema != NODE_SCHEMA_VERSION {
            return Err(StorageError::UnsupportedNodeSchema { actual: schema });
        }
        if bytes[56..64].iter().any(|byte| *byte != 0) {
            return Err(StorageError::NonZeroReservedNodeBytes);
        }
        let record = Self {
            node_id: read_u64(bytes, 0),
            coord_packed: read_u64(bytes, 8),
            type_id: read_u32(bytes, 16),
            file_id: read_u32(bytes, 20),
            byte_start: read_u32(bytes, 24),
            byte_end: read_u32(bytes, 28),
            edge_block_pbn: read_u64(bytes, 32),
            edge_row_idx: read_u16(bytes, 40),
            out_degree: read_u16(bytes, 42),
            generation: read_u32(bytes, 44),
            flags: read_u32(bytes, 48),
        };
        K27Coordinate::from_packed(record.coord_packed)
            .map_err(|_| StorageError::InvalidCoordinate)?;
        Ok(record)
    }
}

#[derive(Debug, Clone)]
pub struct GraphSegment {
    base_node_id: u64,
    base_pbn: u64,
    generation: u32,
    nodes: Vec<NodeRecord>,
    pages: Vec<CsrPage>,
}

impl GraphSegment {
    pub fn from_parts(
        base_node_id: u64,
        base_pbn: u64,
        generation: u32,
        mut nodes: Vec<NodeRecord>,
        mut pages: Vec<CsrPage>,
    ) -> Result<Self, StorageError> {
        nodes.sort_by_key(|node| node.node_id);
        pages.sort_by_key(CsrPage::pbn);
        let segment = Self {
            base_node_id,
            base_pbn,
            generation,
            nodes,
            pages,
        };
        segment.validate()?;
        Ok(segment)
    }

    pub const fn base_node_id(&self) -> u64 {
        self.base_node_id
    }

    pub const fn base_pbn(&self) -> u64 {
        self.base_pbn
    }

    pub const fn generation(&self) -> u32 {
        self.generation
    }

    pub fn node_count(&self) -> usize {
        self.nodes.len()
    }

    pub fn page_count(&self) -> usize {
        self.pages.len()
    }

    pub fn next_node_id(&self) -> u64 {
        self.base_node_id + self.nodes.len() as u64
    }

    pub fn next_pbn(&self) -> u64 {
        self.base_pbn + self.pages.len() as u64
    }

    pub fn node_by_id(&self, node_id: u64) -> Option<&NodeRecord> {
        let relative = node_id.checked_sub(self.base_node_id)? as usize;
        let node = self.nodes.get(relative)?;
        (node.node_id == node_id).then_some(node)
    }

    pub fn page_by_pbn(&self, pbn: u64) -> Option<&CsrPage> {
        let relative = pbn.checked_sub(self.base_pbn)? as usize;
        let page = self.pages.get(relative)?;
        (page.pbn() == pbn).then_some(page)
    }

    pub fn node_table_bytes(&self) -> Vec<u8> {
        let mut bytes = Vec::with_capacity(self.nodes.len() * NODE_RECORD_SIZE);
        for node in &self.nodes {
            bytes.extend_from_slice(&node.encode());
        }
        bytes
    }

    pub fn csr_bytes(&self) -> Vec<u8> {
        let mut bytes = Vec::with_capacity(self.pages.len() * PAGE_SIZE);
        for page in &self.pages {
            bytes.extend_from_slice(page.as_bytes());
        }
        bytes
    }

    pub fn validate(&self) -> Result<(), StorageError> {
        for (index, page) in self.pages.iter().enumerate() {
            let expected_pbn = self.base_pbn + index as u64;
            if page.pbn() != expected_pbn {
                return Err(StorageError::NonContiguousPbn {
                    expected: expected_pbn,
                    actual: page.pbn(),
                });
            }
            if page.generation() != self.generation {
                return Err(StorageError::GenerationMismatch {
                    expected: self.generation,
                    actual: page.generation(),
                });
            }
            page.validate()?;
        }

        for (index, node) in self.nodes.iter().enumerate() {
            let expected_id = self.base_node_id + index as u64;
            if node.node_id != expected_id {
                return Err(StorageError::NonContiguousNodeId {
                    expected: expected_id,
                    actual: node.node_id,
                });
            }
            if node.generation != self.generation {
                return Err(StorageError::GenerationMismatch {
                    expected: self.generation,
                    actual: node.generation,
                });
            }
            K27Coordinate::from_packed(node.coord_packed)
                .map_err(|_| StorageError::InvalidCoordinate)?;
            let page = self
                .page_by_pbn(node.edge_block_pbn)
                .ok_or(StorageError::NodePageMissing {
                    node_id: node.node_id,
                    pbn: node.edge_block_pbn,
                })?;
            if usize::from(node.edge_row_idx) >= usize::from(page.row_count()) {
                return Err(StorageError::NodeRowMissing {
                    node_id: node.node_id,
                    row: node.edge_row_idx,
                });
            }
            let actual = page.row_edges(node.edge_row_idx)?.len() as u16;
            if actual != node.out_degree {
                return Err(StorageError::DegreeMismatch {
                    node_id: node.node_id,
                    expected: node.out_degree,
                    actual,
                });
            }
        }
        Ok(())
    }
}

#[derive(Debug)]
pub struct GraphSegmentBuilder {
    base_node_id: u64,
    base_pbn: u64,
    generation: u32,
    common_prefix: u64,
    nodes: Vec<NodeRecord>,
    pages: Vec<CsrPage>,
}

impl GraphSegmentBuilder {
    pub fn new(base_node_id: u64, base_pbn: u64, generation: u32, common_prefix: u64) -> Self {
        Self {
            base_node_id,
            base_pbn,
            generation,
            common_prefix,
            nodes: Vec::new(),
            pages: Vec::new(),
        }
    }

    pub fn append_node(
        &mut self,
        coord: K27Coordinate,
        type_id: u32,
        file_id: u32,
        byte_start: u32,
        byte_end: u32,
        flags: u32,
        edges: &[(u64, u8)],
    ) -> Result<u64, StorageError> {
        if edges.len() > MAX_CSR_EDGES {
            return Err(StorageError::TooManyEdges {
                requested: edges.len(),
                available: MAX_CSR_EDGES,
            });
        }
        if self
            .pages
            .last()
            .is_none_or(|page| !page.can_fit_row(edges.len()))
        {
            let pbn = self.base_pbn + self.pages.len() as u64;
            self.pages
                .push(CsrPage::new(pbn, self.common_prefix, self.generation));
        }
        let page = self.pages.last_mut().expect("page allocated above");
        let row = page.push_row(edges)?;
        let node_id = self.base_node_id + self.nodes.len() as u64;
        self.nodes.push(NodeRecord {
            node_id,
            coord_packed: coord.packed(),
            type_id,
            file_id,
            byte_start,
            byte_end,
            edge_block_pbn: page.pbn(),
            edge_row_idx: row,
            out_degree: edges.len() as u16,
            generation: self.generation,
            flags,
        });
        Ok(node_id)
    }

    pub fn finish(self) -> Result<GraphSegment, StorageError> {
        GraphSegment::from_parts(
            self.base_node_id,
            self.base_pbn,
            self.generation,
            self.nodes,
            self.pages,
        )
    }
}

fn read_u16(bytes: &[u8], offset: usize) -> u16 {
    u16::from_le_bytes(bytes[offset..offset + 2].try_into().expect("fixed u16 slice"))
}

fn read_u32(bytes: &[u8], offset: usize) -> u32 {
    u32::from_le_bytes(bytes[offset..offset + 4].try_into().expect("fixed u32 slice"))
}

fn read_u64(bytes: &[u8], offset: usize) -> u64 {
    u64::from_le_bytes(bytes[offset..offset + 8].try_into().expect("fixed u64 slice"))
}

fn write_u16(bytes: &mut [u8], offset: usize, value: u16) {
    bytes[offset..offset + 2].copy_from_slice(&value.to_le_bytes());
}

fn write_u32(bytes: &mut [u8], offset: usize, value: u32) {
    bytes[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
}

fn write_u64(bytes: &mut [u8], offset: usize, value: u64) {
    bytes[offset..offset + 8].copy_from_slice(&value.to_le_bytes());
}

#[cfg(test)]
mod tests {
    use super::*;

    fn zero_coord() -> K27Coordinate {
        K27Coordinate::default()
    }

    #[test]
    fn csr_page_is_exactly_one_4k_frame_and_round_trips_rows() {
        let mut page = CsrPage::new(7, 0x1234, 2);
        assert_eq!(page.as_bytes().len(), PAGE_SIZE);
        let row0 = page.push_row(&[(11, 0), (12, 1)]).unwrap();
        let row1 = page.push_row(&[(13, 3)]).unwrap();
        assert_eq!(row0, 0);
        assert_eq!(row1, 1);
        assert_eq!(page.row_edges(0).unwrap(), vec![(11, 0), (12, 1)]);
        assert_eq!(page.row_edges(1).unwrap(), vec![(13, 3)]);
        let decoded = CsrPage::from_bytes(page.as_bytes()).unwrap();
        assert_eq!(decoded, page);
    }

    #[test]
    fn row_and_edge_caps_fail_closed() {
        let mut page = CsrPage::new(0, 0, 1);
        page.push_row(&vec![(1, 0); MAX_CSR_EDGES]).unwrap();
        assert!(matches!(page.push_row(&[(2, 0)]), Err(StorageError::TooManyEdges { .. })));

        let mut page = CsrPage::new(1, 0, 1);
        for _ in 0..MAX_CSR_ROWS {
            page.push_row(&[]).unwrap();
        }
        assert!(matches!(page.push_row(&[]), Err(StorageError::PageFull)));
    }

    #[test]
    fn node_record_is_exactly_64_bytes_and_round_trips_without_rust_layout() {
        let record = NodeRecord {
            node_id: 99,
            coord_packed: zero_coord().packed(),
            type_id: 4,
            file_id: 5,
            byte_start: 10,
            byte_end: 20,
            edge_block_pbn: 77,
            edge_row_idx: 3,
            out_degree: 2,
            generation: 8,
            flags: 0xA5,
        };
        let encoded = record.encode();
        assert_eq!(encoded.len(), NODE_RECORD_SIZE);
        assert_eq!(NodeRecord::decode(&encoded).unwrap(), record);
    }

    #[test]
    fn segment_sorts_postorder_like_records_into_direct_id_lookup_order() {
        let mut page = CsrPage::new(40, 0, 3);
        page.push_row(&[]).unwrap();
        page.push_row(&[]).unwrap();
        let node0 = NodeRecord {
            node_id: 100,
            coord_packed: 0,
            type_id: 1,
            file_id: 1,
            byte_start: 0,
            byte_end: 4,
            edge_block_pbn: 40,
            edge_row_idx: 0,
            out_degree: 0,
            generation: 3,
            flags: 0,
        };
        let node1 = NodeRecord { node_id: 101, edge_row_idx: 1, ..node0 };
        let segment = GraphSegment::from_parts(100, 40, 3, vec![node1, node0], vec![page]).unwrap();
        assert_eq!(segment.node_by_id(100).unwrap().edge_row_idx, 0);
        assert_eq!(segment.node_by_id(101).unwrap().edge_row_idx, 1);
        assert_eq!(NodeRecord::decode(&segment.node_table_bytes()[..64]).unwrap().node_id, 100);
    }

    #[test]
    fn independent_append_generations_use_disjoint_node_and_page_coordinates() {
        let mut first = GraphSegmentBuilder::new(0, 10, 1, 0);
        assert_eq!(first.append_node(zero_coord(), 1, 1, 0, 1, 0, &[]).unwrap(), 0);
        assert_eq!(first.append_node(zero_coord(), 1, 1, 2, 3, 0, &[]).unwrap(), 1);
        let first = first.finish().unwrap();

        let mut second = GraphSegmentBuilder::new(first.next_node_id(), first.next_pbn(), 2, 0);
        assert_eq!(second.append_node(zero_coord(), 1, 1, 4, 5, 0, &[]).unwrap(), 2);
        let second = second.finish().unwrap();

        assert_eq!(first.base_pbn(), 10);
        assert_eq!(second.base_pbn(), 11);
        assert_eq!(first.node_by_id(0).unwrap().edge_block_pbn, 10);
        assert_eq!(second.node_by_id(2).unwrap().edge_block_pbn, 11);
        assert!(first.node_by_id(2).is_none());
        assert!(second.node_by_id(0).is_none());
    }

    #[test]
    fn segment_detects_degree_and_generation_corruption() {
        let mut page = CsrPage::new(3, 0, 4);
        page.push_row(&[(8, 0)]).unwrap();
        let bad_degree = NodeRecord {
            node_id: 5,
            coord_packed: 0,
            type_id: 1,
            file_id: 1,
            byte_start: 0,
            byte_end: 1,
            edge_block_pbn: 3,
            edge_row_idx: 0,
            out_degree: 0,
            generation: 4,
            flags: 0,
        };
        assert!(matches!(
            GraphSegment::from_parts(5, 3, 4, vec![bad_degree], vec![page.clone()]),
            Err(StorageError::DegreeMismatch { .. })
        ));
        let bad_generation = NodeRecord { out_degree: 1, generation: 3, ..bad_degree };
        assert!(matches!(
            GraphSegment::from_parts(5, 3, 4, vec![bad_generation], vec![page]),
            Err(StorageError::GenerationMismatch { .. })
        ));
    }
}
