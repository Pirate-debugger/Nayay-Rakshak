from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class QuestionRequirementType(str, Enum):
    DOCUMENT_EVIDENCE = "DOCUMENT_EVIDENCE"
    LEGAL_AUTHORITY = "LEGAL_AUTHORITY"
    BOTH = "BOTH"
    GENERAL_INFORMATION = "GENERAL_INFORMATION"


class QAContextMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jurisdiction: str = Field(
        "Union of India",
        description="Determined jurisdiction (e.g. Union of India, NCT of Delhi, Maharashtra)",
    )
    document_context: Optional[str] = Field(
        None, description="Document type, identified parties, or subject matter"
    )
    relevant_dates: List[str] = Field(
        default_factory=list, description="Extracted dates, notice intervals, or temporal markers"
    )
    legal_domain: Optional[str] = Field(
        None,
        description="Identified domain (e.g. tenancy, employment, consumer, criminal, contract)",
    )
    missing_facts: List[str] = Field(
        default_factory=list,
        description="Critical unstated facts needed for definitive legal advice",
    )


class QAEvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_title: str
    citation_ref: str
    page_number: Optional[int] = None
    section_or_clause: Optional[str] = None
    verbatim_quote: str
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    provenance_url: Optional[str] = None


class StructuredAnswerSections(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plain_language_answer: str = Field(..., description="Direct, accessible citizen-level summary")
    what_the_document_says: str = Field(..., description="Documentary terms or notice of omission")
    applicable_legal_information: str = Field(
        ..., description="Governing statutory sections or court precedents"
    )
    evidence: List[QAEvidenceItem] = Field(
        default_factory=list, description="Verbatim citations and document excerpts"
    )
    important_uncertainty: str = Field(
        ..., description="Missing facts, statutory ambiguities, or exceptions"
    )
    potential_next_steps: List[str] = Field(
        default_factory=list, description="Actionable recommendations for the citizen"
    )
    questions_for_professional: List[str] = Field(
        default_factory=list, description="Targeted inquiries to ask an advocate"
    )
    legal_disclaimer: str = Field(..., description="Mandatory non-attorney assistance disclaimer")


class CitationItem(BaseModel):
    page_number: int
    section_title: str
    verbatim_quote: str
    relevance_score: float


class QARequest(BaseModel):
    document_id: Optional[int] = Field(
        None,
        description="Optional uploaded document ID. Omit for pure statutory/general inquiries.",
    )
    question: str = Field(..., min_length=3, max_length=1000, description="Citizen legal inquiry")
    language: str = Field(
        "en", description="Preferred response language: 'en' (English) or 'hi' (Hindi)"
    )
    jurisdiction: Optional[str] = Field(
        None, max_length=100, description="Optional state or regional jurisdiction filter"
    )


class QAResponse(BaseModel):
    question: str
    answer: str
    confidence_score: float
    citations: List[CitationItem] = Field(default_factory=list)
    is_found_in_document: bool
    requirement_type: QuestionRequirementType = QuestionRequirementType.GENERAL_INFORMATION
    identified_context: QAContextMetadata = Field(default_factory=QAContextMetadata)
    structured_sections: Optional[StructuredAnswerSections] = None
    language: str = "en"
    localized_sections: Optional[Dict[str, Any]] = None
