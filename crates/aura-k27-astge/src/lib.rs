#![forbid(unsafe_code)]

//! Experimental, nonpromoting storage kernel for the Aura K27 out-of-core AST graph engine.
//!
//! This crate intentionally starts below Tree-Sitter, mmap, agent hydration, and FFI. The
//! persistence ABI is byte-defined so compiler padding/alignment cannot silently change the
//! on-disk format. Stronger performance, durability, or AuraOS-integration claims require later
//! matched benchmarks and consequence-specific receipts.

pub mod coord;
pub mod generation;
pub mod storage;

pub use coord::{CoordinateError, K27Coordinate, K27_TRITS};
pub use generation::{GenerationError, GenerationManifest, GenerationStore};
pub use storage::{
    CsrPage, GraphSegment, GraphSegmentBuilder, NodeRecord, StorageError, MAX_CSR_EDGES,
    MAX_CSR_ROWS, NODE_RECORD_SIZE, PAGE_SIZE,
};
