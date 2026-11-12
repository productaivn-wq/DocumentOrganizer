"""
photo_ingest.py — Multimedia and photo ingestion engine for DocumentOrganizer.

Implements: UC-001
Traces: FR-ORG-02, FR-ORG-05
Verifies: TC-ORG-PHOTO-01

Extracts image metadata (dimensions, format, SHA-256, capture timestamp, EXIF)
with graceful pure-Python binary parsing fallback if Pillow is absent.
"""

from __future__ import annotations

import datetime
import hashlib
import struct
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    from .logger import setup_logger
except ImportError:
    from logger import setup_logger

logger = setup_logger("DocumentOrganizer.PhotoIngest")


@dataclass
class PhotoMetadata:
    filename: str
    file_path: str
    format: str
    size_bytes: int
    sha256_hash: str
    width: int
    height: int
    mtime: str
    exif_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PhotoIngestEngine:
    """Engine for extracting metadata and content features from photo/image assets."""

    SUPPORTED_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
        ".tiff",
        ".tif",
        ".heic",
    }

    @classmethod
    def is_supported(cls, file_path: Path | str) -> bool:
        return Path(file_path).suffix.lower() in cls.SUPPORTED_EXTENSIONS

    @classmethod
    def compute_sha256(cls, file_path: Path) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    @classmethod
    def _parse_jpeg_dimensions(cls, data: bytes) -> tuple[int, int]:
        """Pure-Python fallback parser for JPEG SOF marker (width, height)."""
        idx = 2
        data_len = len(data)
        while idx < data_len - 8:
            if data[idx] != 0xFF:
                idx += 1
                continue
            marker = data[idx + 1]
            # SOF0 (0xC0) or SOF2 (0xC2)
            if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                h, w = struct.unpack(">HH", data[idx + 5 : idx + 9])
                return w, h
            idx += 2 + struct.unpack(">H", data[idx + 2 : idx + 4])[0]
        return 0, 0

    @classmethod
    def _parse_png_dimensions(cls, data: bytes) -> tuple[int, int]:
        """Pure-Python fallback parser for PNG IHDR chunk."""
        if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", data[16:24])
            return w, h
        return 0, 0

    @classmethod
    def extract_metadata(cls, file_path: Path | str) -> PhotoMetadata | None:
        path = Path(file_path).resolve()
        if not path.is_file() or not cls.is_supported(path):
            return None

        size_bytes = path.stat().st_size
        mtime_str = datetime.datetime.fromtimestamp(
            path.stat().st_mtime, tz=datetime.timezone.utc
        ).isoformat()
        sha256 = cls.compute_sha256(path)
        ext = path.suffix.lower()

        fmt = ext.lstrip(".").upper()
        width, height = 0, 0
        exif_dict: dict[str, Any] = {}

        # 1. Try Pillow if installed
        try:
            from PIL import ExifTags, Image

            with Image.open(path) as img:
                width, height = img.size
                fmt = img.format or fmt
                raw_exif = img.getexif()
                if raw_exif:
                    for tag_id, value in raw_exif.items():
                        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                        # Convert complex types to string for serialization
                        exif_dict[tag_name] = str(value)
        except Exception:
            # 2. Fallback to binary parsing
            try:
                with open(path, "rb") as f:
                    header = f.read(65536)
                if ext in {".jpg", ".jpeg"}:
                    width, height = cls._parse_jpeg_dimensions(header)
                elif ext == ".png":
                    width, height = cls._parse_png_dimensions(header)
            except Exception as e:
                logger.warning("Binary header parse failed on %s: %s", path, e)

        return PhotoMetadata(
            filename=path.name,
            file_path=str(path),
            format=fmt,
            size_bytes=size_bytes,
            sha256_hash=sha256,
            width=width,
            height=height,
            mtime=mtime_str,
            exif_data=exif_dict,
        )
