"""Run the public PragmaGraph quickstart flow against a tiny local repo."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import tempfile


def _write_demo_repo(root: Path) -> Path:
    repo = root / "demo-repo"
    source_dir = repo / "src"
    source_dir.mkdir(parents=True)
    (repo / "README.md").write_text(
        "# Runtime Graph Demo\n\nThe `RuntimeGraph` symbol lives in `src/app.py`.\n",
        encoding="utf-8",
    )
    (source_dir / "app.py").write_text(
        "class RuntimeGraph:\n"
        "    pass\n"
        "\n"
        "def build_runtime_graph() -> RuntimeGraph:\n"
        "    return RuntimeGraph()\n",
        encoding="utf-8",
    )
    return repo


def run_demo(output_dir: str | Path) -> dict[str, object]:
    output_root = Path(output_dir)
    repo = _write_demo_repo(output_root)
    config_path = output_root / "workspace.toml"
    html_path = output_root / "pragmagraph.html"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "quickstart",
            str(repo),
            "--config",
            str(config_path),
            "--workspace",
            str(output_root / "workspace"),
            "--store",
            str(output_root / "graph.sqlite"),
            "--html-out",
            str(html_path),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    return {
        "screen": payload["screen"],
        "config_path": payload["quickstart"]["config_path"],
        "html_path": str(html_path),
        "next_visual_command": payload["next_commands"]["visual"],
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pragmagraph-demo-") as tmpdir:
        print(json.dumps(run_demo(tmpdir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
