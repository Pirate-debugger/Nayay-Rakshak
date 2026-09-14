import re
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.comparison import (
    ComparisonCategory,
    ComparisonFindingItem,
    DifferenceDimension,
    DocumentEvidence,
    MaterialityLevel,
)
from app.services.comparison.matcher import AlignedClausePair, normalize_ocr_text
from app.services.comparison.segmenter import ComparisonClause


def detect_negation_inversion(text_a: str, text_b: str) -> Optional[str]:
    """
    Detects polarity inversions between two clauses (e.g., 'shall' vs 'shall not',
    'may' vs 'may not', 'permitted' vs 'prohibited', 'with' vs 'without').
    """
    a_lower = normalize_ocr_text(text_a).lower()
    b_lower = normalize_ocr_text(text_b).lower()

    inversion_pairs = [
        (r"\bshall\b(?!\s+not)", r"\bshall\s+not\b", "Replaced affirmative obligation ('shall') with strict prohibition ('shall not')"),
        (r"\bshall\s+not\b", r"\bshall\b(?!\s+not)", "Replaced prohibition ('shall not') with affirmative obligation ('shall')"),
        (r"\bmay\b(?!\s+not)", r"\bmay\s+not\b", "Replaced permissive right ('may') with denial of right ('may not')"),
        (r"\bmay\s+not\b", r"\bmay\b(?!\s+not)", "Granted permissive right ('may') where previously prohibited ('may not')"),
        (r"\bmay\b(?!\s+not)", r"\bshall\s+not\b", "Replaced permissive right ('may') with strict prohibition ('shall not')"),
        (r"\bshall\s+not\b", r"\bmay\b(?!\s+not)", "Replaced strict prohibition ('shall not') with permissive right ('may')"),
        (r"\bshall\b(?!\s+not)", r"\bmay\s+not\b", "Replaced affirmative obligation ('shall') with denial of right ('may not')"),
        (r"\bmay\s+not\b", r"\bshall\b(?!\s+not)", "Replaced denial of right ('may not') with affirmative obligation ('shall')"),
        (r"\bentitled\s+to\b", r"\bnot\s+entitled\s+to\b", "Removed entitlement right"),
        (r"\bnot\s+entitled\s+to\b", r"\bentitled\s+to\b", "Granted entitlement right"),
        (r"\bwith(?:\s+prior)?\s+consent\b", r"\bwithout(?:\s+prior)?\s+consent\b", "Removed requirement for consent ('without consent')"),
        (r"\bwithout(?:\s+prior)?\s+consent\b", r"\bwith(?:\s+prior)?\s+consent\b", "Added requirement for consent ('with consent')"),
        (r"\bno\s+right\s+to\s+terminate\b", r"\bright\s+to\s+terminate\b", "Granted termination right"),
        (r"\bright\s+to\s+terminate\b", r"\bno\s+right\s+to\s+terminate\b", "Eliminated termination right ('no right to terminate')"),
        (r"\bwaive\b|\bwaiver\b", r"\bno\s+waiver\b", "Replaced waiver with non-waiver protection"),
        (r"\bno\s+waiver\b", r"\bwaive\b|\bwaiver\b", "Introduced waiver of legal rights or claims"),
        (r"\bpermitted\b", r"\bprohibited\b", "Swapped permitted action to prohibited action"),
        (r"\bprohibited\b", r"\bpermitted\b", "Swapped prohibited action to permitted action"),
    ]

    for pat_a, pat_b, desc in inversion_pairs:
        if re.search(pat_a, a_lower) and re.search(pat_b, b_lower):
            return desc

    return None


