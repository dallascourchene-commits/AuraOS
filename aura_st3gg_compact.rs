//! Aura ST3GG Stage 2 compactor.
//! stdin: newline-separated unique keys.
//! stdout: little-endian u32 key count followed by one u8 pilot per key.

use std::collections::HashSet;
use std::io::{self, Read, Write};

const TABLE_SCALE: usize = 2;
const MAX_PILOT: u16 = u8::MAX as u16;
const EMPTY_SLOT: u32 = u32::MAX;

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

fn compile_pilots(keys: &[&str]) -> io::Result<Vec<u8>> {
    if keys.is_empty() {
        return Ok(Vec::new());
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
    Ok(pilots)
}

fn main() -> io::Result<()> {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;
    let keys = parse_unique_keys(&input)?;
    let pilots = compile_pilots(&keys)?;

    let mut stdout = io::stdout();
    stdout.write_all(&(keys.len() as u32).to_le_bytes())?;
    stdout.write_all(&pilots)?;
    stdout.flush()?;
    Ok(())
}
