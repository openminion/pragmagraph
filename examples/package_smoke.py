"""Minimal semantic-alpha smoke example for pragmagraph."""

from __future__ import annotations

import json

import pragmagraph


def main() -> int:
    payload = {
        "package": "pragmagraph",
        "version": pragmagraph.__version__,
        "status": pragmagraph.PACKAGE_STATUS,
        "stable_import_roots": list(pragmagraph.STABLE_IMPORT_ROOTS),
        "semantic_contract": True,
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
