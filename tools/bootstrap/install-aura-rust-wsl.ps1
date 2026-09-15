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
tmp_install="$(mktemp)"
tmp_doctor="$(mktemp)"
cleanup() { rm -f "$tmp_install" "$tmp_doctor"; }
trap cleanup EXIT
curl --fail --silent --show-error --location --retry 3 --retry-all-errors "__INSTALLER_URL__" -o "$tmp_install"
bash -n "$tmp_install"
bash "$tmp_install"
. "$HOME/.config/aura/rust.env"
curl --fail --silent --show-error --location --retry 3 --retry-all-errors "__DOCTOR_URL__" -o "$tmp_doctor"
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
