"""
NYAYA RAKSHAK - Risk Engine Schemas
Strict Pydantic models for deterministic and AI-assisted risk analysis.
Enforces separation of:
1. Finding (objective observation)
2. Evidence (verbatim quote, page, section, offsets)
3. Risk Classification (category, severity)
4. Explanation (plain language, why it matters, negotiation advice)
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RiskCategory(str, Enum):
    FINANCIAL = "FINANCIAL"
    TIME_DEADLINE = "TIME/DEADLINE"
    LIABILITY = "LIABILITY"
    INDEMNITY = "INDEMNITY"
    TERMINATION = "TERMINATION"
    PRIVACY = "PRIVACY"
    IP = "IP"
    ARBITRATION = "ARBITRATION"
    JURISDICTION = "JURISDICTION"
    RENEWAL = "RENEWAL"
    OBLIGATION_ASYMMETRY = "OBLIGATION ASYMMETRY"
    AMBIGUITY = "AMBIGUITY"
    MISSING_PROTECTION = "MISSING PROTECTION"


class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingType(str, Enum):
    DETERMINISTIC_RULE = "DETERMINISTIC_RULE"
    AI_ASSISTED_PATTERN = "AI_ASSISTED_PATTERN"
    CROSS_CLAUSE_CONFLICT = "CROSS_CLAUSE_CONFLICT"
    MISSING_STATUTORY_PROTECTION = "MISSING_STATUTORY_PROTECTION"


class EvidenceLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page_number: int = Field(
        ..., ge=1, description="1-indexed page number where the evidence is located"
    )
    section_heading: Optional[str] = Field(
        None, description="Section heading or title if available"
    )
    verbatim_quote: str = Field(
        ..., min_length=5, description="Exact verbatim text from the document establishing the risk"
    )
    char_start: Optional[int] = Field(
        None, ge=0, description="Character offset start in document/clause text"
    )
    char_end: Optional[int] = Field(
        None, ge=0, description="Character offset end in document/clause text"
    )


class RiskRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    risk_id: str = Field(..., description="Unique identifier for the risk, e.g., RISK-01")
    category: RiskCategory = Field(..., description="One of the 13 standard risk categories")
    severity: RiskSeverity = Field(..., description="Severity tier: LOW, MEDIUM, HIGH, CRITICAL")
    title: str = Field(
        ..., min_length=5, max_length=255, description="Concise title describing the risk finding"
    )
    finding: str = Field(
        ..., min_length=10, description="Objective factual finding observed in the clause"
    )
    plain_language_explanation: str = Field(
        ..., min_length=15, description="Plain English/Hindi citizen explanation"
    )
    why_it_matters: str = Field(
        ..., min_length=15, description="Practical implication or commercial risk to the citizen"
    )
    evidence: EvidenceLocation = Field(
        ..., description="Verifiable textual evidence supporting the finding"
    )
    affected_party: str = Field(
        ...,
        description="Party bearing the disproportionate risk (e.g., Tenant, Employee, Consumer)",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score of the risk detection"
    )
    recommended_question: str = Field(
        ..., min_length=10, description="Negotiation question to ask the counterparty or advocate"
    )
    professional_review_recommended: bool = Field(
        ..., description="Whether professional advocate consultation is advised"
    )

    # Auditability & Versioning metadata
    rule_id: Optional[str] = Field(
        None, description="Identifier of the versioned deterministic rule if triggered"
    )
    rule_version: Optional[str] = Field(
        None, description="Version string of the rule (e.g., 2024.1.0)"
    )
    finding_type: FindingType = Field(
        default=FindingType.DETERMINISTIC_RULE, description="Detection origin"
    )
    statutory_cross_reference: Optional[str] = Field(
        None, description="Relevant statutory provision if applicable (e.g., ICA 1872 § 27)"
    )
    is_camouflaged: bool = Field(
        default=False,
        description="Flag indicating if the clause was buried in unrelated boilerplate",
    )


class RiskSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_risks: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    overall_health_verdict: (
        str  # e.g., "HIGH_RISK_TERMS_DETECTED", "BALANCED", "CRITICAL_ATTENTION_REQUIRED"
    )


class RuleChangelogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    effective_date: str
    description: str
    author: str = "Nyaya Rakshak Legal Rule Committee"


class RuleVersionInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rule_id: str
    version: str
    category: RiskCategory
    default_severity: RiskSeverity
    title: str
    description: str
    statutory_reference: Optional[str] = None
    changelog: List[RuleChangelogEntry] = Field(default_factory=list)


class RiskEngineResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: Optional[int] = Field(None, description="Document identifier if persisted")
    engine_version: str = Field("2024.1.0", description="Semantic Risk Engine version")
    ruleset_version: str = Field(
        "2024.1.0", description="Version of the deterministic rule registry used"
    )
    summary: RiskSummary = Field(..., description="Aggregate counts across severities")
    risks: List[RiskRecord] = Field(
        default_factory=list, description="All detected risks with evidence"
    )
    missing_protections: List[RiskRecord] = Field(
        default_factory=list, description="Missing safety covenants"
    )
    audit_trail: List[Dict[str, Any]] = Field(
        default_factory=list, description="Detailed audit of evaluated rules"
    )
