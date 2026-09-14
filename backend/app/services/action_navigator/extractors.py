"""
Action Navigator — Deterministic Extractors
============================================
Each extractor transforms already-computed analysis data into structured
Action Navigator items.  No AI inference happens here.

Sources consumed:
  - AnalysisResult: clauses_json, risks_json, obligations_json, missing_clauses_json
  - RiskEngineResult: risks, missing_protections
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.schemas.action_navigator import (
    FactItem,
    ImportantDateItem,
    ImportantDocumentItem,
    UrgencyLevel,
)

# ─── Date regex patterns ──────────────────────────────────────────────────────

_DATE_PATTERNS = [
    # ISO: 2024-03-15
    r"\b(\d{4}-\d{2}-\d{2})\b",
    # Indian format: 15/03/2024 or 15-03-2024
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
    # Human: 15 March 2024, March 15, 2024
    r"\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b",
    r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b",
]

_DURATION_PATTERNS = [
    r"\b(\d+)\s*(days?|months?|years?|weeks?)\s+(?:notice|prior|before|after|from)",
    r"(?:notice period|termination notice)\s+of\s+(\d+)\s*(days?|months?)",
    r"within\s+(\d+)\s*(days?|months?|years?|hours?)",
]

_DATE_CONSEQUENCE_MAP = {
    "notice": "Failing to give proper notice may void your rights to a proper termination or deposit return.",
    "renew": "Missing this date may result in automatic renewal or loss of tenancy rights.",
    "payment": "Missing a payment date may trigger late fees or breach-of-contract claims.",
    "termination": "Missing the termination notice window may lock you into the contract longer than intended.",
    "expiry": "Expiry of the agreement may create ambiguity about your rights and obligations.",
    "deadline": "This deadline may affect your legal standing if not met.",
}


def _date_consequence(context: str) -> str:
    ctx = context.lower()
    for kw, msg in _DATE_CONSEQUENCE_MAP.items():
        if kw in ctx:
            return msg
    return "Missing this date may have contractual or legal consequences."


# ─── Known Fact Extractor ─────────────────────────────────────────────────────

def extract_known_facts(
    clauses: List[Dict[str, Any]],
    obligations: List[Dict[str, Any]],
) -> List[FactItem]:
    """
    Extract objectively verifiable facts from clause and obligation data.
    Facts are things that ARE stated in the document with high confidence.
    """
    facts: List[FactItem] = []
    seen: set[str] = set()

    # 1. From clauses: concrete facts (financials, dates, party names)
    financial_re = re.compile(
        r"(₹[\d,]+(?:\.\d+)?|Rs\.?\s*[\d,]+(?:\.\d+)?|\d[\d,]+\s*(?:rupees?|INR|lakh|crore))",
        re.IGNORECASE,
    )
    percent_re = re.compile(r"\b(\d+(?:\.\d+)?)\s*%")
    duration_re = re.compile(r"\b(\d+)\s*(days?|months?|years?)\b", re.IGNORECASE)

    for clause in clauses:
        cid = clause.get("clause_id", "?")
        text = clause.get("original_text", "")
        category = clause.get("category", "General")

        # Financial amounts
        for m in financial_re.finditer(text):
            key = m.group(0).strip()
            if key not in seen:
                seen.add(key)
                facts.append(FactItem(
                    fact=f"The document specifies an amount of {key} in the context of {category}.",
                    source=cid,
                    confidence=0.95,
                    category="Financial",
                ))

        # Percentages
        for m in percent_re.finditer(text):
            key = f"{m.group(0)} in {category}"
            if key not in seen:
                seen.add(key)
                facts.append(FactItem(
                    fact=f"A rate of {m.group(0)} is specified in the {category} clause.",
                    source=cid,
                    confidence=0.90,
                    category="Financial",
                ))

        # Durations
        for m in duration_re.finditer(text):
            key = f"{m.group(0)} in {category}"
            if key not in seen:
                seen.add(key)
                facts.append(FactItem(
                    fact=f"A period of {m.group(1)} {m.group(2)} is stated in the {category} clause.",
                    source=cid,
                    confidence=0.88,
                    category="Duration",
                ))

    # 2. From obligations
    for ob in obligations:
        oid = ob.get("obligation_id", "?")
        party = ob.get("responsible_party", "A party")
        action = ob.get("action", "")
        deadline = ob.get("deadline_or_frequency", "")
        if action:
            key = f"{party}:{action}"
            if key not in seen:
                seen.add(key)
                facts.append(FactItem(
                    fact=f"{party} is obligated to: {action}"
                         + (f" (Frequency/Deadline: {deadline})" if deadline else ""),
                    source=oid,
                    confidence=0.92,
                    category="Obligation",
                ))

    return facts[:20]  # Cap to avoid overwhelming output


# ─── Unknown Fact Extractor ───────────────────────────────────────────────────

def extract_unknown_facts(
    risks: List[Dict[str, Any]],
    missing_clauses: List[Dict[str, Any]],
    risk_records: List[Any],   # RiskRecord objects
) -> List[FactItem]:
    """
    Surface things the document does NOT clearly establish, or that are ambiguous.
    Sources: AMBIGUITY risks, MISSING_PROTECTION risks, missing_clauses.
    """
    unknowns: List[FactItem] = []
    seen: set[str] = set()

    # From missing clauses
    for mc in missing_clauses:
        name = mc.get("clause_name", "")
        why = mc.get("why_needed", "")
        importance = mc.get("importance", "STANDARD")
        if name and name not in seen:
            seen.add(name)
            conf = 0.95 if importance == "CRITICAL" else 0.80
            unknowns.append(FactItem(
                fact=f"The document does not include a {name} clause. "
                     f"This means: {why}",
                source="missing_clauses",
                confidence=conf,
                category="Missing Protection",
            ))

    # From AI analysis risks (ambiguity category)
    for r in risks:
        cat = r.get("category", "")
        if cat.upper() in ("AMBIGUITY", "MISSING PROTECTION"):
            title = r.get("title", r.get("description", ""))
            if title and title not in seen:
                seen.add(title)
                unknowns.append(FactItem(
                    fact=f"Ambiguity / gap identified: {title}. "
                         f"{r.get('countermeasure', '')}",
                    source=r.get("risk_id", "?"),
                    confidence=0.75,
                    category=cat,
                ))

    # From risk engine AMBIGUITY records
    for rr in risk_records:
        cat = getattr(rr, "category", "")
        cat_val = cat.value if hasattr(cat, "value") else str(cat)
        if "AMBIGUITY" in cat_val or "MISSING" in cat_val:
            title = getattr(rr, "title", "")
            if title and title not in seen:
                seen.add(title)
                unknowns.append(FactItem(
                    fact=f"Unclear or absent provision: {title}",
                    source=getattr(rr, "risk_id", "?"),
                    confidence=getattr(rr, "confidence", 0.75),
                    category=cat_val,
                ))

    return unknowns[:15]


# ─── Important Document Builder ───────────────────────────────────────────────

_DOCUMENT_TRIGGERS: List[Dict[str, Any]] = [
    {
        "keywords": ["security deposit", "advance"],
        "document_name": "Security Deposit Receipt / Acknowledgement",
        "why_needed": "Proves the amount paid and creates a legal record for refund claims.",
        "urgency": UrgencyLevel.HIGH,
        "consequence_if_missing": "Without a receipt, recovering the security deposit may be very difficult.",
    },
    {
        "keywords": ["title", "ownership", "owner", "lessor", "landlord"],
        "document_name": "Proof of Ownership (Sale Deed / Property Tax Receipt)",
        "why_needed": "Confirms the other party has legal authority to enter this agreement.",
        "urgency": UrgencyLevel.HIGH,
        "consequence_if_missing": "If the lessor does not own the property, the agreement may be void.",
    },
    {
        "keywords": ["stamp duty", "registration", "registered"],
        "document_name": "Stamp Duty Payment Receipt and Registration Certificate",
        "why_needed": "A registered and stamped agreement has legal enforceability in court.",
        "urgency": UrgencyLevel.HIGH,
        "consequence_if_missing": "Unregistered/unstamped agreements may not be admissible as evidence.",
    },
    {
        "keywords": ["notice", "termination", "eviction"],
        "document_name": "Written Termination / Notice Record",
        "why_needed": "Any notice given or received should be in writing with date and acknowledgement.",
        "urgency": UrgencyLevel.MEDIUM,
        "consequence_if_missing": "Without written proof, disputes about notice timing become difficult to resolve.",
    },
    {
        "keywords": ["salary", "compensation", "wages", "emolument"],
        "document_name": "Salary Slip / Offer Letter",
        "why_needed": "Documents the agreed compensation and forms the basis for statutory calculations.",
        "urgency": UrgencyLevel.MEDIUM,
        "consequence_if_missing": "Disputes about pay may be harder to resolve without documentary evidence.",
    },
    {
        "keywords": ["intellectual property", "ip", "invention", "work product"],
        "document_name": "IP Ownership Clarification / Prior Inventions Schedule",
        "why_needed": "Protects personal/prior work that should not be claimed by the counterparty.",
        "urgency": UrgencyLevel.MEDIUM,
        "consequence_if_missing": "Without a schedule of prior inventions, all your past work may be claimed.",
    },
    {
        "keywords": ["arbitration", "dispute", "arbitrator"],
        "document_name": "Arbitration Clause Reference (Arbitration & Conciliation Act, 1996)",
        "why_needed": "Understand the dispute process before a dispute arises.",
        "urgency": UrgencyLevel.LOW,
        "consequence_if_missing": "If you do not know the process, you may miss filing deadlines.",
    },
    {
        "keywords": ["insurance", "indemnity", "liability"],
        "document_name": "Insurance Policy / Indemnity Proof",
        "why_needed": "Required if the agreement makes you liable for third-party losses.",
        "urgency": UrgencyLevel.MEDIUM,
        "consequence_if_missing": "You may face unlimited liability exposure without insurance coverage.",
    },
    {
        "keywords": ["nda", "confidential", "non-disclosure"],
        "document_name": "Confidentiality / NDA Scope Schedule",
        "why_needed": "Documents exactly what information is considered confidential.",
        "urgency": UrgencyLevel.MEDIUM,
        "consequence_if_missing": "Vague NDA terms may be interpreted very broadly against you.",
    },
]


def extract_important_documents(
    clauses: List[Dict[str, Any]],
    risks: List[Dict[str, Any]],
    obligations: List[Dict[str, Any]],
) -> List[ImportantDocumentItem]:
    """Deterministic rule-based document list derived from clause text."""
    found: List[ImportantDocumentItem] = []
    used_names: set[str] = set()

    all_text = " ".join(
        c.get("original_text", "").lower() for c in clauses
    ) + " ".join(
        o.get("action", "").lower() for o in obligations
    )

    for trigger in _DOCUMENT_TRIGGERS:
        if any(kw in all_text for kw in trigger["keywords"]):
            name = trigger["document_name"]
            if name not in used_names:
                used_names.add(name)
                found.append(ImportantDocumentItem(
                    document_name=name,
                    why_needed=trigger["why_needed"],
                    urgency=trigger["urgency"],
                    consequence_if_missing=trigger["consequence_if_missing"],
                    source="clause_text_match",
                ))

    # Always include the agreement itself
    if "Signed Copy of This Agreement" not in used_names:
        found.insert(0, ImportantDocumentItem(
            document_name="Signed Copy of This Agreement",
            why_needed="Keep a fully executed copy with all parties' signatures as your primary legal record.",
            urgency=UrgencyLevel.HIGH,
            consequence_if_missing="Without a signed original, proving the agreed terms may be difficult.",
            source="always_required",
        ))

    return found


# ─── Important Date Extractor ─────────────────────────────────────────────────

def extract_important_dates(
    clauses: List[Dict[str, Any]],
    obligations: List[Dict[str, Any]],
) -> List[ImportantDateItem]:
    """Extract time-critical dates from clause text and obligations."""
    dates: List[ImportantDateItem] = []
    seen: set[str] = set()

    # From obligations with deadlines
    for ob in obligations:
        oid = ob.get("obligation_id", "?")
        deadline = ob.get("deadline_or_frequency", "")
        action = ob.get("action", "")
        if deadline and deadline.strip().lower() not in ("n/a", "none", "not specified", ""):
            key = f"{action}:{deadline}"
            if key not in seen:
                seen.add(key)
                dates.append(ImportantDateItem(
                    date_description=f"{action} — Deadline/Frequency",
                    estimated_date=deadline,
                    consequence=_date_consequence(action + " " + deadline),
                    urgency=UrgencyLevel.MEDIUM,
                    source=oid,
                ))

    # From clause text: regex-extracted dates
    for clause in clauses:
        cid = clause.get("clause_id", "?")
        text = clause.get("original_text", "")
        category = clause.get("category", "General")

        # Absolute dates
        for pat in _DATE_PATTERNS:
            for m in re.finditer(pat, text, re.IGNORECASE):
                date_str = m.group(0).strip()
                key = f"{cid}:{date_str}"
                if key not in seen:
                    seen.add(key)
                    ctx = text[max(0, m.start() - 40): m.end() + 40]
                    dates.append(ImportantDateItem(
                        date_description=f"{category} clause date",
                        estimated_date=date_str,
                        consequence=_date_consequence(ctx),
                        urgency=UrgencyLevel.MEDIUM,
                        source=cid,
                    ))

        # Relative durations
        for pat in _DURATION_PATTERNS:
            for m in re.finditer(pat, text, re.IGNORECASE):
                key = f"{cid}:{m.group(0)}"
                if key not in seen:
                    seen.add(key)
                    dates.append(ImportantDateItem(
                        date_description=f"{category} — {m.group(0).strip()}",
                        estimated_date=m.group(0).strip(),
                        consequence=_date_consequence(text),
                        urgency=UrgencyLevel.MEDIUM,
                        source=cid,
                    ))

    # Deduplicate by date_description+estimated_date, keep most unique
    return dates[:12]
