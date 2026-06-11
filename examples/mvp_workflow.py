"""Small package-side PragmaGraph MVP workflow."""

from __future__ import annotations

from pathlib import Path

from pragmagraph.adapters import index_path
from pragmagraph.models import QueryRequest
from pragmagraph.query import query
from pragmagraph.storage import save_snapshot


def main() -> int:
    root = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "repos"
        / "tiny_repo"
    )
    snapshot = index_path(root, namespace="fixture")
    save_snapshot(snapshot, Path(".pragmagraph") / "fixture-snapshot.json")
    result = query(snapshot, QueryRequest(query="RuntimeGraph", max_results=3))
    print(result.to_dict()["hits"][0]["node"]["label"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
