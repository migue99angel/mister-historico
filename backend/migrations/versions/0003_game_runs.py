"""Persist runs, replay inputs, append-only decisions and idempotent replies.

Revision ID: 0003_game_runs
Revises: 0002_catalog
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003_game_runs"
down_revision: str | None = "0002_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("playable_season_id", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("replay_content_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("replay_content_format", sa.Integer(), nullable=False),
        sa.Column("replay_content_digest", sa.String(64), nullable=False),
        sa.CheckConstraint("version >= 0", name="ck_runs_version_nonnegative"),
    )
    op.create_table(
        "run_decisions",
        sa.Column(
            "run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("sequence", sa.Integer(), primary_key=True),
        sa.Column("payload", JSONB(), nullable=False),
        sa.CheckConstraint("sequence > 0", name="ck_run_decisions_sequence_positive"),
    )
    op.create_table(
        "run_idempotency",
        sa.Column(
            "run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("payload", JSONB(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("run_idempotency")
    op.drop_table("run_decisions")
    op.drop_table("runs")
