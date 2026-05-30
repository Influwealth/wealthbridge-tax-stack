"""add tax_documents table

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tax_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("record_id", sa.Integer(), sa.ForeignKey("tax_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type", sa.String(50), nullable=False),   # e.g. "1120", "1065", "schedule_c"
        sa.Column("format", sa.String(10), nullable=False),     # "pdf", "xml", "json"
        sa.Column("vault_key", sa.String(255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tax_documents_record_id", "tax_documents", ["record_id"])
    op.create_index("ix_tax_documents_doc_type", "tax_documents", ["doc_type"])


def downgrade() -> None:
    op.drop_table("tax_documents")
