$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Virtual environment Python not found at $python"
}

$configModulePath = Join-Path $PSScriptRoot "config\app_config.py"
$configModuleText = Get-Content $configModulePath -Raw
$versionMatch = [regex]::Match($configModuleText, 'SOURCE_APP_VERSION = "([^"]+)"')
if (-not $versionMatch.Success) {
    throw "Could not determine SOURCE_APP_VERSION from $configModulePath"
}

$buildVersion = $versionMatch.Groups[1].Value
$releaseTag = ($env:RPA_RELEASE_TAG ?? "").Trim()
if ($releaseTag) {
    $normalizedTag = if ($releaseTag.StartsWith("v")) { $releaseTag.Substring(1) } else { $releaseTag }
    if ($normalizedTag -ne $buildVersion) {
        throw "Release tag '$releaseTag' does not match SOURCE_APP_VERSION '$buildVersion'."
    }
}

$commitSha = ""
try {
    $commitSha = (git rev-parse --short HEAD).Trim()
} catch {
    $commitSha = ""
}

$buildMetadataPath = Join-Path $PSScriptRoot "build_metadata.json"
$buildMetadata = @{
    version = $buildVersion
    release_tag = $releaseTag
    commit_sha = $commitSha
    built_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm 'UTC'")
}
$buildMetadata | ConvertTo-Json | Set-Content -Path $buildMetadataPath -Encoding utf8

$buildDir = Join-Path $PSScriptRoot "build"
$distDir = Join-Path $PSScriptRoot "dist"
if (Test-Path $buildDir) {
    try {
        Remove-Item -Recurse -Force $buildDir
    } catch {
        throw "Unable to remove build folder. Close any running build-related processes and try again. Locked path: $buildDir"
    }
}
if (Test-Path $distDir) {
    try {
        Remove-Item -Recurse -Force $distDir
    } catch {
        throw "Unable to remove dist folder. Close any running RAGE Player Assist executable from dist and try again. Locked path: $distDir"
    }
}

$pyinstallerCheck = & $python -c "import importlib.util; import sys; missing = [name for name in ('PyInstaller', 'pygame', 'PySide6') if importlib.util.find_spec(name) is None]; sys.exit(1 if missing else 0)"
if ($LASTEXITCODE -ne 0) {
    throw "Missing required build dependencies. Install PyInstaller, pygame, and PySide6 into the project .venv before building."
}

& $python -m PyInstaller --noconfirm "$PSScriptRoot\rage_player_assist.spec"
