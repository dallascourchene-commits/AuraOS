# Aura Rust WSL handoff

Status: **validated end to end** on 2026-09-15.

This path exists for machines where normal `rustup` / package-manager installation is blocked or unreliable. It installs Rust **1.98.1** for `x86_64-unknown-linux-gnu` from the public AuraOS bootstrap release, verifies SHA-256 and the bridge manifest before extraction, then proves both `rustc` and an offline Cargo build before writing an install receipt.

## Fastest path from Windows PowerShell

From an AuraOS checkout:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\bootstrap\install-aura-rust-wsl.ps1
```

For a specific WSL distro:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\bootstrap\install-aura-rust-wsl.ps1 -Distro Ubuntu
```

The PowerShell launcher enters WSL, downloads the checked-in Bash installer, runs the install, sources the generated environment, downloads/runs the doctor, and exits only after both layers pass.

## Direct path from WSL

```bash
bash tools/bootstrap/install-aura-rust-wsl.sh
source ~/.config/aura/rust.env
bash tools/bootstrap/aura-rust-doctor.sh
```

If the repository is not yet cloned, fetch only the installer first:

```bash
tmp="$(mktemp)" && \
  curl --fail --silent --show-error --location --retry 3 \
    https://raw.githubusercontent.com/dallascourchene-commits/AuraOS/main/tools/bootstrap/install-aura-rust-wsl.sh \
    -o "$tmp" && \
  bash -n "$tmp" && bash "$tmp"; rc=$?; rm -f "$tmp"; exit $rc
```

## Success contract

A valid install ends with:

```text
READY_RUST_TOOLCHAIN
```

The doctor ends with:

```text
READY_RUST_TOOLCHAIN_DOCTOR
```

The Windows launcher ends with:

```text
READY_AURA_RUST_WINDOWS_WSL
```

The installed toolchain lives under:

```text
~/.local/share/aura/rust/1.98.1-x86_64-unknown-linux-gnu
```

The persistent environment file is:

```text
~/.config/aura/rust.env
```

The machine-readable receipt is:

```text
~/.local/state/aura/rust-install-receipt.json
```

No `sudo` is required. The installer is idempotent: it validates in staging before replacing the user-local install.

## Release provenance

Release tag:

```text
aura-rust-1.98.1-x86_64-unknown-linux-gnu
```

The release contains the toolchain archive, SHA-256 sidecar, bridge manifest, and Rust/Cargo version receipts. The publishing workflow first verifies the packaged bytes by extracting the exact archive, compiling/running a raw `rustc` program, and compiling/running a dependency-free Cargo project with `cargo build --offline`.

The repository E2E workflow then behaves like a fresh laptop user: it downloads the public release through the installer into an isolated HOME and independently reruns the doctor. Changes to the bootstrap scripts continuously retrigger this E2E path.

## Recovery

If a shell does not immediately see Rust after installation:

```bash
source ~/.config/aura/rust.env
rustc --version
cargo --version
```

If anything is questionable, do not infer success from PATH alone. Run:

```bash
bash tools/bootstrap/aura-rust-doctor.sh
```

Only treat `READY_RUST_TOOLCHAIN_DOCTOR` as the local handoff closure.
