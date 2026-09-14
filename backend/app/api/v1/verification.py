from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.ai.base import BaseAIProvider
from app.api.deps import get_ai, get_current_user_optional
from app.core.audit import log_audit_event
from app.core.authorization import authorize_object_access
from app.core.exceptions import ObjectNotFoundError
from app.core.roles import Action
from app.db.base import get_db
from app.db.models import Document, DocumentChunk, User
from app.schemas.verification import (
    ClaimVerificationItem,
    ClaimVerificationPipelineRequest,
    ClaimVerificationPipelineResponse,
    VerificationBatchResponse,
    VerificationRequest,
    VerificationStatus,
)
from app.services.claim_verification.engine import claim_verification_engine
from app.services.prompt_guard import check_for_injection, sanitize_user_input

router = APIRouter(prefix="/verification", tags=["Evidence Grounding & Claim Verification"])

@router.post("/", response_model=VerificationBatchResponse)
async def verify_claims_endpoint(
    req: VerificationRequest,
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    ai_provider: BaseAIProvider = Depends(get_ai),
    db: AsyncSession = Depends(get_db)
):
    """
    Evidence Grounding & Claim Verification Engine:
    Validates factual & legal claims against document evidence or Indian statutory registry.
    Assigns strict verification states:
    - SUPPORTED: Verifiable proof in evidence.
    - PARTIALLY_SUPPORTED: Qualified match with caveats.
    - UNSUPPORTED: Claim not found in available sources.
    - CONFLICTING: Evidence directly contradicts the claim.
    - UNVERIFIED: Insufficient data to determine veracity.
    """
    chunk_dicts = []
    if req.document_id:
        doc_res = await db.execute(select(Document).where(Document.id == req.document_id))
        doc = doc_res.scalar_one_or_none()
        if not doc:
            raise ObjectNotFoundError("Document")

        # Strict BOLA / IDOR defense: enforce object-level authorization
        if not current_user:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to verify claims against private documents."
            )
        authorize_object_access(current_user, doc, Action.READ)

        chunks_res = await db.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index)
        )
        chunks = chunks_res.scalars().all()
        chunk_dicts = [
            {"id": c.id, "page_number": c.page_number, "content": c.content, "clean_content": c.clean_content}
            for c in chunks
        ]

    verified_items: List[ClaimVerificationItem] = []

    for i, raw_claim in enumerate(req.claims):
        # Prompt injection sanitization
        check_for_injection(raw_claim, raise_exception=True)
        claim = sanitize_user_input(raw_claim)

        result = await ai_provider.verify_claim(claim, chunk_dicts)
        verified_items.append(
            ClaimVerificationItem(
                claim_id=f"CLM-{i+1:02d}",
                claim_text=claim,
                evidence_source=result.get("evidence_source", "General Sources"),
                page_or_section=result.get("page_or_section"),
                source_authority=result.get("source_authority", "Statute / Contract"),
                source_date_or_version=result.get("source_date_or_version", "Current"),
                verification_status=VerificationStatus(result.get("verification_status", "UNVERIFIED")),
                confidence_strength=float(result.get("confidence_strength", 0.0)),
                evidence_snippet=result.get("evidence_snippet"),
                reasoning=result.get("reasoning", "")
            )
        )

    supported_count = sum(1 for item in verified_items if item.verification_status == VerificationStatus.SUPPORTED)
    conflicting_count = sum(1 for item in verified_items if item.verification_status == VerificationStatus.CONFLICTING)

    if conflicting_count > 0:
        summary_verdict = f"Caution: {conflicting_count} claim(s) conflict with official evidence or statutory protections."
    elif supported_count == len(verified_items):
        summary_verdict = "All evaluated claims are fully supported by verified documentary or statutory evidence."
    else:
        summary_verdict = f"{supported_count} of {len(verified_items)} claim(s) supported. Unverified claims require additional evidence."

    log_audit_event(
        action="CLAIMS_VERIFIED",
        user_id=current_user.id if current_user else None,
        target_type="Verification",
        ip_address=request.client.host if request.client else None,
        status="SUCCESS",
        details={"total_claims": len(req.claims), "supported": supported_count}
    )

    return VerificationBatchResponse(
        document_id=req.document_id,
        total_claims=len(verified_items),
        results=verified_items,
        summary_verdict=summary_verdict
    )


@router.post("/pipeline", response_model=ClaimVerificationPipelineResponse)
async def verify_claims_pipeline_endpoint(
    req: ClaimVerificationPipelineRequest,
    request: Request,
    current_user: User = Depends(get_current_user_optional)
):
    """
    8-Stage Claim Verification Pipeline:
    USER QUESTION -> RETRIEVAL -> DRAFT ANSWER -> CLAIM EXTRACTION -> EVIDENCE MATCHING
    -> VERIFICATION (6 Checks) -> SAFETY GATE -> FINAL RESPONSE.
    Computes verifiable Evidence Coverage, Unsupported Claim Rate, Citation Validity Rate.
    Suppresses false hallucination-free guarantees.
    """
    check_for_injection(req.user_question, raise_exception=True)
    if req.draft_answer:
        check_for_injection(req.draft_answer, raise_exception=True)

    result = await claim_verification_engine.execute_pipeline(req)

    log_audit_event(
        action="CLAIM_PIPELINE_EXECUTED",
        user_id=current_user.id if current_user else None,
        target_type="ClaimVerificationPipeline",
        ip_address=request.client.host if request.client else None,
        status="SUCCESS",
        details={
            "total_claims": result.metrics.total_claims,
            "evidence_coverage": result.metrics.evidence_coverage,
            "unsupported_claim_rate": result.metrics.unsupported_claim_rate,
            "safety_action": result.safety_gate_action
        }
    )

    return result

