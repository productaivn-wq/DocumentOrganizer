"""Portable pytest bootstrap ensuring DocumentOrganizer imports work from any directory name."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for sub in ("", "core", "scripts", "src"):
    p = str(ROOT / sub) if sub else str(ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)

if "DocumentOrganizer" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "DocumentOrganizer",
        ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)],
    )
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules["DocumentOrganizer"] = mod
        spec.loader.exec_module(mod)
    else:
        pkg = types.ModuleType("DocumentOrganizer")
        pkg.__path__ = [str(ROOT)]
        sys.modules["DocumentOrganizer"] = pkg
