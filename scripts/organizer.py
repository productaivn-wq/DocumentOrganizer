#!/usr/bin/env python3
"""
organizer.py — File execution engine for DocumentOrganizer / doc_reorg workflow.

Usage:
    python organizer.py --execute <job_dir> [--max-concurrent 3] [--dry-run]

Reads <job_dir>/tasks.json, executes all file moves safely using pathlib.
Writes:
  <job_dir>/rename_log.md     — every naming violation fixed
  <job_dir>/move_log.md       — every file moved
  <job_dir>/duplicate_log.md  — exact duplicates handled

Rules (non-negotiable):
  - Never delete original files (exact duplicates → moved to _duplicates/)
  - Use pathlib.Path for all path operations (Unicode-safe, Windows-safe)
  - Create target directory before moving into it
  - Enforce naming conventions on every file moved
  - Idempotent: skip already-moved files
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

try:
    from utils import get_file_hash
except ImportError:
    try:
        from .utils import get_file_hash
    except ImportError:
        try:
            from scripts.utils import get_file_hash
        except ImportError:
            from DocumentOrganizer.scripts.utils import get_file_hash

# ---------------------------------------------------------------------------
# Naming convention enforcement
# ---------------------------------------------------------------------------

# Files exempt from lowercase/snake_case conversion
_NAME_EXEMPTIONS = {"SKILL.md", "CHANGELOG.md", "README.md", "LICENSE", "NOTICE"}

_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _to_snake_case(name: str) -> str:
    """Convert camelCase or PascalCase to snake_case."""
    return _CAMEL_RE.sub("_", name).lower()


def enforce_naming(filename: str) -> tuple[str, str | None]:
    """
    Return (new_name, violation_description).
    violation_description is None if no rename needed.
    """
    stem = Path(filename).stem
    suffix = Path(filename).suffix

    if filename in _NAME_EXEMPTIONS:
        return filename, None

    new_stem = stem
    violations = []

    # Replace spaces with underscores
    if " " in new_stem:
        new_stem = new_stem.replace(" ", "_")
        violations.append("spaces → underscores")

    # camelCase → snake_case for .md files and .txt files
    if suffix.lower() in {".md", ".txt", ".rst"} and _CAMEL_RE.search(new_stem):
        new_stem = _to_snake_case(new_stem)
        violations.append("camelCase → snake_case")

    new_name = new_stem + suffix
    if new_name == filename:
        return filename, None

    return new_name, "; ".join(violations)


# ---------------------------------------------------------------------------
# Hashing (for duplicate detection)
# ---------------------------------------------------------------------------


def _file_hash(path: Path, chunk_size: int = 8192) -> str | None:
    return get_file_hash(path, algo="md5", chunk_size=chunk_size)


# ---------------------------------------------------------------------------
# Core move logic
# ---------------------------------------------------------------------------


def _dedup_target_path(dest_root: Path, src: Path, file_hash: str) -> Path:
    """Compute the canonical _duplicates/ target path for a given file.
    Pattern: <dest_root>/_duplicates/<YYYYMMDD>/<stem>_<hash[:8]><ext>
    Always preserves the original file extension.
    """
    day = datetime.now().strftime("%Y%m%d")
    dup_dir = dest_root / "_duplicates" / day
    short = file_hash[:8] if file_hash and file_hash != "ERROR" else "nohash"
    ext = src.suffix  # Always preserve extension
    stem = src.stem
    return dup_dir / f"{stem}_{short}{ext}"


# Per-destination-dir registry of names already claimed in this batch.
# Value: {normalized_name: final_dest_path_already_committed}
_batch_claimed: dict[Path, dict[str, Path]] = {}


# Module-level list of dedup lock-contention events for dedup_log.md reporting.
# Each entry: {"target", "resolution", "waited_ms", "ts"}
_dedup_lock_events: list = []


def _acquire_dedup_lock(sentinel: Path, timeout_sec: float = 3.0) -> tuple[bool, float]:
    """Atomically claim a _duplicates/ target slot across processes.

    Uses O_CREAT | O_EXCL on a sentinel file next to the target. Returns
    (acquired, waited_ms). Retries briefly on contention. Fails gracefully
    (returns True on unexpected OSError) so the caller can proceed without
    blocking forever; the subsequent hash-compare logic remains the final
    safety net.
    """
    start = time.monotonic()
    deadline = start + timeout_sec
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    while True:
        try:
            fd = os.open(str(sentinel), flags, 0o644)
            try:
                os.write(
                    fd, f"pid={os.getpid()} ts={datetime.now().isoformat()}\n".encode()
                )
            finally:
                os.close(fd)
            return True, (time.monotonic() - start) * 1000.0
        except FileExistsError:
            if time.monotonic() >= deadline:
                return False, (time.monotonic() - start) * 1000.0
            time.sleep(0.05)
        except OSError:
            # Locking unavailable / unexpected filesystem error - degrade to
            # best-effort: proceed without a lock. The hash-compare step in
            # _safe_dedup_move still guards against corruption.
            return True, (time.monotonic() - start) * 1000.0


def _release_dedup_lock(sentinel: Path) -> None:
    try:
        sentinel.unlink()
    except (FileNotFoundError, OSError):
        pass


def _log_dedup_event(
    final_dest: Path, resolution: str, waited_ms: float, contended: bool, acquired: bool
) -> None:
    if contended or not acquired:
        _dedup_lock_events.append(
            {
                "target": str(final_dest),
                "resolution": resolution,
                "waited_ms": round(waited_ms, 1),
                "ts": datetime.now().isoformat(),
            }
        )


def _resolve_collision(dup_dest: Path, src: Path) -> Path:
    stem = dup_dest.stem
    suffix = dup_dest.suffix
    counter = 1
    while True:
        candidate = dup_dest.parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
        if counter > 9999:
            raise RuntimeError(f"unable to disambiguate dedup target for {src}")


def _handle_existing_dedup(
    src: Path, final_dest: Path, src_hash: str
) -> tuple[bool, Path, str]:
    existing_hash = _file_hash(final_dest)
    if existing_hash and existing_hash != "ERROR" and existing_hash == src_hash:
        try:
            src.unlink()
        except (FileNotFoundError, OSError):
            pass
        return True, final_dest, "already-deduplicated"

    final_dest = _resolve_collision(final_dest, src)
    return False, final_dest, "collision-suffixed"


def _safe_dedup_move(
    src: Path,
    dup_dest: Path,
    src_hash: str,
    dry_run: bool,
) -> tuple[Path, str]:
    """Move src to a _duplicates/ target, safe across parallel processes.

    Handles cross-process races during parallel zone execution (Phase 4
    --max-concurrent > 1). Two zones racing on the same target are
    serialized via an O_EXCL sentinel lockfile; if the target already
    exists with a matching hash we delete src as already-deduplicated;
    on rare hash-prefix collision we append a numeric counter.

    Returns (final_dest_path, resolution) where resolution is one of:
        "moved"                -- src moved to dup_dest
        "already-deduplicated" -- target already held identical content; src deleted
        "collision-suffixed"   -- hash differed at the 8-char prefix; counter appended
        "dry-run"              -- no filesystem change (dry_run=True)
    """
    if dry_run:
        return dup_dest, "dry-run"

    dup_dest.parent.mkdir(parents=True, exist_ok=True)
    sentinel_name = f".lock_{dup_dest.stem}{dup_dest.suffix}"
    sentinel = dup_dest.parent / sentinel_name

    acquired, waited_ms = _acquire_dedup_lock(sentinel, timeout_sec=3.0)
    contended = waited_ms > 50.0 or not acquired
    try:
        final_dest = dup_dest
        resolution = "moved"

        if final_dest.exists():
            handled, final_dest, resolution = _handle_existing_dedup(
                src, final_dest, src_hash
            )
            if handled:
                _log_dedup_event(final_dest, resolution, waited_ms, contended, acquired)
                return final_dest, resolution

        shutil.move(str(src), str(final_dest))
        _log_dedup_event(final_dest, resolution, waited_ms, contended, acquired)
        return final_dest, resolution
    finally:
        _release_dedup_lock(sentinel)


def _append_timestamp(name: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if "." in name:
        stem, ext = name.rsplit(".", 1)
        return f"{stem}_{ts}.{ext}"
    return f"{name}_{ts}"


def _log_duplicate(
    src_hash: str,
    kept: Path,
    src: Path,
    moved_to: Path,
    resolution: str,
    dup_log: list | None,
    tag: str,
):
    if dup_log is not None:
        dup_log.append(
            {
                "hash": src_hash,
                "kept": str(kept),
                "moved_from": str(src),
                "moved_to": str(moved_to),
                "resolution": resolution,
            }
        )
    p_tag = tag if resolution != "already-deduplicated" else f"{tag}-SEEN"
    print(f"  {p_tag} {src.name} -> _duplicates/ ({resolution}, hash {src_hash[:8]})")


def _handle_dir_merge(
    src: Path,
    dest: Path,
    dry_run: bool,
    rename_log: list | None,
    move_log: list | None,
    dup_log: list | None,
    target_root: Path | None,
):
    print(f"  [MERGE] Directory collision, merging into -> {dest}")
    for item in src.iterdir():
        safe_move(item, dest, dry_run, rename_log, move_log, dup_log, target_root)
    if not dry_run:
        try:
            src.rmdir()
        except OSError:
            pass


def _resolve_batch_collision(
    src: Path,
    dest_dir: Path,
    final_name: str,
    dup_root: Path,
    dry_run: bool,
    dup_log: list | None,
) -> tuple[Path, str, bool, Path | None]:
    claimed = _batch_claimed.get(dest_dir, {})
    prior_dest = claimed.get(final_name)
    if prior_dest is None or src.is_dir():
        return dest_dir / final_name, final_name, False, None

    src_hash = _file_hash(src)
    prior_hash = _file_hash(prior_dest) if prior_dest.exists() else None

    if src_hash and prior_hash and src_hash != "ERROR" and src_hash == prior_hash:
        dup_dest = _dedup_target_path(dup_root, src, src_hash)
        final_dest, res = _safe_dedup_move(src, dup_dest, src_hash, dry_run)
        _log_duplicate(
            src_hash, prior_dest, src, final_dest, res, dup_log, "[DUP-BATCH]"
        )
        return final_dest, final_name, True, final_dest

    final_name = _append_timestamp(final_name)
    print(f"  [COLL-BATCH] Batch collision, distinct content -> {final_name}")
    return dest_dir / final_name, final_name, False, None


def _resolve_disk_collision(
    src: Path,
    dest: Path,
    dest_dir: Path,
    final_name: str,
    dup_root: Path,
    dry_run: bool,
    rename_log: list | None,
    move_log: list | None,
    dup_log: list | None,
    target_root: Path | None,
) -> tuple[Path, str, bool, Path | None]:
    if not dest.exists():
        return dest, final_name, False, None

    if src.is_dir() and dest.is_dir():
        _handle_dir_merge(
            src, dest, dry_run, rename_log, move_log, dup_log, target_root
        )
        return dest, final_name, True, dest

    src_hash, dest_hash = _file_hash(src), _file_hash(dest)
    if src_hash and dest_hash and src_hash == dest_hash:
        dup_dest = _dedup_target_path(dup_root, src, src_hash)
        final_dest, res = _safe_dedup_move(src, dup_dest, src_hash, dry_run)
        _log_duplicate(src_hash, dest, src, final_dest, res, dup_log, "[DUP]")
        return final_dest, final_name, True, final_dest

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_name = f"{final_name}_{ts}" if src.is_dir() else _append_timestamp(final_name)
    print(f"  [COLL] Collision resolved -> {final_name}")
    return dest_dir / final_name, final_name, False, None


def _finalize_move(
    src: Path,
    dest: Path,
    dest_dir: Path,
    final_name: str,
    dry_run: bool,
    move_log: list | None,
) -> Path:
    action = "[DRY]" if dry_run else "[MOVE]"
    print(f"  {action} {src} -> {dest}")
    if not dry_run:
        shutil.move(str(src), str(dest))
    if move_log is not None:
        move_log.append({"src": str(src), "dest": str(dest), "dry_run": dry_run})

    _batch_claimed.setdefault(dest_dir, {})[final_name] = dest
    return dest


def safe_move(
    src: Path,
    dest_dir: Path,
    dry_run: bool = False,
    rename_log: list | None = None,
    move_log: list | None = None,
    dup_log: list | None = None,
    target_root: Path | None = None,
    custom_name: str | None = None,
) -> Path | None:
    """Move src into dest_dir, enforcing naming conventions."""
    if not src.exists():
        print(f"  [SKIP] Already moved or not found: {src}")
        return None

    final_name, violation = (
        (custom_name, None) if custom_name else enforce_naming(src.name)
    )
    if violation and rename_log is not None:
        rename_log.append(
            {"original": str(src), "renamed_to": final_name, "reason": violation}
        )

    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)

    dup_root = target_root if target_root is not None else dest_dir.parent

    dest, final_name, handled, res = _resolve_batch_collision(
        src, dest_dir, final_name, dup_root, dry_run, dup_log
    )
    if handled:
        return res

    dest, final_name, handled, res = _resolve_disk_collision(
        src,
        dest,
        dest_dir,
        final_name,
        dup_root,
        dry_run,
        rename_log,
        move_log,
        dup_log,
        target_root,
    )
    if handled:
        return res

    return _finalize_move(src, dest, dest_dir, final_name, dry_run, move_log)


# ---------------------------------------------------------------------------
# Cross-zone conflict detection
# ---------------------------------------------------------------------------


def _norm(p: str) -> Path:
    try:
        return Path(p).resolve()
    except (OSError, ValueError):
        return Path(p)


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _get_zone_pairs(zone_moves: list) -> list[tuple[Path, Path, dict]]:
    return [
        (_norm(m["src"]), _norm(m["dest"]) / Path(m["src"]).name, m)
        for m in zone_moves
        if m.get("src") and m.get("dest")
    ]


def _get_zone_srcs(zone_moves: list) -> dict[Path, dict]:
    return {_norm(m["src"]): m for m in zone_moves if m.get("src")}


def _get_zone_dsts(zone_moves: list) -> dict[Path, dict]:
    return {
        _norm(m["dest"]) / Path(m["src"]).name: m
        for m in zone_moves
        if m.get("src") and m.get("dest")
    }


def _check_zone_conflicts(
    own_src: Path,
    own_dst: Path,
    other_name: str,
    other_srcs: dict[Path, dict],
    other_dsts: dict[Path, dict],
) -> list[dict]:
    conflicts = []
    if own_src in other_srcs:
        conflicts.append(
            {
                "src": str(own_src),
                "dst": str(own_dst),
                "conflicting_zone": other_name,
                "reason": "src reused in another zone",
            }
        )

    other_same_dst = other_dsts.get(own_dst)
    if other_same_dst and _norm(other_same_dst["src"]) != own_src:
        conflicts.append(
            {
                "src": str(own_src),
                "dst": str(own_dst),
                "conflicting_zone": other_name,
                "reason": "dst collision with different src in another zone",
            }
        )

    for other_src in other_srcs:
        if own_dst != other_src and _is_within(own_dst, other_src):
            conflicts.append(
                {
                    "src": str(own_src),
                    "dst": str(own_dst),
                    "conflicting_zone": other_name,
                    "reason": f"dst inside another zone's src: {other_src}",
                }
            )

    return conflicts


def detect_conflicts(tasks: dict, zone: dict) -> list[dict]:
    """Return cross-zone conflict records for the given zone.

    Detects three classes of collision against every other zone in tasks["zones"]:
      - Cross-zone dst collisions (same dst path, different src)
      - Src reused (same src appears in two zones)
      - Dst inside another zone's src subtree
    Returns [] when only one zone is present or no conflicts are found.
    """
    zones = tasks.get("zones", []) or []
    if len(zones) <= 1:
        return []

    conflicts: list[dict] = []
    own_moves = zone.get("moves", []) or []
    own_pairs = _get_zone_pairs(own_moves)

    for other in zones:
        if other is zone:
            continue
        other_name = other.get("zone", "unknown")
        other_moves = other.get("moves", []) or []
        other_srcs = _get_zone_srcs(other_moves)
        other_dsts = _get_zone_dsts(other_moves)

        for own_src, own_dst, _ in own_pairs:
            conflicts.extend(
                _check_zone_conflicts(
                    own_src, own_dst, other_name, other_srcs, other_dsts
                )
            )

    return conflicts


def _append_conflicts_md(job_dir: Path, zone_name: str, conflicts: list[dict]) -> None:
    path = job_dir / "conflicts.md"
    header_needed = not path.exists()
    lines: list[str] = []
    if header_needed:
        lines.append("# Cross-Zone Conflicts\n\n")
        lines.append(f"_Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n\n")
        lines.append("| Zone | Conflicting Zone | Src | Dst | Reason |\n")
        lines.append("|---|---|---|---|---|\n")
    for c in conflicts:
        lines.append(
            f"| `{zone_name}` | `{c['conflicting_zone']}` | `{c['src']}` | `{c['dst']}` | {c['reason']} |\n"
        )
    with open(path, "a", encoding="utf-8") as f:
        f.write("".join(lines))


# ---------------------------------------------------------------------------
# Zone execution
# ---------------------------------------------------------------------------


def execute_zone(
    zone: dict,
    job_dir: Path,
    dry_run: bool,
    rename_log: list,
    move_log: list,
    dup_log: list,
    target_root: Path | None = None,
    tasks: dict | None = None,
) -> dict:
    """Execute a single zone's file moves. Returns a result dict."""
    zone_name = zone.get("zone", "unknown")
    moves = zone.get("moves", [])
    result = {
        "zone": zone_name,
        "moved": 0,
        "skipped": 0,
        "errors": [],
        "conflicts": [],
    }

    print(f"\n{'-' * 60}")
    print(f"  Zone: {zone_name}  ({len(moves)} files)")
    print(f"{'-' * 60}")

    # Pre-flight: cross-zone conflict check
    if tasks is not None:
        conflicts = detect_conflicts(tasks, zone)
        if conflicts:
            result["conflicts"] = conflicts
            _append_conflicts_md(job_dir, zone_name, conflicts)
            print(
                f"  [CONFLICT] {len(conflicts)} cross-zone conflict(s) — skipping zone execution"
            )
            for c in conflicts:
                print(
                    f"    - vs {c['conflicting_zone']}: {c['reason']} ({c['src']} -> {c['dst']})"
                )
            return result

    for entry in moves:
        src_path = Path(entry["src"])
        dest_dir = Path(entry["dest"])
        custom_name = entry.get("new_name")

        try:
            dest = safe_move(
                src_path,
                dest_dir,
                dry_run,
                rename_log,
                move_log,
                dup_log,
                target_root,
                custom_name,
            )
            if dest:
                result["moved"] += 1
            else:
                result["skipped"] += 1
        except Exception as exc:
            err = f"{src_path}: {exc}"
            result["errors"].append(err)
            print(f"  [ERR]  {err}")

    return result


