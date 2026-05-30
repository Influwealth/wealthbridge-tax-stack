"""add user_roles table and role enum

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLE_ENUM_VALUES = ("admin", "accountant", "business_owner", "agent", "auditor")


def upgrade() -> None:
    # Create the role enum type (PostgreSQL-native; SQLite uses VARCHAR)
    role_enum = sa.Enum(*ROLE_ENUM_VALUES, name="roleenum")
    role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.Enum(*ROLE_ENUM_VALUES, name="roleenum"), nullable=False),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "granted_by",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("ix_user_roles_role", "user_roles", ["role"])


def downgrade() -> None:
    op.drop_table("user_roles")
    sa.Enum(name="roleenum").drop(op.get_bind(), checkfirst=True)
