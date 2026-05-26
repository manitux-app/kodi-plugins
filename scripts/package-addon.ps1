param(
    [string]$AddonId = "plugin.video.dizibox",
    [string]$Version,
    [switch]$BumpPatch,
    [string]$RepositoryId = "repository.manitux"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Get-AddonVersion {
    param([string]$AddonXmlPath)

    [xml]$xml = Get-Content -LiteralPath $AddonXmlPath -Raw
    return [string]$xml.addon.version
}

function Set-AddonVersion {
    param(
        [string]$AddonXmlPath,
        [string]$NewVersion
    )

    $text = Get-Content -LiteralPath $AddonXmlPath -Raw
    $updated = [regex]::Replace(
        $text,
        '(?s)(<addon\b[^>]*?\bversion=")[^"]+(")',
        "`${1}$NewVersion`${2}",
        1
    )
    Set-Content -LiteralPath $AddonXmlPath -Value $updated -NoNewline
}

function Get-NextPatchVersion {
    param([string]$CurrentVersion)

    if ($CurrentVersion -notmatch '^(\d+)\.(\d+)\.(\d+)$') {
        throw "Patch artirma icin surum semver biciminde olmali: $CurrentVersion"
    }

    $patch = [int]$Matches[3] + 1
    return "$($Matches[1]).$($Matches[2]).$patch"
}

function Update-RepositoryAddonBlock {
    param(
        [string]$RepositoryXmlPath,
        [string]$AddonId,
        [string]$AddonXmlPath
    )

    $repoText = Get-Content -LiteralPath $RepositoryXmlPath -Raw
    $addonText = (Get-Content -LiteralPath $AddonXmlPath -Raw).Trim()
    $addonText = [regex]::Replace($addonText, '^\s*<\?xml[^>]*>\s*', '')
    $addonText = $addonText.Trim()

    $escapedId = [regex]::Escape($AddonId)
    $pattern = "(?s)<addon\b(?=[^>]*\bid=`"$escapedId`")[\s\S]*?</addon>"

    if ($repoText -notmatch $pattern) {
        $repoText = $repoText -replace '(?s)</addons>\s*$', "$addonText`r`n</addons>`r`n"
    }
    else {
        $repoText = [regex]::Replace($repoText, $pattern, $addonText, 1)
    }

    [xml]$null = $repoText
    Set-Content -LiteralPath $RepositoryXmlPath -Value $repoText -NoNewline
}

function New-AddonZip {
    param(
        [string]$RepoRoot,
        [string]$AddonId,
        [string]$Version,
        [string]$RepositoryId
    )

    $addonDir = Join-Path $RepoRoot $AddonId
    $targetDir = Join-Path (Join-Path $RepoRoot $RepositoryId) $AddonId
    $zipPath = Join-Path $targetDir "$AddonId-$Version.zip"

    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }

    Compress-Archive -LiteralPath $addonDir -DestinationPath $zipPath -CompressionLevel Optimal
    return $zipPath
}

$root = Get-RepoRoot
$addonDir = Join-Path $root $AddonId
$addonXml = Join-Path $addonDir "addon.xml"
$repoXml = Join-Path (Join-Path $root $RepositoryId) "addons.xml"
$repoMd5 = "$repoXml.md5"

if (-not (Test-Path -LiteralPath $addonXml)) {
    throw "Addon bulunamadi: $addonXml"
}
if (-not (Test-Path -LiteralPath $repoXml)) {
    throw "Repository addons.xml bulunamadi: $repoXml"
}
if ($Version -and $BumpPatch) {
    throw "-Version ve -BumpPatch birlikte kullanilamaz."
}

$currentVersion = Get-AddonVersion -AddonXmlPath $addonXml
$targetVersion = $currentVersion

if ($BumpPatch) {
    $targetVersion = Get-NextPatchVersion -CurrentVersion $currentVersion
}
elseif ($Version) {
    $targetVersion = $Version
}

if ($targetVersion -ne $currentVersion) {
    Set-AddonVersion -AddonXmlPath $addonXml -NewVersion $targetVersion
}

Update-RepositoryAddonBlock -RepositoryXmlPath $repoXml -AddonId $AddonId -AddonXmlPath $addonXml
$zipPath = New-AddonZip -RepoRoot $root -AddonId $AddonId -Version $targetVersion -RepositoryId $RepositoryId

$hash = (Get-FileHash -LiteralPath $repoXml -Algorithm MD5).Hash.ToLower()
Set-Content -LiteralPath $repoMd5 -Value $hash -NoNewline

Write-Host "Addon: $AddonId"
Write-Host "Version: $targetVersion"
Write-Host "Zip: $zipPath"
Write-Host "MD5: $hash"
