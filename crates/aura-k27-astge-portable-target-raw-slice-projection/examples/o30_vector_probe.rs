use aura_k27_astge_portable_target_raw_slice_projection::{
    canonical_payload_bytes, verify_portable_target_raw_slice_projection,
    PortableTargetRawSliceProjectionV1,
};
use std::{env, fs};

fn main() {
    let path = env::args().nth(1).expect("fixture path");
    let raw = fs::read_to_string(path).expect("read fixture");
    let projection: PortableTargetRawSliceProjectionV1 =
        serde_json::from_str(&raw).expect("typed raw-slice projection");
    verify_portable_target_raw_slice_projection(&projection).expect("projection verifies");
    let bytes = canonical_payload_bytes(&projection.payload).expect("canonical payload bytes");
    print!("{}", String::from_utf8(bytes).expect("utf8 JSON"));
}
