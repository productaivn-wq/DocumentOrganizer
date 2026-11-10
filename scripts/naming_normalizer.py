"""
naming_normalizer.py — Canonical naming linter and normalizer for DocumentOrganizer.

Implements: UC-001
Traces: FR-ORG-08, FR-ORG-09
Verifies: TC-ORG-NORM-01, TC-ORG-NORM-02
"""

import re
import unicodedata
from pathlib import Path

# Vietnamese diacritics translation map to clean pure ASCII
VIETNAMESE_MAP = {
    "à": "a",
    "á": "a",
    "ả": "a",
    "ã": "a",
    "ạ": "a",
    "ă": "a",
    "ằ": "a",
    "ắ": "a",
    "ẳ": "a",
    "ẵ": "a",
    "ặ": "a",
    "â": "a",
    "ầ": "a",
    "ấ": "a",
    "ẩ": "a",
    "ẫ": "a",
    "ậ": "a",
    "đ": "d",
    "è": "e",
    "é": "e",
    "ẻ": "e",
    "ẽ": "e",
    "ẹ": "e",
    "ê": "e",
    "ề": "e",
    "ế": "e",
    "ể": "e",
    "ễ": "e",
    "ệ": "e",
    "ì": "i",
    "í": "i",
    "ỉ": "i",
    "ĩ": "i",
    "ị": "i",
    "ò": "o",
    "ó": "o",
    "ỏ": "o",
    "õ": "o",
    "ọ": "o",
    "ô": "o",
    "ồ": "o",
    "ố": "o",
    "ổ": "o",
    "ỗ": "o",
    "ộ": "o",
    "ơ": "o",
    "ờ": "o",
    "ớ": "o",
    "ở": "o",
    "ỡ": "o",
    "ợ": "o",
    "ù": "u",
    "ú": "u",
    "ủ": "u",
    "ũ": "u",
    "ụ": "u",
    "ư": "u",
    "ừ": "u",
    "ứ": "u",
    "ử": "u",
    "ữ": "u",
    "ự": "u",
    "ỳ": "y",
    "ý": "y",
    "ỷ": "y",
    "ỹ": "y",
    "ỵ": "y",
    # Uppercase
    "À": "A",
    "Á": "A",
    "Ả": "A",
    "Ã": "A",
    "Ạ": "A",
    "Ă": "A",
    "Ằ": "A",
    "Ắ": "A",
    "Ẳ": "A",
    "Ẵ": "A",
    "Ặ": "A",
    "Â": "A",
    "Ầ": "A",
    "Ấ": "A",
    "Ẩ": "A",
    "Ẫ": "A",
    "Ậ": "A",
    "Đ": "D",
    "È": "E",
    "É": "E",
    "Ẻ": "E",
    "Ẽ": "E",
    "Ẹ": "E",
    "Ê": "E",
    "Ề": "E",
    "Ế": "E",
    "Ể": "E",
    "Ễ": "E",
    "Ệ": "E",
    "Ì": "I",
    "Í": "I",
    "Ỉ": "I",
    "Ĩ": "I",
    "Ị": "I",
    "Ò": "O",
    "Ó": "O",
    "Ỏ": "O",
    "Õ": "O",
    "Ọ": "O",
    "Ô": "O",
    "Ồ": "O",
    "Ố": "O",
    "Ổ": "O",
    "Ỗ": "O",
    "Ộ": "O",
    "Ơ": "O",
    "Ờ": "O",
    "Ớ": "O",
    "Ở": "O",
    "Ỡ": "O",
    "Ợ": "O",
    "Ù": "U",
    "Ú": "U",
    "Ủ": "U",
    "Ũ": "U",
    "Ụ": "U",
    "Ư": "U",
    "Ừ": "U",
    "Ứ": "U",
    "Ử": "U",
    "Ữ": "U",
    "Ự": "U",
    "Ỳ": "Y",
    "Ý": "Y",
    "Ỷ": "Y",
    "Ỹ": "Y",
    "Ỵ": "Y",
}


