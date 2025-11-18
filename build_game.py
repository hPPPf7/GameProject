"""Build a PyInstaller executable for the game in a single command.

Run this script from the repository root:
    python build_game.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent
ENTRYPOINT = PROJECT_ROOT / "main.py"
DATA_DIRS = ["assets", "data"]
APP_NAME = "InvestigationDiary"


def require_pyinstaller() -> None:
    """Exit with a helpful message if PyInstaller is not available."""
    try:
        import PyInstaller  # type: ignore[import-not-found,unused-import]
    except Exception:
        print(
            "PyInstaller 未安裝。\n"
            "請先執行：\n"
            f"  {sys.executable} -m pip install pyinstaller",
            file=sys.stderr,
        )
        sys.exit(1)


def build_command() -> List[str]:
    """Construct the PyInstaller command using the current Python."""
    # PyInstaller 的 --add-data：
    #   Windows 用 ';'
    #   其他平台用 ':'
    data_sep = ";" if os.name == "nt" else ":"

    cmd: List[str] = [
        sys.executable,   # 目前正在執行這支腳本的 python（.venv 裡的那個）
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        APP_NAME,
    ]

    for folder in DATA_DIRS:
        src = PROJECT_ROOT / folder
        if src.exists():
            cmd.extend(["--add-data", f"{src}{data_sep}{folder}"])

    cmd.append(str(ENTRYPOINT))
    return cmd


def main() -> None:
    if not ENTRYPOINT.exists():
        print(f"Entry point not found: {ENTRYPOINT}", file=sys.stderr)
        sys.exit(1)

    require_pyinstaller()
    cmd = build_command()
    print("Running build command:")
    print(" ", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True)

    # onefile 模式輸出：dist/InvestigationDiary(.exe)
    if os.name == "nt":
        exe_path = PROJECT_ROOT / "dist" / f"{APP_NAME}.exe"
    else:
        exe_path = PROJECT_ROOT / "dist" / APP_NAME

    if exe_path.exists():
        print(f"\n✅ Build complete. Executable located at:\n  {exe_path}")
    else:
        print("\n⚠ Build finished, but executable not found in dist/. Please check dist/ contents.")


if __name__ == "__main__":
    main()
