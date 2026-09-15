#!/usr/bin/env bash
set -euo pipefail

RUST_VERSION="${AURA_RUST_VERSION:-1.98.1}"
TARGET="${AURA_RUST_TARGET:-x86_64-unknown-linux-gnu}"
REPO="dallascourchene-commits/AuraOS"
TAG="aura-rust-${RUST_VERSION}-${TARGET}"
ARCHIVE="rust-${RUST_VERSION}-${TARGET}.tar.xz"
BASE_URL="https://github.com/${REPO}/releases/download/${TAG}"

case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) ;;
  *) echo "HOLD_UNSUPPORTED_PLATFORM: expected Linux-x86_64 (WSL is supported), got $(uname -s)-$(uname -m)" >&2; exit 2 ;;
esac

for cmd in sha256sum tar mktemp; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "HOLD_MISSING_PREREQUISITE: $cmd" >&2; exit 3; }
done
if command -v curl >/dev/null 2>&1; then
  fetch() { curl --fail --silent --show-error --location --retry 3 --retry-all-errors "$1" -o "$2"; }
elif command -v wget >/dev/null 2>&1; then
  fetch() { wget -q --tries=3 -O "$2" "$1"; }
else
  echo "HOLD_MISSING_PREREQUISITE: curl or wget" >&2
  exit 3
fi

INSTALL_BASE="${AURA_RUST_INSTALL_BASE:-$HOME/.local/share/aura/rust}"
FINAL_DIR="$INSTALL_BASE/${RUST_VERSION}-${TARGET}"
CONFIG_DIR="$HOME/.config/aura"
STATE_DIR="$HOME/.local/state/aura"
ENV_FILE="$CONFIG_DIR/rust.env"
RECEIPT="$STATE_DIR/rust-install-receipt.json"
TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

echo "[1/7] Fetching verified Aura Rust bridge release ${TAG}"
fetch "$BASE_URL/$ARCHIVE" "$TMP/$ARCHIVE"
fetch "$BASE_URL/$ARCHIVE.sha256" "$TMP/$ARCHIVE.sha256"
fetch "$BASE_URL/aura-rust-bridge-manifest.json" "$TMP/aura-rust-bridge-manifest.json"

echo "[2/7] Verifying SHA-256 before extraction"
(
  cd "$TMP"
  sha256sum -c "$ARCHIVE.sha256"
)
ARCHIVE_SHA256="$(sha256sum "$TMP/$ARCHIVE" | awk '{print $1}')"

echo "[3/7] Extracting into isolated staging directory"
mkdir -p "$TMP/extract"
tar -xJf "$TMP/$ARCHIVE" -C "$TMP/extract"
TOOLCHAIN_DIR="$(find "$TMP/extract" -mindepth 1 -maxdepth 1 -type d | head -n1)"
test -n "$TOOLCHAIN_DIR"
test -x "$TOOLCHAIN_DIR/bin/rustc"
test -x "$TOOLCHAIN_DIR/bin/cargo"

export PATH="$TOOLCHAIN_DIR/bin:$PATH"
export RUSTC="$TOOLCHAIN_DIR/bin/rustc"

echo "[4/7] Validating relocated rustc and cargo"
RUSTC_VERBOSE="$(rustc --version --verbose)"
CARGO_VERBOSE="$(cargo --version --verbose)"
printf '%s\n' "$RUSTC_VERBOSE"
printf '%s\n' "$CARGO_VERBOSE"
case "$RUSTC_VERBOSE" in
  *"rustc ${RUST_VERSION}"*) ;;
  *) echo "HOLD_RUST_VERSION_MISMATCH" >&2; exit 4 ;;
esac

cat > "$TMP/hello.rs" <<'RS'
fn main() { println!("AURA_RUST_RUSTC_OK"); }
RS
rustc "$TMP/hello.rs" -o "$TMP/hello"
test "$("$TMP/hello")" = "AURA_RUST_RUSTC_OK"

