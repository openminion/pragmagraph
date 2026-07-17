#!/usr/bin/env python3.11
"""Replace producer-local SCIP project roots in checked-in test fixtures."""

from __future__ import annotations

import argparse
from pathlib import Path

from pragmagraph.interchange._schema import scip_pb2


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize one SCIP fixture to a deterministic project root."
    )
    parser.add_argument("index", type=Path)
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()

    index = scip_pb2.Index()
    index.ParseFromString(args.index.read_bytes())
    index.metadata.project_root = args.project_root
    args.index.write_bytes(index.SerializeToString(deterministic=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
