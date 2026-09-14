import re
from typing import Any, Dict, List, Optional

from app.services.deterministic_extractor import extract_deterministic_facts


class ComparisonClause:
    def __init__(
        self,
        clause_id: str,
        section_heading: str,
        section_number: Optional[str],
        page_number: int,
        text: str,
        char_start: int,
        char_end: int,
        document_id: int,
        document_title: str,
    ):
        self.clause_id = clause_id
        self.section_heading = section_heading
        self.section_number = section_number
        self.page_number = page_number
        self.text = text
        self.char_start = char_start
        self.char_end = char_end
        self.document_id = document_id
        self.document_title = document_title

        # Precomputed tokens and facts (normalized for OCR noise robustness)
        from app.services.comparison.matcher import normalize_ocr_text

        norm_text = normalize_ocr_text(text)
        self.tokens = [t.lower() for t in re.findall(r"\w+", norm_text) if len(t) > 1]
        self.token_set = set(self.tokens)
        self.facts = extract_deterministic_facts(norm_text)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clause_id": self.clause_id,
            "section_heading": self.section_heading,
            "section_number": self.section_number,
            "page_number": self.page_number,
            "text": self.text,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "document_id": self.document_id,
            "document_title": self.document_title,
            "facts": self.facts,
        }


def segment_document_for_comparison(
    text: str,
    document_id: int = 1,
    document_title: str = "Document",
    chunks: Optional[List[Any]] = None,
) -> List[ComparisonClause]:
    """
    Segments a legal document into structured clause blocks with exact headings,
    page numbers, and precomputed deterministic legal facts.
    """
    if chunks and len(chunks) > 0:
        clauses = []
        char_cursor = 0
        for idx, chunk in enumerate(chunks):
            if isinstance(chunk, dict):
                content = chunk.get("clean_content") or chunk.get("content") or ""
                page_num = chunk.get("page_number") or 1
                heading = chunk.get("section_heading") or "General Terms"
            else:
                content = (
                    getattr(chunk, "clean_content", "") or getattr(chunk, "raw_content", "") or ""
                )
                page_num = getattr(chunk, "page_number", 1) or 1
                heading = getattr(chunk, "section_heading", "General Terms") or "General Terms"

            # If heading is generic, extract title from first line of chunk content
            if heading == "General Terms" and content:
                first_line = content.strip().splitlines()[0].strip()
                m_head = re.match(
                    r"^(?:Clause|Section|Article|\b[0-9]{1,2}[\.\)])\s*([^\n\:\.]{3,80})",
                    first_line,
                    re.IGNORECASE,
                )
                if m_head:
                    heading = first_line[:80].strip()

            c_start = char_cursor
            c_end = char_cursor + len(content)
            char_cursor = c_end + 2

            # Extract section number if present
            num_match = re.match(
                r"^(?:Clause|Section|Article|\b)?\s*([0-9]+(?:\.[0-9]+)*|[A-Z])[\.\:\s]",
                heading,
                re.IGNORECASE,
            )
            sec_num = num_match.group(1) if num_match else str(idx + 1)

            clauses.append(
                ComparisonClause(
                    clause_id=f"CLAUSE-{idx + 1:02d}",
                    section_heading=heading,
                    section_number=sec_num,
                    page_number=page_num,
                    text=content.strip(),
                    char_start=c_start,
                    char_end=c_end,
                    document_id=document_id,
                    document_title=document_title,
                )
            )
        return clauses

    # Fallback to segmenting raw text
    header_pattern = re.compile(
        r"^(?:Clause|Section|Article|\b(?P<num>[0-9]{1,2}))[:\.\s]*(?P<title>[^\n]+)?",
        re.IGNORECASE,
    )

    blocks: List[Dict[str, Any]] = []
    current_lines: List[str] = []
    current_heading = "Preamble & Recitals"
    current_sec_num = "0"
    current_page = 1
    running_char_len = 0
    start_char = 0

    for ln in text.split("\n\n"):
        p = ln.strip()
        if not p:
            continue

        m = header_pattern.match(p)
        # Approximate page count (assume ~2000 chars per standard legal page)
        current_page = max(1, (running_char_len // 2000) + 1)

        if m and len(" ".join(current_lines)) > 40:
            full_b_text = " ".join(current_lines).strip()
            blocks.append(
                {
                    "heading": current_heading,
                    "sec_num": current_sec_num,
                    "page": current_page,
                    "text": full_b_text,
                    "char_start": start_char,
                    "char_end": start_char + len(full_b_text),
                }
            )
            start_char += len(full_b_text) + 2
            current_lines = [p]
            first_line = p.splitlines()[0].strip()
            colon_idx = first_line.find(":")
            if colon_idx != -1 and colon_idx < 60:
                current_heading = first_line[:colon_idx].strip()
            else:
                current_heading = first_line[:80].strip()
            current_sec_num = m.group("num") or str(len(blocks) + 1)
        else:
            current_lines.append(p)
        running_char_len += len(p)

    if current_lines:
        full_b_text = " ".join(current_lines).strip()
        blocks.append(
            {
                "heading": current_heading,
                "sec_num": current_sec_num,
                "page": max(1, (running_char_len // 2000) + 1),
                "text": full_b_text,
                "char_start": start_char,
                "char_end": start_char + len(full_b_text),
            }
        )

    # If document has single line headers (e.g. numbered list), split by single line pattern
    if len(blocks) <= 1:
        blocks = []
        single_lines = text.split("\n")
        curr_p: List[str] = []
        curr_h = "Preamble"
        curr_num = "1"
        s_char = 0

        for line in single_lines:
            s_line = line.strip()
            if not s_line:
                continue
            m2 = re.match(
                r"^(?:Clause|Section|Article|\b[0-9]{1,2}[\.\)])\s*(.*)", s_line, re.IGNORECASE
            )
            if m2 and curr_p:
                b_txt = "\n".join(curr_p).strip()
                blocks.append(
                    {
                        "heading": curr_h,
                        "sec_num": curr_num,
                        "page": max(1, (s_char // 2000) + 1),
                        "text": b_txt,
                        "char_start": s_char,
                        "char_end": s_char + len(b_txt),
                    }
                )
                s_char += len(b_txt) + 1
                curr_p = [s_line]
                num_match = re.match(
                    r"^(?:Clause|Section|Article|\b)?\s*([0-9]+(?:\.[0-9]+)*|[A-Z])[\.\:\s]",
                    s_line,
                    re.IGNORECASE,
                )
                curr_num = num_match.group(1) if num_match else str(len(blocks) + 1)
                colon_idx = s_line.find(":")
                if colon_idx != -1 and colon_idx < 60:
                    curr_h = s_line[:colon_idx].strip()
                else:
                    curr_h = s_line[:60].strip()
            else:
                curr_p.append(s_line)
                if not curr_h or curr_h == "Preamble":
                    colon_idx = s_line.find(":")
                    if colon_idx != -1 and colon_idx < 60:
                        curr_h = s_line[:colon_idx].strip()
                    else:
                        curr_h = s_line[:60].strip()
                    num_match = re.match(
                        r"^(?:Clause|Section|Article|\b)?\s*([0-9]+(?:\.[0-9]+)*|[A-Z])[\.\:\s]",
                        s_line,
                        re.IGNORECASE,
                    )
                    if num_match:
                        curr_num = num_match.group(1)
        if curr_p:
            b_txt = "\n".join(curr_p).strip()
            blocks.append(
                {
                    "heading": curr_h,
                    "sec_num": curr_num,
                    "page": max(1, (s_char // 2000) + 1),
                    "text": b_txt,
                    "char_start": s_char,
                    "char_end": s_char + len(b_txt),
                }
            )

    result: List[ComparisonClause] = []
    for idx, b in enumerate(blocks):
        result.append(
            ComparisonClause(
                clause_id=f"CLAUSE-{idx + 1:02d}",
                section_heading=b["heading"],
                section_number=b.get("sec_num", str(idx + 1)),
                page_number=b["page"],
                text=b["text"],
                char_start=b["char_start"],
                char_end=b["char_end"],
                document_id=document_id,
                document_title=document_title,
            )
        )

    return result
