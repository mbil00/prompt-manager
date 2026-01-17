"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-01-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prompts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(100), nullable=True, index=True),
        sa.Column("tags", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("is_template", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("template_vars", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("usage_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime, nullable=True),
        sa.Column("success_notes", sa.Text, nullable=True),
        sa.Column("failure_notes", sa.Text, nullable=True),
        sa.Column("related_slugs", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "prompt_id",
            sa.String(36),
            sa.ForeignKey("prompts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("changed_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("change_note", sa.String(500), nullable=True),
    )

    op.create_index("ix_prompt_versions_prompt_id", "prompt_versions", ["prompt_id"])


def downgrade() -> None:
    op.drop_index("ix_prompt_versions_prompt_id", table_name="prompt_versions")
    op.drop_table("prompt_versions")
    op.drop_table("prompts")
