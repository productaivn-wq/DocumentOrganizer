import argparse
import logging
from pathlib import Path

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FRONTMATTER_DELIMITER = "---"


def has_frontmatter(content: str) -> bool:
    """Check if content already has YAML frontmatter.

    Args:
        content: File content to check.

    Returns:
        True if content starts with frontmatter delimiter.
    """
    return content.strip().startswith(FRONTMATTER_DELIMITER)


def format_frontmatter(context: dict[str, str]) -> str:
    """Format context dictionary as YAML frontmatter string.

    Args:
        context: Dictionary of key-value pairs to format.

    Returns:
        Formatted YAML frontmatter string.
    """
    if HAS_YAML:
        try:
            yaml_content = yaml.dump(context, default_flow_style=False, sort_keys=False)
            return f"{FRONTMATTER_DELIMITER}\n{yaml_content}{FRONTMATTER_DELIMITER}\n"
        except Exception:
            pass

    # Fallback to simple key-value format
    front_matter = f"{FRONTMATTER_DELIMITER}\n"
    for key, value in context.items():
        front_matter += f"{key}: {value}\n"
    front_matter += f"{FRONTMATTER_DELIMITER}\n"
    return front_matter


def add_context(
    file: Path,
    context: dict[str, str],
    overwrite: bool = False,
    encoding: str = "utf-8",
) -> None:
    """Add YAML frontmatter context to a file.

    Args:
        file: Path to the file to modify.
        context: Dictionary of key-value pairs to add as frontmatter.
        overwrite: If True, replaces existing frontmatter. If False, skips files with existing frontmatter.
        encoding: File encoding (default: utf-8).

    Raises:
        OSError: If file cannot be read or written.
    """
    content = file.read_text(encoding=encoding)

    if has_frontmatter(content) and not overwrite:
        logger.info(f"Skipping {file} - already has frontmatter")
        return

    front_matter = format_frontmatter(context)
    file.write_text(front_matter + content, encoding=encoding)
    logger.info(f"Added context to {file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Add context to files")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("-k", "--key", required=True, help="Context key")
    parser.add_argument("-v", "--value", required=True, help="Context value")
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing frontmatter"
    )
    parser.add_argument(
        "--encoding", default="utf-8", help="File encoding (default: utf-8)"
    )
    args = parser.parse_args()

    for f in args.files:
        try:
            add_context(
                f,
                {args.key: args.value},
                overwrite=args.overwrite,
                encoding=args.encoding,
            )
        except OSError as e:
            logger.error(f"Failed to process {f}: {e}")


if __name__ == "__main__":
    main()
