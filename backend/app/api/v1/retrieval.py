"""
NYAYA RAKSHAK - Legal Retrieval API Endpoints
Provides endpoints for evidence-first legal retrieval, authoritative source lookup,
and IR benchmark evaluation.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.schemas.retrieval import (
    RetrievalEvaluationRequest,
    RetrievalFilter,
    RetrievalResponse,
)
from app.services.retrieval.evaluator import STANDARD_LEGAL_BENCHMARKS, retrieval_evaluator
from app.services.retrieval.registry import source_registry
from app.services.retrieval.retriever import legal_retriever

router = APIRouter(prefix="/retrieval", tags=["Legal Retrieval"])


class RetrievalSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500, description="Legal question or query")
    document_chunks: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Optional list of chunks from user document: [{'content': '...', 'page_number': 1}]",
    )
    custom_filters: Optional[RetrievalFilter] = Field(
        None, description="Optional explicit retrieval filters (jurisdiction, date, domain)"
    )
    top_k: int = Field(5, ge=1, le=20, description="Max candidate items to return")


@router.post("/search", response_model=RetrievalResponse)
async def search_legal_evidence(req: RetrievalSearchRequest):
    """
    Executes multi-stream evidence-first legal retrieval.
    Segregates User Document Evidence from Legal Authority and Secondary Info.
    Applies strict temporal filtering, jurisdiction isolation, and tier-weighted reranking.
    """
    try:
        response = await legal_retriever.retrieve(
            query=req.query,
            document_chunks=req.document_chunks,
            custom_filters=req.custom_filters,
            top_k=req.top_k,
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Retrieval error: {str(e)}"
        )


@router.post("/evaluate", response_model=Dict[str, float])
async def evaluate_retrieval_quality(req: Optional[RetrievalEvaluationRequest] = None):
    """
    Runs IR evaluation on benchmark queries and returns real computed metrics:
    MRR, Precision@K, Recall@K, NDCG@K. No fabricated or static scores.
    """
    try:
        benchmarks = req.test_queries if req and req.test_queries else STANDARD_LEGAL_BENCHMARKS
        k_values = req.k_values if req and req.k_values else [1, 3, 5]
        metrics = await retrieval_evaluator.evaluate_benchmarks(
            benchmarks=benchmarks, k_values=k_values
        )
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation execution failed: {str(e)}",
        )


@router.get("/sources")
async def list_registered_authorities(
    domain: Optional[str] = Query(None, description="Filter by legal domain"),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
):
    """
    Lists verified canonical legal authorities in the SourceRegistry.
    Every source includes official Gazette or Court URLs and provenance hashes.
    """
    sources = source_registry.list_all()
    if domain:
        sources = [s for s in sources if s.legal_domain == domain]
    if jurisdiction:
        sources = [s for s in sources if s.jurisdiction == jurisdiction]

    return [
        {
            "source_id": s.source_id,
            "title": s.title,
            "short_name": s.short_name,
            "section_number": s.section_number,
            "section_title": s.section_title,
            "jurisdiction": s.jurisdiction,
            "authority_level": s.authority_level.value,
            "tier": s.tier.value,
            "effective_from": s.effective_from,
            "effective_to": s.effective_to,
            "status": s.status.value,
            "official_url": s.official_url,
            "key_principles": s.key_principles,
        }
        for s in sources
    ]


@router.get("/sources/{source_id}")
async def get_authority_by_id(source_id: str):
    """Retrieves full statutory details for a specific canonical source ID."""
    item = source_registry.get(source_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Legal source '{source_id}' not found in registry.",
        )
    return {
        "source_id": item.source_id,
        "title": item.title,
        "short_name": item.short_name,
        "section_number": item.section_number,
        "section_title": item.section_title,
        "content": item.content,
        "key_principles": item.key_principles,
        "jurisdiction": item.jurisdiction,
        "authority_level": item.authority_level.value,
        "tier": item.tier.value,
        "publication_date": item.publication_date,
        "effective_from": item.effective_from,
        "effective_to": item.effective_to,
        "status": item.status.value,
        "official_url": item.official_url,
        "historical_reference": item.historical_reference,
        "legal_domain": item.legal_domain,
    }
