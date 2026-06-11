use std::io::{self, Read, Write};
use std::collections::HashMap;

fn main() {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).unwrap();

    // The Phase 2 Engine: N-Gram Transition Mapping
    let tokens: Vec<&str> = input.split_whitespace().collect();
    let mut transitions: HashMap<String, HashMap<String, u32>> = HashMap::new();
    
    // Map the relational syntax (What root follows what root?)
    for window in tokens.windows(2) {
        let root = window[0].to_string();
        let next_root = window[1].to_string();
        
        let entry = transitions.entry(root).or_insert(HashMap::new());
        *entry.entry(next_root).or_insert(0) += 1;
    }

    // Calculate Syntactic Rigidity (Is it a language or random noise?)
    let mut deterministic_links = 0;
    let mut total_links = 0;

    for (_, next_roots) in &transitions {
        for (_, &count) in next_roots {
            total_links += 1;
            if count > 3 { // Threshold for a strict grammatical rule
                deterministic_links += 1;
            }
        }
    }

    let syntax_probability = if total_links > 0 {
        (deterministic_links as f64 / total_links as f64) * 100.0
    } else {
        0.0
    };

    // Output the structural tensor data
    let output = format!(
        "{{\"phase\": \"2\", \"status\": \"success\", \"metrics\": {{\"total_transitions\": {}, \"deterministic_rules\": {}, \"syntax_rigidity_pct\": {:.2}}}}}",
        total_links, deterministic_links, syntax_probability
    );

    io::stdout().write_all(output.as_bytes()).unwrap();
}
