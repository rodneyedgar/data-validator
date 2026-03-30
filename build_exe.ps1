param(
    [switch]$Clean,
    [switch]$Package,
    [string]$ReleaseVersion
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$appName = "CNDS Data Validation"
$appSlug = "cnds-data-validation"
$pyprojectPath = Join-Path $projectRoot "pyproject.toml"
$versionInfoPath = Join-Path $projectRoot "windows_version_info.txt"

if (-not $ReleaseVersion) {
    if (-not (Test-Path $pyprojectPath)) {
        throw "Could not find pyproject.toml to determine the release version."
    }

    $pyprojectText = Get-Content $pyprojectPath -Raw
    $versionMatch = [regex]::Match($pyprojectText, '(?m)^version\s*=\s*"([^"]+)"')
    if (-not $versionMatch.Success) {
        throw "Could not determine the project version from pyproject.toml."
    }

    $ReleaseVersion = $versionMatch.Groups[1].Value
}

$versionParts = $ReleaseVersion.Split('.')
while ($versionParts.Count -lt 4) {
    $versionParts += '0'
}
$fileVersion = ($versionParts[0..3] -join '.')
$fileVersionTuple = ($versionParts[0..3] -join ', ')

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$buildRoot = Join-Path $projectRoot ".build"
$distRoot = Join-Path $buildRoot ("dist-" + $timestamp)
$workRoot = Join-Path $buildRoot ("work-" + $timestamp)
$releaseRoot = Join-Path $projectRoot "releases"
$releaseFolderName = "$appSlug-win64-$ReleaseVersion-$timestamp"
$releaseFolder = Join-Path $releaseRoot $releaseFolderName
$releaseZip = Join-Path $releaseRoot ($releaseFolderName + ".zip")
$latestPointer = Join-Path $projectRoot "dist_latest.txt"

$pythonCandidates = @(
    "C:\Users\rodne\AppData\Local\Programs\Python\Python313\python.exe",
    (Get-Command py -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue)
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique

if (-not $pythonCandidates) {
    throw "Python was not found. Install Python 3.11+ to build the executable."
}

$pythonExe = $pythonCandidates[0]

New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null
New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null

@"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($fileVersionTuple),
    prodvers=($fileVersionTuple),
    mask=0x3F,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'Rodne'),
          StringStruct('FileDescription', 'CNDS Data Validation'),
          StringStruct('FileVersion', '$fileVersion'),
          StringStruct('InternalName', 'cnds-validator'),
          StringStruct('OriginalFilename', 'CNDS Data Validation.exe'),
          StringStruct('ProductName', 'CNDS Data Validation'),
          StringStruct('ProductVersion', '$fileVersion')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"@ | Set-Content $versionInfoPath

Write-Host "Using Python: $pythonExe"
Write-Host "Release version: $ReleaseVersion"
Write-Host "Build output: $distRoot"

& $pythonExe -m pip install .[build]
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install build dependencies."
}

$buildArgs = @(
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--distpath",
    $distRoot,
    "--workpath",
    $workRoot,
    "cnds_validator.spec"
)

if ($Clean) {
    $buildArgs += "--clean"
}

Push-Location $projectRoot
try {
    & $pythonExe @buildArgs
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }
}
finally {
    Pop-Location
}

$appOutput = Join-Path $distRoot $appName
if (-not (Test-Path $appOutput)) {
    throw "Expected application output was not created: $appOutput"
}

@"
$appOutput
"@ | Set-Content $latestPointer

if ($Package) {
    Copy-Item -Recurse -Force $appOutput $releaseFolder

    $releaseReadme = Join-Path $releaseFolder "README.txt"
    @"
CNDS Data Validation
Version: $ReleaseVersion
Built: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

How to run:
- Open the folder.
- Double-click '$appName.exe'.

Notes:
- This build bundles Python and does not require a separate Python install.
- Keep the EXE and the _internal folder together.
"@ | Set-Content $releaseReadme

    if (Test-Path $releaseZip) {
        Remove-Item $releaseZip -Force
    }
    Compress-Archive -Path $releaseFolder -DestinationPath $releaseZip

    Write-Host ""
    Write-Host "Release package created."
    Write-Host "Release folder: $releaseFolder"
    Write-Host "Release zip: $releaseZip"
}

Write-Host ""
Write-Host "Build complete."
Write-Host "Application folder: $appOutput"
Write-Host "Pointer file: $latestPointer"
