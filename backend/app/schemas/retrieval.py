"""
NYAYA RAKSHAK - Evidence-First Legal Retrieval Schemas
Strict Pydantic models for legal search, source hierarchy, query classification,
verifiable citations, and IR evaluation metrics.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SourceTier(str, Enum):
    TIER_1_OFFICIAL_LEGISLATION_COURTS = "TIER_1_OFFICIAL_LEGISLATION_COURTS"
    TIER_2_OFFICIAL_INSTITUTIONS = "TIER_2_OFFICIAL_INSTITUTIONS"
    TIER_3_REPUTABLE_SECONDARY = "TIER_3_REPUTABLE_SECONDARY"
    TIER_4_GENERAL_WEB = "TIER_4_GENERAL_WEB"


class EvidenceType(str, Enum):
    USER_DOCUMENT_EVIDENCE = "USER_DOCUMENT_EVIDENCE"
    LEGAL_AUTHORITY = "LEGAL_AUTHORITY"
    SECONDARY_INFORMATION = "SECONDARY_INFORMATION"


class QueryIntent(str, Enum):
    DOCUMENT_ONLY = "document-only"
    LEGAL_SOURCE = "legal-source"
    HYBRID = "hybrid"
    GENERAL_INFORMATION = "general-information"


class AuthorityLevel(str, Enum):
    PARLIAMENT_ACT = "PARLIAMENT_ACT"
    STATE_ACT = "STATE_ACT"
    SUPREME_COURT_RULING = "SUPREME_COURT_RULING"
    HIGH_COURT_RULING = "HIGH_COURT_RULING"
    REGULATORY_RULE = "REGULATORY_RULE"
    TRIBUNAL_ORDER = "TRIBUNAL_ORDER"


class SourceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    AMENDED = "AMENDED"
    REPEALED = "REPEALED"
    SUPERSEDED = "SUPERSEDED"
    PENDING_ENACTMENT = "PENDING_ENACTMENT"


class RetrievalFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jurisdiction: Optional[str] = Field(None, description="Target jurisdiction (e.g. 'Union of India', 'NCT of Delhi', 'Maharashtra')")
    allow_cross_jurisdiction: bool = Field(False, description="Whether to allow mixing different state jurisdictions. Default FALSE.")
    court: Optional[str] = Field(None, description="Specific court filter (e.g. 'Supreme Court of India', 'Delhi High Court')")
    legal_domain: Optional[str] = Field(None, description="Domain filter (e.g. 'criminal', 'tenancy', 'contract', 'consumer', 'privacy')")
    as_of_date: Optional[datetime] = Field(None, description="Temporal reference date for filtering active legal validity")
    min_authority_tier: Optional[SourceTier] = Field(None, description="Minimum acceptable authority tier")
    allowed_statuses: Optional[List[SourceStatus]] = Field(
        default=[SourceStatus.ACTIVE, SourceStatus.AMENDED],
        description="Legal source statuses to include"
    )


class CitationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str = Field(..., description="Canonical source ID (e.g. BNS-2023-SEC-318, ICA-1872-SEC-27)")
    title: str = Field(..., min_length=3, description="Official title of the statute or document")
    authority: str = Field(..., description="Originating authority, e.g. Parliament of India / Supreme Court of India")
    authority_tier: SourceTier = Field(..., description="Source hierarchy tier: 1 to 4")
    evidence_type: EvidenceType = Field(..., description="USER_DOCUMENT_EVIDENCE vs LEGAL_AUTHORITY vs SECONDARY_INFORMATION")
    section_or_page: str = Field(..., description="Specific statutory section or user document page reference")
    publication_date: Optional[str] = Field(None, description="Official Gazette publication date")
    effective_date: Optional[str] = Field(None, description="Date from which the provision is enforceable")
    retrieval_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO 8601 UTC timestamp")
    url_or_reference: str = Field(..., description="Authentic official Gazette or India Code URL/citation. NEVER invented.")
    supporting_text: str = Field(..., min_length=5, description="Exact verbatim statutory text or document quote")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score from retriever/reranker")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Metadata trace (hash, paragraph offset, database ID)")


class RetrievalResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: str
    evidence_type: EvidenceType
    tier: SourceTier
    title: str
    content: str
    citation: CitationRecord
    keyword_score: float = Field(0.0, ge=0.0)
    semantic_score: float = Field(0.0, ge=0.0)
    tier_boost: float = Field(1.0, ge=0.0)
    final_score: float = Field(..., ge=0.0)
    jurisdiction: str
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    status: SourceStatus = SourceStatus.ACTIVE


class RetrievalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str
    classified_intent: QueryIntent
    applied_filters: RetrievalFilter
    total_found: int
    has_authoritative_evidence: bool
    explicit_unretrieved_disclaimer: Optional[str] = Field(
        None,
        description="Explicit notice when authoritative evidence cannot be retrieved"
    )
    user_document_items: List[RetrievalResultItem] = Field(default_factory=list)
    legal_authority_items: List[RetrievalResultItem] = Field(default_factory=list)
    secondary_items: List[RetrievalResultItem] = Field(default_factory=list)
    reranked_items: List[RetrievalResultItem] = Field(default_factory=list)
    evaluation_metrics: Optional[Dict[str, float]] = Field(
        None,
        description="Retrieval quality metrics if evaluated (Precision@k, Recall@k, MRR, NDCG)"
    )


class RetrievalEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    test_queries: List[Dict[str, Any]] = Field(..., min_length=1, description="List of benchmark query specs")
    k_values: List[int] = Field(default=[1, 3, 5], description="Cutoff thresholds for Precision and NDCG")
