import hashlib
from pathlib import Path


def get_file_hash(
    path: Path | str, algo: str = "md5", chunk_size: int = 8192
) -> str | None:
    """
    Calculate hash of a file.
    Returns None for directories. Returns 'ERROR' on permission/file errors.
    """
    path_obj = Path(path)
    if not path_obj.is_file():
        return None

    try:
        hasher = hashlib.new(algo)
    except ValueError:
        hasher = hashlib.md5()

    try:
        with open(path_obj, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (FileNotFoundError, PermissionError, OSError):
        return "ERROR"
