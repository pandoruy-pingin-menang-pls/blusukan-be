"""merge multiple heads

Revision ID: 846e6a25bf64
Revises: 9e88a38c21ba, b7d2e821b0f4
Create Date: 2026-07-21 16:17:00.256020

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '846e6a25bf64'
down_revision: Union[str, None] = ('9e88a38c21ba', 'b7d2e821b0f4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
