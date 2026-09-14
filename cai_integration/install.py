"""Install AMP dependencies and build the production frontend."""
from __future__ import annotations

import os
import shlex
import shutil
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


def install_nodejs() -> None:
    """Ensure npm is available, including in minimal Workbench runtimes."""
    if shutil.which("npm"):
        return

    nvm_dir = Path(os.environ.get("NVM_DIR", Path.home() / ".nvm"))
    nvm_sh = nvm_dir / "nvm.sh"
    if not nvm_sh.is_file():
        print("npm not found; installing nvm and Node.js 22", flush=True)
        subprocess.run(
            ["bash", "-c", "curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash"],
            check=True,
            env=os.environ.copy(),
        )
    if not nvm_sh.is_file():
        raise RuntimeError("npm is unavailable and nvm installation did not create ~/.nvm/nvm.sh")

    subprocess.run(
        ["bash", "-c", f'. "{nvm_sh}" && nvm install 22 && nvm alias default 22'],
        check=True,
        env=os.environ.copy(),
    )
    node_path = subprocess.check_output(
        ["bash", "-c", f'. "{nvm_sh}" && command -v node'],
        text=True,
        env=os.environ.copy(),
    ).strip()
    os.environ["PATH"] = str(Path(node_path).parent) + os.pathsep + os.environ.get("PATH", "")


def run_npm(args: list[str], *, cwd: Path) -> None:
    """Run npm from PATH or by sourcing nvm in a minimal runtime."""
    npm = shutil.which("npm")
    if npm:
        run([npm, *args], cwd=cwd)
        return
    nvm_sh = Path(os.environ.get("NVM_DIR", Path.home() / ".nvm")) / "nvm.sh"
    quoted = " ".join(shlex.quote(arg) for arg in args)
    subprocess.run(["bash", "-c", f'. "{nvm_sh}" && npm {quoted}'], cwd=cwd, check=True, env=os.environ.copy())


def main() -> None:
    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    install_nodejs()
    frontend = ROOT / "frontend"
    lockfile = frontend / "package-lock.json"
    run_npm(["ci" if lockfile.is_file() else "install"], cwd=frontend)
    run_npm(["run", "build"], cwd=frontend)
    assert (frontend / "dist" / "index.html").is_file(), "frontend build did not produce dist/index.html"
    print("AMP dependencies installed and frontend built")


if __name__ == "__main__":
    main()
