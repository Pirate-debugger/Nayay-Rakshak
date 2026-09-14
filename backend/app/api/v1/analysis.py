import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.ai.base import BaseAIProvider
from app.api.deps import get_ai, get_current_user
from app.core.audit import log_audit_event
from app.core.authorization import authorize_object_access
from app.core.exceptions import ObjectNotFoundError, UnauthorizedAccessError
from app.core.roles import Action
from app.db.base import get_db
from app.db.models import AnalysisResult, Document, DocumentChunk, User
from app.schemas.analysis import (
    AnalysisResponse,
    ClauseItem,
    MissingClauseItem,
    ObligationItem,
    RiskItem,
)
from app.schemas.action_navigator import ActionNavigatorResponse
from app.schemas.clause_intelligence import StructuredClauseRecord
from app.schemas.risk import RiskEngineResult, RuleVersionInfo
from app.services.action_navigator import ActionNavigatorEngine
from app.services.checklist_service import get_action_checklist
from app.services.clause_intelligence import (
    analyze_clause_structured_async,
    process_document_clauses_async,
)
from app.services.risk_engine import risk_engine, risk_rule_registry

_action_navigator_engine = ActionNavigatorEngine()

router = APIRouter(prefix="/analysis", tags=["Legal Analysis & Clause Intelligence"])



class SingleClauseExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clause_text: str = Field(..., min_length=10, max_length=15000, description="Raw text of the clause to analyze")
    clause_id: Optional[str] = Field("C-01", max_length=50, description="Optional identifier for the clause")
    page_number: Optional[int] = Field(1, ge=1, description="Page number of the clause")
    section_name: Optional[str] = Field("General Covenants", max_length=150, description="Section or title of the clause")
    document_category: Optional[str] = Field(None, max_length=50, description="Optional category hint (e.g. rental, employment, nda)")



@router.post("/clause/extract", response_model=StructuredClauseRecord)
async def extract_single_clause_intelligence(
    payload: SingleClauseExtractRequest,
    current_user: User = Depends(get_current_user)
):
    """
    On-demand Clause Intelligence extraction on an arbitrary clause.
    Detects obligations, rights, prohibitions, penalties, deadlines, governing law,
    and returns strict structured JSON with deterministic guarantees.
    """
    record = await analyze_clause_structured_async(
        clause_id=payload.clause_id or "C-01",
        raw_text=payload.clause_text,
        page_number=payload.page_number or 1,
        section_name=payload.section_name or "General Covenants"
    )
    return record


