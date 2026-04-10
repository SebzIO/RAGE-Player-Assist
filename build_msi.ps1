$ErrorActionPreference = "Stop"

$configModulePath = Join-Path $PSScriptRoot "config\app_config.py"
$configModuleText = Get-Content $configModulePath -Raw
$versionMatch = [regex]::Match($configModuleText, 'SOURCE_APP_VERSION = "([^"]+)"')
if (-not $versionMatch.Success) {
    throw "Could not determine SOURCE_APP_VERSION from $configModulePath"
}

$buildVersion = $versionMatch.Groups[1].Value
$releaseTag = ""
if ($null -ne $env:RPA_RELEASE_TAG) {
    $releaseTag = $env:RPA_RELEASE_TAG.Trim()
}
if ($releaseTag) {
    $normalizedTag = if ($releaseTag.StartsWith("v")) { $releaseTag.Substring(1) } else { $releaseTag }
    if ($normalizedTag -ne $buildVersion) {
        throw "Release tag '$releaseTag' does not match SOURCE_APP_VERSION '$buildVersion'."
    }
}

$packageDir = Join-Path $PSScriptRoot "dist\RAGE Player Assist"
if (-not (Test-Path $packageDir)) {
    throw "Packaged app folder not found at $packageDir. Run build_exe.ps1 first."
}

$installerDir = Join-Path $PSScriptRoot "installer"
$productTemplateFile = Join-Path $installerDir "Product.template.wxs"
$generatedProductFile = Join-Path $installerDir "Product.Generated.wxs"
$generatedFilesFile = Join-Path $installerDir "GeneratedFiles.wxs"

function New-StableId {
    param(
        [string]$Prefix,
        [string]$Value
    )

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
    $sha = [System.Security.Cryptography.SHA1]::Create()
    try {
        $hash = $sha.ComputeHash($bytes)
    } finally {
        $sha.Dispose()
    }
    $hex = ([System.BitConverter]::ToString($hash)).Replace("-", "")
    return "$Prefix$($hex.Substring(0, 16))"
}

function Escape-Xml {
    param([string]$Text)

    if ($null -eq $Text) {
        return ""
    }

    return [System.Security.SecurityElement]::Escape($Text)
}

$productTemplate = Get-Content $productTemplateFile -Raw
$productDefinition = $productTemplate.Replace("__PRODUCT_VERSION__", $buildVersion)
Set-Content -Path $generatedProductFile -Value $productDefinition -Encoding utf8

$directories = @{}
$directories[""] = @{
    Id = "INSTALLFOLDER"
    Name = "RAGE Player Assist"
    Children = New-Object System.Collections.Generic.List[string]
}
$components = New-Object System.Collections.Generic.List[hashtable]

