#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${AURA_RUST_ENV_FILE:-$HOME/.config/aura/rust.env}"
RECEIPT="${AURA_RUST_RECEIPT:-$HOME/.local/state/aura/rust-install-receipt.json}"

test -f "$ENV_FILE" || { echo "HOLD_RUST_ENV_MISSING: $ENV_FILE" >&2; exit 2; }
# shellcheck disable=SC1090
. "$ENV_FILE"

test -n "${AURA_RUST_HOME:-}" || { echo "HOLD_RUST_HOME_UNBOUND" >&2; exit 3; }
test -x "$AURA_RUST_HOME/bin/rustc" || { echo "HOLD_RUSTC_MISSING: $AURA_RUST_HOME/bin/rustc" >&2; exit 4; }
test -x "$AURA_RUST_HOME/bin/cargo" || { echo "HOLD_CARGO_MISSING: $AURA_RUST_HOME/bin/cargo" >&2; exit 5; }

echo "rust_home=$AURA_RUST_HOME"
echo "rustc_path=$(command -v rustc)"
echo "cargo_path=$(command -v cargo)"
rustc --version --verbose
cargo --version --verbose

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cat > "$TMP/doctor.rs" <<'RS'
fn main() { println!("AURA_RUST_DOCTOR_RUSTC_OK"); }
RS
rustc "$TMP/doctor.rs" -o "$TMP/doctor"
test "$("$TMP/doctor")" = "AURA_RUST_DOCTOR_RUSTC_OK"

mkdir -p "$TMP/cargo/src"
cat > "$TMP/cargo/Cargo.toml" <<'TOML'
[package]
name = "aura-rust-doctor"
version = "0.1.0"
edition = "2024"
TOML
cat > "$TMP/cargo/src/main.rs" <<'RS'
fn main() { println!("AURA_RUST_DOCTOR_CARGO_OK"); }
RS
cargo build --offline --quiet --manifest-path "$TMP/cargo/Cargo.toml"
test "$("$TMP/cargo/target/debug/aura-rust-doctor")" = "AURA_RUST_DOCTOR_CARGO_OK"

echo "rustc_smoke=AURA_RUST_DOCTOR_RUSTC_OK"
echo "cargo_offline_smoke=AURA_RUST_DOCTOR_CARGO_OK"
if test -f "$RECEIPT"; then
  echo "receipt=$RECEIPT"
  cat "$RECEIPT"
else
  echo "WARN_RUST_RECEIPT_MISSING: $RECEIPT" >&2
fi

echo "READY_RUST_TOOLCHAIN_DOCTOR"
