"""add summary status fields

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "papers",
        sa.Column(
            "summary_status",
            sa.String(),
            nullable=False,
            server_default="idle",
        ),
    )
    op.add_column("papers", sa.Column("summary_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("papers", "summary_error")
    op.drop_column("papers", "summary_status")