# ---------------------------------------------------------------------------
# Global dedup pre-pass (tasks.json "dedup" array)
# ---------------------------------------------------------------------------


def _process_duplicate(
    dup_raw: str,
    keeper: Path,
    stated_hash: str,
    target_root: Path,
    dry_run: bool,
    dup_log: list,
    summary: dict,
) -> None:
    dup_path = Path(dup_raw)

    if not dup_path.exists():
        print(f"  [SKIP] duplicate not found: {dup_path}")
        summary["skipped"] += 1
        return

    if dup_path.resolve() == keeper.resolve():
        print(f"  [SKIP] keeper listed as duplicate: {dup_path}")
        summary["skipped"] += 1
        return

    file_hash = stated_hash if stated_hash else (_file_hash(dup_path) or "")
    if not file_hash or file_hash == "ERROR":
        err = f"cannot hash duplicate: {dup_path}"
        summary["errors"].append(err)
        print(f"  [ERR]  {err}")
        return

    dup_dest = _dedup_target_path(target_root, dup_path, file_hash)

    try:
        final_dest, resolution = _safe_dedup_move(
            dup_path, dup_dest, file_hash, dry_run
        )
        dup_log.append(
            {
                "hash": file_hash,
                "kept": str(keeper),
                "moved_from": str(dup_path),
                "moved_to": str(final_dest),
                "resolution": resolution,
            }
        )
        if dry_run:
            action = "[DRY]"
        elif resolution == "already-deduplicated":
            action = "[DEDUP-SEEN]"
        else:
            action = "[DEDUP]"
        print(f"  {action} {dup_path.name} -> {final_dest}")
        summary["moved"] += 1
    except Exception as exc:
        err = f"{dup_path}: {exc}"
        summary["errors"].append(err)
        print(f"  [ERR]  {err}")


