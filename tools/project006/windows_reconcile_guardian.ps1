param(
  [string]$Distro = "",
  [string]$BridgePython = "/home/john_of_wick/.local/lib/aura/project006/egress-venv/bin/python",
  [string]$Wrapper = "/home/john_of_wick/.config/aura-drive/bin/project006_consumer_outbox_wrapper.py",
  [int]$IntervalSeconds = 60,
  [int]$CycleTimeoutSeconds = 240
)
$ErrorActionPreference = 'Stop'
$stateRoot = Join-Path $env:LOCALAPPDATA 'AuraOS\Project006'
New-Item -ItemType Directory -Force -Path $stateRoot | Out-Null
$heartbeat = Join-Path $stateRoot 'guardian_heartbeat.json'
$stopSentinel = Join-Path $stateRoot 'guardian.stop'
$stdoutPath = Join-Path $stateRoot 'guardian_last_stdout.txt'
$stderrPath = Join-Path $stateRoot 'guardian_last_stderr.txt'

$createdNew = $false
$mutex = New-Object System.Threading.Mutex($true, 'Local\AuraOSProject006GuardianV2', [ref]$createdNew)
if (-not $createdNew) { exit 0 }

function Write-Heartbeat([string]$Phase, [Nullable[int]]$ExitCode, [string]$Detail) {
  $tmp = "$heartbeat.tmp.$PID"
  $obj = [ordered]@{
    schema = 'AuraOSWindowsGuardianV2'
    pid = $PID
    phase = $Phase
    last_exit_code = $ExitCode
    detail = $Detail
    owner_session_liveness = $true
    boot_level_liveness = $false
    observed_at_utc = [DateTime]::UtcNow.ToString('o')
  }
  ($obj | ConvertTo-Json -Compress) | Set-Content -Encoding UTF8 -Path $tmp
  Move-Item -Force $tmp $heartbeat
}

try {
  while (-not (Test-Path $stopSentinel)) {
    Write-Heartbeat 'BEFORE_RECONCILE' $null 'calling existing Project006 wrapper; no new provider authority'
    $args = @()
    if ($Distro) { $args += @('-d', $Distro) }
    $args += @('--', $BridgePython, $Wrapper, 'once')
    Remove-Item -Force -ErrorAction SilentlyContinue $stdoutPath, $stderrPath
    try {
      $p = Start-Process -FilePath 'wsl.exe' -ArgumentList $args -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
      if (-not $p.WaitForExit($CycleTimeoutSeconds * 1000)) {
        try { $p.Kill() } catch {}
        Write-Heartbeat 'RECONCILE_TIMEOUT' 124 'WSL reconcile exceeded bounded timeout'
      } else {
        Write-Heartbeat 'AFTER_RECONCILE' $p.ExitCode 'wrapper once returned; outbound bus remains the evidence owner'
      }
    } catch {
      Write-Heartbeat 'RECONCILE_FAILED' 111 $_.Exception.GetType().Name
    }
    Start-Sleep -Seconds ([Math]::Max(15, $IntervalSeconds))
  }
  Write-Heartbeat 'STOPPED_BY_SENTINEL' 0 'guardian.stop observed'
} finally {
  if ($createdNew) { $mutex.ReleaseMutex() | Out-Null }
  $mutex.Dispose()
}