def remove_vietnamese_diacritics(text: str) -> str:
    """Replace Vietnamese accented characters with ASCII equivalents."""
    res = []
    for ch in text:
        if ch in VIETNAMESE_MAP:
            res.append(VIETNAMESE_MAP[ch])
        else:
            # Fallback decomposition
            nfkd = unicodedata.normalize("NFKD", ch)
            ascii_ch = "".join(c for c in nfkd if not unicodedata.combining(c))
            res.append(ascii_ch if ascii_ch else ch)
    return "".join(res)


def normalize_name(name: str, is_directory: bool = False) -> str:
    """
    Normalize a file or directory name to strict canonical pure ASCII snake_case.

    Rules:
    - Eliminate Vietnamese diacritics.
    - Replace spaces, dashes, parentheses, brackets with '_'.
    - Convert dots (except version dots like v1.0 or extension) to '_'.
    - Collapse multiple consecutive underscores to a single '_'.
    - Preserve existing clean prefixes (e.g. '01_', 'CUM_01_', 'v1.0_').
    - If directory: convert to UPPER_SNAKE or lower_snake based on majority casing.
    - If file: keep extension lowercase preceded by a dot.
    """
    if is_directory:
        stem = remove_vietnamese_diacritics(name)
        clean = re.sub(r"[^a-zA-Z0-9_]+", "_", stem)
        clean = re.sub(r"_+", "_", clean).strip("_")
        upper_count = sum(1 for c in name if c.isupper())
        lower_count = sum(1 for c in name if c.islower())
        if upper_count > lower_count:
            return clean.upper()
        return clean.lower()
    else:
        p = Path(name)
        ext = p.suffix.lower()
        base = p.stem
        base_clean = remove_vietnamese_diacritics(base)
        # Replace parentheses and numbers like (1) -> _v1
        base_clean = re.sub(r"\s*\(\s*(\d+)\s*\)", r"_v\1", base_clean)
        # Replace non-version dots with underscore
        base_clean = re.sub(r"(?<!v\d)\.", "_", base_clean)
        # Replace non-alphanumeric (allowing dots only if part of version like v2.1)
        base_clean = re.sub(r"[^a-zA-Z0-9_\.]+", "_", base_clean)
        base_clean = re.sub(r"_+", "_", base_clean).strip("_")

        # Lowercase file names unless they are standard uppercase docs (e.g. README.md, PROJECT_ORGANIZATION.md)
        upper_count = sum(1 for c in base if c.isupper())
        lower_count = sum(1 for c in base if c.islower())
        if (
            upper_count > lower_count
            and lower_count == 0
            or upper_count > lower_count
            and base.startswith(
                (
                    "01_",
                    "02_",
                    "03_",
                    "04_",
                    "05_",
                    "06_",
                    "07_",
                    "08_",
                    "09_",
                    "10_",
                    "11_",
                    "12_",
                    "13_",
                    "14_",
                    "15_",
                    "16_",
                    "17_",
                    "18_",
                    "19_",
                    "20_",
                    "21_",
                    "22_",
                    "23_",
                    "24_",
                    "25_",
                    "26_",
                    "27_",
                    "28_",
                    "29_",
                    "30_",
                    "31_",
                    "32_",
                )
            )
        ):
            final_base = base_clean.upper()
        else:
            final_base = base_clean.lower()

        return f"{final_base}{ext}"


class NamingNormalizer:
    """Linter and normalizer for workspace naming and generated asset placement."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root).resolve()

    def lint_path(self, path: Path) -> list[str]:
        violations = []
        name = path.name
        if any(ord(c) >= 128 for c in name):
            violations.append("NON_ASCII_DIACRITICS")
        if " " in name:
            violations.append("CONTAINS_WHITESPACE")
        if "(" in name or ")" in name:
            violations.append("CONTAINS_PARENTHESES")
        if name.startswith(("-", " ")) or name.endswith(("-", " ")):
            violations.append("LEADING_TRAILING_DELIMITERS")
        return violations

    def is_misplaced_in_docs(self, path: Path) -> bool:
        parts = path.parts
        if "docs" in parts:
            ext = path.suffix.lower()
            if ext in {".docx", ".html", ".png", ".jpg", ".jpeg"}:
                return True
        return False