def detect_financial_difference(clause_a: ComparisonClause, clause_b: ComparisonClause) -> Optional[Tuple[str, MaterialityLevel, str]]:
    """
    Compares monetary figures, currency units, interest rates, and fee caps.
    Returns (explanation, materiality, risk_implications) if a financial discrepancy exists.
    """
    facts_a = clause_a.facts
    facts_b = clause_b.facts

    # 1. Percentage / Interest comparison
    pct_a = sorted([p["value"] for p in facts_a.get("percentages", [])])
    pct_b = sorted([p["value"] for p in facts_b.get("percentages", [])])
    
    if pct_a != pct_b and (pct_a or pct_b):
        max_a = max(pct_a) if pct_a else 0.0
        max_b = max(pct_b) if pct_b else 0.0
        if max_b > max_a:
            diff = max_b - max_a
            materiality = MaterialityLevel.CRITICAL if max_b >= 12.0 else MaterialityLevel.MATERIAL
            expl = f"Interest/penalty rate increased from {max_a}% to {max_b}% (+{diff:.1f}%)."
            risk = f"Increases borrowing or late payment interest liability significantly, potentially exceeding statutory usury thresholds."
            return expl, materiality, risk
        elif max_a > max_b:
            expl = f"Interest/penalty rate decreased from {max_a}% to {max_b}%."
            risk = "Favorable reduction in late fee interest rate."
            return expl, MaterialityLevel.MEDIUM, risk

    # 2. Currency amounts comparison
    cur_a = sorted([c["amount"] for c in facts_a.get("currencies", [])])
    cur_b = sorted([c["amount"] for c in facts_b.get("currencies", [])])
    
    if cur_a != cur_b and (cur_a or cur_b):
        tot_a = sum(cur_a)
        tot_b = sum(cur_b)
        if tot_b > tot_a:
            materiality = MaterialityLevel.CRITICAL if (tot_b > 2 * tot_a and tot_a > 0) else MaterialityLevel.MATERIAL
            expl = f"Financial payment/deposit increased from ₹{tot_a:,.0f} to ₹{tot_b:,.0f}."
            risk = "Direct monetary increase in citizen financial outflow or deposit lock-in."
            return expl, materiality, risk
        elif tot_a > tot_b:
            expl = f"Financial payment/deposit decreased from ₹{tot_a:,.0f} to ₹{tot_b:,.0f}."
            risk = "Reduction in stated financial obligations."
            return expl, MaterialityLevel.MEDIUM, risk

    # 3. Daily penalty / compounding keywords
    b_lower = clause_b.text.lower()
    a_lower = clause_a.text.lower()
    if ("compounding" in b_lower or "per day" in b_lower or "daily" in b_lower) and not ("compounding" in a_lower or "per day" in a_lower or "daily" in a_lower):
        return (
            "Target introduces daily compounding fines / per-day late fees absent in base document.",
            MaterialityLevel.CRITICAL,
            "Daily compounding penalties accumulate exponentially, creating extreme debt risk."
        )

    return None


def detect_deadline_difference(clause_a: ComparisonClause, clause_b: ComparisonClause) -> Optional[Tuple[str, MaterialityLevel, str]]:
    """
    Compares time limits, notice durations, and cure periods.
    """
    facts_a = clause_a.facts
    facts_b = clause_b.facts

    dur_a = [d for d in facts_a.get("durations", [])]
    dur_b = [d for d in facts_b.get("durations", [])]

    comb_lower = (clause_a.text + " " + clause_b.text).lower()
    if "limitation of liability" in comb_lower or "maximum aggregate liability" in comb_lower:
        return None

    # Compare equivalent days
    days_a = sorted([d["days_equivalent"] for d in dur_a])
    days_b = sorted([d["days_equivalent"] for d in dur_b])

    if days_a != days_b and (days_a or days_b):
        min_a = min(days_a) if days_a else 0
        min_b = min(days_b) if days_b else 0
        
        # Notice or cure period shortened
        if min_b < min_a and min_b > 0:
            materiality = MaterialityLevel.CRITICAL if min_b <= 7 and min_a >= 30 else MaterialityLevel.MATERIAL
            expl = f"Notice/compliance timeline shortened from {min_a:.0f} days to {min_b:.0f} days."
            risk = f"Drastically reduced response window; failure to comply in {min_b:.0f} days may trigger immediate default or termination."
            return expl, materiality, risk
        elif min_b > min_a and min_a > 0:
            # e.g., deposit refund delayed from 14 days to 90 days
            b_lower = clause_b.text.lower()
            if any(k in b_lower for k in ["refund", "deposit", "return"]):
                materiality = MaterialityLevel.CRITICAL if min_b >= 60 else MaterialityLevel.MATERIAL
                expl = f"Refund/return SLA extended from {min_a:.0f} days to {min_b:.0f} days."
                risk = f"Citizen capital is retained by counterparty for up to {min_b:.0f} days post-vacating."
                return expl, materiality, risk
            else:
                expl = f"Timeline adjusted from {min_a:.0f} days to {min_b:.0f} days."
                risk = "Adjustment in contractual timeframe."
                return expl, MaterialityLevel.MEDIUM, risk

    return None


