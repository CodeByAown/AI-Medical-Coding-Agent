"""Initial schema — all tables including auth and audit

Revision ID: 001
Revises:
Create Date: 2026-05-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_user_email", "users", ["email"])
    op.create_index("ix_user_role", "users", ["role"])

    # ── audit_logs ─────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(100), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_action", "audit_logs", ["action"])
    op.create_index("ix_audit_created", "audit_logs", ["created_at"])
    op.create_index("ix_audit_user", "audit_logs", ["user_id"])

    # ── refresh_tokens ─────────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_token_hash", "refresh_tokens", ["token_hash"])
    op.create_index("ix_refresh_user", "refresh_tokens", ["user_id"])

    # ── coding_sessions ────────────────────────────────────────────────────
    op.create_table(
        "coding_sessions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("specialty", sa.String(50), nullable=False),
        sa.Column("patient_id", sa.String(100), nullable=True),
        sa.Column("encounter_id", sa.String(100), nullable=True),
        sa.Column("clinical_text", sa.Text(), nullable=False),
        sa.Column("phi_encrypted", sa.Boolean(), nullable=False),
        sa.Column("soap_json", sa.JSON(), nullable=True),
        sa.Column("extracted_entities_json", sa.JSON(), nullable=True),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("requires_human_review", sa.Boolean(), nullable=True),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.Column("reviewer_id", sa.String(100), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_session_created", "coding_sessions", ["created_at"])
    op.create_index("ix_session_status_created", "coding_sessions", ["status", "created_at"])
    op.create_index("ix_session_user_id", "coding_sessions", ["user_id"])
    op.create_index("ix_coding_sessions_status", "coding_sessions", ["status"])
    op.create_index("ix_coding_sessions_patient_id", "coding_sessions", ["patient_id"])
    op.create_index("ix_coding_sessions_encounter_id", "coding_sessions", ["encounter_id"])

    # ── assigned_codes ─────────────────────────────────────────────────────
    op.create_table(
        "assigned_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("code_type", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("modifiers", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("hierarchy", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["coding_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_code_type", "assigned_codes", ["code_type"])
    op.create_index("ix_assigned_code", "assigned_codes", ["code"])
    op.create_index("ix_assigned_codes_session_id", "assigned_codes", ["session_id"])

    # ── knowledge_base_log ─────────────────────────────────────────────────
    op.create_table(
        "knowledge_base_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code_type", sa.String(20), nullable=False),
        sa.Column("total_codes", sa.Integer(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("knowledge_base_log")
    op.drop_index("ix_assigned_codes_session_id", "assigned_codes")
    op.drop_index("ix_assigned_code", "assigned_codes")
    op.drop_index("ix_code_type", "assigned_codes")
    op.drop_table("assigned_codes")
    op.drop_index("ix_coding_sessions_encounter_id", "coding_sessions")
    op.drop_index("ix_coding_sessions_patient_id", "coding_sessions")
    op.drop_index("ix_coding_sessions_status", "coding_sessions")
    op.drop_index("ix_session_user_id", "coding_sessions")
    op.drop_index("ix_session_status_created", "coding_sessions")
    op.drop_index("ix_session_created", "coding_sessions")
    op.drop_table("coding_sessions")
    op.drop_index("ix_refresh_user", "refresh_tokens")
    op.drop_index("ix_refresh_token_hash", "refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index("ix_audit_user", "audit_logs")
    op.drop_index("ix_audit_created", "audit_logs")
    op.drop_index("ix_audit_action", "audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_user_role", "users")
    op.drop_index("ix_user_email", "users")
    op.drop_table("users")
