"""Validate the Drug Repurposing Agent AMP contract before import."""
from __future__ import annotations

from pathlib import Path

import yaml

def project_root() -> Path:
    """Resolve the project root in a script or a Workbench notebook cell."""
    script_path = globals().get("__file__")
    if script_path:
        return Path(script_path).resolve().parents[1]
    for candidate in (Path.cwd(), Path("/home/cdsw")):
        if (candidate / ".project-metadata.yaml").is_file() and (candidate / "project.yaml").is_file():
            return candidate
    raise RuntimeError("Could not locate the drug-repurposing project root")


ROOT = project_root()
METADATA = ROOT / ".project-metadata.yaml"
PROJECT = ROOT / "project.yaml"


def validate() -> dict:
    data = yaml.safe_load(METADATA.read_text())
    assert isinstance(data, dict), "AMP metadata must be a YAML mapping"
    for key in ("name", "description", "author", "specification_version", "runtimes", "tasks"):
        assert data.get(key), f"Missing AMP field: {key}"
    assert any(runtime.get("kernel") == "Python 3.11" for runtime in data["runtimes"])
    tasks = {task.get("name"): task for task in data["tasks"]}
    expected = {
        "Install Dependencies": "run_session",
        "Verify Prepared Demo": "run_session",
        "Drug Repurposing Agent": "start_application",
    }
    assert set(expected) <= set(tasks), f"Missing AMP tasks: {set(expected) - set(tasks)}"
    for name, task_type in expected.items():
        task = tasks[name]
        assert task.get("type") == task_type, f"{name} must be {task_type}"
        assert (ROOT / task["script"]).is_file(), f"Missing task script: {task['script']}"
        assert int(task.get("cpu", 0)) > 0 and int(task.get("memory", 0)) > 0
    app = tasks["Drug Repurposing Agent"]
    assert app.get("subdomain") == "drug-repurposing-agent"
    assert app.get("environment_variables", {}).get("TASK_TYPE", {}).get("default") == "START_APPLICATION"

    project = yaml.safe_load(PROJECT.read_text())
    assert project.get("api_version") == "drug-repurposing.cloudera.ai/v1"
    assert project.get("kind") == "ClouderaAIProject"
    assert project["metadata"].get("amp_manifest") == ".project-metadata.yaml"
    assert project["metadata"].get("name") == data["name"]
    project_app = project["spec"]["application"]
    assert project_app.get("script") == app["script"]
    assert project_app.get("subdomain") == app["subdomain"]
    assert project["spec"]["preparation"] == [tasks["Install Dependencies"]["script"], tasks["Verify Prepared Demo"]["script"]]
    return data


if __name__ == "__main__":
    manifest = validate()
    print(f"AMP metadata OK — {len(manifest['tasks'])} tasks")
