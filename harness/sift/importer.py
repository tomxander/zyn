"""Import an existing requirement set (ReqIF, Excel, CSV) with its own IDs kept.

Column and attribute names differ between tools (DOORS, Polarion, Codebeamer, Jama, our own
export), so the importer looks for common names and says which ones it used. Nothing is
rewritten: the text is stored exactly as found, apart from stripping XHTML markup."""

from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

ID_NAMES = ["reqif.foreignid", "id", "req id", "requirement id", "req_id", "identifier",
            "key", "object identifier", "absolute number", "item id", "document id"]
TEXT_NAMES = ["reqif.text", "requirement", "requirement text", "text", "object text",
              "primary text", "description", "statement", "body"]
HEADING_NAMES = ["reqif.chaptername", "heading", "section", "chapter", "section heading",
                 "object heading", "subsystem"]


@dataclass
class ImportedRequirement:
    ext_id: str
    text: str
    heading: str = ""
    order: int = 0
    attrs: dict[str, str] = field(default_factory=dict)


@dataclass
class RequirementSet:
    name: str
    filename: str
    sha256: str
    source_format: str
    columns_used: dict[str, str]
    requirements: list[ImportedRequirement]

    def to_payload(self) -> dict:
        d = asdict(self)
        d.pop("requirements")
        d["count"] = len(self.requirements)
        return d


def _norm(name: str) -> str:
    return " ".join(str(name or "").strip().lower().replace("_", " ").split())


def _pick(names: list[str], wanted: list[str]) -> str | None:
    by_norm = {_norm(n): n for n in names}
    for w in wanted:
        if _norm(w) in by_norm:
            return by_norm[_norm(w)]
    return None


def _strip_xhtml(s: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", s).split())


def _from_rows(header: list[str], rows: list[list[str]]) -> tuple[dict, list]:
    id_col, text_col = _pick(header, ID_NAMES), _pick(header, TEXT_NAMES)
    if not text_col:
        raise ValueError(f"No requirement text column found. Columns: {header}. "
                         f"Expected one of: {', '.join(TEXT_NAMES)}")
    head_col = _pick(header, HEADING_NAMES)
    idx = {h: i for i, h in enumerate(header)}
    reqs = []
    for n, row in enumerate(rows, start=1):
        cells = {h: (str(row[i]).strip() if i < len(row) and row[i] is not None else "")
                 for h, i in idx.items() if h}
        text = cells.get(text_col, "")
        if not text:
            continue
        ext = cells.get(id_col, "") if id_col else ""
        reqs.append(ImportedRequirement(
            ext_id=ext or f"ROW-{n}", text=text, heading=cells.get(head_col, "") if head_col
            else "", order=len(reqs), attrs={k: v for k, v in cells.items() if v}))
    used = {"id": id_col or "(none: row numbers used)", "text": text_col,
            "heading": head_col or "(none)"}
    return used, reqs


def _header_row(rows: list[list[str]]) -> int:
    """First row (of the top ten) that names a text column. Our own export has a title row."""
    for i, r in enumerate(rows[:10]):
        if _pick([str(c) for c in r if c is not None], TEXT_NAMES):
            return i
    raise ValueError("Could not find a header row with a requirement text column "
                     f"(looked for: {', '.join(TEXT_NAMES)}).")


def _load_xlsx(path: Path) -> tuple[dict, list]:
    from openpyxl import load_workbook

    ws = load_workbook(path, read_only=True, data_only=True).active
    rows = [["" if c is None else c for c in r] for r in ws.iter_rows(values_only=True)]
    h = _header_row(rows)
    return _from_rows([str(c) for c in rows[h]], rows[h + 1:])


def _load_csv(path: Path) -> tuple[dict, list]:
    import io

    text = path.read_text(encoding="utf-8-sig")
    try:
        delim = csv.Sniffer().sniff(text[:4096], delimiters=",;\t").delimiter
    except csv.Error:
        # Long quoted requirements full of commas defeat the sniffer; the header line decides.
        first = text.splitlines()[0] if text else ""
        delim = max(",;\t", key=first.count)
    # Read from a stream, not split lines, so quoted cells may span several lines.
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    h = _header_row(rows)
    return _from_rows(rows[h], rows[h + 1:])


def _load_reqif(path: Path) -> tuple[dict, list]:
    from reqif.parser import ReqIFParser

    bundle = ReqIFParser.parse(str(path))
    content = bundle.core_content.req_if_content
    names: dict[str, str] = {}
    for t in content.spec_types or []:
        for a in getattr(t, "attribute_definitions", None) or []:
            names[a.identifier] = a.long_name or a.identifier
    long_names = sorted(set(names.values()))
    id_name, text_name = _pick(long_names, ID_NAMES), _pick(long_names, TEXT_NAMES)
    head_name = _pick(long_names, HEADING_NAMES)
    reqs = []
    for obj in content.spec_objects or []:
        vals = {}
        for a in obj.attributes:
            v = a.value_stripped_xhtml if getattr(a, "value_stripped_xhtml", None) else a.value
            vals[names.get(a.definition_ref, a.definition_ref)] = _strip_xhtml(str(v or ""))
        text = vals.get(text_name, "") if text_name else ""
        if not text:
            continue
        ext = (vals.get(id_name) if id_name else "") or obj.long_name or obj.identifier
        reqs.append(ImportedRequirement(
            ext_id=ext, text=text, heading=vals.get(head_name, "") if head_name else "",
            order=len(reqs), attrs={**{k: v for k, v in vals.items() if v},
                                    "ReqIF identifier": obj.identifier}))
    if not text_name:
        raise ValueError(f"No requirement text attribute found. Attributes: {long_names}")
    used = {"id": id_name or "(spec object name)", "text": text_name,
            "heading": head_name or "(none)"}
    return used, reqs


LOADERS = {".xlsx": ("xlsx", _load_xlsx), ".csv": ("csv", _load_csv),
           ".reqif": ("reqif", _load_reqif)}


def load_requirement_set(path: Path | str) -> RequirementSet:
    path = Path(path)
    fmt, loader = LOADERS.get(path.suffix.lower(), (None, None))
    if loader is None:
        raise ValueError(f"Unsupported file type {path.suffix}. Use ReqIF, XLSX or CSV.")
    used, reqs = loader(path)
    if not reqs:
        raise ValueError("No requirements with text found in the file.")
    return RequirementSet(name=path.stem, filename=path.name,
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          source_format=fmt, columns_used=used, requirements=reqs)
