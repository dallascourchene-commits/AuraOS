//! Native / WASM-compiled accelerator for structural resonance and phase alignment.
//! stdin: JSON  stdout: JSON (matches arch_reasoner_accel.py contract)

use std::io::{self, Read};

fn extract_usize(json: &str, key: &str) -> usize {
    let pat = format!("\"{}\":", key);
    let Some(i) = json.find(&pat) else { return 0 };
    let rest = &json[i + pat.len()..];
    rest.trim_start()
        .trim_start_matches(':')
        .trim()
        .trim_start_matches('"')
        .split(|c: char| !c.is_ascii_digit())
        .next()
        .and_then(|s| s.parse().ok())
        .unwrap_or(0)
}

fn extract_f64_array(json: &str, key: &str) -> Vec<f64> {
    let pat = format!("\"{}\":", key);
    let Some(i) = json.find(&pat) else { return Vec::new() };
    let rest = &json[i + pat.len()..];
    let Some(start) = rest.find('[') else { return Vec::new() };
    let slice = &rest[start + 1..];
    let Some(end) = slice.find(']') else { return Vec::new() };
    slice[..end]
        .split(',')
        .filter_map(|s| s.trim().parse::<f64>().ok())
        .collect()
}

fn structural_resonance(nodes: usize, edges: usize) -> (f64, f64) {
    let n = nodes.max(1) as f64;
    let tension = edges as f64 / n;
    let ideal = 1.5_f64;
    let resonance = 1.0 / (1.0 + (ideal - tension).abs());
    (resonance, tension)
}

fn procrustes_score(a: &[f64], b: &[f64]) -> f64 {
    if a.is_empty() || a.len() != b.len() {
        return 0.0;
    }
    let mut dot = 0.0_f64;
    let mut na = 0.0_f64;
    let mut nb = 0.0_f64;
    for (x, y) in a.iter().zip(b.iter()) {
        dot += x * y;
        na += x * x;
        nb += y * y;
    }
    if na == 0.0 || nb == 0.0 {
        return if na == nb { 1.0 } else { 0.0 };
    }
    (dot / (na.sqrt() * nb.sqrt())).clamp(0.0, 1.0)
}

fn main() {
    let mut raw = String::new();
    io::stdin().read_to_string(&mut raw).unwrap();

    let op = if raw.contains("PROCRUSTES_ALIGNMENT") {
        "PROCRUSTES_ALIGNMENT"
    } else {
        "STRUCTURAL_RESONANCE"
    };

    if op == "PROCRUSTES_ALIGNMENT" {
        let a = extract_f64_array(&raw, "phase_a");
        let b = extract_f64_array(&raw, "phase_b");
        let score = procrustes_score(&a, &b);
        println!(
            "{{\"status\":\"success\",\"operation\":\"WASM_NATIVE_PROCRUSTES_ALIGNMENT\",\"metrics\":{{\"alignment_score\":{:.6}}}}}",
            score
        );
        return;
    }

    let nodes = extract_usize(&raw, "nodes");
    let edges = extract_usize(&raw, "edges");
    let (resonance, tension) = structural_resonance(nodes, edges);
    println!(
        "{{\"status\":\"success\",\"operation\":\"WASM_NATIVE_STRUCTURAL_RESONANCE\",\"metrics\":{{\"resonance\":{:.6},\"tension\":{:.6},\"ideal_tension\":1.5}}}}",
        resonance, tension
    );
}
