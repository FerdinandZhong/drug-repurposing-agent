"""Install AMP dependencies and build the production frontend."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    print("$", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True, env=os.environ.copy())


def main() -> None:
    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    frontend = ROOT / "frontend"
    lockfile = frontend / "package-lock.json"
    run(["npm", "ci" if lockfile.is_file() else "install"], cwd=frontend)
    run(["npm", "run", "build"], cwd=frontend)
    assert (frontend / "dist" / "index.html").is_file(), "frontend build did not produce dist/index.html"
    print("AMP dependencies installed and frontend built")


if __name__ == "__main__":
    main()

