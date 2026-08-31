<#
.SYNOPSIS
    Thin Windows PowerShell front end for AuraOS external knowledge discovery.
.DESCRIPTION
    Delegates provider semantics to tools.aura_external_discovery_cli so PowerShell
    does not become a second ingestion owner. Discovery is read-only and never
    authorizes code execution, model download, remote code, provider effects, or
    semantic K27/native-KV access.
.EXAMPLE
    .\tools\Invoke-AuraExternalDiscovery.ps1 -Provider ARXIV -Query "agent memory" -Limit 5
.EXAMPLE
    .\tools\Invoke-AuraExternalDiscovery.ps1 -Provider GITHUB -Query "agent framework" -TokenEnv GITHUB_TOKEN -Output .\out\github.json
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("ARXIV", "GITHUB", "HUGGING_FACE", "OPENALEX", "CROSSREF", "SEMANTIC_SCHOLAR", "GOOGLE_SCHOLAR")]
    [string]$Provider,

    [Parameter(Mandatory = $true)]
    [string]$Query,

    [ValidateRange(1, 100)]
    [int]$Limit = 5,

    [string]$TokenEnv,
    [string]$Mailto,

    [ValidateSet("model", "dataset", "space")]
    [string]$RepoType = "model",

    [string]$Output
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        $python = Get-Command py -ErrorAction SilentlyContinue
    }
    if (-not $python) {
        throw "Python was not found on PATH. Install/configure Python before invoking Aura external discovery."
    }

    $argsList = @(
        "-m", "tools.aura_external_discovery_cli",
        "--provider", $Provider,
        "--query", $Query,
        "--limit", $Limit.ToString(),
        "--repo-type", $RepoType
    )
    if ($TokenEnv) { $argsList += @("--token-env", $TokenEnv) }
    if ($Mailto) { $argsList += @("--mailto", $Mailto) }
    if ($Output) {
        $parent = Split-Path -Parent $Output
        if ($parent -and -not (Test-Path $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        $argsList += @("--output", $Output)
    }

    & $python.Source @argsList
    if ($LASTEXITCODE -ne 0) {
        throw "Aura external discovery exited with code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
