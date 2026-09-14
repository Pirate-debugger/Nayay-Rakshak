import io
import json
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

import docx
import pypdf

from app.core.exceptions import FileIntegrityError, SecurityValidationError
from app.core.file_security import validate_file_magic_and_mime
from app.services.ocr_service import extract_image_ocr_layout, is_scanned_page


def validate_file_signature(file_bytes: bytes, filename: str) -> str:
    """Wrapper forwarding to deep security validator."""
    return validate_file_magic_and_mime(file_bytes, filename)


def normalize_text(text: str) -> str:
    """Normalize Unicode (NFKC), clean control characters, normalize quotation marks and dashes."""
    if not text:
        return ""
    # Unicode NFKC normalization
    normalized = unicodedata.normalize("NFKC", text)
    # Normalize quotes
    normalized = re.sub(r'[\u2018\u2019\u201A\u201B]', "'", normalized)
    normalized = re.sub(r'[\u201C\u201D\u201E\u201F]', '"', normalized)
    # Normalize dashes
    normalized = re.sub(r'[\u2013\u2014]', '-', normalized)
    # Remove control characters except newlines and tabs
    normalized = "".join(ch for ch in normalized if ch in ("\n", "\t") or ch >= " ")
    return normalized.strip()


def extract_text_and_pages(file_bytes: bytes, file_type: str) -> List[Tuple[int, str]]:
    """
    Extracts text per page from the validated file.
    Maintained for backwards compatibility.
    """
    struct = extract_document_structure(file_bytes, file_type)
    return [(p["page_number"], p["clean_text"]) for p in struct["pages"]]


def extract_document_structure(file_bytes: bytes, file_type: str) -> Dict[str, Any]:
    """
    Comprehensive layout and structural parser preserving:
    - page numbers
    - sections & headings
    - paragraphs
    - tables
    - bullet / numbered lists
    - layout coordinates & OCR confidence
    """
    pages: List[Dict[str, Any]] = []
    sections: List[Dict[str, Any]] = []
    tables: List[Dict[str, Any]] = []
    lists: List[Dict[str, Any]] = []

    if file_type == "pdf":
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for i, page in enumerate(reader.pages):
                page_num = i + 1
                raw_text = page.extract_text() or ""
                clean_text = normalize_text(raw_text)

                # Check if page is a bitmap scan
                if is_scanned_page(clean_text):
                    # Trigger OCR reconstruction with actual image binary if available
                    img_bytes = b""
                    if hasattr(page, "images") and len(page.images) > 0:
                        try:
                            img_bytes = page.images[0].data
                        except Exception:
                            img_bytes = b""
                    ocr_res = extract_image_ocr_layout(img_bytes, page_number=page_num)
                    pages.append({
                        "page_number": page_num,
                        "raw_text": ocr_res["text"],
                        "clean_text": ocr_res["text"],
                        "ocr_confidence": ocr_res["confidence"],
                        "layout_data": json.dumps(ocr_res["boxes"]),
                        "is_scanned": True
                    })
                else:
                    # Synthetic coordinates from layout lines
                    lines = [ln.strip() for ln in clean_text.split("\n") if ln.strip()]
                    boxes = []
                    y_cursor = 50
                    for line_idx, line in enumerate(lines):
                        boxes.append({
                            "line_index": line_idx,
                            "text": line,
                            "x": 40,
                            "y": y_cursor,
                            "width": min(len(line) * 7, 700),
                            "height": 18,
                            "is_heading": is_heading_line(line)
                        })
                        y_cursor += 24

                    pages.append({
                        "page_number": page_num,
                        "raw_text": raw_text,
                        "clean_text": clean_text,
                        "ocr_confidence": 1.0,
                        "layout_data": json.dumps(boxes),
                        "is_scanned": False
                    })
        except Exception as e:
            raise FileIntegrityError(f"Failed to parse PDF document structure: {str(e)}")

    elif file_type == "docx":
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
            para_texts = []
            boxes = []
            y_cursor = 50

            for p_idx, p in enumerate(doc.paragraphs):
                text = p.text.strip()
                if not text:
                    continue
                para_texts.append(text)
                is_head = p.style.name.startswith("Heading") or is_heading_line(text)
                boxes.append({
                    "paragraph_index": p_idx,
                    "text": text,
                    "x": 40,
                    "y": y_cursor,
                    "width": min(len(text) * 7, 700),
                    "height": 22 if is_head else 18,
                    "is_heading": is_head
                })
                y_cursor += 26

            # Extract tables
            for t_idx, table in enumerate(doc.tables):
                t_rows = []
                for row in table.rows:
                    t_rows.append([cell.text.strip() for cell in row.cells])
                if t_rows:
                    tables.append({
                        "page_number": 1,
                        "table_index": t_idx,
                        "rows": t_rows,
                        "markdown": format_table_markdown(t_rows)
                    })

            full_text = normalize_text("\n\n".join(para_texts))
            pages.append({
                "page_number": 1,
                "raw_text": full_text,
                "clean_text": full_text,
                "ocr_confidence": 1.0,
                "layout_data": json.dumps(boxes),
                "is_scanned": False
            })
        except Exception as e:
            raise FileIntegrityError(f"Failed to parse DOCX document: {str(e)}")

    elif file_type == "txt":
        try:
            raw_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raw_text = file_bytes.decode("latin-1", errors="ignore")

        clean_text = normalize_text(raw_text)
        lines = [ln.strip() for ln in clean_text.split("\n") if ln.strip()]
        boxes = []
        y_cursor = 40
        for idx, ln in enumerate(lines):
            boxes.append({
                "line_index": idx,
                "text": ln,
                "x": 30,
                "y": y_cursor,
                "width": min(len(ln) * 6, 650),
                "height": 16,
                "is_heading": is_heading_line(ln)
            })
            y_cursor += 20

        pages.append({
            "page_number": 1,
            "raw_text": raw_text,
            "clean_text": clean_text,
            "ocr_confidence": 1.0,
            "layout_data": json.dumps(boxes),
            "is_scanned": False
        })

    elif file_type in ("png", "jpg"):
        # Scanned document image
        ocr_res = extract_image_ocr_layout(file_bytes, page_number=1)
        clean_text = normalize_text(ocr_res["text"])
        pages.append({
            "page_number": 1,
            "raw_text": ocr_res["text"],
            "clean_text": clean_text,
            "ocr_confidence": ocr_res["confidence"],
            "layout_data": json.dumps(ocr_res["boxes"]),
            "is_scanned": True
        })

    # Detect headings & hierarchical sections across all pages
    sections = detect_sections(pages)

    # Detect clauses
    clauses = detect_clauses(pages)

    return {
        "pages": pages,
        "sections": sections,
        "tables": tables,
        "clauses": clauses,
        "page_count": len(pages)
    }


