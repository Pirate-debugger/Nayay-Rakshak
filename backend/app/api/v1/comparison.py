import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.ai.base import BaseAIProvider
from app.api.deps import get_ai, get_current_user
from app.core.audit import log_audit_event
from app.core.authorization import authorize_object_access
from app.core.config import settings
from app.core.exceptions import ObjectNotFoundError, UnauthorizedAccessError
from app.core.rate_limit import limiter
from app.core.roles import Action
from app.db.base import get_db
from app.db.models import ComparisonResult, Document, DocumentChunk, User
from app.schemas.comparison import ClauseDiffItem, ComparisonResponse, RiskDeltaSummary

router = APIRouter(prefix="/comparison", tags=["Document Comparison"])

class CompareRequest(BaseModel):
    base_document_id: int
    target_document_id: int

@router.post("/", response_model=ComparisonResponse)
@limiter.limit(settings.RATE_LIMIT_COMPARISON)
async def compare_documents_endpoint(
    req: CompareRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    ai_provider: BaseAIProvider = Depends(get_ai),
    db: AsyncSession = Depends(get_db)
):
    """
    Semantically compare two legal documents (e.g. Standard Lease vs Counterparty Harsh Draft).
    Evaluates:
    - Added high-risk covenants
    - Deleted protections or rights
    - Altered liability caps or late penalties
    - Overall Risk Delta verdict
    """
    if req.base_document_id == req.target_document_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot compare a document to itself. Please provide two distinct document IDs."
        )

    # Fetch both documents with centralized object-level authorization checks
    base_res = await db.execute(select(Document).where(Document.id == req.base_document_id))
    base_doc = base_res.scalar_one_or_none()
    if not base_doc:
        raise ObjectNotFoundError(f"Base Document (ID {req.base_document_id})")

    authorize_object_access(
        user=current_user,
        resource=base_doc,
        action=Action.READ
    )

    target_res = await db.execute(select(Document).where(Document.id == req.target_document_id))
    target_doc = target_res.scalar_one_or_none()
    if not target_doc:
        raise ObjectNotFoundError(f"Target Document (ID {req.target_document_id})")

    authorize_object_access(
        user=current_user,
        resource=target_doc,
        action=Action.READ
    )



    # Fetch chunks
    b_chunks_res = await db.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == base_doc.id).order_by(DocumentChunk.chunk_index)
    )
    t_chunks_res = await db.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == target_doc.id).order_by(DocumentChunk.chunk_index)
    )

    b_chunk_list = b_chunks_res.scalars().all()
    t_chunk_list = t_chunks_res.scalars().all()

    b_text = "\n\n".join([c.clean_content for c in b_chunk_list]) or base_doc.raw_content
    t_text = "\n\n".join([c.clean_content for c in t_chunk_list]) or target_doc.raw_content

    # Run Semantic Comparison Engine
    from app.services.comparison.engine import SemanticComparisonEngine
    comp_engine = SemanticComparisonEngine()
    comparison_response = comp_engine.compare(
        base_document_id=base_doc.id,
        base_title=base_doc.title,
        base_text=b_text,
        target_document_id=target_doc.id,
        target_title=target_doc.title,
        target_text=t_text,
        base_chunks=b_chunk_list,
        target_chunks=t_chunk_list
    )

    diffs = comparison_response.clause_diffs
    summary = comparison_response.summary

    # Save comparison record
    comp_record = ComparisonResult(
        user_id=current_user.id,
        base_document_id=base_doc.id,
        target_document_id=target_doc.id,
        base_title=base_doc.title,
        target_title=target_doc.title,
        risk_delta_json=json.dumps(summary.model_dump()),
        added_clauses_json=json.dumps([d.model_dump() for d in diffs if d.change_type == "ADDED"]),
        removed_clauses_json=json.dumps([d.model_dump() for d in diffs if d.change_type == "REMOVED"]),
        modified_clauses_json=json.dumps([d.model_dump() for d in diffs if d.change_type == "MODIFIED"]),
        overall_verdict=comparison_response.overall_verdict,
    )
    db.add(comp_record)
    await db.commit()

    log_audit_event(
        action="DOCUMENTS_COMPARED",
        user_id=current_user.id,
        target_type="Comparison",
        ip_address=request.client.host if request.client else None,
        status="SUCCESS",
        details={
            "base_id": base_doc.id,
            "target_id": target_doc.id,
            "verdict": summary.net_risk_verdict,
            "findings_count": len(comparison_response.findings)
        }
    )

    return comparison_response
