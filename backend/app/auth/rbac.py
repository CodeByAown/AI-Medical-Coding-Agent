"""
Role-Based Access Control (RBAC) for AI Medical Coder.

Roles:
- admin: Full system access, user management, configuration
- coder: Submit clinical notes for coding, view own sessions
- reviewer: Review and approve/reject AI-coded results
- auditor: Read-only access to all sessions and audit logs

Permissions follow least-privilege principle.
"""
from enum import Enum
from typing import Set


class UserRole(str, Enum):
    ADMIN = "admin"
    CODER = "coder"
    REVIEWER = "reviewer"
    AUDITOR = "auditor"


class Permission(str, Enum):
    # Coding operations
    CODE_SUBMIT = "code:submit"
    CODE_VIEW_OWN = "code:view_own"
    CODE_VIEW_ALL = "code:view_all"
    CODE_SEARCH = "code:search"
    CODE_LOOKUP = "code:lookup"

    # Review operations
    REVIEW_VIEW = "review:view"
    REVIEW_SUBMIT = "review:submit"
    REVIEW_QUEUE = "review:queue"

    # Document operations
    DOCUMENT_UPLOAD = "document:upload"

    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # Audit operations
    AUDIT_VIEW = "audit:view"

    # System operations
    SYSTEM_HEALTH = "system:health"
    SYSTEM_CONFIG = "system:config"


# Role → Permission mapping
ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {
    UserRole.ADMIN: {p for p in Permission},  # All permissions

    UserRole.CODER: {
        Permission.CODE_SUBMIT,
        Permission.CODE_VIEW_OWN,
        Permission.CODE_SEARCH,
        Permission.CODE_LOOKUP,
        Permission.DOCUMENT_UPLOAD,
        Permission.SYSTEM_HEALTH,
    },

    UserRole.REVIEWER: {
        Permission.CODE_VIEW_ALL,
        Permission.CODE_SEARCH,
        Permission.CODE_LOOKUP,
        Permission.REVIEW_VIEW,
        Permission.REVIEW_SUBMIT,
        Permission.REVIEW_QUEUE,
        Permission.SYSTEM_HEALTH,
    },

    UserRole.AUDITOR: {
        Permission.CODE_VIEW_ALL,
        Permission.REVIEW_VIEW,
        Permission.REVIEW_QUEUE,
        Permission.AUDIT_VIEW,
        Permission.SYSTEM_HEALTH,
    },
}


def has_permission(role: UserRole, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permission(role: UserRole, permission: Permission) -> None:
    """Raise PermissionError if role lacks permission."""
    if not has_permission(role, permission):
        raise PermissionError(
            f"Role '{role}' does not have permission '{permission}'"
        )
