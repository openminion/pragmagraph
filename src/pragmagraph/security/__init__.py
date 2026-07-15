"""Scope and containment policy for local PragmaGraph indexing."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path

from pragmagraph.models import ParserDiagnostic
from pragmagraph.portability import normalize_relative_path

DEFAULT_IGNORES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    }
)

DEFAULT_MAX_FILE_BYTES = 1_000_000
TEXT_SUFFIXES = frozenset(
    {
        ".cjs",
        ".js",
        ".json",
        ".jsx",
        ".md",
        ".mjs",
        ".lock",
        ".in",
        ".proto",
        ".py",
        ".rst",
        ".sql",
        ".tf",
        ".toml",
        ".ts",
        ".tsx",
        ".txt",
        ".yaml",
        ".yml",
    }
)


@dataclass(frozen=True)
class ScopePolicy:
    """Fail-closed local file policy for deterministic indexing."""

    ignore_names: frozenset[str] = DEFAULT_IGNORES
    include_globs: tuple[str, ...] = ()
    exclude_globs: tuple[str, ...] = ()
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    follow_symlinks: bool = False
    respect_gitignore: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "ignore_names", frozenset(self.ignore_names))
        object.__setattr__(self, "include_globs", tuple(self.include_globs))
        object.__setattr__(self, "exclude_globs", tuple(self.exclude_globs))
        object.__setattr__(self, "max_file_bytes", int(self.max_file_bytes))


def escape_label(text: object) -> str:
    """Normalize labels without inferring semantics."""
    return " ".join(str(text or "").split())


def load_gitignore(root: Path) -> tuple[str, ...]:
    """Read simple path/glob patterns from ``.gitignore``."""
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return ()
    patterns: list[str] = []
    for line in gitignore.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("!"):
            patterns.append(stripped.rstrip("/"))
    return tuple(patterns)


def is_binary_path(path: Path) -> bool:
    """Return true when a file has an early NUL byte."""
    try:
        return b"\0" in path.read_bytes()[:2048]
    except OSError:
        return False


def _matches_any(rel: str, patterns: tuple[str, ...]) -> bool:
    return any(
        fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(Path(rel).name, pattern)
        for pattern in patterns
    )


def ensure_contained(path: Path, root: Path) -> bool:
    """Return true when ``path`` resolves inside ``root``."""
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def should_index_path(
    path: Path,
    root: Path,
    policy: ScopePolicy,
    *,
    gitignore_patterns: tuple[str, ...] = (),
) -> tuple[bool, ParserDiagnostic | None]:
    """Apply scope policy to one candidate path."""
    rel = normalize_relative_path(path.relative_to(root))
    if any(part in policy.ignore_names for part in Path(rel).parts):
        return False, ParserDiagnostic(
            "ignored_name", "path contains ignored name", rel
        )
    if not ensure_contained(path, root):
        return False, ParserDiagnostic(
            "outside_root", "path escaped indexing root", rel
        )
    if path.is_symlink() and not policy.follow_symlinks:
        return False, ParserDiagnostic(
            "symlink_skipped", "symlink indexing is disabled", rel
        )
    if policy.include_globs and not _matches_any(rel, policy.include_globs):
        return False, ParserDiagnostic(
            "not_included", "path did not match include globs", rel
        )
    if policy.exclude_globs and _matches_any(rel, policy.exclude_globs):
        return False, ParserDiagnostic("excluded", "path matched exclude globs", rel)
    if (
        policy.respect_gitignore
        and gitignore_patterns
        and _matches_any(rel, gitignore_patterns)
    ):
        return False, ParserDiagnostic("gitignored", "path matched .gitignore", rel)
    if path.is_file():
        size = path.stat().st_size
        if size > policy.max_file_bytes:
            return False, ParserDiagnostic(
                "max_file_size",
                "file exceeds maximum configured size",
                rel,
                details={"size": size, "max_file_bytes": policy.max_file_bytes},
            )
        if path.suffix.lower() not in TEXT_SUFFIXES and is_binary_path(path):
            return False, ParserDiagnostic("binary_file", "binary file omitted", rel)
    return True, None


__all__ = [
    "DEFAULT_IGNORES",
    "DEFAULT_MAX_FILE_BYTES",
    "ScopePolicy",
    "TEXT_SUFFIXES",
    "ensure_contained",
    "escape_label",
    "is_binary_path",
    "load_gitignore",
    "should_index_path",
]
