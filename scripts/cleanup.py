import shutil
from pathlib import Path


def cleanup_directories(directories: list[str], dry_run: bool = True) -> None:
    """Clean up specified directories."""
    for dir_path in directories:
        path = Path(dir_path)
        if not path.exists():
            print(f"Directory not found: {dir_path}")
            continue

        print(f"{'Would clean' if dry_run else 'Cleaning'}: {dir_path}")

        if not dry_run:
            for item in path.iterdir():
                item_path = path / item
                if item_path.is_file():
                    item_path.unlink()
                else:
                    shutil.rmtree(item_path)


def cleanup_file(file_path: str, dry_run: bool = True) -> None:
    """Remove a specific file."""
    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {file_path}")
        return

    print(f"{'Would remove' if dry_run else 'Removing'}: {file_path}")

    if not dry_run:
        path.unlink()
