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


def _graphfakos_root(root: Path) -> Path | None:
    candidate = root.parent / "graphfakos"
    return candidate if (candidate / "pyproject.toml").exists() else None


def _test_pythonpath(root: Path) -> str:
    paths = [str(root / "src")]
    graphfakos_root = _graphfakos_root(root)
    if graphfakos_root:
        paths.insert(0, str(graphfakos_root / "src"))
    return os.pathsep.join(paths)


def _ensure_graphfakos_wheel(root: Path, python: str) -> Path | None:
    graphfakos_root = _graphfakos_root(root)
    if graphfakos_root is None:
        return None
    shutil.rmtree(graphfakos_root / "build", ignore_errors=True)
    shutil.rmtree(graphfakos_root / "dist", ignore_errors=True)
    for egg_info in graphfakos_root.glob("src/*.egg-info"):
        shutil.rmtree(egg_info, ignore_errors=True)
    _run([python, "-m", "build"], cwd=graphfakos_root)
    return sorted((graphfakos_root / "dist").glob("graphfakos-*.whl"))[-1]


def _create_temp_venv(root: Path, base_dir: Path) -> dict[str, Path]:
    venv_dir = base_dir / "venv"
    _run([sys.executable, "-m", "venv", str(venv_dir)], cwd=root)
    bin_dir = venv_dir / "bin"
    return {
        "venv": venv_dir,
        "python": bin_dir / "python",
        "pip": bin_dir / "pip",
    }


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
        "pragmagraph.navigation",
        "pragmagraph.interchange",
        "pragmagraph.topology",
        "pragmagraph.docgraph",
        "pragmagraph.planner",
        "pragmagraph.certification",
        "pragmagraph.lineage",
        "pragmagraph.parser_support",
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
        root / "docs" / "advanced-structural-views.md",
        root / "docs" / "benchmarking.md",
        root / "docs" / "certification-readiness-matrix.md",
        root / "docs" / "export-mode.md",
        root / "docs" / "git-history-mode.md",
        root / "docs" / "graphify-interop.md",
        root / "docs" / "navigation-mode.md",
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
        extra_env={"PYTHONPATH": _test_pythonpath(root)},
    )
    _run([python, "-m", "build"], cwd=root)
    if not args.skip_twine:
        dist_files = sorted((root / "dist").glob("*"))
        with tempfile.TemporaryDirectory(prefix="pragmagraph-twine-") as twine_tmp:
            twine_paths = _create_temp_venv(root, Path(twine_tmp))
            _run([str(twine_paths["pip"]), "install", "twine>=5,<7"], cwd=root)
            _run(
                [
                    str(twine_paths["python"]),
                    "-m",
                    "twine",
                    "check",
                    *[str(path) for path in dist_files],
                ],
                cwd=root,
            )
    if not args.skip_wheel_smoke:
        graphfakos_wheel = _ensure_graphfakos_wheel(root, python)
        with tempfile.TemporaryDirectory(prefix="pragmagraph-release-") as tmpdir:
            tmp = Path(tmpdir)
            venv_paths = _create_temp_venv(root, tmp)
            graphfakos_ui = venv_paths["venv"] / "bin" / "graphfakos-ui"
            smoke = venv_paths["venv"] / "bin" / "pragmagraph-smoke"
            ui_preview = venv_paths["venv"] / "bin" / "pragmagraph-ui"
            wheel = sorted((root / "dist").glob("pragmagraph-*.whl"))[-1]
            install_cmd = [str(venv_paths["pip"]), "install"]
            if graphfakos_wheel is not None:
                install_cmd.append(str(graphfakos_wheel))
            install_cmd.append(str(wheel))
            _run(install_cmd, cwd=root)
            _run(
                [
                    str(venv_paths["python"]),
                    "-c",
                    (
                        "from pragmagraph.bench import benchmark_root; "
                        "from pragmagraph.export import render_dot, render_mermaid; "
                        "from pragmagraph.graphify import to_graphify_payload; "
                        "from pragmagraph.service import LocalQueryService; "
                        "from pragmagraph.ui import build_ui_screen_manifest; "
                        "from pragmagraph.workspace import initialize_workspace; "
                        "from pragmagraph.certification import "
                        "build_certification_pack; "
                        "from pragmagraph.docgraph import build_doc_graph_summary; "
                        "from pragmagraph.interchange import "
                        "build_symbol_reference_bundle; "
                        "from pragmagraph.lineage import build_git_lineage; "
                        "from pragmagraph.parser_support import "
                        "build_parser_support_matrix; "
                        "from pragmagraph.planner import explain_query_plan; "
                        "from pragmagraph.topology import build_topology_summary; "
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
                    "--artifact-out",
                    str(tmp / "pragmagraph-artifact.json"),
                    "--embed-out",
                    str(tmp / "pragmagraph-embed.html"),
                    "--report-out",
                    str(tmp / "pragmagraph-report.json"),
                    "--markdown-report-out",
                    str(tmp / "pragmagraph-report.md"),
                    "--json",
                ],
                cwd=root,
            )
            _run_capture(
                [
                    str(graphfakos_ui),
                    "--graph-json",
                    str(tmp / "pragmagraph-artifact.json"),
                    "--screen",
                    "provider_status",
                    "--html-out",
                    str(tmp / "pragmagraph-artifact-replay.html"),
                    "--json",
                ],
                cwd=root,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
