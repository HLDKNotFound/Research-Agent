import io
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pandas as pd


@dataclass
class ParsedPage:
    page_number: int
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


def parse_pdf(content: bytes) -> List[ParsedPage]:
    """Extracts text from PDF documents page by page using PyMuPDF."""
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz

    doc = fitz.open(stream=content, filetype="pdf")
    pages: List[ParsedPage] = []

    for page_idx, page in enumerate(doc, 1):
        text = page.get_text("text").strip()
        if text:
            pages.append(
                ParsedPage(
                    page_number=page_idx,
                    text=text,
                    metadata={"total_pages": len(doc), "format": "pdf"},
                )
            )

    doc.close()
    if not pages:
        pages.append(ParsedPage(page_number=1, text="[Empty PDF Document]", metadata={"format": "pdf"}))
    return pages


def parse_docx(content: bytes) -> List[ParsedPage]:
    """Extracts text from Word (.docx) documents preserving heading structure."""
    import docx

    file_stream = io.BytesIO(content)
    doc = docx.Document(file_stream)
    full_text = []

    for para in doc.paragraphs:
        line = para.text.strip()
        if line:
            if para.style.name.startswith("Heading"):
                full_text.append(f"\n### {line}\n")
            else:
                full_text.append(line)

    # Also extract tables
    for table in doc.tables:
        table_rows = []
        for row in table.rows:
            row_text = [cell.text.strip() for cell in row.cells]
            table_rows.append(" | ".join(row_text))
        if table_rows:
            full_text.append("\n" + "\n".join(table_rows) + "\n")

    joined = "\n".join(full_text).strip()
    return [
        ParsedPage(
            page_number=1,
            text=joined or "[Empty Word Document]",
            metadata={"paragraphs": len(doc.paragraphs), "format": "docx"},
        )
    ]


def parse_spreadsheet(content: bytes, is_csv: bool = False) -> List[ParsedPage]:
    """Extracts structured summary and tabular data from Excel/CSV spreadsheets using pandas."""
    file_stream = io.BytesIO(content)
    pages: List[ParsedPage] = []

    if is_csv:
        df = pd.read_csv(file_stream)
        summary = f"CSV Spreadsheet: {len(df)} rows, {len(df.columns)} columns.\nColumns: {', '.join(df.columns.astype(str))}\n\n"
        preview = df.head(50).to_string(index=False)
        pages.append(ParsedPage(page_number=1, text=summary + preview, metadata={"rows": len(df), "columns": len(df.columns), "format": "csv"}))
    else:
        xls = pd.ExcelFile(file_stream, engine="openpyxl")
        for idx, sheet_name in enumerate(xls.sheet_names, 1):
            df = pd.read_excel(xls, sheet_name=sheet_name)
            summary = f"Sheet '{sheet_name}': {len(df)} rows, {len(df.columns)} columns.\nColumns: {', '.join(df.columns.astype(str))}\n\n"
            preview = df.head(40).to_string(index=False)
            pages.append(
                ParsedPage(
                    page_number=idx,
                    text=summary + preview,
                    metadata={"sheet": sheet_name, "rows": len(df), "columns": len(df.columns), "format": "xlsx"},
                )
            )

    return pages


def parse_document(content: bytes, filename: str, mime_type: Optional[str] = None) -> List[ParsedPage]:
    """Unified document parser supporting PDF, Word, Excel, CSV, and Plain Text."""
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf" or mime_type == "application/pdf":
        pages = parse_pdf(content)
    elif ext in [".docx", ".doc"] or mime_type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ]:
        pages = parse_docx(content)
    elif ext in [".xlsx", ".xls"] or mime_type in [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    ]:
        pages = parse_spreadsheet(content, is_csv=False)
    elif ext == ".csv" or mime_type == "text/csv":
        pages = parse_spreadsheet(content, is_csv=True)
    else:
        # Fallback to UTF-8 plain text
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="replace")
        pages = [ParsedPage(page_number=1, text=text.strip(), metadata={"format": "txt"})]

    for p in pages:
        p.metadata["source_filename"] = filename
    return pages
