"""Fingerprint and persistence helpers for the extraction cache."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

from pragmagraph.adapters.git_history import validate_git_identity_mode
from pragmagraph.contracts import INDEXER_VERSION, SCHEMA_VERSION
from pragmagraph.incremental.models import CacheFingerprint, ExtractionCacheBundle
from pragmagraph.models import PragmaGraphError, RefreshManifest
from pragmagraph.parsers import ParserRegistry
from pragmagraph.security import ScopePolicy


def _stable_hash(payload: object) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_cache_fingerprint(
    root_path: str | Path,
    *,
    namespace: str,
    policy: ScopePolicy,
    parser_registry: ParserRegistry,
    manifest: RefreshManifest,
    git_identity_mode: str,
) -> CacheFingerprint:
    """Build a complete local compatibility fingerprint for cached facts."""
    root = Path(root_path).resolve()
    ignore_path = root / ".gitignore"
    ignore_hash = (
        hashlib.sha256(ignore_path.read_bytes()).hexdigest()
        if ignore_path.is_file()
        else ""
    )
    policy_hash = _stable_hash(
        {
            "ignore_names": sorted(policy.ignore_names),
            "include_globs": list(policy.include_globs),
            "exclude_globs": list(policy.exclude_globs),
            "max_file_bytes": policy.max_file_bytes,
            "follow_symlinks": policy.follow_symlinks,
            "respect_gitignore": policy.respect_gitignore,
        }
    )
    parser_signature = _stable_hash(
        [
            {
                "name": parser.name,
                "version": parser.version,
                "suffixes": sorted(parser.suffixes),
            }
            for parser in parser_registry.parsers
        ]
    )
    repository, head, shallow = _git_facts(root)
    return CacheFingerprint(
        snapshot_schema=SCHEMA_VERSION,
        indexer_version=INDEXER_VERSION,
        namespace=namespace,
        root_identity=hashlib.sha256(str(root).encode("utf-8")).hexdigest(),
        policy_hash=policy_hash,
        ignore_hash=ignore_hash,
        parser_signature=parser_signature,
        git_identity_mode=validate_git_identity_mode(git_identity_mode),
        git_repository=repository,
        git_head=head,
        git_shallow=shallow,
        file_set_hash=_stable_hash(sorted(manifest.by_path())),
    )


def load_extraction_cache(path: str | Path) -> ExtractionCacheBundle:
    """Load one typed cache bundle with normalized errors."""
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PragmaGraphError(
            "extraction cache could not be read",
            code="INVALID_EXTRACTION_CACHE",
            details={"path": str(source), "message": str(exc)},
        ) from exc
    if not isinstance(payload, dict):
        raise PragmaGraphError(
            "extraction cache JSON root must be an object",
            code="INVALID_EXTRACTION_CACHE",
            details={"path": str(source)},
        )
    return ExtractionCacheBundle.from_dict(payload)


def save_extraction_cache(bundle: ExtractionCacheBundle, path: str | Path) -> Path:
    """Atomically save one deterministic cache bundle."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(bundle.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)
    return target


def _git_facts(root: Path) -> tuple[str, str, bool]:
    repository = _git_output(root, "rev-parse", "--show-toplevel")
    if not repository:
        return "", "", False
    head = _git_output(root, "rev-parse", "HEAD")
    shallow_text = _git_output(root, "rev-parse", "--is-shallow-repository")
    repository_id = hashlib.sha256(repository.encode("utf-8")).hexdigest()
    return repository_id, head, shallow_text == "true"


def _git_output(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


__all__ = [
    "build_cache_fingerprint",
    "load_extraction_cache",
    "save_extraction_cache",
]
