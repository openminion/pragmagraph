#!/usr/bin/env python3
"""Deterministic release checks for the standalone pragmagraph package."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _run(cmd: list[str], *, cwd: Path, extra_env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd))
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    subprocess.run(cmd, cwd=cwd, check=True, env=env)


def _run_capture(
    cmd: list[str], *, cwd: Path, extra_env: dict[str, str] | None = None
) -> str:
    print("+", " ".join(cmd))
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    print(result.stdout, end="")
    return result.stdout


def _assert_smoke_payload(stdout: str) -> None:
    payload = json.loads(stdout)
    expected_roots = [
        "pragmagraph",
        "pragmagraph.contracts",
        "pragmagraph.models",
        "pragmagraph.query",
        "pragmagraph.storage",
        "pragmagraph.adapters",
        "pragmagraph.bench",
        "pragmagraph.portability",
        "pragmagraph.parsers",
        "pragmagraph.export",
        "pragmagraph.evidence",
        "pragmagraph.graphify",
        "pragmagraph.report",
        "pragmagraph.refresh",
        "pragmagraph.operations",
        "pragmagraph.security",
        "pragmagraph.service",
        "pragmagraph.ui",
        "pragmagraph.workspace",
    ]
    if payload.get("package") != "pragmagraph":
        raise RuntimeError(f"unexpected smoke package: {payload!r}")
    if payload.get("semantic_contract") is not True:
        raise RuntimeError(f"semantic alpha smoke expected: {payload!r}")
    if payload.get("stable_import_roots") != expected_roots:
        raise RuntimeError(f"unexpected stable import roots: {payload!r}")


def _assert_package_docs_shape(root: Path) -> None:
    required_paths = [
        root / "docs" / "README.md",
        root / "docs" / "benchmarking.md",
        root / "docs" / "certification-readiness-matrix.md",
        root / "docs" / "export-mode.md",
        root / "docs" / "git-history-mode.md",
        root / "docs" / "graphify-interop.md",
        root / "docs" / "refresh-operations.md",
        root / "docs" / "report-mode.md",
        root / "docs" / "service-mode.md",
        root / "docs" / "source-tree-owner-map.md",
        root / "docs" / "ui-contracts.md",
        root / "docs" / "workspace-mode.md",
        root / "src" / "pragmagraph" / "README.md",
        root / "tests" / "fixtures" / "repos",
        root / "tests" / "contracts",
    ]
    missing = [
        str(path.relative_to(root)) for path in required_paths if not path.exists()
    ]
    if missing:
        raise RuntimeError(f"package docs/layout drifted: missing {missing!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run pragmagraph release checks")
    parser.add_argument(
        "--skip-twine", action="store_true", help="skip `twine check dist/*`"
    )
    parser.add_argument(
        "--skip-wheel-smoke", action="store_true", help="skip fresh-wheel install smoke"
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    _assert_package_docs_shape(root)
    shutil.rmtree(root / "build", ignore_errors=True)
    shutil.rmtree(root / "dist", ignore_errors=True)
    for egg_info in root.glob("src/*.egg-info"):
        shutil.rmtree(egg_info, ignore_errors=True)

    python = sys.executable
    _run(
        [python, "-m", "pytest", "-q"],
        cwd=root,
        extra_env={"PYTHONPATH": str(root / "src")},
    )
    _run([python, "-m", "build"], cwd=root)
    if not args.skip_twine:
        dist_files = sorted((root / "dist").glob("*"))
        with tempfile.TemporaryDirectory(prefix="pragmagraph-twine-") as twine_tmp:
            twine_venv = Path(twine_tmp) / "venv"
            _run([python, "-m", "venv", str(twine_venv)], cwd=root)
            twine_python = twine_venv / "bin" / "python"
            twine_pip = twine_venv / "bin" / "pip"
            _run([str(twine_pip), "install", "twine>=5,<7"], cwd=root)
            _run(
                [
                    str(twine_python),
                    "-m",
                    "twine",
                    "check",
                    *[str(path) for path in dist_files],
                ],
                cwd=root,
            )
    if not args.skip_wheel_smoke:
        with tempfile.TemporaryDirectory(prefix="pragmagraph-release-") as tmpdir:
            tmp = Path(tmpdir)
            venv_dir = tmp / "venv"
            _run([python, "-m", "venv", str(venv_dir)], cwd=root)
            pip = venv_dir / "bin" / "pip"
            smoke = venv_dir / "bin" / "pragmagraph-smoke"
            ui_preview = venv_dir / "bin" / "pragmagraph-ui"
            wheel = sorted((root / "dist").glob("pragmagraph-*.whl"))[-1]
            _run([str(pip), "install", str(wheel)], cwd=root)
            _run(
                [
                    str(venv_dir / "bin" / "python"),
                    "-c",
                    (
                        "from pragmagraph.bench import benchmark_root; "
                        "from pragmagraph.export import render_dot, render_mermaid; "
                        "from pragmagraph.graphify import to_graphify_payload; "
                        "from pragmagraph.service import LocalQueryService; "
                        "from pragmagraph.ui import build_ui_screen_manifest; "
                        "from pragmagraph.workspace import initialize_workspace; "
                        "from pragmagraph.report import build_report, "
                        "render_markdown_report"
                    ),
                ],
                cwd=root,
            )
            stdout = _run_capture([str(smoke), "--json"], cwd=root)
            _assert_smoke_payload(stdout)
            _run_capture(
                [
                    str(ui_preview),
                    "--screen",
                    "provider_status",
                    "--html-out",
                    str(tmp / "pragmagraph-ui.html"),
                    "--json",
                ],
                cwd=root,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
