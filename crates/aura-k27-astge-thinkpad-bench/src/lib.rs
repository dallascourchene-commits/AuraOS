use aura_k27_astge::{
    FilePageSource, HydratedConeV1, NodeIndexRecordV1, SPlaneGraphReader, StorageError,
    NODE_INDEX_RECORD_SIZE,
};
use aura_k27_astge_mmap::{ImmutableMmapReader, MmapStorageError};
use sha2::{Digest, Sha256};
use std::error::Error;
use std::fmt::{Display, Formatter};
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;

pub const RECEIPT_SCHEMA: &str = "AuraK27AstgeThinkPadWarmBenchmarkV1";
pub const CACHE_STATE: &str = "WARMISH_VERIFICATION_TOUCHED_UNCONTROLLED_OS_PAGE_CACHE";
pub const CLAIM_CEILING: &str =
    "D0_MATCHED_WARM_HOST_OBSERVATION_ONLY_NO_COLDNESS_NO_PHYSICAL_NVME_NO_SUPERIORITY_NO_AUTHORITY";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Backend {
    ReadSeek,
    Mmap,
}

impl Backend {
    pub fn parse(value: &str) -> Result<Self, BenchmarkError> {
        match value {
            "readseek" => Ok(Self::ReadSeek),
            "mmap" => Ok(Self::Mmap),
            _ => Err(BenchmarkError::InvalidConfig("backend")),
        }
    }

