"""
Action Navigator — Step Generator
====================================
Builds an ordered list of ActionStep objects derived entirely from
analysis data: risks, obligations, missing clauses, escalation triggers.

Steps are:
  1. Conservative ("consider", "review", "collect", "check") — never imperative guarantees
  2. Ordered by urgency (IMMEDIATE → HIGH → MEDIUM → LOW → INFORMATIONAL)
  3. Each carries an evidence_source linking to its origin
  4. Dependency-chained where logical (e.g., collect doc before reviewing it)

Steps never state a legal outcome. Language is always hedged.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.schemas.action_navigator import (
    ActionStep,
    EscalationTrigger,
    IssueSeverity,
    QuestionItem,
    UrgencyLevel,
)

# ─── Severity → Urgency mapping ───────────────────────────────────────────────

_SEV_TO_URGENCY: Dict[str, UrgencyLevel] = {
    "CRITICAL": UrgencyLevel.IMMEDIATE,
    "HIGH":     UrgencyLevel.HIGH,
    "MEDIUM":   UrgencyLevel.MEDIUM,
    "LOW":      UrgencyLevel.LOW,
    "SEVERE":   UrgencyLevel.IMMEDIATE,
}


def _urgency_order(u: UrgencyLevel) -> int:
    return {
        UrgencyLevel.IMMEDIATE: 0,
        UrgencyLevel.HIGH: 1,
        UrgencyLevel.MEDIUM: 2,
        UrgencyLevel.LOW: 3,
        UrgencyLevel.INFORMATIONAL: 4,
    }.get(u, 99)


# ─── Step Builders ────────────────────────────────────────────────────────────

def _build_risk_steps(risk_records: List[Any]) -> List[ActionStep]:
    """One ActionStep per risk, focusing on the recommended_question or countermeasure."""
    steps: List[ActionStep] = []
    for rr in risk_records:
        title = getattr(rr, "title", "")
        if not title:
            continue

        sev_obj = getattr(rr, "severity", "MEDIUM")
        sev_str = sev_obj.value if hasattr(sev_obj, "value") else str(sev_obj)
        urgency = _SEV_TO_URGENCY.get(sev_str.upper(), UrgencyLevel.MEDIUM)

        recommended_q = getattr(rr, "recommended_question", "")
        evidence_obj = getattr(rr, "evidence", None)
        evidence_quote = ""
        if evidence_obj:
            evidence_quote = getattr(evidence_obj, "verbatim_quote", "")[:80]

        source = getattr(rr, "risk_id", "?")
        action = (
            f"Review the '{title}' clause carefully. "
            + (f"Consider asking: {recommended_q}" if recommended_q else "")
        )

        steps.append(ActionStep(
            step_number=0,  # Will be renumbered at the end
            action=action.strip(),
            reason=getattr(rr, "why_it_matters", getattr(rr, "plain_language_explanation", "")),
            evidence_source=f"{source}" + (f": \"{evidence_quote}\"" if evidence_quote else ""),
            urgency=urgency,
            dependency=None,
            is_professional_review_step=getattr(rr, "professional_review_recommended", False),
        ))
    return steps


def _build_obligation_steps(obligations: List[Dict[str, Any]]) -> List[ActionStep]:
    steps: List[ActionStep] = []
    for ob in obligations:
        oid = ob.get("obligation_id", "?")
        party = ob.get("responsible_party", "A party")
        action = ob.get("action", "")
        deadline = ob.get("deadline_or_frequency", "")
        penalty = ob.get("penalty_for_breach", "")

        if not action:
            continue

        urgency = UrgencyLevel.MEDIUM
        if deadline and any(
            kw in deadline.lower()
            for kw in ("immediately", "within 24", "within 48", "urgent", "at once")
        ):
            urgency = UrgencyLevel.IMMEDIATE
        elif deadline and any(
            kw in deadline.lower()
            for kw in ("7 days", "7-day", "week")
        ):
            urgency = UrgencyLevel.HIGH

        step_action = (
            f"Note that {party} is obligated to: {action}"
            + (f" (by: {deadline})" if deadline else "")
            + ". Confirm this obligation is clearly understood and achievable."
        )

        steps.append(ActionStep(
            step_number=0,
            action=step_action,
            reason=(
                f"This is a stated obligation in the agreement"
                + (f". Non-compliance may result in: {penalty}" if penalty else ".")
            ),
            evidence_source=oid,
            urgency=urgency,
            dependency=None,
            is_professional_review_step=False,
        ))
    return steps


def _build_missing_clause_steps(missing_clauses: List[Dict[str, Any]]) -> List[ActionStep]:
    steps: List[ActionStep] = []
    for mc in missing_clauses:
        name = mc.get("clause_name", "")
        importance = mc.get("importance", "STANDARD")
        risk = mc.get("risk_if_missing", "")
        suggestion = mc.get("suggested_language", "")

        if not name:
            continue

        urgency = UrgencyLevel.HIGH if importance == "CRITICAL" else UrgencyLevel.MEDIUM
        action = (
            f"Request that a '{name}' clause be included before signing."
            + (f" Suggested language: \"{suggestion[:120]}...\"" if len(suggestion) > 120 else
               (f" Suggested language: \"{suggestion}\"" if suggestion else ""))
        )

        steps.append(ActionStep(
            step_number=0,
            action=action,
            reason=(
                f"This clause is absent, which may leave you without protection. "
                + (f"Risk: {risk}" if risk else "")
            ),
            evidence_source="missing_clause::" + name.replace(" ", "_"),
            urgency=urgency,
            dependency="Collect signed copy of the agreement",
            is_professional_review_step=False,
        ))
    return steps


def _build_escalation_steps(triggers: List[EscalationTrigger]) -> List[ActionStep]:
    if not triggers:
        return []

    step = ActionStep(
        step_number=0,
        action=(
            "Consult a qualified advocate before signing or acting on this document. "
            "Free legal aid is available via NALSA at 15100 or nalsa.gov.in."
        ),
        reason=(
            f"{len(triggers)} professional review trigger(s) were identified: "
            + "; ".join(t.trigger_type.value.replace("_", " ") for t in triggers[:3])
            + ("..." if len(triggers) > 3 else ".")
        ),
        evidence_source="escalation_engine::" + ",".join(
            t.trigger_type.value for t in triggers[:3]
        ),
        urgency=UrgencyLevel.HIGH if any(
            t.severity == IssueSeverity.CRITICAL for t in triggers
        ) else UrgencyLevel.MEDIUM,
        dependency=None,
        is_professional_review_step=True,
    )
    return [step]


def _build_document_collection_step() -> ActionStep:
    return ActionStep(
        step_number=0,
        action="Collect and securely store a fully signed copy of the agreement from all parties.",
        reason="A signed original is your primary legal record. Without it, proving agreed terms is difficult.",
        evidence_source="always_required::signed_agreement",
        urgency=UrgencyLevel.HIGH,
        dependency=None,
        is_professional_review_step=False,
    )


# ─── Question Builder ─────────────────────────────────────────────────────────

_COUNTERPARTY_CATEGORIES = {
    "FINANCIAL", "TERMINATION", "OBLIGATION ASYMMETRY", "RENEWAL",
    "LIABILITY", "INDEMNITY",
}
_ADVOCATE_CATEGORIES = {
    "JURISDICTION", "ARBITRATION", "MISSING PROTECTION", "IP", "AMBIGUITY",
}


def build_questions(
    risk_records: List[Any],
    missing_protections: List[Any],
    analysis_risks: List[Dict[str, Any]],
) -> List[QuestionItem]:
    """Build QuestionItem list from recommended_question fields in risk records."""
    questions: List[QuestionItem] = []
    seen: set[str] = set()

    def _ask_whom(cat_str: str) -> str:
        cat = cat_str.upper()
        if any(c in cat for c in _ADVOCATE_CATEGORIES):
            return "Your Advocate / Legal Adviser"
        if any(c in cat for c in _COUNTERPARTY_CATEGORIES):
            return "Counterparty / Other Party to the Agreement"
        return "Counterparty or Your Advocate"

    for rr in risk_records + missing_protections:
        q_text = getattr(rr, "recommended_question", "")
        if not q_text or q_text in seen:
            continue
        seen.add(q_text)

        cat_obj = getattr(rr, "category", "")
        cat_str = cat_obj.value if hasattr(cat_obj, "value") else str(cat_obj)

        sev_obj = getattr(rr, "severity", "MEDIUM")
        sev_str = sev_obj.value if hasattr(sev_obj, "value") else str(sev_obj)
        priority = _SEV_TO_URGENCY.get(sev_str.upper(), UrgencyLevel.MEDIUM)

        questions.append(QuestionItem(
            question=q_text,
            purpose=getattr(rr, "why_it_matters", "Clarifying this reduces legal risk."),
            ask_whom=_ask_whom(cat_str),
            priority=priority,
            source_risk_id=getattr(rr, "risk_id", None),
        ))

    # From AI analysis risks
    for ar in analysis_risks:
        q_text = ar.get("countermeasure", "")
        if not q_text or q_text in seen:
            continue
        seen.add(q_text)
        cat = ar.get("category", "")
        questions.append(QuestionItem(
            question=f"Regarding the {ar.get('title', 'identified clause')}: {q_text}",
            purpose=ar.get("description", "This addresses an identified concern in the document."),
            ask_whom=_ask_whom(cat),
            priority=UrgencyLevel.MEDIUM,
            source_risk_id=ar.get("risk_id"),
        ))

    # Sort by priority
    questions.sort(key=lambda q: _urgency_order(q.priority))
    return questions[:15]


# ─── Main Assembler ───────────────────────────────────────────────────────────

def build_next_steps(
    risk_records: List[Any],
    missing_protections: List[Any],
    analysis_risks: List[Dict[str, Any]],
    obligations: List[Dict[str, Any]],
    missing_clauses: List[Dict[str, Any]],
    escalation_triggers: List[EscalationTrigger],
) -> List[ActionStep]:
    """
    Assemble a dependency-ordered, urgency-sorted list of ActionSteps.
    Step 1 is always 'Collect signed copy'.
    Professional-review step always comes last.
    """
    steps: List[ActionStep] = []

    # Foundation step
    steps.append(_build_document_collection_step())

    # From risk records
    steps.extend(_build_risk_steps(risk_records + missing_protections))

    # From obligations
    steps.extend(_build_obligation_steps(obligations))

    # From missing clauses
    steps.extend(_build_missing_clause_steps(missing_clauses))

    # Sort by urgency (collect step stays first via dep ordering below)
    steps.sort(key=lambda s: _urgency_order(s.urgency))

    # Professional review steps always last
    steps.extend(_build_escalation_steps(escalation_triggers))

    # Renumber
    for i, step in enumerate(steps, 1):
        step.step_number = i

    # Limit to 15 steps to keep actionable
    return steps[:15]