def detect_liability_difference(clause_a: ComparisonClause, clause_b: ComparisonClause) -> Optional[Tuple[str, MaterialityLevel, str]]:
    """
    Detects shifts toward uncapped liabilities, indemnities, or loss of protection.
    """
    a_lower = clause_a.text.lower()
    b_lower = clause_b.text.lower()

    # Uncapped liability insertion
    if any(k in b_lower for k in ["unlimited liability", "no cap on liability", "entire liability"]) and not any(k in a_lower for k in ["unlimited liability", "no cap"]):
        indem_note = " and blanket indemnity" if "indemnif" in b_lower else ""
        return (
            f"Target introduces uncapped / unlimited liability{indem_note} for citizen.",
            MaterialityLevel.CRITICAL,
            "Removes contractual damage cap, exposing all personal assets to potential breach claims."
        )

    # Indemnity insertion
    if any(k in b_lower for k in ["indemnify and hold harmless", "defend and indemnify", "all claims, damages and losses"]) and not any(k in a_lower for k in ["indemnify"]):
        return (
            "Target introduces expansive unilateral indemnity obligation.",
            MaterialityLevel.CRITICAL,
            "Transfers broad legal defence and damage costs to citizen, even without judicial determination of fault."
        )

    # Gross negligence waiver
    if "gross negligence" in b_lower and any(w in b_lower for w in ["waive", "disclaim", "exclude", "not liable"]):
        if not ("gross negligence" in a_lower and any(w in a_lower for w in ["waive", "disclaim"])):
            return (
                "Target disclaims counterparty liability for gross negligence.",
                MaterialityLevel.CRITICAL,
                "Excludes liability even for egregious willful misconduct, which is legally disfavored under Indian contract law."
            )

    return None


def detect_termination_difference(clause_a: ComparisonClause, clause_b: ComparisonClause) -> Optional[Tuple[str, MaterialityLevel, str]]:
    """
    Detects asymmetric termination power or removal of mutual exit rights.
    """
    a_lower = clause_a.text.lower()
    b_lower = clause_b.text.lower()

    if any(k in b_lower for k in ["sole discretion", "unilateral", "without cause", "immediate termination"]) and not any(k in a_lower for k in ["sole discretion", "unilateral", "without cause"]):
        return (
            "Target grants counterparty unilateral immediate termination rights.",
            MaterialityLevel.CRITICAL,
            "Creates severe tenure insecurity; counterparty can terminate without affording a cure opportunity."
        )

    if ("tenant shall not terminate" in b_lower or "no right to terminate" in b_lower or "lock-in" in b_lower) and not ("no right to terminate" in a_lower or "lock-in" in a_lower):
        return (
            "Target strips citizen of right to terminate early (strict lock-in covenant).",
            MaterialityLevel.CRITICAL,
            "Forces citizen to remain bound to contract and payment obligations regardless of life circumstances."
        )

    return None


def detect_jurisdiction_difference(clause_a: ComparisonClause, clause_b: ComparisonClause) -> Optional[Tuple[str, MaterialityLevel, str]]:
    """
    Detects changes in dispute resolution forums, venue cities, or sole arbitrator appointments.
    """
    a_lower = clause_a.text.lower()
    b_lower = clause_b.text.lower()

    # Forum change: Courts vs Arbitration
    if ("arbitration" in b_lower or "arbitrator" in b_lower) and not ("arbitration" in a_lower or "arbitrator" in a_lower):
        is_sole = "sole arbitrator" in b_lower or "unilaterally appointed" in b_lower
        mat = MaterialityLevel.CRITICAL if is_sole else MaterialityLevel.MATERIAL
        risk = "Private arbitration is expensive and unilateral arbitrator appointment violates Section 12(5) of Arbitration & Conciliation Act." if is_sole else "Mandatory arbitration replaces public court forum."
        return (
            "Dispute resolution mechanism shifted from civil courts to mandatory arbitration.",
            mat,
            risk
        )

    # City/State change
    cities = ["delhi", "mumbai", "bengaluru", "bangalore", "kolkata", "chennai", "hyderabad", "pune", "gurugram", "noida"]
    found_a = [c for c in cities if c in a_lower]
    found_b = [c for c in cities if c in b_lower]
    if found_a and found_b and found_a != found_b:
        return (
            f"Jurisdiction seat changed from {found_a[0].title()} to {found_b[0].title()}.",
            MaterialityLevel.MATERIAL,
            f"Requires litigation or travel to {found_b[0].title()}, significantly increasing travel expenses and legal costs."
        )

    # Consumer court waiver
    if "consumer" in b_lower and any(w in b_lower for w in ["waive", "disclaim", "not maintain", "exclude"]):
        return (
            "Purported waiver of statutory consumer protection forum jurisdiction.",
            MaterialityLevel.CRITICAL,
            "Under Consumer Protection Act 2019, statutory consumer rights cannot be ousted by contract."
        )

    return None