Get-ChildItem -Path $packageDir -Recurse -File | ForEach-Object {
    $fullPath = $_.FullName
    $relativePath = $fullPath.Substring($packageDir.Length).TrimStart('\')
    $relativeDirectory = Split-Path $relativePath -Parent
    if ($relativeDirectory -eq ".") {
        $relativeDirectory = ""
    }

    if ($relativeDirectory) {
        $segments = $relativeDirectory -split '[\\/]'
        $currentPath = ""
        foreach ($segment in $segments) {
            $childPath = if ($currentPath) { Join-Path $currentPath $segment } else { $segment }
            if (-not $directories.ContainsKey($childPath)) {
                $dirId = New-StableId -Prefix "DIR_" -Value $childPath
                $directories[$childPath] = @{
                    Id = $dirId
                    Name = $segment
                    Children = New-Object System.Collections.Generic.List[string]
                }
                if ($directories[$currentPath].Children -notcontains $childPath) {
                    $directories[$currentPath].Children.Add($childPath)
                }
            }
            $currentPath = $childPath
        }
    }

    $componentId = New-StableId -Prefix "CMP_" -Value $relativePath
    $fileId = if ($relativePath -eq "RAGE Player Assist.exe") { "MAINEXEFILE" } else { New-StableId -Prefix "FIL_" -Value $relativePath }
    $directoryId = $directories[$relativeDirectory].Id
    $components.Add(
        @{
            ComponentId = $componentId
            FileId = $fileId
            DirectoryId = $directoryId
            Source = $fullPath
        }
    )
}

function Write-DirectoryXml {
    param(
        [string]$RelativePath,
        [int]$IndentLevel
    )

    $indent = "  " * $IndentLevel
    $directory = $directories[$RelativePath]
    $lines = New-Object System.Collections.Generic.List[string]

    foreach ($childPath in $directory.Children) {
        $child = $directories[$childPath]
        $lines.Add("$indent<Directory Id=""$($child.Id)"" Name=""$(Escape-Xml $child.Name)"">")
        foreach ($line in Write-DirectoryXml -RelativePath $childPath -IndentLevel ($IndentLevel + 1)) {
            $lines.Add($line)
        }
        $lines.Add("$indent</Directory>")
    }

    return $lines
}

$fileLines = New-Object System.Collections.Generic.List[string]
$fileLines.Add('<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">')
$fileLines.Add('  <Fragment>')
$fileLines.Add('    <DirectoryRef Id="INSTALLFOLDER">')
foreach ($line in Write-DirectoryXml -RelativePath "" -IndentLevel 3) {
    $fileLines.Add($line)
}
$fileLines.Add('    </DirectoryRef>')
$fileLines.Add('  </Fragment>')
$fileLines.Add('  <Fragment>')

$componentsByDirectory = $components | Group-Object DirectoryId
foreach ($group in $componentsByDirectory) {
    $fileLines.Add("    <DirectoryRef Id=""$($group.Name)"">")
    foreach ($component in ($group.Group | Sort-Object Source)) {
        $escapedSource = Escape-Xml $component.Source
        $fileLines.Add("      <Component Id=""$($component.ComponentId)"" Guid=""*"">")
        $fileLines.Add("        <File Id=""$($component.FileId)"" Source=""$escapedSource"" KeyPath=""yes"" />")
        $fileLines.Add('      </Component>')
    }
    $fileLines.Add('    </DirectoryRef>')
}

$fileLines.Add('  </Fragment>')
$fileLines.Add('  <Fragment>')
$fileLines.Add('    <ComponentGroup Id="AppFiles">')
foreach ($component in ($components | Sort-Object ComponentId)) {
    $fileLines.Add("      <ComponentRef Id=""$($component.ComponentId)"" />")
}
$fileLines.Add('    </ComponentGroup>')
$fileLines.Add('    <DirectoryRef Id="ApplicationProgramsFolder">')
$fileLines.Add('      <Component Id="ApplicationShortcut" Guid="*">')
$fileLines.Add('        <Shortcut Id="ApplicationStartMenuShortcut" Name="RAGE Player Assist" Target="[#MAINEXEFILE]" WorkingDirectory="INSTALLFOLDER" />')
$fileLines.Add('        <RemoveFolder Id="RemoveApplicationProgramsFolder" Directory="ApplicationProgramsFolder" On="uninstall" />')
$fileLines.Add('        <RegistryValue Root="HKCU" Key="Software\SebzIO\RAGE Player Assist" Name="StartMenuShortcut" Type="integer" Value="1" KeyPath="yes" />')
$fileLines.Add('      </Component>')
$fileLines.Add('    </DirectoryRef>')
$fileLines.Add('  </Fragment>')
$fileLines.Add('</Wix>')

Set-Content -Path $generatedFilesFile -Value $fileLines -Encoding utf8

$outputDir = Join-Path $PSScriptRoot "dist\installer"
if (Test-Path $outputDir) {
    Remove-Item -Recurse -Force $outputDir
}

& dotnet build (Join-Path $installerDir "RagePlayerAssist.Setup.wixproj") -c Release -o $outputDir | Out-Host

$msiPath = Get-ChildItem -Path $outputDir -Filter *.msi | Select-Object -First 1
if ($null -eq $msiPath) {
    throw "MSI build completed without producing an .msi file in $outputDir"
}

Write-Output $msiPath.FullName
