from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ComparisonCategory(str, Enum):
    IDENTICAL = "IDENTICAL"
    SIMILAR = "SIMILAR"
    MODIFIED = "MODIFIED"
    NEW = "NEW"
    REMOVED = "REMOVED"
    CONFLICTING = "CONFLICTING"
    MISSING = "MISSING"


class DifferenceDimension(str, Enum):
    STRUCTURAL = "STRUCTURAL"
    OBLIGATION = "OBLIGATION"
    RIGHTS = "RIGHTS"
    FINANCIAL = "FINANCIAL"
    DEADLINE = "DEADLINE"
    LIABILITY = "LIABILITY"
    TERMINATION = "TERMINATION"
    JURISDICTION = "JURISDICTION"
    GENERAL_TERMS = "GENERAL_TERMS"


class MaterialityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    MATERIAL = "MATERIAL"
    MEDIUM = "MEDIUM"
    MINOR = "MINOR"
    NEGLIGIBLE = "NEGLIGIBLE"


class DocumentEvidence(BaseModel):
    document_id: int
    document_title: str
    clause_id: Optional[str] = None
    section_heading: str
    page_number: int = 1
    verbatim_quote: str
    char_start: Optional[int] = None
    char_end: Optional[int] = None


class ComparisonFindingItem(BaseModel):
    finding_id: str
    category: ComparisonCategory
    dimension: DifferenceDimension
    title: str
    document_a_evidence: Optional[DocumentEvidence] = None
    document_b_evidence: Optional[DocumentEvidence] = None
    difference_explanation: str
    materiality: MaterialityLevel
    risk_implications: str
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    semantic_similarity: float = Field(default=1.0, ge=0.0, le=1.0)


class StructuralDiff(BaseModel):
    doc_a_clause_count: int
    doc_b_clause_count: int
    aligned_clause_count: int
    reordered_clause_count: int
    missing_in_b_count: int
    new_in_b_count: int
    structural_alignment_score: float = Field(default=1.0, ge=0.0, le=1.0)


class ClauseDiffItem(BaseModel):
    category: str
    change_type: str  # "ADDED", "REMOVED", "MODIFIED", "UNCHANGED"
    base_text: Optional[str] = None
    target_text: Optional[str] = None
    risk_delta: str  # "INCREASED_RISK", "DECREASED_RISK", "NEUTRAL"
    impact_analysis: str


class RiskDeltaSummary(BaseModel):
    base_high_risks: int
    target_high_risks: int
    net_risk_verdict: str  # e.g. "TARGET_MORE_HARSH", "BALANCED", "TARGET_MORE_FAVORABLE"
    critical_warnings: List[str] = Field(default_factory=list)


class ComparisonResponse(BaseModel):
    base_document_id: int
    target_document_id: int
    base_title: str
    target_title: str
    overall_verdict: str
    summary: RiskDeltaSummary
    clause_diffs: List[ClauseDiffItem] = Field(default_factory=list)
    structural_diff: Optional[StructuralDiff] = None
    findings: List[ComparisonFindingItem] = Field(default_factory=list)
    dimensions_analyzed: List[str] = Field(default_factory=list)
