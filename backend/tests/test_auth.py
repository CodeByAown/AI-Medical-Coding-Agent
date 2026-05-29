"""Tests for JWT authentication and RBAC."""
import pytest

from app.auth.jwt_handler import create_access_token, decode_access_token
from app.auth.rbac import Permission, UserRole, has_permission


def test_jwt_roundtrip():
    token = create_access_token("user-1", "test@test.com", UserRole.CODER)
    payload = decode_access_token(token)
    assert payload["sub"] == "user-1"
    assert payload["role"] == "coder"
    assert payload["type"] == "access"


def test_jwt_contains_email():
    token = create_access_token("user-1", "test@test.com", UserRole.REVIEWER)
    payload = decode_access_token(token)
    assert payload["email"] == "test@test.com"


def test_rbac_admin_has_all():
    for perm in Permission:
        assert has_permission(UserRole.ADMIN, perm), f"Admin should have {perm}"


def test_rbac_coder_cannot_review():
    assert not has_permission(UserRole.CODER, Permission.REVIEW_SUBMIT)


def test_rbac_coder_cannot_view_all():
    assert not has_permission(UserRole.CODER, Permission.CODE_VIEW_ALL)


def test_rbac_auditor_cannot_code():
    assert not has_permission(UserRole.AUDITOR, Permission.CODE_SUBMIT)


def test_rbac_reviewer_can_approve():
    assert has_permission(UserRole.REVIEWER, Permission.REVIEW_SUBMIT)


def test_rbac_auditor_can_view_audit():
    assert has_permission(UserRole.AUDITOR, Permission.AUDIT_VIEW)


def test_rbac_coder_has_health():
    assert has_permission(UserRole.CODER, Permission.SYSTEM_HEALTH)
