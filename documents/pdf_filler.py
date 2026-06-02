"""
Pure-Python minimal PDF generator for IRS form data.
Produces a valid PDF/1.4 document with form fields rendered as text — no C extensions.
For full fillable-form PDF output, swap the _write_pdf_bytes() call for a pypdf/pdfrw
implementation once the cryptography package issue is resolved in the deployment environment.
"""
import io
import textwrap
from typing import Any


def _escape_pdf_string(s: str) -> str:
    """Escape special characters for PDF string literals."""
    return (
        s.replace("\\", "\\\\")
         .replace("(", "\\(")
         .replace(")", "\\)")
         .replace("\r", "\\r")
         .replace("\n", "\\n")
    )


def _write_pdf_bytes(title: str, fields: dict[str, Any]) -> bytes:
    """
    Write a minimal but valid PDF containing the form fields as a two-column
    key/value table.  Returns raw PDF bytes.
    """
    buf = io.BytesIO()

    # --- helpers ---
    objects: list[bytes] = []
    offsets: list[int] = []

    def add_obj(content: bytes) -> int:
        idx = len(objects) + 1
        objects.append(content)
        return idx

    # Build page content stream
    lines = [f"{_escape_pdf_string(str(k))}: {_escape_pdf_string(str(v))}"
             for k, v in fields.items()]

    content_lines = [
        "BT",
        "/F1 14 Tf",
        "50 780 Td",
        f"({_escape_pdf_string(title)}) Tj",
        "0 -20 Td",
        "/F1 10 Tf",
    ]
    for line in lines:
        # Wrap long lines
        for chunk in textwrap.wrap(line, 90) or [line]:
            content_lines.append(f"({_escape_pdf_string(chunk)}) Tj")
            content_lines.append("0 -14 Td")

    content_lines.append("ET")
    stream_content = "\n".join(content_lines).encode()

    # Objects 1-5: Catalog, Pages, Content stream, Font, Page
    # IDs are referenced by position (1 0 R … 5 0 R), not by variable
    add_obj(b"<< /Type /Catalog /Pages 2 0 R >>")
    add_obj(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    add_obj(
        b"<< /Length " + str(len(stream_content)).encode() + b" >>\n"
        b"stream\n" + stream_content + b"\nendstream"
    )
    add_obj(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding >>"
    )
    add_obj(
        b"<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 612 792] "
        b"/Contents 3 0 R "
        b"/Resources << /Font << /F1 4 0 R >> >> >>"
    )

    # Write PDF
    buf.write(b"%PDF-1.4\n")
    for i, obj in enumerate(objects):
        offsets.append(buf.tell())
        buf.write(f"{i+1} 0 obj\n".encode())
        buf.write(obj)
        buf.write(b"\nendobj\n")

    xref_offset = buf.tell()
    buf.write(b"xref\n")
    buf.write(f"0 {len(objects)+1}\n".encode())
    buf.write(b"0000000000 65535 f \n")
    for off in offsets:
        buf.write(f"{off:010d} 00000 n \n".encode())

    buf.write(b"trailer\n")
    buf.write(f"<< /Size {len(objects)+1} /Root 1 0 R >>\n".encode())
    buf.write(b"startxref\n")
    buf.write(f"{xref_offset}\n".encode())
    buf.write(b"%%EOF\n")

    return buf.getvalue()


def fill_form_pdf(form_data: dict) -> bytes:
    """
    Generate a PDF document from IRS form data dict.
    Returns raw PDF bytes suitable for storing to disk or returning as HTTP response.
    """
    title = (
        f"Form {form_data.get('form', 'TAX')} — "
        f"{form_data.get('tax_year', '')} — "
        f"{form_data.get('entity_name') or form_data.get('partnership_name') or form_data.get('corporation_name') or form_data.get('employer_name') or form_data.get('proprietor_name') or form_data.get('payer_name') or form_data.get('filer_name', 'Entity')}"
    )
    # Exclude meta fields from the rendered table
    exclude = {"generated_by"}
    fields = {k: v for k, v in form_data.items() if k not in exclude}

    return _write_pdf_bytes(title, fields)
