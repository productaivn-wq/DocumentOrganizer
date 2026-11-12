
"""Document metadata and content extraction engine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .logger import setup_logger
    from .photo_ingest import PhotoIngestEngine
except ImportError:
    from logger import setup_logger
    from photo_ingest import PhotoIngestEngine

logger = setup_logger("DocumentOrganizer.Extract")


@dataclass
class ExtractedDocument:
    path: Path
    extension: str
    size_bytes: int
    content: str
    metadata: dict[str, Any]


class DocumentExtractor:
    """Extracts text, multimedia metadata safely with size guards."""

    MAX_FILE_SIZE: int = 25 * 1024 * 1024  # 25 MB for text/office docs
    MAX_MEDIA_FILE_SIZE: int = 10 * 1024 * 1024 * 1024  # 10 GB for video/audio

    @classmethod
    def extract(cls, file_path: Path | str) -> ExtractedDocument | None:
        path = Path(file_path)
        if not path.is_file():
            logger.warning("Target path is not a regular file: %s", path)
            return None

        size = path.stat().st_size
        extension = path.suffix.lower()
        is_media = extension in {
            ".mp4",
            ".mkv",
            ".mov",
            ".webm",
            ".avi",
            ".m4a",
            ".mp3",
            ".wav",
            ".aac",
            ".flac",
        }

        limit = cls.MAX_MEDIA_FILE_SIZE if is_media else cls.MAX_FILE_SIZE
        if size > limit:
            logger.warning("Skipping oversized file (%d bytes): %s", size, path)
            return None

        content = ""
        metadata: dict[str, Any] = {
            "mtime": path.stat().st_mtime,
            "size_mb": round(size / (1024 * 1024), 2),
        }

        try:
            if PhotoIngestEngine.is_supported(path):
                photo_meta = PhotoIngestEngine.extract_metadata(path)
                if photo_meta:
                    metadata["photo"] = photo_meta.to_dict()
                    content = (
                        f"[Photo: {photo_meta.filename}, {photo_meta.width}x{photo_meta.height} "
                        f"{photo_meta.format}, SHA256: {photo_meta.sha256_hash[:12]}]"
                    )
                else:
                    content = f"[Unsupported photo: {path.name}]"
            elif extension in {".docx", ".doc"}:
                import xml.etree.ElementTree as ET
                import zipfile

                try:
                    with zipfile.ZipFile(path) as z:
                        xml_content = z.read("word/document.xml")
                    tree = ET.fromstring(xml_content)
                    paragraphs = [
                        "".join(
                            elem.text
                            for elem in node.iter()
                            if elem.tag.endswith("}t") and elem.text
                        )
                        for node in tree.iter()
                        if node.tag.endswith("}p")
                    ]
                    content = "\n\n".join(p for p in paragraphs if p.strip())
                    metadata["doc_title"] = path.stem
                    metadata["extractor"] = "DocumentOrganizer.DocxXMLExtractor"
                except Exception as fallback_exc:
                    content = f"[Office Document: {path.name} (extraction failed: {fallback_exc})]"
                    metadata["extractor"] = "Failed"
            elif extension in {
                ".txt",
                ".md",
                ".markdown",
                ".rst",
                ".json",
                ".yaml",
                ".yml",
                ".csv",
            }:
                content = path.read_text(encoding="utf-8", errors="replace")
                if extension in {".md", ".markdown"}:
                    import re

                    headings = re.findall(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE)
                    if headings:
                        metadata["headings"] = [f"{h[0]} {h[1]}" for h in headings[:20]]
                        metadata["heading_count"] = len(headings)
            elif is_media:
                content = f"[Media: {path.name}, Size: {round(size / (1024 * 1024), 2)} MB, Ext: {extension}]"
                metadata["media_type"] = (
                    "video"
                    if extension in {".mp4", ".mkv", ".mov", ".webm", ".avi"}
                    else "audio"
                )
                metadata["extractor"] = "DocumentOrganizer.MediaMetadata"
            else:
                # Fallback binary preview or placeholder
                content = f"[{extension.upper().lstrip('.')} Document: {path.name}, Size: {round(size / 1024, 1)} KB]"
        except Exception as exc:
            logger.error("Extraction failure on %s: %s", path, exc)
            return None

        return ExtractedDocument(
            path=path,
            extension=extension,
            size_bytes=size,
            content=content,
            metadata=metadata,
        )
