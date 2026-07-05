"""Tabela thoughts (gânduri libere, fără dată logică).

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-05

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "thoughts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic", sa.String(length=100), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_thoughts_created_at", "thoughts", ["created_at"])


def downgrade():
    op.drop_table("thoughts")
