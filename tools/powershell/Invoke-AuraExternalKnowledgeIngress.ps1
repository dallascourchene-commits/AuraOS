<#!
.SYNOPSIS
    Aura EKI-2 external provider ingress adapter for Windows PowerShell.

.DESCRIPTION
    Collects cheap provider metadata, emits an EKI-1 provider envelope, and
    optionally commits it into the versioned aura-coordinate-memory-kv-v1 store
    through tools.aura_external_knowledge_store_writer.

    The adapter deliberately does NOT perform L2-L4 synthesis. It also does not
    treat a provider fetch, persisted CURRENT label, K27 placement, or cache hit
    as execution authority or source-body truth.

    Direct metadata adapters:
      - arXiv Atom API
      - GitHub REST repository + exact default-branch commit
      - Hugging Face Hub model/dataset/Space metadata + exact repo SHA

    Pointer-only adapters:
      - Google Scholar discovery
      - Reddit discovery
      - generic web

    Scholar/Reddit are pointer-only here because EKI-2 does not scrape services
    or bypass provider access/terms. A future authorized provider adapter can
    feed the same envelope contract without changing the store ABI.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('arxiv','github','hf-model','hf-dataset','hf-space','scholar','reddit','web')]
    [string]$Provider,

    [Parameter(Mandatory = $true)]
    [string]$Id,

    [string]$Uri,
    [string]$Title,
    [string]$Thesis,
    [string]$OutputStore = '.\coordinate_store\external-cognition.json',
    [string]$ReceiptPath,
    [string]$EnvelopePath,
    [string]$GitHubToken,
    [string]$HuggingFaceToken,
    [switch]$EnvelopeOnly,
    [string]$PythonCommand
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-UtcIso8601 {
    return [DateTimeOffset]::UtcNow.ToString('o')
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Text
    )
    $full = [System.IO.Path]::GetFullPath($Path)
    $parent = [System.IO.Path]::GetDirectoryName($full)
    if ($parent -and -not [System.IO.Directory]::Exists($parent)) {
        [System.IO.Directory]::CreateDirectory($parent) | Out-Null
    }
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($full, $Text, $utf8)
}

function Normalize-Whitespace {
    param([AllowNull()][string]$Value)
    if ($null -eq $Value) { return '' }
    return (($Value -replace '\s+', ' ').Trim())
}

function Get-ShortThesis {
    param([AllowNull()][string]$Value)
    $normalized = Normalize-Whitespace $Value
    if (-not $normalized) { return 'Provider metadata discovery pointer.' }
    $match = [regex]::Match($normalized, '^(.{1,600}?[.!?])(?:\s|$)')
    if ($match.Success) { return $match.Groups[1].Value }
    if ($normalized.Length -le 600) { return $normalized }
    return $normalized.Substring(0, 600)
}

function Invoke-AuraJsonGet {
    param(
        [Parameter(Mandatory = $true)][string]$RequestUri,
        [hashtable]$Headers = @{}
    )
    $effective = @{
        'Accept' = 'application/json'
        'User-Agent' = 'AuraOS-EKI2/1.0'
    }
    foreach ($key in $Headers.Keys) { $effective[$key] = $Headers[$key] }
    return Invoke-RestMethod -Uri $RequestUri -Method Get -Headers $effective -TimeoutSec 30
}

function New-UnknownRights {
    return [ordered]@{
        state = 'UNKNOWN'
        license_expression = $null
        terms_uri = $null
    }
}

function New-UnknownSecurity {
    return [ordered]@{
        state = 'UNKNOWN'
        remote_code_requested = $null
        network_capability = $null
        write_capability = $null
        secret_capability = $null
        security_notes = @()
    }
}

