//! Aura ST3GG Stage 2 compactor.
//! stdin: newline-separated unique keys.
//! stdout: versioned little-endian header followed by one u8 pilot per key.

use std::collections::HashSet;
use std::io::{self, Read, Write};

const TABLE_SCALE: usize = 2;
const MAGIC: &[u8; 8] = b"AST3CMP1";
const VERSION: u32 = 1;
const HASH_PROFILE_DJB2_SEED8: u32 = 1;
const MAX_PILOT: u16 = u8::MAX as u16;
const EMPTY_SLOT: u32 = u32::MAX;

struct CompiledPilots {
    table_size: usize,
    pilots: Vec<u8>,
}

#[derive(Clone, Copy)]
struct CompactionHeader {
    key_count: u32,
    table_size: u32,
    table_scale: u32,
    hash_profile: u32,
}

fn djb2_hash(bytes: &[u8], seed: u8) -> usize {
    let mut hash = 5381u64.wrapping_add(seed as u64);
    for &byte in bytes {
        hash = hash.wrapping_mul(33).wrapping_add(byte as u64);
    }
    hash as usize
}

fn parse_unique_keys(input: &str) -> io::Result<Vec<&str>> {
    let keys: Vec<&str> = input.lines().filter(|line| line.is_empty() == false).collect();
    let mut seen = HashSet::with_capacity(keys.len());
    for key in &keys {
        if seen.insert(*key) == false {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "duplicate_st3gg_compaction_key",
            ));
        }
    }
    Ok(keys)
}

fn compile_pilots(keys: &[&str]) -> io::Result<CompiledPilots> {
    if keys.is_empty() {
        return Ok(CompiledPilots {
            table_size: 0,
            pilots: Vec::new(),
        });
    }
    if keys.len() > u32::MAX as usize {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "too_many_st3gg_compaction_keys",
        ));
    }
    let table_size = keys
        .len()
        .checked_mul(TABLE_SCALE)
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "st3gg_table_size_overflow"))?;
    let mut index_slots = vec![EMPTY_SLOT; table_size];
    let mut pilots = vec![0u8; keys.len()];

    for (idx, key) in keys.iter().enumerate() {
        let mut placed = false;
        for pilot in 0..=MAX_PILOT {
            let pilot_byte = pilot as u8;
            let slot = djb2_hash(key.as_bytes(), pilot_byte) % table_size;
            if index_slots[slot] == EMPTY_SLOT {
                index_slots[slot] = idx as u32;
                pilots[idx] = pilot_byte;
                placed = true;
                break;
            }
        }
        if placed == false {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "st3gg_compaction_seed_exhausted",
            ));
        }
    }
    Ok(CompiledPilots { table_size, pilots })
}

fn write_header<W: Write>(mut writer: W, header: CompactionHeader) -> io::Result<()> {
    writer.write_all(MAGIC)?;
    writer.write_all(&VERSION.to_le_bytes())?;
    writer.write_all(&header.key_count.to_le_bytes())?;
    writer.write_all(&header.table_size.to_le_bytes())?;
    writer.write_all(&header.table_scale.to_le_bytes())?;
    writer.write_all(&header.hash_profile.to_le_bytes())?;
    Ok(())
}

fn read_u32_le(raw: &[u8], offset: usize) -> io::Result<u32> {
    let end = offset.saturating_add(4);
    if end > raw.len() {
        return Err(io::Error::new(
            io::ErrorKind::UnexpectedEof,
            "st3gg_compaction_header_truncated",
        ));
    }
    Ok(u32::from_le_bytes([
        raw[offset],
        raw[offset + 1],
        raw[offset + 2],
        raw[offset + 3],
    ]))
}

#[allow(dead_code)]
fn decode_compaction_blob(raw: &[u8]) -> io::Result<(CompactionHeader, &[u8])> {
    const HEADER_LEN: usize = 28;
    if raw.len() < HEADER_LEN {
        return Err(io::Error::new(
            io::ErrorKind::UnexpectedEof,
            "st3gg_compaction_blob_truncated",
        ));
    }
    if &raw[..8] != MAGIC {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "st3gg_compaction_bad_magic",
        ));
    }
    let version = read_u32_le(raw, 8)?;
    if version != VERSION {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "st3gg_compaction_unsupported_version",
        ));
    }
    let header = CompactionHeader {
        key_count: read_u32_le(raw, 12)?,
        table_size: read_u32_le(raw, 16)?,
        table_scale: read_u32_le(raw, 20)?,
        hash_profile: read_u32_le(raw, 24)?,
    };
    if header.table_scale != TABLE_SCALE as u32 {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "st3gg_compaction_table_scale_mismatch",
        ));
    }
    if header.hash_profile != HASH_PROFILE_DJB2_SEED8 {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "st3gg_compaction_hash_profile_mismatch",
        ));
    }
    let expected_table_size = (header.key_count as usize)
        .checked_mul(header.table_scale as usize)
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "st3gg_compaction_table_size_overflow"))?;
    if header.table_size as usize != expected_table_size {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "st3gg_compaction_table_size_mismatch",
        ));
    }
    let pilots = &raw[HEADER_LEN..];
    if pilots.len() != header.key_count as usize {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "st3gg_compaction_pilot_count_mismatch",
        ));
    }
    Ok((header, pilots))
}

fn main() -> io::Result<()> {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;
    let keys = parse_unique_keys(&input)?;
    let compiled = compile_pilots(&keys)?;
    if compiled.table_size > u32::MAX as usize {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "st3gg_table_size_too_large",
        ));
    }
    let header = CompactionHeader {
        key_count: keys.len() as u32,
        table_size: compiled.table_size as u32,
        table_scale: TABLE_SCALE as u32,
        hash_profile: HASH_PROFILE_DJB2_SEED8,
    };

    let mut stdout = io::stdout();
    write_header(&mut stdout, header)?;
    stdout.write_all(&compiled.pilots)?;
    stdout.flush()?;
    Ok(())
}
