"""
Adversarial and boundary edge-case tests for DocumentOrganizer.

Protects against path traversal attacks, malformed filenames, and fuzz payloads.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from core.traceability_resolver import TraceabilityResolver
from scripts.depth_policy import normalize_exception
from scripts.desktop_scanner import DesktopScanner
from scripts.naming_normalizer import normalize_name


def test_path_traversal_exception_normalization(tmp_path: Path):
    """Assert path traversal payload raises ValueError."""
    malicious_inputs = [
        "../../etc/passwd",
        "../../windows/system32/cmd.exe",
        "..\\..\\boot.ini",
        "10_ACTIVE_TIMEBOUND/../../../escape",
    ]
    for bad_input in malicious_inputs:
        with pytest.raises(ValueError):
            normalize_exception(tmp_path, bad_input)


def test_fuzz_filenames_in_normalization():
    """Assert organizer naming normalizer handles extremely long and unusual characters safely."""
    fuzz_filenames = [
        "A" * 300 + ".md",
        "\x00\x01\x02_test.txt",
        "??**<<>>||::.doc",
        "emoji_🚀_test_sprint.md",
        "___---...---___",
    ]
    for fname in fuzz_filenames:
        normalized = normalize_name(fname)
        assert isinstance(normalized, str)
        assert len(normalized) > 0


def test_traceability_resolver_adversarial_text():
    """Assert resolver gracefully handles massive strings and code injection attempts."""
    malicious_summary = "'; DROP TABLE documents; --" * 100 + " UC-001 FR-002 TC-003"
    tag = TraceabilityResolver.parse_text(malicious_summary)
    assert "001" in tag.use_cases
    assert "002" in tag.functional_reqs
    assert "003" in tag.test_cases

    overflow_summary = "A" * 50000 + " UC-004"
    tag2 = TraceabilityResolver.parse_text(overflow_summary)
    assert "004" in tag2.use_cases


def test_desktop_scanner_adversarial_extensions():
    """Assert desktop scanner handles abnormal file paths and extensions gracefully."""
    scanner = DesktopScanner()
    assert scanner.classify(Path(".hidden")) == "misc"
    assert scanner.classify(Path("file.unknown_extension_xyz_123")) == "misc"
    assert scanner.classify(Path("file.PDF")) == "documents"
    assert scanner.classify(Path("script.PY")) == "code"
