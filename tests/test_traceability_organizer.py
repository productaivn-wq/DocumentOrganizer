#!/usr/bin/env python3
"""Comprehensive Test Suite for Traceability-Aware Document Organizer."""

import sys
from pathlib import Path

import pytest

_SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SKILL_ROOT / "core"))
sys.path.insert(0, str(_SKILL_ROOT / "scripts"))

from jd_registry import load_registry, resolve_project_for_file
from organizer_graph import build_document_organizer_graph
from traceability_resolver import TraceabilityContextResolver


@pytest.fixture
def mock_projects_root(tmp_path):
    """Create mock monorepo projects root with standard PP folders."""
    proj_dir = tmp_path / "01_PROJECTS"
    proj_dir.mkdir()
    (proj_dir / "10_PRODUCT_PLATFORM").mkdir()
    (proj_dir / "20_CLOUD_INFRASTRUCTURE").mkdir()
    (proj_dir / "30_DATA_INTELLIGENCE").mkdir()
    (proj_dir / "40_FIELD_RESEARCH").mkdir()
    (proj_dir / "50_FLEET_OPERATIONS").mkdir()
    (proj_dir / "60_DEV_EXPERIENCE").mkdir()
    return proj_dir


def test_monorepo_project_discovery(mock_projects_root):
    """Verify that monorepo project folders are correctly discovered and registered."""
    resolver = TraceabilityContextResolver(projects_root=mock_projects_root)
    registry = resolver.projects_registry

    assert "10" in registry
    assert registry["10"]["name"] == "PRODUCT_PLATFORM"
    assert "20" in registry
    assert registry["20"]["name"] == "CLOUD_INFRASTRUCTURE"
    assert "30" in registry
    assert "40" in registry
    assert "50" in registry
    assert registry["50"]["name"] == "FLEET_OPERATIONS"
    assert "60" in registry


def test_traceability_resolver_file_matching(mock_projects_root):
    """Verify semantic project resolution for characteristic project filenames."""
    resolver = TraceabilityContextResolver(projects_root=mock_projects_root)

    res_platform = resolver.resolve_project_affinity(
        filepath="ProductPlatform_Roadmap_Review_and_Gap_Analysis.docx",
        summary="Roadmap review and gap analysis for ProductPlatform curriculum",
    )
    assert res_platform.pp == "10"
    assert res_platform.project_name == "PRODUCT_PLATFORM"
    assert res_platform.confidence >= 0.50

    res_infra = resolver.resolve_project_affinity(
        filepath="cloud_infrastructure_kubernetes_audit.pdf",
        summary="Kubernetes deployment and terraform incident_audit report",
    )
    assert res_infra.pp == "20"
    assert res_infra.project_name == "CLOUD_INFRASTRUCTURE"

    res_data = resolver.resolve_project_affinity(
        filepath="knowledge_graph_rag_pipeline_spec.md",
        summary="Adaptive chunker and vector_index architecture",
    )
    assert res_data.pp == "30"
    assert res_data.project_name == "DATA_INTELLIGENCE"

    res_field = resolver.resolve_project_affinity(
        filepath="site_inspection_fieldwork_notes.pdf",
        summary="Usability study and artifact_survey field notes",
    )
    assert res_field.pp == "40"
    assert res_field.project_name == "FIELD_RESEARCH"

    res_sec = resolver.resolve_project_affinity(
        filepath="CLI_Harness_Security_Gate_Threat_Scenario.jpg",
        summary="Social engineering threat_scenario and security_gate review",
    )
    assert res_sec.pp == "60"
    assert res_sec.project_name == "DEV_EXPERIENCE"


def test_jd_registry_auto_discovery(mock_projects_root, tmp_path):
    """Verify jd_registry load_registry and resolve_project_for_file integration."""
    reg_path = tmp_path / "registry.json"
    registry = load_registry(path=reg_path, projects_root=mock_projects_root)

    assert "10" in registry["projects"]
    assert "20" in registry["projects"]

    pp, name, tags = resolve_project_for_file(
        filepath="ProductPlatform_Curriculum_Draft.md",
        content_summary="ProductPlatform onboarding modules",
        registry=registry,
    )
    assert pp == "10"
    assert name == "PRODUCT_PLATFORM"


def test_langgraph_workflow_compilation_and_execution(tmp_path, mock_projects_root):
    """Verify end-to-end execution of the typed LangGraph StateGraph workflow."""
    input_dir = tmp_path / "incoming_files"
    input_dir.mkdir()
    (input_dir / "ProductPlatform_Test_Doc.docx").write_text(
        "ProductPlatform roadmap content", encoding="utf-8"
    )
    (input_dir / "CloudInfra_Kubernetes_Audit.pdf").write_text(
        "kubernetes terraform deployment", encoding="utf-8"
    )

    job_dir = tmp_path / "job_run"

    graph = build_document_organizer_graph()
    initial_state = {
        "target_dir": str(input_dir),
        "job_dir": str(job_dir),
        "projects_root": str(mock_projects_root),
        "dry_run": True,
    }

    final_state = graph.invoke(initial_state)

    assert len(final_state.get("scanned_files", [])) == 2
    assert "traceability_matches" in final_state
    assert len(final_state.get("tasks_plan", {}).get("rename", [])) == 2

    renames = final_state["tasks_plan"]["rename"]
    platform_task = next(r for r in renames if "ProductPlatform" in r["src"])
    infra_task = next(r for r in renames if "CloudInfra" in r["src"])

    assert "10" in platform_task["dest_folder"]
    assert "20" in infra_task["dest_folder"]
    assert (job_dir / "tasks.json").exists()


def test_ssot_destination_routing(mock_projects_root, tmp_path):
    """Verify that external intake files are routed to the monorepo SSOT rather than local pseudo-folders."""
    (mock_projects_root / "10_PRODUCT_PLATFORM" / "30_REFERENCE").mkdir(
        parents=True, exist_ok=True
    )

    resolver = TraceabilityContextResolver(projects_root=mock_projects_root)
    match_platform = resolver.resolve_project_affinity(
        filepath="ProductPlatform_Curriculum_2026.docx",
        summary="ProductPlatform curriculum roadmap",
    )

    external_desktop = tmp_path / "Desktop"
    external_desktop.mkdir()
    ssot_dest = resolver.resolve_ssot_destination(
        match=match_platform,
        target_path=external_desktop,
        default_cluster_folder="10_PRODUCT_PLATFORM",
    )
    assert str(mock_projects_root / "10_PRODUCT_PLATFORM" / "30_REFERENCE") in ssot_dest

    internal_proj_dir = mock_projects_root / "10_PRODUCT_PLATFORM" / "00_INBOX"
    internal_dest = resolver.resolve_ssot_destination(
        match=match_platform,
        target_path=internal_proj_dir,
        default_cluster_folder="30_REFERENCE",
    )
    assert internal_dest == "30_REFERENCE"
