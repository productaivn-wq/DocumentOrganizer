#!/usr/bin/env python3
"""validate_tasks.py — Schema validator for Phase 3 planner output (tasks.json).

Usage:
    python validate_tasks.py --tasks <path>

Exit 0 if valid, 1 with error summary if invalid. Stdlib only.
"""

import argparse
import json
import re
import sys
from pathlib import Path

HASH_RE = re.compile(r"^[0-9a-fA-F]{32}$")
REQUIRED_TOP = ("job_dir", "target", "zones")
ZONE_REQUIRED = ("id", "name", "path", "moves")


def _is_abs(p: str) -> bool:
    try:
        return Path(p).is_absolute()
    except Exception:
        return False


def _validate_top_level_optional(data: dict, errors: list[str]) -> None:
    if "mode" in data:
        mode = data.get("mode")
        if mode not in ("quick", "thorough"):
            errors.append(f"'mode' must be 'quick' or 'thorough': {mode!r}")

    if "traceability" in data:
        trace = data.get("traceability")
        if not isinstance(trace, bool):
            errors.append(f"'traceability' must be boolean: {trace!r}")


def _validate_top_level(data: dict, errors: list[str]) -> None:
    for key in REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing required top-level key: '{key}'")

    _validate_top_level_optional(data, errors)

    target = data.get("target")
    if target is not None:
        if not isinstance(target, str) or not _is_abs(target):
            errors.append(f"'target' must be an absolute path string: {target!r}")
        elif not Path(target).exists():
            errors.append(f"'target' path does not exist on disk: {target}")


def _validate_zone_moves(
    moves: list,
    loc: str,
    zid: str,
    idx: int,
    zone_srcs: dict[str, str],
    errors: list[str],
) -> None:
    for midx, mv in enumerate(moves):
        mloc = f"{loc}.moves[{midx}]"
        if not isinstance(mv, dict):
            errors.append(f"{mloc}: must be an object")
            continue
        src = mv.get("src")
        dest = mv.get("dest")
        if not isinstance(src, str) or not _is_abs(src):
            errors.append(f"{mloc}.src: must be an absolute path string: {src!r}")
        else:
            if not Path(src).exists():
                errors.append(f"{mloc}.src: file does not exist on disk: {src}")
            zone_srcs[str(Path(src))] = zid or f"zones[{idx}]"
        if not isinstance(dest, str) or not _is_abs(dest):
            errors.append(f"{mloc}.dest: must be an absolute path string: {dest!r}")


def _validate_zone_keys(
    zone: dict, loc: str, seen_ids: set[str], errors: list[str]
) -> str | None:
    for k in ZONE_REQUIRED:
        if k not in zone:
            errors.append(f"{loc}: missing required key '{k}'")

    zid = zone.get("id")
    if zid is not None:
        if not isinstance(zid, str) or not zid:
            errors.append(f"{loc}.id: must be a non-empty string")
        elif zid in seen_ids:
            errors.append(f"{loc}.id: duplicate zone id '{zid}'")
        else:
            seen_ids.add(zid)
    return zid


def _validate_zones(zones: list, zone_srcs: dict[str, str], errors: list[str]) -> None:
    seen_ids: set[str] = set()
    for idx, zone in enumerate(zones):
        loc = f"zones[{idx}]"
        if not isinstance(zone, dict):
            errors.append(f"{loc}: must be an object")
            continue

        zid = _validate_zone_keys(zone, loc, seen_ids, errors)

        moves = zone.get("moves")
        if moves is None:
            continue
        if not isinstance(moves, list):
            errors.append(f"{loc}.moves: must be an array")
            continue

        _validate_zone_moves(moves, loc, zid, idx, zone_srcs, errors)


def _validate_dedup_entry_dups(
    dups: list, loc: str, keeper: str, dedup_srcs: dict[str, str], errors: list[str]
) -> None:
    for didx, d in enumerate(dups):
        dloc = f"{loc}.duplicates[{didx}]"
        if not isinstance(d, str) or not _is_abs(d):
            errors.append(f"{dloc}: must be an absolute path string: {d!r}")
            continue
        if not Path(d).exists():
            errors.append(f"{dloc}: file does not exist on disk: {d}")
        dedup_srcs[str(Path(d))] = (
            str(keeper) if isinstance(keeper, str) else "<invalid>"
        )


def _validate_dedup_entry(
    entry: dict, loc: str, dedup_srcs: dict[str, str], errors: list[str]
) -> None:
    keeper = entry.get("keeper")
    dups = entry.get("duplicates")
    h = entry.get("hash")

    if not isinstance(keeper, str) or not _is_abs(keeper):
        errors.append(f"{loc}.keeper: must be an absolute path string: {keeper!r}")
    elif not Path(keeper).exists():
        errors.append(f"{loc}.keeper: file does not exist on disk: {keeper}")

    if not isinstance(h, str) or not HASH_RE.match(h or ""):
        errors.append(f"{loc}.hash: must be a 32-char hex string: {h!r}")

    if not isinstance(dups, list):
        errors.append(f"{loc}.duplicates: must be an array")
    else:
        _validate_dedup_entry_dups(dups, loc, keeper, dedup_srcs, errors)


def _validate_dedup(dedup: list, dedup_srcs: dict[str, str], errors: list[str]) -> None:
    for idx, entry in enumerate(dedup):
        loc = f"dedup[{idx}]"
        if not isinstance(entry, dict):
            errors.append(f"{loc}: must be an object")
            continue
        _validate_dedup_entry(entry, loc, dedup_srcs, errors)


def validate(tasks_path: Path) -> list[str]:
    errors: list[str] = []

    if not tasks_path.exists():
        return [f"tasks.json not found: {tasks_path}"]

    try:
        data = json.loads(tasks_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"]

    if not isinstance(data, dict):
        return ["top-level must be an object"]

    _validate_top_level(data, errors)

    zone_srcs: dict[str, str] = {}
    dedup_srcs: dict[str, str] = {}

    zones = data.get("zones")
    if zones is not None:
        if not isinstance(zones, list):
            errors.append("'zones' must be an array")
        else:
            _validate_zones(zones, zone_srcs, errors)

    dedup = data.get("dedup")
    if dedup is not None:
        if not isinstance(dedup, list):
            errors.append("'dedup' must be an array")
        else:
            _validate_dedup(dedup, dedup_srcs, errors)

    for dup_path, keeper in dedup_srcs.items():
        if dup_path in zone_srcs:
            errors.append(
                f"conflict: path listed as both dedup duplicate and zone move src: {dup_path} "
                f"(zone={zone_srcs[dup_path]}, keeper={keeper})"
            )

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate DocumentOrganizer tasks.json")
    ap.add_argument("--tasks", required=True, help="Path to tasks.json")
    args = ap.parse_args()

    tasks_path = Path(args.tasks).resolve()
    errors = validate(tasks_path)

    print("=" * 60)
    print(f"  validate_tasks.py  —  {tasks_path}")
    print("=" * 60)

    if not errors:
        print("OK: tasks.json passed all validation checks.")
        return 0

    print(f"FAILED: {len(errors)} error(s) found:")
    print("-" * 60)
    for i, err in enumerate(errors, 1):
        print(f"  [{i:02d}] {err}")
    print("-" * 60)
    print(f"Summary: {len(errors)} validation error(s). Fix the plan and retry.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
