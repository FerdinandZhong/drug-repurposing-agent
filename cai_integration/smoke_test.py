"""Offline smoke checks for the Drug Repurposing Agent AMP."""
from __future__ import annotations

import json
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> None:
    graph = json.loads((ROOT / "data" / "seed_graph.json").read_text())
    assert graph.get("entities"), "seed graph has no entities"
    assert graph.get("relationships"), "seed graph has no relationships"
    entity_ids = {entity["id"] for entity in graph["entities"]}
    assert {link["source"] for link in graph["relationships"]} <= entity_ids
    assert {link["target"] for link in graph["relationships"]} <= entity_ids

    from tools.graph_tools import bfs_find_paths, score_repurposing_opportunity  # pylint: disable=import-outside-toplevel
    paths = bfs_find_paths(graph, "Metformin", "Type 2 Diabetes")
    assert paths, "expected a seeded metformin-to-diabetes path"
    metformin = next(entity for entity in graph["entities"] if entity["name"] == "Metformin")
    assert all(isinstance(score_repurposing_opportunity(path, metformin)["overall_score"], (int, float)) for path in paths)

    for source in (ROOT / "backend").rglob("*.py"):
        ast.parse(source.read_text(), filename=str(source))
    assert (ROOT / "frontend" / "dist" / "index.html").is_file(), "frontend/dist/index.html is missing"
    print(f"AMP smoke test OK — {len(graph['entities'])} entities, {len(graph['relationships'])} relationships, {len(paths)} paths")


if __name__ == "__main__":
    main()
