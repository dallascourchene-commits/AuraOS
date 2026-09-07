param(
  [Parameter(Mandatory=$true)][string]$RepoPath,
  [string]$Distro = "",
  [string]$Consumer = "/home/john_of_wick/.config/aura-drive/bin/aura_drive_swarm_consumer_v1.py",
  [string]$TaskName = "AuraOS-Project006-Reconcile-Fallback"
)
$ErrorActionPreference='Stop'
$stateRoot = Join-Path $env:LOCALAPPDATA 'AuraOS\Project006'
New-Item -ItemType Directory -Force -Path $stateRoot | Out-Null
$brokerSrc = Join-Path $RepoPath 'tools\project006\windows_wake_broker.py'
$brokerDst = Join-Path $stateRoot 'windows_wake_broker.py'
Copy-Item -Force $brokerSrc $brokerDst

# Correctness fallback deliberately lives on Windows so it can START WSL.
# It is not semantic authority and does not replace Workspace Events/PubSub wake.
$argDistro = if ($Distro) { "-d `"$Distro`" " } else { "" }
$wakeCmd = "wsl.exe ${argDistro}-- python3 $Consumer once"
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -Command `"$wakeCmd`""
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn
$triggerRepeat = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 2)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 3)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($triggerLogon,$triggerRepeat) -Settings $settings -Description 'AuraOS Project006 Windows-resident reconciliation fallback; starts WSL if stopped.' -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Output (@{status='INSTALLED';task=$TaskName;broker=$brokerDst;fallback='WINDOWS_SCHEDULED_RECONCILE';primary_event_path='WORKSPACE_EVENTS_PUBSUB'} | ConvertTo-Json -Compress)
