"""
test_naming_normalizer.py — Unit tests for naming normalizer and generated assets governance.

Implements: UC-001
Traces: FR-ORG-08, FR-ORG-09
Verifies: TC-ORG-NORM-01, TC-ORG-NORM-02
"""

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts.naming_normalizer import (
    NamingNormalizer,
    normalize_name,
    remove_vietnamese_diacritics,
)


def test_remove_vietnamese_diacritics():
    vietnamese = "Bản đồ công nghệ điểm đến du lịch"
    ascii_res = remove_vietnamese_diacritics(vietnamese)
    assert ascii_res == "Ban do cong nghe diem den du lich"
    assert all(ord(c) < 128 for c in ascii_res)

    folder = "CUM_06_AM_THUC_LƯU_TRU_ROOFTOP_T4_T5"
    folder_ascii = remove_vietnamese_diacritics(folder)
    assert folder_ascii == "CUM_06_AM_THUC_LUU_TRU_ROOFTOP_T4_T5"
    assert all(ord(c) < 128 for c in folder_ascii)


def test_normalize_directory_name():
    raw_dir = "CUM_06_AM_THUC_LƯU_TRU_ROOFTOP_T4_T5"
    normalized = normalize_name(raw_dir, is_directory=True)
    assert normalized == "CUM_06_AM_THUC_LUU_TRU_ROOFTOP_T4_T5"
    assert all(ord(c) < 128 for c in normalized)
    assert " " not in normalized


def test_normalize_filenames():
    f1 = "Bản đồ công nghệ điểm đến du lịch.docx"
    assert normalize_name(f1) == "ban_do_cong_nghe_diem_den_du_lich.docx"

    f2 = "tong quan tai lieu eureka (1).docx"
    assert normalize_name(f2) == "tong_quan_tai_lieu_eureka_v1.docx"

    f3 = "yếu tố ảnh hưởng CDS doanh nghiệp du lịch.pdf"
    assert normalize_name(f3) == "yeu_to_anh_huong_cds_doanh_nghiep_du_lich.pdf"

    f4 = "3.Eureka_BC NCKH SV 2025_BVQSH TSVH.docx"
    assert normalize_name(f4) == "3_eureka_bc_nckh_sv_2025_bvqsh_tsvh.docx"


def test_naming_normalizer_lint_and_misplaced(tmp_path: Path):
    normalizer = NamingNormalizer(tmp_path)

    bad_file = tmp_path / "Bản đồ công nghệ.docx"
    violations = normalizer.lint_path(bad_file)
    assert "NON_ASCII_DIACRITICS" in violations
    assert "CONTAINS_WHITESPACE" in violations


