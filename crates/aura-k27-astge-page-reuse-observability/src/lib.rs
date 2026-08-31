#![forbid(unsafe_code)]

//! Observe repeated physical-page demand without changing Aura K27 ASTGE read semantics.
//!
//! The wrapper delegates every request to its underlying `PageSource`. It performs no
//! caching or read elision. This matters because the production ReadSeek safe-default
//! path must not silently acquire an immutability assumption merely because a workload
//! exhibits reuse. The trace is optimization evidence only.

use aura_k27_astge::{PageSource, StorageError, BLOCK_SIZE};
use std::collections::HashSet;
use std::sync::{Arc, Mutex};

pub const TRACE_VERSION: &str = "AURA_K27_ASTGE_PAGE_REUSE_TRACE_V1";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PageReuseTraceV1 {
    pub version: &'static str,
    pub read_requests: usize,
    pub unique_pbns: usize,
    pub repeated_requests: usize,
    pub consecutive_same_pbn_requests: usize,
    pub working_set_bytes: usize,
    pub potential_full_cache_read_elisions: usize,
    pub underlying_reads_elided: usize,
    pub cache_admission_proven: bool,
    pub backing_immutability_proven_by_this_layer: bool,
    pub backend_promotion_authorized: bool,
    pub semantic_k27_authority: bool,
}

#[derive(Debug, Default)]
struct TraceState {
    read_requests: usize,
    seen: HashSet<u64>,
    repeated_requests: usize,
    consecutive_same_pbn_requests: usize,
    last_pbn: Option<u64>,
}

#[derive(Clone, Debug)]
pub struct PageReuseTraceHandle {
    state: Arc<Mutex<TraceState>>,
}

impl PageReuseTraceHandle {
    pub fn snapshot(&self) -> PageReuseTraceV1 {
        let state = self.state.lock().expect("page reuse trace mutex poisoned");
        PageReuseTraceV1 {
            version: TRACE_VERSION,
            read_requests: state.read_requests,
            unique_pbns: state.seen.len(),
            repeated_requests: state.repeated_requests,
            consecutive_same_pbn_requests: state.consecutive_same_pbn_requests,
            working_set_bytes: state.seen.len().saturating_mul(BLOCK_SIZE),
            potential_full_cache_read_elisions: state.repeated_requests,
            underlying_reads_elided: 0,
            cache_admission_proven: false,
            backing_immutability_proven_by_this_layer: false,
            backend_promotion_authorized: false,
            semantic_k27_authority: false,
        }
    }
}

pub struct TracingPageSource<S> {
    inner: S,
    trace: PageReuseTraceHandle,
}

impl<S> TracingPageSource<S> {
    pub fn new(inner: S) -> (Self, PageReuseTraceHandle) {
        let trace = PageReuseTraceHandle {
            state: Arc::new(Mutex::new(TraceState::default())),
        };
        (
            Self {
                inner,
                trace: trace.clone(),
            },
            trace,
        )
    }

    pub fn into_inner(self) -> S {
        self.inner
    }
}

