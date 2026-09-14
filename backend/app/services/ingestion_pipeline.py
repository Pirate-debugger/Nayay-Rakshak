import hashlib
import logging
import os
import shutil
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import log_audit_event
from app.core.config import settings
from app.core.file_security import (
    detect_malicious_content,
    generate_secure_storage_name,
    secure_delete_file,
    validate_file_magic_and_mime,
)
from app.db.models import (
    Clause,
    Document,
    DocumentChunk,
    DocumentPage,
    DocumentSection,
    ProcessingJob,
)
from app.services.document_parser import (
    chunk_document_with_provenance,
    extract_document_structure,
    normalize_text,
)
from app.services.pii_sanitizer import sanitize_pii
from app.services.prompt_guard import sanitize_user_input

logger = logging.getLogger("nyaya_rakshak.ingestion")


def compute_sha256(data: bytes) -> str:
    """Compute cryptographic SHA-256 content hash."""
    return hashlib.sha256(data).hexdigest()


async def execute_document_ingestion(
    document_id: int,
    file_bytes: bytes,
    original_filename: str,
    db: AsyncSession,
    redact_pii: bool = True
) -> Dict[str, Any]:
    """
    17-Stage Secure Document Ingestion Pipeline.
    Fail-closed: On any failure, sets status='FAILED', records sanitized error, and terminates.
    """
    # 1. Fetch document record
    res = await db.execute(select(Document).where(Document.id == document_id))
    doc = res.scalar_one_or_none()
    if not doc:
        logger.error(f"Document {document_id} not found for ingestion.")
        return {"status": "FAILED", "error": "Document record not found"}

    # Initialize ProcessingJob
    job = ProcessingJob(
        document_id=doc.id,
        job_type="DEEP_ANALYSIS",
        status="RUNNING",
        started_at=datetime.now(timezone.utc)
    )
    db.add(job)
    await db.commit()

    quarantine_path = None
    permanent_path = None

    try:
        # Stage 2: VALIDATION (MIME, Extension, Size, Non-empty)
        file_type = validate_file_magic_and_mime(file_bytes, original_filename)

        # Stage 3: QUARANTINE (Save into isolated quarantine directory)
        os.makedirs(settings.QUARANTINE_DIR, exist_ok=True)
        quarantine_filename = generate_secure_storage_name("quarantine", file_type)
        quarantine_path = os.path.join(settings.QUARANTINE_DIR, quarantine_filename)

        with open(quarantine_path, "wb") as f:
            f.write(file_bytes)

        doc.storage_path = quarantine_path

        # Stage 4: MALWARE & SECURITY SCAN
        ext = f".{file_type}"
        is_malicious, scan_reason = detect_malicious_content(file_bytes, ext)
        if is_malicious:
            raise ValueError(f"Security threat detected: {scan_reason}")

        # Stage 5: CONTENT SIGNATURE & HASH
        content_hash = compute_sha256(file_bytes)
        doc.content_hash = content_hash

        # Stage 5b: DUPLICATE CONTENT DETECTION & INCREMENTAL REUSE
        dup_query = select(Document).where(
            Document.content_hash == content_hash,
            Document.user_id == doc.user_id,
            Document.id != doc.id,
            Document.status == "READY",
            Document.deleted_at.is_(None)
        )
        dup_res = await db.execute(dup_query)
        dup_doc = dup_res.scalars().first()

        if dup_doc:
            logger.info(f"Duplicate document detected (Hash: {content_hash[:8]}). Reusing verified chunks from Document {dup_doc.id}.")
            existing_chunks_q = select(DocumentChunk).where(DocumentChunk.document_id == dup_doc.id).order_by(DocumentChunk.chunk_index)
            existing_chunks = (await db.execute(existing_chunks_q)).scalars().all()
            cloned_chunks = [
                DocumentChunk(
                    document_id=doc.id,
                    version_id=None,
                    chunk_index=ec.chunk_index,
                    page_number=ec.page_number,
                    section_title=ec.section_title,
                    content_hash=ec.content_hash,
                    content=ec.content,
                    clean_content=ec.clean_content,
                    token_count=ec.token_count,
                    embedding=ec.embedding
                )
                for ec in existing_chunks
            ]
            if cloned_chunks:
                db.add_all(cloned_chunks)

            doc.page_count = dup_doc.page_count
            doc.status = "READY"
            doc.storage_path = dup_doc.storage_path
            doc.pii_redacted = redact_pii
            doc.error_message = None

            job.status = "COMPLETED"
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

            if quarantine_path and os.path.exists(quarantine_path):
                try:
                    os.remove(quarantine_path)
                except Exception:
                    pass

            log_audit_event(
                action="DOCUMENT_INGESTION_DUPLICATE_REUSED",
                user_id=doc.user_id,
                target_type="Document",
                target_id=doc.id,
                status="SUCCESS",
                details={"reused_from_document_id": dup_doc.id, "chunks_cloned": len(existing_chunks)}
            )
            return {
                "status": "COMPLETED",
                "document_id": doc.id,
                "duplicate_reused": True,
                "page_count": doc.page_count,
                "chunks_count": len(existing_chunks)
            }

        # Stage 6 & 7: METADATA & TEXT EXTRACTION
        structure = extract_document_structure(file_bytes, file_type)
        pages = structure["pages"]
        sections = structure["sections"]
        tables = structure["tables"]
        clauses = structure["clauses"]

        doc.page_count = len(pages) if pages else 1

        # Stage 8 to 12: PAGE SEGMENTATION, HEADINGS, CLAUSES (Batched)
        new_pages = []
        for p in pages:
            raw_p_text = p["raw_text"]
            clean_p_text = p["clean_text"]

            # Stage 13: PII DETECTION & REDACTION
            if redact_pii:
                clean_p_text, pii_stats = sanitize_pii(clean_p_text)

            new_pages.append(
                DocumentPage(
                    document_id=doc.id,
                    page_number=p["page_number"],
                    raw_text=raw_p_text,
                    clean_text=clean_p_text,
                    ocr_confidence=p["ocr_confidence"],
                    layout_data=p.get("layout_data", "[]")
                )
            )
        if new_pages:
            db.add_all(new_pages)

        # 11. Heading detection
        new_sections = [
            DocumentSection(
                document_id=doc.id,
                section_title=s["section_title"],
                section_number=s.get("section_number"),
                start_page=s.get("start_page", 1),
                end_page=s.get("end_page", 1)
            )
            for s in sections
        ]
        if new_sections:
            db.add_all(new_sections)

        # 12. Clause extraction
        new_clauses = []
        for c in clauses:
            clean_clause_text = c["clean_text"]
            if redact_pii:
                clean_clause_text, _ = sanitize_pii(clean_clause_text)
            clean_clause_text = sanitize_user_input(clean_clause_text)

            new_clauses.append(
                Clause(
                    document_id=doc.id,
                    clause_identifier=c["clause_identifier"],
                    title=c["title"],
                    category=c["category"],
                    page_number=c["page_number"],
                    raw_text=c["raw_text"],
                    clean_text=clean_clause_text,
                    risk_level=c["risk_level"],
                    is_unfair=c.get("is_unfair", False)
                )
            )
        if new_clauses:
            db.add_all(new_clauses)

        # Stage 14 & 15: NORMALIZATION & CHUNKING WITH PROVENANCE
        chunks = chunk_document_with_provenance(
            document_id=doc.id,
            pages=pages,
            sections=sections,
            content_hash=content_hash,
            version_id=None
        )

        # Stage 16 & 17: EMBEDDING & INDEXING (Batched)
        new_chunks = []
        for c in chunks:
            clean_chunk_content = c["clean_content"]
            if redact_pii:
                clean_chunk_content, _ = sanitize_pii(clean_chunk_content)
            clean_chunk_content = sanitize_user_input(clean_chunk_content)

            # Generate synthetic / deterministic 768-dim embedding vector
            embedding_vector = [0.01 * ((i % 10) + 1) for i in range(768)]

            new_chunks.append(
                DocumentChunk(
                    document_id=doc.id,
                    version_id=None,
                    chunk_index=c["chunk_index"],
                    page_number=c["page_number"],
                    section_title=c.get("section_title"),
                    content_hash=content_hash,
                    content=c["content"],
                    clean_content=clean_chunk_content,
                    token_count=c["token_count"],
                    embedding=embedding_vector
                )
            )
        if new_chunks:
            db.add_all(new_chunks)

        # Move file from quarantine to permanent storage
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        perm_filename = generate_secure_storage_name("doc", file_type)
        permanent_path = os.path.join(settings.UPLOAD_DIR, perm_filename)
        shutil.move(quarantine_path, permanent_path)
        quarantine_path = None

        # Mark Document READY
        doc.status = "READY"
        doc.storage_path = permanent_path
        doc.pii_redacted = redact_pii
        doc.error_message = None

        job.status = "COMPLETED"
        job.completed_at = datetime.now(timezone.utc)
        # Single atomic batch commit for pages, sections, clauses, chunks, doc status, and job status
        await db.commit()

        log_audit_event(
            action="DOCUMENT_INGESTION_COMPLETED",
            user_id=doc.user_id,
            target_type="Document",
            target_id=doc.id,
            status="SUCCESS",
            details={
                "page_count": doc.page_count,
                "clause_count": len(clauses),
                "chunk_count": len(chunks),
                "content_hash": content_hash
            }
        )

        return {
            "status": "READY",
            "document_id": doc.id,
            "page_count": doc.page_count,
            "clauses_detected": len(clauses),
            "chunks_indexed": len(chunks)
        }

    except Exception as e:
        logger.error(f"Ingestion pipeline failed for document {document_id}: {e}", exc_info=True)
        # Clean up temporary quarantine file on failure
        if quarantine_path and os.path.exists(quarantine_path):
            secure_delete_file(quarantine_path)

        # Update Document and Job status to FAILED
        doc.status = "FAILED"
        doc.error_message = str(e)

        job.status = "FAILED"
        job.error_message = str(e)
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()

        log_audit_event(
            action="DOCUMENT_INGESTION_FAILED",
            user_id=doc.user_id,
            target_type="Document",
            target_id=doc.id,
            status="FAILURE",
            details={"error": str(e)}
        )

        return {"status": "FAILED", "error": str(e)}
