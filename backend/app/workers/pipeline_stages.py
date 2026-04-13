from __future__ import annotations

import io
import zipfile
import xml.etree.ElementTree as ET
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.models.document_model import Document


@dataclass
class ParsedDocument:
    text: str


def _read_bytes(storage_path: str) -> bytes:
    return Path(storage_path).read_bytes()


def _extract_text_from_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("PDF extraction requires pypdf") from exc

    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _extract_text_from_docx(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as docx_zip:
        xml_data = docx_zip.read("word/document.xml")

    root = ET.fromstring(xml_data)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    lines: list[str] = []
    for paragraph in root.findall(".//w:p", ns):
        texts = [t.text for t in paragraph.findall(".//w:t", ns) if t.text]
        if texts:
            lines.append("".join(texts))

    return "\n".join(lines)


def extract_text(storage_path: str, file_type: str) -> ParsedDocument:
    data = _read_bytes(storage_path)
    text = ""

    if file_type in ("text/plain", "text/csv"):
        text = data.decode("utf-8", errors="replace")
    elif file_type == "application/pdf":
        text = _extract_text_from_pdf(data)
    elif file_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        try:
            text = _extract_text_from_docx(data)
        except Exception:
            # Fallback for legacy .doc files or missing parser.
            text = data.decode("utf-8", errors="ignore")
    else:
        text = data.decode("utf-8", errors="ignore")

    text = re.sub(r"\s+", " ", text).strip()
    return ParsedDocument(text=text)


def _top_keywords(text: str, limit: int = 8) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    if not words:
        return []

    stopwords = {
        "the", "and", "for", "that", "with", "this", "from", "you", "your",
        "are", "was", "were", "have", "has", "had", "but", "not", "can", "will",
        "our", "their", "they", "them", "been", "into", "about", "which", "who",
    }
    filtered = [w for w in words if w not in stopwords and len(w) > 2]
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(limit)]


def extract_fields(parsed: ParsedDocument, document: Document) -> dict[str, Any]:
    text = parsed.text
    title = next((line for line in text.splitlines() if line.strip()), document.filename)
    summary = text[:200] if text else document.filename
    keywords = _top_keywords(text)

    return {
        "title": title,
        "category": "general",
        "summary": summary,
        "keywords": keywords,
        "file_metadata": {
            "name": document.filename,
            "type": document.file_type,
            "size": document.file_size,
        },
        "status": "success",
        "extraction_confidence": 0.75,
    }