function New-PointerEnvelope {
    param(
        [Parameter(Mandatory = $true)][string]$SourceKind,
        [Parameter(Mandatory = $true)][string]$ArtifactClass,
        [Parameter(Mandatory = $true)][bool]$AdvisoryOnly
    )
    if (-not $Uri) { throw "-$Provider requires -Uri for pointer-only ingestion." }
    if (-not $Title) { throw "-$Provider requires -Title for pointer-only ingestion." }
    if (-not $Thesis) { throw "-$Provider requires -Thesis for pointer-only ingestion." }
    return [ordered]@{
        source_kind = $SourceKind
        artifact_class = $ArtifactClass
        canonical_id = $Id
        canonical_uri = $Uri
        title = $Title
        thesis = $Thesis
        currentness = 'UNKNOWN'
        generation = $null
        rights = New-UnknownRights
        security = New-UnknownSecurity
        authors_or_owner = @()
        tags = @()
        volatility = 'MEDIUM'
        relevance = 'MEDIUM'
        advisory_only = $AdvisoryOnly
    }
}

function Get-ArxivEnvelope {
    $encodedId = [System.Uri]::EscapeDataString($Id)
    $requestUri = "https://export.arxiv.org/api/query?id_list=$encodedId&start=0&max_results=1"
    $response = Invoke-WebRequest -Uri $requestUri -Method Get -Headers @{
        'User-Agent' = 'AuraOS-EKI2/1.0'
        'Accept' = 'application/atom+xml,application/xml;q=0.9,*/*;q=0.1'
    } -TimeoutSec 30
    [xml]$xml = $response.Content
    $ns = New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
    $ns.AddNamespace('atom', 'http://www.w3.org/2005/Atom')
    $entry = $xml.SelectSingleNode('//atom:entry', $ns)
    if ($null -eq $entry) { throw "arXiv returned no entry for '$Id'." }

    $canonicalUri = Normalize-Whitespace $entry.SelectSingleNode('atom:id', $ns).InnerText
    $paperTitle = Normalize-Whitespace $entry.SelectSingleNode('atom:title', $ns).InnerText
    $summary = Normalize-Whitespace $entry.SelectSingleNode('atom:summary', $ns).InnerText
    $updated = Normalize-Whitespace $entry.SelectSingleNode('atom:updated', $ns).InnerText
    $publishedNode = $entry.SelectSingleNode('atom:published', $ns)
    $published = if ($null -ne $publishedNode) { Normalize-Whitespace $publishedNode.InnerText } else { $null }

    $authors = @()
    foreach ($authorNode in $entry.SelectNodes('atom:author/atom:name', $ns)) {
        $authorName = Normalize-Whitespace $authorNode.InnerText
        if ($authorName) { $authors += $authorName }
    }
    $tags = @()
    foreach ($categoryNode in $entry.SelectNodes('atom:category', $ns)) {
        $term = [string]$categoryNode.GetAttribute('term')
        if ($term) { $tags += $term }
    }

    return [ordered]@{
        source_kind = 'ARXIV'
        artifact_class = 'KNOWLEDGE'
        canonical_id = $canonicalUri
        canonical_uri = $canonicalUri
        title = $paperTitle
        thesis = Get-ShortThesis $summary
        currentness = 'CURRENT'
        generation = [ordered]@{
            generation_type = 'ARXIV_METADATA_REVISION'
            generation_value = "$canonicalUri|$updated"
            checked_at = Get-UtcIso8601
            exact_source_uri = $canonicalUri
            content_sha256 = $null
            etag = $null
            last_modified = $updated
        }
        rights = New-UnknownRights
        security = New-UnknownSecurity
        authors_or_owner = $authors
        tags = $tags
        volatility = 'LOW'
        relevance = 'MEDIUM'
        advisory_only = $false
        provider_metadata = [ordered]@{
            published = $published
            updated = $updated
            abstract_cached_at_l0_only = $true
            source_body_sha256_unresolved = $true
        }
    }
}

