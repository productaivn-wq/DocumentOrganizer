"""Unified CLI entrypoint for `python -m DocumentOrganizer`."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

__version__ = "3.3.1"

SUBCOMMANDS = {
    "organize": "organizer.py",
    "sweep": "sweep.py",
    "hygiene": "hygiene.py",
    "vault": "vault_manager.py",
    "watch": "watch.py",
    "reorganize": "nightly_project_reorganizer.py",
}


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] in {"-h", "--help"}:
        if "--json" in argv:
            print(
                json.dumps(
                    {
                        "name": "DocumentOrganizer",
                        "version": __version__,
                        "subcommands": sorted(SUBCOMMANDS.keys()),
                    },
                    indent=2,
                )
            )
            return 0
        print(f"DocumentOrganizer v{__version__}")
        print("Usage: python -m DocumentOrganizer <subcommand> [options]")
        print("Subcommands:", ", ".join(sorted(SUBCOMMANDS.keys())))
        return 0

    if argv[0] in {"-V", "--version"}:
        if "--json" in argv:
            print(json.dumps({"name": "DocumentOrganizer", "version": __version__}))
        else:
            print(f"DocumentOrganizer {__version__}")
        return 0

    cmd = argv[0]
    if cmd not in SUBCOMMANDS:
        err = {"error": f"Unknown subcommand: {cmd}", "available": sorted(SUBCOMMANDS)}
        if "--json" in argv:
            print(json.dumps(err))
        else:
            print(f"Error: {err['error']}. Choose from: {', '.join(err['available'])}", file=sys.stderr)
        return 2

    script_path = Path(__file__).resolve().parent / "scripts" / SUBCOMMANDS[cmd]
    scripts_dir = str(script_path.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    sys.argv = [str(script_path), *argv[1:]]
    runpy.run_path(str(script_path), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
