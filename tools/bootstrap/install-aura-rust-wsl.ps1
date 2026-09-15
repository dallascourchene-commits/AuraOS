param(
    [string]$Distro = "",
    [string]$RustVersion = "1.98.1"
)

$ErrorActionPreference = "Stop"
$Repo = "dallascourchene-commits/AuraOS"
$InstallerUrl = "https://raw.githubusercontent.com/$Repo/main/tools/bootstrap/install-aura-rust-wsl.sh"
$DoctorUrl = "https://raw.githubusercontent.com/$Repo/main/tools/bootstrap/aura-rust-doctor.sh"

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    throw "HOLD_WSL_MISSING: wsl.exe is not available."
}

$Bash = @'
set -euo pipefail
export AURA_RUST_VERSION="__RUST_VERSION__"
if command -v curl >/dev/null 2>&1; then
  fetch() { curl --fail --silent --show-error --location --retry 3 --retry-all-errors "$1" -o "$2"; }
elif command -v wget >/dev/null 2>&1; then
  fetch() { wget -q --tries=3 -O "$2" "$1"; }
else
  printf 'HOLD_MISSING_PREREQUISITE: curl or wget\n' >&2
  exit 3
fi
tmp_install="$(mktemp)"
tmp_doctor="$(mktemp)"
cleanup() { rm -f "$tmp_install" "$tmp_doctor"; }
trap cleanup EXIT
fetch "__INSTALLER_URL__" "$tmp_install"
bash -n "$tmp_install"
bash "$tmp_install"
. "$HOME/.config/aura/rust.env"
fetch "__DOCTOR_URL__" "$tmp_doctor"
bash -n "$tmp_doctor"
bash "$tmp_doctor"
printf 'AURA_RUST_WINDOWS_WSL_HANDOFF_READY\n'
'@

$Bash = $Bash.Replace("__RUST_VERSION__", $RustVersion).Replace("__INSTALLER_URL__", $InstallerUrl).Replace("__DOCTOR_URL__", $DoctorUrl)

$Args = @()
if ($Distro) {
    $Args += @("-d", $Distro)
}
$Args += @("bash", "-lc", $Bash)

Write-Host "Launching verified Aura Rust bootstrap inside WSL..."
& wsl.exe @Args
if ($LASTEXITCODE -ne 0) {
    throw "HOLD_AURA_RUST_WSL_BOOTSTRAP_FAILED: wsl.exe exited with code $LASTEXITCODE"
}

Write-Host "READY_AURA_RUST_WINDOWS_WSL"
Write-Host "Inside WSL, Rust is configured through ~/.config/aura/rust.env"
Write-Host "Install receipt: ~/.local/state/aura/rust-install-receipt.json"
