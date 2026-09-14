"""
NYAYA RAKSHAK - Claim Extractor
Decomposes draft legal responses and answers into atomic, verifiable claims.
Categorizes claims by type: FACTUAL, LEGAL_STATUTORY, LEGAL_PRECEDENT, CONTRACTUAL_TERM, PROCEDURAL.
"""

import re
from typing import Dict, List
from app.schemas.verification import ClaimType


class ExtractedClaim:
    """Atomic claim extracted from draft text for verification."""

    def __init__(self, claim_id: str, claim_text: str, claim_type: ClaimType, cited_references: List[str]):
        self.claim_id = claim_id
        self.claim_text = claim_text
        self.claim_type = claim_type
        self.cited_references = cited_references


class ClaimExtractor:
    """Extracts factual and legal statements from generated draft answers."""

    def extract_claims(self, text: str) -> List[ExtractedClaim]:
        """
        Segments draft text into sentence-level or assertion-level claims.
        Extracts cited statutes, cases, or clauses.
        """
        # Protect legal abbreviations (v., vs., sec., ltd., etc.) from premature sentence splitting
        protected = re.sub(r"\b(v|vs|sec|ltd|pvt|co|no|art)\.\s+", r"\1_DOT_ ", text, flags=re.IGNORECASE)
        raw_sentences = [
            s.replace("_DOT_", ".").strip()
            for s in re.split(r"(?<=[.?!])\s+", protected)
            if len(s.strip()) > 10
        ]
        claims: List[ExtractedClaim] = []

        for idx, s in enumerate(raw_sentences):
            # Exclude boilerplate disclaimers or conversational greetings
            s_lower = s.lower()
            if any(skip in s_lower for skip in [
                "consult a qualified lawyer", "does not constitute legal advice", "hello", "here is what"
            ]):
                continue

            claim_id = f"CLAIM-{idx+1:03d}"
            claim_type, citations = self._classify_and_extract_citations(s)
            claims.append(ExtractedClaim(
                claim_id=claim_id,
                claim_text=s,
                claim_type=claim_type,
                cited_references=citations
            ))

        # Fallback if no sentences extracted
        if not claims and len(text.strip()) > 10:
            claim_type, citations = self._classify_and_extract_citations(text)
            claims.append(ExtractedClaim(
                claim_id="CLAIM-001",
                claim_text=text.strip(),
                claim_type=claim_type,
                cited_references=citations
            ))

        return claims

    def _classify_and_extract_citations(self, sentence: str) -> (ClaimType, List[str]):
        citations = []
        s_lower = sentence.lower()

        # 1. Statutory citations (Section X of Y, BNS, IPC, CPA, DPDP, etc.)
        statute_pattern = r"\b(?:section\s+\d+(?:\([0-9a-zA-Z]+\))?(?:\s+of\s+[A-Za-z0-9\s,]+(?:act|sanhita|code)(?:,\s*\d{4})?)?|article\s+\d+|bns(?:\s+2023)?|ipc|crpc|dpdp|contract\s+act|model\s+tenancy\s+act|delhi\s+rent\s+control\s+act|maharashtra\s+rent\s+control\s+act|[A-Z][a-zA-Z\s]+(?:Act|Sanhita|Code)(?:,\s*\d{4})?)\b"
        for m in re.finditer(statute_pattern, sentence, flags=re.IGNORECASE):
            cleaned = m.group(0).strip()
            if len(cleaned) > 2 and cleaned.lower() not in ["act", "code", "the act"]:
                citations.append(cleaned)

        # 2. Case precedents (e.g. Sharma v. Union of India, Percept D'Mark v. Zaheer Khan)
        case_pattern = r"\b[A-Z][a-zA-Z0-9'.]*(?:\s+[A-Z][a-zA-Z0-9'.]*)*\s+(?:v\.|vs\.)\s+[A-Z][a-zA-Z0-9'.]*(?:\s+(?:of\s+)?[A-Z][a-zA-Z0-9'.]*)*\b"
        for m in re.finditer(case_pattern, sentence):
            matched_str = m.group(0).strip()
            # Strip leading prepositions like "Under "
            cleaned = re.sub(r"^(?:under|in|per|see)\s+", "", matched_str, flags=re.IGNORECASE).strip()
            if len(cleaned) > 4:
                citations.append(cleaned)

        # 3. Contractual references (Clause X, Paragraph Y)
        contract_pattern = r"\b(?:clause|paragraph|article)\s+\d+(?:\.\d+)?\b"
        for m in re.finditer(contract_pattern, sentence, flags=re.IGNORECASE):
            citations.append(m.group(0).strip())

        # Determine Claim Type
        if any("v." in c or "vs." in c for c in citations):
            claim_type = ClaimType.LEGAL_PRECEDENT
        elif any(k in s_lower for k in ["section", "article", "act", "sanhita", "code"]):
            claim_type = ClaimType.LEGAL_STATUTORY
        elif any("clause" in c.lower() for c in citations) or any(k in s_lower for k in ["your agreement", "your lease", "the contract states", "in this document"]):
            claim_type = ClaimType.CONTRACTUAL_TERM
        elif any(k in s_lower for k in ["file an e-fir", "complaint portal", "court procedure", "online filing"]):
            claim_type = ClaimType.PROCEDURAL
        else:
            claim_type = ClaimType.FACTUAL

        return claim_type, citations


claim_extractor = ClaimExtractor()