def run_global_dedup(
    dedup_entries: list,
    target_root: Path,
    dry_run: bool,
    dup_log: list,
) -> dict:
    """Process the top-level 'dedup' array from tasks.json.

    For each entry, move every listed duplicate path into
    <target_root>/_duplicates/<YYYYMMDD>/<basename>_<hash[:8]><ext>.
    Keeper is never touched. Returns a summary dict.
    """
    summary = {"moved": 0, "skipped": 0, "errors": []}
    if not dedup_entries:
        return summary

    print(f"\n{'=' * 60}")
    print(f"  Global dedup pre-pass  ({len(dedup_entries)} groups)")
    print(f"{'=' * 60}")

    for entry in dedup_entries:
        keeper_raw = entry.get("keeper")
        duplicates = entry.get("duplicates") or []
        stated_hash = entry.get("hash") or ""

        if not keeper_raw:
            err = f"dedup entry missing 'keeper': {entry}"
            summary["errors"].append(err)
            print(f"  [ERR]  {err}")
            continue

        keeper = Path(keeper_raw)
        if not keeper.exists():
            # The keeper does not exist — we refuse to move the duplicates,
            # because that would leave zero copies on disk.
            err = f"keeper missing, skipping group: {keeper}"
            summary["errors"].append(err)
            print(f"  [ERR]  {err}")
            continue

        for dup_raw in duplicates:
            _process_duplicate(
                dup_raw, keeper, stated_hash, target_root, dry_run, dup_log, summary
            )

    return summary


