$ErrorActionPreference = "Stop"

$venvPy = ".\.venv\Scripts\python.exe"

# Ensure local user save/settings do not affect the packaged build.
$userDataRoot = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { $HOME }
$userDataDir = Join-Path $userDataRoot "GameProject"
$saveFile = Join-Path $userDataDir "save.json"
$settingsFile = Join-Path $userDataDir "settings.json"
Remove-Item -LiteralPath @($saveFile, $settingsFile) -ErrorAction SilentlyContinue

& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -U pyinstaller
& $venvPy -m PyInstaller --version
& $venvPy -m PyInstaller --onefile --windowed `
    --add-data "assets;assets" `
    --add-data "data;data" `
    main.py
