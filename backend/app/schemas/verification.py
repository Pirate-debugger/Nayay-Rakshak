from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class VerificationStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"


class ClaimType(str, Enum):
    FACTUAL = "FACTUAL"
    LEGAL_STATUTORY = "LEGAL_STATUTORY"
    LEGAL_PRECEDENT = "LEGAL_PRECEDENT"
    CONTRACTUAL_TERM = "CONTRACTUAL_TERM"
    PROCEDURAL = "PROCEDURAL"


class ClaimVerificationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    check_1_evidence_found: bool = Field(
        ..., description="Check 1: Was candidate evidence retrieved?"
    )
    check_2_claim_evidence_comparison: str = Field(
        ..., description="Check 2: Detailed comparison of claim vs retrieved evidence text"
    )
    check_3_source_authority: str = Field(
        ..., description="Check 3: Authority tier/credibility of matching source"
    )
    check_4_jurisdiction_match: bool = Field(
        ..., description="Check 4: Does source jurisdiction match query jurisdiction?"
    )
    check_5_temporal_validity: bool = Field(
        ..., description="Check 5: Was source active at the relevant date?"
    )
    check_6_status_determined: VerificationStatus = Field(
        ..., description="Check 6: Final support status"
    )


class ClaimVerificationDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    claim_text: str
    claim_type: ClaimType
    verification_status: VerificationStatus
    checks: ClaimVerificationCheck
    matched_evidence_id: Optional[str] = None
    matched_evidence_snippet: Optional[str] = None
    matched_source_url: Optional[str] = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    hedged_text: Optional[str] = Field(
        None, description="Hedged or corrected phrasing if unsupported/conflicting"
    )
    explanation: str


class VerificationMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_coverage: float = Field(
        ..., ge=0.0, le=1.0, description="(Supported + 0.5*PartiallySupported) / TotalClaims"
    )
    unsupported_claim_rate: float = Field(
        ..., ge=0.0, le=1.0, description="(Unsupported + Conflicting) / TotalClaims"
    )
    citation_validity_rate: float = Field(
        ..., ge=0.0, le=1.0, description="ValidCitations / TotalCitedSources"
    )
    total_claims: int
    supported_count: int
    partially_supported_count: int
    unsupported_count: int
    conflicting_count: int
    unverified_count: int


class ClaimVerificationItem(BaseModel):
    claim_id: str
    claim_text: str
    evidence_source: str
    page_or_section: Optional[str] = None
    source_authority: str
    source_date_or_version: Optional[str] = None
    verification_status: VerificationStatus
    confidence_strength: float
    evidence_snippet: Optional[str] = None
    reasoning: str


class VerificationRequest(BaseModel):
    document_id: Optional[int] = None
    claims: List[str] = Field(..., min_length=1, max_length=20)


class VerificationBatchResponse(BaseModel):
    document_id: Optional[int] = None
    total_claims: int
    results: List[ClaimVerificationItem]
    summary_verdict: str


class ClaimVerificationPipelineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_question: str = Field(..., min_length=2, max_length=1000)
    document_chunks: Optional[List[Dict[str, Any]]] = None
    draft_answer: Optional[str] = Field(
        None,
        max_length=10000,
        description="Optional draft answer. If omitted, synthesized from retrieval.",
    )
    jurisdiction: Optional[str] = Field(None, max_length=100)
    as_of_date: Optional[datetime] = None


class ClaimVerificationPipelineResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_question: str
    draft_answer: str
    final_response: str
    safety_gate_action: str
    claims: List[ClaimVerificationDetail]
    metrics: VerificationMetrics
    citations_verified: List[str]
    citations_rejected: List[str]
    never_hallucination_free_compliance: bool = Field(
        True,
        description="Confirms that no false claims of zero hallucination or infallible legal accuracy exist.",
    )
