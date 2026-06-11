use std::io::{self, Read};

// 1. Whitespace-Agnostic ST3GG Extractors
fn extract_string(json: &str, key: &str) -> String {
    let key_pattern = format!("\"{}\"", key);
    if let Some(key_idx) = json.find(&key_pattern) {
        let rest = &json[key_idx + key_pattern.len()..];
        if let Some(colon_idx) = rest.find(':') {
            let after_colon = &rest[colon_idx + 1..];
            if let Some(quote_start) = after_colon.find('"') {
                let val_str = &after_colon[quote_start + 1..];
                if let Some(quote_end) = val_str.find('"') {
                    return val_str[..quote_end].to_string();
                }
            }
        }
    }
    "UNKNOWN".to_string()
}

fn extract_bool(json: &str, key: &str) -> bool {
    let key_pattern = format!("\"{}\"", key);
    if let Some(key_idx) = json.find(&key_pattern) {
        let rest = &json[key_idx + key_pattern.len()..];
        if let Some(colon_idx) = rest.find(':') {
            let after_colon = &rest[colon_idx + 1..];
            return after_colon.trim_start().starts_with("true");
        }
    }
    false
}

// 2. High-Speed Hex Decoder
fn hex_to_bytes(hex: &str) -> Vec<u8> {
    let mut bytes = Vec::with_capacity(hex.len() / 2);
    let bytes_str = hex.as_bytes();
    let mut i = 0;
    while i + 1 < bytes_str.len() {
        let high = (bytes_str[i] as char).to_digit(16).unwrap_or(0) as u8;
        let low = (bytes_str[i+1] as char).to_digit(16).unwrap_or(0) as u8;
        bytes.push((high << 4) | low);
        i += 2;
    }
    bytes
}

fn main() {
    let mut raw_input = String::new();
    io::stdin().read_to_string(&mut raw_input).unwrap();

    // 3. Extract ST3GG Protocols & DKT Payloads
    let thought_id = extract_string(&raw_input, "thought_id");
    let st3gg_pointer = extract_string(&raw_input, "st3gg_pointer");
    let st3gg_detected = extract_bool(&raw_input, "st3gg_detected");
    
    let target_hex = extract_string(&raw_input, "target_hex");
    let history_str = extract_string(&raw_input, "history"); // Format: "ID|STATUS|HEX,ID|STATUS|HEX"

    let target_bytes = hex_to_bytes(&target_hex);
    let mut best_match_id = String::from("NONE");
    let mut best_match_status = String::from("UNKNOWN");
    let mut best_distance = u32::MAX;

    // 4. O(1) Hamming Distance Search w/ DKT Status Tracking
    for record in history_str.split(',') {
        let parts: Vec<&str> = record.split('|').collect();
        if parts.len() == 3 { // Updated to expect ID, STATUS, and HEX
            let hist_id = parts[0];
            let hist_status = parts[1];
            let hist_bytes = hex_to_bytes(parts[2]);

            if !target_bytes.is_empty() && target_bytes.len() == hist_bytes.len() {
                // SIMD bitwise XOR distance
                let distance: u32 = target_bytes.iter()
                    .zip(hist_bytes.iter())
                    .map(|(a, b)| (a ^ b).count_ones())
                    .sum();

                if distance < best_distance {
                    best_distance = distance;
                    best_match_id = hist_id.to_string();
                    best_match_status = hist_status.to_string();
                }
            }
        }
    }

    let pointer_status = if st3gg_detected { "true" } else { "false" };

    // 5. Output Results with Predictive Stability Warning
    let output = format!(
        "{{\n  \"status\": \"success\",\n  \"thought_id\": \"{}\",\n  \"operation\": \"WASM_NATIVE_SEMANTIC_SEARCH\",\n  \"st3gg_pointer_received\": {},\n  \"st3gg_pointer_data\": \"{}\",\n  \"metrics\": {{\n    \"closest_memory_match\": \"{}\",\n    \"predicted_stability\": \"{}\",\n    \"hamming_distance\": {}\n  }}\n}}",
        thought_id,
        pointer_status,
        st3gg_pointer,
        best_match_id,
        best_match_status, // Now Aura knows if she is about to crash!
        if best_distance == u32::MAX { 0 } else { best_distance }
    );

    println!("{}", output);
}
