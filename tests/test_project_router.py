"""Unit tests for ProjectRouter dynamic portfolio discovery & MECE SSOT zone routing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from project_router import VALID_MECE_ZONES, ProjectRouter, sanitize_mece_zone


@pytest.fixture
def mock_portfolio_workspace(tmp_path: Path) -> Path:
    """Create a portable mock workspace with >= 30 portfolio entries."""
    ws = tmp_path / "01_PROJECTS"
    ws.mkdir(parents=True)
    projects = {f"{i:02d}_SAMPLE_PROJECT_{i:02d}": {} for i in range(1, 26)}
    projects.update(
        {
            "10_PRODUCT_PLATFORM": {},
            "20_CLOUD_INFRASTRUCTURE": {},
            "30_DATA_INTELLIGENCE": {},
            "40_FIELD_RESEARCH": {},
            "50_FLEET_OPERATIONS": {},
            "60_DEV_EXPERIENCE": {},
        }
    )
    (ws / "portfolio_manifest.json").write_text(
        json.dumps({"projects": projects}, indent=2),
        encoding="utf-8",
    )
    return ws


def test_sanitize_mece_zone() -> None:
    """Verify that non-MECE paths are sanitized into 20_ACTIVE_CONTINUOUS."""
    assert sanitize_mece_zone("photos") == Path("20_ACTIVE_CONTINUOUS/media/photos")
    assert sanitize_mece_zone("data/photos") == Path("20_ACTIVE_CONTINUOUS/data/photos")
    assert sanitize_mece_zone("media") == Path("20_ACTIVE_CONTINUOUS/media")

    assert sanitize_mece_zone("00_INBOX") == Path("00_INBOX")
    assert sanitize_mece_zone("30_REFERENCE/specs") == Path("30_REFERENCE/specs")
    assert sanitize_mece_zone("40_ARCHIVE/2026") == Path("40_ARCHIVE/2026")


def test_project_router_dynamic_discovery(mock_portfolio_workspace: Path) -> None:
    """Verify ProjectRouter discovers all portfolio projects from manifest."""
    router = ProjectRouter(workspace_base=mock_portfolio_workspace)
    assert len(router.profiles) >= 30, f"Expected >= 30 projects, got {len(router.profiles)}"

    names = {p["name"] for p in router.profiles}
    assert "50_FLEET_OPERATIONS" in names
    assert "30_DATA_INTELLIGENCE" in names
    assert "20_CLOUD_INFRASTRUCTURE" in names
    assert "60_DEV_EXPERIENCE" in names
    assert "10_PRODUCT_PLATFORM" in names


def test_fleet_operations_route_mece(mock_portfolio_workspace: Path) -> None:
    """Verify 50_FLEET_OPERATIONS routes documents and photos strictly to MECE zones."""
    router = ProjectRouter(workspace_base=mock_portfolio_workspace)

    route_doc = router.resolve_destination("maritime_vessel_warranty_documentation.zip")
    assert route_doc is not None
    assert route_doc.project_name == "50_FLEET_OPERATIONS"
    assert route_doc.relative_zone_path.parts[0] in VALID_MECE_ZONES
    assert "20_ACTIVE_CONTINUOUS" in str(route_doc.target_full_path)

    route_photo = router.resolve_destination("maritime_hull_inspection_report.png")
    assert route_photo is not None
    assert route_photo.project_name == "50_FLEET_OPERATIONS"
    assert route_photo.relative_zone_path == Path("20_ACTIVE_CONTINUOUS/media/photos")
    assert route_photo.relative_zone_path.parts[0] in VALID_MECE_ZONES
    assert "20_ACTIVE_CONTINUOUS" in str(route_photo.target_full_path)


def test_data_intelligence_route_mece(mock_portfolio_workspace: Path) -> None:
    """Verify 30_DATA_INTELLIGENCE routes documents and photos strictly to MECE zones."""
    router = ProjectRouter(workspace_base=mock_portfolio_workspace)

    route_doc = router.resolve_destination("adaptive_chunking_rag_pipeline_spec.docx")
    assert route_doc is not None
    assert route_doc.project_name == "30_DATA_INTELLIGENCE"
    assert route_doc.relative_zone_path.parts[0] in VALID_MECE_ZONES

    route_photo = router.resolve_destination("knowledge_graph_rag_diagram.png")
    assert route_photo is not None
    assert route_photo.project_name == "30_DATA_INTELLIGENCE"
    assert route_photo.relative_zone_path == Path("20_ACTIVE_CONTINUOUS/media/photos")
    assert route_photo.relative_zone_path.parts[0] in VALID_MECE_ZONES


def test_general_fallback_mece(mock_portfolio_workspace: Path) -> None:
    """Verify fallback when no project matches routes strictly to 00_INBOX."""
    router = ProjectRouter(workspace_base=mock_portfolio_workspace)
    route = router.resolve_destination("unrelated_mystery_file_12345.xyz")
    assert route is not None
    assert route.relative_zone_path.parts[0] in VALID_MECE_ZONES
    assert route.relative_zone_path == Path("00_INBOX")


def test_discrete_choice_fallback_routing(mock_portfolio_workspace: Path) -> None:
    """TC_UC_DO_013: Verify discrete-choice fallback routes context-matched files with >=0.65 prob."""
    router = ProjectRouter(workspace_base=mock_portfolio_workspace)

    route = router.resolve_destination(
        filename="quarterly_check.txt",
        content_hint="Marina shipyard vessel warranty engine maintenance aftersales inspection",
    )
    assert route is not None
    assert route.project_name == "50_FLEET_OPERATIONS"
    assert route.confidence >= 0.65


def test_autonomous_library_custodian_refile_inbox(
    tmp_path: Path, mock_portfolio_workspace: Path
) -> None:
    """TC_UC_DO_014: Verify Autonomous Custodian evaluates loose inbox files and re-files >=0.70 matches."""
    router = ProjectRouter(workspace_base=mock_portfolio_workspace)

    inbox = tmp_path / "00_INBOX"
    inbox.mkdir(parents=True)

    loose_doc = inbox / "shipyard_hull_cleaning.md"
    loose_doc.write_text(
        "# Marina vessel hull cleaning and engine maintenance warranty", encoding="utf-8"
    )

    proposals = router.review_and_refile_inbox_candidates(
        newly_filed_project_name="50_FLEET_OPERATIONS", inbox_dir=inbox
    )

    assert len(proposals) >= 1
    assert proposals[0]["target_project"] == "50_FLEET_OPERATIONS"
    assert proposals[0]["confidence"] >= 0.70
    assert "Autonomous Custodian" in proposals[0]["rule"]
