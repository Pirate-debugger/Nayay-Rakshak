"""
Action Navigator — Hard Escalation Rules
=========================================
Evaluates whether professional review is required based on OBJECTIVE, DETERMINISTIC
conditions derived from the risk engine output.

The LLM CANNOT override or suppress escalation triggers.
Thresholds are hard-coded and versioned here.

Escalation ruleset version: 2024.1.0
"""

from __future__ import annotations

import re
from typing import Any, List

from app.schemas.action_navigator import (
    EscalationTrigger,
    EscalationTriggerType,
    IssueSeverity,
    UrgencyLevel,
)
from app.schemas.risk import RiskCategory, RiskSeverity

# ─── Constants ────────────────────────────────────────────────────────────────

FINANCIAL_THRESHOLD_INR = 50_000   # ₹50,000 — professional review mandatory above this
HIGH_RISK_COUNT_THRESHOLD = 3       # ≥3 HIGH severity risks → escalate

_COURT_KEYWORDS = re.compile(
    r"\b(court|tribunal|lawsuit|litigation|suit|proceeding|fir|police|criminal|prosecution|offence)\b",
    re.IGNORECASE,
)

_FINANCIAL_RE = re.compile(
    r"(?:₹|Rs\.?\s*)(\d[\d,]*(?:\.\d+)?)\s*(?:lakh|crore|lac)?",
    re.IGNORECASE,
)

_NALSA_NOTE = "Qualified Advocate. Free legal aid available via NALSA at 15100 (nalsa.gov.in)."
_CONSUMER_NOTE = "Qualified Advocate or District Consumer Commission (edaakhil.nic.in)."
_ARBITRATION_NOTE = "Qualified Advocate experienced in arbitration (Arbitration & Conciliation Act, 1996)."


def _parse_inr(text: str) -> float:
    """Return the largest INR amount found in text."""
    amounts = []
    for m in _FINANCIAL_RE.finditer(text):
        raw = float(m.group(1).replace(",", ""))
        context = text[m.start(): m.end() + 5].lower()
        if "lakh" in context or "lac" in context:
            raw *= 100_000
        elif "crore" in context:
            raw *= 10_000_000
        amounts.append(raw)
    return max(amounts, default=0.0)


