"""add rd_projects, rd_expenses, rd_documents tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rd_projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("record_id", sa.Integer(), sa.ForeignKey("tax_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("activity_type", sa.String(50), nullable=True),
        sa.Column("is_qualified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("principal_researcher", sa.String(200), nullable=True),
        sa.Column("start_date", sa.String(20), nullable=True),
        sa.Column("end_date", sa.String(20), nullable=True),
        sa.Column("is_ongoing", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("total_qre", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("estimated_credit", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("validation_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rd_projects_record_id", "rd_projects", ["record_id"])

    op.create_table(
        "rd_expenses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("rd_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("qualification_rate", sa.Numeric(5, 4), nullable=False, server_default="1"),
        sa.Column("qualified_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rd_expenses_project_id", "rd_expenses", ["project_id"])

    op.create_table(
        "rd_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("rd_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_name", sa.String(200), nullable=False),
        sa.Column("doc_type", sa.String(50), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("validation_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("issues", sa.Text(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rd_documents_project_id", "rd_documents", ["project_id"])


def downgrade() -> None:
    op.drop_table("rd_documents")
    op.drop_table("rd_expenses")
    op.drop_table("rd_projects")
