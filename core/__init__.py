"""DocumentOrganizer Core Package.

Provides deterministic 5-zone MECE document sorting, Git artifact adaptation,
traceability resolution, headless subprocess isolation, and
token budget governance.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from typing import Any

__version__ = "3.3.0"

# Output Budget Governance Constants
MAX_INLINE_OUTPUT_CHARS: int = 12_000
DEFAULT_SUBPROCESS_TIMEOUT_SECONDS: int = 30


def get_headless_creation_flags() -> int:
    """Return platform-appropriate headless creation flags."""
    if sys.platform == "win32":
        return int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000))
    return 0


def enforce_token_budget(text: str, max_chars: int = MAX_INLINE_OUTPUT_CHARS) -> str:
    """Truncate output text cleanly to comply with token budget caps."""
    if not text or len(text) <= max_chars:
        return text
    head_budget = int(max_chars * 0.75)
    tail_budget = max_chars - head_budget - 64
    if tail_budget <= 0:
        return text[:max_chars]
    omitted = len(text) - (head_budget + tail_budget)
    return (
        f"{text[:head_budget]}\n"
        f"... [TRUNCATED {omitted} CHARS TO FIT OUTPUT BUDGET] ...\n"
        f"{text[-tail_budget:]}"
    )


_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "GitRunError": (".git_artifact_adapter", "GitRunError"),
    "get_domain_adapter_contract": (
        ".git_artifact_adapter",
        "get_domain_adapter_contract",
    ),
    "is_git_available": (".git_artifact_adapter", "is_git_available"),
    "is_git_repository": (".git_artifact_adapter", "is_git_repository"),
    "init_git_repository": (".git_artifact_adapter", "init_git_repository"),
}

__all__ = [
    "__version__",
    "MAX_INLINE_OUTPUT_CHARS",
    "DEFAULT_SUBPROCESS_TIMEOUT_SECONDS",
    "get_headless_creation_flags",
    "enforce_token_budget",
    *list(_LAZY_EXPORTS.keys()),
]


def __getattr__(name: str) -> Any:
    """Lazily import core submodule attributes on demand."""
    if name in _LAZY_EXPORTS:
        module_name, attr_name = _LAZY_EXPORTS[name]
        module = importlib.import_module(module_name, package=__name__)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
