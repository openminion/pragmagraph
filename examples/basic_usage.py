"""Minimal standalone `pragmagraph` quickstart example."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

from pragmagraph.adapters import index_path
from pragmagraph.models import QueryRequest
from pragmagraph.query import query
from pragmagraph.storage import load_snapshot, save_snapshot


def run_quickstart(root: str | Path) -> dict[str, object]:
    fixture_root = Path(__file__).resolve().parents[1] / "fixtures" / "tiny_repo"
    snapshot = index_path(fixture_root, namespace="quickstart")
    output_path = Path(root) / "snapshot.json"
    save_snapshot(snapshot, output_path)
    loaded = load_snapshot(output_path)
    result = query(loaded, QueryRequest(query="RuntimeGraph", max_results=3))

    return {
        "node_count": len(loaded.nodes),
        "edge_count": len(loaded.edges),
        "first_hit": result.hits[0].node.label if result.hits else None,
        "snapshot_path": str(output_path),
    }


def main() -> int:
    summary = run_quickstart(Path(tempfile.mkdtemp(prefix="pragmagraph-quickstart-")))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
