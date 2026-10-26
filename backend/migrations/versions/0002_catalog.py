"""Catalog snapshots and their content version.

Revision ID: 0002_catalog
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002_catalog"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    version = op.create_table(
        "catalog_version",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_catalog_version_singleton"),
    )
    op.bulk_insert(version, [{"id": 1, "content_hash": ""}])
    op.create_table(
        "catalog_seasons",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("catalog_seasons")
    op.drop_table("catalog_version")