def is_heading_line(line: str) -> bool:
    """Heuristic check for legal headings (Articles, Sections, Clauses, Capitalized titles)."""
    clean = line.strip()
    if not clean or len(clean) > 120:
        return False
    # Standard legal headings
    patterns = [
        r'^(ARTICLE|SECTION|CLAUSE|PART|SCHEDULE|CHAPTER)\s+[0-9IVXLCDM\.]+',
        r'^[0-9]{1,2}\.[0-9]{0,2}\s+[A-Z]',
        r'^[0-9]{1,2}\.\s+[A-Z]',
        r'^(WHEREAS|NOW THEREFORE|IN WITNESS WHEREOF|MEMORANDUM OF UNDERSTANDING)',
        r'^[A-Z\s]{4,60}$'  # ALL CAPS TITLE
    ]
    for p in patterns:
        if re.search(p, clean, re.IGNORECASE):
            return True
    return False


def detect_sections(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect hierarchical sections and headings spanning pages."""
    sections = []
    sec_idx = 1

    for p in pages:
        lines = p["clean_text"].split("\n")
        for line in lines:
            line_str = line.strip()
            if is_heading_line(line_str):
                sections.append({
                    "section_number": f"Sec-{sec_idx}",
                    "section_title": line_str[:200],
                    "start_page": p["page_number"],
                    "end_page": p["page_number"]
                })
                sec_idx += 1

    if not sections:
        sections.append({
            "section_number": "Sec-1",
            "section_title": "General Covenants",
            "start_page": 1,
            "end_page": len(pages)
        })

    return sections


def detect_clauses(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract structured clauses with legal category and initial risk level."""
    clauses = []
    c_idx = 1

    categories_keywords = {
        "Termination": ["terminate", "termination", "notice period", "evict", "forfeit"],
        "Rent Escalation": ["escalation", "increase rent", "per annum", "compounding"],
        "Security Deposit": ["security deposit", "refund", "deduction", "lock-in"],
        "Indemnity": ["indemnify", "hold harmless", "liable", "indemnification"],
        "Non-Compete": ["non-compete", "restraint", "solicitation", "competing business"],
        "Governing Law": ["governing law", "jurisdiction", "courts of", "arbitration"],
        "Force Majeure": ["force majeure", "act of god", "pandemic", "epidemic"],
    }

    for p in pages:
        paragraphs = [para.strip() for para in p["clean_text"].split("\n\n") if para.strip()]
        for para in paragraphs:
            if len(para) < 40:
                continue

            matched_cat = "General Covenant"
            for cat, keywords in categories_keywords.items():
                if any(kw in para.lower() for kw in keywords):
                    matched_cat = cat
                    break

            # Evaluate preliminary risk level
            risk_level = "LOW"
            is_unfair = False
            lower_para = para.lower()

            if "18%" in lower_para or "compounding" in lower_para or "forfeit the entire deposit" in lower_para:
                risk_level = "CRITICAL"
                is_unfair = True
            elif "unilateral" in lower_para or "without notice" in lower_para or "restraint" in lower_para:
                risk_level = "HIGH"
                is_unfair = True
            elif "penalty" in lower_para or "lock-in" in lower_para:
                risk_level = "MEDIUM"

            clauses.append({
                "clause_identifier": f"C-{c_idx:02d}",
                "title": f"{matched_cat} Provision",
                "category": matched_cat,
                "page_number": p["page_number"],
                "raw_text": para,
                "clean_text": para,
                "risk_level": risk_level,
                "is_unfair": is_unfair
            })
            c_idx += 1

    return clauses


def format_table_markdown(rows: List[List[str]]) -> str:
    """Format extracted table cells into GitHub markdown table syntax."""
    if not rows:
        return ""
    md_lines = []
    header = rows[0]
    md_lines.append("| " + " | ".join(header) + " |")
    md_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for r in rows[1:]:
        # Pad row to header length
        padded = r + [""] * (len(header) - len(r))
        md_lines.append("| " + " | ".join(padded[:len(header)]) + " |")
    return "\n".join(md_lines)


def chunk_document_with_provenance(
    document_id: int,
    pages: List[Dict[str, Any]],
    sections: List[Dict[str, Any]],
    content_hash: str,
    version_id: Optional[int] = None,
    target_chunk_size: int = 700,
    overlap: int = 100
) -> List[Dict[str, Any]]:
    """
    Split pages into chunks while strictly preserving provenance:
    - document_id
    - version_id
    - page_number
    - section_title
    - chunk_index
    - content_hash
    """
    chunks = []
    chunk_idx = 0

    for p in pages:
        page_num = p["page_number"]
        text = p["clean_text"]
        if not text:
            continue

        # Find closest active section
        section_title = "Preamble"
        for sec in sections:
            if sec["start_page"] <= page_num <= sec["end_page"]:
                section_title = sec["section_title"]

        paragraphs = [para.strip() for para in text.split("\n") if para.strip()]
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) < target_chunk_size:
                current_chunk = f"{current_chunk}\n{para}".strip()
            else:
                if current_chunk:
                    chunks.append({
                        "chunk_index": chunk_idx,
                        "document_id": document_id,
                        "version_id": version_id,
                        "page_number": page_num,
                        "section_title": section_title,
                        "content_hash": content_hash,
                        "content": current_chunk,
                        "clean_content": current_chunk.strip(),
                        "token_count": len(current_chunk.split())
                    })
                    chunk_idx += 1
                    current_chunk = current_chunk[-overlap:] + "\n" + para
                else:
                    current_chunk = para

        if current_chunk.strip():
            chunks.append({
                "chunk_index": chunk_idx,
                "document_id": document_id,
                "version_id": version_id,
                "page_number": page_num,
                "section_title": section_title,
                "content_hash": content_hash,
                "content": current_chunk,
                "clean_content": current_chunk.strip(),
                "token_count": len(current_chunk.split())
            })
            chunk_idx += 1

    return chunks


def chunk_document_text(
    pages: List[Tuple[int, str]],
    target_chunk_size: int = 700,
    overlap: int = 100
) -> List[dict]:
    """Backwards compatibility chunker for tests expecting simple page tuple input."""
    chunks = []
    chunk_idx = 0
    for page_num, text in pages:
        if not text:
            continue
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) < target_chunk_size:
                current_chunk = f"{current_chunk}\n{para}".strip()
            else:
                if current_chunk:
                    chunks.append({
                        "chunk_index": chunk_idx,
                        "page_number": page_num,
                        "content": current_chunk,
                        "clean_content": current_chunk.strip(),
                        "token_count": len(current_chunk.split())
                    })
                    chunk_idx += 1
                    current_chunk = current_chunk[-overlap:] + "\n" + para
                else:
                    current_chunk = para

        if current_chunk.strip():
            chunks.append({
                "chunk_index": chunk_idx,
                "page_number": page_num,
                "content": current_chunk,
                "clean_content": current_chunk.strip(),
                "token_count": len(current_chunk.split())
            })
            chunk_idx += 1

    return chunks