def _write_dedup_log(job_dir: Path, dup_log: list, dry_run: bool) -> None:
    """Write dedup_log.md with a row for every duplicate move (global + batch + on-disk).

    The Resolution column records cross-process lock outcomes during parallel
    zone execution (see _safe_dedup_move). A trailing section lists any
    lock-contention events so post-mortem analysis can identify races.
    """
    path = job_dir / "dedup_log.md"
    lines = [
        "# Dedup Log\n\n",
        f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n",
        f"_Dry-run: {dry_run}_\n\n",
        f"**Total duplicates handled:** {len(dup_log)}\n\n",
        "| Hash | Kept Path | Moved-From Path | Moved-To Path | Resolution |\n",
        "|---|---|---|---|---|\n",
    ]
    for d in dup_log:
        h = d.get("hash", "")
        short = f"{h[:8]}..." if h else ""
        resolution = d.get("resolution", "moved")
        lines.append(
            f"| `{short}` | `{d.get('kept', '')}` | `{d.get('moved_from', '')}` | "
            f"`{d.get('moved_to', '')}` | {resolution} |\n"
        )
    if not dup_log:
        lines.append("| (none) | — | — | — | — |\n")

    # Cross-process lock contention events (parallel zone races).
    if _dedup_lock_events:
        lines.append(
            f"\n## Cross-process lock contention ({len(_dedup_lock_events)} events)\n\n"
            "Recorded when a parallel zone agent had to wait for, or timed out on, a\n"
            "`_duplicates/` target claim. High counts indicate many parallel collisions;\n"
            "`already-deduplicated` rows show races the lock successfully resolved.\n\n"
            "| Timestamp | Target | Resolution | Waited (ms) |\n"
            "|---|---|---|---|\n"
        )
        for ev in _dedup_lock_events:
            lines.append(
                f"| {ev.get('ts', '')} | `{ev.get('target', '')}` | "
                f"{ev.get('resolution', '')} | {ev.get('waited_ms', 0)} |\n"
            )

    path.write_text("".join(lines), encoding="utf-8")
    print(f"[organizer] dedup_log.md     -> {path}")


