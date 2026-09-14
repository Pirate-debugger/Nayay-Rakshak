"""
NYAYA RAKSHAK — Action Navigator Schemas
======================================
Strict Pydantic models for the conservative, non-binding Action Navigator.

Design contract:
  - Every ActionStep MUST have an evidence_source tracing it to a clause/risk.
  - professional_review_recommended is set deterministically — never by LLM.
  - disclaimer is non-nullable and always populated by the engine.
  - No field may ever state a guaranteed legal outcome.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─── Urgency ──────────────────────────────────────────────────────────────────

class UrgencyLevel(str, Enum):
    IMMEDIATE    = "IMMEDIATE"     # Act within 24-72 hours
    HIGH         = "HIGH"          # Act within this week
    MEDIUM       = "MEDIUM"        # Act within this month
    LOW          = "LOW"           # Act before signing / in due course
    INFORMATIONAL = "INFORMATIONAL"  # Awareness only, no action required now


# ─── Section: Known Facts ─────────────────────────────────────────────────────

class FactItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fact: str = Field(
        ..., min_length=10,
        description="An objectively verifiable fact extracted from the document"
    )
    source: str = Field(
        ..., description="Clause ID, obligation ID, or page reference supporting this fact"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Extraction confidence (1.0 = directly quoted; lower = inferred)"
    )
    category: str = Field(
        ..., description="Thematic category e.g. 'Party', 'Financial', 'Duration', 'Obligation'"
    )


# ─── Section: Important Documents ─────────────────────────────────────────────

class ImportantDocumentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_name: str = Field(..., description="Name or type of document to collect/verify")
    why_needed: str = Field(..., description="Plain-language reason this document matters")
    urgency: UrgencyLevel = Field(..., description="How urgently this document should be obtained")
    consequence_if_missing: str = Field(
        ..., description="What may happen if this document is not available"
    )
    source: Optional[str] = Field(
        None, description="Clause or risk that surfaced the need for this document"
    )


# ─── Section: Important Dates ─────────────────────────────────────────────────

class ImportantDateItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date_description: str = Field(
        ..., description="Description of the date/deadline (e.g. 'Notice period expiry')"
    )
    estimated_date: Optional[str] = Field(
        None,
        description="The extracted date string (ISO or human-readable). May be relative "
                    "(e.g. '30 days after signing') if absolute date is not determinable."
    )
    consequence: str = Field(
        ..., description="What may happen if this date is missed or ignored"
    )
    urgency: UrgencyLevel = Field(...)
    source: str = Field(..., description="Clause or obligation ID that contains this date")


# ─── Section: Potential Issues ────────────────────────────────────────────────

class IssueSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"


class PotentialIssueItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    issue: str = Field(..., min_length=5, description="Short name of the potential issue")
    explanation: str = Field(
        ..., min_length=15, description="Plain-language explanation for a lay reader"
    )
    potential_impact: str = Field(
        ..., description="What this issue could mean practically (without guaranteeing outcome)"
    )
    severity: IssueSeverity
    category: str = Field(..., description="Risk category e.g. FINANCIAL, TERMINATION, etc.")
    source_risk_id: Optional[str] = Field(
        None, description="Risk ID in the risk engine output that generated this issue"
    )


# ─── Section: Questions to Ask ────────────────────────────────────────────────

class QuestionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(
        ..., min_length=10,
        description="A specific question the user should consider asking"
    )
    purpose: str = Field(
        ..., description="Why this question is important to have answered"
    )
    ask_whom: str = Field(
        ...,
        description="Who to direct this question to: e.g. 'Counterparty', "
                    "'Your Advocate', 'Landlord', 'Employer HR'"
    )
    priority: UrgencyLevel = Field(...)
    source_risk_id: Optional[str] = Field(None)


# ─── Section: Possible Next Steps ────────────────────────────────────────────

class ActionStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_number: int = Field(..., ge=0, description="Execution order (1 = first; 0 = placeholder during assembly)")
    action: str = Field(
        ..., min_length=10,
        description="The specific, concrete action to take. "
                    "MUST NOT guarantee a legal outcome."
    )
    reason: str = Field(
        ..., description="Why this action is suggested, referencing the underlying concern"
    )
    evidence_source: str = Field(
        ..., min_length=3,
        description="Clause ID, risk ID, obligation ID, or section that triggered this step"
    )
    urgency: UrgencyLevel = Field(...)
    dependency: Optional[str] = Field(
        None,
        description="Step or action that should be completed before this one (if any)"
    )
    is_professional_review_step: bool = Field(
        default=False,
        description="True if this step is specifically about seeking professional legal help"
    )


# ─── Section: Escalation / Professional Help ─────────────────────────────────

class EscalationTriggerType(str, Enum):
    HIGH_FINANCIAL_EXPOSURE    = "HIGH_FINANCIAL_EXPOSURE"
    SIGNIFICANT_DEADLINE       = "SIGNIFICANT_DEADLINE"
    COURT_MATTER               = "COURT_MATTER"
    CRIMINAL_MATTER            = "CRIMINAL_MATTER"
    SERIOUS_RIGHTS_IMPACT      = "SERIOUS_RIGHTS_IMPACT"
    CONFLICTING_AUTHORITIES    = "CONFLICTING_AUTHORITIES"
    INSUFFICIENT_EVIDENCE      = "INSUFFICIENT_EVIDENCE"
    CRITICAL_RISK_DETECTED     = "CRITICAL_RISK_DETECTED"
    UNCAPPED_INDEMNITY         = "UNCAPPED_INDEMNITY"
    MISSING_DISPUTE_RESOLUTION = "MISSING_DISPUTE_RESOLUTION"
    MULTIPLE_HIGH_RISKS        = "MULTIPLE_HIGH_RISKS"
    JURISDICTION_CONFLICT      = "JURISDICTION_CONFLICT"


class EscalationTrigger(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trigger_type: EscalationTriggerType
    reason: str = Field(
        ..., description="Plain-language explanation of why this trigger fired"
    )
    severity: IssueSeverity = Field(...)
    recommended_resource: str = Field(
        ...,
        description="Who or what the user should contact "
                    "(e.g. 'Qualified Advocate (NALSA free aid available at 15100)', "
                    "'District Consumer Commission')"
    )
    source_risk_id: Optional[str] = Field(None)


# ─── Top-Level Response ───────────────────────────────────────────────────────

NAVIGATOR_DISCLAIMER = (
    "This Action Navigator is an educational assistance tool only. "
    "It does NOT constitute legal advice, does NOT create an attorney-client relationship, "
    "and CANNOT guarantee any legal outcome. "
    "The steps and questions listed are non-binding suggestions to help you organise "
    "your understanding of this document. "
    "For any legal matter of significance, always consult a qualified advocate. "
    "Free legal aid is available via NALSA at 15100 (India)."
)


class ActionNavigatorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Identity
    document_id: int
    document_title: str
    engine_version: str = Field("2024.1.0")

    # The 8 structured sections
    known_facts: List[FactItem] = Field(
        default_factory=list,
        description="Objectively verifiable facts confirmed in the uploaded document"
    )
    unknown_facts: List[FactItem] = Field(
        default_factory=list,
        description="Material facts the document does NOT clearly establish or that are ambiguous"
    )
    important_documents: List[ImportantDocumentItem] = Field(
        default_factory=list,
        description="Documents the user should collect, verify, or keep safe"
    )
    important_dates: List[ImportantDateItem] = Field(
        default_factory=list,
        description="Deadlines, renewal dates, notice periods, and time-sensitive clauses"
    )
    potential_issues: List[PotentialIssueItem] = Field(
        default_factory=list,
        description="Identified concerns that may warrant attention or negotiation"
    )
    questions_to_ask: List[QuestionItem] = Field(
        default_factory=list,
        description="Specific questions to raise with the counterparty or a professional"
    )
    possible_next_steps: List[ActionStep] = Field(
        default_factory=list,
        description="Ordered, non-binding practical steps to take. Never a guaranteed outcome."
    )
    when_to_seek_professional_help: List[EscalationTrigger] = Field(
        default_factory=list,
        description="Specific conditions that make professional legal consultation advisable"
    )

    # Professional review decision (deterministic — never AI-decided)
    professional_review_recommended: bool = Field(
        ...,
        description="True if any escalation trigger fires. Set deterministically."
    )
    professional_review_urgency: UrgencyLevel = Field(
        UrgencyLevel.LOW,
        description="Urgency of professional review if recommended"
    )

    # Mandatory disclaimer — never None
    disclaimer: str = Field(
        default=NAVIGATOR_DISCLAIMER,
        description="Mandatory non-binding disclaimer. Always populated. Never displayed as legal advice."
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
