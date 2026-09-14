import logging
import re
from typing import Any, Dict, List

from app.ai.factory import get_ai_provider
from app.schemas.clause_intelligence import (
    ClauseSemanticInterpretation,
    DeterministicCurrency,
    DeterministicDate,
    DeterministicDuration,
    DeterministicFacts,
    DeterministicPercentage,
    DeterministicSection,
    EvidenceLocation,
    StructuredClauseRecord,
)
from app.services.clause_taxonomy import taxonomy_registry
from app.services.deterministic_extractor import extract_deterministic_facts

logger = logging.getLogger("nyaya_rakshak.clause_intelligence")


def segment_clauses_from_text(full_text: str, default_page: int = 1) -> List[Dict[str, Any]]:
    """
    Segment legal document into candidate clause blocks using numbering patterns and paragraph boundaries.
    """
    candidates = []
    # Split on standard paragraph breaks
    paras = [p.strip() for p in full_text.split("\n\n") if p.strip()]

    current_block = ""
    clause_idx = 1
    current_section = "General Terms"

    clause_header_pattern = re.compile(
        r"^(?:Clause|Section|Article|\b[0-9]{1,2}\.)\s*(?P<num>[0-9]+(?:\.[0-9]+)*|[A-Z])?[:\.\s]*(?P<title>[^\n]+)?",
        re.IGNORECASE,
    )

    for p in paras:
        match = clause_header_pattern.match(p)
        if match and len(current_block) > 40:
            candidates.append(
                {
                    "clause_id": f"C-{clause_idx:02d}",
                    "section": current_section,
                    "text": current_block.strip(),
                    "page": default_page,
                }
            )
            clause_idx += 1
            current_block = p
            if match.group("title"):
                current_section = match.group("title")[:100].strip()
        else:
            if current_block:
                current_block += "\n\n" + p
            else:
                current_block = p

    if current_block.strip():
        candidates.append(
            {
                "clause_id": f"C-{clause_idx:02d}",
                "section": current_section,
                "text": current_block.strip(),
                "page": default_page,
            }
        )

    # If segmentation produced only 1 giant block, split by single newline numbers
    if len(candidates) <= 1 and len(full_text) > 400:
        lines = [ln.strip() for ln in full_text.split("\n") if ln.strip()]
        candidates = []
        clause_idx = 1
        curr_lines = []
        for ln in lines:
            if re.match(r"^[0-9]{1,2}[\.\)]\s+", ln) and curr_lines:
                candidates.append(
                    {
                        "clause_id": f"C-{clause_idx:02d}",
                        "section": current_section,
                        "text": " ".join(curr_lines),
                        "page": default_page,
                    }
                )
                clause_idx += 1
                curr_lines = [ln]
            else:
                curr_lines.append(ln)
        if curr_lines:
            candidates.append(
                {
                    "clause_id": f"C-{clause_idx:02d}",
                    "section": current_section,
                    "text": " ".join(curr_lines),
                    "page": default_page,
                }
            )

    return candidates


def generate_simplified_explanation(category: str, text: str, facts: Dict[str, Any]) -> str:
    """Deterministic citizen-friendly simplified explanation."""
    lower = text.lower()
    currencies = facts.get("currencies", [])
    percentages = facts.get("percentages", [])
    durations = facts.get("durations", [])

    if "rent" in lower and currencies:
        amt = currencies[0]["amount"]
        return f"This clause sets the monthly rent payment at ₹{amt:,.0f} and establishes payment due dates."

    if "late" in lower and ("interest" in lower or "fee" in lower) and percentages:
        pct = percentages[0]["value"]
        return f"This clause charges a late fee of {pct}% if payment is delayed past the due date."

    if "security deposit" in lower and currencies:
        amt = currencies[0]["amount"]
        return f"This clause requires a refundable security deposit of ₹{amt:,.0f} before taking possession."

    if "notice" in lower and ("terminate" in lower or "termination" in lower) and durations:
        d = durations[0]["count"]
        u = durations[0]["unit"]
        return f"Either party can end this agreement by providing at least {d} {u} written advance notice."

    if "non-compete" in lower or "restraint" in lower:
        return "This clause restricts you from joining or working with competing businesses after this contract ends."

    if "confidential" in lower:
        return "This clause requires both parties to keep business and personal information secret and not share it with outsiders."

    if "governing law" in lower or "jurisdiction" in lower:
        return "This clause states which courts and state laws will handle any legal disagreements that arise."

    if "indemnif" in lower:
        return "This clause makes one party pay for legal costs, losses, or damages suffered by the other party."

    return (
        "This clause outlines specific rights, duties, and conditions agreed upon by the parties."
    )