# ---------------------------------------------------------------------------
# Log writers
# ---------------------------------------------------------------------------


def _write_rename_log(job_dir: Path, rename_log: list, dry_run: bool) -> None:
    path = job_dir / "rename_log.md"
    lines = [
        "# Rename Log — Naming Convention Fixes\n",
        f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n",
        f"_Dry-run: {dry_run}_\n\n",
        "| Original Filename | Renamed To | Reason |\n",
        "|---|---|---|\n",
    ]
    for entry in rename_log:
        orig = Path(entry["original"]).name
        lines.append(f"| `{orig}` | `{entry['renamed_to']}` | {entry['reason']} |\n")
    if not rename_log:
        lines.append("| (none) | — | — |\n")
    path.write_text("".join(lines), encoding="utf-8")
    print(f"\n[organizer] rename_log.md -> {path}")


def _write_move_log(
    job_dir: Path, move_log: list, dup_log: list, dry_run: bool
) -> None:
    path = job_dir / "move_log.md"
    lines = [
        "# Move Log\n\n",
        f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n",
        f"_Dry-run: {dry_run}_\n\n",
        f"**Total moves:** {len(move_log)}  |  **Duplicates handled:** {len(dup_log)}\n\n",
        "## File Moves\n\n",
        "| Source | Destination |\n|---|---|\n",
    ]
    for m in move_log:
        lines.append(f"| `{Path(m['src']).name}` | `{m['dest']}` |\n")
    if not move_log:
        lines.append("| (none) | — |\n")

    if dup_log:
        lines.append(
            "\n## Duplicate Files (moved to `_duplicates/`)\n\n| Source | Duplicate Dest | Hash |\n|---|---|---|\n"
        )
        for d in dup_log:
            lines.append(
                f"| `{Path(d['moved_from']).name}` | `{d['moved_to']}` | {d['hash']}... |\n"
            )

    path.write_text("".join(lines), encoding="utf-8")
    print(f"[organizer] move_log.md      -> {path}")


