"""add expected_4h columns for traffic forecasts (recreated)"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c1d2e3f4g5h6"
down_revision = "039e5d99cb6e"
branch_labels = None
depends_on = None


def upgrade():
    # Columns were previously added; keep upgrade as add to be idempotent if rerun
    op.add_column("traffic_forecasts", sa.Column("expected_4h", sa.Float(), nullable=True))
    op.add_column("segment_risks", sa.Column("expected_4h", sa.Float(), nullable=True))


def downgrade():
    # Drop 4h columns to align with current models
    with op.batch_alter_table("segment_risks") as batch:
        batch.drop_column("expected_4h")
    with op.batch_alter_table("traffic_forecasts") as batch:
        batch.drop_column("expected_4h")