    pub fn label(self) -> &'static str {
        match self {
            Self::ReadSeek => "READ_SEEK_SAME_SNAPSHOT",
            Self::Mmap => "IMMUTABLE_GENERATION_MMAP_SAME_SNAPSHOT",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BenchmarkConfig {
    pub roots: Vec<u64>,
    pub max_depth: usize,
    pub max_nodes: usize,
    pub iterations: usize,
}

impl BenchmarkConfig {
    pub fn validate(&self) -> Result<(), BenchmarkError> {
        if self.roots.is_empty() {
            return Err(BenchmarkError::InvalidConfig("roots"));
        }
        if self.max_nodes == 0 {
            return Err(BenchmarkError::InvalidConfig("max_nodes"));
        }
        if self.iterations == 0 {
            return Err(BenchmarkError::InvalidConfig("iterations"));
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct LinuxCounters {
    pub minflt: Option<u64>,
    pub majflt: Option<u64>,
    pub rchar: Option<u64>,
    pub read_bytes: Option<u64>,
    pub syscr: Option<u64>,
}

impl LinuxCounters {
    fn delta(&self, before: &Self) -> Self {
        Self {
            minflt: delta(self.minflt, before.minflt),
            majflt: delta(self.majflt, before.majflt),
            rchar: delta(self.rchar, before.rchar),
            read_bytes: delta(self.read_bytes, before.read_bytes),
            syscr: delta(self.syscr, before.syscr),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HostIdentity {
    pub os: String,
    pub arch: String,
    pub kernel_release: String,
    pub cpu_model: String,
    pub product_name: String,
    pub wsl_observed: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BenchmarkReceipt {
    pub schema: &'static str,
    pub backend: &'static str,
    pub snapshot_generation: u64,
    pub placement_generation: u64,
    pub index_sha256: String,
    pub pages_sha256: String,
    pub query_corpus_sha256: String,
    pub semantic_result_sha256: String,
    pub roots: usize,
    pub iterations: usize,
    pub max_depth: usize,
    pub max_nodes: usize,
    pub elapsed_ns: u128,
    pub hydrated_nodes_total: u64,
    pub edges_traversed_total: u64,
    pub unique_pages_sum: u64,
    pub counters: LinuxCounters,
    pub host: HostIdentity,
    pub cache_state: &'static str,
    pub same_snapshot_verified: bool,
    pub physical_locality_proven_by_this_run: bool,
    pub cache_coldness_proven: bool,
    pub physical_nvme_read_proven: bool,
    pub performance_superiority_proven: bool,
    pub producer_authenticated: bool,
    pub effect_authority: bool,
    pub claim_ceiling: &'static str,
}

impl BenchmarkReceipt {
    pub fn to_kv(&self) -> String {
        let mut lines = Vec::new();
        lines.push(format!("schema={}", self.schema));
        lines.push(format!("backend={}", self.backend));
        lines.push(format!("snapshot_generation={}", self.snapshot_generation));
        lines.push(format!(
            "placement_generation={}",
            self.placement_generation
        ));
        lines.push(format!("index_sha256={}", self.index_sha256));
        lines.push(format!("pages_sha256={}", self.pages_sha256));
        lines.push(format!("query_corpus_sha256={}", self.query_corpus_sha256));
        lines.push(format!(
            "semantic_result_sha256={}",
            self.semantic_result_sha256
        ));
        lines.push(format!("roots={}", self.roots));
        lines.push(format!("iterations={}", self.iterations));
        lines.push(format!("max_depth={}", self.max_depth));
        lines.push(format!("max_nodes={}", self.max_nodes));
        lines.push(format!("elapsed_ns={}", self.elapsed_ns));
        lines.push(format!(
            "hydrated_nodes_total={}",
            self.hydrated_nodes_total
        ));
        lines.push(format!(
            "edges_traversed_total={}",
            self.edges_traversed_total
        ));
        lines.push(format!("unique_pages_sum={}", self.unique_pages_sum));
        lines.push(format!("minflt_delta={}", opt(self.counters.minflt)));
        lines.push(format!("majflt_delta={}", opt(self.counters.majflt)));
        lines.push(format!("rchar_delta={}", opt(self.counters.rchar)));
        lines.push(format!(
            "kernel_read_bytes_delta={}",
            opt(self.counters.read_bytes)
        ));
        lines.push(format!("read_syscalls_delta={}", opt(self.counters.syscr)));
        lines.push(format!("host_os={}", clean(&self.host.os)));
        lines.push(format!("host_arch={}", clean(&self.host.arch)));
        lines.push(format!(
            "kernel_release={}",
            clean(&self.host.kernel_release)
        ));
        lines.push(format!("cpu_model={}", clean(&self.host.cpu_model)));
        lines.push(format!("product_name={}", clean(&self.host.product_name)));
        lines.push(format!("wsl_observed={}", self.host.wsl_observed));
        lines.push(format!("cache_state={}", self.cache_state));
        lines.push(format!(
            "same_snapshot_verified={}",
            self.same_snapshot_verified
        ));
        lines.push(format!(
            "physical_locality_proven_by_this_run={}",
            self.physical_locality_proven_by_this_run
        ));
        lines.push(format!(
            "cache_coldness_proven={}",
            self.cache_coldness_proven
        ));
        lines.push(format!(
            "physical_nvme_read_proven={}",
            self.physical_nvme_read_proven
        ));
        lines.push(format!(
            "performance_superiority_proven={}",
            self.performance_superiority_proven
        ));
        lines.push(format!(
            "producer_authenticated={}",
            self.producer_authenticated
        ));
        lines.push(format!("effect_authority={}", self.effect_authority));
        lines.push(format!("claim_ceiling={}", self.claim_ceiling));
        lines.join("\n") + "\n"
    }
}

#[derive(Debug)]
pub enum BenchmarkError {
    Io(String),
    Storage(StorageError),
    Mmap(MmapStorageError),
    InvalidConfig(&'static str),
    SnapshotDigestMismatch(&'static str),
}

impl Display for BenchmarkError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}
impl Error for BenchmarkError {}
impl From<std::io::Error> for BenchmarkError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value.to_string())
    }
}
impl From<StorageError> for BenchmarkError {
    fn from(value: StorageError) -> Self {
        Self::Storage(value)
    }
}
impl From<MmapStorageError> for BenchmarkError {
    fn from(value: MmapStorageError) -> Self {
        Self::Mmap(value)
    }
}

pub fn benchmark_same_snapshot(
    backend: Backend,
    snapshot_root: impl AsRef<Path>,
    node_index_path: impl AsRef<Path>,
    pages_path: impl AsRef<Path>,
    config: &BenchmarkConfig,
) -> Result<BenchmarkReceipt, BenchmarkError> {
    config.validate()?;
    let snapshot_root = snapshot_root.as_ref();
    let node_index_path = node_index_path.as_ref();
    let pages_path = pages_path.as_ref();

    // PR471 verifies CURRENT -> manifest -> exact file lengths and SHA-256 before mapping.
    // Opening once before either backend deliberately makes this a matched warm-ish benchmark:
    // verification touches the files and OS page-cache state remains uncontrolled.
    let verified = ImmutableMmapReader::open_current(snapshot_root)?;
    let manifest = verified.manifest().clone();

    let index_sha256 = sha256_file(node_index_path)?;
    let pages_sha256 = sha256_file(pages_path)?;
    if index_sha256 != manifest.index_sha256 {
        return Err(BenchmarkError::SnapshotDigestMismatch("node-index"));
    }
    if pages_sha256 != manifest.pages_sha256 {
        return Err(BenchmarkError::SnapshotDigestMismatch("pages"));
    }

    let query_corpus_sha256 = query_digest(config);
    let host = host_identity();
    let before = linux_counters();
    let start = Instant::now();

    let (semantic_result_sha256, hydrated_nodes_total, edges_traversed_total, unique_pages_sum) =
        match backend {
            Backend::ReadSeek => {
                drop(verified);
                let records = read_index(node_index_path)?;
                let pages = FilePageSource::open(pages_path, 0)?;
                let mut reader = SPlaneGraphReader::new(records, pages)?;
                run_queries(config, |root, depth, nodes| {
                    reader
                        .query_cone(root, depth, nodes, None)
                        .map_err(BenchmarkError::Storage)
                })?
            }
            Backend::Mmap => {
                let reader = verified;
                run_queries(config, |root, depth, nodes| {
                    reader
                        .query_cone(root, depth, nodes, None)
                        .map_err(BenchmarkError::Mmap)
                })?
            }
        };

    let elapsed_ns = start.elapsed().as_nanos();
    let after = linux_counters();
    Ok(BenchmarkReceipt {
        schema: RECEIPT_SCHEMA,
        backend: backend.label(),
        snapshot_generation: manifest.snapshot_generation,
        placement_generation: manifest.binding.placement_generation,
        index_sha256,
        pages_sha256,
        query_corpus_sha256,
        semantic_result_sha256,
        roots: config.roots.len(),
        iterations: config.iterations,
        max_depth: config.max_depth,
        max_nodes: config.max_nodes,
        elapsed_ns,
        hydrated_nodes_total,
        edges_traversed_total,
        unique_pages_sum,
        counters: after.delta(&before),
        host,
        cache_state: CACHE_STATE,
        same_snapshot_verified: true,
        physical_locality_proven_by_this_run: false,
        cache_coldness_proven: false,
        physical_nvme_read_proven: false,
        performance_superiority_proven: false,
        producer_authenticated: false,
        effect_authority: false,
        claim_ceiling: CLAIM_CEILING,
    })
}

fn run_queries<F>(
    config: &BenchmarkConfig,
    mut query: F,
) -> Result<(String, u64, u64, u64), BenchmarkError>
where
    F: FnMut(u64, usize, usize) -> Result<HydratedConeV1, BenchmarkError>,
{
    let mut digest = Sha256::new();
    let mut hydrated_nodes_total = 0u64;
    let mut edges_traversed_total = 0u64;
    let mut unique_pages_sum = 0u64;
    for iteration in 0..config.iterations {
        digest.update((iteration as u64).to_le_bytes());
        for root in &config.roots {
            let cone = query(*root, config.max_depth, config.max_nodes)?;
            digest.update(root.to_le_bytes());
            digest.update((cone.node_ids.len() as u64).to_le_bytes());
            for node_id in &cone.node_ids {
                digest.update(node_id.to_le_bytes());
            }
            digest.update((cone.unique_pages as u64).to_le_bytes());
            digest.update((cone.edges_traversed as u64).to_le_bytes());
            hydrated_nodes_total += cone.node_ids.len() as u64;
            edges_traversed_total += cone.edges_traversed as u64;
            unique_pages_sum += cone.unique_pages as u64;
        }
    }
    Ok((
        format!("{:x}", digest.finalize()),
        hydrated_nodes_total,
        edges_traversed_total,
        unique_pages_sum,
    ))
}

fn read_index(path: &Path) -> Result<Vec<NodeIndexRecordV1>, BenchmarkError> {
    let bytes = fs::read(path)?;
    let (chunks, remainder) = bytes.as_chunks::<NODE_INDEX_RECORD_SIZE>();
    if !remainder.is_empty() {
        return Err(BenchmarkError::InvalidConfig("node-index-length"));
    }
    chunks
        .iter()
        .map(|raw| NodeIndexRecordV1::decode(raw))
        .collect::<Result<Vec<_>, _>>()
        .map_err(BenchmarkError::Storage)
}

fn query_digest(config: &BenchmarkConfig) -> String {
    let mut digest = Sha256::new();
    digest.update((config.max_depth as u64).to_le_bytes());
    digest.update((config.max_nodes as u64).to_le_bytes());
    digest.update((config.iterations as u64).to_le_bytes());
    for root in &config.roots {
        digest.update(root.to_le_bytes());
    }
    format!("{:x}", digest.finalize())
}

fn sha256_file(path: &Path) -> Result<String, BenchmarkError> {
    let bytes = fs::read(path)?;
    let mut digest = Sha256::new();
    digest.update(bytes);
    Ok(format!("{:x}", digest.finalize()))
}

pub fn host_identity() -> HostIdentity {
    let kernel_release = read_trim("/proc/sys/kernel/osrelease");
    let version = read_trim("/proc/version");
    HostIdentity {
        os: std::env::consts::OS.to_string(),
        arch: std::env::consts::ARCH.to_string(),
        kernel_release: kernel_release.clone(),
        cpu_model: cpu_model(),
        product_name: read_trim("/sys/class/dmi/id/product_name"),
        wsl_observed: kernel_release.to_ascii_lowercase().contains("microsoft")
            || version.to_ascii_lowercase().contains("microsoft"),
    }
}

pub fn linux_counters() -> LinuxCounters {
    let (minflt, majflt) = stat_faults().unwrap_or((None, None));
    let io = fs::read_to_string("/proc/self/io").unwrap_or_default();
    LinuxCounters {
        minflt,
        majflt,
        rchar: io_field(&io, "rchar"),
        read_bytes: io_field(&io, "read_bytes"),
        syscr: io_field(&io, "syscr"),
    }
}

fn stat_faults() -> Option<(Option<u64>, Option<u64>)> {
    let stat = fs::read_to_string("/proc/self/stat").ok()?;
    let close = stat.rfind(')')?;
    let fields: Vec<&str> = stat[close + 1..].split_whitespace().collect();
    let minflt = fields.get(7).and_then(|v| v.parse().ok());
    let majflt = fields.get(9).and_then(|v| v.parse().ok());
    Some((minflt, majflt))
}

fn io_field(text: &str, wanted: &str) -> Option<u64> {
    text.lines().find_map(|line| {
        let (key, value) = line.split_once(':')?;
        (key.trim() == wanted)
            .then(|| value.trim().parse().ok())
            .flatten()
    })
}

fn cpu_model() -> String {
    fs::read_to_string("/proc/cpuinfo")
        .ok()
        .and_then(|text| {
            text.lines().find_map(|line| {
                let (key, value) = line.split_once(':')?;
                (key.trim() == "model name").then(|| value.trim().to_string())
            })
        })
        .unwrap_or_else(|| "UNAVAILABLE".to_string())
}

fn read_trim(path: impl Into<PathBuf>) -> String {
    fs::read_to_string(path.into())
        .map(|v| v.trim().to_string())
        .unwrap_or_else(|_| "UNAVAILABLE".to_string())
}

fn delta(after: Option<u64>, before: Option<u64>) -> Option<u64> {
    after.zip(before).and_then(|(a, b)| a.checked_sub(b))
}

fn opt(value: Option<u64>) -> String {
    value
        .map(|v| v.to_string())
        .unwrap_or_else(|| "UNAVAILABLE".to_string())
}

fn clean(value: &str) -> String {
    value.replace(['\n', '\r', '='], " ")
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge::{PageRow, PhysicalPageV1, StorageGenerationBindingV1, BLOCK_SIZE};
    use aura_k27_astge_mmap::publish_generation;
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(1);

    fn temp_root(label: &str) -> PathBuf {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "aura-k27-thinkpad-bench-{label}-{}-{n}",
            std::process::id()
        ));
        fs::create_dir_all(&path).unwrap();
        path
    }

    fn fixture() -> (PathBuf, PathBuf, PathBuf, PathBuf) {
        let root = temp_root("fixture");
        let raw = root.join("raw");
        let snapshot = root.join("snapshot");
        fs::create_dir_all(&raw).unwrap();

        let node_count = 512u64;
        let page_count = 2u64;
        let placement_generation = 19u64;
        let scheme = [0xA7; 32];
        let binding = StorageGenerationBindingV1 {
            node_count,
            page_count,
            placement_generation,
            placement_scheme_digest: scheme,
        };

        let mut records = Vec::new();
        for node_id in 0..node_count {
            let pbn = node_id / 256;
            let row = (node_id % 256) as u16;
            let out_degree = if node_id + 1 < node_count { 1 } else { 0 };
            records.push(NodeIndexRecordV1 {
                node_id,
                semantic_handle_digest: [(node_id % 251) as u8; 32],
                pbn,
                row,
                out_degree,
                file_id: 1,
                byte_start: node_id as u32,
                byte_end: node_id as u32 + 1,
            });
        }

        let mut index_bytes = Vec::with_capacity(node_count as usize * NODE_INDEX_RECORD_SIZE);
        for record in &records {
            index_bytes.extend_from_slice(&record.encode());
        }

        let mut page_bytes = Vec::with_capacity(page_count as usize * BLOCK_SIZE);
        for pbn in 0..page_count {
            let start_node = pbn * 256;
            let rows_in_page = usize::min(256, (node_count - start_node) as usize);
            let mut rows = Vec::with_capacity(rows_in_page);
            let mut targets = Vec::new();
            for row in 0..rows_in_page {
                let node_id = start_node + row as u64;
                let first_edge = targets.len() as u16;
                let degree = if node_id + 1 < node_count { 1 } else { 0 };
                rows.push(PageRow { first_edge, degree });
                if degree == 1 {
                    targets.push(node_id + 1);
                }
            }
            let page = PhysicalPageV1 {
                pbn,
                placement_generation,
                placement_scheme_digest: scheme,
                rows,
                edge_kinds: vec![0; targets.len()],
                targets,
            };
            page_bytes.extend_from_slice(&page.encode().unwrap());
        }

        let index_path = raw.join("node-index.bin");
        let pages_path = raw.join("pages.bin");
        fs::write(&index_path, &index_bytes).unwrap();
        fs::write(&pages_path, &page_bytes).unwrap();
        publish_generation(&snapshot, 7, binding, &index_bytes, &page_bytes).unwrap();
        (root, snapshot, index_path, pages_path)
    }

    #[test]
    fn matched_backends_emit_identical_semantic_result_on_same_snapshot() {
        let (_root, snapshot, index, pages) = fixture();
        let config = BenchmarkConfig {
            roots: vec![0, 128, 256, 384],
            max_depth: 63,
            max_nodes: 64,
            iterations: 3,
        };
        let readseek =
            benchmark_same_snapshot(Backend::ReadSeek, &snapshot, &index, &pages, &config).unwrap();
        let mmap =
            benchmark_same_snapshot(Backend::Mmap, &snapshot, &index, &pages, &config).unwrap();
        assert_eq!(readseek.index_sha256, mmap.index_sha256);
        assert_eq!(readseek.pages_sha256, mmap.pages_sha256);
        assert_eq!(readseek.query_corpus_sha256, mmap.query_corpus_sha256);
        assert_eq!(readseek.semantic_result_sha256, mmap.semantic_result_sha256);
        assert_eq!(readseek.hydrated_nodes_total, mmap.hydrated_nodes_total);
        assert_eq!(readseek.edges_traversed_total, mmap.edges_traversed_total);
        assert_eq!(readseek.unique_pages_sum, mmap.unique_pages_sum);
    }

    #[test]
    fn receipt_cannot_promote_warm_host_counters_into_nvme_or_superiority_proof() {
        let (_root, snapshot, index, pages) = fixture();
        let config = BenchmarkConfig {
            roots: vec![0],
            max_depth: 8,
            max_nodes: 16,
            iterations: 1,
        };
        let receipt =
            benchmark_same_snapshot(Backend::ReadSeek, &snapshot, &index, &pages, &config).unwrap();
        assert!(receipt.same_snapshot_verified);
        assert_eq!(receipt.cache_state, CACHE_STATE);
        assert!(!receipt.physical_locality_proven_by_this_run);
        assert!(!receipt.cache_coldness_proven);
        assert!(!receipt.physical_nvme_read_proven);
        assert!(!receipt.performance_superiority_proven);
        assert!(!receipt.producer_authenticated);
        assert!(!receipt.effect_authority);
        assert_eq!(receipt.claim_ceiling, CLAIM_CEILING);
    }

    #[test]
    fn raw_bytes_must_match_verified_snapshot_before_timing() {
        let (_root, snapshot, index, pages) = fixture();
        let mut bytes = fs::read(&pages).unwrap();
        bytes[0] ^= 0xFF;
        fs::write(&pages, bytes).unwrap();
        let config = BenchmarkConfig {
            roots: vec![0],
            max_depth: 1,
            max_nodes: 4,
            iterations: 1,
        };
        assert!(matches!(
            benchmark_same_snapshot(Backend::ReadSeek, &snapshot, &index, &pages, &config),
            Err(BenchmarkError::SnapshotDigestMismatch("pages"))
        ));
    }
}
