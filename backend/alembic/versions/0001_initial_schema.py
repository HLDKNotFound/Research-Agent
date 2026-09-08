"""0001_initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-08 16:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.core.config import settings

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    is_postgres = conn.dialect.name == "postgresql"

    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True)

    # 2. projects
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_projects_created_at", "projects", ["created_at"])
    op.create_index("idx_projects_deleted_at", "projects", ["deleted_at"])

    # 3. project_members
    op.create_table(
        "project_members",
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=50), server_default="member", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id", "user_id"),
    )
    op.create_index("idx_project_members_user_id", "project_members", ["user_id"])

    # 4. conversations
    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), server_default="New Conversation", nullable=False),
        sa.Column("langgraph_thread_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_conversations_project_created", "conversations", ["project_id", "created_at"])
    op.create_index("idx_conversations_thread_id", "conversations", ["langgraph_thread_id"], unique=True)
    op.create_index("idx_conversations_deleted_at", "conversations", ["deleted_at"])

    # 5. messages
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("conversation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_messages_conversation_created", "messages", ["conversation_id", "created_at"])

    # 6. files
    op.create_table(
        "files",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("storage_provider", sa.String(length=50), server_default="local", nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="uploaded", nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=100), nullable=True),
        sa.Column("metadata", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "idempotency_key", name="uq_files_project_idempotency"),
    )
    op.create_index("idx_files_project_created", "files", ["project_id", "created_at"])
    op.create_index("idx_files_project_status", "files", ["project_id", "status"])
    op.create_index("idx_files_deleted_at", "files", ["deleted_at"])
    op.create_index("idx_files_checksum", "files", ["checksum"])

    # 7. file_chunks
    vector_col = sa.Column("embedding", postgresql.ARRAY(sa.Float()).with_variant(sa.JSON(), "sqlite"), nullable=True)
    if is_postgres:
        from pgvector.sqlalchemy import Vector
        vector_col = sa.Column("embedding", Vector(settings.EMBEDDING_DIMENSION), nullable=True)

    op.create_table(
        "file_chunks",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("file_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        vector_col,
        sa.Column("metadata", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_id", "chunk_index", name="uq_file_chunks_file_index"),
    )
    op.create_index("idx_file_chunks_file_page", "file_chunks", ["file_id", "page_number"])

    # 8. runs
    op.create_table(
        "runs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("conversation_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="queued", nullable=False),
        sa.Column("current_step", sa.String(length=100), nullable=True),
        sa.Column("progress_pct", sa.Integer(), server_default="0", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_retries", sa.Integer(), server_default="3", nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=True),
        sa.Column("langgraph_thread_id", sa.String(length=255), nullable=True),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_details", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=True),
        sa.Column("config", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "idempotency_key", name="uq_runs_project_idempotency"),
    )
    op.create_index("idx_runs_project_created", "runs", ["project_id", "created_at"])
    op.create_index("idx_runs_project_status", "runs", ["project_id", "status"])
    op.create_index("idx_runs_conversation_created", "runs", ["conversation_id", "created_at"])

    # 9. run_steps
    op.create_table(
        "run_steps",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("run_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("step_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("input", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=True),
        sa.Column("output", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_run_steps_run_started", "run_steps", ["run_id", "started_at"])

    # 10. run_events
    op.create_table(
        "run_events",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("run_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("agent_name", sa.String(length=50), nullable=True),
        sa.Column("step_number", sa.Integer(), server_default="0", nullable=False),
        sa.Column("payload", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_run_events_run_created", "run_events", ["run_id", "created_at"])
    op.create_index("idx_run_events_run_type", "run_events", ["run_id", "event_type"])

    # 11. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_logs_user_created", "audit_logs", ["user_id", "created_at"])
    op.create_index("idx_audit_logs_project_created", "audit_logs", ["project_id", "created_at"])
    op.create_index("idx_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"])

    # 12. evidence
    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("run_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("file_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("chunk_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_title", sa.String(length=500), nullable=True),
        sa.Column("source_domain", sa.String(length=255), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("metadata", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chunk_id"], ["file_chunks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_evidence_run_type", "evidence", ["run_id", "type"])
    op.create_index("idx_evidence_run_created", "evidence", ["run_id", "created_at"])
    op.create_index("idx_evidence_run_score", "evidence", ["run_id", "relevance_score"])

    # 13. reports
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("run_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="completed", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("format", sa.String(length=50), server_default="markdown", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index("idx_reports_project_created", "reports", ["project_id", "created_at"])
    op.create_index("idx_reports_deleted_at", "reports", ["deleted_at"])

    # 14. report_sections
    op.create_table(
        "report_sections",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("report_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("section_key", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("section_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="completed", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_report_sections_order", "report_sections", ["report_id", "section_order"])

    # 15. citations
    op.create_table(
        "citations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("report_section_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("evidence_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("citation_text", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["report_section_id"], ["report_sections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_citations_section_position", "citations", ["report_section_id", "position"])


def downgrade() -> None:
    op.drop_table("citations")
    op.drop_table("report_sections")
    op.drop_table("reports")
    op.drop_table("evidence")
    op.drop_table("audit_logs")
    op.drop_table("run_events")
    op.drop_table("run_steps")
    op.drop_table("runs")
    op.drop_table("file_chunks")
    op.drop_table("files")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_table("users")

    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("DROP EXTENSION IF EXISTS vector;")
