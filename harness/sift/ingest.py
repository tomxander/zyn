"""Document ingestion: file -> Markdown -> numbered sections.

Markdown and plain text are read directly. PDF and DOCX are converted to Markdown by
Docling (layout and tables preserved), then go through the same section parser, so
every format ends up in the same structure.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
NUMBERED = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(.+)$")
SUPPORTED = {".md", ".markdown", ".txt", ".pdf", ".docx"}


@dataclass
class Section:
    section_id: str
    number: str | None
    heading: str
    level: int
    text: str
    order: int
    page: int | None = None  # first page of the section, when the source has pages (PDF)


@dataclass
class SourceDocument:
    filename: str
    sha256: str
    title: str
    converter: str
    markdown: str
    sections: list[Section] = field(default_factory=list)

    def to_payload(self) -> dict:
        d = asdict(self)
        d.pop("sections")
        return d


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def to_markdown(path: Path) -> tuple[str, str]:
    """Returns (markdown, converter_name)."""
    markdown, converter, _ = convert(path)
    return markdown, converter


def convert(path: Path) -> tuple[str, str, dict[str, int]]:
    """Returns (markdown, converter_name, heading -> page number)."""
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED:
        raise ValueError(f"Unsupported file type '{suffix}'. Supported: {sorted(SUPPORTED)}")
    if suffix in {".md", ".markdown", ".txt"}:
        return path.read_text(encoding="utf-8"), "plain", {}
    try:
        from docling.document_converter import DocumentConverter  # heavy, load on demand
    except ImportError:
        raise ValueError(
            f"Reading {suffix} files needs the document reader, which the light install "
            "leaves out. Install it with: pipx inject zyn-harness docling "
            "(or pip install docling), or give Zyn the text as .md or .txt."
        ) from None

    result = DocumentConverter().convert(str(path))
    return result.document.export_to_markdown(), "docling", heading_pages(result.document)


def _norm_heading(text: str) -> str:
    return " ".join(re.sub(r"[#*_`]", " ", text).split()).lower()


def heading_pages(document) -> dict[str, int]:
    """Heading text -> page number, from Docling's provenance. Empty when the source has no
    pages (DOCX) or the items carry no provenance."""
    pages: dict[str, int] = {}
    try:
        items = document.iterate_items()
    except AttributeError:
        return pages
    for entry in items:
        item = entry[0] if isinstance(entry, tuple) else entry
        label = str(getattr(item, "label", "")).lower()
        prov = getattr(item, "prov", None) or []
        text = getattr(item, "text", "") or ""
        if text and prov and ("header" in label or "title" in label):
            page = getattr(prov[0], "page_no", None)
            if page is not None:
                pages.setdefault(_norm_heading(text), int(page))
    return pages


def split_sections(markdown: str) -> tuple[str, list[Section]]:
    """Splits on Markdown headings. Level comes from the heading number when present
    (3.1.2 -> level 3) because converters often flatten heading levels."""
    title = ""
    sections: list[Section] = []
    current: dict | None = None
    body: list[str] = []
    seen: dict[str, int] = {}

    def flush() -> None:
        if current is None:
            return
        text = "\n".join(body).strip()
        sections.append(Section(text=text, order=len(sections), **current))

    for line in markdown.splitlines():
        m = HEADING.match(line)
        if not m:
            body.append(line)
            continue
        flush()
        body = []
        hashes, heading = len(m.group(1)), m.group(2).strip()
        num = NUMBERED.match(heading)
        number = num.group(1) if num else None
        name = num.group(2).strip() if num else heading
        if not title and hashes == 1 and number is None:
            title = heading
        level = number.count(".") + 1 if number else hashes
        base = f"S{number}" if number else "S-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        seen[base] = seen.get(base, 0) + 1
        sid = base if seen[base] == 1 else f"{base}-{seen[base]}"
        current = {"section_id": sid, "number": number, "heading": name, "level": level}
    flush()
    if current is None:  # no headings at all: one section holding everything
        sections = [Section("S-body", None, "Document body", 1, markdown.strip(), 0)]
    return title or "Untitled document", [s for s in sections if s.text or s.level > 1]


def load_document(path: Path | str) -> SourceDocument:
    path = Path(path)
    markdown, converter, pages = convert(path)
    title, sections = split_sections(markdown)
    for sec in sections:
        key = _norm_heading(f"{sec.number} {sec.heading}" if sec.number else sec.heading)
        sec.page = pages.get(key) or pages.get(_norm_heading(sec.heading))
    return SourceDocument(
        filename=path.name, sha256=file_sha256(path), title=title, converter=converter,
        markdown=markdown, sections=sections,
    )
