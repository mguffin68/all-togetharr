"""Add the users table.

Revision ID: 0003_users
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_users"
down_revision: str | None = "0002_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("name_key", sa.String(length=100), nullable=False, unique=True),
        sa.Column(
            "role",
            sa.Enum(
                "admin",
                "manager",
                "requester",
                "viewer",
                name="role",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column(
            "auth_source",
            sa.Enum(
                "local",
                "jellyfin",
                "oidc",
                name="auth_source",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "auth_source != 'local' OR password_hash IS NOT NULL",
            name="local_has_password",
        ),
    )


def downgrade() -> None:
    op.drop_table("users")
