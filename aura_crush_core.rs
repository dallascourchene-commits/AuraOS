//! Aura context-crush accelerator.
//! stdin: {"operation":"crush_json|crush_log|crush_text","payload_hex":"..."}
//! stdout: {"status":"success","accelerator":"rust:aura_crush_core","operation":"...","compressed_hex":"..."}

use std::io::{self, Read};

fn extract_json_string(raw: &str, key: &str) -> String {
    let pattern = format!("\"{}\"", key);
    let Some(key_idx) = raw.find(&pattern) else {
        return String::new();
    };
    let rest = &raw[key_idx + pattern.len()..];
    let Some(colon_idx) = rest.find(':') else {
        return String::new();
    };
    let value = rest[colon_idx + 1..].trim_start();
    let Some(stripped) = value.strip_prefix('"') else {
        return String::new();
    };
    let mut out = String::new();
    let mut escape = false;
    for ch in stripped.chars() {
        if escape {
            out.push(ch);
            escape = false;
            continue;
        }
        if ch == '\\' {
            escape = true;
            continue;
        }
        if ch == '"' {
            break;
        }
        out.push(ch);
    }
    out
}

fn from_hex_digit(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        b'A'..=b'F' => Some(byte - b'A' + 10),
        _ => None,
    }
}

fn decode_hex(raw: &str) -> Result<Vec<u8>, &'static str> {
    let bytes = raw.as_bytes();
    if bytes.len() % 2 != 0 {
        return Err("payload_hex_odd_length");
    }
    let mut out = Vec::with_capacity(bytes.len() / 2);
    let mut idx = 0;
    while idx < bytes.len() {
        let high = match from_hex_digit(bytes[idx]) {
            Some(value) => value,
            None => return Err("payload_hex_invalid_digit"),
        };
        let low = match from_hex_digit(bytes[idx + 1]) {
            Some(value) => value,
            None => return Err("payload_hex_invalid_digit"),
        };
        out.push((high << 4) | low);
        idx += 2;
    }
    Ok(out)
}

fn encode_hex(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0f) as usize] as char);
    }
    out
}

fn crush_json(raw: &str) -> String {
    let mut out = String::with_capacity(raw.len());
    let mut in_string = false;
    let mut escape = false;
    for ch in raw.chars() {
        if escape {
            out.push(ch);
            escape = false;
            continue;
        }
        if ch == '\\' {
            out.push(ch);
            escape = true;
            continue;
        }
        if ch == '"' {
            in_string = in_string == false;
            out.push(ch);
            continue;
        }
        if in_string == false && ch.is_whitespace() {
            continue;
        }
        out.push(ch);
    }
    out
}

fn has_log_signal(line: &str) -> bool {
    let upper = line.to_ascii_uppercase();
    upper.contains("ERROR")
        || upper.contains("FAIL")
        || upper.contains("FATAL")
        || upper.contains("CRITICAL")
        || upper.contains("TRACEBACK")
        || upper.contains("EXCEPTION")
        || upper.contains("WARN")
}

fn mask_line_timestamp(line: &str) -> String {
    let bytes = line.as_bytes();
    if bytes.len() >= 19
        && bytes[4] == b'-'
        && bytes[7] == b'-'
        && (bytes[10] == b' ' || bytes[10] == b'T')
        && bytes[13] == b':'
        && bytes[16] == b':'
    {
        return format!("[T]{}", line.get(19..).unwrap_or(""));
    }
    line.to_string()
}

fn crush_log(raw: &str) -> String {
    let lines: Vec<&str> = raw.lines().collect();
    let mut keep = vec![false; lines.len()];
    for idx in 0..lines.len().min(4) {
        keep[idx] = true;
    }
    for idx in lines.len().saturating_sub(4)..lines.len() {
        keep[idx] = true;
    }
    for (idx, line) in lines.iter().enumerate() {
        if has_log_signal(line) {
            let start = idx.saturating_sub(2);
            let end = (idx + 4).min(lines.len());
            for pos in start..end {
                keep[pos] = true;
            }
        }
    }
    let mut rendered = Vec::new();
    for (idx, line) in lines.iter().enumerate() {
        if keep[idx] {
            rendered.push(format!("{}: {}", idx + 1, mask_line_timestamp(line)));
        }
        if rendered.len() >= 80 {
            break;
        }
    }
    let omitted = lines.len().saturating_sub(rendered.len());
    let mut out = format!(
        "[AURA_RUST_LOG_CRUSH lines={} kept={} omitted={}]",
        lines.len(),
        rendered.len(),
        omitted
    );
    for line in rendered {
        out.push('\n');
        out.push_str(&line);
    }
    out
}

fn crush_text(raw: &str) -> String {
    raw.split_whitespace().collect::<Vec<&str>>().join(" ")
}

fn emit_success(operation: &str, compressed: &str) {
    println!(
        "{{\"status\":\"success\",\"accelerator\":\"rust:aura_crush_core\",\"operation\":\"{}\",\"compressed_hex\":\"{}\"}}",
        operation,
        encode_hex(compressed.as_bytes())
    );
}

fn emit_error(message: &str) {
    println!(
        "{{\"status\":\"error\",\"accelerator\":\"rust:aura_crush_core\",\"message\":\"{}\"}}",
        message.replace('"', "'")
    );
}

fn main() {
    let mut raw = String::new();
    if io::stdin().read_to_string(&mut raw).is_err() {
        emit_error("stdin_read_failed");
        return;
    }
    let operation = extract_json_string(&raw, "operation");
    let payload_hex = extract_json_string(&raw, "payload_hex");
    if operation.is_empty() || payload_hex.is_empty() {
        emit_error("missing_operation_or_payload");
        return;
    }
    let payload = match decode_hex(&payload_hex) {
        Ok(payload) => payload,
        Err(message) => {
            emit_error(message);
            return;
        }
    };
    let input = String::from_utf8_lossy(&payload);
    let compressed = match operation.as_str() {
        "crush_json" => crush_json(&input),
        "crush_log" => crush_log(&input),
        "crush_text" => crush_text(&input),
        _ => {
            emit_error("unsupported_operation");
            return;
        }
    };
    emit_success(&operation, &compressed);
}
