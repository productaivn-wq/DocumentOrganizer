import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.depth_policy import audit, load_exception_manifest, normalize_exception
from scripts.scan import scan_directory


def write(root: Path, relative: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("test", encoding="utf-8")


def test_project_zone_document_is_allowed(tmp_path: Path) -> None:
    write(tmp_path, "30_REFERENCE/document.pdf")
    assert audit(tmp_path) == []


def test_category_folder_is_already_too_deep(tmp_path: Path) -> None:
    write(tmp_path, "30_REFERENCE/Career/document.pdf")
    assert [item["depth"] for item in audit(tmp_path)] == [3]


def test_recursive_audit_still_finds_deeper_documents(tmp_path: Path) -> None:
    write(tmp_path, "40_ARCHIVE/domain/collection/sub/document.docx")
    write(tmp_path, "40_ARCHIVE/domain/collection/sub/deeper/document.txt")
    assert [item["depth"] for item in audit(tmp_path)] == [5, 6]


def test_declared_opaque_exception_allows_deep_technical_tree(tmp_path: Path) -> None:
    exception = normalize_exception(tmp_path, "40_ARCHIVE/Legacy/snapshots")
    assert audit(tmp_path, exceptions=[exception]) == []


def test_exception_does_not_hide_sibling_managed_documents(tmp_path: Path) -> None:
    write(tmp_path, "40_ARCHIVE/Legacy/snapshots/tool/readme.md")
    write(tmp_path, "40_ARCHIVE/Legacy/records/old/report.pdf")
    exception = normalize_exception(tmp_path, "40_ARCHIVE/Legacy/snapshots")
    assert [item["path"] for item in audit(tmp_path, exceptions=[exception])] == [
        str(Path("40_ARCHIVE/Legacy/records/old/report.pdf"))
    ]


@pytest.mark.parametrize("value", ["../outside", "not-a-zone/tree"])
def test_exception_must_be_inside_a_lifecycle_zone(tmp_path: Path, value: str) -> None:
    with pytest.raises(ValueError):
        normalize_exception(tmp_path, value)


def test_manifest_requires_explicit_opaque_exceptions_array(tmp_path: Path) -> None:
    manifest = tmp_path / "exceptions.json"
    manifest.write_text(
        '{"opaque_exceptions":["10_ACTIVE_TIMEBOUND/Project"]}', encoding="utf-8"
    )
    assert load_exception_manifest(tmp_path, manifest) == [
        Path("10_ACTIVE_TIMEBOUND/Project")
    ]


def test_scanner_inventory_reaches_beyond_layer_six(tmp_path: Path) -> None:
    write(tmp_path, "40_ARCHIVE/a/b/c/d/e/f/deep.txt")
    output = scan_directory(tmp_path, 50, set(), str(tmp_path / "output"), True, None)
    import json

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["inventory"]["total_files"] == 1