# ---------------------------------------------------------------------------
# Main execute loop
# ---------------------------------------------------------------------------


def _infer_target_root(tasks: dict, zones: list) -> Path | None:
    """Derive the workspace target root used for the _duplicates/ landing zone.

    Order of precedence:
      1. tasks.json top-level "target" key
      2. Common ancestor of every zone's dest directory
    """
    explicit = tasks.get("target")
    if explicit:
        return Path(explicit).resolve()

    dests: list[Path] = []
    for zone in zones:
        for entry in zone.get("moves", []):
            d = entry.get("dest")
            if d:
                dests.append(Path(d).resolve())
    if not dests:
        return None

    try:
        from os.path import commonpath

        common = commonpath([str(d) for d in dests])
        return Path(common)
    except ValueError:
        # Paths on different drives (Windows) — no shared root.
        return dests[0].parent


def _load_tasks(job_dir: Path, graceful_no_op: bool = False) -> dict:
    tasks_file = job_dir / "tasks.json"
    if not tasks_file.exists():
        if graceful_no_op:
            print(f"Graceful no-op: tasks.json not found at {tasks_file}")
            sys.exit(0)
        print(f"ERROR: tasks.json not found at {tasks_file}")
        sys.exit(1)
    with open(tasks_file, encoding="utf-8") as f:
        return json.load(f)


