"""merge_heads

Revision ID: 1e17be66a8f3
Revises: a1b2c3d4e5f6, c1d2e3f4g5h6
Create Date: 2025-12-14 06:40:59.475652

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e17be66a8f3'
down_revision: Union[str, None] = ('a1b2c3d4e5f6', 'c1d2e3f4g5h6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

