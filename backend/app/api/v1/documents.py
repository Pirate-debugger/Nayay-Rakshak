import logging
import os
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_user
from app.core.audit import log_audit_event
from app.core.authorization import authorize_object_access
from app.core.config import settings
from app.core.exceptions import ObjectNotFoundError
from app.core.file_security import (
    sanitize_filename,
    secure_delete_file,
    validate_file_magic_and_mime,
)
from app.core.rate_limit import limiter
from app.core.roles import Action
from app.db.base import AsyncSessionLocal, get_db
from app.db.models import (
    Document,
    DocumentChunk,
    ProcessingJob,
    User,
)
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentResponse,
    DocumentStatusResponse,
)
from app.services.ai_cache import ai_cache_service
from app.services.ingestion_pipeline import execute_document_ingestion

logger = logging.getLogger("nyaya_rakshak.documents")

router = APIRouter(prefix="/documents", tags=["Documents"])


async def _run_background_ingestion(
    document_id: int, file_bytes: bytes, original_filename: str, redact_pii: bool
):
    """Background worker task for non-blocking document ingestion."""
    async with AsyncSessionLocal() as session:
        try:
            await execute_document_ingestion(
                document_id=document_id,
                file_bytes=file_bytes,
                original_filename=original_filename,
                db=session,
                redact_pii=redact_pii,
            )
        except Exception as e:
            logger.error(
                f"Background ingestion worker failed for document {document_id}: {e}", exc_info=True
            )


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    redact_pii: bool = Form(True),
    async_processing: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Secure document upload endpoint executing the 17-stage ingestion flow:
    1. Validates magic bytes against extension (rejects disguised executables/macros).
    2. Enforces maximum file size limit (15MB) and rejects empty files.
    3. Stashes in isolated quarantine directory.
    4. Computes SHA-256 content hash.
    5. Extracts text and layout (supports PDF, DOCX, TXT, and scanned PNG/JPG via OCR).
    6. Redacts Indian PII (Aadhaar, PAN, phone, email, IFSC).
    7. Retains chunk provenance (document_id, page, section, content_hash).
    8. Updates status to READY upon completion or FAILED on any error.
    """
    contents = await file.read()
    raw_filename = file.filename or "uploaded_document.txt"
    safe_name = sanitize_filename(raw_filename)

    # Validate file integrity and magic signature fail-closed
    file_type = validate_file_magic_and_mime(contents, safe_name)

    doc_title = (
        title.strip()
        if title and title.strip()
        else os.path.splitext(safe_name)[0].replace("_", " ").title()
    )

    initial_status = "PROCESSING" if async_processing else "UPLOADED"
    # Create document record
    # Notice: Client-supplied user_id is completely ignored; strictly assigned to current_user.id
    doc = Document(
        user_id=current_user.id,
        title=doc_title,
        filename=safe_name,
        file_type=file_type,
        file_size=len(contents),
        storage_path="",  # Will be set during quarantine/indexing
        page_count=1,
        pii_redacted=redact_pii,
        status=initial_status,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # If non-blocking async worker processing requested
    if async_processing:
        background_tasks.add_task(
            _run_background_ingestion, doc.id, contents, safe_name, redact_pii
        )
        return DocumentResponse.model_validate(doc)

    # Synchronous processing pipeline
    await execute_document_ingestion(
        document_id=doc.id,
        file_bytes=contents,
        original_filename=safe_name,
        db=db,
        redact_pii=redact_pii,
    )

    await db.refresh(doc)

    log_audit_event(
        action="DOCUMENT_UPLOAD_PROCESSED",
        user_id=current_user.id,
        target_type="Document",
        target_id=doc.id,
        ip_address=request.client.host if request.client else None,
        status="SUCCESS" if doc.status == "READY" else "FAILURE",
        details={
            "filename": safe_name,
            "status": doc.status,
            "page_count": doc.page_count,
            "error_message": doc.error_message,
        },
    )

    return DocumentResponse.model_validate(doc)


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve real-time processing status of a document.
    Enforces object-level authorization (IDOR/BOLA protected).
    """
    query = select(Document).where(Document.id == document_id)
    res = await db.execute(query)
    doc = res.scalar_one_or_none()

    if not doc:
        raise ObjectNotFoundError("Document")

    authorize_object_access(current_user, doc, Action.READ)

    # Fetch associated processing jobs
    jobs_q = (
        select(ProcessingJob)
        .where(ProcessingJob.document_id == doc.id)
        .order_by(ProcessingJob.created_at.desc())
    )
    jobs = (await db.execute(jobs_q)).scalars().all()

    jobs_data = [
        {
            "id": j.id,
            "job_type": j.job_type,
            "status": j.status,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            "error_message": j.error_message,
        }
        for j in jobs
    ]

    return DocumentStatusResponse(
        id=doc.id,
        status=doc.status,
        page_count=doc.page_count,
        error_message=doc.error_message,
        content_hash=doc.content_hash,
        jobs=jobs_data,
    )


