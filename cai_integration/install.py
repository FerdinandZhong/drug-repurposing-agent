"""Install AMP dependencies and build the production frontend."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

def project_root() -> Path:
    """Resolve the project root in a script or a Workbench notebook cell."""
    script_path = globals().get("__file__")
    if script_path:
        return Path(script_path).resolve().parents[1]
    for candidate in (Path.cwd(), Path("/home/cdsw")):
        if (candidate / "requirements.txt").is_file() and (candidate / "frontend").is_dir():
            return candidate
    raise RuntimeError("Could not locate the drug-repurposing project root")


ROOT = project_root()


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