impl<S: PageSource> PageSource for TracingPageSource<S> {
    fn read_page(&mut self, pbn: u64) -> Result<[u8; BLOCK_SIZE], StorageError> {
        {
            let mut state = self
                .trace
                .state
                .lock()
                .expect("page reuse trace mutex poisoned");
            state.read_requests = state.read_requests.saturating_add(1);
            if !state.seen.insert(pbn) {
                state.repeated_requests = state.repeated_requests.saturating_add(1);
            }
            if state.last_pbn == Some(pbn) {
                state.consecutive_same_pbn_requests =
                    state.consecutive_same_pbn_requests.saturating_add(1);
            }
            state.last_pbn = Some(pbn);
        }
        // Deliberately delegate every request. This trace cannot mask backing-file drift.
        self.inner.read_page(pbn)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge::{
        NodeIndexRecordV1, PageRow, PhysicalPageV1, SPlaneGraphReader,
    };
    use std::collections::HashMap;
    use std::sync::atomic::{AtomicUsize, Ordering};

    #[derive(Clone)]
    struct MemoryPages {
        pages: HashMap<u64, [u8; BLOCK_SIZE]>,
        reads: Arc<AtomicUsize>,
    }

    impl PageSource for MemoryPages {
        fn read_page(&mut self, pbn: u64) -> Result<[u8; BLOCK_SIZE], StorageError> {
            self.reads.fetch_add(1, Ordering::Relaxed);
            self.pages
                .get(&pbn)
                .copied()
                .ok_or_else(|| StorageError::Io("missing fixture page".to_string()))
        }
    }

    fn fixture_source() -> (MemoryPages, Vec<NodeIndexRecordV1>) {
        let page = PhysicalPageV1 {
            pbn: 0,
            placement_generation: 7,
            placement_scheme_digest: [0x31; 32],
            rows: vec![
                PageRow {
                    first_edge: 0,
                    degree: 2,
                },
                PageRow {
                    first_edge: 2,
                    degree: 1,
                },
                PageRow {
                    first_edge: 3,
                    degree: 1,
                },
                PageRow {
                    first_edge: 4,
                    degree: 0,
                },
                PageRow {
                    first_edge: 4,
                    degree: 0,
                },
            ],
            targets: vec![1, 2, 3, 4],
            edge_kinds: vec![0, 0, 0, 0],
        }
        .encode()
        .unwrap();
        let source = MemoryPages {
            pages: HashMap::from([(0, page)]),
            reads: Arc::new(AtomicUsize::new(0)),
        };
        let records = (0u64..5)
            .map(|node_id| {
                let (row, out_degree) = match node_id {
                    0 => (0, 2),
                    1 => (1, 1),
                    2 => (2, 1),
                    3 => (3, 0),
                    _ => (4, 0),
                };
                NodeIndexRecordV1 {
                    node_id,
                    semantic_handle_digest: [node_id as u8; 32],
                    pbn: 0,
                    row,
                    out_degree,
                    file_id: 1,
                    byte_start: node_id as u32,
                    byte_end: node_id as u32 + 1,
                }
            })
            .collect();
        (source, records)
    }

    #[test]
    fn tracing_never_elides_underlying_reads() {
        let (source, _) = fixture_source();
        let counter = source.reads.clone();
        let (mut traced, handle) = TracingPageSource::new(source);
        for pbn in [0, 0, 0, 0] {
            traced.read_page(pbn).unwrap();
        }
        let trace = handle.snapshot();
        assert_eq!(counter.load(Ordering::Relaxed), 4);
        assert_eq!(trace.read_requests, 4);
        assert_eq!(trace.unique_pbns, 1);
        assert_eq!(trace.repeated_requests, 3);
        assert_eq!(trace.consecutive_same_pbn_requests, 3);
        assert_eq!(trace.underlying_reads_elided, 0);
        assert!(!trace.cache_admission_proven);
        assert!(!trace.backing_immutability_proven_by_this_layer);
        assert!(!trace.backend_promotion_authorized);
    }

    #[test]
    fn trace_preserves_exact_graph_consequence() {
        let (baseline_source, records) = fixture_source();
        let (traced_source, trace_handle) = TracingPageSource::new(baseline_source.clone());

        let mut baseline = SPlaneGraphReader::new(records.clone(), baseline_source).unwrap();
        let mut traced = SPlaneGraphReader::new(records, traced_source).unwrap();

        let expected = baseline.query_cone(0, 2, 16, None).unwrap();
        let observed = traced.query_cone(0, 2, 16, None).unwrap();
        assert_eq!(observed, expected);

        let trace = trace_handle.snapshot();
        assert_eq!(trace.read_requests, 3);
        assert_eq!(trace.unique_pbns, 1);
        assert_eq!(trace.repeated_requests, 2);
        assert_eq!(trace.working_set_bytes, BLOCK_SIZE);
        assert_eq!(trace.potential_full_cache_read_elisions, 2);
        assert_eq!(trace.underlying_reads_elided, 0);
    }

    #[test]
    fn distinct_pages_expand_working_set_without_granting_cache_authority() {
        let reads = Arc::new(AtomicUsize::new(0));
        let source = MemoryPages {
            pages: HashMap::from([(0, [0u8; BLOCK_SIZE]), (4, [4u8; BLOCK_SIZE])]),
            reads: reads.clone(),
        };
        let (mut traced, handle) = TracingPageSource::new(source);
        for pbn in [0, 4, 0, 4, 4] {
            traced.read_page(pbn).unwrap();
        }
        let trace = handle.snapshot();
        assert_eq!(reads.load(Ordering::Relaxed), 5);
        assert_eq!(trace.unique_pbns, 2);
        assert_eq!(trace.repeated_requests, 3);
        assert_eq!(trace.working_set_bytes, 2 * BLOCK_SIZE);
        assert_eq!(trace.underlying_reads_elided, 0);
        assert!(!trace.semantic_k27_authority);
    }
}