@router.get("/{document_id}/clauses-structured", response_model=List[StructuredClauseRecord])
async def get_document_structured_clauses(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Extract all legally meaningful clauses from the document into structured, explainable records.
    Guarantees deterministic extractions (dates, currency, percentages, durations, sections)
    are preserved with AI semantic interpretation and statutory cross-references.
    """
    doc_query = select(Document).where(Document.id == document_id)
    doc_res = await db.execute(doc_query)
    doc = doc_res.scalar_one_or_none()

    if not doc:
        raise ObjectNotFoundError("Document")

    authorize_object_access(
        user=current_user,
        resource=doc,
        action=Action.READ
    )

    chunk_query = select(DocumentChunk).where(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index)
    chunk_res = await db.execute(chunk_query)
    chunks = chunk_res.scalars().all()

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no content chunks available for clause intelligence."
        )

    full_text = "\n\n".join([c.clean_content for c in chunks])
    records = await process_document_clauses_async(full_text, default_page=1)
    return records


@router.post("/{document_id}", response_model=AnalysisResponse)
async def analyze_document_endpoint(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    ai_provider: BaseAIProvider = Depends(get_ai),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform deep legal analysis:
    - Simplifies document into plain English and Hindi summaries.
    - Extracts and classifies key clauses.
    - Identifies red flags, harsh penalties, and asymmetric obligations.
    - Detects missing customary statutory protections.
    """
    # Fetch document with centralized object-level authorization
    doc_query = select(Document).where(Document.id == document_id)
    doc_res = await db.execute(doc_query)
    doc = doc_res.scalar_one_or_none()

    if not doc:
        raise ObjectNotFoundError("Document")

    authorize_object_access(
        user=current_user,
        resource=doc,
        action=Action.READ
    )

    # Fetch document chunks
    chunk_query = select(DocumentChunk).where(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index)
    chunk_res = await db.execute(chunk_query)
    chunks = chunk_res.scalars().all()

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no content chunks available for analysis."
        )

    full_text = "\n\n".join([c.clean_content for c in chunks])


    # Run AI Analysis
    raw_analysis = await ai_provider.analyze_document(full_text, doc.title)

    # Convert to schema items
    clauses = [ClauseItem(**c) for c in raw_analysis.get("clauses", [])]
    risks = [RiskItem(**r) for r in raw_analysis.get("risks", [])]
    obligations = [ObligationItem(**o) for o in raw_analysis.get("obligations", [])]
    missing = [MissingClauseItem(**m) for m in raw_analysis.get("missing_clauses", [])]

    # Check if analysis record exists, update or create
    existing_q = select(AnalysisResult).where(AnalysisResult.document_id == doc.id)
    existing_res = await db.execute(existing_q)
    existing_analysis = existing_res.scalar_one_or_none()

    clauses_json = json.dumps([c.model_dump() for c in clauses])
    risks_json = json.dumps([r.model_dump() for r in risks])
    obligations_json = json.dumps([o.model_dump() for o in obligations])
    missing_json = json.dumps([m.model_dump() for m in missing])

    if existing_analysis:
        existing_analysis.summary_citizen = raw_analysis.get("summary_citizen", "")
        existing_analysis.summary_legal = raw_analysis.get("summary_legal", "")
        existing_analysis.summary_hindi = raw_analysis.get("summary_hindi", "")
        existing_analysis.clauses_json = clauses_json
        existing_analysis.risks_json = risks_json
        existing_analysis.obligations_json = obligations_json
        existing_analysis.missing_clauses_json = missing_json
        existing_analysis.flesch_kincaid_score = raw_analysis.get("flesch_kincaid_score", 55.0)
    else:
        new_analysis = AnalysisResult(
            document_id=doc.id,
            summary_citizen=raw_analysis.get("summary_citizen", ""),
            summary_legal=raw_analysis.get("summary_legal", ""),
            summary_hindi=raw_analysis.get("summary_hindi", ""),
            clauses_json=clauses_json,
            risks_json=risks_json,
            obligations_json=obligations_json,
            missing_clauses_json=missing_json,
            flesch_kincaid_score=raw_analysis.get("flesch_kincaid_score", 55.0)
        )
        db.add(new_analysis)

    await db.commit()

    log_audit_event(
        action="DOCUMENT_ANALYZED",
        user_id=current_user.id,
        target_type="Document",
        target_id=doc.id,
        ip_address=request.client.host if request.client else None,
        status="SUCCESS",
        details={"clauses_count": len(clauses), "risks_count": len(risks)}
    )

    return AnalysisResponse(
        document_id=doc.id,
        summary_citizen=raw_analysis.get("summary_citizen", ""),
        summary_legal=raw_analysis.get("summary_legal", ""),
        summary_hindi=raw_analysis.get("summary_hindi", ""),
        flesch_kincaid_score=raw_analysis.get("flesch_kincaid_score", 55.0),
        reading_level=raw_analysis.get("reading_level", "Standard Citizen Level"),
        clauses=clauses,
        risks=risks,
        obligations=obligations,
        missing_clauses=missing
    )

