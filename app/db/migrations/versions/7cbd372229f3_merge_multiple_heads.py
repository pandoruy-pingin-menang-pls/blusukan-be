"""merge multiple heads

Revision ID: 7cbd372229f3
Revises: 9aef02516199, a1b2c3d4e5f6
Create Date: 2026-07-19 02:37:30.327485

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7cbd372229f3'
down_revision: Union[str, None] = ('9aef02516199', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
