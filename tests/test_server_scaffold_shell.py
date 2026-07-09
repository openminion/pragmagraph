from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def test_cli_help_lists_serve_stdio_subcommand() -> None:
    root = Path(__file__).resolve().parents[1]
    env = {"PYTHONPATH": str(root / "src")}
    help_run = subprocess.run(
        [sys.executable, "-m", "pragmagraph.server", "--help"],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "serve-stdio" in help_run.stdout


def test_serve_stdio_help_documents_snapshot_and_root_options() -> None:
    root = Path(__file__).resolve().parents[1]
    env = {"PYTHONPATH": str(root / "src")}
    help_run = subprocess.run(
        [sys.executable, "-m", "pragmagraph.server", "serve-stdio", "--help"],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "--snapshot" in help_run.stdout
    assert "--root" in help_run.stdout
    assert "--git-identity-mode" in help_run.stdout