@router.post("/load-sample", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def load_sample_document(
    sample_key: str = Form("standard_residential_lease_delhi"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Load a realistic sample Indian legal document for instant demonstration."""
    sample_files = {
        "standard_residential_lease_delhi": (
            "Standard Residential Lease (Delhi NCR)",
            "sample_documents/standard_residential_lease_delhi.txt",
        ),
        "harsh_landlord_lease_delhi": (
            "Harsh Landlord Lease (Delhi NCR - High Risk)",
            "sample_documents/harsh_landlord_lease_delhi.txt",
        ),
        "employment_agreement_tech_bangalore": (
            "Tech Employment & Non-Compete Agreement (Bangalore)",
            "sample_documents/employment_agreement_tech_bangalore.txt",
        ),
        "consumer_services_contract": (
            "Consumer Subscription Terms (Unfair Terms)",
            "sample_documents/consumer_services_contract.txt",
        ),
    }

    if sample_key not in sample_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown sample key. Available samples: {list(sample_files.keys())}",
        )

    title, rel_path = sample_files[sample_key]
    if not os.path.exists(rel_path):
        candidate_parent = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../..", rel_path)
        )
        candidate_parent2 = os.path.join("..", rel_path)
        if os.path.exists(candidate_parent):
            rel_path = candidate_parent
        elif os.path.exists(candidate_parent2):
            rel_path = candidate_parent2
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample file {rel_path} not found on server.",
            )

    with open(rel_path, "rb") as f:
        content_bytes = f.read()

    doc = Document(
        user_id=current_user.id,
        title=title,
        filename=os.path.basename(rel_path),
        file_type="txt",
        file_size=len(content_bytes),
        storage_path=rel_path,
        page_count=1,
        pii_redacted=True,
        status="UPLOADED",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Ingest through pipeline
    await execute_document_ingestion(
        document_id=doc.id,
        file_bytes=content_bytes,
        original_filename=os.path.basename(rel_path),
        db=db,
        redact_pii=True,
    )
    await db.refresh(doc)

    return DocumentResponse.model_validate(doc)


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """List all documents owned by current user (excluding soft-deleted)."""
    query = (
        select(Document)
        .where(Document.user_id == current_user.id, Document.deleted_at.is_(None))
        .order_by(Document.created_at.desc())
    )
    res = await db.execute(query)
    docs = res.scalars().all()
    return [DocumentResponse.model_validate(d) for d in docs]


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve document details and chunk previews with strict object-level authorization."""
    query = select(Document).where(Document.id == document_id)
    res = await db.execute(query)
    doc = res.scalar_one_or_none()

    if not doc:
        raise ObjectNotFoundError("Document")

    # Centralized Object-Level Authorization (IDOR/BOLA defense)
    authorize_object_access(current_user, doc, Action.READ)

    # Fetch chunks count and sample text
    chunk_query = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc.id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunk_res = await db.execute(chunk_query)
    chunks = chunk_res.scalars().all()

    preview = "\n".join([c.clean_content for c in chunks[:3]]) if chunks else ""

    return DocumentDetailResponse(
        id=doc.id,
        user_id=doc.user_id,
        title=doc.title,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        page_count=doc.page_count,
        pii_redacted=doc.pii_redacted,
        status=doc.status,
        error_message=doc.error_message,
        content_hash=doc.content_hash,
        created_at=doc.created_at,
        chunk_count=len(chunks),
        preview_text=preview[:1200],
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Securely delete document with strict object-level authorization and physical disk wiping.
    """
    query = select(Document).where(Document.id == document_id)
    res = await db.execute(query)
    doc = res.scalar_one_or_none()

    if not doc:
        raise ObjectNotFoundError("Document")

    # Centralized Object-Level Authorization (IDOR/BOLA defense)
    authorize_object_access(current_user, doc, Action.DELETE)

    # Securely wipe physical file from disk
    if doc.storage_path:
        secure_delete_file(doc.storage_path)

    # Purge sensitive AI cache entries associated with this document (privacy guarantee)
    if doc.content_hash:
        await ai_cache_service.evict_document(doc.content_hash, db=db)

    await db.delete(doc)
    await db.commit()

    log_audit_event(
        action="DOCUMENT_DELETED",
        user_id=current_user.id,
        target_type="Document",
        target_id=document_id,
        ip_address=request.client.host if request.client else None,
        status="SUCCESS",
    )
    return None