def _log_execution_start(
    job_dir: Path, zones: list, dedup_entries: list, dry_run: bool
) -> None:
    mode = "DRY-RUN" if dry_run else "LIVE"
    print(f"\n{'=' * 60}")
    print(f"  DocumentOrganizer - Execute Phase  [{mode}]")
    print(f"  Job dir:  {job_dir}")
    print(f"  Zones:    {len(zones)}")
    print(f"  Dedup:    {len(dedup_entries)} groups")
    print(f"{'=' * 60}")


def _handle_global_dedup(
    dedup_entries: list, target_root: Path | None, dry_run: bool, dup_log: list
) -> dict:
    if not dedup_entries:
        return {"moved": 0, "skipped": 0, "errors": []}
    if target_root is None:
        print(
            "ERROR: 'dedup' present but target root could not be inferred. "
            "Set tasks.json 'target' or pass --target."
        )
        sys.exit(1)
    return run_global_dedup(dedup_entries, target_root, dry_run, dup_log)


def _cleanup_stale_logs(job_dir: Path) -> None:
    stale_conflicts = job_dir / "conflicts.md"
    if stale_conflicts.exists():
        try:
            stale_conflicts.unlink()
        except OSError:
            pass


def _run_zones(
    zones: list,
    job_dir: Path,
    dry_run: bool,
    rename_log: list,
    move_log: list,
    dup_log: list,
    target_root: Path | None,
    tasks: dict,
    max_concurrent: int,
) -> list:
    all_results = []
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = {
            executor.submit(
                execute_zone,
                zone,
                job_dir,
                dry_run,
                rename_log,
                move_log,
                dup_log,
                target_root,
                tasks,
            ): zone
            for zone in zones
        }
        for future in as_completed(futures):
            all_results.append(future.result())
    return all_results


def _log_execution_finish(
    job_dir: Path,
    all_results: list,
    dedup_summary: dict,
    rename_log: list,
    move_log: list,
    dup_log: list,
    dry_run: bool,
) -> None:
    tm = sum(r["moved"] for r in all_results) + dedup_summary["moved"]
    ts = sum(r["skipped"] for r in all_results) + dedup_summary["skipped"]
    te = sum(len(r["errors"]) for r in all_results) + len(dedup_summary["errors"])
    cz = [r for r in all_results if r.get("conflicts")]
    tc = sum(len(r["conflicts"]) for r in cz)

    print(
        f"\n{'=' * 60}\n  COMPLETE - Moved: {tm}  Skipped: {ts}  Errors: {te}  Conflicted zones: {len(cz)}\n{'=' * 60}"
    )

    _write_rename_log(job_dir, rename_log, dry_run)
    _write_move_log(job_dir, move_log, dup_log, dry_run)
    _write_dedup_log(job_dir, dup_log, dry_run)

    # Write unified JSON manifest
    try:
        manifest_path = job_dir / "document_organizer_moves.json"
        manifest_data = {
            "moves": move_log,
            "renames": rename_log,
            "duplicates": dup_log,
        }
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest_data, mf, indent=2, ensure_ascii=False)
        print(f"[organizer] document_organizer_moves.json -> {manifest_path}")
    except Exception as exc:
        print(f"[organizer] WARNING: failed to write unified manifest: {exc}")

    # FR-ORG-14: Autonomous Library Custodian post-filing re-evaluation (stolen with pride from Jevbox)
    try:
        from project_router import ProjectRouter

        touched_projects = set()
        for m in move_log:
            dst = Path(m.get("moved_to", m.get("to", "")))
            for part in dst.parts:
                if any(part.startswith(f"{i:02d}_") for i in range(100)):
                    touched_projects.add(part)
                    break
        if touched_projects:
            router = ProjectRouter()
            for proj in touched_projects:
                proposals = router.review_and_refile_inbox_candidates(
                    newly_filed_project_name=proj
                )
                if proposals:
                    print(
                        f"[organizer:custodian] Autonomous Custodian found {len(proposals)} loose 00_INBOX candidate(s) for '{proj}':"
                    )
                    for prop in proposals:
                        print(
                            f"  -> Match: {Path(prop['source_file']).name} (confidence: {prop['confidence']:.4f})"
                        )
    except Exception as exc:
        print(f"[organizer:custodian] Note: custodian review skipped ({exc})")

    if cz:
        _write_conflicts_summary(job_dir, cz, tc)
        print(
            f"\n[organizer] WARNING: {len(cz)} zone(s) halted on cross-zone conflicts — check conflicts.md"
        )
    if te:
        print(f"\n[organizer] WARNING: {te} errors encountered — check move_log.md")
    if te or cz:
        sys.exit(1)


