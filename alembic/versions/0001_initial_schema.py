"""initial users and tax_records tables

Revision ID: 0001
Revises:
Create Date: 2026-05-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=150), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "tax_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_name", sa.String(length=255), nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("income", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column(
            "expenses",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("tax_due", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tax_records_id", "tax_records", ["id"])
    op.create_index("ix_tax_records_entity_name", "tax_records", ["entity_name"])
    op.create_index("ix_tax_records_tax_year", "tax_records", ["tax_year"])


def downgrade() -> None:
    op.drop_table("tax_records")
    op.drop_table("users")
