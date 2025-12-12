$ErrorActionPreference = "Stop"

$venvPy = ".\.venv\Scripts\python.exe"
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -U pyinstaller
& $venvPy -m PyInstaller --version
& $venvPy -m PyInstaller --onefile --windowed `
    --add-data "assets;assets" `
    --add-data "data;data" `
    main.py
