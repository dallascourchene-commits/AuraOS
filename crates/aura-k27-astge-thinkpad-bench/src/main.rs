use aura_k27_astge_thinkpad_bench::{benchmark_same_snapshot, Backend, BenchmarkConfig};
use std::env;
use std::path::PathBuf;

fn usage() -> ! {
    eprintln!(
        "usage: aura-k27-astge-thinkpad-bench <readseek|mmap> <snapshot_root> <node_index> <pages> <roots_csv> <max_depth> <max_nodes> <iterations>"
    );
    std::process::exit(2);
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 9 {
        usage();
    }
    let backend = Backend::parse(&args[1])?;
    let snapshot_root = PathBuf::from(&args[2]);
    let node_index = PathBuf::from(&args[3]);
    let pages = PathBuf::from(&args[4]);
    let roots = args[5]
        .split(',')
        .map(str::parse::<u64>)
        .collect::<Result<Vec<_>, _>>()?;
    let config = BenchmarkConfig {
        roots,
        max_depth: args[6].parse()?,
        max_nodes: args[7].parse()?,
        iterations: args[8].parse()?,
    };
    let receipt = benchmark_same_snapshot(backend, snapshot_root, node_index, pages, &config)?;
    print!("{}", receipt.to_kv());
    Ok(())
}
