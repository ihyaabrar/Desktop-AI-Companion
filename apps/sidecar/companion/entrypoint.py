"""Executable entry point used by the bundled Tauri sidecar."""

from __future__ import annotations

import argparse

import uvicorn

from companion.main import app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Companion local API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