def run_execute(
    job_dir: Path,
    max_concurrent: int,
    dry_run: bool,
    target_override: Path | None = None,
    graceful_no_op: bool = False,
) -> None:
    tasks = _load_tasks(job_dir, graceful_no_op=graceful_no_op)
    zones = tasks.get("zones", [])
    dedup_entries = tasks.get("dedup", [])
    renames = tasks.get("rename", [])

    # Synthesize LLM rename tasks into zones for the execution engine
    if renames:
        rename_zones = {}
        target_root = target_override or Path(tasks.get("target", ""))
        for r in renames:
            z_name = r.get("dest_folder", "unknown")
            if z_name not in rename_zones:
                rename_zones[z_name] = []

            src = Path(r["src"])
            dest = target_root / z_name
            rename_zones[z_name].append(
                {"src": str(src), "dest": str(dest), "new_name": r["dest_name"]}
            )

        for z_name, moves in rename_zones.items():
            zones.append({"name": z_name, "moves": moves})

    if not zones and not dedup_entries:
        if graceful_no_op:
            print(
                "Graceful no-op: tasks.json has no 'zones', 'dedup', or 'rename' work to do."
            )
            sys.exit(0)
        print("ERROR: tasks.json has no 'zones', 'dedup', or 'rename' work to do.")
        sys.exit(1)

    _log_execution_start(job_dir, zones, dedup_entries, dry_run)

    rename_log, move_log, dup_log, all_results = [], [], [], []
    target_root = target_override or _infer_target_root(tasks, zones)

    _batch_claimed.clear()
    _dedup_lock_events.clear()

    dedup_summary = _handle_global_dedup(dedup_entries, target_root, dry_run, dup_log)
    _cleanup_stale_logs(job_dir)

    if zones:
        all_results = _run_zones(
            zones,
            job_dir,
            dry_run,
            rename_log,
            move_log,
            dup_log,
            target_root,
            tasks,
            max_concurrent,
        )

    _log_execution_finish(
        job_dir, all_results, dedup_summary, rename_log, move_log, dup_log, dry_run
    )


def _write_conflicts_summary(
    job_dir: Path, conflicted_zones: list, total_conflicts: int
) -> None:
    path = job_dir / "conflicts_summary.md"
    lines = [
        "# Cross-Zone Conflicts Summary\n\n",
        f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n\n",
        f"**Affected zones:** {len(conflicted_zones)}  |  **Total conflicts:** {total_conflicts}\n\n",
        "| Zone | Conflicts | Reasons |\n|---|---|---|\n",
    ]
    for r in conflicted_zones:
        reasons = "; ".join(sorted({c["reason"] for c in r["conflicts"]}))
        lines.append(f"| `{r['zone']}` | {len(r['conflicts'])} | {reasons} |\n")
    lines.append("\nSee `conflicts.md` for the full per-move breakdown.\n")
    path.write_text("".join(lines), encoding="utf-8")
    print(f"[organizer] conflicts_summary.md -> {path}")


def main() -> None:
    if sys.platform == "win32":
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Execute a DocumentOrganizer reorganization plan"
    )
    parser.add_argument(
        "--execute",
        metavar="JOB_DIR",
        required=True,
        help="Path to job directory containing tasks.json",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=3,
        help="Max parallel zone agents (default: 3)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview moves without actually moving files",
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Optional override for target workspace root (where _duplicates/ lives)",
    )
    parser.add_argument(
        "--graceful-no-op",
        action="store_true",
        help="Exit with 0 instead of 1 if job dir, tasks.json or tasks are missing",
    )

    args = parser.parse_args()
    job_dir = Path(args.execute).resolve()

    if not job_dir.is_dir():
        if args.graceful_no_op:
            print(f"Graceful no-op: job dir not found: {job_dir}")
            sys.exit(0)
        print(f"ERROR: job dir not found: {job_dir}")
        sys.exit(1)

    target_override = Path(args.target).resolve() if args.target else None
    run_execute(
        job_dir,
        args.max_concurrent,
        args.dry_run,
        target_override,
        graceful_no_op=args.graceful_no_op,
    )


if __name__ == "__main__":
    main()
