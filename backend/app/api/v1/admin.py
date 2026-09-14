from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import require_admin, require_system_operator
from app.core.audit import log_audit_event
from app.db.base import get_db
from app.db.models import AuditLog, Document, ProcessingJob, SecurityEvent, User

router = APIRouter(prefix="/admin", tags=["Administration & Operations"])


@router.get("/stats", response_model=Dict[str, Any])
async def get_system_stats(
    admin_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    """
    Retrieve operational system metrics.
    Restricted to ADMIN and SYSTEM_OPERATOR roles.
    """
    total_users = len((await db.execute(select(User.id))).scalars().all())
    total_docs = len((await db.execute(select(Document.id))).scalars().all())
    total_jobs = len((await db.execute(select(ProcessingJob.id))).scalars().all())
    failed_jobs = len(
        (await db.execute(select(ProcessingJob.id).where(ProcessingJob.status == "FAILED")))
        .scalars()
        .all()
    )

    return {
        "total_users": total_users,
        "total_documents": total_docs,
        "total_processing_jobs": total_jobs,
        "failed_processing_jobs": failed_jobs,
        "operator_email": admin_user.email,
        "operator_role": admin_user.role,
    }


@router.get("/security-events", response_model=List[Dict[str, Any]])
async def list_security_events(
    operator: User = Depends(require_system_operator),
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    Inspect telemetry on security violations (BOLA attempts, prompt injections, rate limits).
    Restricted strictly to SYSTEM_OPERATOR.
    """
    q = select(SecurityEvent).order_by(SecurityEvent.timestamp.desc()).limit(limit)
    events = (await db.execute(q)).scalars().all()
    return [
        {
            "id": e.id,
            "uuid": e.uuid,
            "timestamp": e.timestamp.isoformat(),
            "user_id": e.user_id,
            "event_type": e.event_type,
            "severity": e.severity,
            "ip_address": e.ip_address,
            "payload_sample": e.payload_sample,
            "remediated": e.remediated,
        }
        for e in events
    ]


@router.get("/audit-logs", response_model=List[Dict[str, Any]])
async def list_audit_logs(
    admin_user: User = Depends(require_admin), limit: int = 50, db: AsyncSession = Depends(get_db)
):
    """
    Inspect immutable system audit trail.
    Restricted to ADMIN and SYSTEM_OPERATOR.
    """
    q = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
    logs = (await db.execute(q)).scalars().all()
    return [
        {
            "id": entry.id,
            "uuid": entry.uuid,
            "timestamp": entry.timestamp.isoformat(),
            "user_id": entry.user_id,
            "action": entry.action,
            "target_type": entry.target_type,
            "target_id": entry.target_id,
            "status": entry.status,
            "details_json": entry.details_json,
        }
        for entry in logs
    ]


@router.post("/users/{user_id}/unlock", status_code=status.HTTP_200_OK)
async def unlock_user_account(
    user_id: int, admin_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    """
    Manually unlock an account locked by brute-force protection.
    Restricted to ADMIN.
    """
    q = select(User).where(User.id == user_id)
    res = await db.execute(q)
    target_user = res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found.")

    target_user.failed_login_attempts = 0
    target_user.locked_until = None
    await db.commit()

    log_audit_event(
        action="USER_ACCOUNT_UNLOCKED_BY_ADMIN",
        user_id=admin_user.id,
        target_type="User",
        target_id=target_user.id,
        status="SUCCESS",
    )

    return {"message": f"User account {target_user.email} has been successfully unlocked."}
