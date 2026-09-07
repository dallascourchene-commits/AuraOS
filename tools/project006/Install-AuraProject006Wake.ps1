param(
  [Parameter(Mandatory=$true)][string]$RepoPath,
  [string]$Distro = "",
  [string]$Consumer = "/home/john_of_wick/.config/aura-drive/bin/aura_drive_swarm_consumer_v1.py",
  [string]$TaskName = "AuraOS-Project006-Reconcile-Fallback",
  [string]$CanaryCommandId = "AWJ033-CURRENT-CONSUMER-WAKE-ADMISSION-DIAGNOSTIC-20260902T234505Z-R1"
)
$ErrorActionPreference='Stop'
$distroArgs = @()
if ($Distro) { $distroArgs = @('-d', $Distro) }
$stateRoot = Join-Path $env:LOCALAPPDATA 'AuraOS\Project006'
New-Item -ItemType Directory -Force -Path $stateRoot | Out-Null
$brokerSrc = Join-Path $RepoPath 'tools\project006\windows_wake_broker.py'
$brokerDst = Join-Path $stateRoot 'windows_wake_broker.py'
$guardianSrc = Join-Path $RepoPath 'tools\project006\windows_reconcile_guardian.ps1'
$guardianDst = Join-Path $stateRoot 'windows_reconcile_guardian.ps1'
Copy-Item -Force $brokerSrc $brokerDst
Copy-Item -Force $guardianSrc $guardianDst

$repoWsl = (& wsl.exe @distroArgs -- wslpath -a -u $RepoPath).Trim()
if (-not $repoWsl) { throw 'WSL_REPO_PATH_UNRESOLVED' }
$bin = '/home/john_of_wick/.config/aura-drive/bin'
$wrapper = "$bin/project006_consumer_outbox_wrapper.py"
$outbox = "$bin/terminal_outbox.py"
$bridgePython = '/home/john_of_wick/.local/lib/aura/project006/egress-venv/bin/python'

$consumerBefore = (& wsl.exe @distroArgs -- sha256sum $Consumer 2>$null | Out-String).Trim()
& wsl.exe @distroArgs -- install -m 0644 "$repoWsl/tools/project006/terminal_outbox.py" $outbox
if ($LASTEXITCODE -ne 0) { throw 'INSTALL_TERMINAL_OUTBOX_FAILED' }
& wsl.exe @distroArgs -- install -m 0755 "$repoWsl/tools/project006/project006_consumer_outbox_wrapper.py" $wrapper
if ($LASTEXITCODE -ne 0) { throw 'INSTALL_CONSUMER_OUTBOX_WRAPPER_FAILED' }
$outboxHash = (& wsl.exe @distroArgs -- sha256sum $outbox | Out-String).Trim()
$wrapperHash = (& wsl.exe @distroArgs -- sha256sum $wrapper | Out-String).Trim()
$consumerAfter = (& wsl.exe @distroArgs -- sha256sum $Consumer 2>$null | Out-String).Trim()
if ($consumerBefore -and $consumerAfter -and ($consumerBefore.Split(' ')[0] -ne $consumerAfter.Split(' ')[0])) {
  throw 'INSTALLED_CONSUMER_CHANGED_UNEXPECTEDLY'
}

function Install-UserSessionGuardian {
  $startup = [Environment]::GetFolderPath('Startup')
  if (-not $startup) { throw 'WINDOWS_STARTUP_FOLDER_UNRESOLVED' }
  $startupCmd = Join-Path $startup 'AuraOS-Project006-Guardian.cmd'
  $distroArg = if ($Distro) { " -Distro `"$Distro`"" } else { "" }
  $line = "start `"`" powershell.exe -NoProfile -WindowStyle Hidden -File `"$guardianDst`"$distroArg -BridgePython `"$bridgePython`" -Wrapper `"$wrapper`""
  @('@echo off', $line) | Set-Content -Encoding ASCII -Path $startupCmd
  $args = @('-NoProfile','-WindowStyle','Hidden','-File',$guardianDst)
  if ($Distro) { $args += @('-Distro',$Distro) }
  $args += @('-BridgePython',$bridgePython,'-Wrapper',$wrapper)
  Start-Process -FilePath 'powershell.exe' -ArgumentList $args -WindowStyle Hidden | Out-Null
  return $startupCmd
}

# Preferred correctness fallback: Task Scheduler. On the real owner host this can
# fail with Access is denied / 0x80070005 under a non-elevated user token. That
# privilege boundary MUST NOT be hidden or converted into a boot-level liveness
# claim. In that exact case, install a per-user Startup guardian that remains a
# Windows process and can invoke wsl.exe after the distro is stopped.
$argDistro = if ($Distro) { "-d `"$Distro`" " } else { "" }
$wakeCmd = "wsl.exe ${argDistro}-- $bridgePython $wrapper once"
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -Command `"$wakeCmd`""
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn
$triggerRepeat = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 2)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 4)

