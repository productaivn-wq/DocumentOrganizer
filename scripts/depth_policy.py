"""
depth_policy.py — 3-layer MECE directory depth governance for DocumentOrganizer.

Enforces workspace hierarchy nesting invariants:
Layer 1: Zone folder (00_INBOX, 10_ACTIVE_TIMEBOUND, 20_ACTIVE_CONTINUOUS, 30_REFERENCE, 40_ARCHIVE)
Layer 2: Document (root -> zone -> document)
Documents nested at depth > 2 are violations unless declared in opaque_exceptions.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

VALID_ZONES: set[str] = {
    "00_INBOX",
    "10_ACTIVE_TIMEBOUND",
    "20_ACTIVE_CONTINUOUS",
    "30_REFERENCE",
    "40_ARCHIVE",
}


@dataclass
class DepthPolicy:
    """Configuration for directory depth policy."""

    max_depth: int = 3
    allowed_levels: list[str] = field(
        default_factory=lambda: ["root", "section", "subsection"]
    )


DEFAULT_POLICY = DepthPolicy(
    max_depth=3, allowed_levels=["root", "section", "subsection"]
)

# Alias for backward compatibility with adversarial test suite
DepthPolicyValidator = DepthPolicy


class PathValidationError(ValueError):
    """Raised when a path pattern fails validation."""


class ManifestLoadError(ValueError):
    """Raised when exception manifest cannot be loaded or parsed."""


def _validate_path_pattern(raw_pattern: str) -> list[str]:
    """Validate and normalize a path pattern, returning its parts.

    Args:
        raw_pattern: Path pattern string to validate.

    Returns:
        List of path parts.

    Raises:
        PathValidationError: If pattern contains path traversal or invalid zone.
    """
    raw_pattern = raw_pattern.strip().replace("\\", "/")
    parts = [p for p in raw_pattern.split("/") if p and p != "."]

    if not parts or parts[0] == ".." or ".." in parts:
        raise PathValidationError(
            f"Exception pattern cannot traverse outside lifecycle zones: {raw_pattern}"
        )

    zone = parts[0]
    if zone not in VALID_ZONES:
        raise PathValidationError(
            f"Exception must be inside a lifecycle zone: {raw_pattern} "
            f"(zone '{zone}' is not in {VALID_ZONES})"
        )

    return parts


def normalize_exception(
    arg1: Path | str,
    arg2: Path | str | None = None,
) -> Path:
    """
    Normalizes and validates an opaque exception path pattern.
    Supports normalize_exception(root, pattern) or normalize_exception(pattern).
    Must reside strictly inside one of the VALID_ZONES.

    Args:
        arg1: First argument (either root path or pattern string).
        arg2: Optional second argument (pattern string if first is root).

    Returns:
        Normalized Path object.

    Raises:
        PathValidationError: If pattern is invalid.
    """
    if arg2 is not None:
        raw_pattern = str(arg2)
    else:
        raw_pattern = str(arg1)

    parts = _validate_path_pattern(raw_pattern)
    return Path(*parts)


class ExceptionManifestList(list):
    """List subclass providing dict-like access for backwards compatibility."""

    def __init__(
        self, items: Iterable[Path], raw_data: dict[str, Any] | None = None
    ) -> None:
        super().__init__(items)
        self.raw_data = raw_data or {"opaque_exceptions": [str(x) for x in items]}

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw_data.get(key, default)

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, str):
            return self.raw_data[key]
        return super().__getitem__(key)


def _parse_exception_arg(
    arg1: Path | str | None, arg2: Path | str | None
) -> tuple[Path | None, Path]:
    """Parse exception manifest arguments into (root, manifest_path)."""
    if arg2 is not None:
        root = Path(arg1) if arg1 else None
        manifest_path = Path(arg2)
    elif arg1 is not None:
        p = Path(arg1)
        if p.is_file() or str(p).endswith(".json"):
            manifest_path = p
            root = p.parent
        else:
            root = p
            manifest_path = root / "exceptions.json"
    else:
        root = Path.cwd()
        manifest_path = root / "exceptions.json"

    return root, manifest_path


def load_exception_manifest(
    arg1: Path | str | None = None,
    arg2: Path | str | None = None,
) -> ExceptionManifestList:
    """
    Loads and normalizes opaque depth exceptions from a manifest file.
    Supports load_exception_manifest(root, manifest_path) or load_exception_manifest(manifest_path).

    Args:
        arg1: First argument (either root path or manifest path).
        arg2: Optional second argument (manifest path if first is root).

    Returns:
        ExceptionManifestList containing normalized exception paths.

    Raises:
        ManifestLoadError: If manifest cannot be read or parsed.
    """
    root, manifest_path = _parse_exception_arg(arg1, arg2)

    if not manifest_path.exists():
        return ExceptionManifestList([], {"opaque_exceptions": []})

    try:
        content = manifest_path.read_text(encoding="utf-8")
        data = json.loads(content)
    except (OSError, json.JSONDecodeError) as e:
        raise ManifestLoadError(
            f"Failed to read or parse manifest {manifest_path}: {e}"
        ) from e

    if (
        not isinstance(data, dict)
        or "opaque_exceptions" not in data
        or not isinstance(data["opaque_exceptions"], list)
    ):
        raise ManifestLoadError("Manifest requires explicit opaque_exceptions array")

    exceptions: list[Path] = []
    for item in data["opaque_exceptions"]:
        try:
            norm = (
                normalize_exception(root, item) if root else normalize_exception(item)
            )
            exceptions.append(norm)
        except PathValidationError:
            continue

    return ExceptionManifestList(exceptions, data)


def _normalize_exceptions(
    exceptions: list[Any] | dict[str, Any] | set[Any], root: Path | None
) -> list[tuple[str, ...]]:
    """Normalize exception patterns into tuple form for matching.

    Args:
        exceptions: Exception patterns in various formats.
        root: Optional root path for resolution.

    Returns:
        List of normalized path part tuples.
    """
    normalized: list[tuple[str, ...]] = []
    raw_list: list[Any] = []

    if isinstance(exceptions, dict):
        raw_list = exceptions.get("opaque_exceptions", list(exceptions.values()))
    elif isinstance(exceptions, (list, tuple, set)):
        raw_list = list(exceptions)
    else:
        raw_list = [exceptions]

    for exc in raw_list:
        exc_str = str(exc).strip().replace("\\", "/")
        exc_parts = tuple(p for p in exc_str.split("/") if p and p != ".")
        if exc_parts:
            normalized.append(exc_parts)

    return normalized


def _is_exempted(
    rel_parts: tuple[str, ...], normalized_exceptions: list[tuple[str, ...]]
) -> bool:
    """Check if a path is exempted by any exception pattern.

    Args:
        rel_parts: Path parts to check.
        normalized_exceptions: List of exception pattern tuples.

    Returns:
        True if path matches any exception pattern.
    """
    for exc_parts in normalized_exceptions:
        if (
            len(rel_parts) >= len(exc_parts)
            and rel_parts[: len(exc_parts)] == exc_parts
        ):
            return True
    return False


def audit(
    root: Path | str,
    exceptions: list[Any] | dict[str, Any] | set[Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Audits directory hierarchy against the 3-layer MECE rule (root -> zone -> document).
    Layer 1: Zone folder
    Layer 2: Document directly inside Zone
    Documents at depth > 2 are reported as violations unless covered by an opaque exception.

    Args:
        root: Root directory path to audit.
        exceptions: Exception patterns (list, dict, or set). If None, loads from exceptions.json.

    Returns:
        List of violation dictionaries with 'path' and 'depth' keys.
    """
    root_path = Path(root).resolve()
    if not root_path.exists() or not root_path.is_dir():
        return []

    normalized_exceptions: list[tuple[str, ...]] = []
    if exceptions is not None:
        normalized_exceptions = _normalize_exceptions(exceptions, root_path)
    else:
        manifest_file = root_path / "exceptions.json"
        if manifest_file.is_file():
            try:
                loaded = load_exception_manifest(root_path, manifest_file)
                for exc in loaded:
                    exc_parts = tuple(
                        p
                        for p in str(exc).replace("\\", "/").split("/")
                        if p and p != "."
                    )
                    if exc_parts:
                        normalized_exceptions.append(exc_parts)
            except (ManifestLoadError, PathValidationError):
                pass

    violations: list[dict[str, Any]] = []
    for p in root_path.rglob("*"):
        if not p.is_file():
            continue

        try:
            rel = p.relative_to(root_path)
        except ValueError:
            continue

        rel_parts = rel.parts
        if any(part.startswith(".") or part == "__pycache__" for part in rel_parts):
            continue

        depth = len(rel_parts)
        if depth > 2:
            if not _is_exempted(rel_parts, normalized_exceptions):
                violations.append(
                    {
                        "path": str(Path(*rel_parts)),
                        "depth": depth,
                    }
                )

    violations.sort(key=lambda item: (item["depth"], item["path"]))
    return violations