@router.get("/{document_id}", response_model=AnalysisResponse)
async def get_analysis(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve existing cached analysis for a document."""
    doc_query = select(Document).where(Document.id == document_id)
    doc_res = await db.execute(doc_query)
    doc = doc_res.scalar_one_or_none()

    if not doc:
        raise ObjectNotFoundError("Document")

    authorize_object_access(
        user=current_user,
        resource=doc,
        action=Action.READ
    )

    q = select(AnalysisResult).where(AnalysisResult.document_id == doc.id)
    res = await db.execute(q)
    analysis = res.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis has not yet been run for this document. Please trigger POST /analysis/{document_id}."
        )

    clauses = [ClauseItem(**c) for c in json.loads(analysis.clauses_json)]
    risks = [RiskItem(**r) for r in json.loads(analysis.risks_json)]
    obligations = [ObligationItem(**o) for o in json.loads(analysis.obligations_json)]
    missing = [MissingClauseItem(**m) for m in json.loads(analysis.missing_clauses_json)]

    return AnalysisResponse(
        document_id=doc.id,
        summary_citizen=analysis.summary_citizen,
        summary_legal=analysis.summary_legal,
        summary_hindi=analysis.summary_hindi,
        flesch_kincaid_score=analysis.flesch_kincaid_score,
        reading_level="Standard Citizen Level (Grade 9-10)",
        clauses=clauses,
        risks=risks,
        obligations=obligations,
        missing_clauses=missing
    )


@router.get("/{document_id}/checklist")
async def get_document_checklist(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get tailored procedural action checklist based on document content."""
    doc_query = select(Document).where(Document.id == document_id)
    doc_res = await db.execute(doc_query)
    doc = doc_res.scalar_one_or_none()

    if not doc:
        raise ObjectNotFoundError("Document")

    authorize_object_access(
        user=current_user,
        resource=doc,
        action=Action.READ
    )

    return get_action_checklist(doc.title)


class RiskEvaluateTextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(..., min_length=10, max_length=50000, description="Legal text or clause to evaluate for risks")
    document_title: Optional[str] = Field("Ad-hoc Document", max_length=200, description="Optional title or context")


@router.post("/{document_id}/risk-engine", response_model=RiskEngineResult)
async def evaluate_document_risks_endpoint(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    ai_provider: BaseAIProvider = Depends(get_ai),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute the NYAYA RAKSHAK Deterministic + AI-Assisted Risk Engine on a document.
    Enforces strict 4-layer separation (Finding, Evidence, Classification, Explanation)
    across all 13 risk categories with mandatory language hedging.
    """
    doc_query = select(Document).where(Document.id == document_id)
    doc_res = await db.execute(doc_query)
    doc = doc_res.scalar_one_or_none()

    if not doc:
        raise ObjectNotFoundError("Document")

    authorize_object_access(
        user=current_user,
        resource=doc,
        action=Action.READ
    )

    chunk_query = select(DocumentChunk).where(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index)
    chunk_res = await db.execute(chunk_query)
    chunks = chunk_res.scalars().all()

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no content chunks available for risk analysis."
        )

    full_text = "\n\n".join([c.clean_content for c in chunks])
    result = await risk_engine.analyze_document_risks(
        document_text=full_text,
        document_id=doc.id,
        document_title=doc.title,
        ai_provider=ai_provider
    )

    log_audit_event(
        action="RISK_ENGINE_EVALUATED",
        user_id=current_user.id,
        target_type="Document",
        target_id=doc.id,
        ip_address=request.client.host if request.client else None,
        status="SUCCESS",
        details={"total_risks": result.summary.total_risks, "verdict": result.summary.overall_health_verdict}
    )

    return result


@router.post("/risk-engine/evaluate-text", response_model=RiskEngineResult)
async def evaluate_text_risks_endpoint(
    payload: RiskEvaluateTextRequest,
    current_user: User = Depends(get_current_user),
    ai_provider: BaseAIProvider = Depends(get_ai)
):
    """
    On-demand ad-hoc evaluation of arbitrary contract text through the NYAYA RAKSHAK Risk Engine.
    """
    return await risk_engine.analyze_document_risks(
        document_text=payload.text,
        document_title=payload.document_title,
        ai_provider=ai_provider
    )


@router.get("/risk-engine/rules", response_model=List[RuleVersionInfo])
async def list_versioned_risk_rules(
    current_user: User = Depends(get_current_user)
):
    """
    List all registered, versioned deterministic risk rules with audit changelogs.
    """
    return risk_rule_registry.get_all_rule_infos()


@router.post("/{document_id}/action-navigator", response_model=ActionNavigatorResponse)
async def generate_action_plan(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    ai_provider: BaseAIProvider = Depends(get_ai),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a conservative, non-binding Action Navigator plan for a document.

    The plan includes:
      - KNOWN FACTS (verified from document)
      - UNKNOWN FACTS (gaps/ambiguities)
      - IMPORTANT DOCUMENTS (to collect or verify)
      - IMPORTANT DATES (deadlines, notice periods)
      - POTENTIAL ISSUES (from deterministic risk engine)
      - QUESTIONS TO ASK (from risk recommended questions)
      - POSSIBLE NEXT STEPS (dependency-ordered, evidence-anchored)
      - WHEN TO SEEK PROFESSIONAL HELP (hard escalation triggers)

    This endpoint NEVER states a legal outcome. All steps are non-binding.
    """
    # 1. Fetch & authorize document
    doc_query = select(Document).where(Document.id == document_id)
    doc_res = await db.execute(doc_query)
    doc = doc_res.scalar_one_or_none()
    if not doc:
        raise ObjectNotFoundError("Document")
    authorize_object_access(user=current_user, resource=doc, action=Action.READ)

    # 2. Load document chunks for full text
    chunk_query = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc.id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunk_res = await db.execute(chunk_query)
    chunks = chunk_res.scalars().all()
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no content chunks available for Action Navigator.",
        )
    full_text = "\n\n".join(c.clean_content for c in chunks)

    # 3. Load cached analysis (create if not exists)
    analysis_q = select(AnalysisResult).where(AnalysisResult.document_id == doc.id)
    analysis_res = await db.execute(analysis_q)
    analysis = analysis_res.scalar_one_or_none()

    if not analysis:
        # Run analysis first to populate the cache
        raw = await ai_provider.analyze_document(full_text, doc.title)
        clauses = [ClauseItem(**c) for c in raw.get("clauses", [])]
        analysis_risks_items = [RiskItem(**r) for r in raw.get("risks", [])]
        obligations_items = [ObligationItem(**o) for o in raw.get("obligations", [])]
        missing_items = [MissingClauseItem(**m) for m in raw.get("missing_clauses", [])]
        import json as _json
        analysis = AnalysisResult(
            document_id=doc.id,
            summary_citizen=raw.get("summary_citizen", ""),
            summary_legal=raw.get("summary_legal", ""),
            summary_hindi=raw.get("summary_hindi", ""),
            clauses_json=_json.dumps([c.model_dump() for c in clauses]),
            risks_json=_json.dumps([r.model_dump() for r in analysis_risks_items]),
            obligations_json=_json.dumps([o.model_dump() for o in obligations_items]),
            missing_clauses_json=_json.dumps([m.model_dump() for m in missing_items]),
            flesch_kincaid_score=raw.get("flesch_kincaid_score", 55.0),
        )
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)

    # 4. Run deterministic Risk Engine (always fresh — fast, < 2s)
    risk_result = await risk_engine.analyze_document_risks(
        document_text=full_text,
        document_id=doc.id,
        document_title=doc.title,
        ai_provider=ai_provider,
    )

    # 5. Generate Action Navigator plan (fully deterministic from this point)
    plan = _action_navigator_engine.generate(
        document_id=doc.id,
        document_title=doc.title,
        document_full_text=full_text,
        analysis_clauses_json=analysis.clauses_json,
        analysis_risks_json=analysis.risks_json,
        analysis_obligations_json=analysis.obligations_json,
        analysis_missing_clauses_json=analysis.missing_clauses_json,
        risk_engine_result=risk_result,
    )

    log_audit_event(
        action="ACTION_NAVIGATOR_GENERATED",
        user_id=current_user.id,
        target_type="Document",
        target_id=doc.id,
        ip_address=request.client.host if request.client else None,
        status="SUCCESS",
        details={
            "steps": len(plan.possible_next_steps),
            "escalation_triggers": len(plan.when_to_seek_professional_help),
            "professional_review_recommended": plan.professional_review_recommended,
        },
    )

    return plan

