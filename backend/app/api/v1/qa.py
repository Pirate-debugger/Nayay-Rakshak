from typing import Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_user
from app.core.audit import log_audit_event
from app.core.authorization import authorize_object_access
from app.core.exceptions import ObjectNotFoundError
from app.core.roles import Action
from app.db.base import get_db
from app.db.models import Document, DocumentChunk, User
from app.schemas.qa import QARequest, QAResponse
from app.services.prompt_guard import check_for_injection
from app.services.qa_engine.engine import qa_engine

router = APIRouter(prefix="/qa", tags=["Grounded Q&A"])


@router.post("/", response_model=QAResponse)
async def question_answering_endpoint(
    req: QARequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Enterprise Legal Q&A Engine:
    - Determines requirement: DOCUMENT_EVIDENCE, LEGAL_AUTHORITY, BOTH, GENERAL_INFORMATION.
    - Identifies jurisdiction, document context, dates, domain, and missing facts.
    - Synthesizes 8-part structured answer with evidence quotes and provenance.
    - Suppresses outcome guarantees and enforces epistemic modesty.
    - Supports English and Hindi localization without reasoning from translated law.
    """
    # 1. Prompt Injection Defense
    check_for_injection(req.question, raise_exception=True)

    chunk_dicts = None
    target_doc_id = None

    # 2. If a document_id is provided, load and authorize access
    if req.document_id is not None:
        doc_res = await db.execute(select(Document).where(Document.id == req.document_id))
        doc = doc_res.scalar_one_or_none()
        if not doc:
            raise ObjectNotFoundError("Document")

        authorize_object_access(
            user=current_user,
            resource=doc,
            action=Action.READ
        )
        target_doc_id = doc.id

        chunks_res = await db.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index)
        )
        chunks = chunks_res.scalars().all()
        chunk_dicts = [
            {
                "id": c.id,
                "page_number": c.page_number,
                "content": c.content,
                "clean_content": c.clean_content or c.content,
                "section_heading": f"Page {c.page_number} Section"
            }
            for c in chunks
        ]

    # 3. Cache lookup with strict provenance & legal source version invalidation
    from app.services.ai_cache import ai_cache_service
    doc_hash = doc.content_hash if req.document_id is not None and 'doc' in locals() and doc else None
    cache_key = ai_cache_service.compute_cache_key(
        document_content_hash=doc_hash,
        question=f"{req.question}:{req.language}:{req.jurisdiction or ''}",
        model_name="qa-grounded-v1",
        prompt_version="v1.0",
        pii_redacted=True
    )
    cached_data = await ai_cache_service.get(cache_key, db=db)
    if cached_data:
        return QAResponse.model_validate(cached_data)

    # 4. Execute Legal Q&A Pipeline
    response: QAResponse = await qa_engine.answer_legal_question(
        req=req,
        document_chunks=chunk_dicts
    )

    # Persist to cache
    await ai_cache_service.set(
        cache_key=cache_key,
        response_data=response.model_dump(),
        document_content_hash=doc_hash,
        model_name="qa-grounded-v1",
        prompt_version="v1.0",
        db=db
    )

    log_audit_event(
        action="LEGAL_QA_EXECUTED",
        user_id=current_user.id,
        target_type="Document" if target_doc_id else "LegalSource",
        target_id=target_doc_id,
        ip_address=request.client.host if request.client else None,
        status="SUCCESS",
        details={
            "requirement_type": response.requirement_type.value,
            "is_found_in_document": response.is_found_in_document,
            "language": response.language
        }
    )

    return response
