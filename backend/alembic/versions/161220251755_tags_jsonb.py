from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "161220251755_tags_jsonb"
down_revision = "7a1f5f11d72a"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "processo",
        "tags",
        type_=postgresql.JSONB(),
        postgresql_using="tags::jsonb",
        existing_type=sa.JSON(),
        nullable=False,
    )
    op.create_index(
        "ix_processo_tags_gin",
        "processo",
        ["tags"],
        postgresql_using="gin",
        if_not_exists=True
    )


def downgrade():
    op.drop_index("ix_processo_tags_gin", table_name="processo", if_exists=True)
    op.alter_column(
        "processo",
        "tags",
        type_=sa.JSON(),
        postgresql_using="tags::json",
        existing_type=postgresql.JSONB(),
        nullable=True,
    )