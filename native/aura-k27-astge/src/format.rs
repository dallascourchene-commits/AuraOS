use sha2::{Digest, Sha256};
use std::io::{Error, ErrorKind, Result as IoResult};

pub const BLOCK_SIZE: usize = 4096;
pub const NODE_RECORD_SIZE: usize = 64;
pub const MAX_ROWS_PER_BLOCK: usize = 256;
pub const ROW_OFFSET_COUNT: usize = MAX_ROWS_PER_BLOCK + 1;
pub const EDGE_HEADER_SIZE: usize = 32;
pub const ROW_OFFSETS_SIZE: usize = ROW_OFFSET_COUNT * 2;
pub const EDGE_ENTRY_SIZE: usize = 9;
pub const MAX_EDGES_PER_BLOCK: usize = 384;
pub const EDGE_DATA_OFFSET: usize = EDGE_HEADER_SIZE + ROW_OFFSETS_SIZE;
pub const EDGE_USED_BYTES: usize = EDGE_DATA_OFFSET + MAX_EDGES_PER_BLOCK * EDGE_ENTRY_SIZE;
pub const EDGE_MAGIC: &[u8; 8] = b"AUK27E01";
pub const K27_MODULUS: u128 = 7_625_597_484_987; // 3^27

const _: () = assert!(EDGE_USED_BYTES <= BLOCK_SIZE);
const _: () = assert!(BLOCK_SIZE - EDGE_USED_BYTES == 94);
const _: () = assert!(NODE_RECORD_SIZE == 64);
const _: () = assert!(MAX_ROWS_PER_BLOCK <= u16::MAX as usize);
const _: () = assert!(MAX_EDGES_PER_BLOCK <= u16::MAX as usize);

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct K27Coordinate {
    pub packed: u64,
}

impl K27Coordinate {
    pub fn matches_prefix(self, other: Self, len: usize) -> bool {
        if len > 27 {
            return false;
        }
        if len == 0 {
            return true;
        }
        let bits = len * 2;
        let mask = (1u64 << bits) - 1;
        (self.packed & mask) == (other.packed & mask)
    }
}

/// Deterministic K27 placement coordinate.
///
/// This is deliberately domain-separated hashing for physical partitioning.
/// It does not assert semantic locality or transfer source/currentness authority.
pub fn coordinate_for_sid(sid: &str, domain_axis: u8) -> K27Coordinate {
    let mut hasher = Sha256::new();
    hasher.update(b"AURA_K27_ASTGE_PLACEMENT_V0\0");
    hasher.update(sid.as_bytes());
    hasher.update([0]);
    hasher.update([domain_axis]);
    let hash = hasher.finalize();

    let mut first = [0u8; 16];
    first.copy_from_slice(&hash[..16]);
    let mut value = u128::from_be_bytes(first) % K27_MODULUS;
    let mut packed = 0u64;
    for index in 0..27 {
        let trit = (value % 3) as u64;
        packed |= trit << (index * 2);
        value /= 3;
    }
    K27Coordinate { packed }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct NodeRecord {
    pub node_id: u64,
    pub placement_coord_packed: u64,
    pub coordinate_generation: u64,
    pub type_id: u32,
    pub file_id: u32,
    pub byte_start: u32,
    pub byte_end: u32,
    pub edge_block_pbn: u64,
    pub edge_row_idx: u16,
    pub out_degree: u16,
    pub flags: u32,
}

impl NodeRecord {
    pub fn encode(self) -> [u8; NODE_RECORD_SIZE] {
        let mut out = [0u8; NODE_RECORD_SIZE];
        put_u64(&mut out, 0, self.node_id);
        put_u64(&mut out, 8, self.placement_coord_packed);
        put_u64(&mut out, 16, self.coordinate_generation);
        put_u32(&mut out, 24, self.type_id);
        put_u32(&mut out, 28, self.file_id);
        put_u32(&mut out, 32, self.byte_start);
        put_u32(&mut out, 36, self.byte_end);
        put_u64(&mut out, 40, self.edge_block_pbn);
        put_u16(&mut out, 48, self.edge_row_idx);
        put_u16(&mut out, 50, self.out_degree);
        put_u32(&mut out, 52, self.flags);
        // 56..64 reserved and canonical zero for forward-compatible V0 decoding.
        out
    }

    pub fn decode(bytes: &[u8]) -> IoResult<Self> {
        if bytes.len() != NODE_RECORD_SIZE {
            return Err(Error::new(ErrorKind::InvalidData, "node record size mismatch"));
        }
        if bytes[56..64].iter().any(|value| *value != 0) {
            return Err(Error::new(ErrorKind::InvalidData, "node reserved bytes are nonzero"));
        }
        let record = Self {
            node_id: get_u64(bytes, 0),
            placement_coord_packed: get_u64(bytes, 8),
            coordinate_generation: get_u64(bytes, 16),
            type_id: get_u32(bytes, 24),
            file_id: get_u32(bytes, 28),
            byte_start: get_u32(bytes, 32),
            byte_end: get_u32(bytes, 36),
            edge_block_pbn: get_u64(bytes, 40),
            edge_row_idx: get_u16(bytes, 48),
            out_degree: get_u16(bytes, 50),
            flags: get_u32(bytes, 52),
        };
        if record.byte_end < record.byte_start {
            return Err(Error::new(ErrorKind::InvalidData, "node byte span is inverted"));
        }
        Ok(record)
    }
}

pub(crate) fn put_u16(dst: &mut [u8], offset: usize, value: u16) {
    dst[offset..offset + 2].copy_from_slice(&value.to_le_bytes());
}

pub(crate) fn put_u32(dst: &mut [u8], offset: usize, value: u32) {
    dst[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
}

pub(crate) fn put_u64(dst: &mut [u8], offset: usize, value: u64) {
    dst[offset..offset + 8].copy_from_slice(&value.to_le_bytes());
}

pub(crate) fn get_u16(src: &[u8], offset: usize) -> u16 {
    u16::from_le_bytes(src[offset..offset + 2].try_into().expect("checked fixed-width slice"))
}

pub(crate) fn get_u32(src: &[u8], offset: usize) -> u32 {
    u32::from_le_bytes(src[offset..offset + 4].try_into().expect("checked fixed-width slice"))
}

pub(crate) fn get_u64(src: &[u8], offset: usize) -> u64 {
    u64::from_le_bytes(src[offset..offset + 8].try_into().expect("checked fixed-width slice"))
}