function Get-GitHubEnvelope {
    if ($Id -notmatch '^[^/]+/[^/]+$') { throw "GitHub -Id must be owner/repo." }
    $headers = @{}
    if ($GitHubToken) { $headers['Authorization'] = "Bearer $GitHubToken" }
    $repo = Invoke-AuraJsonGet -RequestUri "https://api.github.com/repos/$Id" -Headers $headers
    if (-not $repo.default_branch) { throw "GitHub repository did not expose default_branch." }
    $encodedBranch = [System.Uri]::EscapeDataString([string]$repo.default_branch)
    $commit = Invoke-AuraJsonGet -RequestUri "https://api.github.com/repos/$Id/commits/$encodedBranch" -Headers $headers
    if (-not $commit.sha) { throw "GitHub commit endpoint did not expose sha." }

    $rights = New-UnknownRights
    if ($repo.license -and $repo.license.spdx_id -and $repo.license.spdx_id -ne 'NOASSERTION') {
        $rights = [ordered]@{
            state = 'DECLARED'
            license_expression = [string]$repo.license.spdx_id
            terms_uri = $null
        }
    }
    $repoTitle = if ($repo.full_name) { [string]$repo.full_name } else { $Id }
    $description = if ($repo.description) { [string]$repo.description } else { "GitHub repository $repoTitle." }
    $topics = @()
    if ($repo.topics) { $topics = @($repo.topics | ForEach-Object { [string]$_ }) }

    return [ordered]@{
        source_kind = 'GITHUB'
        artifact_class = 'CODE'
        canonical_id = $repoTitle
        canonical_uri = [string]$repo.html_url
        title = $repoTitle
        thesis = Get-ShortThesis $description
        currentness = 'CURRENT'
        generation = [ordered]@{
            generation_type = 'GIT_COMMIT'
            generation_value = [string]$commit.sha
            checked_at = Get-UtcIso8601
            exact_source_uri = "https://github.com/$Id/tree/$($commit.sha)"
            content_sha256 = $null
            etag = $null
            last_modified = if ($commit.commit.committer.date) { [string]$commit.commit.committer.date } else { $null }
        }
        rights = $rights
        security = New-UnknownSecurity
        authors_or_owner = @([string]$repo.owner.login)
        tags = $topics
        volatility = 'HIGH'
        relevance = 'MEDIUM'
        advisory_only = $false
        provider_metadata = [ordered]@{
            default_branch = [string]$repo.default_branch
            archived = [bool]$repo.archived
            disabled = [bool]$repo.disabled
            fork = [bool]$repo.fork
            pushed_at = [string]$repo.pushed_at
            conditional_request_recommended = $true
        }
    }
}

function Get-HuggingFaceEnvelope {
    param(
        [Parameter(Mandatory = $true)][ValidateSet('model','dataset','space')][string]$RepoType
    )
    if ($Id -notmatch '^[^/]+/[^/]+$') { throw "Hugging Face -Id must be namespace/repo." }
    $headers = @{}
    if ($HuggingFaceToken) { $headers['Authorization'] = "Bearer $HuggingFaceToken" }
    switch ($RepoType) {
        'model'   { $apiSegment = 'models';   $sourceKind = 'HUGGINGFACE_MODEL';   $artifactClass = 'MODEL' }
        'dataset' { $apiSegment = 'datasets'; $sourceKind = 'HUGGINGFACE_DATASET'; $artifactClass = 'DATASET' }
        'space'   { $apiSegment = 'spaces';   $sourceKind = 'HUGGINGFACE_SPACE';   $artifactClass = 'TOOL' }
    }
    $data = Invoke-AuraJsonGet -RequestUri "https://huggingface.co/api/$apiSegment/$Id" -Headers $headers
    if (-not $data.sha) { throw "Hugging Face metadata did not expose repo sha." }

    $tags = @()
    if ($data.tags) { $tags = @($data.tags | ForEach-Object { [string]$_ }) }
    $licenseTag = $tags | Where-Object { $_ -like 'license:*' } | Select-Object -First 1
    $rights = New-UnknownRights
    if ($licenseTag) {
        $rights = [ordered]@{
            state = 'DECLARED'
            license_expression = ([string]$licenseTag).Substring('license:'.Length)
            terms_uri = $null
        }
    }
    $displayId = if ($data.id) { [string]$data.id } elseif ($data.modelId) { [string]$data.modelId } else { $Id }

    return [ordered]@{
        source_kind = $sourceKind
        artifact_class = $artifactClass
        canonical_id = $displayId
        canonical_uri = "https://huggingface.co/$([string]$(if ($RepoType -eq 'dataset') {'datasets/'} elseif ($RepoType -eq 'space') {'spaces/'} else {''}))$Id"
        title = $displayId
        thesis = "Hugging Face $RepoType repository metadata at an exact pinned revision."
        currentness = 'CURRENT'
        generation = [ordered]@{
            generation_type = 'HF_REPO_SHA'
            generation_value = [string]$data.sha
            checked_at = Get-UtcIso8601
            exact_source_uri = "https://huggingface.co/$([string]$(if ($RepoType -eq 'dataset') {'datasets/'} elseif ($RepoType -eq 'space') {'spaces/'} else {''}))$Id/tree/$($data.sha)"
            content_sha256 = $null
            etag = $null
            last_modified = if ($data.lastModified) { [string]$data.lastModified } else { $null }
        }
        rights = $rights
        security = New-UnknownSecurity
        authors_or_owner = @($Id.Split('/')[0])
        tags = $tags
        volatility = 'HIGH'
        relevance = 'MEDIUM'
        advisory_only = $false
        provider_metadata = [ordered]@{
            private = if ($null -ne $data.private) { [bool]$data.private } else { $null }
            gated = if ($null -ne $data.gated) { $data.gated } else { $null }
            disabled = if ($null -ne $data.disabled) { [bool]$data.disabled } else { $null }
            repo_sha_pinned = $true
        }
    }
}

