"""Schema inițială: entries + photos, unaccent + FTS.

Revision ID: 0001
Revises:
Create Date: 2026-07-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    # unaccent() standard e doar STABLE; coloanele generate cer IMMUTABLE,
    # așa că folosim un wrapper care fixează explicit dicționarul.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION f_unaccent(text)
        RETURNS text AS
        $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        """
    )

    op.create_table(
        "entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
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
        sa.Column(
            "search_vector",
            TSVECTOR(),
            sa.Computed(
                "to_tsvector('simple', f_unaccent(coalesce(title, '') || ' ' || body))",
                persisted=True,
            ),
        ),
        sa.UniqueConstraint("entry_date", name="uq_entries_entry_date"),
    )
    op.create_index("ix_entries_entry_date", "entries", ["entry_date"])
    op.create_index(
        "ix_entries_search_vector",
        "entries",
        ["search_vector"],
        postgresql_using="gin",
    )

    op.create_table(
        "photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("r2_key_original", sa.String(length=500), nullable=False),
        sa.Column("r2_key_display", sa.String(length=500), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["entries.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_photos_entry_id", "photos", ["entry_id"])


def downgrade():
    op.drop_table("photos")
    op.drop_table("entries")
    op.execute("DROP FUNCTION IF EXISTS f_unaccent(text)")
