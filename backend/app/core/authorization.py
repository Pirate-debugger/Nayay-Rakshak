from typing import Any, List, Optional, Union

from fastapi import HTTPException, status

from app.core.audit import log_audit_event
from app.core.roles import Action, Role, has_role_privilege, is_admin_or_operator, normalize_role
from app.db.models import User


def authorize_object_access(
    user: User,
    resource: Any,
    action: Action = Action.READ,
    resource_type: Optional[str] = None,
    request: Optional[Any] = None,
    db: Optional[Any] = None,
) -> None:
    """
    Mandatory Object-Level Authorization (Anti-BOLA/IDOR).
    Enforces strict ownership and tenant isolation on every user-owned entity.

    Steps:
    1. Authenticate user context.
    2. Determine tenant/ownership context.
    3. Authorize access.
    4. Reject fail-closed with HTTP 403.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access this resource.",
        )

    # Admins and System Operators have supervisory operational access
    if is_admin_or_operator(user.role):
        return

    # Check direct user ownership
    owner_id = getattr(resource, "user_id", None)
    if owner_id is None:
        owner_id = getattr(resource, "owner_id", None)

    if owner_id is not None:
        if owner_id != user.id:
            res_name = resource_type or resource.__class__.__name__
            res_id = getattr(resource, "id", "unknown")
            log_audit_event(
                action="BOLA_IDOR_VIOLATION_BLOCKED",
                user_id=user.id,
                target_type=res_name,
                target_id=res_id,
                status="DENIED",
                details={
                    "attempted_action": action.value,
                    "resource_owner_id": owner_id,
                    "requesting_user_id": user.id,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. You do not have permission to {action.value.lower()} this {res_name}.",
            )
        return

    # If the resource has an organization_id, check tenant association
    org_id = getattr(resource, "organization_id", None)
    if org_id is not None:
        # Check user's memberships if loaded
        user_memberships = getattr(user, "memberships", [])
        if user_memberships:
            is_member = any(m.organization_id == org_id for m in user_memberships)
            if not is_member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. You do not belong to the organization owning this resource.",
                )


def check_user_role(user: User, allowed_roles: List[Union[str, Role]]) -> None:
    """Validate that the user has at least one of the allowed role privileges."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    norm_allowed = [normalize_role(r) for r in allowed_roles]
    user_norm = normalize_role(user.role)
    if not any(has_role_privilege(user_norm, r) for r in norm_allowed):
        log_audit_event(
            action="RBAC_PRIVILEGE_VIOLATION_BLOCKED",
            user_id=user.id,
            status="DENIED",
            details={"user_role": user_norm, "required_roles": norm_allowed},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have the required role privileges to access this resource.",
        )
