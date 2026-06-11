use serde::{Deserialize, Serialize};
use std::collections::{HashMap, VecDeque};
use std::io::{self, Read};

// ... [Keep your Node, Edge, and Payload structs exactly the same] ...

fn main() {
    let mut stdin = io::stdin();
    
    // 1. Read the 4-byte length prefix (Little Endian)
    let mut len_buf = [0u8; 4];
    if stdin.read_exact(&mut len_buf).is_err() {
        let err = ErrorResponse { status: "error: cannot read length prefix".to_string() };
        println!("{}", serde_json::to_string(&err).unwrap());
        return;
    }
    let len = u32::from_le_bytes(len_buf) as usize;
    
    // 2. Read the exact byte-length of the payload
    let mut buffer = vec![0u8; len];
    if stdin.read_exact(&mut buffer).is_err() {
        let err = ErrorResponse { status: "error: cannot read payload bytes".to_string() };
        println!("{}", serde_json::to_string(&err).unwrap());
        return;
    }
    
    // 3. Convert bytes back to string and parse
    let input = match String::from_utf8(buffer) {
        Ok(s) => s,
        Err(_) => {
            let err = ErrorResponse { status: "invalid utf8".to_string() };
            println!("{}", serde_json::to_string(&err).unwrap());
            return;
        }
    };

    let payload: DagPayload = match serde_json::from_str(&input) {
        // ... [Rest of Kahn's Algorithm remains exactly the same!]
