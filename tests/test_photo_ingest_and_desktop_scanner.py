"""
test_photo_ingest_and_desktop_scanner.py — Test suite for photo ingestion and desktop scanning.

Implements: UC-001
Traces: FR-ORG-01, FR-ORG-02, FR-ORG-03, FR-ORG-04, FR-ORG-05
Verifies: TC-ORG-PHOTO-01, TC-ORG-DESKTOP-01, TC-ORG-ROUTER-01
"""

import sys
from pathlib import Path

# Ensure skill root is on sys.path
SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts.desktop_scanner import DesktopScanner
from scripts.photo_ingest import PhotoIngestEngine
from scripts.project_router import ProjectRouter


def create_mock_jpeg(path: Path, width: int = 100, height: int = 100) -> None:
    """Create a minimal valid JPEG file using pure python headers or PIL if available."""
    try:
        from PIL import Image

        img = Image.new("RGB", (width, height), color=(255, 0, 0))
        img.save(path, "JPEG")
    except ImportError:
        # Minimal valid 1x1 JPEG binary fallback
        minimal_jpeg = bytes(
            [
                0xFF,
                0xD8,
                0xFF,
                0xE0,
                0x00,
                0x10,
                0x4A,
                0x46,
                0x49,
                0x46,
                0x00,
                0x01,
                0x01,
                0x01,
                0x00,
                0x48,
                0x00,
                0x48,
                0x00,
                0x00,
                0xFF,
                0xDB,
                0x00,
                0x43,
                0x00,
                0x08,
                0x06,
                0x06,
                0x07,
                0x06,
                0x05,
                0x08,
                0x07,
                0x07,
                0x07,
                0x09,
                0x09,
                0x08,
                0x0A,
                0x0C,
                0x14,
                0x0D,
                0x0C,
                0x0B,
                0x0B,
                0x0C,
                0x19,
                0x12,
                0x13,
                0x0F,
                0x14,
                0x1D,
                0x1A,
                0x1F,
                0x1E,
                0x1D,
                0x1A,
                0x1C,
                0x1C,
                0x20,
                0x24,
                0x2E,
                0x27,
                0x20,
                0x22,
                0x2C,
                0x23,
                0x1C,
                0x1C,
                0x28,
                0x37,
                0x29,
                0x2C,
                0x30,
                0x31,
                0x34,
                0x34,
                0x34,
                0x1F,
                0x27,
                0x39,
                0x3D,
                0x38,
                0x32,
                0x3C,
                0x2E,
                0x33,
                0x34,
                0x32,
                0xFF,
                0xC0,
                0x00,
                0x0B,
                0x08,
                0x00,
                0x01,
                0x00,
                0x01,
                0x01,
                0x01,
                0x11,
                0x00,
                0xFF,
                0xC4,
                0x00,
                0x1F,
                0x00,
                0x00,
                0x01,
                0x05,
                0x01,
                0x01,
                0x01,
                0x01,
                0x01,
                0x01,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x01,
                0x02,
                0x03,
                0x04,
                0x05,
                0x06,
                0x07,
                0x08,
                0x09,
                0x0A,
                0x0B,
                0xFF,
                0xDA,
                0x00,
                0x08,
                0x01,
                0x01,
                0x00,
                0x00,
                0x3F,
                0x00,
                0xBF,
                0x80,
                0xFF,
                0xD9,
            ]
        )
        path.write_bytes(minimal_jpeg)


def test_photo_ingest_metadata_extraction(tmp_path: Path):
    img_path = tmp_path / "gate screen survey.jpg"
    create_mock_jpeg(img_path, width=200, height=150)

    engine = PhotoIngestEngine()
    meta = engine.extract_metadata(img_path)

    assert meta is not None
    assert meta.filename == "gate screen survey.jpg"
    assert meta.format.lower() in {"jpeg", "jpg"}
    assert meta.size_bytes > 0
    assert len(meta.sha256_hash) == 64
    assert meta.width > 0
    assert meta.height > 0


def test_photo_ingest_unsupported_file(tmp_path: Path):
    txt_path = tmp_path / "notes.txt"
    txt_path.write_text("Regular text notes", encoding="utf-8")

    engine = PhotoIngestEngine()
    meta = engine.extract_metadata(txt_path)
    assert meta is None


def test_desktop_scanner_finds_unorganized_assets(tmp_path: Path):
    mock_desktop = tmp_path / "Desktop"
    mock_desktop.mkdir(parents=True)

    photo_folder = mock_desktop / "Survey photo"
    photo_folder.mkdir()

    p1 = photo_folder / "gate screen survey.jpg"
    create_mock_jpeg(p1)
    p2 = photo_folder / "ticket price at the gate.jpg"
    create_mock_jpeg(p2)

    scanner = DesktopScanner(override_paths=[mock_desktop])
    unorganized = scanner.scan_unorganized()

    assert len(unorganized) >= 2
    paths = [item.path for item in unorganized]
    assert p1 in paths
    assert p2 in paths


def test_project_router_matches_field_research(tmp_path: Path):
    router = ProjectRouter(workspace_base=tmp_path)

    # Register project
    eureka_dir = tmp_path / "40_FIELD_RESEARCH"
    eureka_dir.mkdir(parents=True)

    filename = "gate screen survey.jpg"
    route = router.resolve_destination(
        filename=filename,
        source_dir_name="Survey photo",
        content_hint="Heritage Craft Museum fieldwork",
    )

    assert route is not None
    assert route.project_name == "40_FIELD_RESEARCH"
    assert "fieldwork_photos" in str(route.relative_zone_path)
    assert route.standardized_filename.startswith(
        "img_"
    ) or route.standardized_filename.endswith(".jpg")
