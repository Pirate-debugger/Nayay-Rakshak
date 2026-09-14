from typing import List, Optional, Union

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.ai.base import BaseAIProvider
from app.ai.factory import get_ai_provider
from app.core.authorization import check_user_role
from app.core.roles import Role
from app.core.security import decode_access_token
from app.db.base import get_db
from app.db.models import RevokedToken, User

security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Validate bearer token, check session revocation registry, and retrieve authenticated user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("token_type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Bearer access token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check session revocation registry
    jti = payload.get("jti")
    if jti:
        revoked = await db.execute(select(RevokedToken).where(RevokedToken.token_jti == jti))
        if revoked.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    user_id = payload.get("sub")
    query = select(User).where(User.id == int(user_id))
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Optional user authentication for public/demo endpoints."""
    if not credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload or payload.get("token_type") != "access":
        return None
    try:
        user_id = payload.get("sub")
        query = select(User).where(User.id == int(user_id))
        result = await db.execute(query)
        return result.scalar_one_or_none()
    except Exception:
        return None


def require_roles(allowed_roles: List[Union[str, Role]]):
    """Dependency factory enforcing Role-Based Access Control (RBAC)."""
    async def _role_verifier(current_user: User = Depends(get_current_user)) -> User:
        check_user_role(current_user, allowed_roles)
        return current_user
    return _role_verifier


require_admin = require_roles([Role.ADMIN, Role.SYSTEM_OPERATOR])
require_system_operator = require_roles([Role.SYSTEM_OPERATOR])


def get_ai() -> BaseAIProvider:
    """Dependency injection for AI provider."""
    return get_ai_provider()
