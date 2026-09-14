import json

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.ai.base import BaseAIProvider
from app.api.deps import get_ai, get_current_user
from app.core.audit import log_audit_event
from app.core.authorization import authorize_object_access
from app.core.exceptions import ObjectNotFoundError
from app.core.roles import Action
from app.db.base import get_db
from app.db.models import AnalysisResult, ConsultationBrief, Document, DocumentChunk, User
from app.schemas.brief import BriefCreateRequest, BriefResponse
from app.services.brief_generator import generate_citizen_brief

router = APIRouter(prefix="/briefs", tags=["Consultation Briefs"])


@router.post("/", response_model=BriefResponse, status_code=status.HTTP_201_CREATED)
async def create_consultation_brief_endpoint(
    req: BriefCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    ai_provider: BaseAIProvider = Depends(get_ai),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a structured consultation brief for a citizen to take to an advocate.
    Synthesizes executive summary, red flags, missing protections, and targeted questions.
    """
    doc_res = await db.execute(select(Document).where(Document.id == req.document_id))
    doc = doc_res.scalar_one_or_none()
    if not doc:
        raise ObjectNotFoundError("Document")

    authorize_object_access(user=current_user, resource=doc, action=Action.READ)

    # Check for existing analysis or run on the fly
    analysis_res = await db.execute(
        select(AnalysisResult).where(AnalysisResult.document_id == doc.id)
    )
    analysis = analysis_res.scalar_one_or_none()

    if analysis:
        analysis_data = {
            "summary_citizen": analysis.summary_citizen,
            "summary_legal": analysis.summary_legal,
            "summary_hindi": analysis.summary_hindi,
            "risks": json.loads(analysis.risks_json),
            "clauses": json.loads(analysis.clauses_json),
            "missing_clauses": json.loads(analysis.missing_clauses_json),
        }
    else:
        chunks_res = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc.id)
            .order_by(DocumentChunk.chunk_index)
        )
        full_text = "\n\n".join([c.clean_content for c in chunks_res.scalars().all()])
        analysis_data = await ai_provider.analyze_document(full_text, doc.title)

    brief_data = generate_citizen_brief(
        document_title=doc.title,
        client_name=req.client_name.strip(),
        analysis_data=analysis_data,
        custom_questions=req.specific_questions,
    )

    brief_record = ConsultationBrief(
        user_id=current_user.id,
        document_id=doc.id,
        title=brief_data["title"],
        client_name=req.client_name.strip(),
        brief_markdown=brief_data["brief_markdown"],
        key_issues_json=json.dumps(brief_data["key_issues"]),
        questions_for_lawyer_json=json.dumps(brief_data["questions_for_lawyer"]),
    )
    db.add(brief_record)
    await db.commit()
    await db.refresh(brief_record)

    log_audit_event(
        action="BRIEF_CREATED",
        user_id=current_user.id,
        target_type="ConsultationBrief",
        target_id=brief_record.id,
        ip_address=request.client.host if request.client else None,
        status="SUCCESS",
    )

    return BriefResponse(
        id=brief_record.id,
        document_id=brief_record.document_id,
        title=brief_record.title,
        client_name=brief_record.client_name,
        brief_markdown=brief_record.brief_markdown,
        key_issues=brief_data["key_issues"],
        questions_for_lawyer=brief_data["questions_for_lawyer"],
        created_at=brief_record.created_at,
    )


@router.get("/{brief_id}", response_model=BriefResponse)
async def get_brief(
    brief_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve consultation brief with authorization check."""
    res = await db.execute(select(ConsultationBrief).where(ConsultationBrief.id == brief_id))
    brief = res.scalar_one_or_none()
    if not brief:
        raise ObjectNotFoundError("Consultation Brief")

    authorize_object_access(user=current_user, resource=brief, action=Action.READ)

    return BriefResponse(
        id=brief.id,
        document_id=brief.document_id,
        title=brief.title,
        client_name=brief.client_name,
        brief_markdown=brief.brief_markdown,
        key_issues=json.loads(brief.key_issues_json),
        questions_for_lawyer=json.loads(brief.questions_for_lawyer_json),
        created_at=brief.created_at,
    )


@router.get("/{brief_id}/export")
async def export_brief_markdown(
    brief_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export consultation brief as downloadable Markdown document."""
    res = await db.execute(select(ConsultationBrief).where(ConsultationBrief.id == brief_id))
    brief = res.scalar_one_or_none()
    if not brief:
        raise ObjectNotFoundError("Consultation Brief")

    authorize_object_access(user=current_user, resource=brief, action=Action.READ)

    safe_title = "".join(c for c in brief.title if c.isalnum() or c in (" ", "_", "-")).rstrip()
    filename = f"{safe_title.replace(' ', '_')}.md"

    return Response(
        content=brief.brief_markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
