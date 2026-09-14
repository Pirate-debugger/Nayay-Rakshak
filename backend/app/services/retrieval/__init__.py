"""
NYAYA RAKSHAK - Retrieval Service Package
Exports LegalRetriever, SourceRegistry, LegalSourceProvider, TierWeightedReranker,
QueryClassifier, and RetrievalEvaluator.
"""

from app.schemas.retrieval import (
    AuthorityLevel,
    CitationRecord,
    EvidenceType,
    QueryIntent,
    RetrievalEvaluationRequest,
    RetrievalFilter,
    RetrievalResponse,
    RetrievalResultItem,
    SourceStatus,
    SourceTier,
)
from app.services.retrieval.classifier import QueryClassifier, query_classifier
from app.services.retrieval.evaluator import RetrievalEvaluator, retrieval_evaluator
from app.services.retrieval.provider import LegalSourceProvider, legal_source_provider
from app.services.retrieval.registry import AuthoritativeLegalItem, SourceRegistry, source_registry
from app.services.retrieval.reranker import TierWeightedReranker, tier_weighted_reranker
from app.services.retrieval.retriever import LegalRetriever, legal_retriever

__all__ = [
    "SourceTier",
    "EvidenceType",
    "QueryIntent",
    "AuthorityLevel",
    "SourceStatus",
    "RetrievalFilter",
    "CitationRecord",
    "RetrievalResultItem",
    "RetrievalResponse",
    "RetrievalEvaluationRequest",
    "SourceRegistry",
    "source_registry",
    "AuthoritativeLegalItem",
    "LegalSourceProvider",
    "legal_source_provider",
    "TierWeightedReranker",
    "tier_weighted_reranker",
    "QueryClassifier",
    "query_classifier",
    "LegalRetriever",
    "legal_retriever",
    "RetrievalEvaluator",
    "retrieval_evaluator",
]
