"""
Action Navigator — Issue Mapper
================================
Converts Risk Engine records (RiskRecord, RiskItem) into PotentialIssueItem
for the "Potential Issues" section of the Action Navigator.

This is purely a transformation layer — severity is mapped 1:1 from the
risk record; no re-evaluation is performed here.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.action_navigator import IssueSeverity, PotentialIssueItem

# Map risk categories to human-readable labels
_CATEGORY_LABELS: Dict[str, str] = {
    "FINANCIAL":             "Financial Risk",
    "TIME/DEADLINE":         "Deadline / Time Risk",
    "LIABILITY":             "Liability Exposure",
    "INDEMNITY":             "Indemnity Risk",
    "TERMINATION":           "Termination Risk",
    "PRIVACY":               "Privacy & Data Risk",
    "IP":                    "Intellectual Property Risk",
    "ARBITRATION":           "Arbitration / Dispute Risk",
    "JURISDICTION":          "Jurisdiction Risk",
    "RENEWAL":               "Auto-Renewal Risk",
    "OBLIGATION ASYMMETRY":  "Obligation Imbalance",
    "AMBIGUITY":             "Ambiguous / Unclear Terms",
    "MISSING PROTECTION":    "Missing Legal Protection",
}


def _map_severity(severity_str: str) -> IssueSeverity:
    s = severity_str.upper()
    if s in ("CRITICAL", "SEVERE"):
        return IssueSeverity.CRITICAL
    if s == "HIGH":
        return IssueSeverity.HIGH
    if s == "MEDIUM":
        return IssueSeverity.MEDIUM
    return IssueSeverity.LOW


def map_risks_to_issues(
    analysis_risks: List[Dict[str, Any]],
    risk_engine_records: List[Any],      # List[RiskRecord]
    missing_protections: List[Any],      # List[RiskRecord]
) -> List[PotentialIssueItem]:
    """
    Merge risk engine records and AI analysis risks into PotentialIssueItem list.
    Priority: risk engine records (deterministic) first, then AI analysis risks.
    """
    issues: List[PotentialIssueItem] = []
    seen_titles: set[str] = set()

    # 1. Risk Engine Records (most authoritative — deterministic + versioned rules)
    for rr in risk_engine_records:
        title = getattr(rr, "title", "")
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)

        cat_obj = getattr(rr, "category", "")
        cat_str = cat_obj.value if hasattr(cat_obj, "value") else str(cat_obj)
        cat_label = _CATEGORY_LABELS.get(cat_str.upper(), cat_str)

        sev_obj = getattr(rr, "severity", "MEDIUM")
        sev_str = sev_obj.value if hasattr(sev_obj, "value") else str(sev_obj)

        issues.append(PotentialIssueItem(
            issue=title,
            explanation=getattr(rr, "plain_language_explanation", getattr(rr, "finding", title)),
            potential_impact=getattr(rr, "why_it_matters", "This clause may affect your rights or obligations."),
            severity=_map_severity(sev_str),
            category=cat_label,
            source_risk_id=getattr(rr, "risk_id", None),
        ))

    # 2. Missing protections (risk engine)
    for mp in missing_protections:
        title = getattr(mp, "title", "")
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)

        cat_obj = getattr(mp, "category", "")
        cat_str = cat_obj.value if hasattr(cat_obj, "value") else str(cat_obj)

        issues.append(PotentialIssueItem(
            issue=title,
            explanation=getattr(mp, "plain_language_explanation", title),
            potential_impact=getattr(mp, "why_it_matters", "This absent clause may leave you without legal protection."),
            severity=IssueSeverity.HIGH,  # Missing protections default to HIGH
            category=_CATEGORY_LABELS.get(cat_str.upper(), "Missing Protection"),
            source_risk_id=getattr(mp, "risk_id", None),
        ))

    # 3. AI Analysis Risks (supplementary — lower confidence)
    for ar in analysis_risks:
        title = ar.get("title", ar.get("description", ""))
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)

        sev = ar.get("severity", "MEDIUM")
        cat = ar.get("category", "General")

        issues.append(PotentialIssueItem(
            issue=title,
            explanation=ar.get("description", title),
            potential_impact=ar.get("countermeasure", "Review this clause carefully."),
            severity=_map_severity(sev),
            category=_CATEGORY_LABELS.get(cat.upper(), cat),
            source_risk_id=ar.get("risk_id"),
        ))

    # Sort: CRITICAL → HIGH → MEDIUM → LOW
    _order = {IssueSeverity.CRITICAL: 0, IssueSeverity.HIGH: 1,
              IssueSeverity.MEDIUM: 2, IssueSeverity.LOW: 3}
    issues.sort(key=lambda i: _order.get(i.severity, 99))

    return issues[:20]
