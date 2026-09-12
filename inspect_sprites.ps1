$ErrorActionPreference = "Stop"
$inspectorPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $inspectorPython)) {
    $inspectorPython = (Get-Command python -ErrorAction Stop).Source
}
& $inspectorPython (Join-Path $PSScriptRoot 'sprite_sheet_inspector.py') @args