def evaluate_escalation(
    risk_engine_result: Any,           # RiskEngineResult
    analysis_risks: List[dict],
    document_full_text: str,
) -> List[EscalationTrigger]:
    """
    Evaluate all hard escalation triggers.
    Returns a list of EscalationTrigger objects; empty list = no escalation.
    All triggers are boolean — determined by objective conditions.
    """
    triggers: List[EscalationTrigger] = []
    risk_records = getattr(risk_engine_result, "risks", [])
    missing = getattr(risk_engine_result, "missing_protections", [])

    # ── Rule 1: Any CRITICAL severity risk ──────────────────────────────────
    critical_risks = [
        r for r in risk_records
        if getattr(r, "severity", None) == RiskSeverity.CRITICAL
        or (hasattr(r, "severity") and getattr(r.severity, "value", "") == "CRITICAL")
    ]
    if critical_risks:
        r = critical_risks[0]
        triggers.append(EscalationTrigger(
            trigger_type=EscalationTriggerType.CRITICAL_RISK_DETECTED,
            reason=(
                f"At least {len(critical_risks)} CRITICAL severity risk(s) detected "
                f"in this document. Example: '{getattr(r, 'title', 'Critical risk')}'. "
                "Critical risks require professional interpretation."
            ),
            severity=IssueSeverity.CRITICAL,
            recommended_resource=_NALSA_NOTE,
            source_risk_id=getattr(r, "risk_id", None),
        ))

    # ── Rule 2: ≥ HIGH_RISK_COUNT_THRESHOLD HIGH severity risks ─────────────
    high_risks = [
        r for r in risk_records
        if getattr(r, "severity", None) == RiskSeverity.HIGH
        or (hasattr(r, "severity") and getattr(r.severity, "value", "") == "HIGH")
    ]
    if len(high_risks) >= HIGH_RISK_COUNT_THRESHOLD:
        triggers.append(EscalationTrigger(
            trigger_type=EscalationTriggerType.MULTIPLE_HIGH_RISKS,
            reason=(
                f"{len(high_risks)} HIGH severity risks were identified. "
                "When multiple high-severity issues appear together, the cumulative risk "
                "warrants professional assessment."
            ),
            severity=IssueSeverity.HIGH,
            recommended_resource=_NALSA_NOTE,
            source_risk_id=None,
        ))

    # ── Rule 3: Uncapped indemnity ────────────────────────────────────────────
    indemnity_risks = [
        r for r in risk_records
        if getattr(r, "category", None) in (RiskCategory.INDEMNITY, "INDEMNITY")
        or (hasattr(r, "category") and getattr(r.category, "value", "") == "INDEMNITY")
    ]
    uncapped = [
        r for r in indemnity_risks
        if re.search(
            r"\b(unlimited|uncapped|without limit|no cap|no limit|full|entire|all)\b",
            getattr(r, "evidence", None) and getattr(r.evidence, "verbatim_quote", "") or "",
            re.IGNORECASE,
        )
    ]
    if uncapped:
        triggers.append(EscalationTrigger(
            trigger_type=EscalationTriggerType.UNCAPPED_INDEMNITY,
            reason=(
                "This document appears to contain an uncapped indemnity clause. "
                "Unlimited financial liability is one of the most serious risks in "
                "a contract and must be assessed by a qualified advocate."
            ),
            severity=IssueSeverity.CRITICAL,
            recommended_resource=_NALSA_NOTE,
            source_risk_id=getattr(uncapped[0], "risk_id", None),
        ))

    # ── Rule 4: Missing dispute resolution mechanism ──────────────────────────
    arb_risks = [
        r for r in risk_records
        if getattr(r, "category", None) in (RiskCategory.ARBITRATION, "ARBITRATION")
        or (hasattr(r, "category") and getattr(r.category, "value", "") == "ARBITRATION")
    ]
    missing_dispute = [
        m for m in missing
        if "dispute" in getattr(m, "title", "").lower()
        or "arbitration" in getattr(m, "title", "").lower()
    ]
    if arb_risks or missing_dispute:
        triggers.append(EscalationTrigger(
            trigger_type=EscalationTriggerType.MISSING_DISPUTE_RESOLUTION,
            reason=(
                "The document lacks a clear, enforceable dispute resolution mechanism. "
                "Without this, you may not know which forum to approach in case of a dispute."
            ),
            severity=IssueSeverity.HIGH,
            recommended_resource=_ARBITRATION_NOTE,
            source_risk_id=getattr(arb_risks[0], "risk_id", None) if arb_risks else None,
        ))

    # ── Rule 5: Court / criminal keywords in document ─────────────────────────
    if _COURT_KEYWORDS.search(document_full_text):
        # Only trigger if it seems like an active matter, not just a governing-law clause
        # Heuristic: multiple hits suggests this is about a dispute, not just boilerplate
        hits = _COURT_KEYWORDS.findall(document_full_text)
        if len(hits) >= 2:
            triggers.append(EscalationTrigger(
                trigger_type=EscalationTriggerType.COURT_MATTER,
                reason=(
                    "The document references court proceedings, tribunal, or criminal matters. "
                    "If this document relates to an active or potential legal proceeding, "
                    "professional representation is strongly advisable."
                ),
                severity=IssueSeverity.HIGH,
                recommended_resource=_NALSA_NOTE,
                source_risk_id=None,
            ))

    # ── Rule 6: Significant financial exposure ────────────────────────────────
    max_amount = _parse_inr(document_full_text)
    if max_amount >= FINANCIAL_THRESHOLD_INR:
        triggers.append(EscalationTrigger(
            trigger_type=EscalationTriggerType.HIGH_FINANCIAL_EXPOSURE,
            reason=(
                f"The document involves financial figures exceeding "
                f"₹{max_amount:,.0f}. Contracts involving significant sums "
                "benefit from professional review to avoid costly errors."
            ),
            severity=IssueSeverity.HIGH,
            recommended_resource=_NALSA_NOTE,
            source_risk_id=None,
        ))

    # ── Rule 7: Jurisdiction conflicts ────────────────────────────────────────
    jurisdiction_risks = [
        r for r in risk_records
        if getattr(r, "category", None) in (RiskCategory.JURISDICTION, "JURISDICTION")
        or (hasattr(r, "category") and getattr(r.category, "value", "") == "JURISDICTION")
    ]
    if jurisdiction_risks:
        triggers.append(EscalationTrigger(
            trigger_type=EscalationTriggerType.JURISDICTION_CONFLICT,
            reason=(
                "A jurisdiction issue was detected. Proceeding without understanding "
                "which court or law applies may affect your ability to seek redress."
            ),
            severity=IssueSeverity.HIGH,
            recommended_resource=_NALSA_NOTE,
            source_risk_id=getattr(jurisdiction_risks[0], "risk_id", None),
        ))

    # ── Rule 8: Serious rights impact — serious rights-stripping clauses ──────
    serious_rights = [
        r for r in risk_records
        if (
            getattr(r, "severity", None) in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)
            or (hasattr(r, "severity") and getattr(r.severity, "value", "") in ("HIGH", "CRITICAL"))
        ) and any(
            kw in getattr(r, "title", "").lower()
            for kw in ("waive", "forfeit", "surrender", "relinquish", "fundamental", "constitutional")
        )
    ]
    if serious_rights:
        triggers.append(EscalationTrigger(
            trigger_type=EscalationTriggerType.SERIOUS_RIGHTS_IMPACT,
            reason=(
                f"The document may require you to waive, forfeit, or relinquish "
                f"significant rights. Example: '{getattr(serious_rights[0], 'title', '')}'. "
                "Right-waiver clauses should always be reviewed by a professional."
            ),
            severity=IssueSeverity.CRITICAL,
            recommended_resource=_NALSA_NOTE,
            source_risk_id=getattr(serious_rights[0], "risk_id", None),
        ))

    # Deduplicate by trigger_type
    seen_types: set[str] = set()
    unique: List[EscalationTrigger] = []
    for t in triggers:
        if t.trigger_type not in seen_types:
            seen_types.add(t.trigger_type)
            unique.append(t)

    return unique


def compute_professional_review_urgency(
    triggers: List[EscalationTrigger],
) -> UrgencyLevel:
    """Return the highest urgency across all triggers."""
    if not triggers:
        return UrgencyLevel.LOW
    severities = [t.severity for t in triggers]
    if IssueSeverity.CRITICAL in severities:
        return UrgencyLevel.HIGH
    if IssueSeverity.HIGH in severities:
        return UrgencyLevel.MEDIUM
    return UrgencyLevel.LOW