mkdir -p "$TMP/cargo-smoke/src"
cat > "$TMP/cargo-smoke/Cargo.toml" <<'TOML'
[package]
name = "aura-rust-smoke"
version = "0.1.0"
edition = "2024"
TOML
cat > "$TMP/cargo-smoke/src/main.rs" <<'RS'
fn main() { println!("AURA_RUST_CARGO_OK"); }
RS
cargo build --offline --quiet --manifest-path "$TMP/cargo-smoke/Cargo.toml"
test "$("$TMP/cargo-smoke/target/debug/aura-rust-smoke")" = "AURA_RUST_CARGO_OK"

echo "[5/7] Promoting validated toolchain into user-local install"
mkdir -p "$INSTALL_BASE" "$CONFIG_DIR" "$STATE_DIR" "$HOME/.local/bin"
rm -rf "$FINAL_DIR.new"
mv "$TOOLCHAIN_DIR" "$FINAL_DIR.new"
rm -rf "$FINAL_DIR"
mv "$FINAL_DIR.new" "$FINAL_DIR"
ln -sfn "$FINAL_DIR/bin/rustc" "$HOME/.local/bin/rustc"
ln -sfn "$FINAL_DIR/bin/cargo" "$HOME/.local/bin/cargo"
if test -x "$FINAL_DIR/bin/rustdoc"; then ln -sfn "$FINAL_DIR/bin/rustdoc" "$HOME/.local/bin/rustdoc"; fi

cat > "$ENV_FILE" <<EOF
# Managed by Aura Rust bootstrap. Safe to source repeatedly.
export AURA_RUST_HOME="$FINAL_DIR"
export RUSTC="$FINAL_DIR/bin/rustc"
case ":\$PATH:" in
  *":$FINAL_DIR/bin:"*) ;;
  *) export PATH="$FINAL_DIR/bin:\$PATH" ;;
esac
EOF

SOURCE_LINE='test -f "$HOME/.config/aura/rust.env" && . "$HOME/.config/aura/rust.env"'
touch "$HOME/.bashrc"
grep -Fqx "$SOURCE_LINE" "$HOME/.bashrc" || printf '\n%s\n' "$SOURCE_LINE" >> "$HOME/.bashrc"
# shellcheck disable=SC1090
. "$ENV_FILE"

echo "[6/7] Re-validating from promoted path"
test "$(rustc "$TMP/hello.rs" -o "$TMP/hello-promoted" >/dev/null 2>&1; "$TMP/hello-promoted")" = "AURA_RUST_RUSTC_OK"
rm -rf "$TMP/cargo-promoted"
cp -a "$TMP/cargo-smoke" "$TMP/cargo-promoted"
rm -rf "$TMP/cargo-promoted/target"
cargo build --offline --quiet --manifest-path "$TMP/cargo-promoted/Cargo.toml"
test "$("$TMP/cargo-promoted/target/debug/aura-rust-smoke")" = "AURA_RUST_CARGO_OK"

RUSTC_LINE="$(rustc --version)"
CARGO_LINE="$(cargo --version)"
cat > "$RECEIPT" <<EOF
{
  "schema": "aura.rust.install.receipt.v1",
  "status": "READY_RUST_TOOLCHAIN",
  "rust_version_requested": "$RUST_VERSION",
  "target": "$TARGET",
  "rustc": "$RUSTC_LINE",
  "cargo": "$CARGO_LINE",
  "archive_sha256": "$ARCHIVE_SHA256",
  "install_dir": "$FINAL_DIR",
  "rustc_path": "$FINAL_DIR/bin/rustc",
  "cargo_path": "$FINAL_DIR/bin/cargo",
  "bridge_release": "$TAG",
  "bridge_manifest_url": "$BASE_URL/aura-rust-bridge-manifest.json",
  "rustc_smoke": "AURA_RUST_RUSTC_OK",
  "cargo_offline_smoke": "AURA_RUST_CARGO_OK"
}
EOF

echo "[7/7] READY_RUST_TOOLCHAIN"
echo "$RUSTC_LINE"
echo "$CARGO_LINE"
echo "receipt=$RECEIPT"
echo "env=$ENV_FILE"
echo "Restart your shell or run: source '$ENV_FILE'"
