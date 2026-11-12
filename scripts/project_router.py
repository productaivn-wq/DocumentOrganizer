
"""
project_router.py — Intelligent project workspace and MECE lifecycle zone router.

Implements: UC-001
Traces: FR-ORG-04, FR-ORG-05
Verifies: TC-ORG-ROUTER-01

Routes documents and multimedia assets to the correct project workspace
and MECE zone based on keyword taxonomy, task associations, and content clues.
Enforces the Zero Desktop Invariant and Single Source of Truth (SSOT) architecture.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from .logger import setup_logger
except ImportError:
    from logger import setup_logger

logger = setup_logger("DocumentOrganizer.ProjectRouter")

DEFAULT_PROJECT_BASE = Path(os.environ.get("WORKSPACE_PROJECTS_ROOT", str(Path.home() / "Projects")))

VALID_MECE_ZONES: set[str] = {
    "00_INBOX",
    "10_ACTIVE_TIMEBOUND",
    "20_ACTIVE_CONTINUOUS",
    "30_REFERENCE",
    "40_ARCHIVE",
}


def sanitize_mece_zone(zone: Path | str, default_category: str = "docs") -> Path:
    """Sanitizes and enforces that relative zone path strictly resides in a valid MECE zone.

    If a legacy or non-MECE path is supplied (e.g. 'docs', 'data/photos', 'media'),
    it is mapped into '20_ACTIVE_CONTINUOUS/<category>'.
    """
    p = Path(zone)
    parts = p.parts
    if not parts:
        return Path("20_ACTIVE_CONTINUOUS") / default_category

    top = parts[0]
    if top in VALID_MECE_ZONES:
        return p

    # Remap non-MECE legacy directories into 20_ACTIVE_CONTINUOUS
    if top in ("docs", "doc"):
        return Path("20_ACTIVE_CONTINUOUS/docs") / Path(*parts[1:])
    elif top in ("photos", "photo", "images", "assets"):
        return Path("20_ACTIVE_CONTINUOUS/media/photos") / Path(*parts[1:])
    elif top in ("media", "videos", "recordings"):
        return Path("20_ACTIVE_CONTINUOUS/media") / Path(*parts[1:])
    elif top in ("data", "datasets"):
        return Path("20_ACTIVE_CONTINUOUS/data") / Path(*parts[1:])

    return Path("20_ACTIVE_CONTINUOUS") / p


# Curated rich domain profiles with extensive keyword dictionaries
CURATED_PROFILES: list[dict[str, Any]] = [
    {
        "name": "10_PRODUCT_PLATFORM",
        "keywords": [
            "product platform",
            "product_platform",
            "roadmap",
            "prd",
            "curriculum",
            "onboarding",
            "release notes",
            "api gateway",
        ],
        "photo_zone": Path("20_ACTIVE_CONTINUOUS/media/photos"),
        "doc_zone": Path("20_ACTIVE_CONTINUOUS/docs"),
        "data_zone": Path("20_ACTIVE_CONTINUOUS/data"),
        "media_zone": Path("20_ACTIVE_CONTINUOUS/media"),
    },
    {
        "name": "20_CLOUD_INFRASTRUCTURE",
        "keywords": [
            "cloud infrastructure",
            "kubernetes",
            "terraform",
            "deployment",
            "observability",
            "runbook",
            "postmortem",
        ],
        "photo_zone": Path("20_ACTIVE_CONTINUOUS/media/photos"),
        "doc_zone": Path("20_ACTIVE_CONTINUOUS/docs"),
        "data_zone": Path("20_ACTIVE_CONTINUOUS/data"),
        "media_zone": Path("20_ACTIVE_CONTINUOUS/media"),
    },
    {
        "name": "30_DATA_INTELLIGENCE",
        "keywords": [
            "data intelligence",
            "chunker",
            "adaptive chunking",
            "adaptive chunker",
            "knowledge graph",
            "rag pipeline",
            "rag diagram",
            "vector search",
        ],
        "photo_zone": Path("20_ACTIVE_CONTINUOUS/media/photos"),
        "doc_zone": Path("20_ACTIVE_CONTINUOUS/docs"),
        "data_zone": Path("20_ACTIVE_CONTINUOUS/data"),
        "media_zone": Path("20_ACTIVE_CONTINUOUS/media"),
    },
    {
        "name": "40_FIELD_RESEARCH",
        "keywords": [
            "field research",
            "heritage craft",
            "artifact survey",
            "fieldwork",
            "site survey",
            "survey photo",
            "usability lab",
            "gate screen",
            "ticket booth",
        ],
        "photo_zone": Path("20_ACTIVE_CONTINUOUS/data/fieldwork_photos"),
        "doc_zone": Path("20_ACTIVE_CONTINUOUS/docs"),
        "data_zone": Path("20_ACTIVE_CONTINUOUS/data"),
        "media_zone": Path("20_ACTIVE_CONTINUOUS/data/fieldwork_videos"),
    },
    {
        "name": "50_FLEET_OPERATIONS",
        "keywords": [
            "fleet operations",
            "maritime",
            "vessel",
            "hull inspection",
            "hull cleaning",
            "marina",
            "shipyard",
            "warranty",
            "aftersales",
            "mro",
            "engine maintenance",
        ],
        "photo_zone": Path("20_ACTIVE_CONTINUOUS/media/photos"),
        "doc_zone": Path("20_ACTIVE_CONTINUOUS/docs"),
        "data_zone": Path("20_ACTIVE_CONTINUOUS/data"),
        "media_zone": Path("20_ACTIVE_CONTINUOUS/media"),
    },
    {
        "name": "60_DEV_EXPERIENCE",
        "keywords": [
            "dev experience",
            "developer portal",
            "cli harness",
            "workspace demo",
            "screen capture",
            "automation walkthrough",
            "governance",
        ],
        "photo_zone": Path("20_ACTIVE_CONTINUOUS/media/photos"),
        "doc_zone": Path("20_ACTIVE_CONTINUOUS/docs"),
        "data_zone": Path("20_ACTIVE_CONTINUOUS/data"),
        "media_zone": Path("20_ACTIVE_CONTINUOUS/media"),
    },
]

# Backward-compatibility alias
PROJECT_PROFILES = CURATED_PROFILES


GENERIC_STOPWORDS: set[str] = {
    "file",
    "files",
    "skill",
    "skills",
    "tool",
    "tools",
    "repo",
    "module",
    "shared",
    "core",
    "project",
    "projects",
    "docs",
    "doc",
    "data",
    "management",
    "public",
    "from",
    "knowledge",
    "app",
    "code",
    "dev",
    "test",
    "tests",
}


@dataclass
class ProjectRoute:
    project_name: str
    project_path: Path
    relative_zone_path: Path
    target_full_path: Path
    standardized_filename: str
    confidence: float
    matched_rule: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["project_path"] = str(self.project_path)
        d["relative_zone_path"] = str(self.relative_zone_path)
        d["target_full_path"] = str(self.target_full_path)
        return d


def _score_discrete_choice_profile(
    query: str, profiles: list[dict[str, Any]]
) -> tuple[dict[str, Any], float] | None:
    """Evaluates project profiles using deterministic token-overlap discrete-choice scoring.

    Confidence invariant: top score >= 0.65 and margin >= 0.20 over runner-up.
    """
    if not query or not profiles:
        return None

    def _norm(text: str) -> str:
        nfkd = unicodedata.normalize("NFKD", text.lower())
        return (
            "".join(c for c in nfkd if not unicodedata.combining(c))
            .replace("đ", "d")
            .replace("_", " ")
            .replace("-", " ")
        )

    norm_query = _norm(query)
    q_tokens = {t for t in re.findall(r"[a-z0-9]{3,}", norm_query) if t not in GENERIC_STOPWORDS}
    if not q_tokens:
        return None

    scored: list[tuple[float, dict[str, Any]]] = []
    for p in profiles:
        kws = [_norm(k) for k in p.get("keywords", [])]
        phrase_hits = sum(1 for k in kws if k and k in norm_query)
        p_tokens = {
            t
            for k in kws
            for t in re.findall(r"[a-z0-9]{3,}", k)
            if t not in GENERIC_STOPWORDS
        }
        overlap = len(q_tokens & p_tokens)
        if phrase_hits == 0 and overlap == 0:
            scored.append((0.0, p))
            continue
        raw = min(0.98, 0.45 + 0.22 * phrase_hits + 0.12 * overlap)
        scored.append((raw, p))

    scored.sort(key=lambda item: item[0], reverse=True)
    top_score, top_profile = scored[0]
    runner_up_score = scored[1][0] if len(scored) > 1 else 0.0

    if top_score >= 0.65 and (top_score - runner_up_score) >= 0.20:
        return top_profile, top_score
    return None


class ProjectRouter:
    """Matches files and multimedia assets to active project repositories following MECE SSOT."""

    def __init__(self, workspace_base: Path | str | None = None) -> None:
        if workspace_base:
            self.workspace_base = Path(workspace_base).resolve()
        elif DEFAULT_PROJECT_BASE.exists():
            self.workspace_base = DEFAULT_PROJECT_BASE.resolve()
        else:
            self.workspace_base = Path.cwd().resolve()

        self.profiles: list[dict[str, Any]] = self._build_profiles()

    def _build_profiles(self) -> list[dict[str, Any]]:
        """Dynamically builds complete project catalog combining portfolio manifest and curated domain profiles."""
        profile_map: dict[str, dict[str, Any]] = {}

        # 1. Discover all projects from portfolio_manifest.json or workspace directory scan
        manifest_path = self.workspace_base / "portfolio_manifest.json"
        if not manifest_path.exists() and DEFAULT_PROJECT_BASE.exists():
            manifest_path = DEFAULT_PROJECT_BASE / "portfolio_manifest.json"

        discovered_names: set[str] = set()
        if manifest_path.exists():
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                for p_name in data.get("projects", {}).keys():
                    discovered_names.add(p_name)
            except Exception as e:
                logger.warning("Failed to parse portfolio_manifest.json: %s", e)

        # Directory inspection fallback / augment
        if self.workspace_base.exists() and self.workspace_base.is_dir():
            for child in self.workspace_base.iterdir():
                if child.is_dir() and re.match(r"^\d+_[A-Z0-9_]+$", child.name):
                    discovered_names.add(child.name)

        # 2. Build default MECE profile for every discovered project
        for name in discovered_names:
            clean_name = re.sub(r"^\d+_", "", name).lower()
            tokens = [
                t
                for t in re.split(r"[-_]+", clean_name)
                if len(t) >= 4 and t not in GENERIC_STOPWORDS
            ]
            keywords = [clean_name.replace("_", " ")] + tokens

            profile_map[name] = {
                "name": name,
                "keywords": list(set(keywords)),
                "photo_zone": Path("20_ACTIVE_CONTINUOUS/media/photos"),
                "doc_zone": Path("20_ACTIVE_CONTINUOUS/docs"),
                "data_zone": Path("20_ACTIVE_CONTINUOUS/data"),
                "media_zone": Path("20_ACTIVE_CONTINUOUS/media"),
            }

        # 3. Layer curated profiles with rich domain-specific keywords and zone overrides
        for curated in CURATED_PROFILES:
            c_name = curated["name"]
            if c_name in profile_map:
                existing_kw = set(profile_map[c_name]["keywords"])
                existing_kw.update(curated["keywords"])
                profile_map[c_name]["keywords"] = list(existing_kw)
                profile_map[c_name]["photo_zone"] = sanitize_mece_zone(
                    curated.get(
                        "photo_zone", Path("20_ACTIVE_CONTINUOUS/media/photos")
                    ),
                    "media/photos",
                )
                profile_map[c_name]["doc_zone"] = sanitize_mece_zone(
                    curated.get("doc_zone", Path("20_ACTIVE_CONTINUOUS/docs")), "docs"
                )
                profile_map[c_name]["data_zone"] = sanitize_mece_zone(
                    curated.get("data_zone", Path("20_ACTIVE_CONTINUOUS/data")), "data"
                )
                profile_map[c_name]["media_zone"] = sanitize_mece_zone(
                    curated.get("media_zone", Path("20_ACTIVE_CONTINUOUS/media")),
                    "media",
                )
            else:
                c_copy = dict(curated)
                c_copy["photo_zone"] = sanitize_mece_zone(
                    curated.get(
                        "photo_zone", Path("20_ACTIVE_CONTINUOUS/media/photos")
                    ),
                    "media/photos",
                )
                c_copy["doc_zone"] = sanitize_mece_zone(
                    curated.get("doc_zone", Path("20_ACTIVE_CONTINUOUS/docs")), "docs"
                )
                c_copy["data_zone"] = sanitize_mece_zone(
                    curated.get("data_zone", Path("20_ACTIVE_CONTINUOUS/data")), "data"
                )
                c_copy["media_zone"] = sanitize_mece_zone(
                    curated.get("media_zone", Path("20_ACTIVE_CONTINUOUS/media")),
                    "media",
                )
                profile_map[c_name] = c_copy

        return list(profile_map.values())

    def standardize_filename(self, filename: str, index: int | None = None) -> str:
        """Sanitize filename into standard clean snake_case, stripping accents."""
        p = Path(filename)
        nfkd = unicodedata.normalize("NFKD", p.stem)
        clean = (
            "".join(c for c in nfkd if not unicodedata.combining(c))
            .replace("đ", "d")
            .replace("Đ", "D")
        )
        stem = clean.lower()
        suffix = p.suffix.lower()

        clean_stem = re.sub(r"[^\w\-]+", "_", stem).strip("_")
        clean_stem = re.sub(r"_+", "_", clean_stem)

        if index is not None and not clean_stem.startswith("img_"):
            return f"img_{index:02d}_{clean_stem}{suffix}"
        elif index is not None:
            return f"{clean_stem}{suffix}"

        return f"{clean_stem}{suffix}"

    def resolve_destination(
        self,
        filename: str,
        source_dir_name: str = "",
        content_hint: str = "",
        seq_index: int | None = None,
    ) -> ProjectRoute | None:
        # Formulate search corpus with spaces in place of punctuation
        spaced_name = re.sub(r"[-_.]+", " ", filename).lower()
        combined_text = (
            f"{filename} {spaced_name} {source_dir_name} {content_hint}".lower()
        )
        nfkd = unicodedata.normalize("NFKD", combined_text)
        unaccented_text = (
            "".join(c for c in nfkd if not unicodedata.combining(c))
            .replace("đ", "d")
            .replace("Đ", "D")
        )
        search_corpus = f"{combined_text} {unaccented_text}"

        suffix = Path(filename).suffix.lower()
        is_image = suffix in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".bmp",
            ".tiff",
            ".heic",
        }
        is_video = suffix in {
            ".mp4",
            ".mkv",
            ".mov",
            ".webm",
            ".avi",
        }
        is_audio = suffix in {
            ".m4a",
            ".mp3",
            ".wav",
            ".aac",
            ".flac",
        }
        is_media = is_video or is_audio

        best_match: dict[str, Any] | None = None
        best_score = 0
        matched_keyword = ""

        for profile in self.profiles:
            score = 0
            for kw in profile["keywords"]:
                kw_lower = kw.lower()
                if kw_lower in search_corpus:
                    # Give higher priority to multi-word phrases and filename occurrences
                    weight = 3 if (" " in kw_lower or len(kw_lower) >= 6) else 1
                    if kw_lower in filename.lower() or kw_lower in spaced_name:
                        weight *= 2
                    score += len(kw_lower) * weight
                    if score > best_score:
                        matched_keyword = kw
            if score > best_score:
                best_score = score
                best_match = profile

        std_name = self.standardize_filename(filename, index=seq_index)

        # FR-ORG-13: Discrete-choice profile fallback scoring
        if not best_match or best_score < 8:
            choice_match = _score_discrete_choice_profile(search_corpus, self.profiles)
            if choice_match:
                best_match, choice_confidence = choice_match
                matched_keyword = (
                    f"DiscreteChoiceScorer (prob={choice_confidence:.4f})"
                )
                best_score = int(choice_confidence * 25)

        # Require a minimum score threshold of 8 to avoid noisy false positives
        if not best_match or best_score < 8:
            # Fallback strictly to 00_INBOX inside workspace base to maintain MECE compliance
            work_root = (
                self.workspace_base.parent
                if self.workspace_base.name == "01_PROJECTS"
                else self.workspace_base
            )
            zone = Path("00_INBOX")
            target_path = work_root / zone / std_name
            return ProjectRoute(
                project_name="_GENERAL_INBOX",
                project_path=work_root,
                relative_zone_path=zone,
                target_full_path=target_path,
                standardized_filename=std_name,
                confidence=0.3,
                matched_rule="Fallback to 00_INBOX staging",
            )

        project_dir = self.workspace_base / best_match["name"]
        if is_media:
            zone = best_match.get("media_zone", Path("20_ACTIVE_CONTINUOUS/media"))
        elif is_image:
            zone = best_match.get(
                "photo_zone", Path("20_ACTIVE_CONTINUOUS/media/photos")
            )
        else:
            zone = best_match.get("doc_zone", Path("20_ACTIVE_CONTINUOUS/docs"))

        # Invariant Guard: Assert zone strictly starts with a valid MECE lifecycle zone
        zone = sanitize_mece_zone(zone)
        target_path = project_dir / zone / std_name
        confidence = min(1.0, 0.5 + (best_score / 30.0))

        return ProjectRoute(
            project_name=best_match["name"],
            project_path=project_dir,
            relative_zone_path=zone,
            target_full_path=target_path,
            standardized_filename=std_name,
            confidence=confidence,
            matched_rule=f"Matched profile '{best_match['name']}' on keyword '{matched_keyword}' (score={best_score})",
        )

    def review_and_refile_inbox_candidates(
        self,
        newly_filed_project_name: str,
        inbox_dir: Path | None = None,
        max_candidates: int = 10,
        min_similarity: float = 0.70,
    ) -> list[dict[str, Any]]:
        """FR-ORG-14: Autonomous Library Custodian post-filing re-evaluation.
        When a file is placed into a project, inspects unfiled loose files in 00_INBOX.
        If any loose file matches the newly targeted project with similarity >= min_similarity (default 0.70),
        it evaluates and recommends/executes re-filing into the destination project MECE zone.
        """
        if inbox_dir is None:
            work_root = (
                self.workspace_base.parent
                if self.workspace_base.name == "01_PROJECTS"
                else self.workspace_base
            )
            inbox_dir = work_root / "00_INBOX"

        if not inbox_dir.exists() or not inbox_dir.is_dir():
            return []

        # Find target profile
        target_profile = next(
            (p for p in self.profiles if p["name"] == newly_filed_project_name), None
        )
        if not target_profile:
            return []

        loose_files = [
            f for f in inbox_dir.iterdir() if f.is_file() and not f.name.startswith(".")
        ][:max_candidates]
        re_filed_proposals = []

        for candidate_file in loose_files:
            hint = ""
            try:
                # Read first 500 chars if text
                if candidate_file.suffix.lower() in {".md", ".txt", ".json", ".csv"}:
                    hint = candidate_file.read_text(encoding="utf-8", errors="replace")[
                        :500
                    ]
            except Exception:
                pass

            # Score using discrete-choice profile matcher
            combined = f"{candidate_file.name} {hint}".strip()
            choice_match = _score_discrete_choice_profile(combined, [target_profile])
            route = self.resolve_destination(candidate_file.name, content_hint=hint)
            prob = choice_match[1] if choice_match else (route.confidence if route else 0.0)
            if (
                route
                and route.project_name == newly_filed_project_name
                and prob >= min_similarity
            ):
                re_filed_proposals.append(
                    {
                        "source_file": str(candidate_file),
                        "target_project": newly_filed_project_name,
                        "target_path": str(route.target_full_path),
                        "confidence": prob,
                        "rule": "Autonomous Custodian Post-Filing Re-evaluation (FR-ORG-14)",
                    }
                )

        return re_filed_proposals
