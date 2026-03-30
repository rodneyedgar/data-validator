param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$srcPath = Join-Path $projectRoot 'src'

if (-not (Test-Path $srcPath)) {
    throw "Could not find src folder at $srcPath"
}

$env:PYTHONPATH = $srcPath

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -m cnds_validator
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m cnds_validator
    exit $LASTEXITCODE
}

Add-Type -AssemblyName PresentationFramework
[System.Windows.MessageBox]::Show(
    'Python was not found. Install Python 3 and ensure either py or python is available on PATH.',
    'CNDS Validator Launcher',
    'OK',
    'Error'
) | Out-Null
exit 1
