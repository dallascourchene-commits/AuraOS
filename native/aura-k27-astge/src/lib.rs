//! Aura K27 out-of-core AST graph storage kernel.
//!
//! V0 intentionally proves only a deterministic, generation-bound storage and
//! query substrate. K27 coordinates are physical retrieval hints; they are not
//! semantic identity, source truth, currentness, review evidence, or authority.

mod format;
mod ingest;
mod reader;
mod storage;

pub use format::{
    coordinate_for_sid, K27Coordinate, NodeRecord, BLOCK_SIZE, MAX_EDGES_PER_BLOCK,
    MAX_ROWS_PER_BLOCK, NODE_RECORD_SIZE,
};
pub use ingest::{parse_rust_source, IngestedAst, AST_CHILD_EDGE_KIND};
pub use reader::{HydratedCone, SnapshotReader};
pub use storage::{publish_snapshot, EdgeInput, NodeInput, SnapshotManifest};