def detect_obligation_and_rights_difference(clause_a: ComparisonClause, clause_b: ComparisonClause) -> Optional[Tuple[str, MaterialityLevel, str]]:
    """
    Detects expansion or reduction of non-financial rights and obligations.
    """
    a_lower = clause_a.text.lower()
    b_lower = clause_b.text.lower()

    # Non-compete / restraint of trade
    if any(k in b_lower for k in ["non-compete", "restraint", "shall not work", "shall not engage"]) and not any(k in a_lower for k in ["non-compete", "restraint"]):
        return (
            "Target introduces post-termination non-compete restriction.",
            MaterialityLevel.CRITICAL,
            "Restricts citizen right to practice trade/profession, void under Section 27 of Indian Contract Act 1872."
        )

    # Broad IP assignment
    if any(k in b_lower for k in ["moral rights", "perpetual irrevocable", "all personal inventions"]) and not any(k in a_lower for k in ["moral rights", "personal inventions"]):
        return (
            "Target expands IP assignment to personal inventions and moral rights.",
            MaterialityLevel.MATERIAL,
            "Transfers ownership of works developed outside working hours or personal projects."
        )

    return None


def analyze_aligned_clause_pair(
    pair: AlignedClausePair,
    finding_index: int
) -> ComparisonFindingItem:
    """
    Inspects a matched or unmatched pair of clauses across all 9 legal dimensions
    and outputs a structured ComparisonFindingItem with verified evidence.
    """
    fid = f"FINDING-{finding_index:03d}"
    ca = pair.clause_a
    cb = pair.clause_b
    sim = pair.similarity

    # 1. Unmatched A -> REMOVED / MISSING
    if ca is not None and cb is None:
        heading_lower = ca.section_heading.lower()
        is_protection = any(k in heading_lower or k in ca.text.lower() for k in ["cure", "grace", "quiet enjoyment", "deposit refund", "notice period", "dispute"])
        materiality = MaterialityLevel.CRITICAL if is_protection else MaterialityLevel.MATERIAL
        
        return ComparisonFindingItem(
            finding_id=fid,
            category=ComparisonCategory.REMOVED,
            dimension=DifferenceDimension.STRUCTURAL,
            title=f"Clause Removed: {ca.section_heading}",
            document_a_evidence=DocumentEvidence(
                document_id=ca.document_id,
                document_title=ca.document_title,
                clause_id=ca.clause_id,
                section_heading=ca.section_heading,
                page_number=ca.page_number,
                verbatim_quote=ca.text[:300].strip(),
                char_start=ca.char_start,
                char_end=ca.char_end
            ),
            document_b_evidence=None,
            difference_explanation=f"Clause '{ca.section_heading}' present in original agreement was completely omitted in target draft.",
            materiality=materiality,
            risk_implications="Citizen loses protective covenants, warranties, or procedural rights present in the base draft.",
            confidence=0.95,
            semantic_similarity=0.0
        )

    # 2. Unmatched B -> NEW
    if ca is None and cb is not None:
        heading_lower = cb.section_heading.lower()
        is_harsh = any(k in heading_lower or k in cb.text.lower() for k in ["penalty", "indemnity", "non-compete", "interest", "forfeit", "sole discretion"])
        materiality = MaterialityLevel.CRITICAL if is_harsh else MaterialityLevel.MATERIAL
        
        return ComparisonFindingItem(
            finding_id=fid,
            category=ComparisonCategory.NEW,
            dimension=DifferenceDimension.STRUCTURAL,
            title=f"Newly Added Clause: {cb.section_heading}",
            document_a_evidence=None,
            document_b_evidence=DocumentEvidence(
                document_id=cb.document_id,
                document_title=cb.document_title,
                clause_id=cb.clause_id,
                section_heading=cb.section_heading,
                page_number=cb.page_number,
                verbatim_quote=cb.text[:300].strip(),
                char_start=cb.char_start,
                char_end=cb.char_end
            ),
            difference_explanation=f"New clause '{cb.section_heading}' introduced in target draft with no counterpart in base draft.",
            materiality=materiality,
            risk_implications="Introduces new binding covenants, restrictions, or operational burdens not agreed to in base terms.",
            confidence=0.95,
            semantic_similarity=0.0
        )

    # 3. Both clauses present: Deep Semantic Discrepancy Inspection
    assert ca is not None and cb is not None

    ev_a = DocumentEvidence(
        document_id=ca.document_id,
        document_title=ca.document_title,
        clause_id=ca.clause_id,
        section_heading=ca.section_heading,
        page_number=ca.page_number,
        verbatim_quote=ca.text[:300].strip(),
        char_start=ca.char_start,
        char_end=ca.char_end
    )
    ev_b = DocumentEvidence(
        document_id=cb.document_id,
        document_title=cb.document_title,
        clause_id=cb.clause_id,
        section_heading=cb.section_heading,
        page_number=cb.page_number,
        verbatim_quote=cb.text[:300].strip(),
        char_start=cb.char_start,
        char_end=cb.char_end
    )

    # 3a. Negation / Polarity Inversion (CONFLICTING)
    neg_diff = detect_negation_inversion(ca.text, cb.text)
    if neg_diff:
        return ComparisonFindingItem(
            finding_id=fid,
            category=ComparisonCategory.CONFLICTING,
            dimension=DifferenceDimension.RIGHTS,
            title=f"Direct Legal Conflict: {cb.section_heading}",
            document_a_evidence=ev_a,
            document_b_evidence=ev_b,
            difference_explanation=neg_diff,
            materiality=MaterialityLevel.CRITICAL,
            risk_implications="Inversion of rights directly opposes base terms, creating potential dispute and loss of legal remedy.",
            confidence=0.95,
            semantic_similarity=sim
        )

    # 3b. Liability & Indemnity (MODIFIED / CONFLICTING)
    liab_diff = detect_liability_difference(ca, cb)
    if liab_diff:
        expl, mat, risk = liab_diff
        return ComparisonFindingItem(
            finding_id=fid,
            category=ComparisonCategory.MODIFIED,
            dimension=DifferenceDimension.LIABILITY,
            title=f"Liability Escalation: {cb.section_heading}",
            document_a_evidence=ev_a,
            document_b_evidence=ev_b,
            difference_explanation=expl,
            materiality=mat,
            risk_implications=risk,
            confidence=0.93,
            semantic_similarity=sim
        )

    # 3c. Termination Discrepancies (MODIFIED / CONFLICTING)
    term_diff = detect_termination_difference(ca, cb)
    if term_diff:
        expl, mat, risk = term_diff
        return ComparisonFindingItem(
            finding_id=fid,
            category=ComparisonCategory.MODIFIED,
            dimension=DifferenceDimension.TERMINATION,
            title=f"Termination Terms Modified: {cb.section_heading}",
            document_a_evidence=ev_a,
            document_b_evidence=ev_b,
            difference_explanation=expl,
            materiality=mat,
            risk_implications=risk,
            confidence=0.90,
            semantic_similarity=sim
        )

    # 3d. Jurisdiction & Dispute Resolution (MODIFIED)
    jur_diff = detect_jurisdiction_difference(ca, cb)
    if jur_diff:
        expl, mat, risk = jur_diff
        return ComparisonFindingItem(
            finding_id=fid,
            category=ComparisonCategory.MODIFIED,
            dimension=DifferenceDimension.JURISDICTION,
            title=f"Dispute Forum Modified: {cb.section_heading}",
            document_a_evidence=ev_a,
            document_b_evidence=ev_b,
            difference_explanation=expl,
            materiality=mat,
            risk_implications=risk,
            confidence=0.92,
            semantic_similarity=sim
        )

    # 3e. Financial Discrepancies (MODIFIED)
    fin_diff = detect_financial_difference(ca, cb)
    if fin_diff:
        expl, mat, risk = fin_diff
        comb_text = (ca.text + " " + cb.text).lower()
        if "penalty" in comb_text or "interest" in comb_text or "fine" in comb_text:
            title_prefix = "Late Rent Penalty & Interest"
        elif "rent" in comb_text:
            title_prefix = "Rent & Payment Terms"
        elif "deposit" in comb_text:
            title_prefix = "Security Deposit Terms"
        else:
            title_prefix = "Financial Terms Altered"

        return ComparisonFindingItem(
            finding_id=fid,
            category=ComparisonCategory.MODIFIED,
            dimension=DifferenceDimension.FINANCIAL,
            title=f"{title_prefix}: {cb.section_heading}",
            document_a_evidence=ev_a,
            document_b_evidence=ev_b,
            difference_explanation=expl,
            materiality=mat,
            risk_implications=risk,
            confidence=0.92,
            semantic_similarity=sim
        )

    # 3f. Deadline / Temporal Discrepancies (MODIFIED)
    dl_diff = detect_deadline_difference(ca, cb)
    if dl_diff:
        expl, mat, risk = dl_diff
        return ComparisonFindingItem(
            finding_id=fid,
            category=ComparisonCategory.MODIFIED,
            dimension=DifferenceDimension.DEADLINE,
            title=f"Timeline / Notice Shift: {cb.section_heading}",
            document_a_evidence=ev_a,
            document_b_evidence=ev_b,
            difference_explanation=expl,
            materiality=mat,
            risk_implications=risk,
            confidence=0.90,
            semantic_similarity=sim
        )

    # 3g. Obligations & Rights (MODIFIED)
    ob_diff = detect_obligation_and_rights_difference(ca, cb)
    if ob_diff:
        expl, mat, risk = ob_diff
        return ComparisonFindingItem(
            finding_id=fid,
            category=ComparisonCategory.MODIFIED,
            dimension=DifferenceDimension.OBLIGATION,
            title=f"Obligation / Right Shift: {cb.section_heading}",
            document_a_evidence=ev_a,
            document_b_evidence=ev_b,
            difference_explanation=expl,
            materiality=mat,
            risk_implications=risk,
            confidence=0.88,
            semantic_similarity=sim
        )

    # 4. Check for Identical vs Similar vs Reordered
    norm_a = normalize_ocr_text(ca.text)
    norm_b = normalize_ocr_text(cb.text)
    
    if norm_a.lower() == norm_b.lower() or sim >= 0.98:
        title = f"Identical Clause: {cb.section_heading}"
        if pair.is_reordered:
            title += " (Reordered in Target)"
        return ComparisonFindingItem(
            finding_id=fid,
            category=ComparisonCategory.IDENTICAL,
            dimension=DifferenceDimension.GENERAL_TERMS,
            title=title,
            document_a_evidence=ev_a,
            document_b_evidence=ev_b,
            difference_explanation="Both documents contain semantically identical operative language for this clause." + (" Note: clause was reordered in the target document." if pair.is_reordered else ""),
            materiality=MaterialityLevel.NEGLIGIBLE,
            risk_implications="No risk differential; clause obligations remain consistent across both drafts.",
            confidence=0.98,
            semantic_similarity=1.0
        )

    # High/moderate similarity without substantive discrepancies -> SIMILAR
    return ComparisonFindingItem(
        finding_id=fid,
        category=ComparisonCategory.SIMILAR,
        dimension=DifferenceDimension.GENERAL_TERMS,
        title=f"Similar Wording: {cb.section_heading}",
        document_a_evidence=ev_a,
        document_b_evidence=ev_b,
        difference_explanation="Wording differs stylistically or grammatically, but no substantive rights, timelines, or financial liabilities were altered.",
        materiality=MaterialityLevel.MINOR,
        risk_implications="Cosmetic rephrasing; legal effect remains largely unchanged.",
        confidence=round(max(0.65, sim), 2),
        semantic_similarity=round(sim, 3)
    )
