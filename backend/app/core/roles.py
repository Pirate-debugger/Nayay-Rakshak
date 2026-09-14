from enum import Enum
from typing import List, Union


class Role(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    SYSTEM_OPERATOR = "SYSTEM_OPERATOR"
    ADVOCATE = "ADVOCATE"


class Action(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    EXECUTE = "EXECUTE"
    ADMIN = "ADMIN"


ROLE_HIERARCHY = {
    Role.SYSTEM_OPERATOR: [Role.SYSTEM_OPERATOR, Role.ADMIN, Role.ADVOCATE, Role.USER],
    Role.ADMIN: [Role.ADMIN, Role.ADVOCATE, Role.USER],
    Role.ADVOCATE: [Role.ADVOCATE, Role.USER],
    Role.USER: [Role.USER],
}


def normalize_role(role: Union[str, Role]) -> str:
    """Normalize string or Role enum to standard uppercase role string."""
    if isinstance(role, Role):
        return role.value
    clean = str(role).strip().upper()
    if clean in ("USER", "CITIZEN"):
        return Role.USER.value
    if clean in ("ADMIN", "SUPERADMIN"):
        return Role.ADMIN.value
    if clean in ("SYSTEM_OPERATOR", "OPERATOR", "DEVOPS", "SYSOP"):
        return Role.SYSTEM_OPERATOR.value
    if clean in ("ADVOCATE", "LAWYER"):
        return Role.ADVOCATE.value
    return clean


def has_role_privilege(user_role: Union[str, Role], required_role: Union[str, Role]) -> bool:
    """Check if user_role has sufficient hierarchical privilege for required_role."""
    norm_user = normalize_role(user_role)
    norm_req = normalize_role(required_role)

    try:
        user_enum = Role(norm_user)
        req_enum = Role(norm_req)
        return req_enum in ROLE_HIERARCHY.get(user_enum, [])
    except ValueError:
        return norm_user == norm_req


def is_admin_or_operator(role: Union[str, Role]) -> bool:
    """Convenience helper for admin/operator permission checks."""
    norm = normalize_role(role)
    return norm in (Role.ADMIN.value, Role.SYSTEM_OPERATOR.value)