switch ($Provider) {
    'arxiv'      { $envelope = Get-ArxivEnvelope }
    'github'     { $envelope = Get-GitHubEnvelope }
    'hf-model'   { $envelope = Get-HuggingFaceEnvelope -RepoType 'model' }
    'hf-dataset' { $envelope = Get-HuggingFaceEnvelope -RepoType 'dataset' }
    'hf-space'   { $envelope = Get-HuggingFaceEnvelope -RepoType 'space' }
    'scholar'    { $envelope = New-PointerEnvelope -SourceKind 'GOOGLE_SCHOLAR_DISCOVERY' -ArtifactClass 'KNOWLEDGE' -AdvisoryOnly $true }
    'reddit'     { $envelope = New-PointerEnvelope -SourceKind 'REDDIT' -ArtifactClass 'DISCUSSION' -AdvisoryOnly $true }
    'web'        { $envelope = New-PointerEnvelope -SourceKind 'WEB' -ArtifactClass 'KNOWLEDGE' -AdvisoryOnly $true }
    default      { throw "Unsupported provider '$Provider'." }
}

$envelopeJson = $envelope | ConvertTo-Json -Depth 16
if ($EnvelopePath) {
    Write-Utf8NoBom -Path $EnvelopePath -Text ($envelopeJson + [Environment]::NewLine)
}

if ($EnvelopeOnly) {
    $envelopeJson
    exit 0
}

$tempEnvelope = [System.IO.Path]::GetTempFileName()
try {
    Write-Utf8NoBom -Path $tempEnvelope -Text ($envelopeJson + [Environment]::NewLine)

    $pythonExe = $PythonCommand
    $pythonPrefix = @()
    if (-not $pythonExe) {
        if (Get-Command python -ErrorAction SilentlyContinue) {
            $pythonExe = 'python'
        } elseif (Get-Command py -ErrorAction SilentlyContinue) {
            $pythonExe = 'py'
            $pythonPrefix = @('-3')
        } else {
            throw 'Python 3 is required. Install Python or pass -PythonCommand.'
        }
    }

    $arguments = @()
    $arguments += $pythonPrefix
    $arguments += @(
        '-m', 'tools.aura_external_knowledge_store_writer',
        '--envelope', $tempEnvelope,
        '--store', $OutputStore
    )
    if ($ReceiptPath) {
        $arguments += @('--receipt', $ReceiptPath)
    }

    & $pythonExe @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "EKI-2 writer exited with code $LASTEXITCODE."
    }
} finally {
    Remove-Item -LiteralPath $tempEnvelope -Force -ErrorAction SilentlyContinue
}
