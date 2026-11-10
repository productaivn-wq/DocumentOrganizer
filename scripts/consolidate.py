import json
from pathlib import Path


def consolidate_documents(input_dir: str, output_file: str) -> None:
    """Consolidate multiple documents into a single file."""
    input_path = Path(input_dir)
    output_path = Path(output_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    consolidated = {}

    for file_path in input_path.glob("*.json"):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                consolidated[file_path.stem] = data
            except json.JSONDecodeError as e:
                print(f"Error parsing {file_path}: {e}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(consolidated, f, indent=2, ensure_ascii=False)

    print(f"Consolidated {len(consolidated)} documents into {output_file}")
