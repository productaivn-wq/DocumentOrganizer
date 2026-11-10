"""Traceability resolver and monorepo project context resolution for DocumentOrganizer.

Implements semantic project affinity matching, Johnny Decimal integration,
and bi-directional requirement-to-artifact traceability mapping.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProjectAffinityMatch:
    """Represents a matched project affinity outcome for a given document."""

    pp: str
    project_name: str
    confidence: float = 1.0
    matched_keywords: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class TraceabilityTag:
    """Parsed traceability tags from document text or summary."""

    use_cases: list[str] = field(default_factory=list)
    functional_reqs: list[str] = field(default_factory=list)
    test_cases: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    designs: list[str] = field(default_factory=list)
    specs: list[str] = field(default_factory=list)
    tasks: list[str] = field(default_factory=list)
    raw_references: dict[str, list[str]] = field(default_factory=dict)


# Fallback semantic keyword mappings for well-known projects in the monorepo taxonomy
_KNOWN_PROJECT_PATTERNS = [
    {
        "pp": "10",
        "name": "PRODUCT_PLATFORM",
        "keywords": [
            "product_platform",
            "productplatform",
            "product platform",
            "roadmap",
            "curriculum",
            "prd",
            "onboarding",
        ],
    },
    {
        "pp": "20",
        "name": "CLOUD_INFRASTRUCTURE",
        "keywords": [
            "cloud_infrastructure",
            "cloudinfra",
            "kubernetes",
            "terraform",
            "deployment",
            "sre",
            "incident_audit",
        ],
    },
    {
        "pp": "30",
        "name": "DATA_INTELLIGENCE",
        "keywords": [
            "data_intelligence",
            "knowledge_graph",
            "adaptive_chunker",
            "rag_pipeline",
            "vector_index",
            "analytics_spec",
        ],
    },
    {
        "pp": "40",
        "name": "FIELD_RESEARCH",
        "keywords": [
            "field_research",
            "fieldwork",
            "artifact_survey",
            "site_inspection",
            "usability_study",
        ],
    },
    {
        "pp": "50",
        "name": "FLEET_OPERATIONS",
        "keywords": [
            "fleet_operations",
            "vessel",
            "hull_inspection",
            "maintenance_checklist",
            "warranty",
            "aftersales",
        ],
    },
    {
        "pp": "60",
        "name": "DEV_EXPERIENCE",
        "keywords": [
            "dev_experience",
            "cli_harness",
            "workspace_hygiene",
            "security_gate",
            "threat_scenario",
            "social_engineering",
        ],
    },
]


class TraceabilityContextResolver:
    """Discovers monorepo projects and resolves semantic project affinity for document files."""

    def __init__(
        self,
        projects_root: Path | str | None = None,
        registry_path: Path | str | None = None,
    ):
        self.projects_root = Path(projects_root).resolve() if projects_root else None
        self.registry_path = Path(registry_path).resolve() if registry_path else None
        self.projects_registry: dict[str, dict[str, Any]] = {}
        self._discover_projects()

    def _discover_projects(self) -> None:
        """Scan projects_root for PP_NAME project directories."""
        if not self.projects_root or not self.projects_root.exists():
            # Populate with baseline known projects if root does not exist
            for proj in _KNOWN_PROJECT_PATTERNS:
                self.projects_registry[proj["pp"]] = {
                    "pp": proj["pp"],
                    "name": proj["name"],
                    "folder": f"{proj['pp']}_{proj['name']}",
                    "path": "",
                }
            return

        for entry in self.projects_root.iterdir():
            if entry.is_dir():
                match = re.match(r"^(\d{2})_(.+)$", entry.name)
                if match:
                    pp = match.group(1)
                    name = match.group(2)
                    self.projects_registry[pp] = {
                        "pp": pp,
                        "name": name,
                        "folder": entry.name,
                        "path": str(entry.resolve()),
                    }

    def resolve_project_affinity(
        self,
        filepath: Path | str,
        summary: str = "",
        content: str = "",
    ) -> ProjectAffinityMatch:
        """Resolve semantic project affinity for a document based on name and summary content."""
        filename = Path(filepath).name
        search_blob = f"{filename} {summary} {content}".lower()

        # 1. Check known explicit pattern taxonomy
        for pat in _KNOWN_PROJECT_PATTERNS:
            matched_kws = [kw for kw in pat["keywords"] if kw in search_blob]
            if matched_kws:
                pp = pat["pp"]
                # Resolve name from discovered registry if present, else pattern name
                reg_entry = self.projects_registry.get(pp)
                proj_name = reg_entry["name"] if reg_entry else pat["name"]
                confidence = (
                    0.90
                    if len(matched_kws) > 1
                    or filename.lower().startswith(pat["name"].lower())
                    else 0.75
                )
                return ProjectAffinityMatch(
                    pp=pp,
                    project_name=proj_name,
                    confidence=confidence,
                    matched_keywords=matched_kws,
                    reason=f"Matched keywords: {matched_kws}",
                )

        # 2. Check discovered projects registry
        for pp, info in self.projects_registry.items():
            name = info.get("name", "")
            if name and name.lower() in search_blob:
                return ProjectAffinityMatch(
                    pp=pp,
                    project_name=name,
                    confidence=0.80,
                    matched_keywords=[name.lower()],
                    reason=f"Matched project name: {name}",
                )

        # 3. Check for numeric prefix in filename (e.g., 11.001 - ...)
        num_match = re.match(r"^(\d{2})[\._]", filename)
        if num_match and num_match.group(1) in self.projects_registry:
            pp = num_match.group(1)
            name = self.projects_registry[pp]["name"]
            return ProjectAffinityMatch(
                pp=pp,
                project_name=name,
                confidence=0.95,
                matched_keywords=[pp],
                reason=f"Matched prefix {pp}",
            )

        # Fallback to uncategorized / root inbox
        return ProjectAffinityMatch(
            pp="00",
            project_name="INBOX",
            confidence=0.10,
            matched_keywords=[],
            reason="No affinity pattern matched",
        )

    def resolve_ssot_destination(
        self,
        match: ProjectAffinityMatch,
        target_path: Path | str,
        default_cluster_folder: str = "",
    ) -> str:
        """Route external intake documents to Monorepo SSOT or preserve internal folders.

        If target_path is external (not located inside the project), route to Monorepo SSOT
        ({projects_root}/{pp}_{project_name}/30_REFERENCE).
        If target_path is already inside the project, preserve default_cluster_folder.
        """
        target = Path(target_path).resolve()
        if not self.projects_root:
            return default_cluster_folder

        proj_entry = self.projects_registry.get(match.pp)
        proj_folder_name = (
            proj_entry["folder"] if proj_entry else f"{match.pp}_{match.project_name}"
        )
        proj_dir = (self.projects_root / proj_folder_name).resolve()

        # Check if target is inside the project directory
        try:
            target.relative_to(proj_dir)
            is_internal = True
        except ValueError:
            is_internal = False

        if is_internal:
            return default_cluster_folder

        # External intake: route to project SSOT
        ref_dir = proj_dir / "30_REFERENCE"
        if ref_dir.exists():
            return str(ref_dir)
        cluster_dir = proj_dir / default_cluster_folder
        if cluster_dir.exists():
            return str(cluster_dir)
        return str(ref_dir)


class TraceabilityResolver:
    """Extracts and resolves bi-directional traceability references between documents."""

    def __init__(self, custom_patterns: dict[str, re.Pattern] | None = None):
        self.patterns: dict[str, re.Pattern] = custom_patterns or {
            "requirement": re.compile(
                r"@(?:req|requirement)\s+([A-Za-z0-9_.\-]+)", re.IGNORECASE
            ),
            "design": re.compile(
                r"@(?:design|arch)\s+([A-Za-z0-9_.\-]+)", re.IGNORECASE
            ),
            "test": re.compile(r"@(?:test|tc)\s+([A-Za-z0-9_.\-]+)", re.IGNORECASE),
            "spec": re.compile(r"@spec\s+([A-Za-z0-9_.\-]+)", re.IGNORECASE),
            "task": re.compile(r"@task\s+([A-Za-z0-9_.\-]+)", re.IGNORECASE),
        }

    @classmethod
    def parse_text(cls, text: str) -> TraceabilityTag:
        """Safely parse traceability tags from arbitrary text, immune to injection and overflow."""
        if not text or not isinstance(text, str):
            return TraceabilityTag()

        # Extract UC references (e.g. UC-001, UC_001)
        uc_matches = re.findall(r"\bUC[-_]?([A-Za-z0-9_.\-]+)", text, re.IGNORECASE)
        # Extract FR references (e.g. FR-002, FR_002)
        fr_matches = re.findall(r"\bFR[-_]?([A-Za-z0-9_.\-]+)", text, re.IGNORECASE)
        # Extract TC references (e.g. TC-003, TC_003)
        tc_matches = re.findall(r"\bTC[-_]?([A-Za-z0-9_.\-]+)", text, re.IGNORECASE)

        def _dedup(items: list[str]) -> list[str]:
            seen: set[str] = set()
            return [x for x in items if not (x in seen or seen.add(x))]

        inst = cls()
        annotated = inst.extract_references(text)

        return TraceabilityTag(
            use_cases=_dedup(uc_matches),
            functional_reqs=_dedup(fr_matches),
            test_cases=_dedup(tc_matches),
            requirements=annotated.get("requirement", []),
            designs=annotated.get("design", []),
            specs=annotated.get("spec", []),
            tasks=annotated.get("task", []),
            raw_references=annotated,
        )

    def extract_references(self, content: str) -> dict[str, list[str]]:
        """Extract all traceability references from text content without duplicates."""
        references: dict[str, list[str]] = {}
        for ref_type, pattern in self.patterns.items():
            matches = pattern.findall(content)
            if matches:
                # Deduplicate while preserving original appearance order
                seen: set[str] = set()
                deduped = [m for m in matches if not (m in seen or seen.add(m))]
                references[ref_type] = deduped
        return references

    def resolve_traceability(
        self, documents: dict[str, str]
    ) -> dict[str, dict[str, list[str]]]:
        """Resolve traceability references across a collection of document contents."""
        traceability_map: dict[str, dict[str, list[str]]] = {}
        for doc_id, content in documents.items():
            refs = self.extract_references(content)
            if refs:
                traceability_map[doc_id] = refs
        return traceability_map

    def find_document_links(
        self,
        doc_id: str,
        traceability_map: dict[str, dict[str, list[str]]],
    ) -> list[tuple[str, str, str]]:
        """Find all incoming and outgoing 3-tuple links (source, target, ref_type) for doc_id."""
        links: list[tuple[str, str, str]] = []

        # Outgoing links from this document
        if doc_id in traceability_map:
            for ref_type, ref_ids in traceability_map[doc_id].items():
                for ref_id in ref_ids:
                    links.append((doc_id, ref_id, ref_type))

        # Incoming links from other documents targeting this document
        for other_id, refs in traceability_map.items():
            if other_id == doc_id:
                continue
            for ref_type, ref_ids in refs.items():
                if doc_id in ref_ids:
                    links.append((other_id, doc_id, ref_type))

        return links
