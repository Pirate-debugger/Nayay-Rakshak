import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_user, security_bearer
from app.core.audit import log_audit_event
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    get_password_hash,
    hash_token,
    validate_password_strength,
    verify_password,
)
from app.db.base import get_db
from app.db.models import RefreshToken, RevokedToken, SecurityEvent, User
from app.schemas.auth import (
    SessionResponse,
    TokenRefreshRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def make_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)



@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    req: UserRegister,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Register a new citizen account with strict password validation."""
    clean_email = req.email.lower().strip()

    # 1. Enforce password complexity
    is_valid, reason = validate_password_strength(req.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password does not meet complexity requirements: {reason}"
        )

    # 2. Check duplicate email
    query = select(User).where(User.email == clean_email)
    res = await db.execute(query)
    existing = res.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # 3. Create user
    hashed_pw = get_password_hash(req.password)
    new_user = User(
        email=clean_email,
        hashed_password=hashed_pw,
        full_name=req.full_name.strip(),
        role="USER"
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # 4. Generate token pair
    access_token = create_access_token({"sub": str(new_user.id), "email": new_user.email, "role": new_user.role})
    refresh_jwt, t_hash, fam_id, exp_at = create_refresh_token(new_user.id)

    # Store refresh token
    ip_addr = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")[:250]
    db_refresh = RefreshToken(
        token_hash=t_hash,
        user_id=new_user.id,
        family_id=fam_id,
        expires_at=exp_at,
        ip_address=ip_addr,
        user_agent=user_agent
    )
    db.add(db_refresh)
    await db.commit()

    # Set secure HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_jwt,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth"
    )

    log_audit_event(
        action="USER_REGISTER",
        user_id=new_user.id,
        target_type="User",
        target_id=new_user.id,
        ip_address=ip_addr,
        status="SUCCESS"
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_jwt,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(new_user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    req: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user with brute-force lockout protection and issue token pair."""
    clean_email = req.email.lower().strip()
    ip_addr = request.client.host if request.client else None
    now = utc_now()

    query = select(User).where(User.email == clean_email)
    res = await db.execute(query)
    user = res.scalar_one_or_none()

    if not user:
        log_audit_event(
            action="USER_LOGIN_FAILED",
            target_type="User",
            ip_address=ip_addr,
            status="FAILURE",
            details={"reason": "User not found"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # Check account lockout
    locked_dt = make_aware(user.locked_until)
    if locked_dt and locked_dt > now:
        remaining_secs = int((locked_dt - now).total_seconds())
        remaining_mins = max(1, remaining_secs // 60)

        log_audit_event(
            action="LOCKED_ACCOUNT_LOGIN_ATTEMPT_BLOCKED",
            user_id=user.id,
            target_type="User",
            target_id=user.id,
            ip_address=ip_addr,
            status="DENIED"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account is temporarily locked due to excessive failed attempts. Try again in {remaining_mins} minute(s)."
        )

    # Verify password
    if not verify_password(req.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
            sec_event = SecurityEvent(
                user_id=user.id,
                event_type="RATE_LIMIT_EXCEEDED",
                severity="HIGH",
                ip_address=ip_addr,
                payload_sample=f"Brute force detected: {user.failed_login_attempts} failed attempts on email {clean_email}"
            )
            db.add(sec_event)

        await db.commit()

        log_audit_event(
            action="USER_LOGIN_FAILED",
            user_id=user.id,
            target_type="User",
            target_id=user.id,
            ip_address=ip_addr,
            status="FAILURE",
            details={"attempts": user.failed_login_attempts}
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # Reset failed attempts upon successful login
    user.failed_login_attempts = 0
    user.locked_until = None

    # Issue token pair
    access_token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    refresh_jwt, t_hash, fam_id, exp_at = create_refresh_token(user.id)

    user_agent = request.headers.get("user-agent", "")[:250]
    db_refresh = RefreshToken(
        token_hash=t_hash,
        user_id=user.id,
        family_id=fam_id,
        expires_at=exp_at,
        ip_address=ip_addr,
        user_agent=user_agent
    )
    db.add(db_refresh)
    await db.commit()

    response.set_cookie(
        key="refresh_token",
        value=refresh_jwt,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth"
    )

    log_audit_event(
        action="USER_LOGIN_SUCCESS",
        user_id=user.id,
        target_type="User",
        target_id=user.id,
        ip_address=ip_addr,
        status="SUCCESS"
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_jwt,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: Request,
    response: Response,
    req_body: Optional[TokenRefreshRequest] = None,
    cookie_token: Optional[str] = Cookie(None, alias="refresh_token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh Token Rotation with Reuse / Theft Detection.
    When a refresh token is used, it is revoked and replaced with a new token in the same family.
    If a revoked token is re-submitted, ALL tokens in that family are immediately terminated!
    """
    raw_token = (req_body.refresh_token if req_body else None) or cookie_token
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required. Provide in request body or cookie."
        )

    t_hash = hash_token(raw_token)
    q = select(RefreshToken).where(RefreshToken.token_hash == t_hash)
    res = await db.execute(q)
    token_record = res.scalar_one_or_none()

    now = utc_now()
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token. Please log in again."
        )

    # Check for Token Reuse / Theft Attempt FIRST
    if token_record.is_revoked:
        # Revoke the entire family immediately
        revoke_all_q = select(RefreshToken).where(RefreshToken.family_id == token_record.family_id)
        all_family = (await db.execute(revoke_all_q)).scalars().all()
        for t in all_family:
            t.is_revoked = True

        sec_event = SecurityEvent(
            user_id=token_record.user_id,
            event_type="BOLA_IDOR_ATTEMPT",
            severity="CRITICAL",
            ip_address=request.client.host if request.client else None,
            payload_sample=f"Refresh token reuse detected on family {token_record.family_id}. All family tokens revoked."
        )
        db.add(sec_event)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Security violation: Refresh token reuse detected. All sessions in this token family have been revoked and invalidated."
        )

    token_exp = make_aware(token_record.expires_at)
    if not token_exp or token_exp < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token. Please log in again."
        )


    # Invalidate current token and rotate to a new one
    token_record.is_revoked = True

    # Retrieve user
    u_res = await db.execute(select(User).where(User.id == token_record.user_id))
    user = u_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account no longer exists.")

    new_access_token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    new_refresh_jwt, new_hash, fam_id, exp_at = create_refresh_token(user.id, family_id=token_record.family_id)

    new_token_record = RefreshToken(
        token_hash=new_hash,
        user_id=user.id,
        family_id=fam_id,
        expires_at=exp_at,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:250]
    )
    db.add(new_token_record)
    await db.commit()

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_jwt,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth"
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_jwt,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Session Revocation & Logout.
    Blacklists the current access token JTI and revokes all active refresh tokens for the user.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token_str = auth_header[7:].strip()
        payload = decode_access_token(token_str)
        if payload and "jti" in payload:
            exp_ts = payload.get("exp")
            exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc) if exp_ts else utc_now() + timedelta(minutes=15)
            revoked_entry = RevokedToken(
                token_jti=payload["jti"],
                token_type="access",
                user_id=current_user.id,
                expires_at=exp_dt
            )
            db.add(revoked_entry)

    # Invalidate all active refresh tokens for this user
    q_refresh = select(RefreshToken).where(RefreshToken.user_id == current_user.id, RefreshToken.is_revoked.is_(False))
    active_tokens = (await db.execute(q_refresh)).scalars().all()
    for t in active_tokens:
        t.is_revoked = True

    await db.commit()

    # Clear cookie
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")

    log_audit_event(
        action="USER_LOGOUT",
        user_id=current_user.id,
        target_type="User",
        target_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        status="SUCCESS"
    )

    return {"message": "Logged out successfully. All session tokens revoked."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve profile of authenticated user."""
    return UserResponse.model_validate(current_user)


@router.get("/sessions", response_model=List[SessionResponse])
async def list_active_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all active cryptographic sessions for the authenticated user."""
    q = select(RefreshToken).where(
        RefreshToken.user_id == current_user.id,
        RefreshToken.is_revoked.is_(False),
        RefreshToken.expires_at > utc_now()
    ).order_by(RefreshToken.created_at.desc())
    sessions = (await db.execute(q)).scalars().all()
    return [SessionResponse.model_validate(s) for s in sessions]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
async def revoke_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Revoke a specific active session."""
    q = select(RefreshToken).where(
        RefreshToken.id == session_id,
        RefreshToken.user_id == current_user.id
    )
    res = await db.execute(q)
    sess = res.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    sess.is_revoked = True
    await db.commit()
    return {"message": f"Session {session_id} has been revoked."}
