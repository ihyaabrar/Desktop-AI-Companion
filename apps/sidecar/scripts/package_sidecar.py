"""Package the FastAPI service for Tauri's externalBin convention.

Run through uv so PyInstaller stays a build-only dependency:
    uv run --with pyinstaller python scripts/package_sidecar.py
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SIDECAR_NAME = "companion-sidecar"


def host_target_triple() -> str:
    machine = platform.machine().lower()
    architecture = "aarch64" if machine in {"arm64", "aarch64"} else "x86_64"
    system = platform.system()
    if system == "Windows":
        return f"{architecture}-pc-windows-msvc"
    if system == "Darwin":
        return f"{architecture}-apple-darwin"
    if system == "Linux":
        return f"{architecture}-unknown-linux-gnu"
    raise RuntimeError(f"Unsupported build host: {system}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", help="Tauri target triple; defaults to the current host")
    args = parser.parse_args()

    sidecar_root = Path(__file__).resolve().parents[1]
    desktop_root = sidecar_root.parent / "desktop"
    work_root = sidecar_root / ".pyinstaller"
    dist_root = work_root / "dist"
    target = args.target or host_target_triple()
    extension = ".exe" if target.endswith("windows-msvc") else ""
    binary_dir = desktop_root / "src-tauri" / "binaries"
    binary_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            # LiteLLM loads its model-cost catalogue at runtime instead of
            # importing it as Python code, so PyInstaller cannot infer it.
            "--collect-data",
            "litellm",
            # Encoding definitions are discovered through the tiktoken plugin
            # namespace rather than ordinary imports.
            "--collect-submodules",
            "tiktoken_ext",
            "--name",
            SIDECAR_NAME,
            "--distpath",
            str(dist_root),
            "--workpath",
            str(work_root / "build"),
            "--specpath",
            str(work_root / "spec"),
            str(sidecar_root / "companion" / "entrypoint.py"),
        ],
        check=True,
        cwd=sidecar_root,
    )

    source = dist_root / f"{SIDECAR_NAME}{extension}"
    destination = binary_dir / f"{SIDECAR_NAME}-{target}{extension}"
    shutil.copy2(source, destination)
    print(f"Bundled sidecar: {destination}")


if __name__ == "__main__":
    main()
