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
Copy-Item -Force $brokerSrc $brokerDst

$repoWsl = (& wsl.exe @distroArgs -- wslpath -a -u $RepoPath).Trim()
if (-not $repoWsl) { throw 'WSL_REPO_PATH_UNRESOLVED' }
$bin = '/home/john_of_wick/.config/aura-drive/bin'
$wrapper = "$bin/project006_consumer_outbox_wrapper.py"
$outbox = "$bin/terminal_outbox.py"

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

# Correctness fallback lives on Windows so it can START WSL. It runs the existing
# consumer unchanged and then bridges newly produced terminal receipts to Drive.
$argDistro = if ($Distro) { "-d `"$Distro`" " } else { "" }
$wakeCmd = "wsl.exe ${argDistro}-- python3 $wrapper once"
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -Command `"$wakeCmd`""
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn
$triggerRepeat = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 2)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 4)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($triggerLogon,$triggerRepeat) -Settings $settings -Description 'AuraOS Project006 Windows-resident reconciliation + terminal outbox fallback; starts WSL if stopped.' -Force | Out-Null

# Immediate zero-provider proof: run the existing consumer and flush any current or
# historical local-only terminal for the exact AWJ033 diagnostic onto the outbound bus.
$canaryRaw = (& wsl.exe @distroArgs -- python3 $wrapper once --command-id $CanaryCommandId 2>&1 | Out-String).Trim()
$canaryExit = $LASTEXITCODE
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Milliseconds 500
$task = Get-ScheduledTask -TaskName $TaskName
$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName

$result = [ordered]@{
  status = if ($canaryExit -eq 0) { 'INSTALLED_AND_CANARY_INVOKED' } else { 'INSTALLED_CANARY_FAILED' }
  task = $TaskName
  task_state = [string]$task.State
  last_task_result = $taskInfo.LastTaskResult
  broker = $brokerDst
  fallback = 'WINDOWS_SCHEDULED_RECONCILE_WITH_TERMINAL_OUTBOX'
  primary_event_path = 'WORKSPACE_EVENTS_PUBSUB_WHEN_CONFIGURED'
  consumer_before = $consumerBefore
  consumer_after = $consumerAfter
  terminal_outbox_sha256 = $outboxHash
  wrapper_sha256 = $wrapperHash
  canary_command_id = $CanaryCommandId
  canary_exit_code = $canaryExit
  canary_result = $canaryRaw
}
Write-Output ($result | ConvertTo-Json -Compress -Depth 6)
if ($canaryExit -ne 0) { exit $canaryExit }