$taskInstalled = $false
$taskRegistrationError = $null
$startupGuardian = $null
$livenessMode = 'NONE'
try {
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($triggerLogon,$triggerRepeat) -Settings $settings -Description 'AuraOS Project006 Windows-resident reconciliation + terminal outbox fallback; starts WSL if stopped.' -Force | Out-Null
  $taskInstalled = $true
  $livenessMode = 'WINDOWS_SCHEDULED_RECONCILE'
} catch {
  $taskRegistrationError = $_.Exception.ToString()
  $hresultHex = ('0x{0:X8}' -f ($_.Exception.HResult -band 0xffffffffL))
  $isAccessDenied = ($hresultHex -eq '0x80070005') -or ($taskRegistrationError -match '0x80070005') -or ($taskRegistrationError -match 'Access is denied')
  if (-not $isAccessDenied) { throw }
  $startupGuardian = Install-UserSessionGuardian
  $livenessMode = 'WINDOWS_USER_SESSION_GUARDIAN'
}

# Immediate zero-provider admission/return proof. This proves the installed wrapper
# can return the execution-false AWJ033 canary. It deliberately does NOT prove
# wake-from-stopped: that requires a later destructive WSL-stop observation.
$canaryRaw = (& wsl.exe @distroArgs -- $bridgePython $wrapper once --command-id $CanaryCommandId 2>&1 | Out-String).Trim()
$canaryExit = $LASTEXITCODE
$canaryObj = $null
try { $canaryObj = $canaryRaw | ConvertFrom-Json } catch { $canaryObj = $null }
$published = @()
if ($null -ne $canaryObj -and $null -ne $canaryObj.published) { $published = @($canaryObj.published) }
$outboundIds = @($published | Where-Object { $_.status -eq 'RETURN_WRITTEN' -and $_.outbound_file_id } | ForEach-Object { [string]$_.outbound_file_id })
$canaryVerified = ($canaryExit -eq 0 -and $outboundIds.Count -gt 0)

$taskState = $null
$lastTaskResult = $null
if ($taskInstalled) {
  Start-ScheduledTask -TaskName $TaskName
  Start-Sleep -Milliseconds 500
  $task = Get-ScheduledTask -TaskName $TaskName
  $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
  $taskState = [string]$task.State
  $lastTaskResult = $taskInfo.LastTaskResult
}

$installationAcceptance = ($canaryVerified -and ($taskInstalled -or $startupGuardian))
$result = [ordered]@{
  status = if ($installationAcceptance) { 'INSTALLED_CANARY_RETURN_WRITTEN' } elseif ($canaryExit -ne 0) { 'INSTALLED_CANARY_FAILED' } else { 'INSTALLED_CANARY_NO_OUTBOUND' }
  installation_acceptance = [bool]$installationAcceptance
  physical_acceptance = $false
  wake_from_stopped_proven = $false
  owner_session_liveness = [bool]($taskInstalled -or $startupGuardian)
  boot_level_liveness = $false
  boot_level_liveness_reason = 'Requires a separately authorized Windows service/SYSTEM or equivalent pre-login owner; neither AtLogOn task nor Startup guardian proves this.'
  liveness_mode = $livenessMode
  task = $TaskName
  task_installed = $taskInstalled
  task_state = $taskState
  last_task_result = $lastTaskResult
  task_registration_error = $taskRegistrationError
  startup_guardian = $startupGuardian
  guardian = $guardianDst
  broker = $brokerDst
  primary_event_path = 'WORKSPACE_EVENTS_PUBSUB_WHEN_CONFIGURED'
  consumer_before = $consumerBefore
  consumer_after = $consumerAfter
  terminal_outbox_sha256 = $outboxHash
  wrapper_sha256 = $wrapperHash
  canary_command_id = $CanaryCommandId
  canary_exit_code = $canaryExit
  outbound_file_ids = $outboundIds
  provider_effect_authorized_for_canary = $false
  canary_result = $canaryRaw
}
Write-Output ($result | ConvertTo-Json -Compress -Depth 8)
if (-not $installationAcceptance) { exit 23 }