def extract_semantic_interpretation_rules(text: str, facts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract semantic elements (obligations, rights, prohibitions, conditions, deadlines, etc.)
    using robust legal linguistic patterns and verified facts.
    """
    lower = text.lower()

    obligations = []
    rights = []
    prohibitions = []
    conditions = []
    triggers = []
    deadlines = []
    monetary_values = [f"{c['currency']} {c['amount']:,.0f}" for c in facts.get("currencies", [])]
    penalties = []
    termination_conditions = []

    sentences = [s.strip() for s in re.split(r"[\.\;\n]", text) if s.strip()]

    for s in sentences:
        s_lower = s.lower()
        # Obligations
        if any(
            w in s_lower
            for w in [
                "shall pay",
                "must pay",
                "shall provide",
                "shall maintain",
                "agrees to",
                "is required to",
            ]
        ):
            obligations.append(s.strip())
        # Rights
        if any(
            w in s_lower for w in ["may", "has the right", "is entitled to", "at its sole option"]
        ):
            rights.append(s.strip())
        # Prohibitions
        if any(
            w in s_lower
            for w in ["shall not", "must not", "prohibited", "neither party shall", "will not"]
        ):
            prohibitions.append(s.strip())
        # Conditions & Triggers
        if any(
            w in s_lower
            for w in ["provided that", "subject to", "on condition", "in the event", "upon failure"]
        ):
            conditions.append(s.strip())
            triggers.append(s.strip())
        # Deadlines
        if any(w in s_lower for w in ["within", "prior to", "before", "by the", "on or before"]):
            deadlines.append(s.strip())
        # Penalties
        if any(
            w in s_lower
            for w in ["penalty", "forfeit", "interest of", "liquidated damages", "late charge"]
        ):
            penalties.append(s.strip())
        # Termination
        if any(w in s_lower for w in ["terminate", "termination", "cancel", "vacate", "eviction"]):
            termination_conditions.append(s.strip())

    # Detect parties
    parties = []
    party_keywords = [
        "landlord",
        "tenant",
        "employer",
        "employee",
        "service provider",
        "client",
        "lender",
        "borrower",
        "disclosing party",
        "receiving party",
    ]
    for pk in party_keywords:
        if pk in lower:
            parties.append(pk.title())
    if not parties:
        parties = ["First Party", "Second Party"]

    # Jurisdiction and governing law
    jurisdiction = None
    jur_m = re.search(r"(?:courts\s+(?:of|at|in))\s+([A-Z][a-zA-Z]+)", text, re.IGNORECASE)
    if jur_m:
        jurisdiction = f"Courts at {jur_m.group(1).strip()}"

    governing_law = None
    if "laws of india" in lower or "law of india" in lower:
        governing_law = "Laws of India"
    else:
        gov_m = re.search(
            r"(?:governed\s+by\s+(?:the\s+)?laws\s+of)\s+([A-Z][a-zA-Z]+)", text, re.IGNORECASE
        )
        if gov_m:
            governing_law = f"Laws of {gov_m.group(1).strip()}"

    # Arbitration
    arbitration = None
    if "arbitration" in lower:
        arbitration = (
            "Arbitration and Conciliation Act, 1996"
            if "1996" in lower or "india" in lower
            else "Binding Arbitration Clause"
        )

    # Confidentiality
    confidentiality = None
    if "confidential" in lower or "proprietary" in lower:
        confidentiality = "Duty to maintain strict non-disclosure of confidential materials."

    # Indemnity
    indemnity = None
    if "indemnif" in lower or "hold harmless" in lower:
        indemnity = "Hold harmless and indemnification against liabilities or claims."

    # Liability
    liability = None
    if "liability" in lower:
        liability = "Stated limitation or exclusion of contractual liability."

    # IP
    ip = None
    if any(
        k in lower
        for k in ["intellectual property", "inventions", "copyright", "patent", "work for hire"]
    ):
        ip = "Intellectual property ownership and assignment terms."

    # Renewal
    renewal = None
    if "renew" in lower or "extension" in lower:
        renewal = "Contract renewal or lease extension conditions."

    # Dispute resolution
    dispute_res = None
    if any(k in lower for k in ["dispute", "conciliation", "mediation", "arbitration", "courts"]):
        dispute_res = "Dispute escalation framework (negotiation, arbitration, or courts)."

    # Privacy / data terms
    privacy = None
    if any(k in lower for k in ["personal data", "consent", "dpdp", "privacy", "processing"]):
        privacy = "Personal data handling and privacy compliance under DPDP Act 2023."

    return {
        "parties_affected": parties,
        "obligations": obligations[:5],
        "rights": rights[:5],
        "prohibitions": prohibitions[:5],
        "conditions": conditions[:5],
        "triggers": triggers[:5],
        "deadlines": deadlines[:5],
        "monetary_values": monetary_values,
        "penalties": penalties[:5],
        "termination_conditions": termination_conditions[:5],
        "jurisdiction": jurisdiction,
        "governing_law": governing_law,
        "arbitration": arbitration,
        "confidentiality": confidentiality,
        "indemnity": indemnity,
        "liability": liability,
        "intellectual_property": ip,
        "renewal": renewal,
        "dispute_resolution": dispute_res,
        "privacy_data_terms": privacy,
    }


def enforce_deterministic_immutability(
    raw_facts: Dict[str, Any], semantic_data: Dict[str, Any]
) -> ClauseSemanticInterpretation:
    """
    Guarantees that deterministic extractions (monetary values, dates, percentages, durations, sections)
    are NEVER silently overwritten or dropped by AI or rule interpretations.
    """
    # 1. Monetary values: AI cannot alter or drop detected deterministic monetary values
    det_currencies = raw_facts.get("currencies", [])
    if det_currencies:
        det_monetary = [f"{c['currency']} {c['amount']:,.0f}" for c in det_currencies]
        ai_monetary = semantic_data.get("monetary_values") or []
        combined_monetary = list(det_monetary)
        for m in ai_monetary:
            if m not in combined_monetary:
                combined_monetary.append(m)
        semantic_data["monetary_values"] = combined_monetary

    # 2. Deadlines / Durations / Dates
    det_durations = raw_facts.get("durations", [])
    det_dates = raw_facts.get("dates", [])
    if det_durations or det_dates:
        det_deadlines = [f"{d['count']} {d['unit']}" for d in det_durations] + [
            dt["date_string"] for dt in det_dates
        ]
        existing_deadlines = semantic_data.get("deadlines") or []
        combined_deadlines = list(existing_deadlines)
        for d in det_deadlines:
            if not any(d.lower() in ed.lower() for ed in combined_deadlines):
                combined_deadlines.append(f"Statutory/Contractual period: {d}")
        semantic_data["deadlines"] = combined_deadlines

    # 3. Penalties & Percentages
    det_percentages = raw_facts.get("percentages", [])
    if det_percentages:
        existing_penalties = semantic_data.get("penalties") or []
        combined_penalties = list(existing_penalties)
        for p in det_percentages:
            pct_str = f"{p['value']}% ({p['frequency']})"
            if not any(f"{p['value']}%" in pen for pen in combined_penalties):
                combined_penalties.append(f"Interest rate/Charge: {pct_str}")
        semantic_data["penalties"] = combined_penalties

    # 4. Filter to exact ClauseSemanticInterpretation keys
    valid_keys = {
        "parties_affected",
        "obligations",
        "rights",
        "prohibitions",
        "conditions",
        "triggers",
        "deadlines",
        "monetary_values",
        "penalties",
        "termination_conditions",
        "jurisdiction",
        "governing_law",
        "arbitration",
        "confidentiality",
        "indemnity",
        "liability",
        "intellectual_property",
        "renewal",
        "dispute_resolution",
        "privacy_data_terms",
    }
    clean_kwargs = {}
    for k in valid_keys:
        val = semantic_data.get(k)
        if val is None:
            clean_kwargs[k] = (
                []
                if k
                in [
                    "parties_affected",
                    "obligations",
                    "rights",
                    "prohibitions",
                    "conditions",
                    "triggers",
                    "deadlines",
                    "monetary_values",
                    "penalties",
                    "termination_conditions",
                ]
                else None
            )
        else:
            clean_kwargs[k] = val

    return ClauseSemanticInterpretation(**clean_kwargs)


def analyze_clause_structured(
    clause_id: str,
    raw_text: str,
    page_number: int = 1,
    section_name: str = "General Covenants",
    char_offset: int = 0,
) -> StructuredClauseRecord:
    """
    Extract deterministic facts, evaluate taxonomy risk rules,
    synthesize semantic interpretation, and guarantee deterministic integrity.
    """
    # 1. Deterministic extraction (immutability guaranteed)
    raw_facts = extract_deterministic_facts(raw_text)

    det_currencies = [
        DeterministicCurrency(currency=c["currency"], amount=c["amount"], raw_text=c["raw_text"])
        for c in raw_facts["currencies"]
    ]
    det_percentages = [
        DeterministicPercentage(value=p["value"], frequency=p["frequency"], raw_text=p["raw_text"])
        for p in raw_facts["percentages"]
    ]
    det_durations = [
        DeterministicDuration(
            count=d["count"],
            unit=d["unit"],
            days_equivalent=d["days_equivalent"],
            raw_text=d["raw_text"],
        )
        for d in raw_facts["durations"]
    ]
    det_dates = [
        DeterministicDate(
            date_string=dt["date_string"], format=dt["format"], raw_text=dt["raw_text"]
        )
        for dt in raw_facts["dates"]
    ]
    det_sections = [
        DeterministicSection(
            prefix=s["prefix"], number=s["number"], full_reference=s["full_reference"]
        )
        for s in raw_facts["sections"]
    ]

    deterministic_facts_model = DeterministicFacts(
        currencies=det_currencies,
        percentages=det_percentages,
        durations=det_durations,
        dates=det_dates,
        sections=det_sections,
    )

    # 2. Taxonomy classification & evaluation
    cat_id, cat_name = taxonomy_registry.classify_clause(raw_text)
    plugin = taxonomy_registry.get(cat_id)

    risk_level = "LOW"
    is_unfair = False
    statutory_ref = None

    if plugin:
        risk_level, is_unfair, statutory_ref, _ = plugin.evaluate_covenant_risk(raw_text, raw_facts)

    # 3. Semantic interpretation with deterministic immutability
    semantic_data = extract_semantic_interpretation_rules(raw_text, raw_facts)
    structured_interpretation = enforce_deterministic_immutability(raw_facts, semantic_data)

    # 4. Simplified explanation
    simplified_expl = generate_simplified_explanation(cat_id, raw_text, raw_facts)

    # 5. Evidence location
    evidence_loc = EvidenceLocation(
        page_number=page_number,
        char_start=char_offset,
        char_end=char_offset + len(raw_text),
        quote_snippet=raw_text[:150] + ("..." if len(raw_text) > 150 else ""),
    )

    title = f"{cat_name.split('&')[0].strip()} Covenant"
    if det_sections:
        title = f"{det_sections[0].full_reference}: {title}"

    return StructuredClauseRecord(
        clause_id=clause_id,
        section=section_name,
        title=title,
        page=page_number,
        clause_type=f"{cat_id}_covenant",
        category=cat_id,
        original_text=raw_text,
        simplified_explanation=simplified_expl,
        evidence_location=evidence_loc,
        deterministic_facts=deterministic_facts_model,
        structured_interpretation=structured_interpretation,
        extraction_confidence=0.98,
        interpretation_confidence=0.95,
        is_unfair=is_unfair,
        risk_level=risk_level,
        statutory_cross_reference=statutory_ref,
    )


async def analyze_clause_structured_async(
    clause_id: str,
    raw_text: str,
    page_number: int = 1,
    section_name: str = "General Covenants",
    char_offset: int = 0,
) -> StructuredClauseRecord:
    """
    Asynchronous Clause Intelligence analysis.
    Uses AI provider for semantic interpretation while guaranteeing deterministic immutability.
    """
    raw_facts = extract_deterministic_facts(raw_text)

    det_currencies = [
        DeterministicCurrency(currency=c["currency"], amount=c["amount"], raw_text=c["raw_text"])
        for c in raw_facts["currencies"]
    ]
    det_percentages = [
        DeterministicPercentage(value=p["value"], frequency=p["frequency"], raw_text=p["raw_text"])
        for p in raw_facts["percentages"]
    ]
    det_durations = [
        DeterministicDuration(
            count=d["count"],
            unit=d["unit"],
            days_equivalent=d["days_equivalent"],
            raw_text=d["raw_text"],
        )
        for d in raw_facts["durations"]
    ]
    det_dates = [
        DeterministicDate(
            date_string=dt["date_string"], format=dt["format"], raw_text=dt["raw_text"]
        )
        for dt in raw_facts["dates"]
    ]
    det_sections = [
        DeterministicSection(
            prefix=s["prefix"], number=s["number"], full_reference=s["full_reference"]
        )
        for s in raw_facts["sections"]
    ]

    deterministic_facts_model = DeterministicFacts(
        currencies=det_currencies,
        percentages=det_percentages,
        durations=det_durations,
        dates=det_dates,
        sections=det_sections,
    )

    cat_id, cat_name = taxonomy_registry.classify_clause(raw_text)
    plugin = taxonomy_registry.get(cat_id)

    risk_level = "LOW"
    is_unfair = False
    statutory_ref = None

    if plugin:
        risk_level, is_unfair, statutory_ref, _ = plugin.evaluate_covenant_risk(raw_text, raw_facts)

    # Call AI Provider for semantic interpretation
    ai_provider = get_ai_provider()
    try:
        raw_ai_semantics = await ai_provider.interpret_clause(raw_text, raw_facts)
    except Exception as e:
        logger.warning(f"AI clause interpretation failed ({e}), using rule-based extraction.")
        raw_ai_semantics = extract_semantic_interpretation_rules(raw_text, raw_facts)

    # Enforce deterministic immutability: AI values CANNOT silently overwrite deterministic values
    structured_interpretation = enforce_deterministic_immutability(raw_facts, raw_ai_semantics)

    simplified_expl = generate_simplified_explanation(cat_id, raw_text, raw_facts)

    evidence_loc = EvidenceLocation(
        page_number=page_number,
        char_start=char_offset,
        char_end=char_offset + len(raw_text),
        quote_snippet=raw_text[:150] + ("..." if len(raw_text) > 150 else ""),
    )

    title = f"{cat_name.split('&')[0].strip()} Covenant"
    if det_sections:
        title = f"{det_sections[0].full_reference}: {title}"

    return StructuredClauseRecord(
        clause_id=clause_id,
        section=section_name,
        title=title,
        page=page_number,
        clause_type=f"{cat_id}_covenant",
        category=cat_id,
        original_text=raw_text,
        simplified_explanation=simplified_expl,
        evidence_location=evidence_loc,
        deterministic_facts=deterministic_facts_model,
        structured_interpretation=structured_interpretation,
        extraction_confidence=0.98,
        interpretation_confidence=0.96,
        is_unfair=is_unfair,
        risk_level=risk_level,
        statutory_cross_reference=statutory_ref,
    )


def process_document_clauses(full_text: str, default_page: int = 1) -> List[StructuredClauseRecord]:
    """
    End-to-end Clause Intelligence processing for a complete document text (synchronous).
    Returns list of validated StructuredClauseRecords.
    """
    candidates = segment_clauses_from_text(full_text, default_page=default_page)
    records = []
    char_cursor = 0

    for c in candidates:
        rec = analyze_clause_structured(
            clause_id=c["clause_id"],
            raw_text=c["text"],
            page_number=c.get("page", default_page),
            section_name=c.get("section", "General Covenants"),
            char_offset=char_cursor,
        )
        records.append(rec)
        char_cursor += len(c["text"]) + 2

    return records


async def process_document_clauses_async(
    full_text: str, default_page: int = 1
) -> List[StructuredClauseRecord]:
    """
    End-to-end Clause Intelligence processing for a complete document text (asynchronous with AI).
    Returns list of validated StructuredClauseRecords.
    """
    candidates = segment_clauses_from_text(full_text, default_page=default_page)
    records = []
    char_cursor = 0

    for c in candidates:
        rec = await analyze_clause_structured_async(
            clause_id=c["clause_id"],
            raw_text=c["text"],
            page_number=c.get("page", default_page),
            section_name=c.get("section", "General Covenants"),
            char_offset=char_cursor,
        )
        records.append(rec)
        char_cursor += len(c["text"]) + 2

    return records
